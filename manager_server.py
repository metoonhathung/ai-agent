from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
import os

_ = load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

agent = None

@app.on_event("startup")
async def startup_event():
    global agent
    client = MultiServerMCPClient(
        {
            "search": {
                "url": os.environ['MANAGER_MCP_URL'],
                "transport": "streamable_http",
            }
        }
    )
    tools = await client.get_tools()
    agent = create_react_agent(
        model="gpt-4o",
        tools=tools,
        prompt="""
        You are a world class powerful assistant, managing a group of agents with different capabilities.
        Call the list_agents tool to get full list of capabilities of agents.
        Call the execute_agent tool to call relevant agent with the input.
        """,
        checkpointer=InMemorySaver()
    )

class ChatRequest(BaseModel):
    text: str

@app.get("/")
async def root():
    return {"message": "OK"}

@app.get("/chat/{room_id}")
async def get_chat(room_id: str):
    config = {"configurable": {"thread_id": room_id}}
    snapshot = agent.get_state(config)
    messages = snapshot.values["messages"] if "messages" in snapshot.values else []
    return {"messages": messages}

@app.post("/chat/{room_id}")
async def post_chat(room_id: str, payload: ChatRequest):
    config = {"configurable": {"thread_id": room_id}}
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": payload.text}]},
        config  
    )
    output = response["messages"][-1].content
    print(f"Request: {payload.text}, Response: {output}")
    return output
