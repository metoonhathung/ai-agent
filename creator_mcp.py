from mcp.server.fastmcp import FastMCP
from typing import Optional
from tools import image_generate

mcp = FastMCP(name="Creator MCP Server",description="Create a new image or edit an existing image (image_url provided) from a query.", host="0.0.0.0", port=8001)

@mcp.tool()
async def generate_image(query: str, image_url: Optional[str] = None) -> str:
    """Create a new image or edit an existing image (image_url provided) from a query."""
    output = await image_generate.ainvoke({"query": query, "image_url": image_url})
    return output

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
