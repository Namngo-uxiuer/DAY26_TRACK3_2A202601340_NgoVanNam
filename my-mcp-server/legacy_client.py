"""Legacy client: chứng minh search_workspace v1 vẫn chạy qua stdio."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).with_name("server.py")


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search_workspace", {"keyword": "MCP", "limit": 3})
            print("[v1] search_workspace vẫn hoạt động:")
            print(result.content[0].text)

            excerpt = await session.call_tool(
                "read_workspace_file",
                {"relative_path": "README.md", "start_line": 1, "max_lines": 5},
            )
            print("\nread_workspace_file:")
            print(excerpt.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
