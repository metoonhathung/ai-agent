# AI Agent

Technologies: Streamlit, FastAPI, LangGraph, MCP, A2A, ADK

## Run locally

```
pipenv install
pipenv shell
streamlit run web.py --server.address=0.0.0.0 --server.port=8501
uvicorn manager_server:app --reload --host 0.0.0.0 --port 80
python3 worker_server.py --host 0.0.0.0 --port 10000
python3 mcp_server.py --host 0.0.0.0 --port 8000
```
