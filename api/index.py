"""
Vercel serverless entry point.
Adds the project root to sys.path so all modules are importable,
then re-exports the FastAPI app instance.
"""
import sys
import os

# Make the project root importable (api/ is one level below root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401 — Vercel looks for `app` in this module
