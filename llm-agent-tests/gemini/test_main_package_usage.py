#!/usr/bin/env python3
"""
Testing the FallbackGeminiClient through the main package setup_client function.
"""

import os
import sys
from dotenv import load_dotenv

# Import the setup_client function from prometheus_swarm
from prometheus_swarm.clients import setup_client

def main():
    # Load API key from environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("Error: GEMINI_API_KEY not found or is a placeholder.")
        print("Please set your Gemini API key in the .env file.")
        return
    
    print("Setting up fallback_gemini client through the main package...")
    
    try:
        # Use the setup_client function to create the fallback_gemini client
        # Starting with gemini-2.0-flash to avoid rate limits
        client = setup_client("fallback_gemini", "gemini-2.0-flash")
        print(f"Client created: {type(client).__name__}")
        
        # Create a new conversation
        conversation_id = client.create_conversation()
        print(f"Created conversation with ID: {conversation_id}")
        
        # Test a simple prompt
        prompt = "What are some benefits of using the Gemini API for tool calling?"
        print(f"\nSending simple prompt: {prompt}")
        
        response = client.send_message(
            prompt=prompt,
            conversation_id=conversation_id
        )
        
        # Display the response
        print("\n=== Response ===")
        if isinstance(response.get("content"), list):
            for item in response["content"]:
                if item.get("type") == "text":
                    print(f"{item['text']}")
        
        # Now test with tool calling
        tool_prompt = """
        Based on the following repository characteristics, please classify it:
        - Python files with machine learning imports (scikit-learn, tensorflow)
        - Jupyter notebooks
        - Requirements.txt with data science packages
        - Data preprocessing scripts
        """
        
        print(f"\nSending prompt with tool calling requirement...")
        
        tool_response = client.send_message(
            prompt=tool_prompt,
            conversation_id=conversation_id,
            tools_required=True  # Require tool calling
        )
        
        # Display the tool calling response
        print("\n=== Tool Calling Response ===")
        tool_calls = []
        if isinstance(tool_response.get("content"), list):
            for item in tool_response["content"]:
                if item.get("type") == "text":
                    print(f"{item['text']}")
                elif item.get("type") == "tool_call":
                    tool_call = item["tool_call"]
                    print(f"Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                    tool_calls.append(tool_call)
        
        print("\nTest complete!")
        
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    main() 