# mock_llm_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import json
import random

app = Flask(__name__)
CORS(app)

# Mock responses database
MOCK_RESPONSES = {
    'code': """Here's a Python solution:

```python
# Mock Python code for your request
import pandas as pd
import matplotlib.pyplot as plt

def analyze_data(filename):
    # Load data
    df = pd.read_csv(filename)
    
    # Basic analysis
    summary = df.describe()
    print("Data Summary:")
    print(summary)
    
    # Create visualization
    df.plot(kind='bar')
    plt.title('Data Analysis')
    plt.show()
    
    return summary

# Example usage
result = analyze_data('data.csv')
```

This code provides a basic data analysis framework. Would you like me to modify it for your specific needs?""",
    
    'analyze': """I'll help you analyze that data. Here's my systematic approach:

1. **Data Loading & Inspection**
   - Load the dataset
   - Check data types and structure
   - Identify missing values

2. **Data Cleaning**
   - Handle missing values
   - Remove duplicates
   - Fix data type issues

3. **Exploratory Analysis**
   - Statistical summaries
   - Distribution analysis
   - Correlation analysis

4. **Visualization**
   - Create charts and graphs
   - Identify patterns and trends

Would you like me to write the specific code for any of these steps?""",
    
    'mcp': """I understand you're working with MCP (Model Context Protocol). Here's how I can help:

**MCP Integration Capabilities:**
- Tool calling and function execution
- Resource management and access
- Multi-agent coordination
- Protocol-compliant communication

For your AutoGen + MCP setup, I can:
1. Generate MCP-compliant tool definitions
2. Handle resource requests and responses  
3. Coordinate between multiple agents
4. Manage conversation context

What specific MCP functionality would you like me to implement?""",
    
    'default': """I understand your request. As a mock LLM, I can assist with:

**Programming & Development:**
- Code generation and debugging
- API integration
- System architecture

**Data & Analysis:**
- Data processing and analysis
- Visualization and reporting
- Statistical analysis

**AI & Automation:**
- Agent coordination
- Workflow automation
- Multi-model integration

How can I help you with your specific task?"""
}

def generate_mock_response(messages, model):
    """Generate contextually appropriate mock responses"""
    if not messages:
        return MOCK_RESPONSES['default']
    
    last_message = messages[-1].get('content', '').lower()
    
    # Determine response type based on keywords
    if any(keyword in last_message for keyword in ['code', 'python', 'script', 'function']):
        return MOCK_RESPONSES['code']
    elif any(keyword in last_message for keyword in ['analyze', 'analysis', 'data', 'csv', 'dataset']):
        return MOCK_RESPONSES['analyze']
    elif any(keyword in last_message for keyword in ['mcp', 'protocol', 'agent', 'autogen']):
        return MOCK_RESPONSES['mcp']
    else:
        return MOCK_RESPONSES['default']

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI-compatible chat completions endpoint"""
    try:
        data = request.json
        print(f"\n=== INCOMING REQUEST ===")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {json.dumps(data, indent=2)}")
        
        # Extract request parameters
        messages = data.get('messages', [])
        model = data.get('model', 'mock-llm-v1')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1000)
        
        # Generate mock response
        mock_content = generate_mock_response(messages, model)
        
        # Calculate token usage (rough estimate)
        prompt_tokens = sum(len(msg.get('content', '')) for msg in messages) // 4
        completion_tokens = len(mock_content) // 4
        total_tokens = prompt_tokens + completion_tokens
        
        # Create OpenAI-compatible response
        response = {
            'id': f'chatcmpl-{int(time.time())}{random.randint(1000, 9999)}',
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': mock_content
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            }
        }
        
        print(f"\n=== OUTGOING RESPONSE ===")
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Simulate processing delay
        time.sleep(0.5)
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'error': {
                'message': f'Mock server error: {str(e)}',
                'type': 'mock_error',
                'code': 'internal_error'
            }
        }), 500

@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models endpoint"""
    response = {
        'object': 'list',
        'data': [
            {
                'id': 'mock-llm-v1',
                'object': 'model',
                'created': int(time.time()),
                'owned_by': 'mock-org',
                'permission': [],
                'root': 'mock-llm-v1'
            },
            {
                'id': 'mock-claude-sonnet-4',
                'object': 'model',
                'created': int(time.time()),
                'owned_by': 'mock-org',
                'permission': [],
                'root': 'mock-claude-sonnet-4'
            },
            {
                'id': 'mock-gpt-4',
                'object': 'model',
                'created': int(time.time()),
                'owned_by': 'mock-org',
                'permission': [],
                'root': 'mock-gpt-4'
            }
        ]
    }
    return jsonify(response)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'server': 'Mock LLM Server',
        'version': '1.0.0'
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with server info"""
    return jsonify({
        'message': 'Mock LLM Server',
        'endpoints': {
            'chat_completions': '/v1/chat/completions',
            'models': '/v1/models',
            'health': '/health'
        },
        'compatible_with': 'OpenAI API v1'
    })

if __name__ == '__main__':
    print("🚀 Starting Mock LLM Server...")
    print("📡 Endpoints available:")
    print("   - POST http://localhost:8080/v1/chat/completions")
    print("   - GET  http://localhost:8080/v1/models")
    print("   - GET  http://localhost:8080/health")
    print("\n💡 Ready for testing with Postman or AutoGen!")
    
    app.run(host='0.0.0.0', port=8080, debug=True)