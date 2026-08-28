"""Workspace Search MCP Server.

Use case: thay vì mở từng README/Python file và tìm bằng tay, AI client có thể
tìm nội dung hoặc đọc một đoạn file trong chính repository này. Server chỉ đọc
những file text được cho phép bên trong repository; không nhận đường dẫn tuyệt
đối và không thể đi ra ngoài workspace.

Transport:
  - stdio (mặc định): dùng cho Claude Code trên cùng máy.
  - streamable-http: bật bằng MCP_TRANSPORT=streamable-http và yêu cầu bearer
    token từ MCP_AUTH_TOKEN.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

SERVER_NAME = "workspace-search"
SERVER_VERSION = "2.0.0"
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_EXTENSIONS = {".md", ".py", ".txt", ".json", ".toml", ".yaml", ".yml"}
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules"}
MAX_FILE_BYTES = 1_000_000
MAX_RESULTS = 50


def _transport() -> str:
    """Return the configured transport in the spelling accepted by MCPServer."""
    value = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if value in {"http", "streamable_http", "streamable-http"}:
        return "streamable-http"
    if value == "stdio":
        return "stdio"
    raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'.")


def _http_base_url() -> str:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = os.getenv("MCP_PORT", "8765")
    return os.getenv("MCP_SERVER_BASE_URL", f"http://{host}:{port}").rstrip("/")


class EnvironmentTokenVerifier(TokenVerifier):
    """Verify exactly one bearer token supplied through MCP_AUTH_TOKEN.

    The token stays in the process environment and is never written to source
    control. A production deployment would replace this with JWT/OAuth checks.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        expected_token = os.getenv("MCP_AUTH_TOKEN")
        if not expected_token or token != expected_token:
            return None
        return AccessToken(token=token, client_id="workspace-search-client", scopes=["workspace:read"])


def _create_server() -> MCPServer:
    instructions = (
        "Search and read text files inside the current learning repository. "
        "Use search_workspace_v2 when structured results are useful. "
        "search_workspace is the legacy v1 tool and remains available for old clients."
    )
    if _transport() == "streamable-http":
        base_url = _http_base_url()
        return MCPServer(
            SERVER_NAME,
            instructions=instructions,
            auth=AuthSettings(issuer_url=base_url, resource_server_url=base_url),
            token_verifier=EnvironmentTokenVerifier(),
        )
    return MCPServer(SERVER_NAME, instructions=instructions)


mcp = _create_server()


