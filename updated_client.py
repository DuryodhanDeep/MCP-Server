import asyncio
import logging
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools, McpWorkbench
from autogen_core import CancellationToken

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_improved_agent(model_client, tools_or_workbench, use_workbench=False):
    """Create an improved database agent with better response flow."""
    
    # Enhanced system message for more natural responses
    system_message = """You are an expert PostgreSQL database assistant for a movie database. Your primary goal is to answer user questions completely and naturally and execute user instructions.

CRITICAL INSTRUCTIONS:
1. ALWAYS provide a final answer to the user's question - never stop after just using tools
2. Use tools to gather data, then IMMEDIATELY provide a comprehensive response
3. When you use a tool, continue the conversation by analyzing and presenting the results
4. Think of yourself as having a conversation with the user - tools are just your way of looking up information
5. After getting data from tools, always synthesize it into a natural, helpful response

WORKFLOW FOR EVERY QUERY:
1. Use necessary tools to get information
2. Analyze the tool results
3. Provide a complete, conversational answer to the user
4. Never end your response with just tool calls - always follow up with analysis and conclusions

Example flow:
- Tool call: get movie data
- Immediate follow-up: "Based on the database query, here's what I found about the movie..."

REMEMBER: Your job is not done until you've given the user a complete, helpful answer to their question."""

    if use_workbench:
        agent = AssistantAgent(
            name="enhanced_postgres_agent",
            model_client=model_client,
            workbench=tools_or_workbench,
            system_message=system_message,
            # Key improvements for better flow - try enabling reflection with clear guidance
            reflect_on_tool_use=True,  # Enable reflection but with better system instructions
            model_client_stream=False,  # More coherent responses
        )
    else:
        agent = AssistantAgent(
            name="enhanced_postgres_agent", 
            model_client=model_client,
            tools=tools_or_workbench,
            system_message=system_message,
            # Key improvements for better flow - try enabling reflection with clear guidance
            reflect_on_tool_use=True,  # Enable reflection but with better system instructions
            model_client_stream=False,  # More coherent responses
        )
    
    return agent

async def enhanced_main():
    """Improved main function with better response handling."""
    
    # Configure the model with better parameters
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key="AIzaSyBD1yF5WhT5xa3Yeqlg4WCjkmsjmrEAf_c",
        # Additional parameters for better responses
        temperature=0.3,  # More consistent responses
        max_tokens=2000,  # Allow longer responses
    )
    
    # Setup MCP server parameters
    postgres_mcp_server = StdioServerParams(
        command="python",
        args=["postgres_server.py"],
        read_timeout_seconds=45,  # Increased timeout
        write_timeout_seconds=10
    )
    
    try:
        # Get tools from MCP server
        tools = await mcp_server_tools(postgres_mcp_server)
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
        
        # Create enhanced agent
        database_agent = await create_improved_agent(model_client, tools, use_workbench=False)
        
        # Welcome message
        print("🎬 Enhanced PostgreSQL Movie Database Assistant")
        print("=" * 60)
        print("I can help you with queries about movies, actors, directors, and more!")
        print("Examples:")
        print("  • 'Show me all movies by Christopher Nolan'")
        print("  • 'What are the highest rated movies from 2020?'")
        print("  • 'Tell me about the movie Inception'")
        print("  • 'List all actors in The Dark Knight'")
        print("\nType 'quit', 'exit', or 'q' to stop.")
        print("=" * 60)
        
        while True:
            try:
                # Get user input with better prompt
                user_query = input("\n🎭 Your question: ").strip()
                
                # Check for exit commands
                if user_query.lower() in ['quit', 'exit', 'q', 'bye']:
                    print("\n👋 Thanks for using the Movie Database Assistant! Goodbye!")
                    break
                
                if not user_query:
                    print("Please enter a question about the movie database.")
                    continue
                
                print(f"\n🔍 Processing your query...")
                print("-" * 40)
                
                # Enhanced task with more explicit instructions
                enhanced_task = f"""
                USER REQUEST: {user_query}"""
                
                # Run the agent with enhanced error handling
                try:
                    await Console(
                        database_agent.run_stream(
                            task=enhanced_task,
                            cancellation_token=CancellationToken()
                        )
                    )
                except asyncio.TimeoutError:
                    print("⚠️  The query took too long to process. Please try a simpler query.")
                except Exception as query_error:
                    print(f"❌ Error processing query: {str(query_error)}")
                    print("Please try rephrasing your question or check if the database is accessible.")
                
                print("\n" + "=" * 60)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Operation cancelled by user.")
                break
            except EOFError:
                print("\n\n👋 Session ended. Goodbye!")
                break
    
    except Exception as e:
        logger.error(f"Failed to initialize the database agent: {str(e)}")
        print(f"❌ Initialization failed: {str(e)}")
        print("Please ensure:")
        print("  • postgres_server.py is in the correct path")
        print("  • Your PostgreSQL database is running")
        print("  • MCP server dependencies are installed")
    
    finally:
        try:
            await model_client.close()
        except:
            pass

