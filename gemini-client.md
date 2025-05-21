# Gemini Client Design

This document outlines the design for a Gemini client to be integrated into the `prometheus-swarm` project.

## Overview

The `GeminiClient` will provide an interface to Google's Gemini models, similar to the existing clients for OpenAI, Anthropic, etc. It will handle message formatting, API calls, and tool usage according to the Gemini API specifications.

## Class Structure

The `GeminiClient` will inherit from the `Client` base class (`prometheus_swarm.clients.base_client.Client`).

```python
import google.generativeai as genai
from .base_client import Client
from ..types import (
    ToolDefinition,
    MessageContent,
    # ... other necessary types
)
import json # For handling arguments

class GeminiClient(Client):
    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        # ... any other Gemini-specific options
        **kwargs,
    ):
        super().__init__(model=model, **kwargs)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model) # Or however the Gemini client is initialized for chat
        # ...

    def _get_api_name(self) -> str:
        return "Gemini"

    def _get_default_model(self) -> str:
        # Choose a sensible default, e.g., "gemini-1.5-flash" or "gemini-pro"
        return "gemini-1.5-flash" # Or "gemini-pro" or other suitable default

    def _should_split_tool_responses(self) -> bool:
        # To be determined based on Gemini API specifics for tool/function calling.
        # Assume False for now, meaning tool responses can be grouped.
        return False

    def _convert_tool_to_api_format(self, tool: ToolDefinition) -> Dict[str, Any]:
        # Convert our ToolDefinition to Gemini's FunctionDeclaration format.
        # Reference: https://ai.google.dev/docs/function_calling
        # Example:
        # return genai.types.FunctionDeclaration(
        #     name=tool["name"],
        #     description=tool["description"],
        #     parameters={
        #         "type_": genai.types.SchemaType.OBJECT, # Corrected
        #         "properties": tool["parameters"]["properties"],
        #         "required": tool["parameters"].get("required", []),
        #     }
        # )
        # Simplified for now, assuming direct mapping. Details will depend on exact Gemini SDK types.
        return {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"], # This will need to be mapped to Gemini's schema objects
        }


    def _convert_message_to_api_format(self, message: MessageContent) -> Dict[str, Any]:
        # Convert our MessageContent to Gemini's Content format.
        # Role mapping: "user" -> "user", "assistant" -> "model", "tool" -> "function" (or "tool")
        # Content structure will vary based on text, tool calls, and tool responses.
        # Example:
        # role_map = {"user": "user", "assistant": "model", "tool": "function"} # "tool" might be "tool" or "function"
        # api_parts = []
        # if isinstance(message["content"], str):
        #     api_parts.append({"text": message["content"]})
        # else: # List of content blocks
        #     for block in message["content"]:
        #         if block["type"] == "text":
        #             api_parts.append({"text": block["text"]})
        #         elif block["type"] == "tool_call":
        #             # Convert to genai.types.FunctionCall
        #             api_parts.append(genai.types.Part.from_function_call(
        #                 name=block["tool_call"]["name"],
        #                 args=block["tool_call"]["arguments"]
        #             ))
        #         elif block["type"] == "tool_response":
        #             # Convert to genai.types.FunctionResponse
        #             api_parts.append(genai.types.Part.from_function_response(
        #                 name=block["tool_response"]["name"], # Need to get the original tool name
        #                 response={"content": block["tool_response"]["content"]} # Gemini expects a dict
        #             ))
        # return {"role": role_map.get(message["role"], "user"), "parts": api_parts}
        # Simplified for now.
        content = message["content"]
        role = message["role"]
        api_role = "user"
        if role == "assistant":
            api_role = "model"
        elif role == "tool":
            # This will need careful handling based on Gemini's tool response structure
            # For now, assuming tool responses are structured within the 'parts' list
            # and the role might still be 'user' or a special role for tool interactions.
            # Gemini uses 'function' role for function responses (tool responses).
            api_role = "function" # Or "tool" if that's what Gemini uses

        api_parts = []

        if isinstance(content, str):
            api_parts.append({"text": content})
        elif isinstance(content, list):
            for block in content:
                if block["type"] == "text":
                    api_parts.append({"text": block["text"]})
                elif block["type"] == "tool_call":
                    # This needs to be converted to Gemini's FunctionCall format
                    # genai.types.Part.from_function_call(name=..., args=...)
                    api_parts.append({
                        "function_call": {
                            "name": block["tool_call"]["name"],
                            "args": block["tool_call"]["arguments"] # Gemini expects dict
                        }
                    })
                elif block["type"] == "tool_response":
                    # This needs to be converted to Gemini's FunctionResponse format
                    # genai.types.Part.from_function_response(name=..., response=...)
                    # The 'name' here should be the original function name that was called.
                    # The 'response' should be a dict containing the result.
                    api_parts.append({
                        "function_response": {
                            "name": block["tool_response"]["name"], # Assuming 'name' is present in our ToolResponseContent
                            "response": {
                                "content": block["tool_response"]["content"] # Gemini expects a structured response
                            }
                        }
                    })
        return {"role": api_role, "parts": api_parts}


    def _convert_api_response_to_message(self, response: Any) -> MessageContent:
        # Convert Gemini's GenerateContentResponse to our MessageContent format.
        # Extract text and tool calls from response.candidates[0].content.parts
        # Example:
        # content_parts = []
        # for part in response.candidates[0].content.parts:
        #     if part.text:
        #         content_parts.append({"type": "text", "text": part.text})
        #     elif part.function_call:
        #         content_parts.append({
        #             "type": "tool_call",
        #             "tool_call": {
        #                 "id": part.function_call.name, # Gemini might not provide a separate ID like OpenAI. Use name as ID for now.
        #                 "name": part.function_call.name,
        #                 "arguments": dict(part.function_call.args), # Convert from FunctionCall.Args (mapping) to dict
        #             },
        #         })
        # return {"role": "assistant", "content": content_parts}
        # Simplified for now.
        api_content_parts = []
        gemini_response_content = response.candidates[0].content

        for part in gemini_response_content.parts:
            if hasattr(part, "text") and part.text:
                api_content_parts.append({"type": "text", "text": part.text})
            elif hasattr(part, "function_call") and part.function_call:
                # Gemini's function_call.args is a google.protobuf.struct_pb2.Struct
                # We need to convert it to a dict.
                args_dict = {}
                if part.function_call.args:
                    for key, value in part.function_call.args.items():
                        # This might need more sophisticated handling for different value types
                        args_dict[key] = value

                api_content_parts.append({
                    "type": "tool_call",
                    "tool_call": {
                        # Gemini uses the function name as the identifier for the call.
                        # We might need a unique ID if multiple calls to the same tool are made.
                        # For now, using the name as the ID.
                        "id": part.function_call.name, # Consider generating a unique ID if needed
                        "name": part.function_call.name,
                        "arguments": args_dict,
                    },
                })
        return {"role": "assistant", "content": api_content_parts}


    def _convert_tool_choice_to_api_format(
        self, tool_choice: ToolChoice # Our ToolChoice type
    ) -> Any: # Gemini's tool_config (genai.types.ToolConfig)
        # Convert our ToolChoice to Gemini's tool_config.
        # "optional" -> mode AUTO / ANY
        # "required" (specific tool) -> mode FUNCTION, with the specified function name
        # Reference: https://ai.google.dev/docs/function_calling
        # Example:
        # if tool_choice["type"] == "optional":
        #     return genai.types.ToolConfig(
        #         function_calling_config=genai.types.FunctionCallingConfig(
        #             mode=genai.types.FunctionCallingConfig.Mode.ANY # or AUTO
        #         )
        #     )
        # elif tool_choice["type"] == "required" and tool_choice.get("tool"):
        #     return genai.types.ToolConfig(
        #         function_calling_config=genai.types.FunctionCallingConfig(
        #             mode=genai.types.FunctionCallingConfig.Mode.ANY, # or FUNCTION if only one
        #             allowed_function_names=[tool_choice["tool"]]
        #         )
        #     )
        # else: # "none" or unhandled
        #     return None # Or default configuration for no tools
        # Simplified for now.
        if tool_choice["type"] == "optional":
            # Gemini's equivalent might be 'AUTO' or 'ANY' mode for function calling
            return {"function_calling_config": {"mode": "ANY"}} # Or "AUTO"
        elif tool_choice["type"] == "required" and tool_choice.get("tool"):
            # Gemini allows specifying allowed function names
            return {
                "function_calling_config": {
                    "mode": "ANY", # Or "FUNCTION" if we want to force this specific tool
                    "allowed_function_names": [tool_choice["tool"]]
                }
            }
        return None # Default: Gemini decides or no tools explicitly.


    def _make_api_call(
        self,
        messages: List[Dict[str, Any]], # Already converted by _convert_message_to_api_format
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None, # Already converted by _convert_tool_to_api_format
        tool_choice: Optional[Any] = None, # Already converted by _convert_tool_choice_to_api_format
        extra_headers: Optional[Dict[str, str]] = None, # Gemini SDK might not support custom headers directly
    ) -> Any: # Gemini's GenerateContentResponse
        # Construct history from messages.
        # Handle system prompt (Gemini might take it as a special first message or a parameter).
        # Make the call: self.client.generate_content(contents=..., tools=..., tool_config=...)
        # `tools` will be a list of `genai.types.Tool` (which contains FunctionDeclarations)
        # `tool_config` will be `genai.types.ToolConfig`

        generation_config = {}
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
            # generation_config["candidate_count"] = 1 # Default
            # generation_config["temperature"] = ... # Add if needed

        # Prepare tools for Gemini API
        gemini_tools = None
        if tools:
            # Each tool from `_convert_tool_to_api_format` needs to be wrapped in `genai.types.Tool`
            # For now, assume `tools` contains `FunctionDeclaration`-like dicts
            # gemini_tools = [genai.types.Tool(function_declarations=[t]) for t in tools]
            # Simplified for now, will use actual SDK types in implementation
             gemini_tools_declarations = []
             for t_dict in tools:
                 # This needs to be converted to genai.types.FunctionDeclaration
                 # Placeholder for now, assuming direct use of dict might work or needs mapping
                 gemini_tools_declarations.append(t_dict)
             if gemini_tools_declarations:
                gemini_tools = [{"function_declarations": gemini_tools_declarations}]


        # The `messages` are already in Gemini format.
        # Gemini API expects `contents` which is the list of messages.
        # System prompt handling: Gemini prefers system instructions at the start of the `contents` list
        # or via a specific `system_instruction` parameter if available in the SDK version.
        api_messages = messages
        if system_prompt:
            # Prepend system instruction as a user message, or use dedicated field if SDK supports
            # For multi-turn, system instructions are typically at the start.
            # Gemini's `GenerativeModel` can take `system_instruction` at initialization
            # or `generate_content` can take it.
            # Let's assume we might need to pass it to `generate_content` if not set at model init.
            # For now, we will not explicitly pass system_prompt to generate_content,
            # assuming it's handled by the `Client` base class or set during model init.
            # If the SDK supports a `system_instruction` field in `generate_content`, use it.
            # Otherwise, it might be part of the `contents`.
            # Current Gemini Python SDK (google.generativeai) takes system_instruction in GenerativeModel(...)
            # For this PoC, let's assume it's handled if passed to __init__ or needs to be first message.
            # If a system message is needed for `generate_content` specifically, it should be formatted as a message.
            # The base client logic might already prepend it to `messages`.
            pass


        response = self.client.generate_content(
            contents=api_messages,
            tools=gemini_tools, # List of genai.types.Tool
            tool_config=tool_choice, # genai.types.ToolConfig
            generation_config=genai.types.GenerationConfig(**generation_config) if generation_config else None,
        )
        return response # This is a GenerateContentResponse

    def _format_tool_response(
        self,
        tool_call_id: str, # ID of the tool call this response is for. Gemini might use name.
        response: str,      # The stringified JSON response from the tool.
        tool_name: str,     # The name of the tool that was called.
    ) -> MessageContent:
        # Format the tool execution result back into a message that Gemini API understands.
        # This will likely be a "function" role message containing a FunctionResponse part.
        # The `response` string needs to be parsed (if JSON) and structured correctly.
        # Gemini expects the response part to have `name` (original function name) and `response` (a dict).

        # The base_client.py expects this method to return a MessageContent.
        # The `tool_call_id` from our system might be the `tool_name` if Gemini doesn't use separate IDs.
        # The `response` is the actual content from the tool.
        # The `tool_name` is the function that was called.

        # Gemini's FunctionResponse part requires:
        # - name: The name of the function that was called.
        # - response: A dict containing the "content" of the response.
        #   e.g., {"content": "tool output string or structured data"}

        # Our `MessageContent` for a tool response needs to be transformed into
        # Gemini's `Content` with a `Part` of type `FunctionResponse`.
        # This method's output will be passed to `_convert_message_to_api_format`.

        # What this method should actually return is OUR internal `MessageContent` format
        # for a tool *response*.
        return {
            "role": "tool", # Our internal role for tool responses
            "content": [
                {
                    "type": "tool_response",
                    "tool_response": {
                        "tool_call_id": tool_call_id, # This ID should match the one from the tool_call
                        "name": tool_name, # Gemini needs the name of the function for its FunctionResponse part
                        "content": response, # The actual content from the tool execution
                    },
                }
            ],
        }

    # Any other Gemini-specific helper methods
    # ...

```

