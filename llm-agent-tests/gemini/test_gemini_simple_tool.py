import os
import json
from dotenv import load_dotenv
from prometheus_swarm.clients import setup_client

def run_simple_tool_test():
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file.")
        return
        
    try:
        # Initialize client using project setup
        print("Setting up Gemini client...")
        gemini_client = setup_client(client="gemini", model="gemini-1.5-flash-latest")
        
        # Define a simple demo conversation with list_files tool
        conversation_id = gemini_client.create_conversation(
            system_prompt="You are a helpful assistant who can list files. Always use tools when appropriate.",
            available_tools=["list_files"]  # Just use one simple tool
        )
        print(f"Created conversation with list_files tool")
        
        # Use a very specific prompt
        prompt = "Please list the files in the prometheus_swarm directory. You MUST use the list_files tool."
        print(f"Sending prompt: \"{prompt}\"")
        
        # Set tool_choice to require the list_files tool
        tool_choice = {"type": "required", "tool": "list_files"}
        
        # Send message and catch the first response
        response = gemini_client.send_message(
            prompt=prompt,
            conversation_id=conversation_id,
            max_tokens=200,
            tool_choice=tool_choice
        )
        
        # Process the response looking for tool calls
        tool_calls = []
        if response and response.get("content"):
            print("\n--- Gemini Initial Response ---")
            for block in response["content"]:
                if block["type"] == "text":
                    print("TEXT:", block["text"])
                elif block["type"] == "tool_call":
                    tool_call = block["tool_call"]
                    print(f"TOOL CALL: {tool_call['name']}")
                    print(f"Arguments: {json.dumps(tool_call['arguments'], indent=2)}")
                    tool_calls.append(tool_call)
        
        # If we got tool calls, handle them and process the results
        if tool_calls:
            print("\n--- Tool Execution Results ---")
            # Store tool results for sending back
            tool_results = []
            
            for tool_call in tool_calls:
                result = gemini_client.execute_tool(tool_call)
                print(f"Result: {json.dumps(result, indent=2)}")
                
                # Add tool result to the results list
                tool_results.append({
                    "tool_call_id": tool_call["id"],
                    "response": str(result)
                })
            
            # If we have tool results, send them back for a final response
            if tool_results:
                print("\n--- Sending Tool Results Back ---")
                tool_response_str = json.dumps(tool_results)
                
                continued_response = gemini_client.send_message(
                    conversation_id=conversation_id,
                    tool_response=tool_response_str,
                    max_tokens=200
                )
                
                print("\n--- Gemini Final Response ---")
                if continued_response and continued_response.get("content"):
                    for block in continued_response["content"]:
                        if block["type"] == "text":
                            print("TEXT:", block["text"])
                
        print("-----------------------\n")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_simple_tool_test() 