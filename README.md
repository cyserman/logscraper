# LogScraper — Forensic Timeline Extractor

Two components: a **Python extraction engine** for parsing SMS/call log evidence, and a **Next.js frontend** for viewing results.

---

## Python — Timeline Extractor

Parses raw SMS exports and call logs from co-parent litigation into structured, timestamped evidence tables. Detects contradictions, flags legal events, and aggregates summary counts by category.

### Supported input formats
- SMS: `.txt`, `.md`, `.pdf`, `.docx`
- Call logs: `.csv`, `.json`, `.xlsx`, `.xls`, `.pdf`, `.html`, `.txt`
- Images (OCR via Gemini Vision): `.png`, `.jpg`, `.jpeg`

### Setup

```bash
pip install -r requirements.txt
```

### API keys

Set one of the following depending on your provider:

```bash
# Google Gemini
export GEMINI_API_KEY='your_key'

# OpenAI
export OPENAI_API_KEY='your_key'

# OpenRouter
export OPENROUTER_API_KEY='your_key'

# Ollama — no key needed, runs locally
# Default: http://localhost:11434/v1
# Override: export OLLAMA_BASE_URL='http://your-host:11434/v1'
```

### CLI usage

```bash
# Extract timeline from SMS export
python -m timeline_extractor extract sms_export.txt -o ./output

# Extract from call log
python -m timeline_extractor call-log call_log.csv -o ./output/calls.csv

# Cross-reference multiple documents
python -m timeline_extractor analyze doc1.pdf doc2.txt -o ./analysis.txt

# Multi-document timeline (SMS + call logs + PDFs combined)
python -m timeline_extractor multi sms.txt calls.csv exhibit.pdf -o ./output
```

### Model selection

Pass any supported model via the `model` argument in code, or the default `gemini-2.0-flash` is used.

| Provider | Model string example |
|----------|---------------------|
| Gemini | `gemini-2.0-flash`, `gemini-1.5-pro` |
| OpenAI | `gpt-4o`, `o3-mini` |
| OpenRouter | `openrouter/meta-llama/llama-3.1-70b-instruct` |
| Ollama (local) | `ollama/hermes3:latest`, `ollama/llama3.2` |

```python
from timeline_extractor import extract_timeline

# Ollama
result = extract_timeline(sms_text, model="ollama/hermes3:latest")

# OpenRouter
result = extract_timeline(sms_text, model="openrouter/meta-llama/llama-3.1-70b-instruct")

# Custom endpoint
from timeline_extractor.extraction import extract_with_llm
events = extract_with_llm(text, model="my-model", base_url="https://my-proxy.example.com/v1")
```

### Output

Each run produces CSVs in the output directory:

- `events.csv` — every extracted event with date, actor, type, fact, quote, legal significance
- `late_pickups.csv`, `denied_visits.csv`, `holidays.csv`, etc. — aggregated summary tables
- `contradictions.csv` — flagged self-contradictions and implausible timelines

### Demo

```bash
python demo.py
```

### Tests

```bash
python test_parsing.py -v
```

---

## Frontend — Next.js

Web interface for viewing call log and timeline data.

**Stack:** Next.js 16, React 19, Tailwind CSS 4, TypeScript

```bash
bun install
bun dev       # http://localhost:3000
bun build
bun lint
bun typecheck
```

> The frontend currently displays a static call log table. API integration with the Python backend is in progress.
