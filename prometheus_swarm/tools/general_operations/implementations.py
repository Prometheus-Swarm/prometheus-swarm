from typing import Dict, Any
from prometheus_swarm.tools.file_operations.implementations import write_file


def review_file(recommendation: str, comment: str, **kwargs) -> Dict[str, Any]:
    """
    Review the file and provide a recommendation and comment.

    Args:
        recommendation: The recommendation the file
        comment: The comment to create on the file
    """
    return {
        "success": True,
        "message": "README file reviewed successfully",
        "data": {"recommendation": recommendation, "comment": comment},
    }

def create_readme_file_with_name(title: str, **kwargs) -> Dict[str, Any]:
    """
    Create a README file in the repository.

    Args:
        title: The title of the README file
    """
    readme_content = kwargs.get("readme_content")
    file_name = kwargs.get("file_name")

    readme_file = f"# {title}\n\n{readme_content}"
    write_file(
        file_name,
        readme_file,
        "Create Prometheus-generated README file",
    )

    return {
        "success": True,
        "message": "README file created successfully",
    }
