from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import tool
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

_ = load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

WORKER_URL = "http://localhost:10000"
checkpointer = InMemorySaver()
cards = []
agent = None

@app.on_event("startup")
async def startup_event():
    global cards, agent
    urls = [WORKER_URL]
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [A2ACardResolver(client, url).get_agent_card() for url in urls]
        cards = await asyncio.gather(*tasks)

    @tool
    async def list_agents() -> list:
        """List all available agents."""
        tools = [{"name": card.name, "description": card.description, "url": card.url} for card in cards]
        return tools

    @tool
    async def execute_agent(tool_name: str, input: str) -> str:
        """Call an agent with the given input."""
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
            return result

    tools = [list_agents, execute_agent]
    agent = create_react_agent(
        model="gpt-4o",
        tools=tools,
        prompt="You are a world class manager of agents. You can also call the list_agents tool to get the list of available agents. Then you can call the execute_agent tool to call the agent with the input.",
        checkpointer=checkpointer
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
    return response["messages"][-1].content
