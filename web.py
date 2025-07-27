import streamlit as st
import requests
from dotenv import load_dotenv, find_dotenv
import os
from tools import upload_supabase

_ = load_dotenv(find_dotenv())

def chats():
    url = f"{os.environ['MANAGER_SERVER_URL']}/chat"
    response = requests.get(url)
    chats = response.json()
    st.table(chats)

def history():
    room_id = st.session_state["room_id"]
    url = f"{os.environ['MANAGER_SERVER_URL']}/chat/{room_id}"
    response = requests.get(url)
    messages = response.json()["messages"]
    return messages

def chat():
    room_id = st.session_state["room_id"]
    input = st.session_state["input"]
    if not input: return
    url = f"{os.environ['MANAGER_SERVER_URL']}/chat/{room_id}"
    text = input.text
    file_url = None
    file_type = None
    if input["files"] and input["files"][0]:
        file_bytes = input["files"][0].getvalue()
        file_type = input["files"][0].type
        file_url = upload_supabase(file_bytes, file_type)
        if file_type == "application/pdf":
            add_tools(file_url, "pdf")
            text = f"{input.text}. (Uploaded PDF)"
        elif file_type in ["image/jpeg", "image/png"]:
            text = f"{input.text}. Uploaded Image URL: {file_url}"
    headers = { "Content-Type": "application/json" }
    data = { "text": text, "file_url": file_url, "file_type": file_type }
    response = requests.post(url, json=data, headers=headers)
    content = response.json()
    return content

def add_tools(tool_url: str, tool_type: str):
    if not tool_url: return
    url = f"{os.environ['MANAGER_SERVER_URL']}/tools"
    headers = { "Content-Type": "application/json" }
    data = { "tool_url": tool_url, "tool_type": tool_type }
    response = requests.post(url, json=data, headers=headers)
    content = response.json()
    return content

def main():
    st.set_page_config(page_title="AI Agent", page_icon="random")
    st.title("AI Agent")
    with st.sidebar:
        st.text_input("Room ID", key="room_id")
        st.text_input("MCP URL", key="mcp_url", on_change=lambda: add_tools(st.session_state["mcp_url"], "mcp"))
        with st.expander("Rooms"):
            chats()
    if not st.session_state["room_id"]:
        st.info("Enter Room ID")
        st.stop()
    st.chat_input("Ask anything", accept_file=True, file_type=["jpg", "jpeg", "png", "pdf"], key="input", on_submit=chat)
    messages = history()
    for message in messages:
        if message["type"] in ["human", "ai"] and message["content"]:
            if isinstance(message["content"], str):
                st.chat_message(message["type"]).write(message["content"])
            else:
                msg = st.chat_message(message["type"])
                msg.write(message["content"][0]["text"])
                msg.image(message["content"][1]["image_url"]["url"], use_container_width=True)
        else:
            msg = st.chat_message(message["type"])
            expander = msg.expander("Reasoning...")
            expander.write(message)

if __name__ == "__main__":
    main()
