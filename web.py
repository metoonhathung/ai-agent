import streamlit as st
import requests
from dotenv import load_dotenv, find_dotenv
import os
from tools import upload_supabase

_ = load_dotenv(find_dotenv())

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
    image_url = None
    if input["files"] and input["files"][0]:
        file_bytes = input["files"][0].getvalue()
        image_url = upload_supabase(file_bytes, input["files"][0].type)
    headers = { "Content-Type": "application/json" }
    data = { "text": input.text, "image_url": image_url }
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
    st.chat_input("Ask anything", accept_file=True, file_type=["jpg", "jpeg", "png"], key="input", on_submit=chat)
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
