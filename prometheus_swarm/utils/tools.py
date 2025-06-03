"""
Utility functions for managing tools in prometheus-swarm
"""

from prometheus_swarm.tools.general_operations.definitions import DEFINITIONS as general_operations
from prometheus_swarm.tools.file_operations.definitions import DEFINITIONS as file_operations
from prometheus_swarm.tools.git_operations.definitions import DEFINITIONS as git_operations
from prometheus_swarm.tools.kno_sdk_wrapper.definitions import DEFINITIONS as kno_sdk_wrapper
from prometheus_swarm.tools.execute_command.definitions import DEFINITIONS as execute_command
from prometheus_swarm.tools.github_operations.definitions import DEFINITIONS as github_operations
from prometheus_swarm.tools.summarizer_operations.definitions import DEFINITIONS as summarizer_operations
from prometheus_swarm.tools.repo_operations.definitions import DEFINITIONS as repo_operations

def get_all_tools():
    """
    Retrieve all available tools from all tool categories.
    
    Returns:
        dict: A dictionary containing all tool definitions, where keys are tool names
              and values are their respective definitions.
    """
    return {
        **general_operations,
        # **planner_operations,
        **file_operations,
        **git_operations,
        **kno_sdk_wrapper,
        **execute_command,
        **github_operations,
        # **summarizer_operations,
        # **repo_operations,
    }

def get_tool_names():
    """
    Get a list of all available tool names.
    
    Returns:
        list: A list of strings containing all tool names.
    """
    return list(get_all_tools().keys())

def get_all_definitions():
    """
    Get all tool definitions from all categories.
    
    Returns:
        dict: A dictionary containing all tool definitions organized by category.
              Each category contains its respective tool definitions.
    """
    return {
        'general_operations': general_operations,
        'file_operations': file_operations,
        'git_operations': git_operations,
        'kno_sdk_wrapper': kno_sdk_wrapper,
        'execute_command': execute_command,
        'github_operations': github_operations,
        # 'summarizer_operations': summarizer_operations,
        # 'repo_operations': repo_operations
    } 