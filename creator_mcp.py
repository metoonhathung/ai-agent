from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import requests
import os
import uuid
from supabase import create_client
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    yield {"supabase": supabase}

mcp = FastMCP(
    name="Creator MCP Server",
    description="Create images",
    host="0.0.0.0",
    port=8001,
    lifespan=app_lifespan,
)

def call_inference_api(model, inputs, type):
    ctx = mcp.get_context()
    supabase = ctx.request_context.lifespan_context["supabase"]
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {os.environ['HUGGINGFACEHUB_API_TOKEN']}"}
    payload = {"inputs": inputs}
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        bucket = "llm"
        path = f"{uuid.uuid4()}.{type.split('/')[1]}"
        res = supabase.storage.from_(bucket).upload(
            path=path,
            file=response.content,
            file_options={"content-type": type}
        )
        if res.path:
            public_url = supabase.storage.from_(bucket).get_public_url(res.path)
            print(f"Request: {inputs}, Response: {public_url}")
            return public_url
    else:
        return None

@mcp.tool()
async def create_image(query: str) -> str:
    """Create an image from a query"""
    output = call_inference_api("stabilityai/stable-diffusion-xl-base-1.0", query, "image/jpeg")
    return output

if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http")
