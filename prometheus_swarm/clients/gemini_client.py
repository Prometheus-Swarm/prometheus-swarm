"""Gemini API client implementation."""

from typing import Dict, Any, Optional, List, Union
import json
import ast # For literal_eval
import google.generativeai as genai
from google.generativeai.types import (
    Tool as GeminiTool,
    FunctionDeclaration,
    Schema as GeminiSchema,
    Type as GeminiType,
    StructType, # For protobuf struct to dict
    FunctionCallingConfig,
    Content,
    Part,
    GenerationConfig,
    GenerateContentResponse
)
from google.protobuf.struct_pb2 import Struct # For type hinting Struct
from .base_client import Client
from ..types import (
    ToolDefinition,
    MessageContent,
    TextContent,
    ToolCallContent,
    ToolResponseContent, # Correctly imported
    ToolResponse,      # For type hinting within conversion
    ToolOutput,        # For type hinting within conversion
    ToolChoice,
    ToolCall,
)
from prometheus_swarm.utils.logging import log_error, log_key_value
from prometheus_swarm.utils.errors import ClientAPIError


# Helper to convert protobuf Struct to Python dict
def _protobuf_struct_to_dict(struct_pb: Optional[Struct]) -> Dict[str, Any]:
    """Converts a google.protobuf.struct_pb2.Struct to a Python dictionary."""
    if not struct_pb:
        return {}
    # Using _pb field to get the underlying protobuf message, then converting
    # This is a common pattern if a direct to_dict() is not available or suitable
    # For google.protobuf.struct_pb2.Struct, it behaves like a dict
    return dict(struct_pb)


# Helper to map our JSON schema types to Gemini's Schema types
def _map_json_type_to_gemini_type(json_type: str) -> GeminiType:
    type_map = {
        "string": GeminiType.STRING,
        "number": GeminiType.NUMBER,
        "integer": GeminiType.INTEGER,
        "boolean": GeminiType.BOOLEAN,
        "array": GeminiType.ARRAY,
        "object": GeminiType.OBJECT,
    }
    gemini_type = type_map.get(json_type.lower())
    if gemini_type is None:
        log_key_value(f"Warning: Unsupported JSON type '{json_type}', defaulting to STRING.", "GeminiClient")
        return GeminiType.STRING # Default or raise error
    return gemini_type


