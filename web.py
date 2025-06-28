import streamlit as st
import requests
import json
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
API_URL = "http://localhost"

def history():
    room_id = st.session_state["room_id"]
    url = f"{API_URL}/chat/{room_id}"
    response = requests.get(url)
    messages = response.json()["messages"]
    return messages

def chat():
    room_id = st.session_state["room_id"]
    text = st.session_state["text"]
    if not text: return
    url = f"{API_URL}/chat/{room_id}"
    headers = { "Content-Type": "application/json" }
    data = { "room_id": room_id, "text": text }
    response = requests.post(url, json=data, headers=headers)
    content = response.json()
    return content

def main():
    st.title("AI Agent")
    with st.sidebar:
        st.text_input("Room ID", key="room_id")
    if not st.session_state["room_id"]:
        st.info("Enter Room ID")
        st.stop()
    st.chat_input("Ask anything", key="text", on_submit=chat)
    messages = history()
    for message in messages:
        if message["type"] in ["human", "ai"] and message["content"]:
            st.chat_message(message["type"]).write(message["content"])

if __name__ == "__main__":
    main()
