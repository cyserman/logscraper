#!/usr/bin/env python3
"""
Phone-friendly LogScraper — no Node.js needed.

Serves a single touch UI (mobile/index.html) at / on top of backend_api's existing
endpoints (/api/extract-sms, /api/extract-calls, /health): one engine, one API.

Run:   python mobile_backend.py
Phone: ssh -N -L 8000:localhost:8000 root@<vps>   then open http://localhost:8000
       (or set LOGSCRAPER_HOST to the VPS Tailscale IP and browse to it directly)

Env:
  HERMES_MODEL      model pre-filled in the UI     default ollama/hermes3:latest
  OLLAMA_BASE_URL   where ollama/<model> is sent   default http://localhost:11434/v1
  LOGSCRAPER_HOST   bind address                   default 127.0.0.1 (never expose publicly:
                                                   the API has no auth on these routes)
  LOGSCRAPER_PORT   default 8000
"""

import html
import os
from pathlib import Path

from fastapi.responses import HTMLResponse

from backend_api import app

UI_PATH = Path(__file__).resolve().parent / "mobile" / "index.html"
DEFAULT_MODEL = os.environ.get("HERMES_MODEL", "ollama/hermes3:latest")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def mobile_ui():
    page = UI_PATH.read_text(encoding="utf-8")
    return page.replace("__DEFAULT_MODEL__", html.escape(DEFAULT_MODEL, quote=True))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("LOGSCRAPER_HOST", "127.0.0.1"),
        port=int(os.environ.get("LOGSCRAPER_PORT", "8000")),
    )
