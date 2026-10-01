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
                              │  • cross_reference    │
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

# Basic
result = extract_timeline(sms_text, model="ollama/hermes3:latest")

# With case-specific third parties
result = extract_timeline(
    sms_text,
    model="gemini-2.0-flash",
    third_parties=["Ricky", "Terry", "Cody"],
)
# result = { events: [...], contradictions: [...], summary: {...} }
```

### Third-party name injection

Pass case-specific names so the extraction prompt targets exactly the right people:

```python
# Each case can define its own relevant parties
extract_timeline(text, third_parties=["Marcus", "Denise", "Aunt Karen"])

# Default when omitted: flags any named third party generically
```

This replaces hardcoded names in the prompt — required for multi-tenant / enterprise use.

### Supported input formats

| Type | Formats |
|------|---------|
| SMS / text | `.txt`, `.md`, `.pdf`, `.docx` |
| Call logs | `.csv`, `.json`, `.xlsx`, `.xls`, `.pdf`, `.html`, `.txt` |
| Images (OCR) | `.png`, `.jpg`, `.jpeg` via Gemini Vision |

### Output files

Running any extraction writes CSVs + a manifest to the output directory:

| File | Contents |
|------|----------|
| `events.csv` | All extracted events: date, time, actor, type, fact, quote, legal significance |
| `{case_id}_contradictions.csv` | LLM-flagged + cross-reference contradictions with SOURCE column |
| `{case_id}_manifest.json` | Chain of custody record (see below) |
| `late_pickups.csv` | Dates, actors, duration, stated reason |
| `denied_visits.csv` | Dates, reason codes |
| `location_changes.csv` | Pickup location changes with notice given |
| `holidays.csv` | Holiday dates, access granted Y/N |
| `travel.csv` | Out-of-state travel mentions |
| `contact_attempts.csv` | Unanswered contact attempts |
| `child_calls.csv` | Child-initiated calls, complete/dropped |
| `cys_allegations.csv` | CYS/supervision references |

### Chain of custody manifest

Every extraction produces a `{case_id}_manifest.json`:

```json
{
  "case_id": "smith-v-jones",
  "processed_at": "2026-05-27T14:32:00+00:00",
  "extractor_version": "0.1.0",
  "model": "gemini-2.0-flash",
  "platform": "Linux-6.17...",
  "inputs": {
    "sms_file": {
      "path": "/absolute/path/to/sms.txt",
      "sha256": "a3f9d2...",
      "size_bytes": 84210
    },
    "call_log": { "path": "...", "sha256": "...", "size_bytes": 12400 }
  },
  "event_count": 47,
  "contradiction_count": 3
}
```

SHA-256 hashes allow independent verification that the source files were not altered after extraction.

### Cross-reference contradiction detection

`extract_timeline_with_calls()` runs SMS + call log extraction and cross-references them automatically:

```python
from timeline_extractor import extract_timeline_with_calls, save_results

result = extract_timeline_with_calls(
    sms_text="...",
    call_log_file="call_log.csv",
    model="gemini-2.0-flash",
    third_parties=["Ricky", "Terry"],
)

save_results(
    output_dir="./output",
    case_id="smith-v-jones",
    events=result['events'],
    contradictions=result['contradictions'],
    summary=result['summary'],
    call_events=result['call_events'],
    sms_path="sms.txt",
    call_log_path="call_log.csv",
    model="gemini-2.0-flash",
)
```

Three contradiction patterns are detected automatically:

| Pattern | Description |
|---------|-------------|
| `CALL_CLAIM_VS_LOG` | SMS claims no calls / no response, but call log shows active calls that day |
| `BLOCKED_VS_ACTIVE` | `COMMUNICATION_BLOCKED` event type, but calls appear in log |
| `PICKUP_NO_CALL` | `VISIT_DENIED` / `VISIT_MISSED` / `PICKUP_LATE`, but zero calls logged that day |

---

## REST API (FastAPI)

Auto-docs available at `http://localhost:8000/docs`.