## Dependencies

- `google-generativeai`

## Tool Calling (Function Calling)

Gemini supports function calling, which is analogous to OpenAI's tool usage. The implementation will need to:
1.  Convert `ToolDefinition` from our format to Gemini's `FunctionDeclaration` and `Tool` schema.
2.  Process `tool_choice` to set Gemini's `tool_config` (e.g., mode AUTO, ANY, FUNCTION).
3.  When the model returns a `FunctionCall`, extract its `name` and `args`.
4.  Format the tool's execution result as a `FunctionResponse` part and send it back to the model.

## Message Formatting

-   **Roles**: Map our internal roles (`user`, `assistant`, `tool`) to Gemini's roles (`user`, `model`, `function`). The `system` role might be handled by a `system_instruction` parameter in the `GenerativeModel` or as the first message in the `contents` list.
-   **Content**: Messages can contain text and tool-related parts (`FunctionCall`, `FunctionResponse`). Our `MessageContent` will be converted to a list of Gemini `Part` objects.

## Error Handling

Implement robust error handling for API calls, including rate limits, authentication issues, and invalid requests.

## Testing Considerations

-   Basic chat completion.
-   Chat completion with system prompt.
-   Single tool call and response.
-   Multiple tool calls in one turn (if supported by Gemini and our framework).
-   `tool_choice` variations: "optional", "required", "none".
-   Error handling for invalid API key or model.

