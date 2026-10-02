#!/usr/bin/env python3
"""Tests for local-model routing, claw_worker batch handling and the mobile UI route."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import claw_worker
from timeline_extractor import chunk_text, generate_manifest
from timeline_extractor import extraction


class TestLocalModelRouting(unittest.TestCase):

    def test_base_url_strips_ollama_prefix(self):
        """Ollama/vLLM only know 'hermes3:latest' — sending 'ollama/hermes3:latest' 404s."""
        with mock.patch.object(extraction, 'call_openai', return_value='') as call:
            extraction.call_llm('p', 'c', model='ollama/hermes3:latest',
                                base_url='http://localhost:11434/v1')
        self.assertEqual(call.call_args.args[3], 'hermes3:latest')

    def test_base_url_keeps_plain_model(self):
        with mock.patch.object(extraction, 'call_openai', return_value='') as call:
            extraction.call_llm('p', 'c', model='NousResearch/Hermes-3', base_url='http://vllm:8000/v1')
        self.assertEqual(call.call_args.args[3], 'NousResearch/Hermes-3')

    def test_llm_timeout_env(self):
        with mock.patch.dict(os.environ, {'LOGSCRAPER_LLM_TIMEOUT': '900'}):
            self.assertEqual(extraction._llm_timeout(), 900.0)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(extraction._llm_timeout(), 120.0)

    def test_chunk_size_env(self):
        text = '\n'.join(['x' * 400] * 10)  # ~100 tokens per line
        with mock.patch.dict(os.environ, {'LOGSCRAPER_CHUNK_TOKENS': '250'}):
            self.assertEqual(len(list(chunk_text(text))), 5)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(len(list(chunk_text(text))), 1)


class TestLocalModelOutput(unittest.TestCase):
    """Small local models rarely return the bare table — these used to parse to zero events."""

    ROW = '2026-05-24 | 3:15 PM | Parent B | PICKUP_LATE | late | "traffic" | none'

    def test_preamble_and_fences(self):
        out = f"Here are the events:\n```\nDATE | TIME | ACTOR | EVENT_TYPE | FACT | QUOTE | LEGAL\n{self.ROW}\n```"
        events = extraction.parse_csv_output(out)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event_type'], 'PICKUP_LATE')

    def test_markdown_table(self):
        out = ("| DATE | TIME | ACTOR | EVENT_TYPE | FACT | QUOTE | LEGAL |\n"
               "|------|------|-------|------------|------|-------|-------|\n"
               f"| {self.ROW} |")
        events = extraction.parse_csv_output(out)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['date'], '2026-05-24')
        self.assertEqual(events[0]['legal_significance'], 'none')

    def test_markdown_call_table(self):
        out = ("| DATE | TIME | CALLER | RECIPIENT | CALL_TYPE | DURATION | ANSWERED | SIG |\n"
               "|---|---|---|---|---|---|---|---|\n"
               "| 2026-05-24 | 15:00 | A | B | OUTGOING | 0s | NO | unanswered |")
        events = extraction.parse_call_csv_output(out)
        self.assertEqual(events[0]['caller'], 'A')
        self.assertEqual(events[0]['answered'], 'NO')

    def test_plain_format_keeps_empty_first_field(self):
        out = "DATE|TIME|ACTOR|EVENT_TYPE|FACT|QUOTE|LEGAL\n|3:15 PM|B|PICKUP_LATE|late|q|sig"
        self.assertEqual(extraction.parse_csv_output(out)[0]['date'], '')

    def test_no_header_still_empty(self):
        self.assertEqual(extraction.parse_csv_output('I could not find any events.'), [])


class TestManifestInputFiles(unittest.TestCase):

    def test_all_files_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for name in ('a.txt', 'b.csv'):
                p = os.path.join(d, name)
                Path(p).write_text(name)
                paths.append(p)
            m = generate_manifest('c', input_files=paths)
        self.assertEqual([f['size_bytes'] for f in m['inputs']['all_files']], [5, 5])
        self.assertEqual(len(m['inputs']['all_files'][0]['sha256']), 64)

    def test_no_input_files_key_by_default(self):
        self.assertNotIn('all_files', generate_manifest('c')['inputs'])


class TestClawWorker(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.incoming, self.output = root / 'incoming', root / 'out'
        self.incoming.mkdir()
        patches = [
            mock.patch.object(claw_worker, 'INCOMING', self.incoming),
            mock.patch.object(claw_worker, 'OUTPUT', self.output),
            mock.patch.object(claw_worker, 'extract_timeline', return_value={
                'events': [{'date': '2026-05-24', 'event_type': 'VISIT_DENIED', 'fact': 'denied'}],
                'contradictions': [], 'summary': {},
            }),
            mock.patch.object(claw_worker, 'extract_call_log_events', return_value=[]),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    def drop(self, name, content='x', age=60):
        p = self.incoming / name
        p.write_text(content)
        past = time.time() - age
        os.utime(p, (past, past))
        return p

    def run_dir(self):
        dirs = [d for d in self.output.iterdir() if d.is_dir()]
        self.assertEqual(len(dirs), 1)
        return dirs[0]

    def test_idle_when_empty(self):
        self.assertIsNone(claw_worker.process_batch('case'))

    def test_claims_all_files_and_never_reprocesses(self):
        self.drop('thread1.txt', 'hello')
        self.drop('thread2.md')
        self.drop('calls.csv')
        self.assertTrue(claw_worker.process_batch('case'))

        run = self.run_dir()
        self.assertEqual(sorted(p.name for p in (run / 'inputs').iterdir()),
                         ['calls.csv', 'thread1.txt', 'thread2.md'])
        self.assertEqual(list(self.incoming.iterdir()), [])
        # Both SMS files went into one extraction, each under its own header
        sms_text = claw_worker.extract_timeline.call_args.args[0]
        self.assertIn('=== thread1.txt ===\nhello', sms_text)
        self.assertIn('=== thread2.md ===', sms_text)

        manifest = json.loads((run / 'case_manifest.json').read_text())
        self.assertEqual(len(manifest['inputs']['all_files']), 3)
        self.assertTrue((run / 'events.csv').exists())
        # Second pass finds nothing — files were claimed, not copied
        self.assertIsNone(claw_worker.process_batch('case'))

    def test_skips_files_still_uploading(self):
        self.drop('fresh.txt', age=0)
        self.assertIsNone(claw_worker.process_batch('case'))
        self.assertTrue((self.incoming / 'fresh.txt').exists())

    def test_skips_hidden_temp_and_unsupported(self):
        self.drop('.partial.txt')
        self.drop('~syncthing.txt')
        self.drop('photo.jpg')
        self.assertIsNone(claw_worker.process_batch('case'))
        self.assertEqual(len(list(self.incoming.iterdir())), 3)

    def test_failure_keeps_inputs_and_writes_reason(self):
        self.drop('thread.txt')
        claw_worker.extract_timeline.side_effect = RuntimeError('Ollama down')
        self.assertFalse(claw_worker.process_batch('case'))
        run = self.run_dir()
        self.assertIn('Ollama down', (run / 'FAILED.txt').read_text())
        self.assertTrue((run / 'inputs' / 'thread.txt').exists())

    def test_passes_local_endpoint(self):
        self.drop('calls.json')
        claw_worker.process_batch('case')
        kwargs = claw_worker.extract_call_log_events.call_args.kwargs
        self.assertEqual(kwargs['base_url'], claw_worker.OLLAMA_BASE_URL)
        self.assertEqual(kwargs['model'], claw_worker.HERMES_MODEL)

    @unittest.skipIf(claw_worker.fcntl is None, 'no fcntl on this platform')
    def test_lock_blocks_second_instance(self):
        first = claw_worker.acquire_lock()
        self.assertIsNotNone(first)
        self.assertIsNone(claw_worker.acquire_lock())
        first.close()


class TestMobileUI(unittest.TestCase):

    def test_serves_ui_with_escaped_model(self):
        import mobile_backend
        with mock.patch.object(mobile_backend, 'DEFAULT_MODEL', 'x"><script>'):
            page = mobile_backend.mobile_ui()
        self.assertIn('value="x&quot;&gt;&lt;script&gt;"', page)
        self.assertNotIn('__DEFAULT_MODEL__', page)

    def test_mounted_on_shared_api(self):
        import mobile_backend
        paths = {r.path for r in mobile_backend.app.routes}
        self.assertTrue({'/', '/api/extract-sms', '/api/extract-calls', '/health'} <= paths)


if __name__ == '__main__':
    unittest.main()