### `POST /api/extract-sms`
```json
{
  "text": "...",
  "model": "gemini-2.0-flash",
  "base_url": null,
  "third_parties": ["Ricky", "Terry"],
  "case_id": "smith-v-jones"
}
```
Returns `{ events, contradictions, summary, manifest }`

### `POST /api/extract-calls`
Multipart form: `file` (call log), `model`, `base_url`
Returns `{ events, count, manifest }`

### `GET /health`
Returns `{ status: "ok", api_key_configured: true }`

---

## Phone + VPS (local Hermes model)

Two entry points run the same engine against a local model, with no Node.js and no API key:

| | What it does | Best for |
|---|---|---|
| `mobile_backend.py` | Touch UI at `/` on top of the REST API above; results can be saved as JSON | Quick pastes / single call logs from a phone |
| `claw_worker.py` | Watches `incoming/`; every file that finishes uploading is moved into `processed_evidence/<case>_<UTC>/inputs/`, extracted, cross-referenced, and written out with a manifest hashing every input | Large exports and batches. It survives the phone sleeping. |

The worker processes **all** files in a drop. It merges SMS exports (`.txt`/`.md`) into one timeline and cross-references them against every call log (`.csv`/`.xlsx`/`.xls`/`.json`). It never processes a file twice, skips files modified in the last 15s (still uploading), and holds a lock so overlapping runs can't happen. On failure it writes `FAILED.txt` next to the kept inputs, together with the `mv` command to retry.

### VPS setup (once)

```bash
# Ollama's installer already runs it as a systemd service — don't start `ollama serve` by hand
ollama pull hermes3:latest
sudo systemctl edit ollama          # add:  [Service]
                                    #       Environment="OLLAMA_CONTEXT_LENGTH=16384"
sudo systemctl restart ollama

git clone https://github.com/cyserman/logscraper /root/logscraper && cd /root/logscraper
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp deploy/logscraper.env.example .env                    # model, endpoint, case id
sudo cp deploy/*.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now logscraper-mobile claw-worker
journalctl -u claw-worker -f
```

Without systemd: `python claw_worker.py my_case` (one pass, cron-friendly) or `python claw_worker.py my_case --watch`.

### From the phone (Termux)

```bash
ssh -N -o ServerAliveInterval=30 -L 8000:localhost:8000 root@<vps>   # then open http://localhost:8000
scp export.txt calls.csv root@<vps>:/root/logscraper/incoming/       # queue a batch for the worker
scp -r root@<vps>:/root/logscraper/processed_evidence/<run> .        # pull results back
```

The UI binds to `127.0.0.1` by default. These routes have no auth, so never bind it to a public interface. Set `LOGSCRAPER_HOST` to your Tailscale IP if you'd rather skip the tunnel.

### Local-model pitfalls

- **Silent truncation:** Ollama drops whatever doesn't fit its context window, with no error, so events go missing. Keep `LOGSCRAPER_CHUNK_TOKENS` well under `OLLAMA_CONTEXT_LENGTH` (6000 for 16384 leaves room for the prompt and output).
- **Speed:** on a CPU-only VPS, expect minutes per chunk. Set `LOGSCRAPER_LLM_TIMEOUT` high (1800), and send big exports through the worker rather than the phone UI. A browser request that runs that long usually dies when the phone sleeps. Pointing `OLLAMA_BASE_URL` at a GPU/high-RAM machine on your tailnet is the biggest speedup.
- **RAM:** hermes3 8B plus a 16k context window needs about 7 GB. On a 12 GB box shared with other models, keep only one loaded at a time.
- **Summary tables** are produced in one call over all events, so on very large cases a local model may truncate them too. `events.csv` is the source of truth.
- `HERMES_MODEL` keeps the `ollama/` prefix (e.g. `ollama/hermes3:latest`). The worker also accepts bare names and vLLM model ids, since it always sends to `OLLAMA_BASE_URL`.

---

## Development

```bash
python -m pytest -q          # unit tests, no API key or model needed
bun typecheck
bun lint
```

---

## Tech Stack

**Backend:** Python 3.12, FastAPI, Uvicorn
**Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4
**LLM:** Google Gemini, OpenAI, OpenRouter, Ollama (local)
**Runtime:** Bun
