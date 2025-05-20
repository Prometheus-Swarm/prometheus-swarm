"""Gemini API client implementation."""

from typing import Dict, Any, Optional, List, Union
import json
import ast
import google.generativeai as genai
# Just import the types we know are available
from google.generativeai.types import (
    GenerateContentResponse,
    GenerationConfig
)
from google.protobuf.struct_pb2 import Struct

from .base_client import Client
from ..types import (
    ToolDefinition,
    MessageContent,
    TextContent,
    ToolCallContent,
    ToolResponseContent,
    ToolResponse,
    ToolOutput,
    ToolChoice,
)
from prometheus_swarm.utils.logging import log_error, log_key_value
from prometheus_swarm.utils.errors import ClientAPIError


# Helper to convert protobuf Struct to Python dict
def _protobuf_struct_to_dict(struct_pb: Optional[Struct]) -> Dict[str, Any]:
    """Converts a google.protobuf.struct_pb2.Struct to a Python dictionary."""
    if not struct_pb:
        return {}
    return dict(struct_pb)


class GeminiClient(Client):
    """Gemini API client implementation."""

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(model=model, **kwargs)
        genai.configure(api_key=api_key)
        self.system_instruction = system_instruction
        self._initialize_model()

    def _initialize_model(self):
        """Initializes or re-initializes the GenerativeModel client."""
        model_kwargs = {}
        if self.system_instruction:
            model_kwargs["system_instruction"] = self.system_instruction

        self.client = genai.GenerativeModel(
            model_name=self.model, 
            **model_kwargs
        )

    def _get_api_name(self) -> str:
        return "Gemini"

    def _get_default_model(self) -> str:
        return "gemini-1.5-flash-latest"

    def _should_split_tool_responses(self) -> bool:
        return False

    def _convert_tool_to_api_format(self, tool: ToolDefinition) -> Dict[str, Any]:
        """Convert our tool definition to Gemini's function format."""
        # Create a sanitized version of the schema parameters
        # Gemini is picky about JSON Schema fields it doesn't recognize
        parameters = {}
        if "parameters" in tool and isinstance(tool["parameters"], dict):
            schema = tool["parameters"]
            
            # Copy basic JSON Schema properties that Gemini recognizes
            parameters["type"] = "object"  # Always an object at the top level
            
            # Handle properties - this is required for the object
            if "properties" in schema and isinstance(schema["properties"], dict):
                properties = {}
                
                # Convert each property
                for prop_name, prop_value in schema["properties"].items():
                    # Create a clean property definition with only supported fields
                    clean_prop = {}
                    
                    # Basic properties common to all types
                    if "type" in prop_value:
                        clean_prop["type"] = prop_value["type"]
                    if "description" in prop_value:
                        clean_prop["description"] = prop_value["description"]
                    
                    # Handle string-specific properties
                    if prop_value.get("type") == "string" and "enum" in prop_value:
                        clean_prop["enum"] = prop_value["enum"]
                    
                    # Handle array properties - Gemini requires 'items' for arrays
                    if prop_value.get("type") == "array":
                        # If items is missing, add a default
                        if "items" not in prop_value:
                            # Default to string items if not specified
                            clean_prop["items"] = {"type": "string"}
                        else:
                            # Sanitize existing items schema
                            items_schema = prop_value["items"]
                            clean_items = {}
                            
                            # Copy basic properties from items
                            if isinstance(items_schema, dict):
                                if "type" in items_schema:
                                    clean_items["type"] = items_schema["type"]
                                else:
                                    clean_items["type"] = "string"  # Default type
                                
                                if "description" in items_schema:
                                    clean_items["description"] = items_schema["description"]
                                    
                                # Add enum if it's a string array with enum values
                                if items_schema.get("type") == "string" and "enum" in items_schema:
                                    clean_items["enum"] = items_schema["enum"]
                            else:
                                # If items is not a dict, default to string
                                clean_items["type"] = "string"
                                
                            clean_prop["items"] = clean_items
                    
                    # Handle nested objects (if needed)
                    if prop_value.get("type") == "object" and "properties" in prop_value:
                        nested_properties = {}
                        for nested_name, nested_value in prop_value["properties"].items():
                            nested_prop = {}
                            if "type" in nested_value:
                                nested_prop["type"] = nested_value["type"]
                            if "description" in nested_value:
                                nested_prop["description"] = nested_value["description"]
                                
                            # Handle array types in nested objects too
                            if nested_value.get("type") == "array":
                                if "items" not in nested_value:
                                    nested_prop["items"] = {"type": "string"}
                                else:
                                    nested_items = nested_value["items"]
                                    if isinstance(nested_items, dict):
                                        clean_nested_items = {"type": nested_items.get("type", "string")}
                                        if "description" in nested_items:
                                            clean_nested_items["description"] = nested_items["description"]
                                        nested_prop["items"] = clean_nested_items
                                    else:
                                        nested_prop["items"] = {"type": "string"}
                            
                            nested_properties[nested_name] = nested_prop
                            
                        clean_prop["properties"] = nested_properties
                        
                        # Handle required fields for nested objects
                        if "required" in prop_value and isinstance(prop_value["required"], list):
                            clean_prop["required"] = prop_value["required"]
                    
                    # Add the cleaned property to our parameters
                    properties[prop_name] = clean_prop
                
                parameters["properties"] = properties
            
            # Add required fields if present
            if "required" in schema and isinstance(schema["required"], list):
                parameters["required"] = schema["required"]
                
        return {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": parameters
        }

    def _convert_message_to_api_format(self, message: MessageContent) -> Dict[str, Any]:
        """Convert our message format to Gemini's Content format."""
        role = message["role"]
        content = message["content"]
        
        # Map our roles to Gemini roles
        api_role = "user"
        if role == "assistant":
            api_role = "model"
        elif role == "tool":
            api_role = "function"  # Gemini uses "function" for tool responses

        api_parts = []
        if isinstance(content, str):
            api_parts.append({"text": content})
        elif isinstance(content, list):
            for block in content:
                block_type = block["type"]
                if block_type == "text":
                    api_parts.append({"text": block["text"]})
                elif block_type == "tool_call":
                    # Convert tool calls
                    tool_call = block["tool_call"]
                    args = tool_call["arguments"]
                    if not isinstance(args, dict):
                        try:
                            args = json.loads(str(args))
                        except json.JSONDecodeError:
                            log_error(f"Failed to parse tool arguments for {tool_call['name']}: {args}", "GeminiClient")
                            args = {}
                    
                    # Create a function call part
                    api_parts.append({
                        "function_call": {
                            "name": tool_call["name"],
                            "args": args
                        }
                    })
                elif block_type == "tool_response":
                    # Convert tool responses
                    tool_response = block["tool_response"]
                    response_content = tool_response.get("output", {})
                    
                    # Create a function response part
                    api_parts.append({
                        "function_response": {
                            "name": tool_response["tool_call_id"],  # Use the tool_call_id as the function name
                            "response": {
                                "content": response_content
                            }
                        }
                    })
        
        return {"role": api_role, "parts": api_parts}

    def _convert_api_response_to_message(self, response: GenerateContentResponse) -> MessageContent:
        """Convert Gemini's API response to our MessageContent format."""
        content_list = []
        
        if not response.candidates:
            log_error("Gemini API response has no candidates", "GeminiClient")
            return {"role": "assistant", "content": [{"type": "text", "text": "Error: No response from API"}]}
            
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        
        # Check for early termination
        if finish_reason not in [1, "STOP", None]:  # 1 or "STOP" means normal completion
            text_content = f"Model response terminated early. Finish Reason: {finish_reason}.\n"
            
            # Try to get any partial content
            try:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_content += part.text
            except Exception as e:
                log_error(f"Error accessing partial content: {e}", "GeminiClient")
                
            content_list.append({"type": "text", "text": text_content})
            return {"role": "assistant", "content": content_list}
            
        # Process normal response
        gemini_content = candidate.content
        for part in gemini_content.parts:
            if hasattr(part, "text") and part.text:
                content_list.append({"type": "text", "text": part.text})
            elif hasattr(part, "function_call") and part.function_call:
                # Convert function call to tool call
                fc = part.function_call
                args_dict = {}
                
                if hasattr(fc, "args") and fc.args:
                    # Convert args to dict
                    args_dict = _protobuf_struct_to_dict(fc.args)
                    
                content_list.append({
                    "type": "tool_call",
                    "tool_call": {
                        "id": fc.name,  # Use function name as ID
                        "name": fc.name,
                        "arguments": args_dict
                    }
                })
                
        return {"role": "assistant", "content": content_list}

    def _convert_tool_choice_to_api_format(self, tool_choice: ToolChoice) -> Optional[Dict[str, Any]]:
        """Convert our tool choice format to Gemini's format."""
        choice_type = tool_choice.get("type", "optional")
        
        if choice_type == "none":
            return {"function_calling_config": {"mode": "NONE"}}
        elif choice_type == "optional":
            return {"function_calling_config": {"mode": "ANY"}}
        elif choice_type == "required" and tool_choice.get("tool"):
            # For a specific required tool
            return {
                "function_calling_config": {
                    "mode": "ANY",
                    "allowed_function_names": [tool_choice["tool"]]
                }
            }
        
        # Default to ANY mode (optional)
        return {"function_calling_config": {"mode": "ANY"}}

    def _make_api_call(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Make API call to Gemini."""
        # Set up generation config
        generation_config_args = {}
        if max_tokens is not None:
            generation_config_args["max_output_tokens"] = max_tokens
            
        final_generation_config = GenerationConfig(**generation_config_args) if generation_config_args else None
        
        # Prepare tools
        gemini_tools = None
        if tools:
            # Create a tool with function declarations
            gemini_tools = [{"function_declarations": tools}]
            
        # Handle system prompt
        target_client = self.client
        if system_prompt and system_prompt != self.system_instruction:
            # Create a new client instance with the provided system instruction
            target_client = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt
            )
            
        try:
            # Make the API call
            response = target_client.generate_content(
                contents=messages,
                tools=gemini_tools,
                tool_config=tool_choice,
                generation_config=final_generation_config
            )
            return response
        except Exception as e:
            # Handle common API errors
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg or "API_KEY_MISSING" in error_msg:
                log_error(e, "Invalid or missing API key", include_traceback=False)
                raise ClientAPIError(e)
            elif "billing" in error_msg.lower():
                log_error(e, "Billing account issue", include_traceback=False)
                raise ClientAPIError(e)
                
            # Log and re-raise other errors
            log_error(e, f"Error during Gemini API call to model {self.model}", include_traceback=True)
            raise ClientAPIError(e)

    def _format_tool_response(self, response_str: str) -> MessageContent:
        """Format a tool execution result into our MessageContent format."""
        tool_results = json.loads(response_str)
        content_blocks = []
        
        for result in tool_results:
            tool_call_id = result["tool_call_id"]
            response_string = result["response"]
            
            try:
                # Parse the response string to a dict
                tool_output = ast.literal_eval(response_string)
                if not isinstance(tool_output, dict) or "success" not in tool_output:
                    raise ValueError("Invalid tool output format")
            except (SyntaxError, ValueError) as e:
                log_error(f"Error parsing tool response: {e}", "GeminiClient")
                tool_output = {
                    "success": False,
                    "message": f"Error parsing tool response: {e}",
                    "data": None
                }
                
            content_blocks.append({
                "type": "tool_response",
                "tool_response": {
                    "tool_call_id": tool_call_id,
                    "output": tool_output
                }
            })
            
        return {"role": "tool", "content": content_blocks}

    def create_conversation(
        self,
        system_prompt: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ) -> str:
        """Create a new conversation and return its ID."""
        # Use provided system prompt or fall back to default
        effective_system_prompt = system_prompt if system_prompt is not None else self.system_instruction
        
        return self.storage.create_conversation(
            model=self.model,
            system_prompt=effective_system_prompt,
            available_tools=available_tools
        ) 