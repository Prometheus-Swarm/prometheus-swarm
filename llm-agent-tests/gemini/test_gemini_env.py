import os
import sys
import json
from dotenv import load_dotenv
from prometheus_swarm.clients.gemini_client import GeminiClient

def run_gemini_test():
    # Try to load from .env if exists, but continue without it
    try:
        load_dotenv()
    except:
        pass
    
    print("Setting up Gemini client...")
    
    # Get API key from environment or prompt for it
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = input("Please enter your Gemini API key: ")
        if not api_key:
            print("Error: No API key provided.")
            return
    
    try:
        # Initialize the client directly
        gemini_client = GeminiClient(
            api_key=api_key,
            model="gemini-1.5-flash-latest",  # Or "gemini-pro" or your preferred model
            system_instruction="You are a helpful assistant."
        )
        print(f"Gemini client setup with model: {gemini_client.model}")
        
        # Register tools - simplified for this test
        tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prometheus_swarm", "tools")
        if os.path.exists(tools_dir):
            registered_tools = gemini_client.register_tools(tools_dir)
            print(f"Registered {len(registered_tools)} tools from {tools_dir}")
        else:
            print(f"Warning: Tools directory not found at {tools_dir}")
        
        # Create a conversation
        conversation_id = gemini_client.create_conversation()
        print(f"Created conversation ID: {conversation_id}")
        
        # Send a message
        prompt = "Hello, Gemini! Tell me a fun fact about programming."
        print(f"Sending prompt: \"{prompt}\"")
        
        response = gemini_client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            max_tokens=150
        )
        
        print("\n--- Gemini Response ---")
        if response and response.get("content"):
            for block in response["content"]:
                if block["type"] == "text":
                    print(block["text"])
                elif block["type"] == "tool_call":
                    print(f"Tool Call: {block['tool_call']['name']}")
                    print(f"Arguments: {json.dumps(block['tool_call']['arguments'], indent=2)}")
        else:
            print("No response or empty content received.")
        print("-----------------------\n")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gemini_test() 