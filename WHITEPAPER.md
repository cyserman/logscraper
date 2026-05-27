# LogScraper: Automated Forensic Timeline Extraction for Family Law Litigation

**Technical Overview — v1.0**

---

## Abstract

LogScraper is an open-source forensic evidence processing tool designed to transform raw SMS exports and carrier call logs into structured, court-ready evidence timelines. It combines a rule-based document parsing layer with large language model (LLM) extraction to detect legally significant events — including denied visitation, communication patterns, self-contradictions, and schedule violations — across unstructured communication records. The system is designed to run locally on commodity hardware using open-weight models, preserving evidentiary chain of custody by keeping all data off third-party servers.

---

## 1. Problem Statement

Pro se litigants and family law attorneys routinely possess hundreds or thousands of SMS messages and months of call logs that contain legally significant facts but lack the structure needed to present them effectively. Key challenges include:

- **Volume:** Multi-year SMS threads may contain thousands of messages across multiple exports
- **Format fragmentation:** Call logs vary by carrier — CSV, JSON, PDF, HTML, and spreadsheet formats all exist in the wild
- **Signal extraction:** Legally significant events (late pickups, denied visits, location changes, CYS references) are embedded in conversational text
- **Contradiction detection:** Self-contradictions by a party are often only visible when messages from different time periods are compared
- **Admissibility preparation:** Courts expect structured, dated evidence — raw exports are unwieldy

Manual review of this volume of material is time-consuming, error-prone, and expensive when billed at attorney rates.

---

## 2. System Architecture

LogScraper is a three-layer stack:

```
┌─────────────────────────────────────────────┐
│  Presentation Layer                          │
│  Next.js 16 / React 19 / Tailwind CSS 4     │
│  • File upload (SMS text, call logs)         │
│  • Model selection                           │
│  • Results tables with legal significance   │
│  • CSV export                               │
└──────────────────┬──────────────────────────┘
                   │ HTTP (JSON / multipart)
┌──────────────────▼──────────────────────────┐
│  API Layer                                   │
│  FastAPI / Uvicorn (Python 3.12)            │
│  • /api/extract-sms                         │
│  • /api/extract-calls                       │
│  • /health                                  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Extraction Engine (timeline_extractor/)     │
│                                             │
│  ┌─────────────┐    ┌──────────────────┐   │
│  │ Document    │    │ Call Log         │   │
│  │ Parser      │    │ Parser           │   │
│  │ .pdf .docx  │    │ .csv .json .xlsx │   │
│  │ .txt .md    │    │ .pdf .html .txt  │   │
│  │ .png .jpg   │    │                  │   │
│  └──────┬──────┘    └────────┬─────────┘   │
│         │                    │              │
│         └──────────┬─────────┘              │
│                    ▼                        │
│           ┌────────────────┐                │
│           │  LLM Router    │                │
│           │  Gemini        │                │
│           │  OpenAI        │                │
│           │  OpenRouter    │                │
│           │  Ollama        │                │
│           └────────┬───────┘                │
│                    ▼                        │
│           ┌────────────────┐                │
│           │  Structured    │                │
│           │  Output        │                │
│           │  events.csv    │                │
│           │  summary CSVs  │                │
│           └────────────────┘                │
└─────────────────────────────────────────────┘
```

---

## 3. Document Parsing Layer

The parsing layer normalizes heterogeneous inputs into plain text before LLM processing.

### 3.1 SMS / Document Formats

| Format | Method |
|--------|--------|
| `.txt`, `.md` | Direct UTF-8 read |
| `.pdf` | `pdfplumber` (primary), `pdftotext` subprocess (fallback) |
| `.docx` | `python-docx` paragraph extraction |
| `.png`, `.jpg`, `.jpeg` | Gemini Vision API (base64 inline data) — OCR with full-text transcription prompt |

### 3.2 Call Log Formats

Call logs vary significantly by carrier and export tool. The parser handles six distinct format families:

