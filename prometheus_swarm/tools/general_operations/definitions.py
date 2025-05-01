"""Summarizer operations tool definitions."""

from prometheus_swarm.tools.general_operations.implementations import (
    create_readme_file_with_name,
    review_file,
)

DEFINITIONS = {
    "create_readme_file_with_name": {
        "name": "create_readme_file_with_name",
        "description": "Create a README file.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the README file",
                },
            },
            "required": ["title"],
        },
        "function": create_readme_file_with_name,
        "final_tool": True,
    },
    "review_file": {
        "name": "review_file",
        "description": "Review the README file and provide a recommendation and comment.",
        "parameters": {
            "type": "object",
            "properties": {
                "recommendation": {
                    "type": "string",
                    "description": "APPROVE/REVISE/REJECT",
                },
                "comment": {
                    "type": "string",
                    "description": "The comment to create on the README file",
                },
            },
            "required": ["recommendation", "comment"],
        },
        "function": review_file,
    },
}
