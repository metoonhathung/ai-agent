from mcp.server.fastmcp import FastMCP
from langchain_community.tools import DuckDuckGoSearchRun

mcp = FastMCP("Search")

search = DuckDuckGoSearchRun()

@mcp.tool()
async def search_online(query: str) -> str:
    """Search DuckDuckGo for a query"""
    return search.run(query)

if __name__ == "__main__":
    mcp.run(transport="stdio")
    # mcp.run(transport="streamable-http")