| Format | Strategy |
|--------|----------|
| `.csv` | Pattern matching against 5 compiled regex patterns → column header detection fallback |
| `.json` | Key aliasing (`date`/`timestamp`, `number`/`phoneNumber`/`address`, `duration`/`callDuration`) with Unix epoch normalization |
| `.xlsx`/`.xls` | `openpyxl` with header-based column detection |
| `.pdf` | Text extraction then line-level pattern matching |
| `.html` | `<tr>`/`<td>` extraction then pattern matching |
| `.txt` | Line-by-line pattern matching |

All formats are normalized to the same canonical string representation before LLM processing:

```
2024-03-15 14:32 | INCOMING CALL | +1 (555) 867-5309 | Duration: 4:23
```

---

## 4. LLM Extraction Pipeline

### 4.1 Prompt Architecture

Two purpose-built system prompts drive the extraction:

**SMS Extraction Prompt** — instructs the model to act as a forensic extraction engine and output a strict pipe-delimited CSV with the schema:

```
DATE | TIME | ACTOR | EVENT_TYPE | FACT | QUOTE | LEGAL_SIGNIFICANCE
```

Twenty event type tags are defined, covering the most legally significant communication patterns in custody/divorce litigation:

```
PICKUP_LATE          PICKUP_LOCATION_CHANGE   VISIT_DENIED
VISIT_MISSED         COMMUNICATION_BLOCKED    SCHEDULE_CHANGE
ALLEGATION           CYS_REFERENCE            THIRD_PARTY_REFERENCE
TRAVEL               HOLIDAY                  TOOL_PROPERTY
FINANCIAL            CHILD_STATEMENT          COURT_ORDER_REFERENCE
THREAT_OR_PRESSURE   CALL_INITIATED           CALL_DROPPED
CALL_REFUSED         CALL_MISSED
```

The prompt explicitly instructs the model to flag self-contradictions and cases where a stated reason contradicts a prior stated reason.

**Call Log Extraction Prompt** — cross-references call records against SMS timeline patterns, flagging:
- Calls immediately before/after scheduled pickups
- Patterns of unanswered calls
- Calls to/from named third parties
- Call patterns during alleged supervision events

**Aggregation Prompt** — takes the extracted event CSV and generates 10 structured summary tables (late pickups with dates and reasons, denied visits with reason codes, holiday access log, travel references, etc.)

### 4.2 Chunking Strategy

Large documents are chunked to fit within model context windows. Chunk size is estimated at 4 characters per token (conservative approximation for legal prose), with a default ceiling of 150,000 tokens per chunk. Each chunk is processed independently; events are aggregated post-processing.

### 4.3 Multi-Provider LLM Routing

The `call_llm()` function routes to the appropriate API based on model name prefix:

| Prefix | Route | Auth |
|--------|-------|------|
| `gemini-*` | Google Generative Language API | `GEMINI_API_KEY` |
| `gpt-*`, `o3-*`, `o4-*` | OpenAI Chat Completions API | `OPENAI_API_KEY` |
| `openrouter/*` | OpenRouter (OpenAI-compatible) | `OPENROUTER_API_KEY` |
| `ollama/*` | Local Ollama instance | None |
| Any + `base_url` | OpenAI-compatible endpoint | Optional |

All HTTP calls use Python's standard `urllib.request` — no SDK dependencies for the core engine. This keeps the package lean and reduces supply chain surface area.

---

## 5. Output Schema

### 5.1 Event Record

```
DATE              — ISO 8601 or verbatim from source
TIME              — HH:MM or approximate
ACTOR             — Party name or identifier
EVENT_TYPE        — One of 20 defined tags
FACT              — Objective statement of what occurred
QUOTE             — Verbatim text from the record if available
LEGAL_SIGNIFICANCE — Model-assessed relevance to litigation
```

### 5.2 Summary Tables

Ten aggregation tables are generated per run, each designed to answer a specific evidentiary question a family court filing might need to address.

---

## 6. Privacy and Chain of Custody

Running LogScraper locally with Ollama means **all data stays on-device**. No SMS content, names, or case facts leave the machine. For users with Gemini or OpenAI keys, data is processed per those providers' API terms.

