import json
from typing import Optional
from .extraction import call_llm


CASE_ANALYSIS_PROMPT = """You are a forensic document analysis engine for family law litigation. Your job is to cross-reference multiple documents to find contradictions, test assumptions, and build a timeline of events.

INPUT DOCUMENTS:
{documents}

TASK:
1. Extract all factual claims from each document (who, what, when, where)
2. Cross-reference dates, times, locations, and statements across ALL documents
3. Identify:
   - Direct contradictions (same fact, opposite claims)
   - Implausible timelines (impossible sequences based on timestamps/locations)
   - Self-contradictions by the same party over time
   - Unverified claims that could be tested against other documents
4. Generate TESTABLE HYPOTHESES — statements that can be verified or falsified by examining the documents more closely
5. Note any gaps where additional documents or information would help

OUTPUT FORMAT:
For each finding, provide:
- DOCUMENT(S) REFERENCED
- CONTRADICTION/HYPOTHESIS
- EVIDENCE FOR
- EVIDENCE AGAINST
- RECOMMENDED VERIFICATION

Also list any additional documents or data that would strengthen the analysis."""


HYPOTHESIS_TEST_PROMPT = """You have extracted the following contradictions and hypotheses from document analysis:

{hy potheses}

Now test each hypothesis against this ADDITIONAL DOCUMENT:
{new_document}

For each hypothesis:
- Does the new document SUPPORT, CONTRADICT, or have NO INFORMATION about the hypothesis?
- Extract any NEW FACTS that relate to the hypothesis
- Note any NEW CONTRADICTIONS introduced by this document
- State whether the hypothesis is: VERIFIED / FALSIFIED / UNRESOLVED / REFINED

If you need additional documents to resolve any hypothesis, explicitly state what types of documents would help (e.g., "need text message logs from April 2024", "need school attendance records")."""


REFINE_QUESTIONS_PROMPT = """Based on the documents analyzed so far, generate a list of SPECIFIC QUESTIONS that would help resolve remaining contradictions or fill critical gaps.

Format each question as:
Q: [specific question]
WHY NEEDED: [what this would prove or disprove]
ALTERNATIVE: [what else could answer the same question]

Focus on questions that:
1. Target specific unresolved contradictions
2. Request documents that would verify/alibi key claims
3. Probe timeline gaps
4. Test credibility of claims made by either party"""


def analyze_documents(documents: dict[str, str], api_key: str = None) -> dict:
    """
    Cross-reference multiple documents to find contradictions and test assumptions.

    Args:
        documents: dict of {filename: text_content}
        api_key: LLM API key

    Returns:
        dict with 'contradictions', 'hypotheses', 'verification_needed', 'questions_for_user'
    """
    docs_text = "\n\n".join([f"=== {name} ===\n{content[:10000]}" for name, content in documents.items()])

    response = call_llm(CASE_ANALYSIS_PROMPT.format(documents=docs_text), "", api_key)

    result = {
        'contradictions': [],
        'hypotheses': [],
        'verification_needed': [],
        'questions_for_user': [],
        'raw_analysis': response
    }

    _parse_analysis_response(response, result)

    return result


def test_hypothesis_with_document(hypothesis: str, new_document: str, api_key: str = None) -> dict:
    """Test existing hypotheses against a new document."""
    response = call_llm(
        HYPOTHESIS_TEST_PROMPT.format(hypotheses=hypothesis, new_document=new_document[:10000]),
        "", api_key
    )

    return {'test_result': response, 'verification_status': 'UNRESOLVED'}


def request_additional_info(current_analysis: dict, api_key: str = None) -> list[dict]:
    """Generate specific questions to fill gaps in the analysis."""
    response = call_llm(
        REFINE_QUESTIONS_PROMPT,
        json.dumps(current_analysis.get('hypotheses', [])),
        api_key
    )

    questions = []
    for line in response.split('\n'):
        if line.startswith('Q:'):
            questions.append({'question': line[2:].strip()})

    return questions


def _parse_analysis_response(response: str, result: dict) -> None:
    """Parse LLM analysis output into structured data."""
    current_section = None
    current_item = {}

    for line in response.split('\n'):
        line = line.strip()
        if not line:
            continue

        lower = line.lower()
        if 'contradiction' in lower:
            current_section = 'contradictions'
        elif 'hypothesis' in lower:
            current_section = 'hypotheses'
        elif 'verification' in lower or 'recommended' in lower:
            current_section = 'verification_needed'
        elif 'question' in lower or 'documents' in lower and 'need' in lower:
            current_section = 'questions_for_user'
        elif current_section:
            if ':' in line:
                key, _, value = line.partition(':')
                current_item[key.strip().lower().replace(' ', '_')] = value.strip()

        if current_item and len(current_item) >= 3:
            result[current_section].append(current_item)
            current_item = {}

    if current_item:
        result[current_section].append(current_item)