async def enhanced_workbench_main():
    """Enhanced workbench implementation with better connection management."""
    
    # Configure model
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key="AIzaSyBD1yF5WhT5xa3Yeqlg4WCjkmsjmrEAf_c",
        temperature=0.3,
        max_tokens=2000,
    )
    
    # Setup server parameters
    postgres_server_params = StdioServerParams(
        command="python",
        args=["postgres_server.py"],
        read_timeout_seconds=45,
        write_timeout_seconds=10
    )
    
    try:
        # Use McpWorkbench for managed connection
        async with McpWorkbench(postgres_server_params) as workbench:
            
            # Create enhanced agent with workbench
            database_agent = await create_improved_agent(model_client, workbench, use_workbench=True)
            
            # Welcome message
            print("🎬 Enhanced Movie Database Assistant (Workbench Mode)")
            print("=" * 60)
            print("Advanced connection management for better reliability!")
            print("Ask me anything about movies, actors, directors, or genres.")
            print("\nType 'quit' to exit.")
            print("=" * 60)
            
            while True:
                try:
                    user_query = input("\n🎭 Your question: ").strip()
                    
                    if user_query.lower() in ['quit', 'exit', 'q', 'bye']:
                        print("\n👋 Thanks for using the assistant! Goodbye!")
                        break
                    
                    if user_query:
                        print(f"\n🔍 Analyzing your request...")
                        print("-" * 40)
                        
                        # More direct and focused task instruction
                        enhanced_task = f"""
                        USER QUESTION: {user_query}"""
                        
                        try:
                            await Console(
                                database_agent.run_stream(
                                    task=enhanced_task,
                                    cancellation_token=CancellationToken()
                                )
                            )
                        except Exception as query_error:
                            print(f"❌ Query error: {str(query_error)}")
                            print("Please try rephrasing your question.")
                        
                        print("\n" + "=" * 60)
                
                except KeyboardInterrupt:
                    print("\n\n⚠️  Interrupted by user.")
                    break
                except EOFError:
                    break
    
    except Exception as e:
        logger.error(f"Workbench error: {str(e)}")
        print(f"❌ Error: {str(e)}")
    
    finally:
        try:
            await model_client.close()
        except:
            pass

def display_menu():
    """Display implementation choice menu."""
    print("\n🎬 Movie Database Assistant Setup")
    print("=" * 40)
    print("Choose your preferred implementation:")
    print()
    print("1️⃣  Standard MCP Tools")
    print("   • Direct tool integration")
    print("   • Good for simple queries")
    print()
    print("2️⃣  McpWorkbench (Recommended)")
    print("   • Better connection management")
    print("   • More reliable for complex operations")
    print("   • Automatic connection recovery")
    print()
    print("=" * 40)

if __name__ == "__main__":
    display_menu()
    
    while True:
        try:
            choice = input("Enter your choice (1 or 2): ").strip()
            
            if choice == "1":
                print("\n🚀 Starting Standard MCP Implementation...")
                asyncio.run(enhanced_main())
                break
            elif choice == "2":
                print("\n🚀 Starting McpWorkbench Implementation...")
                asyncio.run(enhanced_workbench_main())
                break
            else:
                print("Please enter 1 or 2")
                continue
                
        except KeyboardInterrupt:
            print("\n\n👋 Setup cancelled. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Setup error: {str(e)}")
            break
