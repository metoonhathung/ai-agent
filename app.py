from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.tools import DuckDuckGoSearchRun

_ = load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

search = DuckDuckGoSearchRun()

checkpointer = InMemorySaver()

agent = create_react_agent(
    model="gpt-4o",
    tools=[search],
    prompt="You are a helpful assistant",
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
    response = agent.invoke(
        {"messages": [{"role": "user", "content": payload.text}]},
        config  
    )
    return response
