import os
from dotenv import load_dotenv
from prometheus_swarm.clients import setup_client

def run_gemini_test():
    load_dotenv()
    print("Setting up Gemini client...")
    try:
        # Ensure GEMINI_API_KEY is set in your .env file
        if not os.getenv("GEMINI_API_KEY"):
            print("Error: GEMINI_API_KEY not found in .env file.")
            print("Please add it and try again.")
            return

        # Use the default model for Gemini, or specify one
        # e.g., model="gemini-1.5-pro-latest"
        gemini_client = setup_client(client="gemini") 
        print(f"Gemini client setup with model: {gemini_client.model}")

        # Create a conversation
        conversation_id = gemini_client.create_conversation(
            system_prompt="You are a helpful assistant."
        )
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
                    print(f"Tool Call: {block['tool_call']}")
        else:
            print("No response or empty content received.")
        print("-----------------------\n")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gemini_test() 