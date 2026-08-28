"""Version-aware client: đọc metadata và ưu tiên tool v2."""

from __future__ import annotations

import asyncio
import json
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
            info = await session.read_resource("server://info")
            metadata = json.loads(info.contents[0].text)
            print(f"Server {metadata['name']} v{metadata['version']}")
            print(f"Migration: {metadata['migration_guide']}")

            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            selected_tool = "search_workspace_v2" if "search_workspace_v2" in tool_names else "search_workspace"
            print(f"Selected tool: {selected_tool}")

            result = await session.call_tool(
                selected_tool,
                {"keyword": "MCP", "extensions": [".md", ".py"], "limit": 5}
                if selected_tool == "search_workspace_v2"
                else {"keyword": "MCP", "limit": 5},
            )
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
