from prometheus_swarm.clients import setup_client
import time
from prometheus_swarm.utils.logging import log_section, log_key_value, configure_logging
import json
import logging

def main():
    # Configure logging
    configure_logging()
    logging.getLogger("builder").setLevel(logging.DEBUG)
    
    # Create a real client instance (defaults to Anthropic)
    client = setup_client("anthropic")
    
    # Create a new conversation
    conversation_id = client.create_conversation()
    print(f"Created conversation with ID: {conversation_id}")
    
    # Send 15 messages
    for i in range(15):
        message = f"This is message number {i + 1}"
        print(f"\nSending message {i + 1}: {message}")
        
        try:
            response = client.send_message(
                prompt=message,
                conversation_id=conversation_id
            )
            
            # Print the response
            for block in response["content"]:
                if block["type"] == "text":
                    print(f"Response: {block['text']}")
                elif block["type"] == "tool_call":
                    print(f"Tool call: {block['tool_call']['name']}")
            
            # Get and log summarized messages
            summarized_messages = client.storage.get_summarized_messages(conversation_id)
            if summarized_messages:
                print("\nSummarized Messages:")
                for msg in summarized_messages:
                    content = json.loads(msg["content"])
                    if isinstance(content, dict) and "summary" in content:
                        print(f"Summary: {content['summary']}")
                    else:
                        print(f"Consolidated Messages: {content}")
            
            # Add a small delay between messages
            time.sleep(1)
            
        except Exception as e:
            print(f"Error sending message {i + 1}: {str(e)}")
            break

if __name__ == "__main__":
    main() 