import json
import csv
import sys
import os
from typing import Iterator

from .extraction import extract_with_llm, aggregate_summary
from .document_parser import parse_document
from .analysis import analyze_documents, test_hypothesis_with_document, request_additional_info


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


def analyze_case(documents: dict[str, str], api_key: str = None) -> dict:
    """
    Cross-reference multiple documents to find contradictions and test assumptions.

    Args:
        documents: dict of {filename: text_content}
        api_key: LLM API key

    Returns:
        dict with 'contradictions', 'hypotheses', 'verification_needed', 'questions_for_user', 'raw_analysis'
    """
    return analyze_documents(documents, api_key)


def add_document_to_case(case_state: dict, filename: str, api_key: str = None) -> dict:
    """
    Add a new document to an existing case analysis and re-analyze.

    Args:
        case_state: previous analysis result
        filename: path to new document
        api_key: LLM API key

    Returns:
        updated case analysis with new findings
    """
    new_content = parse_document(filename)
    new_documents = case_state.get('documents', {})
    new_documents[filename] = new_content

    return analyze_documents(new_documents, api_key)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Timeline Extraction & Case Analysis')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    extract_parser = subparsers.add_parser('extract', help='Extract timeline from SMS text')
    extract_parser.add_argument('input_file', help='Input SMS text file')
    extract_parser.add_argument('-o', '--output', default='./output', help='Output directory')

    analyze_parser = subparsers.add_parser('analyze', help='Analyze documents for contradictions')
    analyze_parser.add_argument('files', nargs='+', help='Input document files')
    analyze_parser.add_argument('-o', '--output', default='./analysis', help='Output file')

    args = parser.parse_args()

    if args.command == 'extract':
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        with open(args.input_file, 'r') as f:
            raw_text = f.read()
        result = extract_timeline(raw_text, api_key)
        events_to_csv(result['events'], f'{args.output}/events.csv')
        write_summary_tables(result['summary'], args.output)
        print(f"Extracted {len(result['events'])} events")

    elif args.command == 'analyze':
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        documents = {}
        for f in args.files:
            documents[f] = parse_document(f)
        result = analyze_documents(documents, api_key)

        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(result['raw_analysis'])
        print(f"Analysis written to {args.output}")

    else:
        parser.print_help()