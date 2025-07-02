from flask import Flask, request, jsonify
import json
import time

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        messages = data.get('messages', [])
        
        # Check if the last message is a tool response
        if messages and messages[-1].get('role') == 'tool':
            # Tool has been executed, provide final answer based on tool result
            tool_response = messages[-1].get('content', '')
            
            # Parse the tool response if it's JSON
            try:
                tool_data = json.loads(tool_response)
                if tool_data.get('status') == 'success':
                    final_content = f"Here's the information you requested: {tool_data.get('report', '')}"
                else:
                    final_content = f"I encountered an issue: {tool_data.get('error_message', 'Unknown error')}"
            except (json.JSONDecodeError, AttributeError):
                final_content = f"Based on the information I retrieved: {tool_response}"
            
            return jsonify({
                "id": f"chatcmpl-mock{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "mock-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            })
        
        # Get the latest user message
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if not user_messages:
            return jsonify({
                "id": f"chatcmpl-mock{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "mock-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 10,
                    "total_tokens": 15
                }
            })
        
        latest_user_message = user_messages[-1]['content'].lower()
        
        # Check if current user request needs a tool call
        tools = data.get('tools', [])
        if tools:
            # Determine which tool to call based on the LATEST user message
            if 'weather' in latest_user_message:
                return jsonify({
                    "id": f"chatcmpl-mock{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": f"call_weather_{int(time.time())}",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": json.dumps({"city": "New York"})
                                }
                            }]
                        },
                        "finish_reason": "tool_calls"
                    }],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 5,
                        "total_tokens": 20
                    }
                })
            elif 'time' in latest_user_message:
                return jsonify({
                    "id": f"chatcmpl-mock{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": f"call_time_{int(time.time())}",
                                "type": "function",
                                "function": {
                                    "name": "get_current_time",
                                    "arguments": json.dumps({"city": "New York"})
                                }
                            }]
                        },
                        "finish_reason": "tool_calls"
                    }],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 5,
                        "total_tokens": 20
                    }
                })
        
        # Default response for greetings or non-tool requests
        return jsonify({
            "id": f"chatcmpl-mock{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "mock-model",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! I can help you with weather and time information. Just ask me about the weather or current time!"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "internal_error",
                "code": "internal_error"
            }
        }), 500

if __name__ == '__main__':
    print("Starting Mock LLM Server on http://localhost:8001")
    app.run(host='0.0.0.0', port=8001, debug=True)
