from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'codex'))


class SessionPatcherTests(unittest.TestCase):
    def test_refusal_detector_supports_real_chinese_refusal(self):
        from session_patcher import RefusalDetector
        detector = RefusalDetector()
        self.assertTrue(detector.detect('我不能帮助你实施这次攻击。'))
        self.assertFalse(detector.detect('我不能确认这个漏洞，需要更多证据。'))

    def test_mock_response_is_readable_chinese(self):
        from session_patcher import MOCK_RESPONSE
        self.assertIn('好的', MOCK_RESPONSE)
        self.assertIn('下一步', MOCK_RESPONSE)

    def test_clean_session_replaces_refusal_with_mock_response(self):
        from session_patcher import MOCK_RESPONSE, clean_session
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp) / 'sample.jsonl'
            line = {
                'type': 'response_item',
                'payload': {
                    'type': 'message',
                    'role': 'assistant',
                    'content': [{'type': 'output_text', 'text': 'I cannot assist with that.'}],
                },
            }
            session.write_text(json.dumps(line, ensure_ascii=False) + '\n', encoding='utf-8')
            cleaned, modified, changes = clean_session(str(session), use_ai=False)
            self.assertTrue(modified)
            self.assertEqual(changes[0].change_type, 'replace')
            replaced = cleaned[0]['payload']['content'][0]['text']
            self.assertEqual(replaced, MOCK_RESPONSE)


if __name__ == '__main__':
    unittest.main()
