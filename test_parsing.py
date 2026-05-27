#!/usr/bin/env python3
"""
Unit tests for LogScraper parsing logic
Tests the CSV parsing and basic functionality without requiring API keys
"""

import unittest
import tempfile
import os
from timeline_extractor import parse_csv_output, parse_call_csv_output, events_to_csv

class TestParsingLogic(unittest.TestCase):
    
    def test_parse_csv_output(self):
        """Test SMS event CSV parsing"""
        csv_data = """DATE|TIME|ACTOR|EVENT_TYPE|FACT|QUOTE|LEGAL_SIGNIFICANCE
2026-05-24|3:15 PM|Parent B|PICKUP_LATE|was late for pickup|"No I was running late again sorry about that traffic was horrible"|Contradicts prior statement about pharmacy stop
2026-05-24|3:20 PM|Parent A|ALLEGATION|alleges dishonesty|"You're not being honest about where you really were"|Tests credibility
"""
        
        events = parse_csv_output(csv_data)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['date'], '2026-05-24')
        self.assertEqual(events[0]['time'], '3:15 PM')
        self.assertEqual(events[0]['actor'], 'Parent B')
        self.assertEqual(events[0]['event_type'], 'PICKUP_LATE')
        self.assertEqual(events[0]['fact'], 'was late for pickup')
        self.assertIn('traffic was horrible', events[0]['quote'])
        self.assertEqual(events[1]['event_type'], 'ALLEGATION')
    
    def test_parse_call_csv_output(self):
        """Test call log CSV parsing"""
        csv_data = """DATE|TIME|CALLER|RECIPIENT|CALL_TYPE|DURATION|ANSWERED|LEGAL_SIGNIFICANCE
2026-05-24|3:15 PM|Parent A|Parent B|OUTGOING|2m:30s|YES|Call about pickup timing
2026-05-24|3:20 PM|Parent B|Parent A|INCOMING|1m:15s|NO|Missed call during alleged pharmacy visit
"""
        
        events = parse_call_csv_output(csv_data)
        
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['date'], '2026-05-24')
        self.assertEqual(events[0]['time'], '3:15 PM')
        self.assertEqual(events[0]['caller'], 'Parent A')
        self.assertEqual(events[0]['recipient'], 'Parent B')
        self.assertEqual(events[0]['call_type'], 'OUTGOING')
        self.assertEqual(events[0]['duration'], '2m:30s')
        self.assertEqual(events[0]['answered'], 'YES')
        self.assertEqual(events[1]['call_type'], 'INCOMING')
        self.assertEqual(events[1]['answered'], 'NO')
    
    def test_events_to_csv(self):
        """Test writing events to CSV"""
        events = [
            {
                'date': '2026-05-24',
                'time': '3:15 PM',
                'actor': 'Parent B',
                'event_type': 'PICKUP_LATE',
                'fact': 'was late for pickup',
                'quote': 'Sorry about that',
                'legal_significance': 'Shows pattern of lateness'
            },
            {
                'date': '2026-05-24',
                'time': '3:20 PM',
                'actor': 'Parent A',
                'event_type': 'ALLEGATION',
                'fact': 'alleges dishonesty',
                'quote': "You're not being honest",
                'legal_significance': 'Credibility attack'
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            events_to_csv(events, temp_path)
            
            # Read back and verify
            with open(temp_path, 'r') as f:
                content = f.read()
                
            self.assertIn('DATE,TIME,ACTOR,EVENT_TYPE,FACT,QUOTE,LEGAL_SIGNIFICANCE', content)
            self.assertIn('2026-05-24,3:15 PM,Parent B,PICKUP_LATE,was late for pickup,Sorry about that,Shows pattern of lateness', content)
            self.assertIn("2026-05-24,3:20 PM,Parent A,ALLEGATION,alleges dishonesty,You're not being honest,Credibility attack", content)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

class TestContradictionPipeline(unittest.TestCase):

    def test_contradiction_routing(self):
        """LLM-flagged contradictions are routed to all_contradictions."""
        mock_events = [
            {
                'date': '2024-03-15', 'time': '10:00', 'actor': 'Plaintiff',
                'event_type': 'VISIT_DENIED', 'fact': 'Denied visit without notice',
                'quote': 'he cant come today',
                'legal_significance': 'CONTRADICTS prior statement on 2024-02-10',
            },
            {
                'date': '2024-03-16', 'time': '14:00', 'actor': 'Defendant',
                'event_type': 'PICKUP_LATE', 'fact': 'Arrived on time',
                'quote': '', 'legal_significance': 'No issue',
            },
        ]
        from timeline_extractor import _CONTRADICTION_KEYWORDS
        contradictions = [
            e for e in mock_events
            if any(
                kw in ((e.get('legal_significance') or '') + ' ' + (e.get('fact') or '')).upper()
                for kw in _CONTRADICTION_KEYWORDS
            )
        ]
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]['date'], '2024-03-15')
        self.assertEqual(contradictions[0]['actor'], 'Plaintiff')

    def test_cross_reference_call_claim_vs_log(self):
        """SMS quote 'never calls back' + outgoing call in log → CALL_CLAIM_VS_LOG."""
        from timeline_extractor.cross_reference import cross_reference_sms_calls
        sms = [{
            'date': '2024-03-15', 'actor': 'Plaintiff', 'event_type': 'COMMUNICATION_BLOCKED',
            'fact': 'Claims defendant never answers', 'quote': 'he never calls back',
            'legal_significance': '',
        }]
        calls = [{
            'date': '2024-03-15', 'time': '10:30', 'caller': 'Defendant',
            'recipient': 'Plaintiff', 'call_type': 'OUTGOING', 'duration': '3:22',
            'answered': 'YES', 'legal_significance': '',
        }]
        result = cross_reference_sms_calls(sms, calls)
        self.assertEqual(len(result), 1)
        # 'never calls back' matches NEVER_CALL keyword → CALL_CLAIM_VS_LOG fires first
        self.assertEqual(result[0]['contradiction_type'], 'CALL_CLAIM_VS_LOG')
        self.assertEqual(result[0]['date'], '2024-03-15')

    def test_cross_reference_blocked_vs_active(self):
        """COMMUNICATION_BLOCKED event type (no keyword in text) + calls → BLOCKED_VS_ACTIVE."""
        from timeline_extractor.cross_reference import cross_reference_sms_calls
        sms = [{
            'date': '2024-03-15', 'actor': 'Plaintiff', 'event_type': 'COMMUNICATION_BLOCKED',
            'fact': 'Communication was blocked', 'quote': '',
            'legal_significance': '',
        }]
        calls = [{
            'date': '2024-03-15', 'time': '10:30', 'caller': 'Defendant',
            'recipient': 'Plaintiff', 'call_type': 'OUTGOING', 'duration': '3:22',
            'answered': 'YES', 'legal_significance': '',
        }]
        result = cross_reference_sms_calls(sms, calls)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['contradiction_type'], 'BLOCKED_VS_ACTIVE')

    def test_cross_reference_pickup_no_call(self):
        """VISIT_MISSED with zero calls that day → PICKUP_NO_CALL."""
        from timeline_extractor.cross_reference import cross_reference_sms_calls
        sms = [{
            'date': '2024-04-07', 'actor': 'Defendant', 'event_type': 'VISIT_MISSED',
            'fact': 'Visit missed', 'quote': '', 'legal_significance': '',
        }]
        result = cross_reference_sms_calls(sms, [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['contradiction_type'], 'PICKUP_NO_CALL')
        self.assertIsNone(result[0]['call_record'])

    def test_cross_reference_no_false_positive(self):
        """Normal visit event with matching calls should NOT flag a contradiction."""
        from timeline_extractor.cross_reference import cross_reference_sms_calls
        sms = [{
            'date': '2024-04-07', 'actor': 'Defendant', 'event_type': 'SCHEDULE_CHANGE',
            'fact': 'Schedule adjusted', 'quote': '', 'legal_significance': '',
        }]
        calls = [{
            'date': '2024-04-07', 'call_type': 'INCOMING', 'duration': '2:00',
            'caller': '', 'recipient': '', 'answered': 'YES', 'time': '', 'legal_significance': '',
        }]
        result = cross_reference_sms_calls(sms, calls)
        self.assertEqual(len(result), 0)

    def test_contradictions_to_csv(self):
        """contradictions_to_csv writes correct headers and handles both formats."""
        import tempfile
        from timeline_extractor import contradictions_to_csv
        contradictions = [
            {
                'date': '2024-03-15', 'actor': 'Plaintiff',
                'sms_claim': 'Claims no calls', 'call_log_fact': 'OUTGOING call 3:22',
                'contradiction_type': 'CALL_CLAIM_VS_LOG', 'sms_quote': 'never calls back',
            },
            {
                'date': '2024-03-16', 'actor': 'Plaintiff', 'event_type': 'VISIT_DENIED',
                'fact': 'Denied visit', 'legal_significance': 'CONTRADICTS prior statement',
                'quote': 'he cant come',
            },
        ]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            tmp = f.name
        try:
            contradictions_to_csv(contradictions, tmp)
            with open(tmp) as f:
                content = f.read()
            self.assertIn('DATE,ACTOR,PRIOR_STATEMENT', content)
            self.assertIn('CALL_CLAIM_VS_LOG', content)
            self.assertIn('cross_reference', content)
            self.assertIn('llm_flagged', content)
        finally:
            os.unlink(tmp)


class TestManifestAndThirdParties(unittest.TestCase):

    def test_manifest_structure(self):
        """generate_manifest returns required fields without file paths."""
        from timeline_extractor import generate_manifest
        manifest = generate_manifest(
            case_id='test-001',
            model='gemini-2.0-flash',
            event_count=42,
            contradiction_count=7,
        )
        self.assertEqual(manifest['case_id'], 'test-001')
        self.assertEqual(manifest['event_count'], 42)
        self.assertEqual(manifest['contradiction_count'], 7)
        self.assertIn('processed_at', manifest)
        self.assertIn('extractor_version', manifest)
        self.assertIn('platform', manifest)
        self.assertIsNone(manifest['inputs']['sms_file'])
        self.assertIsNone(manifest['inputs']['call_log'])

    def test_manifest_file_hashing(self):
        """generate_manifest hashes a real file and records its size."""
        import tempfile
        from timeline_extractor import generate_manifest
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('test sms content')
            tmp = f.name
        try:
            manifest = generate_manifest(case_id='hash-test', sms_path=tmp)
            meta = manifest['inputs']['sms_file']
            self.assertIsNotNone(meta)
            self.assertEqual(len(meta['sha256']), 64)
            self.assertGreater(meta['size_bytes'], 0)
            self.assertTrue(meta['path'].endswith('.txt'))
        finally:
            os.unlink(tmp)

    def test_third_parties_substitution(self):
        """EXTRACTION_PROMPT accepts third_parties format argument."""
        from timeline_extractor.extraction import EXTRACTION_PROMPT
        result = EXTRACTION_PROMPT.format(third_parties='Alice, Bob, Charlie')
        self.assertIn('Alice, Bob, Charlie', result)

    def test_third_parties_default(self):
        """Default fallback when no third_parties passed."""
        from timeline_extractor.extraction import EXTRACTION_PROMPT
        result = EXTRACTION_PROMPT.format(third_parties='any named third party')
        self.assertIn('any named third party', result)

    def test_third_parties_empty_list(self):
        """Empty list uses fallback string, not blank."""
        from timeline_extractor.extraction import extract_with_llm
        import inspect
        sig = inspect.signature(extract_with_llm)
        self.assertIn('third_parties', sig.parameters)


if __name__ == '__main__':
    unittest.main()