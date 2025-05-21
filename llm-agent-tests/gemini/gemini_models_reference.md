# Gemini Models Reference Guide

This document summarizes the different Gemini models available, their capabilities with tool calling, and rate limits to consider when implementing the `GeminiClient` in prometheus-swarm.

## Available Models

### Gemini 1.5 Models

| Model Name | Tool Calling | Description | Free Tier Limits | Notes |
|------------|-------------|-------------|-----------------|-------|
| `gemini-1.5-pro-latest` | ✅ | Latest version of 1.5 Pro | Strict rate limits | Most capable for tool calling but frequently hits `ResourceExhausted` errors |
| `gemini-1.5-pro` | ✅ | Stable version of 1.5 Pro | Strict rate limits | Same rate limiting issues as latest |
| `gemini-1.5-flash-latest` | ✅ | Latest version of 1.5 Flash | Less strict limits | May be less reliable for tool calls but avoids rate limits |
| `gemini-1.5-flash` | ✅ | Stable version of 1.5 Flash | Less strict limits | Balance of reliability and rate limits |

### Gemini 2.0 Models (Preview)

| Model Name | Tool Calling | Description | Free Tier Limits | Notes |
|------------|-------------|-------------|-----------------|-------|
| `gemini-2.0-pro` | ✅ | Preview of 2.0 Pro | Very strict limits | Limited access in preview |
| `gemini-2.0-flash` | ✅ | Preview of 2.0 Flash | Moderate limits | Inconsistent tool calling behavior |
| `gemini-2.0-flash-lite` | ⚠️ | Lightweight 2.0 Flash | Least strict limits | Rarely makes tool calls despite capability |

## Rate Limit Observations

- **Pro models**: The most capable but hit `ResourceExhausted` errors frequently on the free tier
- **Flash models**: Less likely to hit rate limits but less reliable for tool calling
- **Rate limit recovery**: Even with retry logic, persistent rate limits can occur with Pro models
- **Delay requirements**: Delays of 60+ seconds are often needed between retries for Pro models

## Tool Calling Recommendations

1. **For development/testing**:
   - Use `gemini-1.5-flash-latest` with explicit tool calling instructions
   - Configure `max_retries_on_exhaustion=3` and `retry_delay_seconds=60`
   - Optimize prompts to be extremely explicit about tool calls

2. **For production**:
   - Consider using Google Cloud with API quotas that avoid rate limits
   - Fall back to Flash models when rate limits are encountered with Pro models
   - Implement exponential backoff for retries

3. **Prompt Engineering for Tool Calls**:
   - Be extremely explicit about the tool to use
   - Format prompt to emphasize that a tool call is required
   - Include examples of correct tool call formats if possible

## Client Configuration Best Practices

```python
# Example for development environment with retry logic
client = GeminiClient(
    api_key=api_key,
    model="gemini-1.5-flash-latest",
    max_retries_on_exhaustion=3,
    retry_delay_seconds=60,
    system_instruction="You are a helpful AI assistant. When a tool is available, always use it rather than responding directly."
)

# Example for production environment with fallback
try:
    client = GeminiClient(
        api_key=api_key,
        model="gemini-1.5-pro-latest",
        max_retries_on_exhaustion=5,
        retry_delay_seconds=90
    )
    # Attempt operation with Pro model
except ClientAPIError as e:
    if isinstance(e.original_exception, ResourceExhausted):
        # Fallback to Flash model
        client = GeminiClient(
            api_key=api_key,
            model="gemini-1.5-flash-latest",
            max_retries_on_exhaustion=2,
            retry_delay_seconds=30
        )
```

## Future Considerations

- Monitor the Gemini 2.0 models as they mature out of preview
- Consider implementing adaptive retry logic that increases delay times automatically
- Explore multi-model strategies that balance rate limits and tool calling capabilities 