# Project Timeline Extractor

This project consists of two primary components: a **Forensic Timeline Extraction Engine** (Python) and a **Frontend Template** (Next.js).

## 🛠️ Timeline Extractor (Python)

A forensic utility designed to parse raw SMS conversations and call logs between co-parents in litigation to extract structured, factual evidence.

### Features
- **SMS Extraction**: Detects specific event types such as late pickups, denied visits, schedule changes, and legal references.
- **Call Log Analysis**: Parses call logs to identify patterns of communication or contradictions with SMS claims.
- **Automated Aggregation**: Generates summary tables of contradictions, missed visits, and third-party mentions.
- **LLM Integration**: Supports Google Gemini and OpenAI models for high-accuracy forensic parsing.

### Setup & Usage
1. **Environment**: Ensure you have Python 3.9+ installed.
2. **API Keys**: Set your API key as an environment variable:
   ```bash
   export GEMINI_API_KEY='your_key_here'
   # OR
   export OPENAI_API_KEY='your_key_here'
   ```
3. **Running**: Use the scripts within the `timeline_extractor/` directory to parse your data.

---

## 💻 Frontend (Next.js)

A modern web interface template built with Next.js 16, React 19, and Tailwind CSS.

### Tech Stack
- **Framework**: Next.js (App Router)
- **Styling**: Tailwind CSS 4.0
- **Language**: TypeScript

### Development
```bash
bun install
bun dev
```

### Scripts
- `bun build`: Build the production application
- `bun lint`: Run ESLint for code quality
- `bun typecheck`: Run TypeScript type checking
