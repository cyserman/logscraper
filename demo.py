#!/usr/bin/env python3
"""
Demo script for LogScraper Forensic Timeline Extractor
Shows basic usage of the SMS and call log extraction functionality
"""

import os
import sys
from timeline_extractor import extract_timeline, extract_call_log_events, events_to_csv, write_summary_tables

def demo_sms_extraction():
    """Demonstrate SMS timeline extraction"""
    print("=== SMS Timeline Extraction Demo ===")
    
    # Read sample SMS data
    sample_file = "sample_sms.txt"
    if not os.path.exists(sample_file):
        print(f"Sample file {sample_file} not found!")
        return
    
    with open(sample_file, 'r') as f:
        sms_content = f.read()
    
    print(f"Read {len(sms_content)} characters of SMS data")
    
    # Extract timeline (requires API key - will fail gracefully if not set)
    try:
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Warning: No API key set. Set GEMINI_API_KEY or OPENAI_API_KEY to run extraction.")
            print("Skipping actual extraction - showing what would happen instead.")
            
            # Show what the extraction would produce
            print("\nExpected output structure:")
            print("- Events: List of dicts with DATE, TIME, ACTOR, EVENT_TYPE, FACT, QUOTE, LEGAL_SIGNIFICANCE")
            print("- Contradictions: Flagged inconsistencies in statements")
            print("- Summary: Aggregated tables (late pickups, location changes, etc.)")
            return
        
        print("Extracting timeline with LLM...")
        result = extract_timeline(sms_content, api_key)
        
        # Save results
        os.makedirs("demo_output", exist_ok=True)
        events_to_csv(result['events'], 'demo_output/events.csv')
        write_summary_tables(result['summary'], 'demo_output')
        
        print(f"Extracted {len(result['events'])} events")
        print(f"Found {len(result.get('contradictions', []))} contradictions")
        print("Results saved to demo_output/")
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        print("This is expected if no valid API key is available.")

def demo_call_log_extraction():
    """Demonstrate call log extraction"""
    print("\n=== Call Log Extraction Demo ===")
    
    # Use the provided cleaned call log
    call_log_file = "exchange/call_log_clean.csv"
    if not os.path.exists(call_log_file):
        print(f"Call log file {call_log_file} not found!")
        return
    
    print(f"Found call log: {call_log_file}")
    
    try:
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Warning: No API key set. Skipping actual extraction.")
            print("The call log parser can handle CSV, JSON, PDF, HTML, TXT, XLSX formats.")
            return
            
        print("Extracting call events...")
        events = extract_call_log_events(call_log_file, api_key)
        
        os.makedirs("demo_output", exist_ok=True)
        output_file = "demo_output/call_events.csv"
        
        import csv
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['DATE', 'TIME', 'CALLER', 'RECIPIENT', 'CALL_TYPE', 'DURATION', 'ANSWERED', 'LEGAL_SIGNIFICANCE'])
            for e in events:
                writer.writerow([e.get('date', ''), e.get('time', ''), e.get('caller', ''),
                               e.get('recipient', ''), e.get('call_type', ''), e.get('duration', ''),
                               e.get('answered', ''), e.get('legal_significance', '')])
        
        print(f"Extracted {len(events)} call events to {output_file}")
        
    except Exception as e:
        print(f"Call log extraction failed: {e}")

def main():
    """Run all demos"""
    print("LogScraper Forensic Timeline Extractor - Demo")
    print("=" * 50)
    
    demo_sms_extraction()
    demo_call_log_extraction()
    
    print("\n=== Demo Complete ===")
    print("To run actual extractions:")
    print("1. Set your API key: export GEMINI_API_KEY='your_key_here'")
    print("2. Run: python demo.py")
    print("3. Or use the CLI: python -m timeline_extractor extract sample_sms.txt -o ./output")

if __name__ == "__main__":
    main()