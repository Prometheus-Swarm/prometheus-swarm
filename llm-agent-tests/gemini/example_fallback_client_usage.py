#!/usr/bin/env python3
"""
Example usage of the FallbackGeminiClient.
This demonstrates how to use the client with automatic fallback for tool calling.
"""

import os
from dotenv import load_dotenv
from prometheus_swarm.clients.fallback_gemini_client import FallbackGeminiClient
from prometheus_swarm.types import ToolDefinition

def main():
    # Load API key from environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("Error: GEMINI_API_KEY not found or is a placeholder.")
        print("Please set your Gemini API key in the .env file.")
        return
    
    print("Creating FallbackGeminiClient...")
    
    # Create the client, starting with Flash model to avoid initial rate limits
    # You could also start with Pro model: start_with_model="gemini-1.5-pro-latest"
    client = FallbackGeminiClient(
        api_key=api_key,
        system_instruction="You are a helpful AI assistant that uses tools when available.",
        start_with_model="gemini-1.5-flash-latest",
        verify_tool_calls=True  # Check if models actually make tool calls
    )
    
    # Define and register a sample tool
    classify_repository_tool = {
        "name": "classify_repository",
        "description": "Classify a repository into a specific type",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_type": {
                    "type": "string",
                    "description": "The repository type, must be one of: web_application, mobile_application, data_science, embedded_systems, game_development, devops_tool, library, documentation, machine_learning, other",
                    "enum": [
                        "web_application",
                        "mobile_application", 
                        "data_science",
                        "embedded_systems",
                        "game_development", 
                        "devops_tool",
                        "library",
                        "documentation",
                        "machine_learning",
                        "other"
                    ]
                }
            },
            "required": ["repo_type"]
        },
        "function": lambda args: {
            "success": True,
            "message": f"Repository classified as: {args['repo_type']}",
            "data": {"classification": args["repo_type"]}
        }
    }
    
    # Register the tool with the client
    print("Registering tool...")
    client.register_tool(classify_repository_tool)
    
    # Create a conversation
    print("Creating conversation...")
    conversation_id = client.create_conversation()
    
    # Explicit prompt that requests tool use
    user_prompt = """
    You have access to a tool called 'classify_repository'.
    
    Based on these characteristics:
    - Has HTML, CSS, and JavaScript files
    - Contains React components
    - Has a package.json with web dependencies
    - Includes API endpoints
    
    Please use the classify_repository tool to categorize this project.
    """
    
    print("\nSending message with tool requirement...")
    # Send message and require tool use
    response = client.send_message(
        prompt=user_prompt,
        conversation_id=conversation_id,
        tools_required=True  # This tells the client that a tool call is required
    )
    
    # Process and display the response
    print("\n=== Response ===")
    
    # Check for tool calls in the response
    tool_calls = []
    if isinstance(response.get("content"), list):
        for item in response["content"]:
            if item.get("type") == "text":
                print(f"Text: {item['text']}")
            elif item.get("type") == "tool_call":
                tool_call = item["tool_call"]
                print(f"Tool call: {tool_call['name']} with args: {tool_call['arguments']}")
                tool_calls.append(tool_call)
    
    # If tool calls were made, execute them and continue the conversation
    if tool_calls:
        print("\nExecuting tool calls and continuing conversation...")
        
        # For each tool call, execute the tool and format the response
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            
            if tool_name in client.tool_functions:
                # Get the tool function
                tool_fn = client.tool_functions[tool_name]
                
                # Execute the tool with the provided arguments
                result = tool_fn(tool_call["arguments"])
                print(f"Tool result: {result}")
                
                # Format the response as text prompt instead of a structured message
                # This is more reliable for the Gemini API
                follow_up_prompt = f"""
                I executed the tool {tool_name} with the arguments {tool_call['arguments']}.
                The tool returned the following result:
                {result}
                
                Please provide a summary of what this means.
                """
                
                # Send the tool response back to continue the conversation
                try:
                    follow_up_response = client.send_message(
                        prompt=follow_up_prompt,
                        conversation_id=conversation_id
                    )
                    
                    print("\n=== Follow-up Response ===")
                    if isinstance(follow_up_response.get("content"), list):
                        for item in follow_up_response["content"]:
                            if item.get("type") == "text":
                                print(f"Text: {item['text']}")
                except Exception as e:
                    print(f"Error getting follow-up response: {e}")
    
    print("\nDemonstration complete!")

if __name__ == "__main__":
    main() 