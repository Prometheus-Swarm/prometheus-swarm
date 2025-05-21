#!/usr/bin/env python3
"""
Testing the read_file tool with the FallbackGeminiClient.
"""

import os
from dotenv import load_dotenv
from prometheus_swarm.clients import setup_client

def main():
    # Load API key from environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("Error: GEMINI_API_KEY not found or is a placeholder.")
        print("Please set your Gemini API key in the .env file.")
        return
    
    print("Setting up fallback_gemini client to test read_file tool...")
    
    # Use the setup_client function to create the fallback_gemini client
    # Starting with gemini-1.5-flash-latest to try a different model
    client = setup_client("fallback_gemini", "gemini-1.5-flash-latest")
    
    # Create a new conversation
    conversation_id = client.create_conversation()
    print(f"Created conversation with ID: {conversation_id}")
    
    # Test the read_file tool
    test_read_file(client, conversation_id)

def test_read_file(client, conversation_id):
    print("\n=== Testing read_file tool ===")
    
    prompt = """
    I need to see the contents of a file. The file is called "test_multiple_tools.py".
    Please use the read_file tool to display the first 10 lines of the file.
    """
    
    try:
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            tools_required=True
        )
        
        # Check for tool calls
        found_tool_call = False
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    if tool_call["name"] == "read_file":
                        found_tool_call = True
                        print(f"✅ Success! Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        break
        
        if not found_tool_call:
            print("❌ Failed: read_file tool call not found in response")
    
    except Exception as e:
        print(f"❌ Error testing read_file: {e}")

if __name__ == "__main__":
    main() 