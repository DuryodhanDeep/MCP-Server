import asyncio
import os
import sys
import logging
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams, StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

# Suppress warnings
logging.getLogger().setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Configuration
SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                          "C:/Users/duryo/OneDrive/Desktop/Coding/MCP-Learning/4-Rough/Server-Code/select-insert-integration/working-code-2/server.py")

class MCPTester:
    def __init__(self):
        self.runner = None
        self.session_service = None
        self.setup_complete = False
        
    async def setup(self):
        """Setup agent and session"""
        try:
            print("🔧 Setting up MCP toolset...")
            
            # Create MCP toolset
            mcp_toolset = MCPToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="python",
                        args=[SERVER_PATH],
                        env={}
                    )
                )    
            )
            
            print("🤖 Creating agent with Gemini...")
            
            # Create agent
            root_agent = Agent(
                name="movie_database_agent_qwen",
                model=LiteLlm(
                    model="ollama_chat/qwen2:7b",
                ),
                description="Agent to answer questions about movie database.",
                instruction="You are a helpful agent who can answer user questions about postgres movie database. Use appropriate tools to answer user queries. Be concise and helpful.",
                tools=[mcp_toolset],
            )
            
            print("📝 Setting up session...")
            
            # Setup session
            self.session_service = InMemorySessionService()
            await self.session_service.create_session(
                app_name="movie_db_test", 
                user_id="test_user", 
                session_id="test_session"
            )
            
            # Create runner
            self.runner = Runner(
                agent=root_agent, 
                app_name="movie_db_test", 
                session_service=self.session_service
            )
            
            self.setup_complete = True
            print("✅ Setup complete!")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def query(self, query_text: str):
        """Execute a query"""
        if not self.setup_complete:
            print("❌ Setup not complete. Run setup() first.")
            return None
            
        print(f"\n🔍 Query: {query_text}")
        print("-" * 50)
        
        user_content = types.Content(role='user', parts=[types.Part(text=query_text)])
        
        try:
            async for event in self.runner.run_async(
                user_id="test_user", 
                session_id="test_session", 
                new_message=user_content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    response = event.content.parts[0].text
                    print(f"🤖 Response: {response}")
                    print("-" * 50)
                    return response
            
            print("❌ No response received")
            return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    async def interactive_mode(self):
        """Interactive testing mode"""
        print("\n🎬 Movie Database Interactive Test")
        print("=" * 50)
        print("Type 'quit' or 'q' to exit")
        print("Example queries:")
        print("- What tools do you have?")
        print("- Show me all movies")
        print("- List all directors")
        print("=" * 50)
        
        while True:
            try:
                query_input = input("\n💬 Your query: ").strip()
                
                if query_input.lower() in ['quit', 'q', 'exit']:
                    break
                    
                if query_input:
                    await self.query(query_input)
                
            except (KeyboardInterrupt, EOFError):
                break
        
        print("\n👋 Goodbye!")

async def main():
    """Main function"""
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not found!")
        print("Please set your Google API key in your .env file:")
        print("GOOGLE_API_KEY=your_api_key_here")
        return
    
    tester = MCPTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed. Exiting.")
            return
        
        # Run interactive mode
        await tester.interactive_mode()
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
