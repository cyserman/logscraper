# Active Context: LogScraper

## Current State

**Module Status**: SMS and call-log extraction are integrated with the Next.js frontend; RFA/RFP evidence matrix is available in the browser.
**Purpose**: Extract communication timelines and organize reviewed evidence for discovery requests without generating legal responses.
**Data handling**: Matrix persistence is explicit opt-in, browser-local, and exportable; source files are not changed.

## Recently Completed

- [x] Timeline extraction module architecture
- [x] Two-pass extraction: raw events + aggregated summaries
- [x] Multi-document analysis with cross-referencing
- [x] document_parser.py: PDF, images (OCR via Vision), docx, xlsx, csv, md, txt
- [x] analysis.py: contradiction finding, testable hypothesis generation
- [x] Interactive refinement: asks for additional docs to fill gaps
- [x] Call log parsing: CSV, JSON, PDF, HTML, TXT, XLSX
- [x] Pattern matching for 6 common carrier call log formats
- [x] Cross-document timeline extraction from mixed file types
- [x] New CLI commands: 'call-log' and 'multi'
- [x] document_parser.py: PDF, images (OCR via Vision), docx, xlsx, csv, md, txt
- [x] analysis.py: contradiction finding, testable hypothesis generation
- [x] Interactive refinement: asks for additional docs to fill gaps
- [x] Case state persists and grows as new documents are added
- [x] claw_worker.py: unattended incoming/ → processed_evidence/ batch worker (local model, lock, settle, per-batch manifest)
- [x] mobile_backend.py + mobile/index.html: phone UI served on top of backend_api (no Node.js)
- [x] Local-model hardening: ollama/ prefix + base_url routing, LOGSCRAPER_CHUNK_TOKENS, LOGSCRAPER_LLM_TIMEOUT, tolerant table parsing
- [x] deploy/: systemd units + env template for the VPS
- [x] Next.js RFA/RFP evidence matrix: per-request event linking, counts, source quotes/provenance, review notes, CSV/JSON export, and opt-in browser-local save/load
- [x] WHITEPAPER.md quick-start: documented the Ubuntu/Debian python3-venv prerequisite

## Project Architecture

```
timeline_extractor/
├── __init__.py      # Main API: extract_timeline(), events_to_csv(), write_summary_tables()
└── extraction.py    # LLM calls, CSV parsing, aggregation logic
```

## Key Design Decisions

1. **Module-first**: Function signature `extract_timeline(raw_text, api_key) -> dict` stays identical across products
2. **Two-pass approach**: Pass 1 = raw event extraction; Pass 2 = aggregation into counts/date lists
3. **Contradiction flagging**: Automatic Falsus in Uno ammunition from Plaintiff's self-contradictions
4. **No chain of custody yet**: Discovery tool version vs private analysis tool still TBD
5. **Evidence matrix**: Request wording and reviewed links are user-entered; extracted interpretations remain separate from source facts; unavailable provenance is disclosed instead of inferred.

## Session History

| Date | Changes |
|------|---------|
| 2026-05-22 | Timeline extraction module created for CaseCraft prototype |
| 2026-10-26 | Added interactive RFA/RFP evidence matrix to the Next.js frontend |
| 2026-10-27 | Documented the Python venv package prerequisite in the whitepaper quick-start |
