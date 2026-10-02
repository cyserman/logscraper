#!/usr/bin/env python3
"""
Hermes Claw worker — unattended evidence intake for a local model (Ollama or vLLM).

Drop SMS exports (.txt/.md) and call logs (.csv/.xlsx/.xls/.json) into incoming/.
Each pass claims every file that has finished uploading, moves it into
processed_evidence/<case>_<UTC stamp>/inputs/ (so nothing is ever processed twice and the
hashed originals sit beside their outputs), extracts one timeline across all SMS files,
cross-references it against every call log, and writes CSVs + a chain-of-custody manifest.

Usage:
  python claw_worker.py [case_id]                  one pass, then exit (cron-friendly)
  python claw_worker.py [case_id] --watch [SECS]   poll forever, default 30s (systemd-friendly)

Env:
  OLLAMA_BASE_URL          OpenAI-compatible endpoint      default http://localhost:11434/v1
  HERMES_MODEL             model ("ollama/" prefix ok)     default ollama/hermes3:latest
  LOGSCRAPER_INCOMING      drop folder                     default ./incoming next to this file
  LOGSCRAPER_OUTPUT        results folder                  default ./processed_evidence
  LOGSCRAPER_CHUNK_TOKENS  keep well under the model's context window (see README)
  LOGSCRAPER_LLM_TIMEOUT   seconds per LLM call; CPU-only boxes need 600+
"""

import argparse
import os
import re
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows — run without the overlap guard
    fcntl = None

from timeline_extractor import extract_timeline, extract_call_log_events, save_results
from timeline_extractor.cross_reference import cross_reference_sms_calls

BASE_DIR = Path(__file__).resolve().parent
INCOMING = Path(os.environ.get("LOGSCRAPER_INCOMING", BASE_DIR / "incoming"))
OUTPUT = Path(os.environ.get("LOGSCRAPER_OUTPUT", BASE_DIR / "processed_evidence"))
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
HERMES_MODEL = os.environ.get("HERMES_MODEL", "ollama/hermes3:latest")

SMS_EXTS = {".txt", ".md"}
CALL_EXTS = {".csv", ".xlsx", ".xls", ".json"}
SETTLE_SECONDS = 15  # files touched more recently than this are probably still uploading

_warned: set[str] = set()


def log(msg: str) -> None:
    print(f"[Hermes-Claw {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def find_ready_inputs() -> tuple[list[Path], list[Path]]:
    """Return (sms_files, call_files) in incoming/ that have stopped changing."""
    sms, calls = [], []
    now = time.time()
    for p in sorted(INCOMING.iterdir()):
        # Skip dirs and temp/hidden files (rsync .name.XXXX, syncthing ~name.tmp, .DS_Store)
        if not p.is_file() or p.name.startswith((".", "~")):
            continue
        if now - p.stat().st_mtime < SETTLE_SECONDS:
            continue
        ext = p.suffix.lower()
        if ext in SMS_EXTS:
            sms.append(p)
        elif ext in CALL_EXTS:
            calls.append(p)
        elif p.name not in _warned:
            _warned.add(p.name)
            log(f"Ignoring {p.name}: unsupported type (SMS: .txt/.md, calls: .csv/.xlsx/.xls/.json)")
    return sms, calls


def run_extraction(sms_files: list[Path], call_files: list[Path]) -> dict:
    llm = {"model": HERMES_MODEL, "base_url": OLLAMA_BASE_URL}
    events, contradictions, summary = [], [], {}

    if sms_files:
        # One timeline across every export in the drop; headers keep the source visible
        sms_text = "\n\n".join(
            f"=== {p.name} ===\n{p.read_text(encoding='utf-8', errors='replace')}" for p in sms_files
        )
        result = extract_timeline(sms_text, **llm)
        events, contradictions, summary = result["events"], result["contradictions"], result["summary"]

    call_events = []
    for p in call_files:
        call_events.extend(extract_call_log_events(str(p), **llm))

    if events and call_events:
        cross_ref = cross_reference_sms_calls(events, call_events)
        log(f"Cross-reference found {len(cross_ref)} additional contradictions")
        contradictions = contradictions + cross_ref

    return {"events": events, "call_events": call_events,
            "contradictions": contradictions, "summary": summary}


def process_batch(case_id: str) -> bool | None:
    """One pass over incoming/. Returns None if idle, True on success, False on failure."""
    INCOMING.mkdir(parents=True, exist_ok=True)
    sms_files, call_files = find_ready_inputs()
    if not sms_files and not call_files:
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUTPUT / f"{case_id}_{stamp}"
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True)

    # Claim before processing: a crash mid-run can never cause a double extraction
    sms_files = [Path(shutil.move(p, inputs_dir / p.name)) for p in sms_files]
    call_files = [Path(shutil.move(p, inputs_dir / p.name)) for p in call_files]
    log(f"{run_dir.name}: {len(sms_files)} SMS file(s), {len(call_files)} call log(s) "
        f"→ {HERMES_MODEL} @ {OLLAMA_BASE_URL}")

    try:
        results = run_extraction(sms_files, call_files)
        save_results(
            output_dir=str(run_dir),
            events=results["events"],
            contradictions=results["contradictions"],
            summary=results["summary"],
            case_id=case_id,
            call_events=results["call_events"],
            sms_path=str(sms_files[0]) if len(sms_files) == 1 else None,
            call_log_path=str(call_files[0]) if len(call_files) == 1 else None,
            model=HERMES_MODEL,
            input_files=[str(p) for p in sms_files + call_files],
        )
    except Exception:
        (run_dir / "FAILED.txt").write_text(traceback.format_exc())
        log(f"FAILED — see {run_dir / 'FAILED.txt'}. To retry: mv '{inputs_dir}'/* '{INCOMING}/'")
        return False

    log(f"Done: {len(results['events'])} events, {len(results['call_events'])} calls, "
        f"{len(results['contradictions'])} contradictions → {run_dir}")
    return True


def acquire_lock():
    """Hold an exclusive lock so a slow run and the next cron tick never overlap."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if fcntl is None:
        return True
    fh = open(OUTPUT / ".claw_worker.lock", "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        return None
    return fh  # keep the handle alive for the life of the process


def main() -> int:
    ap = argparse.ArgumentParser(description="Process evidence dropped into incoming/ with a local model.")
    ap.add_argument("case_id", nargs="?", default="default_case")
    ap.add_argument("--watch", nargs="?", const=30, type=int, metavar="SECS",
                    help="keep polling incoming/ every SECS seconds (default 30)")
    args = ap.parse_args()
    case_id = re.sub(r"[^A-Za-z0-9._-]", "_", args.case_id) or "default_case"

    lock = acquire_lock()
    if lock is None:
        log("Another claw_worker is already running — exiting.")
        return 0

    if args.watch is None:
        outcome = process_batch(case_id)
        if outcome is None:
            log(f"No new evidence files in {INCOMING}.")
        return 1 if outcome is False else 0

    log(f"Watching {INCOMING} every {args.watch}s")
    while True:
        process_batch(case_id)
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
