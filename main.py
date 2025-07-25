import streamlit as st
import asyncio
from dotenv import load_dotenv, find_dotenv
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

_ = load_dotenv(find_dotenv())

async def startup():
    tools = []
    if st.session_state.get("mcp_url"):
        client = MultiServerMCPClient({"search": {"url": st.session_state["mcp_url"], "transport": "streamable_http"}})
        tools = await client.get_tools()
    st.session_state["agent"] = create_react_agent(
        model="gpt-4o",
        tools=tools,
        prompt="You are a helpful assistant",
        checkpointer=st.session_state["checkpointer"]
    )

async def history():
    room_id = st.session_state["room_id"]
    config = {"configurable": {"thread_id": room_id}}
    snapshot = await st.session_state["agent"].aget_state(config)
    messages = snapshot.values["messages"] if "messages" in snapshot.values else []
    return messages

async def chat():
    room_id = st.session_state["room_id"]
    text = st.session_state["text"]
    if not text: return
    config = {"configurable": {"thread_id": room_id}}
    response = await st.session_state["agent"].ainvoke({"messages": [{"role": "user", "content": text}]}, config)
    content = response["messages"][-1].content
    return content

async def main():
    if "checkpointer" not in st.session_state:
        st.session_state["checkpointer"] = InMemorySaver()
    if "agent" not in st.session_state:
        await startup()
    st.title("AI Agent")
    with st.sidebar:
        st.text_input("Room ID", key="room_id")
        st.text_input("MCP URL", key="mcp_url", on_change=lambda: asyncio.run(startup()))
    if not st.session_state["room_id"]:
        st.info("Enter Room ID")
        st.stop()
    st.chat_input("Ask anything", key="text", on_submit=lambda: asyncio.run(chat()))
    messages = await history()
    for message in messages:
        if message.type in ["human", "ai"] and message.content:
            st.chat_message(message.type).write(message.content)
        else:
            msg = st.chat_message(message.type)
            expander = msg.expander("Reasoning...")
            expander.write(message)

asyncio.run(main())
