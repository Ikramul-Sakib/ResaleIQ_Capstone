"""Start the ResaleIQ API for local development:  python run.py

For hosting (PythonAnywhere, Render, ...) point the WSGI server at `run:app`.
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        debug=app.config["APP_ENV"] == "development",
    )
