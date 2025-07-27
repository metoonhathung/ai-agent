from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from typing import Optional
from collections import Counter
import os
import requests
import tempfile
import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import PyPDFLoader
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from psycopg import AsyncConnection
from tools import online_search, image_generate, supabase

_ = load_dotenv(find_dotenv())

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

agent = None
tools = None
checkpointer = None
model = None
prompt = None
vector_store = None

@app.on_event("startup")
async def startup_event():
    global agent, tools, checkpointer, model, prompt, vector_store
    
    index = faiss.IndexFlatL2(len(OpenAIEmbeddings().embed_query("hello world")))
    vector_store = FAISS(embedding_function=OpenAIEmbeddings(), index=index, docstore= InMemoryDocstore(), index_to_docstore_id={})
    retriever = vector_store.as_retriever()
    retriever_tool = create_retriever_tool(retriever, "document_retrieval", "Analyze uploaded PDF documents")

    tools = [retriever_tool, online_search, image_generate]
    # client = MultiServerMCPClient({"default": {"url": os.environ['MANAGER_MCP_URL'], "transport": "streamable_http"}})
    # mcp_tools = await client.get_tools()
    # tools = [retriever_tool] + mcp_tools

    connection_kwargs = {"autocommit": True, "prepare_threshold": 0, "sslmode": "require", "gssencmode": "disable"}
    conn = await AsyncConnection.connect(os.environ['SUPABASE_DB_URI'], **connection_kwargs)
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()

    model = "gpt-4.1"
    prompt = """You are a helpful assistant that can search the web and create/edit images."""
    # prompt = """
    # You are a world class powerful assistant, managing a group of agents with different capabilities.
    # Must always call the 'list_agents' tool only once initially to get full list of capabilities of agents, so you know what you are capable of.
    # Call the 'execute_agent' tool to call relevant agent with the input.
    # """

    agent = create_react_agent(model=model, tools=tools, checkpointer=checkpointer, prompt=prompt)

class ChatRequest(BaseModel):
    text: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None

class ToolRequest(BaseModel):
    tool_url: str
    tool_type: str

@app.get("/")
async def root():
    return {"message": "OK"}

@app.get("/chat")
async def get_chats():
    threads = supabase.table("checkpoints").select("thread_id").execute()
    counts = dict(Counter(thread["thread_id"] for thread in threads.data))
    rooms = [{"Room": thread_id, "Messages": count} for thread_id, count in counts.items()]
    return rooms

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
            "content": [{"type": "text", "text": payload.text}, {"type": "image_url", "image_url": {"url": payload.file_url}}] if (payload.file_url and payload.file_type in ["image/jpeg", "image/png"]) else payload.text
        }]},
        config
    )
    output = response["messages"][-1].content
    print(f"Request: {payload.text}, Response: {output}")
    return output

async def add_mcp(mcp_url: str):
    global agent, tools
    client = MultiServerMCPClient({"import": {"url": mcp_url, "transport": "streamable_http"}})
    mcp_tools = await client.get_tools()
    tools += mcp_tools
    agent = create_react_agent(model=model, tools=tools, checkpointer=checkpointer, prompt=prompt)
    return {"message": "MCP added."}

async def add_pdf(pdf_url: str):
    global agent, tools, vector_store
    response = requests.get(pdf_url)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(response.content)
        local_pdf_path = tmp_file.name
    loader = PyPDFLoader(local_pdf_path)
    pages = loader.load_and_split()
    vector_store.add_documents(pages)
    retriever = vector_store.as_retriever()
    retriever_tool = create_retriever_tool(retriever, "document_retrieval", "Analyze uploaded PDF documents")
    tools[0] = retriever_tool
    agent = create_react_agent(model=model, tools=tools, checkpointer=checkpointer, prompt=prompt)
    os.remove(local_pdf_path)
    return {"message": "PDF added."}

@app.post("/tools")
async def add_tool(payload: ToolRequest):
    if payload.tool_type == "mcp":
        return await add_mcp(payload.tool_url)
    elif payload.tool_type == "pdf":
        return await add_pdf(payload.tool_url)
    else:
        return {"message": "No valid tool request provided."}
