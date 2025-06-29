from crewai import LLM, Agent, Crew, Task
from crewai.process import Process
from crewai_tools import MCPServerAdapter

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
CREATOR AGENT
"""

CREATOR_MCP_URL = "http://localhost:8001/mcp"
CREATOR_SERVER_URL = "http://localhost:10001"

class CreatorAgent:
    def __init__(self):
        server_params = {
            "url": CREATOR_MCP_URL,
            "transport": "streamable-http"
        }
        self.model = LLM(model="gpt-4o")
        self.tools = MCPServerAdapter(server_params).tools
        self.agent = Agent(
            role="Creator Agent",
            goal="Use tool create_image to create an image from a query.",
            backstory="You are a world class image creator.",
            tools=self.tools,
            llm=self.model,
        )

        self.task = Task(
            description="Create image about '{user_prompt}'", 
            agent=self.agent, 
            expected_output="Image about '{user_prompt}'",
        )

        self.crew = Crew(
            agents=[self.agent],
            tasks=[self.task],
            process=Process.sequential,
        )

    async def invoke(self, query, session_id) -> str:
        inputs = {
            'user_prompt': query,
        }
        response = await self.crew.kickoff_async(inputs)
        return {
            "is_task_complete": True,
            "require_user_input": False,
            "content": response.raw,
        }
    
"""
CREATOR AGENT EXECUTOR
"""

class CreatorAgentExecutor(AgentExecutor):
    """Creator AgentExecutor Example."""

    def __init__(self):
        self.agent = CreatorAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        event = await self.agent.invoke(query, context.context_id)
        print(f"Request: {query}, Response: {event['content']}")
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
CREATOR SERVER
"""

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10000)
def main(host: str, port: int):
    request_handler = DefaultRequestHandler(
        agent_executor=CreatorAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AFastAPIApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )
    import uvicorn
    uvicorn.run(server.build(), host=host, port=port)

def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Creator Agent."""
    capabilities = AgentCapabilities(streaming=False, pushNotifications=False)
    skill = AgentSkill(
        id='create_image',
        name='Create Image Tool',
        description='create image from a query',
        tags=['create', 'image'],
        examples=['Create an image of a dog.'],
    )
    return AgentCard(
        name='Creator Agent',
        description='Helper agent for creating images',
        url=CREATOR_SERVER_URL,
        version='1.0.0',
        defaultInputModes=['text', 'text/plain'],
        defaultOutputModes=['text', 'text/plain'],
        capabilities=capabilities,
        skills=[skill],
    )

if __name__ == '__main__':
    main()
