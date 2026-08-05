"""Vercel entrypoint — re-exports the ASGI app so @vercel/python can serve it."""

import os
import sys

# api/ is a subdirectory; the project root has to be importable for `app.*`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401
