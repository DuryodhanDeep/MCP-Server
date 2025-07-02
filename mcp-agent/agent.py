import os
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

load_dotenv()

PATH_TO_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "C:/Users/duryo/OneDrive/Desktop/Coding/MCP-Learning/5-google-adk/mcp-agent/weather_time_server.py")

mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[PATH_TO_SERVER],
            env={}
        )
    )    
)

root_agent = Agent(
    name="weather_time_agent",
    model=LiteLlm(
        model="openai/mock-model",
        api_base="http://localhost:8001/v1",
        api_key="mock-key"
    ),
    description="Agent to answer questions about the time and weather in a city.",
    instruction="You are a helpful agent who can answer user questions about the time and weather in a city.",
    tools=[mcp_toolset],
)

# root_agent = Agent(
#     name="weather_time_agent",
#     model=LiteLlm(
#         model="gemini/gemini-2.0-flash",  # LiteLLM format for Gemini
#         api_key=os.getenv("GOOGLE_API_KEY")  # Your Google API key
#     ),
#     description="Agent to answer questions about the time and weather in a city.",
#     instruction="You are a helpful agent who can answer user questions about the time and weather in a city.",
#     tools=[mcp_toolset],
# )