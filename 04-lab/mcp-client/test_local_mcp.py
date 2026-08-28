"""Smoke test for the local Lab 04 Streamable HTTP MCP server."""

from __future__ import annotations

import asyncio

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:8085/mcp"


async def main() -> None:
    async with httpx.AsyncClient() as http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print("MCP tools:", ", ".join(tool.name for tool in tools.tools))

                health = await session.call_tool("health_check", {})
                print("health_check:", health.content[0].text)

                current = await session.call_tool("get_current_weather", {"city": "Hanoi"})
                print("get_current_weather(Hanoi):")
                print(current.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
