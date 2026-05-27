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

if __name__ == '__main__':
    unittest.main()