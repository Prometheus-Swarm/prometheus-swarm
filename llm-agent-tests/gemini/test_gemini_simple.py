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
            model="gemini-1.5-flash-latest",
            system_instruction="You are a helpful assistant."
        )
        print(f"Gemini client setup with model: {gemini_client.model}")
        
        # Create a conversation without registering tools
        conversation_id = gemini_client.create_conversation()
        print(f"Created conversation ID: {conversation_id}")
        
        # Send a message directly using client._make_api_call without tools
        prompt = "Hello, Gemini! Tell me a fun fact about programming."
        print(f"Sending prompt: \"{prompt}\"")
        
        # Convert the prompt to the format expected by the API
        api_messages = [{"role": "user", "parts": [{"text": prompt}]}]
        
        try:
            # Call the API directly without involving tools
            response = gemini_client._make_api_call(
                messages=api_messages,
                max_tokens=150
            )
            
            # Handle the response
            print("\n--- Gemini Response ---")
            if response and hasattr(response, "candidates") and response.candidates:
                text_content = response.candidates[0].content.parts[0].text
                print(text_content)
            else:
                print("No response received.")
            print("-----------------------\n")
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gemini_test() 