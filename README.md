# LogScraper — Forensic Timeline Extractor

A full-stack forensic evidence tool for parsing SMS exports and call logs into structured, timestamped legal timelines. Built for family law litigation support.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────┐
│  Next.js Frontend   │  HTTP  │  FastAPI Backend      │
│  localhost:3000     │◄──────►│  localhost:8000       │
│                     │        │                       │
│  • SMS paste tab    │        │  /api/extract-sms     │
│  • Call log upload  │        │  /api/extract-calls   │
│  • Model selector   │        │  /health              │
│  • CSV export       │        └──────────┬────────────┘
└─────────────────────┘                   │
                                          ▼
                              ┌──────────────────────┐
                              │  timeline_extractor/  │
                              │  Python package       │
                              │                       │
                              │  • document_parser    │
                              │  • call_log_parser    │
                              │  • extraction (LLM)   │
                              │  • analysis           │
                              └──────────┬────────────┘
                                         │
                              ┌──────────▼────────────┐
                              │  LLM Provider         │
                              │  Gemini / OpenAI /    │
                              │  OpenRouter / Ollama  │
                              └───────────────────────┘
```

---

## Running Locally

**Prerequisites:** Python 3.9+, Node.js / Bun, one LLM API key (or Ollama running locally)

```bash
# 1. Clone
git clone git@github.com:cyserman/logscraper.git
cd logscraper

# 2. Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" python-multipart
cp .env.example .env          # add your API key
python backend_api.py         # runs on :8000

# 3. Next.js frontend (separate terminal)
bun install
bun dev                       # runs on :3000
```

Open `http://localhost:3000`.

---

## API Keys

Set one in `.env` or as an environment variable:

```bash
GEMINI_API_KEY=...        # Google Gemini (default model: gemini-2.0-flash)
OPENAI_API_KEY=...        # OpenAI (gpt-4o, o3-mini, etc.)
OPENROUTER_API_KEY=...    # OpenRouter (access 100+ models)
# Ollama needs no key — runs at http://localhost:11434/v1
```

---

## Python Package — CLI Usage

```bash
source .venv/bin/activate

# Extract SMS timeline
python -m timeline_extractor extract sms_export.txt -o ./output

# Extract call log events
python -m timeline_extractor call-log call_log.csv -o ./output/calls.csv

# Cross-reference multiple documents
python -m timeline_extractor analyze doc1.pdf doc2.txt -o ./analysis.txt

# Multi-document combined timeline
python -m timeline_extractor multi sms.txt calls.csv exhibit.pdf -o ./output
```

### Model selection

| Provider | Model string |
|----------|-------------|
| Gemini (default) | `gemini-2.0-flash`, `gemini-1.5-pro` |
| OpenAI | `gpt-4o`, `o3-mini` |
| OpenRouter | `openrouter/meta-llama/llama-3.1-70b-instruct` |
| Ollama (local) | `ollama/hermes3:latest`, `ollama/llama3.2` |

```python
from timeline_extractor import extract_timeline

result = extract_timeline(sms_text, model="ollama/hermes3:latest")
# result = { events: [...], contradictions: [...], summary: {...} }
```

### Supported input formats

| Type | Formats |
|------|---------|
| SMS / text | `.txt`, `.md`, `.pdf`, `.docx` |
| Call logs | `.csv`, `.json`, `.xlsx`, `.xls`, `.pdf`, `.html`, `.txt` |
| Images (OCR) | `.png`, `.jpg`, `.jpeg` via Gemini Vision |

### Output files

Running any extraction writes CSVs to the output directory:

| File | Contents |
|------|----------|
| `events.csv` | All extracted events: date, time, actor, type, fact, quote, legal significance |
| `late_pickups.csv` | Dates, actors, duration, stated reason |
| `denied_visits.csv` | Dates, reason codes |
| `location_changes.csv` | Pickup location changes with notice given |
| `holidays.csv` | Holiday dates, access granted Y/N |
| `travel.csv` | Out-of-state travel mentions |
| `contact_attempts.csv` | Unanswered contact attempts |
| `child_calls.csv` | Child-initiated calls, complete/dropped |
| `cys_allegations.csv` | CYS/supervision references |
| `contradictions.csv` | Flagged self-contradictions |

---

## REST API (FastAPI)

Auto-docs available at `http://localhost:8000/docs`.

### `POST /api/extract-sms`
```json
{ "text": "...", "model": "gemini-2.0-flash", "base_url": null }
```
Returns `{ events: [...], contradictions: [...], summary: {...} }`

### `POST /api/extract-calls`
Multipart form: `file` (call log), `model`, `base_url`
Returns `{ events: [...], count: N }`

### `GET /health`
Returns `{ status: "ok", api_key_configured: true }`

---

## Development

```bash
python test_parsing.py -v    # unit tests (no API key needed)
bun typecheck                # TypeScript check
bun lint
```

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, Uvicorn
**Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4
**LLM:** Google Gemini, OpenAI, OpenRouter, Ollama (local)
**Runtime:** Bun
