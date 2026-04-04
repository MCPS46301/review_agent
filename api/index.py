"""
Vercel serverless entry point.
"""
import sys
import os
import traceback

# Make the project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app  # noqa: F401
except Exception as e:
    print(f"STARTUP ERROR: {e}")
    traceback.print_exc()

    # Return a minimal app that shows the error so we can debug
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    _error = traceback.format_exc()

    app = FastAPI()

    @app.get("/{path:path}")
    def error_page(path: str = ""):
        return PlainTextResponse(
            f"App failed to start. Error:\n\n{_error}",
            status_code=500
        )
