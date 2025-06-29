from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StreamableHTTPConnectionParams,
)

from typing_extensions import override
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_text_artifact, completed_task

import click
from dotenv import load_dotenv, find_dotenv
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

_ = load_dotenv(find_dotenv())

"""
RESEARCHER AGENT
"""

RESEARCHER_MCP_URL = "http://localhost:8000/mcp"
RESEARCHER_SERVER_URL = "http://localhost:10000"

class ResearcherAgent:
    def __init__(self):
        self.agent = LlmAgent(
            model=LiteLlm(model="openai/gpt-4o"),
            name="researcher_agent",
            description="You are a world class web researcher.",
            instruction="""Use tool search_online to search the web for information.""",
            tools=[MCPToolset(connection_params=StreamableHTTPConnectionParams(url=RESEARCHER_MCP_URL))],
        )
        self.runner = Runner(
            app_name="researcher_agent",
            agent=self.agent,
            session_service=InMemorySessionService(),
        )

    async def invoke(self, query, session_id) -> str:
        session = await self.runner.session_service.get_session(app_name="researcher_agent", user_id="self", session_id=session_id)
        if session is None:
            session = await self.runner.session_service.create_session(app_name="researcher_agent", user_id="self", session_id=session_id)
        content = types.Content(role='user', parts=[types.Part(text=query)])
        final_response_text = "Agent did not produce a final response."
        async for event in self.runner.run_async(user_id="self", session_id=session_id, new_message=content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break
        print(f"Request: {query}, Response: {final_response_text}")
        return {
            "is_task_complete": True,
            "require_user_input": False,
            "content": final_response_text,
        }
    
"""
RESEARCHER AGENT EXECUTOR
"""

class ResearcherAgentExecutor(AgentExecutor):
    """Researcher AgentExecutor Example."""

    def __init__(self):
        self.agent = ResearcherAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        event = await self.agent.invoke(query, context.context_id)
        await event_queue.enqueue_event(
            completed_task(
                context.task_id,
                context.context_id,
                [new_text_artifact(name='current_result', description='Result of request to agent.', text=event['content'])],
                [context.message],
            )
        )

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')


"""
RESEARCHER SERVER
"""

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host: str, port: int):
    request_handler = DefaultRequestHandler(
        agent_executor=ResearcherAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AFastAPIApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )
    import uvicorn
    uvicorn.run(server.build(), host=host, port=port)

def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Researcher Agent."""
    capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
    skill = AgentSkill(
        id='search_online',
        name='Search Online Tool',
        description='Search DuckDuckGo for a query',
        tags=['search', 'online'],
        examples=['What are the latest news today?'],
    )
    return AgentCard(
        name='Researcher Agent',
        description='Helper agent for searching online',
        url=RESEARCHER_SERVER_URL,
        version='1.0.0',
        defaultInputModes=['text', 'text/plain'],
        defaultOutputModes=['text', 'text/plain'],
        capabilities=capabilities,
        skills=[skill],
    )

if __name__ == '__main__':
    main()
