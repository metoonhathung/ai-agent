from mcp.server.fastmcp import FastMCP
from tools import online_search

mcp = FastMCP(name="Researcher MCP Server", description="Search online", host="0.0.0.0", port=8000)

@mcp.tool()
async def search_online(query: str) -> str:
    """Search online for a query"""
    output = await online_search.ainvoke(query)
    return output

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
