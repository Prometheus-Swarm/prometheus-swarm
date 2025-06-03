from prometheus_swarm.tools.kno_sdk_wrapper.implementations import search_code_wrapper


DEFINITIONS = {
    "search_code": {
        "name": "search_code",
        "description": "Search for code in the repository",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to search for"}
            },
            "required": ["query"]
        },
        "function": search_code_wrapper
    }
}

