import os
import re
from datetime import datetime


CALL_LOG_PATTERNS = [
    re.compile(r'^\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(\d{1,2}:\d{2})\s+(IN|OUT|missed|incoming|outgoing|missed call)\s+(\d+):(\d+)?', re.IGNORECASE),
    re.compile(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\+?\d+)\s+(IN|OUT|missed)\s+(\d+):(\d+)', re.IGNORECASE),
    re.compile(r'^"(\d{4}-\d{2}-\d{2})","(\d{2}:\d{2}:\d{2})","([^"]+)","([^"]+)","(\d+)","(IN|OUT|MISSED)"', re.IGNORECASE),
    re.compile(r'^(\d{2}/\d{2}/\d{4}),(\d{2}:\d{2}),(.*?),(\d+),(\d+),(IN|OUT|MISSED|INCOMING|OUTGOING)', re.IGNORECASE),
    re.compile(r'^Date:\s*(\d{4}-\d{2}-\d{2})\s+Time:\s*(\d{2}:\d{2})\s+Number:\s*(\+?[\d\s]+)\s+Type:\s*(IN|OUT|MISSED)', re.IGNORECASE),
]


CALL_TYPES = {
    'in': 'INCOMING',
    'out': 'OUTGOING',
    'missed': 'MISSED',
    'incoming': 'INCOMING',
    'outgoing': 'OUTGOING',
    'missed call': 'MISSED',
}


def parse_call_log(file_path: str) -> str:
    """
    Parse various call log formats into standardized SMS-like text format.
    Preserves: date, time, phone number, duration, call type, contact name if available.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.csv':
        return _parse_csv_call_log(file_path)
    elif ext == '.pdf':
        return _parse_pdf_call_log(file_path)
    elif ext == '.txt':
        return _parse_txt_call_log(file_path)
    elif ext in ['.xlsx', '.xls']:
        return _parse_spreadsheet_call_log(file_path)
    elif ext == '.json':
        return _parse_json_call_log(file_path)
    elif ext == '.html':
        return _parse_html_call_log(file_path)
    else:
        raise ValueError(f"Unsupported call log format: {ext}")


def _parse_csv_call_log(path: str) -> str:
    """Parse CSV call log into standardized text."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.strip().split('\n')
    if not lines:
        return ""

    entries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parsed = _try_parse_call_line(line)
        if parsed:
            date, time, number, call_type, duration = parsed
            entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

    if entries:
        return '\n'.join(entries)

    header = lines[0].lower()
    if 'number' in header or 'caller' in header or 'duration' in header:
        return _parse_csv_generic(lines)

    return content


def _try_parse_call_line(line: str) -> tuple[str, str, str, str, str] | None:
    """Try to parse a line as a call log entry. Returns (date, time, number, type, duration) or None."""
    for pattern in CALL_LOG_PATTERNS:
        match = pattern.match(line)
        if match:
            groups = match.groups()
            if len(groups) >= 4:
                try:
                    if re.match(r'^\d{4}-\d{2}-\d{2}', groups[0]):
                        date = groups[0]
                        time = groups[1]
                        number = groups[2] if len(groups) > 2 else ""
                        call_type = groups[3].upper() if len(groups) > 3 else "UNKNOWN"
                        duration = groups[4] if len(groups) > 4 else "0:00"
                    elif len(groups) >= 6:
                        date = groups[0]
                        time = groups[1]
                        number = groups[2]
                        call_type = groups[5].upper()
                        duration = f"{groups[3]}:{groups[4]}" if len(groups) >= 5 else "0:00"
                    else:
                        date = groups[0]
                        time = groups[1]
                        number = groups[2]
                        call_type = groups[3].upper() if len(groups) > 3 else "UNKNOWN"
                        duration = groups[4] if len(groups) > 4 else "0:00"

                    return (date, time, number, call_type, duration)
                except (ValueError, IndexError):
                    continue
    return None


