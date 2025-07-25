from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from typing import Optional
import os
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from psycopg import AsyncConnection
from tools import online_search, image_generate

_ = load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

agent = None

@app.on_event("startup")
async def startup_event():
    global agent

    tools = [online_search, image_generate]
    # client = MultiServerMCPClient({"search": {"url": os.environ['MANAGER_MCP_URL'], "transport": "streamable_http"}})
    # tools = await client.get_tools()

    connection_kwargs = {"autocommit": True, "prepare_threshold": 0, "sslmode": "require", "gssencmode": "disable"}
    conn = await AsyncConnection.connect(os.environ['SUPABASE_DB_URI'], **connection_kwargs)
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()

    agent = create_react_agent(
        model="gpt-4.1",
        tools=tools,
        checkpointer=checkpointer,
        prompt="""You are a helpful assistant that can search the web and create/edit images.""",
        # prompt="""
        # You are a world class powerful assistant, managing a group of agents with different capabilities.
        # Must always call the 'list_agents' tool only once initially to get full list of capabilities of agents, so you know what you are capable of.
        # Call the 'execute_agent' tool to call relevant agent with the input.
        # """,
    )

class ChatRequest(BaseModel):
    text: str
    image_url: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "OK"}

@app.get("/chat/{room_id}")
async def get_chat(room_id: str):
    config = {"configurable": {"thread_id": room_id}}
    snapshot = await agent.aget_state(config)
    messages = snapshot.values["messages"] if "messages" in snapshot.values else []
    return {"messages": messages}

@app.post("/chat/{room_id}")
async def post_chat(room_id: str, payload: ChatRequest):
    config = {"configurable": {"thread_id": room_id}}
    response = await agent.ainvoke(
        {"messages": [{
            "role": "user",
            "content": payload.text if not payload.image_url else [
                {"type": "text", "text": f"{payload.text}. Image URL: {payload.image_url}"},
                {"type": "image_url", "image_url": {"url": payload.image_url}}
            ]
        }]},
        config
    )
    output = response["messages"][-1].content
    print(f"Request: {payload.text}, Response: {output}")
    return output
