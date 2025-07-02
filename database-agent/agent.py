import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

load_dotenv()

PATH_TO_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "C:/Users/duryo/OneDrive/Desktop/Coding/MCP-Learning/4-Rough/Server-Code/select-insert-integration/working-code-2/server.py")

mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[PATH_TO_SERVER],
            env={}
        )
    )    
)

# root_agent = Agent(
#     name="weather_time_agent",
#     model=LiteLlm(
#         model="openai/mock-model",
#         api_base="http://localhost:8001/v1",
#         api_key="mock-key"
#     ),
#     description="Agent to answer questions about movie database.",
#     instruction="You are a helpful agent who can answer user questions about postgres movie database. Use appropriate tools to answer user queries.",
#     tools=[mcp_toolset],
# )

root_agent = Agent(
    name="movie_database_agent",
    model=LiteLlm(
        model="gemini/gemini-2.0-flash",
        api_key=os.getenv("GOOGLE_API_KEY")
    ),
    description="Agent to answer questions about movie database.",
    instruction="You are a helpful agent who can answer user questions about postgres movie database. Use appropriate tools to answer user queries.",
    tools=[mcp_toolset],
)