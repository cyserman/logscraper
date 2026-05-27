"""
Cross-reference SMS timeline events against call log facts to find contradictions.
"""


_BLOCKED_KEYWORDS = frozenset([
    'NEVER CALL', 'NEVER ANSWER', 'NO RESPONSE', 'NOT ANSWER',
    'WONT ANSWER', "WON'T ANSWER", 'IGNORING', 'BLOCKING',
    # Note: COMMUNICATION_BLOCKED and CALL_REFUSED are event_type tags handled
    # by Pattern 2, not text keywords — keep them out of this set.
])

_MISSED_VISIT_TYPES = frozenset(['VISIT_DENIED', 'VISIT_MISSED', 'PICKUP_LATE'])


def cross_reference_sms_calls(
    sms_events: list[dict],
    call_events: list[dict],
) -> list[dict]:
    """
    Find contradictions between SMS claims and call log facts.

    Patterns detected:
    - SMS claims no contact / blocked / no answer on date X but call log
      shows calls occurred that day (CALL_CLAIM_VS_LOG)
    - SMS tags COMMUNICATION_BLOCKED but calls appear in log (BLOCKED_VS_ACTIVE)
    - VISIT_DENIED / VISIT_MISSED / PICKUP_LATE but no calls logged that day (PICKUP_NO_CALL)

    Returns list of contradiction dicts:
    {
        date, sms_claim, call_log_fact, contradiction_type,
        sms_quote, call_record, actor
    }
    """
    calls_by_date: dict[str, list[dict]] = {}
    for call in call_events:
        date = (call.get('date') or '')[:10]
        if date:
            calls_by_date.setdefault(date, []).append(call)

    contradictions: list[dict] = []

    for sms in sms_events:
        date = (sms.get('date') or '')[:10]
        if not date:
            continue

        event_type = (sms.get('event_type') or '').upper()
        fact = (sms.get('fact') or '').upper()
        legal_sig = (sms.get('legal_significance') or '').upper()
        quote = (sms.get('quote') or '').upper()
        combined = ' '.join([fact, legal_sig, quote, event_type])

        day_calls = calls_by_date.get(date, [])

        # Pattern 1: SMS claims no-contact / no-answer, but calls happened
        if any(kw in combined for kw in _BLOCKED_KEYWORDS):
            active_calls = [c for c in day_calls
                            if (c.get('call_type') or '').upper() in ('INCOMING', 'OUTGOING')]
            for call in active_calls:
                contradictions.append({
                    'date': date,
                    'actor': sms.get('actor', ''),
                    'sms_claim': sms.get('fact', ''),
                    'call_log_fact': (
                        f"{call.get('call_type', '').upper()} call"
                        f", duration {call.get('duration', 'unknown')}"
                    ),
                    'contradiction_type': 'CALL_CLAIM_VS_LOG',
                    'sms_quote': sms.get('quote', ''),
                    'call_record': call,
                })

        # Pattern 2: COMMUNICATION_BLOCKED event type but calls in log that day
        elif event_type == 'COMMUNICATION_BLOCKED' and day_calls:
            contradictions.append({
                'date': date,
                'actor': sms.get('actor', ''),
                'sms_claim': sms.get('fact', ''),
                'call_log_fact': f"{len(day_calls)} call(s) recorded in log this day",
                'contradiction_type': 'BLOCKED_VS_ACTIVE',
                'sms_quote': sms.get('quote', ''),
                'call_record': day_calls[0],
            })

        # Pattern 3: Missed/denied visit but zero calls logged all day
        elif event_type in _MISSED_VISIT_TYPES and not day_calls:
            contradictions.append({
                'date': date,
                'actor': sms.get('actor', ''),
                'sms_claim': sms.get('fact', ''),
                'call_log_fact': 'No calls recorded in log for this date',
                'contradiction_type': 'PICKUP_NO_CALL',
                'sms_quote': sms.get('quote', ''),
                'call_record': None,
            })

    return contradictions
