# Active Context: Timeline Intelligence Engine

## Current State

**Module Status**: ✅ Created - timeline_extractor module ready
**Purpose**: Forensic SMS extraction for co-parent litigation cases
**CaseCraft Alignment**: Targeting mobile app and enterprise products

## Recently Completed

- [x] Multi-document analysis with cross-referencing
- [x] document_parser.py: PDF, images (OCR via Vision), docx, xlsx, csv, md, txt
- [x] analysis.py: contradiction finding, testable hypothesis generation
- [x] Interactive refinement: asks for additional docs to fill gaps
- [x] Case state persists and grows as new documents are added

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

## Session History

| Date | Changes |
|------|---------|
| 2026-05-22 | Timeline extraction module created for CaseCraft prototype |
