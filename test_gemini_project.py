import os
from dotenv import load_dotenv
from prometheus_swarm.clients import setup_client

def run_gemini_test():
    """Test Gemini client using the project's setup_client approach."""
    # Load environment variables 
    load_dotenv()
    
    # Ensure GEMINI_API_KEY is set
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file.")
        print("Please add it and try again.")
        return

    try:
        print("Setting up Gemini client using project setup_client...")
        gemini_client = setup_client(client="gemini", model="gemini-1.5-flash-latest")
        print(f"Client setup successful with model: {gemini_client.model}")
        
        # Create a conversation
        conversation_id = gemini_client.create_conversation(
            system_prompt="You are a helpful assistant with knowledge of AI and programming."
        )
        print(f"Created conversation ID: {conversation_id}")
        
        # Send a message
        prompt = "What is the best approach for handling errors in Python?"
        print(f"Sending prompt: \"{prompt}\"")
        
        response = gemini_client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            max_tokens=300
        )
        
        # Display the response
        print("\n--- Gemini Response ---")
        if response and response.get("content"):
            for block in response["content"]:
                if block["type"] == "text":
                    print(block["text"])
                elif block["type"] == "tool_call":
                    print(f"Tool Call: {block['tool_call']['name']}")
        else:
            print("No response or empty content received.")
        print("-----------------------\n")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gemini_test() 