import streamlit as st
import requests
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())
host = "http://localhost"

def history():
    room_id = st.session_state["room_id"]
    url = f"{host}/chat/{room_id}"
    response = requests.get(url)
    messages = response.json()["messages"]
    return messages

def chat():
    room_id = st.session_state["room_id"]
    text = st.session_state["text"]
    if not text: return
    url = f"{host}/chat/{room_id}"
    headers = { "Content-Type": "application/json" }
    data = { "room_id": room_id, "text": text }
    response = requests.post(url, json=data, headers=headers)
    content = response.json()["messages"][-1]["content"]
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
        st.chat_message(message["type"]).write(message["content"])

if __name__ == "__main__":
    main()
