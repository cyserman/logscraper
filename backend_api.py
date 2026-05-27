#!/usr/bin/env python3
"""
FastAPI server — exposes the timeline extraction engine over HTTP.
Run: python backend_api.py
Docs: http://localhost:8000/docs
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from timeline_extractor import (
    extract_timeline, extract_call_log_events, generate_manifest, format_for_casecraft,
)

app = FastAPI(title="LogScraper API", version="1.0")

_bearer = HTTPBearer(auto_error=False)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Optional Bearer token gate. Only enforced when LOGSCRAPER_API_KEY is set."""
    required = os.environ.get("LOGSCRAPER_API_KEY")
    if not required:
        return  # open in local / personal mode
    if not credentials or credentials.credentials != required:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


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
    third_parties: list[str] = []
    case_id: str = "case"


class CaseCraftRequest(BaseModel):
    text: str
    case_id: str
    firm_id: str | None = None
    third_parties: list[str] = []
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
        result = extract_timeline(
            req.text, api_key,
            model=req.model,
            base_url=req.base_url,
            third_parties=req.third_parties or None,
        )
        manifest = generate_manifest(
            case_id=req.case_id,
            model=req.model,
            event_count=len(result['events']),
            contradiction_count=len(result['contradictions']),
        )
        return {**result, 'manifest': manifest}
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
        manifest = generate_manifest(
            case_id='call_log',
            call_log_path=tmp_path,
            model=model,
            event_count=len(events),
        )
        return {"events": events, "count": len(events), "manifest": manifest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/extract-for-casecraft", dependencies=[Depends(verify_api_key)])
def extract_for_casecraft(req: CaseCraftRequest):
    """Extract SMS timeline and return CaseCraft EvidenceRecord-shaped payload.

    Requires Authorization: Bearer <LOGSCRAPER_API_KEY> when that env var is set.
    firm_id is optional — pass it for B2B tenants, omit for personal/pro-se use.
    """
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
    )
    try:
        result = extract_timeline(
            req.text, api_key,
            model=req.model,
            base_url=req.base_url,
            third_parties=req.third_parties or None,
        )
        manifest = generate_manifest(
            case_id=req.case_id,
            model=req.model,
            event_count=len(result['events']),
            contradiction_count=len(result['contradictions']),
        )
        payload = format_for_casecraft(
            events=result['events'],
            contradictions=result['contradictions'],
            summary=result['summary'],
            manifest=manifest,
            case_id=req.case_id,
            firm_id=req.firm_id or None,
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
