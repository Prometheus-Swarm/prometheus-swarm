# prometheus-swarm

## API Setup

The Prometheus Swarm framework supports multiple LLM providers. To use a specific provider:

1.  Set the appropriate API key in your `.env` file:
    ```
    # API Keys (add the ones you need)
    GEMINI_API_KEY="your_gemini_api_key"
    OPENAI_API_KEY="your_openai_api_key"
    ANTHROPIC_API_KEY="your_anthropic_api_key"
    XAI_API_KEY="your_xai_api_key"
    OPENROUTER_API_KEY="your_openrouter_api_key"
    ```

2.  When initializing the client, specify which provider to use:
    ```python
    from prometheus_swarm.clients import setup_client

    # For Gemini
    client = setup_client(client="gemini")

    # For OpenAI
    # client = setup_client(client="openai")

    # For Anthropic
    # client = setup_client(client="anthropic")
    ```

3.  Optionally specify a model:
    ```python
    # Use a specific model
    client = setup_client(client="gemini", model="gemini-1.5-pro-latest")
    ```
See `test_setup_instructions.txt` for more details on obtaining API keys.

## Prometheus Swarm Overview

**TODO: This section needs to be filled in with a detailed explanation of how Prometheus Swarm works.**

## Job Specification Schema

In Prometheus Swarm, "job specifications" are primarily defined by the input parameters of the various tools available within the system. These tools are designed to perform specific, automatable tasks. The schema for a job is dictated by the `parameters` field in the tool's definition.

Tool definitions are typically found in Python dictionaries within files like:
*   `prometheus_swarm/tools/github_operations/definitions.py`
*   `prometheus_swarm/tools/repo_operations/definitions.py`
*   `prometheus_swarm/tools/execute_command/definitions.py`

Each tool definition includes:
*   `name`: A unique identifier for the tool.
*   `description`: A human-readable explanation of what the tool does.
*   `parameters`: An object defining the expected inputs for the tool. This follows a JSON Schema-like structure, specifying:
    *   `type`: The overall type of the parameters object (usually "object").
    *   `properties`: A dictionary where each key is an input parameter name. For each parameter, it defines:
        *   `type`: The data type of the parameter (e.g., "string", "boolean", "array", "object").
        *   `description`: A description of the parameter.
        *   `enum`: (Optional) A list of allowed values for the parameter.
        *   `items`: (Optional, for "array" type) A schema for the elements within the array.
    *   `required`: A list of parameter names that are mandatory for the tool to execute.
*   `function`: The Python function that implements the tool's logic.

For example, the `create_worker_pull_request` tool might have parameters like `title`, `description`, `changes`, `tests`, and `todo`, each with a defined type and description. When a "job" is created to use this tool, the input must conform to this schema.

## Local Environment Setup

To run Prometheus Swarm locally, you'll need to set up your environment as follows:

**1. Prerequisites:**
*   Python 3.12 (as suggested by `Dockerfile`)
*   Git
*   `curl` and `sudo` (primarily for Docker setup, but good to have)

**2. Python Virtual Environment:**
It is highly recommended to use a Python virtual environment to manage dependencies.
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows
```

**3. Install Dependencies:**
Install all required Python packages using pip:
```bash
pip install -r requirements.txt
```
Key dependencies include:
*   LLM client libraries: `anthropic`, `openai`, `google-generativeai`
*   Web framework: `Flask`, `gunicorn`
*   Database: `sqlmodel`, `SQLAlchemy` (for SQLite)
*   Environment management: `python-dotenv`

**4. Environment Variables (.env file):**
Create a `.env` file in the project root. This file will store your API keys and other configuration variables. Refer to the "API Setup" section above for API key configuration.
Other potential environment variables (based on `Dockerfile` and codebase):
```
MIDDLE_SERVER_URL=https://builder247.api.koii.network # Example value
DATABASE_PATH=./database.db # Or /data/database.db if running in Docker
```
Ensure `DATABASE_PATH` points to where you want your local SQLite database file (`database.db`) to be stored.

**5. Database:**
Prometheus Swarm uses a SQLite database (managed via `sqlmodel` and `SQLAlchemy`). If `DATABASE_PATH` is set correctly, the database file should be created automatically when the application runs if it doesn't already exist. No separate database server installation is typically required for SQLite.

**6. Running the Application:**
The `Dockerfile` suggests using `gunicorn` to serve the application (presumably a Flask app defined in `main:app`).
To run locally (ensure your virtual environment is active and `.env` is configured):
```bash
# Example, actual command might vary based on main.py structure
gunicorn --log-level=info --error-logfile=- --capture-output --enable-stdio-inheritance -w 1 -b 0.0.0.0:8080 main:app
```
Adjust the host, port, and number of workers (`-w`) as needed. The `main:app` part refers to an `app` instance of Flask in a `main.py` file. You might need to identify the correct entry point for your application.

**7. Docker (Alternative):**
Alternatively, you can build and run the application using Docker, which handles the environment setup within a container.
```bash
docker build -t prometheus-swarm .
docker run -p 8080:8080 --env-file .env prometheus-swarm
```
Make sure your `.env` file is correctly populated with API keys and other necessary environment variables. The `.dockerignore` file ensures that secrets like `.env` are not copied into the image if not handled carefully, so using `--env-file` with `docker run` is a common practice for injecting them at runtime. The `Dockerfile` copies the whole directory, so ensure your local `.env` is not included in the build context if it contains sensitive information not meant to be baked into the image.