import os
import json
from dotenv import load_dotenv
from prometheus_swarm.clients.gemini_client import GeminiClient
from prometheus_swarm.utils.logging import log_key_value

def get_weather(location: str):
    """Get the weather for a location."""
    return {
        "success": True,
        "message": f"Weather information for {location}",
        "data": {
            "location": location,
            "temperature": 72,
            "conditions": "sunny",
            "forecast": ["sunny", "cloudy", "rainy"]
        }
    }

def run_gemini_test():
    # Try to load from .env file
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
            system_instruction="You are a helpful assistant who has access to a weather tool."
        )
        print(f"Gemini client setup with model: {gemini_client.model}")
        
        # Register a simple tool manually
        weather_tool = {
            "name": "get_weather",
            "description": "Get the current weather and forecast for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state or country (e.g., 'San Francisco, CA' or 'Paris, France')"
                    }
                },
                "required": ["location"]
            },
            "function": get_weather
        }
        
        # Manually add the tool to the client's tool dictionary
        gemini_client.tools["get_weather"] = weather_tool
        print("Registered weather tool")
        
        # Create a conversation with the available tool
        conversation_id = gemini_client.create_conversation(
            available_tools=["get_weather"]
        )
        print(f"Created conversation ID: {conversation_id}")
        
        # Send a message requesting weather
        prompt = "I'd like to know the weather in Miami Beach, Florida."
        print(f"Sending prompt: \"{prompt}\"")
        
        # Send message normally, which will handle tool calling
        try:
            response = gemini_client.send_message(
                prompt=prompt,
                conversation_id=conversation_id,
                max_tokens=150
            )
            
            print("\n--- Gemini Initial Response ---")
            if response and response.get("content"):
                for block in response["content"]:
                    if block["type"] == "text":
                        print("TEXT:", block["text"])
                    elif block["type"] == "tool_call":
                        tool_call = block["tool_call"]
                        print(f"TOOL CALL: {tool_call['name']}")
                        print(f"Arguments: {json.dumps(tool_call['arguments'], indent=2)}")
                        
                        # Execute the tool and continue the conversation
                        print("\n--- Executing Tool ---")
                        tool_result = gemini_client.execute_tool(tool_call)
                        print(f"Result: {json.dumps(tool_result, indent=2)}")
                        
                        # Format tool response for the model
                        tool_response = json.dumps([{
                            "tool_call_id": tool_call["id"],
                            "response": str(tool_result)
                        }])
                        
                        # Send the tool response back to continue the conversation
                        print("\n--- Sending Tool Response ---")
                        continued_response = gemini_client.send_message(
                            conversation_id=conversation_id,
                            tool_response=tool_response
                        )
                        
                        print("\n--- Gemini Final Response ---")
                        if continued_response and continued_response.get("content"):
                            for block in continued_response["content"]:
                                if block["type"] == "text":
                                    print("TEXT:", block["text"])
            else:
                print("No response or empty content received.")
            print("-----------------------\n")
            
        except Exception as e:
            print(f"Error during conversation: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_gemini_test() 