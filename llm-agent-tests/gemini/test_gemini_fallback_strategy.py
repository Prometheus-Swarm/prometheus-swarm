import os
import unittest
import time
from dotenv import load_dotenv
from prometheus_swarm.clients.gemini_client import GeminiClient
from prometheus_swarm.types import MessageContent, ToolDefinition
from prometheus_swarm.utils.errors import ClientAPIError
from google.api_core.exceptions import ResourceExhausted

load_dotenv()

# Define the tool for testing
classify_repository_tool_def: ToolDefinition = {
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
            },
        },
        "required": ["repo_type"],
    },
    "function": lambda repo_type: {"success": True, "message": f"Classified as {repo_type}"}
}

class FallbackGeminiClient:
    """
    A wrapper around GeminiClient that implements a fallback strategy.
    When a ResourceExhausted error occurs, it tries progressively less strict models.
    """
    def __init__(self, api_key, system_instruction=None, start_with_model=None):
        self.api_key = api_key
        self.system_instruction = system_instruction
        self.tools = {}
        self.tool_functions = {}
        
        # Define fallback sequence from most to least strict models
        self.model_sequence = [
            {
                "name": "gemini-1.5-pro-latest",
                "max_retries": 3,
                "retry_delay": 60,
                "capability": "high"
            },
            {
                "name": "gemini-1.5-flash-latest",
                "max_retries": 2,
                "retry_delay": 30,
                "capability": "medium"
            },
            {
                "name": "gemini-2.0-flash",
                "max_retries": 1,
                "retry_delay": 15,
                "capability": "low"
            }
        ]
        
        # Find the starting model index
        start_index = 0
        if start_with_model:
            for i, model_config in enumerate(self.model_sequence):
                if model_config["name"] == start_with_model:
                    start_index = i
                    break
                    
        # Initialize with the selected model
        self._create_client(start_index)
    
    def _create_client(self, model_index):
        """Create a client with the specified model index from the sequence"""
        if model_index >= len(self.model_sequence):
            raise ValueError("No more models available in the fallback sequence")
            
        model_config = self.model_sequence[model_index]
        print(f"Creating client with model: {model_config['name']}")
        
        self.current_model_index = model_index
        self.client = GeminiClient(
            api_key=self.api_key,
            model=model_config["name"],
            system_instruction=self.system_instruction,
            max_retries_on_exhaustion=model_config["max_retries"],
            retry_delay_seconds=model_config["retry_delay"]
        )
        
        # Register tools with the client
        self.client.tools = self.tools
        self.client.tool_functions = self.tool_functions
    
    def register_tool(self, tool_def):
        """Register a tool with the fallback client"""
        self.tools[tool_def["name"]] = tool_def
        self.tool_functions[tool_def["name"]] = tool_def["function"]
        
        # Make sure current client has the tools
        if hasattr(self, 'client'):
            self.client.tools = self.tools
            self.client.tool_functions = self.tool_functions
    
    def send_message(self, prompt, conversation_id=None):
        """
        Send a message with automatic fallback to less strict models if rate limits are hit
        """
        original_model_index = self.current_model_index
        
        while self.current_model_index < len(self.model_sequence):
            try:
                # Try with current model
                print(f"Attempting with model: {self.model_sequence[self.current_model_index]['name']}")
                response = self.client.send_message(prompt=prompt, conversation_id=conversation_id)
                
                # Check if the model actually made a tool call (for models with lower capability)
                if self.model_sequence[self.current_model_index]["capability"] != "high":
                    tool_call_made = False
                    if isinstance(response.get("content"), list):
                        for item in response["content"]:
                            if item.get("type") == "tool_call":
                                tool_call_made = True
                                break
                    
                    # If no tool call was made and we're not on the highest capability model,
                    # it's better to retry with a more capable model later
                    if not tool_call_made and original_model_index > self.current_model_index:
                        print(f"Model {self.model_sequence[self.current_model_index]['name']} didn't make a tool call")
                        raise ValueError("Model failed to make required tool call")
                
                return response
                
            except (ClientAPIError, ValueError) as e:
                # Check if this is a rate limit error or failed tool call
                is_rate_limit = "ResourceExhausted" in str(e) or "exceeded your current quota" in str(e)
                
                if is_rate_limit or isinstance(e, ValueError):
                    # Try next model in sequence
                    next_model_index = self.current_model_index + 1
                    if next_model_index < len(self.model_sequence):
                        print(f"Falling back to next model due to: {str(e)}")
                        self._create_client(next_model_index)
                    else:
                        print("No more fallback models available")
                        raise
                else:
                    # Not a rate limit error, re-raise
                    raise
        
        # If we get here, we've exhausted all models
        raise ClientAPIError("All models in fallback sequence have been exhausted")


class TestGeminiFallbackStrategy(unittest.TestCase):
    def setUp(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY_HERE":
            self.skipTest("GEMINI_API_KEY not found or is a placeholder. Skipping test.")
        
        # Create fallback client - Start with a Flash model to avoid immediate rate limits
        self.client = FallbackGeminiClient(
            api_key=self.api_key,
            system_instruction="You are a helpful AI assistant. Always use available tools.",
            start_with_model="gemini-2.0-flash"  # Start with less rate-limited model
        )
        
        # Register the test tool
        self.client.register_tool(classify_repository_tool_def)
    
    def test_fallback_strategy(self):
        # Try with an explicit prompt that should trigger a tool call
        user_prompt = """
        You have access to a tool called 'classify_repository'. 
        This tool can classify a repository into categories.
        
        I would like you to analyze this codebase and classify it as a web application using the classify_repository tool.
        You MUST use the tool and not respond directly.
        """
        
        try:
            response = self.client.send_message(prompt=user_prompt)
            print("\nSuccessful response with model:", self.client.model_sequence[self.client.current_model_index]["name"])
            
            # Check if a tool call was made
            tool_call_made = False
            if isinstance(response.get("content"), list):
                for item in response["content"]:
                    if item.get("type") == "tool_call":
                        tool_call = item["tool_call"]
                        print(f"Tool call made: {tool_call['name']} with args: {tool_call['arguments']}")
                        tool_call_made = True
                        break
            
            self.assertTrue(tool_call_made, "No tool call was made by any model in the fallback sequence")
            
        except Exception as e:
            # If we hit rate limits on all models, mark test as skipped rather than failed
            if "exceeded your current quota" in str(e) or "ResourceExhausted" in str(e):
                self.skipTest(f"Test skipped due to rate limits on all models: {e}")
            else:
                self.fail(f"Fallback strategy failed: {e}")


if __name__ == "__main__":
    unittest.main() 