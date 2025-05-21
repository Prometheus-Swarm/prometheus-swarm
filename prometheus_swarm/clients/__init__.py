# check if a fork exists, sync if it does, create a fork if it doesn't
from dotenv import load_dotenv
import os
from pathlib import Path
from prometheus_swarm.clients.base_client import Client
from prometheus_swarm.clients.anthropic_client import AnthropicClient
from prometheus_swarm.clients.xai_client import XAIClient
from prometheus_swarm.clients.openai_client import OpenAIClient
from prometheus_swarm.clients.openrouter_client import OpenRouterClient
from prometheus_swarm.clients.gemini_client import GeminiClient
from prometheus_swarm.clients.fallback_gemini_client import FallbackGeminiClient


# from prometheus_swarm.clients.ollama_client import OllamaClient


def setup_client(client: str, model: str = None) -> Client:
    """Configure and return the an LLM client with tools.

    Args:
        client: The client type to use ("openai", "anthropic", "xai", etc.)
        model: Optional model to use (overrides client's default model)

    Returns:
        Client: Configured client instance with tools loaded

    Environment Variables:
        TOOLS_DIR: Path to tools directory (required)
    """
    load_dotenv()

    client_config = clients[client]
    
    # Special handling for fallback_gemini client
    if client == "fallback_gemini":
        client_instance = client_config["client"](
            api_key=os.environ[client_config["api_key"]],
            system_instruction=None,  # Can be customized as needed
            start_with_model=model if model else "gemini-1.5-flash-latest"
        )
    else:
        client_instance = client_config["client"](
            api_key=os.environ[client_config["api_key"]], model=model
        )
    
    base_dir = Path(__file__).parent.parent

    tools_dir = base_dir / "tools"
    if not tools_dir:
        raise ValueError("TOOLS_DIR environment variable must be set")

    client_instance.register_tools(tools_dir)
    return client_instance


clients = {
    "anthropic": {"client": AnthropicClient, "api_key": "ANTHROPIC_API_KEY"},
    "xai": {"client": XAIClient, "api_key": "XAI_API_KEY"},
    "openai": {"client": OpenAIClient, "api_key": "OPENAI_API_KEY"},
    "openrouter": {"client": OpenRouterClient, "api_key": "OPENROUTER_API_KEY"},
    "gemini": {"client": GeminiClient, "api_key": "GEMINI_API_KEY"},
    "fallback_gemini": {"client": FallbackGeminiClient, "api_key": "GEMINI_API_KEY"},
    # "ollama": {"client": OllamaClient, "api_key": "N/A"},  # TODO: This is not correct
}
