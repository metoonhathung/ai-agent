# AI Agent

Technologies: Streamlit, FastAPI, LangGraph, MCP, A2A

## Run locally

```
pipenv install
pipenv shell
streamlit run main.py
uvicorn app:app --reload --host 0.0.0.0 --port 80
python3 mcp_server.py
```
