# Gemini Tool Calling Tests

This directory contains tests and utilities for working with Google's Gemini models via the `GeminiClient` implementation in prometheus-swarm.

## Overview

These tests focus on exploring and resolving challenges with Gemini API's tool calling capabilities, particularly with regard to:

1. Rate limiting issues with Pro models
2. Tool calling reliability differences between model tiers
3. Implementation of robust retry and fallback strategies

## Key Files

- **`test_custom_gemini_client_tool_call.py`**: Tests the enhanced `GeminiClient` with retry logic for `ResourceExhausted` errors
- **`test_gemini_fallback_strategy.py`**: Implements and tests a model fallback strategy for more reliable tool calling
- **`gemini_models_reference.md`**: Reference documentation on Gemini models and their tool calling capabilities
- **`testing_procedure.md`**: Overview of the testing approach and methodology

## Findings Summary

1. **Rate Limits**: Gemini Pro models frequently hit rate limits (`ResourceExhausted` errors) on free tier, requiring retry strategies
2. **Model Capabilities**: Pro models are most reliable for tool calling but most susceptible to rate limits
3. **Flash Models**: Less likely to hit rate limits but less reliable for making tool calls
4. **Retry Logic**: Even with retry logic, persistent rate limits can occur with Pro models
5. **Fallback Strategy**: A tiered approach starting with Pro models and falling back to Flash models shows the most promise

## Usage

### Running the Tests

1. Create a `.env` file at the project root with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

2. Install the package in development mode:
   ```
   pip install -e .
   ```

3. Run the tests:
   ```
   cd llm-agent-tests/gemini
   python test_custom_gemini_client_tool_call.py
   python test_gemini_fallback_strategy.py
   ```

### Using the FallbackGeminiClient

The `FallbackGeminiClient` class in `test_gemini_fallback_strategy.py` provides a robust implementation that:

1. Attempts to use Pro models first (best for tool calling)
2. Falls back to Flash models when rate limits are hit
3. Checks if models actually make the required tool calls
4. Can be adapted for production use

Example usage:

```python
from path.to.fallback_client import FallbackGeminiClient

# Create the client
client = FallbackGeminiClient(
    api_key="your_api_key",
    system_instruction="You are a helpful assistant that uses tools."
)

# Register your tools
client.register_tool(your_tool_definition)

# Send messages with automatic fallback handling
response = client.send_message("Use the tool to classify this repository")
```

## Future Improvements

- Implementation of exponential backoff for retries
- Addition of adaptive tool prompt optimization
- Integration with paid API tiers to avoid rate limits
- Testing with newer Gemini model versions as they become available 