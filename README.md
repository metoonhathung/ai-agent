# AI Agent

Web: http://localhost:8501

Manager: http://localhost:80

Worker: http://localhost:10000

MCP: http://localhost:8000

Technologies: Streamlit, FastAPI, LangGraph, MCP, A2A

## Run locally

```
pipenv install
pipenv shell
streamlit run main.py
uvicorn app:app --reload --host 0.0.0.0 --port 80
python3 worker_server.py
python3 mcp_server.py
```
