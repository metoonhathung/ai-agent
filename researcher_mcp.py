from mcp.server.fastmcp import FastMCP
from langchain_community.tools import DuckDuckGoSearchRun

mcp = FastMCP(name="Researcher MCP Server", description="Search online", host="0.0.0.0", port=8000)

search = DuckDuckGoSearchRun()

@mcp.tool()
async def search_online(query: str) -> str:
    """Search DuckDuckGo for a query"""
    output = await search.arun(query)
    print(f"Request: {query}, Response: {output}")
    return output

if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http")