class GeminiClient(Client):
    """Gemini API client implementation."""

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None, # Gemini specific
        **kwargs,
    ):
        super().__init__(model=model, **kwargs)
        genai.configure(api_key=api_key)
        
        # Store system_instruction to be passed to GenerativeModel
        self.system_instruction = system_instruction
        
        # Initialize the model
        self._initialize_model()

    def _initialize_model(self):
        """Initializes or re-initializes the GenerativeModel client."""
        model_kwargs = {}
        if self.system_instruction:
            # Convert system_instruction string to Content object if needed, or pass directly
            # Assuming system_instruction is passed as a simple string for now
            # The SDK might expect a specific format like genai.protos.Content
             model_kwargs["system_instruction"] = self.system_instruction


        self.client = genai.GenerativeModel(
            model_name=self.model, 
            **model_kwargs
        )
        # Start a chat session if the model supports it (for multi-turn)
        # Some Gemini models might be better with chat.start_chat() for history management
        # For now, we'll pass history directly to generate_content
        # self.chat = self.client.start_chat(history=[]) 


    def _get_api_name(self) -> str:
        """Get API name for logging."""
        return "Gemini"

    def _get_default_model(self) -> str:
        """Get the default model for this API."""
        return "gemini-1.5-flash-latest" # Or a more general one like "gemini-pro"

    def _should_split_tool_responses(self) -> bool:
        """Gemini can handle multiple tool responses in one message."""
        return False

    def _convert_tool_to_api_format(self, tool: ToolDefinition) -> FunctionDeclaration:
        """Convert our tool definition to Gemini's FunctionDeclaration format."""
        
        def convert_properties(properties: Dict[str, Any]) -> Dict[str, GeminiSchema]:
            gemini_props = {}
            for key, value in properties.items():
                param_type = value.get("type", "string")
                gemini_props[key] = GeminiSchema(
                    type=_map_json_type_to_gemini_type(param_type),
                    description=value.get("description"),
                    # TODO: Handle nested properties, arrays (items), enums etc.
                )
            return gemini_props

        parameters_schema = tool.get("parameters", {})
        
        # Ensure properties is a dictionary
        properties_dict = parameters_schema.get("properties")
        if not isinstance(properties_dict, dict):
            properties_dict = {} # Default to empty if not a dict

        required_list = parameters_schema.get("required")
        if not isinstance(required_list, list):
            required_list = [] # Default to empty if not a list

        return FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=GeminiSchema(
                type=GeminiType.OBJECT,
                properties=convert_properties(properties_dict),
                required=required_list,
            )
        )

    def _convert_message_to_api_format(self, message: MessageContent) -> Content:
        """Convert our message format to Gemini's Content format."""
        role = message["role"]
        content = message["content"]

        api_role = "user"  # Default
        if role == "assistant":
            api_role = "model"
        elif role == "tool":
            api_role = "function" # Gemini uses "function" for tool responses

        api_parts: List[Part] = []

        if isinstance(content, str):
            api_parts.append(Part(text=content))
        elif isinstance(content, list):
            for block in content:
                if block["type"] == "text":
                    api_parts.append(Part(text=block["text"]))
                elif block["type"] == "tool_call":
                    # Our ToolCallContent -> Gemini FunctionCall Part
                    fc_block = block["tool_call"]
                    # Gemini expects args as a dict. Ensure it is.
                    args = fc_block["arguments"]
                    if not isinstance(args, dict):
                        try:
                            args = json.loads(str(args)) # Attempt to parse if stringified JSON
                        except json.JSONDecodeError:
                            log_error(f"Failed to parse tool arguments for {fc_block['name']}: {args}", "GeminiClient")
                            args = {} # Default to empty dict on error
                            
                    api_parts.append(Part(function_call=genai.types.FunctionCall(
                        name=fc_block["name"],
                        args=args 
                    )))
                elif block["type"] == "tool_response":
                    # Our ToolResponseContent -> Gemini FunctionResponse Part
                    fr_block = block["tool_response"]
                    
                    # Ensure the response content is a dict as expected by Gemini
                    response_content = fr_block["content"]
                    if isinstance(response_content, str):
                        try:
                            # Attempt to parse if it's a JSON string
                            parsed_response_content = json.loads(response_content)
                        except json.JSONDecodeError:
                            # If not JSON, wrap it in a standard way, e.g. {"text_response": ...}
                            # Or, if it's meant to be a simple string, Gemini might still expect a dict.
                            # For now, let's assume the tool function in base_client returns a JSON string
                            # which represents a dictionary. If it's just a plain string, this might need adjustment.
                            log_key_value(f"Warning: Tool response content for {fr_block['name']} is a string, attempting to parse as JSON.", "")
                            parsed_response_content = {"result": response_content} # Default wrapping
                    elif isinstance(response_content, dict):
                        parsed_response_content = response_content
                    else: # Neither string nor dict, try to convert to string and wrap
                         parsed_response_content = {"result": str(response_content)}


                    api_parts.append(Part(function_response=genai.types.FunctionResponse(
                        name=fr_block["name"], # This should be the name of the function that was called
                        response={"content": parsed_response_content} # Gemini expects a dict, often {"content": actual_tool_output}
                    )))
        
        return Content(role=api_role, parts=api_parts)

    def _convert_api_response_to_message(self, response: GenerateContentResponse) -> MessageContent:
        """Convert Gemini's API response to our MessageContent format."""
        content_list: List[Union[TextContent, ToolCallContent]] = []

        if not response.candidates:
            log_error("Gemini API response has no candidates.", "GeminiClient")
            # Return a message indicating no response or an error
            return {"role": "assistant", "content": [{"type": "text", "text": "Error: No response from API."}]}

        # Assuming the first candidate is the one we want
        gemini_content = response.candidates[0].content
        
        for part in gemini_content.parts:
            if part.text:
                content_list.append({"type": "text", "text": part.text})
            elif hasattr(part, 'function_call') and part.function_call:
                fc = part.function_call
                # Convert Struct to dict for arguments
                args_dict = _protobuf_struct_to_dict(fc.args)
                
                content_list.append({
                    "type": "tool_call",
                    "tool_call": {
                        # Gemini uses the function name as its identifier.
                        # We use this name for both id and name for consistency with our types.
                        "id": fc.name, 
                        "name": fc.name,
                        "arguments": args_dict,
                    },
                })
        
        return {"role": "assistant", "content": content_list}

    def _convert_tool_choice_to_api_format(
        self, tool_choice: ToolChoice
    ) -> Optional[FunctionCallingConfig]:
        """Convert our tool choice format to Gemini's FunctionCallingConfig."""
        # Based on https://ai.google.dev/docs/function_calling#define-tools-and-toolconfig
        # And https://ai.google.dev/api/python/google/generativeai/types/FunctionCallingConfig
        
        mode_map = {
            "optional": FunctionCallingConfig.Mode.ANY, # ANY: model can call one or more functions
            "required": FunctionCallingConfig.Mode.ANY, # ANY allows specifying allowed_function_names
                                                        # If we want to force *a* tool, but not specific, it's ANY.
                                                        # If we want to force a *specific* tool, we set allowed_function_names.
            "none": FunctionCallingConfig.Mode.NONE, # Model will not call any functions
        }

        fc_type = tool_choice.get("type", "optional") # Default to optional
        mode = mode_map.get(fc_type)
        
        if mode is None: # Should not happen if ToolChoice is validated
            log_error(f"Invalid tool choice type: {fc_type}", "GeminiClient")
            return None 

        if fc_type == "required" and tool_choice.get("tool"):
            # If a specific tool is required, set it in allowed_function_names
            return FunctionCallingConfig(
                mode=FunctionCallingConfig.Mode.ANY, # Still ANY, but filtered
                allowed_function_names=[tool_choice["tool"]]
            )
        elif fc_type == "none":
             return FunctionCallingConfig(mode=FunctionCallingConfig.Mode.NONE)
        elif fc_type == "optional": # Default to ANY mode
            return FunctionCallingConfig(mode=FunctionCallingConfig.Mode.ANY)

        # Default or unhandled cases
        return None


    def _make_api_call(
        self,
        messages: List[Content], # Already converted by _convert_message_to_api_format
        system_prompt: Optional[str] = None, # Handled at model initialization for Gemini
        max_tokens: Optional[int] = None,
        tools: Optional[List[FunctionDeclaration]] = None, # Already converted
        tool_choice: Optional[FunctionCallingConfig] = None, # Already converted
        extra_headers: Optional[Dict[str, str]] = None, # Gemini SDK does not use this directly
    ) -> GenerateContentResponse:
        """Make API call to Gemini."""
        
        generation_config_args = {}
        if max_tokens is not None:
            generation_config_args["max_output_tokens"] = max_tokens
        # Add other generation parameters like temperature, top_p, top_k if needed
        # generation_config_args["temperature"] = 0.7 
        
        final_generation_config = GenerationConfig(**generation_config_args) if generation_config_args else None

        # Prepare tools for Gemini API if they exist
        gemini_tools_list = None
        if tools:
            # Each FunctionDeclaration needs to be wrapped in a GeminiTool object
            gemini_tools_list = [GeminiTool(function_declarations=tools)] # Pass the list of FunctionDeclarations

        # The `system_prompt` is handled during `GenerativeModel` initialization via `self.system_instruction`.
        # If `system_prompt` is passed here and differs from `self.system_instruction`,
        # it might indicate a need to re-initialize the model or handle it differently.
        # For now, we assume system instructions are static per client instance.
        if system_prompt and system_prompt != self.system_instruction:
            log_key_value("Warning: system_prompt in _make_api_call differs from initial system_instruction. Re-initializing model.", "GeminiClient")
            self.system_instruction = system_prompt
            self._initialize_model() # Re-initialize with new system instruction


        try:
            # `messages` is already a list of `Content` objects
            response = self.client.generate_content(
                contents=messages,
                tools=gemini_tools_list,
                tool_config=tool_choice,
                generation_config=final_generation_config,
            )
            return response
        except Exception as e:
            # Catch specific Gemini API errors if possible, or general exceptions
            log_error(e, f"Error during Gemini API call to model {self.model}", include_traceback=True)
            # Convert to a ClientAPIError for consistent error handling in the base class
            raise ClientAPIError(f"Gemini API Error: {str(e)}", original_exception=e)


    def _format_tool_response(
        self, 
        tool_call_id: str, # ID of the tool call this response is for. For Gemini, this is the tool name.
        response: str,      # The stringified JSON response from the tool.
        tool_name: str,     # The name of the tool that was called. (Redundant if tool_call_id is name)
    ) -> MessageContent:
        """Format a tool execution result into our internal MessageContent format."""
        # This method is called by the base client to wrap the raw tool output (a string, usually JSON)
        # into the standard MessageContent structure that will then be converted by
        # _convert_message_to_api_format before sending back to the LLM.

        # `tool_name` is the name of the function that was called.
        # `tool_call_id` in our system is usually the unique ID of the call, which for Gemini
        # seems to correspond to the `tool_name` from the `FunctionCall` part.

        # The `response` is the raw string output from the tool execution.
        # It's expected to be a string, often JSON, as per base_client.py `execute_tool`
        
        # Ensure response content matches what _convert_message_to_api_format expects for tool_response
        # Our internal format for a tool response block:
        return {
            "role": "tool", 
            "content": [
                {
                    "type": "tool_response",
                    "tool_response": {
                        "tool_call_id": tool_call_id, # Should match the ID from the assistant's tool_call
                        "name": tool_name, # Name of the function, Gemini needs this for its FunctionResponse
                        "content": response, # The actual content from the tool (string, typically JSON)
                    },
                }
            ],
        }

    # Override register_tools to pass system_prompt if it was provided at init
    def create_conversation(
        self,
        system_prompt: Optional[str] = None, # This can be passed by user
        available_tools: Optional[List[str]] = None,
    ) -> str:
        """Create a new conversation and return its ID."""
        # If a system_prompt is provided here, it overrides the client's default
        # If not provided, use the client's default system_instruction
        effective_system_prompt = system_prompt if system_prompt is not None else self.system_instruction
        
        # If the effective_system_prompt for this conversation is different from the current model's
        # system instruction, we might need to consider how to handle it.
        # For now, the base class ConversationManager stores this system_prompt per conversation.
        # The Gemini client uses its self.system_instruction for model initialization.
        # If a conversation specific system_prompt is to be used, it should be passed to _make_api_call.
        # The base client's send_message gets it from storage and passes it.
        # Our _make_api_call checks if this differs and re-initializes the model.

        return self.storage.create_conversation(
            model=self.model,
            system_prompt=effective_system_prompt, # Use the resolved system prompt
            available_tools=available_tools,
        ) 