import subprocess
import os
from prometheus_swarm.types import ToolOutput
from typing import Tuple, Callable

from kno_sdk.agent import build_tools
from kno_sdk.agent import AgentConfig
from kno_sdk.agent import AgentFactory
from kno_sdk.agent import LLMProviderBase

# Create an AgentConfig with your desired settings


# Create an instance of AgentFactory
factory = AgentFactory()
search_code = None

def build_tools_wrapper(repo_index) -> Tuple[Callable, Callable]:
    global search_code
    config = AgentConfig(
        repo_path=repo_index,
        llm_provider="anthropic",  # or "openai"
        model_name="claude-3-5-haiku-latest",  # or any other model name
        temperature=0.0,
        max_tokens=4096
    )
    llm = factory.get_llm(config)
    tools = build_tools(repo_index, llm=llm, cfg=config)
    # Store the functions from the tools
    search_code = tools[0].func
    return tools

def search_code_wrapper(query: str, **kwargs) -> ToolOutput:
    if search_code is None:
        raise RuntimeError("search_code function not initialized. Call build_tools_wrapper first.")
    return search_code(query)