def _parse_csv_generic(lines: list[str]) -> str:
    """Parse CSV with unknown structure by detecting columns."""
    import csv
    from io import StringIO

    reader = csv.reader(StringIO('\n'.join(lines)))
    header = next(reader, [])

    header_lower = [h.lower().strip() for h in header]
    date_idx = next((i for i, h in enumerate(header_lower) if 'date' in h), 0)
    time_idx = next((i for i, h in enumerate(header_lower) if 'time' in h), 1)
    num_idx = next((i for i, h in enumerate(header_lower) if 'number' in h or 'caller' in h or 'phone' in h), 2)
    type_idx = next((i for i, h in enumerate(header_lower) if 'type' in h or 'direction' in h), 3)
    dur_idx = next((i for i, h in enumerate(header_lower) if 'duration' in h or 'length' in h), 4)

    entries = []
    for row in reader:
        if len(row) > max(date_idx, time_idx, num_idx):
            date = row[date_idx] if date_idx < len(row) else ""
            time = row[time_idx] if time_idx < len(row) else ""
            number = row[num_idx] if num_idx < len(row) else ""
            call_type = row[type_idx].upper() if type_idx < len(row) and row[type_idx] else "UNKNOWN"
            duration = row[dur_idx] if dur_idx < len(row) else "0:00"
            entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

    return '\n'.join(entries)


def _parse_txt_call_log(path: str) -> str:
    """Parse plain text call log."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')
    entries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parsed = _try_parse_call_line(line)
        if parsed:
            date, time, number, call_type, duration = parsed
            entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

    if entries:
        return '\n'.join(entries)

    return content


def _parse_pdf_call_log(path: str) -> str:
    """Extract call log data from PDF."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        full_text = '\n\n'.join(text_parts)

        lines = full_text.split('\n')
        entries = []
        for line in lines:
            parsed = _try_parse_call_line(line)
            if parsed:
                date, time, number, call_type, duration = parsed
                entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

        if entries:
            return '\n'.join(entries)
        return full_text

    except ImportError:
        import subprocess
        result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True)
        return result.stdout


def _parse_spreadsheet_call_log(path: str) -> str:
    """Extract call log from spreadsheet."""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("openpyxl required: pip install openpyxl")

    wb = openpyxl.load_workbook(path, data_only=True)
    entries = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        for row in sheet.iter_rows(values_only=True):
            row_str = ' | '.join([str(c) if c else '' for c in row])
            parsed = _try_parse_call_line(row_str)
            if parsed:
                date, time, number, call_type, duration = parsed
                entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")
            elif any(c for c in row if c):
                entries.append(row_str)

    return '\n'.join(entries) if entries else ""


def _parse_json_call_log(path: str) -> str:
    """Parse JSON call log (common from some carriers/apps)."""
    import json
    with open(path, 'r') as f:
        data = json.load(f)

    entries = []
    records = data if isinstance(data, list) else data.get('calls', data.get('callLog', []))

    for call in records:
        if isinstance(call, dict):
            date = call.get('date', call.get('timestamp', ''))
            time = call.get('time', call.get('formattedTime', ''))
            number = call.get('number', call.get('phoneNumber', call.get('address', '')))
            duration = call.get('duration', call.get('callDuration', '0'))
            call_type = call.get('type', call.get('direction', 'UNKNOWN')).upper()

            if isinstance(date, (int, float)):
                dt = datetime.fromtimestamp(date / 1000 if date > 1e10 else date)
                date = dt.strftime('%Y-%m-%d')
                time = dt.strftime('%H:%M:%S')

            entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

    return '\n'.join(entries) if entries else json.dumps(data, indent=2)


def _parse_html_call_log(path: str) -> str:
    """Parse HTML call log (e.g., from carrier websites)."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    import re
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE)
    entries = []

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
        if cells:
            cleaned = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            line = ' | '.join(c for c in cleaned if c)
            parsed = _try_parse_call_line(line)
            if parsed:
                date, time, number, call_type, duration = parsed
                entries.append(f"{date} {time} | {call_type} CALL | {number} | Duration: {duration}")

    if entries:
        return '\n'.join(entries)
    return re.sub(r'<[^>]+>', ' ', content)