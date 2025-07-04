import asyncio
import os
import sys
import logging
import json
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

def print_event_details(event):
    """Print complete event details"""
    print(f"\n📋 EVENT DETAILS:")
    print(f"   Author: {event.author}")
    print(f"   ID: {event.id}")
    print(f"   Invocation ID: {event.invocation_id}")
    print(f"   Timestamp: {event.timestamp}")
    print(f"   Partial: {event.partial}")
    print(f"   Is Final Response: {event.is_final_response()}")
    
    # Content details
    if event.content:
        print(f"   Content Role: {event.content.role}")
        if event.content.parts:
            for i, part in enumerate(event.content.parts):
                print(f"   Part {i+1}:")
                if hasattr(part, 'text') and part.text:
                    print(f"     Text: {part.text}")
                if hasattr(part, 'function_call') and part.function_call:
                    print(f"     Function Call: {part.function_call}")
                if hasattr(part, 'function_response') and part.function_response:
                    print(f"     Function Response: {part.function_response}")
    
    # Function calls
    function_calls = event.get_function_calls()
    if function_calls:
        print(f"   Function Calls: {len(function_calls)}")
        for i, call in enumerate(function_calls):
            print(f"     Call {i+1}: {call.name} - {call.args}")
    
    # Function responses
    function_responses = event.get_function_responses()
    if function_responses:
        print(f"   Function Responses: {len(function_responses)}")
        for i, response in enumerate(function_responses):
            print(f"     Response {i+1}: {response.name} - {response.response}")
    
    # Actions
    if event.actions:
        print(f"   Actions:")
        if event.actions.state_delta:
            print(f"     State Delta: {event.actions.state_delta}")
        if event.actions.artifact_delta:
            print(f"     Artifact Delta: {event.actions.artifact_delta}")
        if hasattr(event.actions, 'transfer_to_agent') and event.actions.transfer_to_agent:
            print(f"     Transfer to Agent: {event.actions.transfer_to_agent}")
        if hasattr(event.actions, 'escalate') and event.actions.escalate:
            print(f"     Escalate: {event.actions.escalate}")
        if hasattr(event.actions, 'skip_summarization') and event.actions.skip_summarization:
            print(f"     Skip Summarization: {event.actions.skip_summarization}")
    
    # Error details
    if hasattr(event, 'error_code') and event.error_code:
        print(f"   Error Code: {event.error_code}")
    if hasattr(event, 'error_message') and event.error_message:
        print(f"   Error Message: {event.error_message}")
    
    print("-" * 80)

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
                name="movie_database_agent",
                model=LiteLlm(
                    model="gemini/gemini-2.0-flash",
                    api_key=os.getenv("GOOGLE_API_KEY")
                ),
                description="Agent to answer questions about movie database.",
                instruction="You are a helpful agent who can answer user questions about postgres movie database. Use appropriate tools to answer user queries.",
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
        """Execute a query and print all events"""
        if not self.setup_complete:
            print("❌ Setup not complete. Run setup() first.")
            return None
            
        print(f"\n🔍 QUERY: {query_text}")
        print("=" * 80)
        
        user_content = types.Content(role='user', parts=[types.Part(text=query_text)])
        
        try:
            final_response = None
            event_count = 0
            
            async for event in self.runner.run_async(
                user_id="test_user", 
                session_id="test_session", 
                new_message=user_content
            ):
                event_count += 1
                print(f"\n🎯 EVENT #{event_count}:")
                print_event_details(event)
                
                # Store final response
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
            
            print(f"\n🎬 FINAL RESPONSE:")
            print(f"   {final_response}")
            print("=" * 80)
            
            return final_response
                
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