## Future Considerations

-   Streaming responses.
-   Image/multi-modal inputs if supported by the chosen Gemini model and relevant to `prometheus-swarm`.
-   Fine-tuning specific Gemini parameters (`temperature`, `top_p`, `top_k`, etc.) via `generation_config`.

## Open Questions / To-Do:

1.  **`_should_split_tool_responses`**: Verify if Gemini requires tool responses to be sent individually or if they can be batched in a single "function" role message with multiple `FunctionResponse` parts. Assuming `False` (batched allowed) for now.
2.  **Tool Call ID**: Gemini's `FunctionCall` in the response uses `name`. If multiple calls to the *same* tool are possible in one turn, how are they distinguished? Our system uses a `tool_call_id`. We may need to generate unique IDs if Gemini doesn't provide them and map them back. For now, assuming `name` is used as the primary identifier from Gemini.
3.  **`tool_response.name`**: The `_convert_message_to_api_format` for `tool_response` currently uses `block["tool_response"]["name"]`. Ensure our `ToolResponseContent` type includes this `name` field, which should be the name of the function that was called.
4.  **Gemini SDK types**: Replace dictionary placeholders in conversion methods with actual `genai.types` objects (e.g., `FunctionDeclaration`, `Tool`, `ToolConfig`, `Part`, `Content`, `Schema`) for type safety and correctness.
5.  **System Prompt**: Confirm the best way to pass system prompts (via `GenerativeModel(system_instruction=...)` or as the first message in `contents`). The base client's `_prepare_chat_kwargs` might handle this.
6.  **Argument Serialization**: Gemini's `FunctionCall.args` is a `Struct`. Ensure conversion to/from Python dicts is handled correctly, especially for complex nested parameters. `json.dumps` might be needed for string arguments if the schema expects strings. The `parameters` in `FunctionDeclaration` should use Gemini's `Schema` objects.
7. **`google-generativeai` installation**: This will need to be added to `requirements.txt`.

This design provides a starting point. The implementation details will be refined by consulting the latest `google-generativeai` Python SDK documentation. 