# Testing Procedure for Custom Gemini Client Adaptations

This document outlines the plan to test adaptations made to the `prometheus_swarm.clients.gemini_client.py`.

## Plan Steps

1.  **Modify `prometheus_swarm/clients/gemini_client.py`**:
    *   Implement robust retry logic within the `_make_api_call` method specifically for `ResourceExhausted` errors.
    *   This includes adding parameters for `max_retries_on_exhaustion` and `retry_delay_seconds`.
    *   The retry loop will catch `ResourceExhausted`, log the event, wait for `retry_delay_seconds`, and then `continue` to the next attempt.
    *   Other exceptions will be handled as before or re-raised as `ClientAPIError`.

2.  **Create a New Test Script (`test_custom_gemini_client_tool_call.py`)**:
    *   This script will be located in the `llm-agent-tests/gemini/` folder.
    *   It will be a `unittest.TestCase`.
    *   It will directly import and use the `GeminiClient` from `prometheus_swarm.clients.gemini_client` (not relying on LangChain's `ChatGoogleGenerativeAI` for this specific test).
    *   **Setup**: The `setUp` method will:
        *   Load environment variables (for `GEMINI_API_KEY`).
        *   Instantiate `GeminiClient` with the API key and a target model (e.g., `gemini-1.5-pro-latest` to specifically test the retry logic, or a Flash model if rate limits are still a concern).
    *   **Test Method**: A test method (e.g., `test_classify_repository_tool_call`) will:
        *   Define a sample list of messages (e.g., a user prompt like "Use the classify_repository tool to classify this repository as a web application.").
        *   Define the `classify_repository` tool using `ToolDefinition` format expected by the client.
        *   Call the appropriate public method of `GeminiClient` (likely `get_completion` or a similar method that internally uses `_make_api_call`) to get a response, passing the messages and the tool definition.
        *   **Assertions**:
            *   Verify that the call completes, even if it initially hits a (mocked or real) `ResourceExhausted` error and retries.
            *   If the call is successful (and doesn't just error out), assert that a tool call to `classify_repository` was made.
            *   Assert that the arguments for the tool call are as expected (e.g., `{'repo_type': 'web_application'}`).

3.  **Execute the New Test Script**:
    *   Run `test_custom_gemini_client_tool_call.py`.

4.  **Report and Analyze Results**:
    *   If the test passes, it indicates the retry logic in `GeminiClient` is functioning and the client can successfully facilitate a tool call with the chosen model.
    *   If the test fails:
        *   Due to `ResourceExhausted` errors even after retries: This would mean the retry parameters (delay/attempts) are still insufficient for the current API quota, or the quota is extremely restrictive.
        *   Due to `AssertionError` (no tool call made): This would point to issues with how the model (even via the custom client) is interpreting the prompt or the tool definition, similar to what was observed with Flash models via LangChain.
        *   Due to other errors: These would need to be investigated based on the error message.
    *   Detail the outcome and any reasons for failure. 