import json
import csv
import sys
import os
from typing import Iterator

from .extraction import extract_with_llm, aggregate_summary


def chunk_text(text: str, max_tokens: int = 150000) -> Iterator[str]:
    """Split text into chunks that fit within token limits."""
    lines = text.split('\n')
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line) // 4
        if current_size + line_size > max_tokens:
            if current_chunk:
                yield '\n'.join(current_chunk)
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size

    if current_chunk:
        yield '\n'.join(current_chunk)


def extract_timeline(raw_text: str, api_key: str = None) -> dict:
    """
    Extract structured timeline events from raw SMS text.

    Returns dict with:
    - events: list of structured event dicts
    - contradictions: list of flagged contradictions
    - summary: aggregated summary tables
    """
    all_events = []
    all_contradictions = []

    for i, chunk in enumerate(chunk_text(raw_text)):
        print(f"Processing chunk {i+1}...")
        result = extract_with_llm(chunk, api_key)
        all_events.extend(result)

    print(f"Extracted {len(all_events)} events total")

    summary = aggregate_summary(all_events, api_key)

    return {
        'events': all_events,
        'contradictions': all_contradictions,
        'summary': summary
    }


def events_to_csv(events: list[dict], output_path: str) -> None:
    """Write events list to CSV file."""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['DATE', 'TIME', 'ACTOR', 'EVENT_TYPE', 'FACT', 'QUOTE', 'LEGAL_SIGNIFICANCE'])
        for event in events:
            writer.writerow([
                event.get('date', ''),
                event.get('time', ''),
                event.get('actor', ''),
                event.get('event_type', ''),
                event.get('fact', ''),
                event.get('quote', ''),
                event.get('legal_significance', '')
            ])


def write_summary_tables(summary: dict, output_dir: str) -> None:
    """Write summary tables to separate CSV files."""
    os.makedirs(output_dir, exist_ok=True)

    sections = [
        ('late_pickups', ['DATE', 'ACTOR', 'HOW_LATE', 'REASON']),
        ('location_changes', ['DATE', 'ACTOR', 'NEW_LOCATION', 'NOTICE_GIVEN']),
        ('denied_visits', ['DATE', 'ACTOR', 'REASON_CODE', 'REASON_TEXT']),
        ('holidays', ['DATE', 'HOLIDAY_NAME', 'ACCESS_GRANTED']),
        ('travel', ['DATE', 'DESTINATION', 'CHILDREN_PRESENT', 'MENTIONED_BY']),
        ('contact_attempts', ['DATE', 'METHOD', 'RESPONDED']),
        ('child_calls', ['DATE', 'COMPLETE', 'NOTES']),
        ('cys_allegations', ['DATE', 'TYPE', 'DETAILS']),
        ('third_party_mentions', ['DATE', 'NAME', 'CONTEXT']),
        ('contradictions', ['DATE', 'ACTOR', 'PRIOR_STATEMENT', 'NEW_ACTION', 'CONTRADICTION_TYPE'])
    ]

    for section_name, headers in sections:
        if section_name in summary and summary[section_name]:
            with open(f'{output_dir}/{section_name}.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for item in summary[section_name]:
                    row = [item.get(h.lower().replace('_', ''), '') for h in headers]
                    writer.writerow(row)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m timeline_extractor <input_file> [output_dir]")
        print("  input_file: Path to raw SMS text file")
        print("  output_dir: Output directory (default: ./output)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './output'

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')

    with open(input_file, 'r') as f:
        raw_text = f.read()

    print(f"Loaded {len(raw_text)} characters from {input_file}")
    print("Calling LLM for extraction...")
    result = extract_timeline(raw_text, api_key)

    events_to_csv(result.get('events', []), f'{output_dir}/events.csv')
    write_summary_tables(result.get('summary', {}), output_dir)

    print(f"\nOutput written to {output_dir}/")
    print(f"  - events.csv ({len(result.get('events', []))} events)")
    for key in result.get('summary', {}):
        count = len(result['summary'][key])
        print(f"  - {key}.csv ({count} entries)")