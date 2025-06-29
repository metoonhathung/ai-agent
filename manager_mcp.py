from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os
import asyncio
import httpx
from typing import Any
from uuid import uuid4
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    SendMessageResponse,
    SendMessageRequest,
    MessageSendParams,
)

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    urls = [os.environ['RESEARCHER_SERVER_URL'], os.environ['CREATOR_SERVER_URL']]
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [A2ACardResolver(client, url).get_agent_card() for url in urls]
        cards = await asyncio.gather(*tasks)
        yield {"cards": cards}

mcp = FastMCP(
    name="Manager MCP Server",
    description="Talk to other agents",
    host="0.0.0.0",
    port=8080,
    lifespan=app_lifespan,
)

@mcp.tool()
async def list_agents() -> list:
    """List all available agents."""
    ctx = mcp.get_context()
    cards = ctx.request_context.lifespan_context["cards"]
    tools = [{"name": card.name, "description": card.description, "url": card.url} for card in cards]
    print(f"Request: , Response: {tools}")
    return tools

@mcp.tool()
async def execute_agent(tool_name: str, input: str) -> str:
    """Call an agent with the given input."""
    ctx = mcp.get_context()
    cards = ctx.request_context.lifespan_context["cards"]
    card = next((card for card in cards if card.name == tool_name), None)
    async with httpx.AsyncClient(timeout=30) as httpx_client:
        client = A2AClient(httpx_client, card, card.url)
        message_id = str(uuid4())
        payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': input}],
                'messageId': message_id,
            },
        }
        request = SendMessageRequest(id=message_id, params=MessageSendParams(**payload))
        response: SendMessageResponse = await client.send_message(request)
        result = response.root.result.artifacts[0].parts[0].root.text if hasattr(response, 'root') else ""
        print(f"Request: {tool_name} + {input}, Response: {result}")
        return result

if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http")
