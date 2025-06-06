# Complete Mock LLM Server Testing Setup

## Prerequisites Installation

```bash
# Install required packages
pip install flask flask-cors autogen-agentchat

# Or create requirements.txt
echo "flask==2.3.3
flask-cors==4.0.0
autogen-agentchat==0.2.30" > requirements.txt

pip install -r requirements.txt
```

## Step 1: Run the Mock Server

1. **Save the mock server code** as `mock_llm_server.py`

2. **Start the server:**
```bash
python mock_llm_server.py
```

3. **Verify server is running:**
   - Open browser: `http://localhost:8080`
   - Should see server info JSON

## Step 2: Postman Testing

### Test 1: Basic Chat Completion

**Request Setup:**
- **Method:** POST
- **URL:** `http://localhost:8080/v1/chat/completions`
- **Headers:**
  ```
  Content-Type: application/json
  Authorization: Bearer test-api-key
  ```
- **Body (JSON):**
```json
{
  "model": "mock-llm-v1",
  "messages": [
    {
      "role": "user", 
      "content": "Write a Python function to calculate fibonacci numbers"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Expected Response:**
- Status: 200 OK
- Body: OpenAI-format response with Python code

### Test 2: Data Analysis Request

**Body (JSON):**
```json
{
  "model": "mock-claude-sonnet-4",
  "messages": [
    {
      "role": "user",
      "content": "Analyze this CSV dataset and create visualizations"
    }
  ]
}
```

### Test 3: MCP-Related Query

**Body (JSON):**
```json
{
  "model": "mock-gpt-4", 
  "messages": [
    {
      "role": "system",
      "content": "You are an AI assistant with MCP protocol capabilities"
    },
    {
      "role": "user",
      "content": "Help me integrate MCP with AutoGen agents"
    }
  ]
}
```

### Test 4: List Models

**Request:**
- **Method:** GET
- **URL:** `http://localhost:8080/v1/models`

## Step 3: AutoGen Integration Test

Create this test script:

```python
# test_autogen_integration.py
import os
import autogen

# Configure mock LLM
config_list = [
    {
        "model": "mock-claude-sonnet-4",
        "base_url": "http://localhost:8080/v1",
        "api_key": "test-key",  # Mock server accepts any key
    }
]

# Create agents
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list},
    system_message="You are a helpful AI assistant that can write code and analyze data."
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config={
        "work_dir": "test_workspace",
        "use_docker": False
    }
)

# Test conversation
if __name__ == "__main__":
    print("🧪 Testing AutoGen with Mock LLM Server...")
    
    user_proxy.initiate_chat(
        assistant,
        message="Write a Python script to analyze a simple dataset and create a basic visualization"
    )
    
    print("\n✅ Test completed!")
```

## Step 4: Advanced Testing Scenarios

### Scenario 1: Multi-Model Failover

```python
# test_failover.py
config_list = [
    {
        "model": "mock-claude-sonnet-4",
        "base_url": "http://localhost:8080/v1",
        "api_key": "test-key",
    },
    {
        "model": "mock-gpt-4", 
        "base_url": "http://localhost:8080/v1",
        "api_key": "backup-key",
    }
]

# AutoGen will try first model, then fallback to second
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list}
)
```

### Scenario 2: Error Handling Test

Stop the mock server and test how AutoGen handles connection errors.

### Scenario 3: Rate Limiting Test

Modify mock server to simulate rate limiting:

```python
# Add to mock_llm_server.py
import time
from datetime import datetime, timedelta

# Simple rate limiting
last_request_time = {}

@app.before_request
def rate_limit():
    client_ip = request.remote_addr
    now = datetime.now()
    
    if client_ip in last_request_time:
        if now - last_request_time[client_ip] < timedelta(seconds=1):
            return jsonify({
                'error': {
                    'message': 'Rate limit exceeded',
                    'type': 'rate_limit_error'
                }
            }), 429
    
    last_request_time[client_ip] = now
```

## Troubleshooting Guide

### Common Issues:

1. **Server won't start:**
   - Check if port 8080 is available
   - Try different port: `app.run(port=8081)`

2. **Postman connection refused:**
   - Verify server is running
   - Check firewall settings
   - Try `127.0.0.1` instead of `localhost`

3. **AutoGen connection errors:**
   - Verify `base_url` ends with `/v1`
   - Check API key format (can be anything for mock)
   - Enable debug logging in AutoGen

4. **Response format issues:**
   - Compare mock response with real OpenAI API
   - Check JSON structure matches exactly
   - Verify all required fields are present

### Debug Commands:

```bash
# Test server connectivity
curl http://localhost:8080/health

# Test chat endpoint
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-llm-v1","messages":[{"role":"user","content":"Hello"}]}'
```

## Validation Checklist

✅ Mock server starts without errors  
✅ Postman can connect to all endpoints  
✅ Chat completion returns valid OpenAI format  
✅ Models endpoint lists available models  
✅ AutoGen successfully connects and gets responses  
✅ Error handling works properly  
✅ Multiple models/failover works  

Once all tests pass, you can replace the mock server URL with any real OpenAI-compatible endpoint!