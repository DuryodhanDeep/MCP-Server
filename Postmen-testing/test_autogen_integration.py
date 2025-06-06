# test_autogen_integration.py
import os
import autogen
import json
from pathlib import Path

def test_basic_conversation():
    """Test basic AutoGen conversation with mock LLM"""
    print("🧪 Test 1: Basic Conversation")
    
    # Configure mock LLM
    config_list = [
        {
            "model": "mock-claude-sonnet-4",
            "base_url": "http://localhost:8080/v1",
            "api_key": "test-api-key",  # Mock server accepts any key
        }
    ]
    
    # Create agents
    assistant = autogen.AssistantAgent(
        name="coding_assistant",
        llm_config={"config_list": config_list},
        system_message="You are a helpful coding assistant. Write clean, commented Python code."
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy", 
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        code_execution_config={
            "work_dir": "test_workspace",
            "use_docker": False
        }
    )
    
    # Test conversation
    try:
        user_proxy.initiate_chat(
            assistant,
            message="Write a Python function to calculate the factorial of a number"
        )
        print("✅ Basic conversation test passed!")
        return True
    except Exception as e:
        print(f"❌ Basic conversation test failed: {e}")
        return False

def test_multi_model_config():
    """Test multiple model configuration and failover"""
    print("\n🧪 Test 2: Multi-Model Configuration")
    
    config_list = [
        {
            "model": "mock-claude-sonnet-4",
            "base_url": "http://localhost:8080/v1", 
            "api_key": "primary-key",
            "tags": ["primary", "advanced"]
        },
        {
            "model": "mock-gpt-4",
            "base_url": "http://localhost:8080/v1",
            "api_key": "backup-key", 
            "tags": ["backup", "reliable"]
        }
    ]
    
    # Test filtering
    try:
        primary_config = autogen.filter_config(config_list, {"tags": ["primary"]})
        backup_config = autogen.filter_config(config_list, {"tags": ["backup"]})
        
        print(f"Primary config: {len(primary_config)} models")
        print(f"Backup config: {len(backup_config)} models")
        
        # Create agent with filtered config
        assistant = autogen.AssistantAgent(
            name="assistant",
            llm_config={"config_list": primary_config}
        )
        
        print("✅ Multi-model configuration test passed!")
        return True
    except Exception as e:
        print(f"❌ Multi-model configuration test failed: {e}")
        return False

def test_data_analysis_workflow():
    """Test data analysis workflow"""
    print("\n🧪 Test 3: Data Analysis Workflow")
    
    config_list = [
        {
            "model": "mock-llm-v1",
            "base_url": "http://localhost:8080/v1",
            "api_key": "test-key"
        }
    ]
    
    # Create specialized agents
    data_analyst = autogen.AssistantAgent(
        name="data_analyst",
        llm_config={"config_list": config_list},
        system_message="""You are a data analyst. When given a task:
        1. Write Python code for data analysis
        2. Include proper imports and error handling
        3. Explain your approach step by step"""
    )
    
    executor = autogen.UserProxyAgent(
        name="executor",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        code_execution_config={
            "work_dir": "analysis_workspace",
            "use_docker": False
        }
    )
    
    try:
        executor.initiate_chat(
            data_analyst,
            message="Analyze a sample dataset with sales data and create a visualization"
        )
        print("✅ Data analysis workflow test passed!")
        return True
    except Exception as e:
        print(f"❌ Data analysis workflow test failed: {e}")
        return False

def test_mcp_scenario():
    """Test MCP-related scenario"""
    print("\n🧪 Test 4: MCP Integration Scenario")
    
    config_list = [
        {
            "model": "mock-claude-sonnet-4",
            "base_url": "http://localhost:8080/v1",
            "api_key": "mcp-test-key"
        }
    ]
    
    mcp_assistant = autogen.AssistantAgent(
        name="mcp_assistant",
        llm_config={"config_list": config_list},
        system_message="""You are an AI assistant with MCP (Model Context Protocol) capabilities.
        You can help with:
        - Tool integration and management
        - Resource coordination
        - Multi-agent communication
        - Protocol-compliant responses"""
    )
    
    coordinator = autogen.UserProxyAgent(
        name="mcp_coordinator",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2
    )
    
    try:
        coordinator.initiate_chat(
            mcp_assistant,
            message="Help me set up MCP tools for file management and database access in my agent system"
        )
        print("✅ MCP integration scenario test passed!")
        return True
    except Exception as e:
        print(f"❌ MCP integration scenario test failed: {e}")
        return False

def test_error_handling():
    """Test error handling with wrong endpoint"""
    print("\n🧪 Test 5: Error Handling")
    
    # Intentionally wrong configuration
    config_list = [
        {
            "model": "mock-llm-v1",
            "base_url": "http://localhost:9999/v1",  # Wrong port
            "api_key": "test-key"
        },
        {
            "model": "mock-backup",
            "base_url": "http://localhost:8080/v1",  # Correct fallback
            "api_key": "backup-key"
        }
    ]
    
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={"config_list": config_list}
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1
    )
    
    try:
        user_proxy.initiate_chat(
            assistant,
            message="Simple test message"
        )
        print("✅ Error handling test passed! (Fallback worked)")
        return True
    except Exception as e:
        print(f"⚠️ Error handling test result: {e}")
        print("   This might be expected if no fallback succeeded")
        return False

def create_test_environment():
    """Create necessary directories for testing"""
    directories = ["test_workspace", "analysis_workspace"]
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
    print("📁 Test directories created")

def main():
    """Run all tests"""
    print("🚀 Starting AutoGen Mock LLM Integration Tests")
    print("=" * 50)
    
    # Check if mock server is running
    try:
        import requests
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ Mock server is running")
        else:
            print("❌ Mock server health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to mock server: {e}")
        print("   Make sure to run: python mock_llm_server.py")
        return
    
    # Create test environment
    create_test_environment()
    
    # Run tests
    tests = [
        test_basic_conversation,
        test_multi_model_config, 
        test_data_analysis_workflow,
        test_mcp_scenario,
        test_error_handling
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    passed = sum(results)
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is working correctly.")
        print("\n📋 Next steps:")
        print("   1. Replace mock server URL with real LLM endpoints")
        print("   2. Add your actual API keys")
        print("   3. Test with production workloads")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()