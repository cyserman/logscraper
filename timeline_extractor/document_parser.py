import os
import json
import base64
from typing import Optional


def parse_document(file_path: str) -> str:
    """Parse any supported document into raw text."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.md':
        return parse_markdown(file_path)
    elif ext == '.txt':
        return parse_txt(file_path)
    elif ext == '.pdf':
        return parse_pdf(file_path)
    elif ext in ['.doc', '.docx']:
        return parse_doc(file_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        return parse_image(file_path)
    elif ext in ['.xlsx', '.xls', '.csv']:
        return parse_spreadsheet(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def parse_markdown(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


def parse_txt(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


def parse_pdf(path: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return '\n\n'.join(text_parts)
    except ImportError:
        import subprocess
        result = subprocess.run(['pdftotext', path, '-'], capture_output=True, text=True)
        return result.stdout


def parse_doc(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        return '\n\n'.join([p.text for p in doc.paragraphs])
    except ImportError:
        raise ValueError("python-docx required for .doc/.docx support: pip install python-docx")


def parse_image(path: str) -> str:
    """OCR via Gemini Vision - returns description of image content."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY required for image OCR")

    import urllib.request

    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": "Extract ALL text content from this image. If this is a document or form, transcribe every word exactly. Preserve structure where possible."
            }, {
                "inlineData": {
                    "mimeType": f"image/{os.path.splitext(path)[1][1:]}",
                    "data": image_data
                }
            }]
        }],
        "generationConfig": {"temperature": 0.1}
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")


def parse_spreadsheet(path: str) -> str:
    """Extract all cell values from spreadsheet."""
    ext = os.path.splitext(path)[1].lower()

    if ext == '.csv':
        with open(path, 'r') as f:
            return f.read()

    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        parts = []
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            parts.append(f"=== Sheet: {sheet_name} ===")
            for row in sheet.iter_rows(values_only=True):
                row_data = [str(c) if c is not None else '' for c in row]
                if any(c for c in row_data):
                    parts.append(' | '.join(row_data))
        return '\n'.join(parts)
    except ImportError:
        raise ValueError("openpyxl required for spreadsheet support: pip install openpyxl")