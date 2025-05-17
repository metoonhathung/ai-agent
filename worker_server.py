import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from typing_extensions import override
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_task, new_text_artifact

import click
from dotenv import load_dotenv
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

load_dotenv()

"""
WORKER AGENT
"""

MCP_URL = "http://localhost:8000/mcp"
checkpointer = InMemorySaver()

def get_mcp_tools() -> list:
    client = MultiServerMCPClient(
        {
            "search": {
                # "command": "python",
                # "args": ["mcp_server.py"],
                # "transport": "stdio",
                "url": MCP_URL,
                "transport": "streamable_http",
            }
        }
    )

    return asyncio.run(client.get_tools())

class WorkerAgent:
    SYSTEM_INSTRUCTION = "You are a world class web searcher assistant."

    def __init__(self):
        self.tools = get_mcp_tools()
        self.model = ChatOpenAI(model="gpt-4o")
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=checkpointer,
            prompt=self.SYSTEM_INSTRUCTION,
        )

    async def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        response = await self.graph.ainvoke({"messages": [("user", query)]}, config)
        return {
            "is_task_complete": True,
            "require_user_input": False,
            "content": response["messages"][-1].content,
        }
    
"""
WORKER AGENT EXECUTOR
"""

class WorkerAgentExecutor(AgentExecutor):
    """Worker AgentExecutor Example."""

    def __init__(self):
        self.agent = WorkerAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        event = await self.agent.invoke(query, task.contextId)
        if event['is_task_complete']:
            event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    contextId=task.contextId,
                    taskId=task.id,
                    lastChunk=True,
                    artifact=new_text_artifact(
                        name='current_result',
                        description='Result of request to agent.',
                        text=event['content'],
                    ),
                )
            )
            event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.completed),
                    final=True,
                    contextId=task.contextId,
                    taskId=task.id,
                )
            )

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')


"""
WORKER SERVER
"""

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host: str, port: int):
    request_handler = DefaultRequestHandler(
        agent_executor=WorkerAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )
    import uvicorn
    uvicorn.run(server.build(), host=host, port=port)

def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Worker Agent."""
    capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
    skill = AgentSkill(
        id='search_online',
        name='Search Online Tool',
        description='Search DuckDuckGo for a query',
        tags=['search', 'online'],
        examples=['What are the latest news today?'],
    )
    return AgentCard(
        name='Worker Agent',
        description='Helper agent for searching online',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text', 'text/plain'],
        defaultOutputModes=['text', 'text/plain'],
        capabilities=capabilities,
        skills=[skill],
        authentication=AgentAuthentication(schemes=['public']),
    )

if __name__ == '__main__':
    main()