def _relative_path(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()


def _is_allowed_file(path: Path) -> bool:
    """Allow only small text files contained in the workspace root."""
    try:
        resolved = path.resolve()
        relative = resolved.relative_to(WORKSPACE_ROOT)
    except (OSError, ValueError):
        return False

    if any(part in IGNORED_DIRECTORIES for part in relative.parts):
        return False
    if not resolved.is_file() or resolved.is_symlink():
        return False
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    try:
        return resolved.stat().st_size <= MAX_FILE_BYTES
    except OSError:
        return False


def _iter_workspace_files(extensions: set[str]) -> Iterator[Path]:
    for path in WORKSPACE_ROOT.rglob("*"):
        if path.suffix.lower() in extensions and _is_allowed_file(path):
            yield path


def _normalise_extensions(extensions: list[str] | None) -> set[str]:
    if not extensions:
        return set(ALLOWED_EXTENSIONS)

    normalised = {
        (extension if extension.startswith(".") else f".{extension}").lower().strip()
        for extension in extensions
        if extension and extension.strip()
    }
    return normalised & ALLOWED_EXTENSIONS


def _bounded_limit(limit: int) -> int:
    return max(1, min(limit, MAX_RESULTS))


def _search(keyword: str, extensions: set[str], limit: int) -> tuple[list[dict[str, object]], int, bool]:
    needle = keyword.casefold().strip()
    if not needle:
        raise ValueError("keyword must not be empty.")

    matches: list[dict[str, object]] = []
    scanned_files = 0
    truncated = False
    for path in _iter_workspace_files(extensions):
        scanned_files += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if needle in line.casefold():
                matches.append(
                    {
                        "path": _relative_path(path),
                        "line": line_number,
                        "snippet": line.strip()[:300],
                    }
                )
                if len(matches) >= limit:
                    truncated = True
                    return matches, scanned_files, truncated
    return matches, scanned_files, truncated


@mcp.tool()
def search_workspace(keyword: str, limit: int = 10) -> str:
    """[v1 - legacy] Tìm keyword trong tài liệu và mã nguồn của repository.

    Giữ nguyên cho client cũ. Client mới nên dùng search_workspace_v2 để nhận
    JSON có cấu trúc và có thể lọc theo phần mở rộng file.
    """
    matches, _, truncated = _search(keyword, set(ALLOWED_EXTENSIONS), _bounded_limit(limit))
    if not matches:
        return f"Không tìm thấy kết quả nào cho {keyword!r}."

    lines = [f"{item['path']}:{item['line']}: {item['snippet']}" for item in matches]
    if truncated:
        lines.append(f"... kết quả đã được giới hạn ở {_bounded_limit(limit)} dòng.")
    return "\n".join(lines)


@mcp.tool()
def search_workspace_v2(
    keyword: str,
    extensions: list[str] | None = None,
    limit: int = 20,
) -> str:
    """[v2] Tìm keyword và trả JSON có cấu trúc.

    Args:
        keyword: Chuỗi cần tìm, không phân biệt hoa thường.
        extensions: Danh sách đuôi file tùy chọn, ví dụ [".md", ".py"].
        limit: Số kết quả tối đa từ 1 đến 50, mặc định 20.
    """
    selected_extensions = _normalise_extensions(extensions)
    if extensions and not selected_extensions:
        return json.dumps(
            {
                "error": "Không có phần mở rộng hợp lệ.",
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            },
            ensure_ascii=False,
        )

    bounded_limit = _bounded_limit(limit)
    matches, scanned_files, truncated = _search(keyword, selected_extensions, bounded_limit)
    return json.dumps(
        {
            "api_version": "2.0",
            "keyword": keyword,
            "extensions": sorted(selected_extensions),
            "scanned_files": scanned_files,
            "returned_matches": len(matches),
            "truncated": truncated,
            "matches": matches,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def read_workspace_file(relative_path: str, start_line: int = 1, max_lines: int = 80) -> str:
    """Đọc một đoạn file text trong workspace một cách an toàn.

    Args:
        relative_path: Đường dẫn tương đối từ gốc repository, ví dụ README.md.
        start_line: Dòng bắt đầu, đánh số từ 1.
        max_lines: Số dòng tối đa cần trả về, từ 1 đến 200.
    """
    if start_line < 1:
        return json.dumps({"error": "start_line must be at least 1."}, ensure_ascii=False)

    requested_path = (WORKSPACE_ROOT / relative_path).resolve()
    if not _is_allowed_file(requested_path):
        return json.dumps(
            {
                "error": "File không tồn tại, không được hỗ trợ hoặc nằm ngoài workspace.",
                "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
            },
            ensure_ascii=False,
        )

    safe_max_lines = max(1, min(max_lines, 200))
    try:
        all_lines = requested_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return json.dumps({"error": f"Không thể đọc file: {error}"}, ensure_ascii=False)

    start_index = start_line - 1
    excerpt = all_lines[start_index : start_index + safe_max_lines]
    return json.dumps(
        {
            "path": _relative_path(requested_path),
            "start_line": start_line,
            "end_line": start_index + len(excerpt),
            "total_lines": len(all_lines),
            "content": "\n".join(excerpt),
        },
        ensure_ascii=False,
    )


@mcp.resource("server://info")
def server_info() -> str:
    """Metadata về version, capability và lộ trình migration của server."""
    return json.dumps(
        {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "workspace_root": WORKSPACE_ROOT.name,
            "transport": _transport(),
            "capabilities": ["safe-file-search", "safe-file-read", "bearer-auth-over-http"],
            "tools": {
                "search_workspace": {
                    "version": "1.0.0",
                    "deprecated": True,
                    "replacement": "search_workspace_v2",
                },
                "search_workspace_v2": {"version": "2.0.0", "deprecated": False},
                "read_workspace_file": {"version": "1.0.0", "deprecated": False},
            },
            "migration_guide": "Client mới đọc server://info và ưu tiên search_workspace_v2; "
            "client cũ vẫn có thể gọi search_workspace.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )


def main() -> None:
    transport = _transport()
    if transport == "streamable-http":
        if not os.getenv("MCP_AUTH_TOKEN"):
            raise SystemExit("MCP_AUTH_TOKEN is required when MCP_TRANSPORT=streamable-http.")
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8765"))
        mcp.run(transport="streamable-http", host=host, port=port)
        return
    mcp.run()


if __name__ == "__main__":
    main()
