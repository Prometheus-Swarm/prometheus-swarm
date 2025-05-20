# prometheus-swarm

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