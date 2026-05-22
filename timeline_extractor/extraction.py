import os
import json
import re
from typing import Optional


EXTRACTION_PROMPT = """You are a forensic timeline extraction engine. Your input is a raw SMS conversation export between two co-parents in active litigation. Your job is to extract every discrete factual event and return structured data only. No summaries, no opinions, no analysis.

Extract the exact quote when possible.
If date is ambiguous use the nearest preceding date header.
Flag any event where Plaintiff's stated reason contradicts a prior stated reason.
Flag any event where Plaintiff's action contradicts her own prior statement.

For every event extracted, output exactly this structure:
DATE | TIME | ACTOR | EVENT_TYPE | FACT | QUOTE | LEGAL_SIGNIFICANCE

Event types to detect and tag:
- PICKUP_LATE (who was late, how late if stated)
- PICKUP_LOCATION_CHANGE (who changed it, notice given)
- VISIT_DENIED (reason given or not given)
- VISIT_MISSED (reason given or not given)
- COMMUNICATION_BLOCKED (method, duration)
- SCHEDULE_CHANGE (who initiated, notice given)
- ALLEGATION (what alleged, by whom)
- CYS_REFERENCE (case status mentioned)
- THIRD_PARTY_REFERENCE (Ricky/Terry/other named)
- TRAVEL (destination mentioned, children present)
- HOLIDAY (which holiday, access granted or denied)
- TOOL_PROPERTY (any mention of tools, belongings, garage access)
- FINANCIAL (taxes, support, payments mentioned)
- CHILD_STATEMENT (anything a child said, direct or reported)
- COURT_ORDER_REFERENCE (any mention of orders, agreements, lawyers)
- THREAT_OR_PRESSURE (explicit or implicit)

Output as CSV with headers."""


AGGREGATION_PROMPT = """Using the extracted CSV data, generate the following counts and date lists:

1. Total times Defendant was late for pickup — list each date and stated reason
2. Total times Plaintiff changed pickup location — list each date and new location
3. Total times Plaintiff changed pickup time with less than 2 hours notice
4. All dates Defendant was denied or missed a visit — with reason code
5. All holiday dates — access granted Y/N
6. All mentions of Tennessee, Kentucky, or out-of-state travel
7. All dates children called Defendant — note if call was complete or dropped
8. All dates Defendant attempted contact and received no response
9. All dates Plaintiff referenced CYS, allegations, or supervision requirements
10. All dates third parties (Ricky, Terry, Cody) were mentioned

Output as separate tables, one per category, in CSV format with clear headers."""


def parse_csv_output(output: str) -> list[dict]:
    """Parse CSV-formatted LLM output into list of event dicts."""
    lines = output.strip().split('\n')
    if not lines:
        return []

    header = lines[0]
    if not header.startswith('DATE'):
        return []

    events = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) >= 6:
            event = {
                'date': parts[0].strip(),
                'time': parts[1].strip() if len(parts) > 1 else '',
                'actor': parts[2].strip() if len(parts) > 2 else '',
                'event_type': parts[3].strip() if len(parts) > 3 else '',
                'fact': parts[4].strip() if len(parts) > 4 else '',
                'quote': parts[5].strip() if len(parts) > 6 else '',
                'legal_significance': parts[6].strip() if len(parts) > 6 else ''
            }
            events.append(event)

    return events


def call_llm(prompt: str, content: str, api_key: Optional[str] = None,
             model: str = "gemini-2.0-flash") -> str:
    """
    Call LLM API with extraction prompt and SMS content.

    Supports:
    - Google Gemini via GEMINI_API_KEY env var
    - OpenAI via OPENAI_API_KEY env var
    """
    api_key = api_key or os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')

    if not api_key:
        raise ValueError("No API key provided. Set GEMINI_API_KEY or OPENAI_API_KEY environment variable.")

    if 'gemini' in model.lower() or 'claude' in model.lower():
        return call_gemini(prompt, content, api_key, model)
    elif 'gpt' in model.lower() or 'o3' in model.lower() or 'o4' in model.lower():
        return call_openai(prompt, content, api_key, model)
    else:
        raise ValueError(f"Unsupported model: {model}")


def call_gemini(system_prompt: str, user_content: str, api_key: str, model: str) -> str:
    """Call Google Gemini API."""
    import urllib.request

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\n---\n\nSMS DATA TO EXTRACT:\n{user_content}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.8,
            "topK": 40
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")


def call_openai(system_prompt: str, user_content: str, api_key: str, model: str) -> str:
    """Call OpenAI API."""
    import urllib.request

    url = "https://api.openai.com/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.1
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {e}")


def extract_with_llm(raw_text: str, api_key: str = None, model: str = "gemini-2.0-flash") -> list[dict]:
    """Extract timeline events from raw SMS text using LLM."""
    output = call_llm(EXTRACTION_PROMPT, raw_text, api_key, model)
    return parse_csv_output(output)


def aggregate_summary(events: list[dict], api_key: str = None, model: str = "gemini-2.0-flash") -> dict:
    """Generate summary tables from extracted events using LLM."""
    events_csv = "DATE,TIME,ACTOR,EVENT_TYPE,FACT,QUOTE,LEGAL_SIGNIFICANCE\n"
    for e in events:
        events_csv += f"{e['date']},{e['time']},{e['actor']},{e['event_type']},{e['fact']},{e['quote']},{e['legal_significance']}\n"

    output = call_llm(AGGREGATION_PROMPT, events_csv, api_key, model)

    summary = {'contradictions': []}

    lines = output.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if 'late' in line.lower() and 'pickup' in line.lower():
            current_section = 'late_pickups'
            summary[current_section] = []
        elif 'location' in line.lower() and 'change' in line.lower():
            current_section = 'location_changes'
            summary[current_section] = []
        elif 'denied' in line.lower() or 'missed' in line.lower() and 'visit' in line.lower():
            current_section = 'denied_visits'
            summary[current_section] = []
        elif 'holiday' in line.lower():
            current_section = 'holidays'
            summary[current_section] = []
        elif 'travel' in line.lower():
            current_section = 'travel'
            summary[current_section] = []
        elif 'contact' in line.lower() and 'attempt' in line.lower():
            current_section = 'contact_attempts'
            summary[current_section] = []
        elif 'child' in line.lower() and 'call' in line.lower():
            current_section = 'child_calls'
            summary[current_section] = []
        elif 'cys' in line.lower() or 'allegation' in line.lower():
            current_section = 'cys_allegations'
            summary[current_section] = []
        elif 'third' in line.lower() or 'ricky' in line.lower() or 'terry' in line.lower():
            current_section = 'third_party_mentions'
            summary[current_section] = []
        elif current_section and line and not line.startswith('DATE'):
            pass

    return summary