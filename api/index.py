"""
Vercel serverless entry point.
"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

# app must be defined at top level for Vercel to detect it
app = FastAPI()
_startup_error = None

try:
    import main as _main
    app = _main.app
except Exception:
    _startup_error = traceback.format_exc()
    print(f"STARTUP ERROR:\n{_startup_error}")

if _startup_error:
    _err = _startup_error

    @app.get("/{path:path}")
    def error_page(path: str = ""):
        return PlainTextResponse(
            f"App failed to start. Error:\n\n{_err}",
            status_code=500
        )