The system makes no writes to the original evidence files. All output is written to a separate output directory, leaving the source material intact for independent verification.

---

## 7. Deployment Modes

| Mode | Frontend | Backend | LLM |
|------|----------|---------|-----|
| Local (air-gapped) | `bun dev` | `python backend_api.py` | Ollama |
| Local + cloud LLM | `bun dev` | `python backend_api.py` | Gemini / OpenAI |
| CLI only | — | — | Any |
| Headless batch | — | — | Any |

---

## 8. Tech Stack

| Component | Technology |
|-----------|-----------|
| Extraction engine | Python 3.12, stdlib only (core) |
| API server | FastAPI 0.111, Uvicorn |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Runtime | Bun |
| PDF parsing | pdfplumber |
| Spreadsheet | openpyxl |
| Word docs | python-docx |
| Image OCR | Google Gemini Vision API |
| LLM providers | Gemini, OpenAI, OpenRouter, Ollama |

---

## 9. Limitations

- **LLM output consistency:** Structured CSV output depends on model instruction-following quality. Smaller models (< 7B parameters) may produce malformed rows that are silently dropped.
- **Chunking context loss:** Events that span chunk boundaries may be missed or partially extracted.
- **Handwriting / photos:** Image OCR requires Gemini Vision — local-only (Ollama) deployments cannot process image files.
- **Not legal advice:** This tool extracts and organizes factual claims from communications records. The legal significance annotations are LLM-generated and should be reviewed by a qualified attorney before use in proceedings.

---

## 10. Quick-Start Copy/Paste Reference

> These blocks are safe to run in order on a fresh Ubuntu/Debian machine.

**Step 1 — Clone and enter the project**
```bash
# Clones via SSH — requires your GitHub SSH key to be added
git clone git@github.com:cyserman/logscraper.git
cd logscraper
```

**Step 2 — Python backend setup**
```bash
# Creates an isolated Python environment (keeps system Python clean)
python3 -m venv .venv
source .venv/bin/activate      # activate — you'll see (.venv) in your prompt

# Installs the API server and file-upload support
pip install fastapi "uvicorn[standard]" python-multipart

# Optional: PDF, Word, and Excel parsing
pip install pdfplumber python-docx openpyxl
```

**Step 3 — Configure your API key**
```bash
# Copy the example env file and fill in your key
cp .env.example .env
# Then edit .env and set one of:
#   GEMINI_API_KEY=...
#   OPENAI_API_KEY=...
#   OPENROUTER_API_KEY=...
# No key needed if using Ollama locally
```

**Step 4 — Start the Python backend**
```bash
# Must be in the project directory with .venv active
source .venv/bin/activate
python backend_api.py
# Running at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Step 5 — Start the frontend (separate terminal)**
```bash
bun install        # first time only
bun dev            # http://localhost:3000
```

**Step 6 — CLI extraction (no frontend needed)**
```bash
source .venv/bin/activate

# SMS timeline from a text file
python -m timeline_extractor extract my_sms_export.txt -o ./output

# Call log from CSV
python -m timeline_extractor call-log call_log.csv -o ./output/calls.csv

# Use local Ollama instead of cloud API
# (Ollama must be running: ollama serve)
python -m timeline_extractor extract my_sms_export.txt \
  --model ollama/hermes3:latest -o ./output

# Cross-reference multiple documents at once
python -m timeline_extractor multi sms.txt calls.csv exhibit.pdf -o ./output
```

**Step 7 — Run tests**
```bash
# No API key needed — tests only cover parsing logic
python3 test_parsing.py -v
```

**Useful Ollama commands**
```bash
ollama serve                   # start Ollama daemon if not running
ollama list                    # see installed models
ollama pull hermes3            # download hermes3 (best for structured extraction)
ollama run hermes3             # test it interactively
```

**Re-activating your environment after a reboot**
```bash
cd ~/path/to/logscraper
source .venv/bin/activate      # always do this before running Python commands
python backend_api.py
```

---

## 11. Repository

[github.com/cyserman/logscraper](https://github.com/cyserman/logscraper)
