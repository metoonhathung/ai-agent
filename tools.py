import httpx
import os
import uuid
import base64
import json
from typing import Optional
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv, find_dotenv
from langchain.tools import tool
from ddgs import DDGS

_ = load_dotenv(find_dotenv())

search = DDGS()

client = OpenAI()

supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def upload_supabase(content, type):
    print(f"Request: {type}, Tool: upload_supabase")
    bucket = "llm"
    path = f"{uuid.uuid4()}.{type.split('/')[1]}"
    res = supabase.storage.from_(bucket).upload(
        path=path,
        file=content,
        file_options={"content-type": type}
    )
    if res.path:
        public_url = supabase.storage.from_(bucket).get_public_url(res.path)
        print(f"Request: {type}, Response: {public_url}")
        return public_url

@tool
async def image_generate(query: str, image_url: Optional[str] = None) -> str:
    """Create a new image or edit an existing image (image_url provided) from a query."""
    print(f"Request: {query} + {image_url}, Tool: image_generate")
    if image_url:
        image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{image_data}"
    response = client.responses.create(
        model="gpt-4.1",
        input=query if not image_url else [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": query},
                    {"type": "input_image", "image_url": data_uri}
                ],
            }
        ],
        tools=[{"type": "image_generation"}],
    )
    image_generation_calls = [output for output in response.output if output.type == "image_generation_call"]
    image_data = [output.result for output in image_generation_calls]
    if image_data:
        image_base64 = image_data[0]
        image_bytes = base64.b64decode(image_base64)
        output = upload_supabase(image_bytes, "image/jpeg")
        print(f"Request: {query} + {image_url}, Response: {output}")
        return output
    else:
        return None

@tool
async def online_search(query: str) -> str:
    """Search online for a query"""
    print(f"Request: {query}, Tool: online_search")
    data = search.text(query)
    output = json.dumps(data)
    print(f"Request: {query}, Response: {output}")
    return output
