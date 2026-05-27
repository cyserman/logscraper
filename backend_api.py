#!/usr/bin/env python3
"""
FastAPI server — exposes the timeline extraction engine over HTTP.
Run: python backend_api.py
Docs: http://localhost:8000/docs
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from timeline_extractor import extract_timeline, extract_call_log_events

app = FastAPI(title="LogScraper API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class SMSRequest(BaseModel):
    text: str
    model: str = "gemini-2.0-flash"
    base_url: str | None = None


@app.get("/health")
def health():
    configured = bool(
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    return {"status": "ok", "api_key_configured": configured}


@app.post("/api/extract-sms")
def extract_sms(req: SMSRequest):
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    try:
        result = extract_timeline(req.text, api_key, model=req.model, base_url=req.base_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-calls")
async def extract_calls(
    file: UploadFile = File(...),
    model: str = Form(default="gemini-2.0-flash"),
    base_url: str = Form(default=None),
):
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )

    suffix = os.path.splitext(file.filename)[1] or ".csv"
    allowed = {".csv", ".json", ".xlsx", ".xls", ".pdf", ".html", ".txt"}
    if suffix.lower() not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        events = extract_call_log_events(tmp_path, api_key, model=model, base_url=base_url)
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
