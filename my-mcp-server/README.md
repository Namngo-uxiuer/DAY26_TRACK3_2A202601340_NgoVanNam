# Workspace Search MCP Server

MCP server cho tác vụ thực tế: tra cứu nhanh tài liệu và mã nguồn trong repository học tập. Thay vì mở từng file rồi tìm thủ công, Claude Code có thể tìm nội dung và đọc một đoạn file qua MCP tools.

Server chỉ đọc các file text được cho phép (`.md`, `.py`, `.txt`, `.json`, `.toml`, `.yaml`, `.yml`) bên trong repository. Nó bỏ qua `.git`, virtual environments, `node_modules` và không chấp nhận đường dẫn vượt ra ngoài workspace.

## Tools

| Tool | Phiên bản | Input | Output |
| --- | --- | --- | --- |
| `search_workspace` | v1, deprecated | `keyword`, `limit` | Các dòng text `path:line:snippet`; vẫn giữ cho client cũ. |
| `search_workspace_v2` | v2 | `keyword`, `extensions?`, `limit?` | JSON có `matches`, line number, snippets, số file đã quét và cờ `truncated`. |
| `read_workspace_file` | v1 | `relative_path`, `start_line?`, `max_lines?` | JSON chứa một đoạn nội dung file an toàn. |

Resource `server://info` công bố server version, tool versions, deprecation và migration guide.

## Cài đặt

Dependencies của repository đã nằm ở `../requirements.txt` và môi trường gốc `.venv` đã được tạo.

```powershell
cd D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer
.\.venv\Scripts\Activate.ps1
cd .\my-mcp-server
```

## Chạy local qua stdio

`stdio` là mặc định và không cần token/API key.

```powershell
python .\legacy_client.py
python .\versioned_client.py
```

`legacy_client.py` chứng minh client cũ vẫn gọi được `search_workspace` v1. `versioned_client.py` đọc `server://info`, phát hiện v2 và ưu tiên `search_workspace_v2`.

## Đăng ký với Claude Code

Từ thư mục gốc repository, chạy lệnh sau. Dùng đúng Python trong `.venv` để Claude Code luôn có đủ MCP dependencies.

```powershell
claude mcp add workspace-search --scope project -- "D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer\.venv\Scripts\python.exe" "D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer\my-mcp-server\server.py"
claude mcp get workspace-search
```

Sau khi mở/reload Claude Code trong repo, thử câu tự nhiên:

```text
Tìm trong repository những file nói về authentication của MCP, rồi đọc phần hướng dẫn chạy auth server.
```

Lệnh `claude mcp add <name> -- <command> [args...]` và `--scope project` là cú pháp Claude Code hiện hành; xem [tài liệu MCP của Anthropic](https://docs.anthropic.com/en/docs/claude-code/mcp).

## Streamable HTTP + authentication

Không đưa token thật vào source code hay Git. Copy mẫu `.env.example` để tham khảo, nhưng trong PowerShell hãy đặt token vào environment của terminal đang chạy server:

Terminal 1:

```powershell
cd D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer
.\.venv\Scripts\Activate.ps1
cd .\my-mcp-server
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_AUTH_TOKEN = "tu-tao-mot-token-dai-va-ngau-nhien"
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8765"
python .\server.py
```

Terminal 2, dùng đúng **cùng giá trị** `MCP_AUTH_TOKEN`:

```powershell
cd D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer
.\.venv\Scripts\Activate.ps1
cd .\my-mcp-server
$env:MCP_AUTH_TOKEN = "tu-tao-mot-token-dai-va-ngau-nhien"
python .\http_client.py
```

`http_client.py` kiểm tra cả ba tình huống: không token, token sai (đều phải nhận HTTP 401/403), và token hợp lệ (MCP call thành công). Server bind mặc định `127.0.0.1`; nếu cần thử LAN, đặt `MCP_HOST=0.0.0.0`, mở firewall cho port 8765 và đặt `MCP_SERVER_BASE_URL`/`MCP_SERVER_URL` thành IP LAN phù hợp.

## Versioning và backward compatibility

`search_workspace` v1 trả text theo format cũ nên legacy client tiếp tục chạy. `search_workspace_v2` là tool song song trả JSON cấu trúc, đồng thời thêm tham số optional `extensions` và `limit`. Client mới phải đọc `server://info`, dùng v2 nếu server công bố nó và fallback v1 nếu không có.

## Secret checklist

- Không commit `.env`, API key, token hoặc password.
- Mẫu [`.env.example`](.env.example) chỉ có placeholder, an toàn để commit.
- Bài này không cần Gemini hay WeatherAPI key. Hai key đó chỉ cần nếu chạy Lab 04 weather agent có sẵn.
