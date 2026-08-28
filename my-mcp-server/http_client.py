"""HTTP authentication test for Workspace Search MCP Server.

Start server.py in another terminal with MCP_TRANSPORT=streamable-http first.
The script proves missing and invalid tokens are rejected, then makes a valid
MCP call using the token in MCP_AUTH_TOKEN.
"""

from __future__ import annotations

import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp")


async def _rejection_status(label: str, token: str | None) -> int:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    initialize_request = {
        "jsonrpc": "2.0",
        "id": label,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "workspace-auth-test", "version": "1.0.0"},
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(SERVER_URL, headers=headers, json=initialize_request, timeout=10.0)
    print(f"{label}: HTTP {response.status_code}")
    return response.status_code


async def _valid_call(token: str) -> None:
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "search_workspace_v2",
                    {"keyword": "MCP", "extensions": [".md"], "limit": 3},
                )
                print("valid token: MCP call succeeded")
                print(result.content[0].text)


async def main() -> None:
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        raise SystemExit("Set MCP_AUTH_TOKEN before running this client.")

    missing_status = await _rejection_status("missing token", None)
    invalid_status = await _rejection_status("invalid token", "definitely-not-the-right-token")
    if missing_status not in {401, 403} or invalid_status not in {401, 403}:
        raise RuntimeError("Expected missing and invalid tokens to be rejected with HTTP 401 or 403.")
    await _valid_call(token)


if __name__ == "__main__":
    asyncio.run(main())
