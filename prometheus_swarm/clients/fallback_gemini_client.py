"""Fallback Gemini client implementation that handles rate limits and model capabilities."""

from typing import Dict, Any, Optional, List, Union
import time
import logging
import os
from pathlib import Path

from google.api_core.exceptions import ResourceExhausted

from prometheus_swarm.clients.gemini_client import GeminiClient
from prometheus_swarm.types import MessageContent, ToolDefinition
from prometheus_swarm.utils.errors import ClientAPIError
from prometheus_swarm.utils.logging import log_key_value, log_error

class FallbackGeminiClient:
    """
    A wrapper around GeminiClient that implements a fallback strategy.
    When ResourceExhausted errors occur, it tries progressively less strict models.
    It also checks whether models actually make tool calls when required.
    
    Attributes:
        api_key: Gemini API key
        system_instruction: System instruction to use for all models
        tools: Dictionary of registered tools
        tool_functions: Dictionary of registered tool functions
        model_sequence: List of model configurations to try in order
        current_model_index: Current index in the model sequence
        client: Current GeminiClient instance
    """
    
    def __init__(
        self, 
        api_key: str, 
        system_instruction: Optional[str] = None,
        start_with_model: str = "gemini-1.5-pro-latest",
        verify_tool_calls: bool = True
    ):
        """
        Initialize the fallback client.
        
        Args:
            api_key: Gemini API key
            system_instruction: System instruction to use for all models
            start_with_model: Which model to start with (must be in model_sequence)
            verify_tool_calls: Whether to verify that models make tool calls
        """
        self.api_key = api_key
        self.system_instruction = system_instruction
        self.verify_tool_calls = verify_tool_calls
        self.tools: Dict[str, ToolDefinition] = {}
        self.tool_functions: Dict[str, Any] = {}
        
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
        for i, model_config in enumerate(self.model_sequence):
            if model_config["name"] == start_with_model:
                start_index = i
                break
        
        # Initialize with the selected model
        self._create_client(start_index)
    
    def _create_client(self, model_index: int):
        """
        Create a client with the specified model index from the sequence.
        
        Args:
            model_index: Index in the model_sequence
            
        Raises:
            ValueError: If model_index is out of bounds
        """
        if model_index >= len(self.model_sequence):
            raise ValueError("No more models available in the fallback sequence")
            
        model_config = self.model_sequence[model_index]
        log_key_value(
            f"Creating Gemini client with model", 
            model_config["name"],
            "FallbackGeminiClient"
        )
        
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
    
    def register_tool(self, tool_def: ToolDefinition):
        """
        Register a tool with the fallback client.
        
        Args:
            tool_def: Tool definition
        """
        self.tools[tool_def["name"]] = tool_def
        self.tool_functions[tool_def["name"]] = tool_def["function"]
        
        # Make sure current client has the tools
        if hasattr(self, 'client'):
            self.client.tools = self.tools
            self.client.tool_functions = self.tool_functions

    def register_tools(self, tools_dir: Union[str, Path]):
        """
        Register all tools from a directory.
        
        This delegates to the current client's register_tools method.
        
        Args:
            tools_dir: Directory containing tool modules
        """
        if not hasattr(self, 'client'):
            raise ValueError("Client not initialized")
            
        # Delegate to the client's register_tools method
        self.client.register_tools(tools_dir)
        
        # After tools are registered with the client, update our local copies
        self.tools = self.client.tools
        self.tool_functions = self.client.tool_functions
    
    def send_message(
        self, 
        prompt: str, 
        conversation_id: Optional[str] = None,
        tools_required: bool = False
    ) -> MessageContent:
        """
        Send a message with automatic fallback to less strict models if rate limits are hit.
        
        Args:
            prompt: User prompt to send
            conversation_id: Conversation ID if continuing a conversation
            tools_required: Whether tool calls are required in the response
            
        Returns:
            MessageContent: Response from the model
            
        Raises:
            ClientAPIError: If all models in the fallback sequence have been exhausted
        """
        original_model_index = self.current_model_index
        
        while self.current_model_index < len(self.model_sequence):
            try:
                # Try with current model
                log_key_value(
                    f"Attempting with model", 
                    self.model_sequence[self.current_model_index]["name"],
                    "FallbackGeminiClient"
                )
                response = self.client.send_message(prompt=prompt, conversation_id=conversation_id)
                
                # Check if the model actually made a tool call when required
                if tools_required and self.verify_tool_calls:
                    tool_call_made = False
                    if isinstance(response.get("content"), list):
                        for item in response["content"]:
                            if item.get("type") == "tool_call":
                                tool_call_made = True
                                break
                    
                    # If no tool call was made and we're not on the highest capability model,
                    # fall back to a more capable model if possible
                    if not tool_call_made:
                        capability = self.model_sequence[self.current_model_index]["capability"]
                        model_name = self.model_sequence[self.current_model_index]["name"]
                        
                        log_key_value(
                            f"Model {model_name} ({capability} capability) didn't make required tool call", 
                            "Falling back if possible",
                            "FallbackGeminiClient"
                        )
                        
                        # If we're not already at the highest capability, try to go back to a higher tier model
                        higher_capability_model_index = None
                        for i in range(self.current_model_index):
                            if self.model_sequence[i]["capability"] == "high":
                                higher_capability_model_index = i
                                break
                                
                        if higher_capability_model_index is not None:
                            # Wait before trying a higher tier model to avoid hitting rate limits again
                            time.sleep(30)  # 30 second cooldown
                            self._create_client(higher_capability_model_index)
                            continue  # Try again with the higher capability model
                        
                        # No higher capability models available, accept the response without tool calls
                        log_key_value(
                            f"No higher capability models available", 
                            f"Accepting response without tool calls from {model_name}",
                            "FallbackGeminiClient"
                        )
                
                # If we got here, we have a valid response
                return response
                
            except (ClientAPIError, ValueError) as e:
                # Check if this is a rate limit error
                is_rate_limit = isinstance(e, ClientAPIError) and isinstance(
                    getattr(e, 'original_exception', None), ResourceExhausted
                )
                
                if is_rate_limit:
                    # Try next model in sequence
                    next_model_index = self.current_model_index + 1
                    if next_model_index < len(self.model_sequence):
                        log_key_value(
                            f"Rate limit hit with {self.model_sequence[self.current_model_index]['name']}", 
                            f"Falling back to {self.model_sequence[next_model_index]['name']}",
                            "FallbackGeminiClient"
                        )
                        self._create_client(next_model_index)
                    else:
                        log_error("No more fallback models available", "FallbackGeminiClient")
                        raise ClientAPIError("All models in fallback sequence have been exhausted due to rate limits")
                else:
                    # Not a rate limit error, re-raise
                    log_error(e, "Non-rate-limit error during API call", "FallbackGeminiClient")
                    raise
        
        # If we get here, we've exhausted all models
        raise ClientAPIError("All models in fallback sequence have been exhausted")

    def create_conversation(
        self,
        system_prompt: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ) -> str:
        """
        Create a new conversation and return its ID.
        
        Args:
            system_prompt: System prompt for the conversation
            available_tools: List of tools available for the conversation
            
        Returns:
            str: Conversation ID
        """
        return self.client.create_conversation(
            system_prompt=system_prompt,
            available_tools=available_tools
        )
        
    def get_completion(
        self,
        messages: List[MessageContent],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
    ) -> MessageContent:
        """
        Get a completion with fallback handling.
        
        This is a lower-level API that proxies to the current client's get_completion.
        It doesn't implement the full fallback logic - use send_message for that.
        
        Args:
            messages: List of messages
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            tools: List of tools
            tool_choice: Tool choice configuration
            
        Returns:
            MessageContent: Response from the model
        """
        return self.client.get_completion(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice
        ) 