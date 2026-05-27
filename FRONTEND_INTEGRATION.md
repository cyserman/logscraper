# Frontend-Backend Integration Guide for LogScraper

## Overview
This document explains how the Next.js frontend template can integrate with the Python forensic timeline extraction backend to create a full-stack application.

## Current Architecture
- **Backend**: Python-based forensic extraction engine (`timeline_extractor/`)
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind CSS template (`src/app/`)

## Integration Approaches

### 1. API Route Approach (Recommended)
Create Next.js API routes that call the Python extraction engine.

#### Backend Setup
Create a simple Python Flask/FastAPI service or use direct subprocess calls:

```python
# backend_api.py (example)
from timeline_extractor import extract_timeline, extract_call_log_events
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/api/extract-sms', methods=['POST'])
def extract_sms():
    data = request.json
    text = data.get('text')
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        return jsonify({'error': 'API key not configured'}), 500
    
    try:
        result = extract_timeline(text, api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/extract-calls', methods=['POST'])
def extract_calls():
    # Handle file upload and process
    pass

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

#### Frontend Usage
```typescript
// src/app/api/extract-sms/route.ts
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { text } = await request.json()
    
    // Call your Python backend service
    const response = await fetch('http://localhost:5000/api/extract-sms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
    
    if (!response.ok) {
      throw new Error('Extraction failed')
    }
    
    const result = await response.json()
    return NextResponse.json(result)
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to extract timeline' },
      { status: 500 }
    )
  }
}
```

### 2. Direct Python Execution (Alternative)
Execute Python scripts directly from Next.js API routes using `child_process`.

### 3. Microservice Approach
Deploy the Python extraction engine as a separate microservice (Docker, AWS Lambda, etc.) and communicate via REST/gRPC.

## Data Flow
1. User uploads SMS/call log data via frontend form
2. Frontend sends data to Next.js API route
3. API route calls Python extraction engine
4. Engine returns structured events and summaries
5. Frontend displays results in tables, charts, or timelines
6. User can export results (CSV, PDF) for legal proceedings

## UI Components to Build
- File upload component (SMS, call logs, PDFs, etc.)
- Timeline visualization (using libraries like vis.js, react-calendar, or custom)
- Event table with filtering and search
- Summary dashboard with charts
- Export buttons (CSV, PDF, JSON)
- Case management (save/load analyses)

## Environment Variables
Add to `.env.local`:
```
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
PYTHON_BACKEND_URL=http://localhost:5000  # If using separate service
```

## Deployment Considerations
1. **Python Backend**: Deploy separately (Heroku, AWS, DigitalOcean, etc.)
2. **Frontend**: Deploy to Vercel (Next.js optimized)
3. **Communication**: Secure API calls with proper CORS settings
4. **Rate Limiting**: Implement to prevent API abuse
5. **Security**: Sanitize inputs, validate file types, limit upload sizes

## Example Feature Timeline
```
Week 1: Basic file upload and API route
Week 2: SMS extraction integration and results display
Week 3: Call log processing and timeline visualization
Week 4: Summary tables, export functionality, and polishing
```

## Benefits of Integration
- **User-Friendly**: Non-technical users can run complex forensic analysis
- **Professional Output**: Clean, court-ready reports and visualizations
- **Audit Trail**: All extractions logged and exportable
- **Scalable**: Backend can handle large document batches
- **Extensible**: Easy to add new document types or analysis methods

## Next Steps
1. Choose integration approach (API routes recommended)
2. Create backend service or direct call mechanism
3. Build upload components in frontend
4. Implement results display and visualization
5. Add export functionality
6. Test with real/sample data
7. Deploy and monitor