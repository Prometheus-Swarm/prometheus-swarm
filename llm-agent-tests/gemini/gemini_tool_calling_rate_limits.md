# Gemini Models: Tool Calling Capabilities and Free Tier Rate Limits

This document summarizes the Free Tier rate limits for various Gemini models and discusses their general tool-calling capabilities. Rate limits are sourced from [https://ai.google.dev/gemini-api/docs/rate-limits#free-tier](https://ai.google.dev/gemini-api/docs/rate-limits#free-tier).

Tool calling (also known as function calling) is a core feature of most Gemini models, allowing them to interact with external tools and APIs. However, the proficiency and reliability of tool calling can vary between models, especially with lighter or experimental versions.

| Model                                     | RPM | TPM                        | RPD    | Tool Calling Notes                                                                 |
| ----------------------------------------- | --- | -------------------------- | ------ | ---------------------------------------------------------------------------------- |
| Gemini 2.5 Flash Preview 05-20            | 10  | 250,000                    | 500    | Expected to support tool calling. Preview models might have evolving capabilities. |
| Gemini 2.5 Pro Preview 05-06              | --  | --                         | --     | Expected to support tool calling. Limits are not specified for the Free Tier.      |
| Gemini 2.5 Pro Experimental 03-25         | 5   | 250,000 TPM  1,000,000 TPD | 25     | Expected to support tool calling. Experimental models may have varying reliability.| 
| Gemini 2.0 Flash                          | 15  | 1,000,000                  | 1,500  | Supports tool calling.                                                             |
| Gemini 2.0 Flash Preview Image Generation | 10  | 200,000                    | 100    | Primarily for image generation; tool calling for other tasks might be secondary.   |
| Gemini 2.0 Flash Experimental             | 10  | 1,000,000                  | 1,000  | Expected to support tool calling. Experimental models may have varying reliability.| 
| Gemini 2.0 Flash-Lite                     | 30  | 1,000,000                  | 1,500  | Supports tool calling (as observed, though may require explicit prompting).        |
| Gemini 1.5 Flash                          | 15  | 250,000                    | 500    | Supports tool calling.                                                             |
| Gemini 1.5 Flash-8B                       | 15  | 250,000                    | 500    | Supports tool calling.                                                             |
| Gemini 1.5 Pro                            | --  | --                         | --     | Supports tool calling (this is the model we initially tried, `gemini-1.5-pro-latest`). Limits are not specified for the Free Tier, and we experienced rate limiting. |
| Veo 2                                     | --  | --                         | --     | Primarily a video generation model; general tool calling capabilities unclear.     |
| Imagen 3                                  | --  | --                         | --     | Primarily an image generation model; general tool calling capabilities unclear.    |

**Observations from recent testing:**
*   `gemini-1.5-pro-latest` consistently hit `ResourceExhausted` errors, suggesting its effective Free Tier limits are restrictive or were quickly met, despite "--" in the rate limit table for the generic "Gemini 1.5 Pro".
*   `gemini-2.0-flash-lite` did not hit rate limits in initial tests but failed to make a tool call with a less explicit prompt, suggesting it might require more direct prompting for tool usage or could be less adept at it compared to Pro models.

**Note:**
*   RPM = Requests Per Minute
*   TPM = Tokens Per Minute
*   RPD = Requests Per Day
*   "--" indicates that the limits are not specified for the Free Tier in the provided documentation. This does not necessarily mean unlimited, and observed behavior can differ.
*   Rate limits are per project.
*   The effectiveness of tool calling can also depend on prompt clarity and the complexity of the tool's schema.

This information should help in selecting models for testing and understanding potential limitations. 