"""Offline regression checks; never use saved credentials or contact CMS."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import requests
from requests_ntlm import HttpNtlmAuth

spec = importlib.util.spec_from_file_location('cms_test', Path(__file__).resolve().parents[1] / 'cms_downloader.py')
cms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cms)


class LoginAndDownloadTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(cms.SESSION_CREDS, username='student', password=' test secret '))
        self.stack.enter_context(patch.object(cms, 'ERROR_LOG', []))
        self.stack.enter_context(patch.object(cms.time, 'sleep'))
        self.session = self.stack.enter_context(patch('requests.Session')).return_value.__enter__.return_value
        self.response = self.session.get.return_value.__enter__.return_value
        self.response.status_code = 200
        self.response.text = '<html>courses</html>'
        self.response.iter_content.return_value = [b'course ', b'material']
        self.folder = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.target = Path(self.folder) / 'lecture.pdf'

    def test_page_fetch_uses_ntlm_without_redirects(self):
        self.assertEqual(cms._request('https://cms.example/page'), ('200', '<html>courses</html>'))
        self.assertIsInstance(self.session.auth, HttpNtlmAuth)
        self.assertFalse(self.session.get.call_args.kwargs['allow_redirects'])

    def test_complete_download_replaces_file(self):
        self.target.write_bytes(b'old')
        code, _ = cms._request('https://cms.example/file', self.target)
        self.assertEqual(code, '200')
        self.assertEqual(self.target.read_bytes(), b'course material')
        self.assertFalse(Path(str(self.target) + '.part').exists())

    def test_rejected_responses_preserve_file(self):
        for status in (302, 401, 403, 500):
            with self.subTest(status=status):
                self.target.write_bytes(b'old')
                self.response.status_code = status
                self.assertEqual(cms._request('https://cms.example/file', self.target)[0], str(status))
                self.assertEqual(self.target.read_bytes(), b'old')

    def test_interrupted_transfer_preserves_file_and_cleans_partial(self):
        self.target.write_bytes(b'old')
        def chunks(**kwargs):
            yield b'partial'
            raise requests.exceptions.ConnectionError('connection lost')
        self.response.iter_content.side_effect = chunks
        self.assertEqual(cms._request('https://cms.example/file', self.target, retries=1)[0], 'CONN_ERROR')
        self.assertEqual(self.target.read_bytes(), b'old')
        self.assertFalse(Path(str(self.target) + '.part').exists())

    def test_empty_transfer_preserves_file(self):
        self.target.write_bytes(b'old')
        self.response.iter_content.return_value = []
        self.assertEqual(cms._request('https://cms.example/file', self.target, retries=1)[0], 'ERROR')
        self.assertEqual(self.target.read_bytes(), b'old')

    def test_timeout_retries_and_reports_reason(self):
        self.session.get.side_effect = requests.exceptions.Timeout()
        self.assertEqual(cms._request('https://cms.example', timeout=7, retries=2), ('TIMEOUT', 'Timeout after 7s'))
        self.assertEqual(self.session.get.call_count, 2)

    def test_certificate_failure_is_explicit(self):
        self.session.get.side_effect = requests.exceptions.SSLError('certificate failed')
        code, message = cms._request('https://cms.example')
        self.assertEqual(code, 'ERROR')
        self.assertIn('certificate', message)
        self.assertEqual(self.session.get.call_count, 1)

    def test_transport_error_redacts_password(self):
        self.session.get.side_effect = requests.exceptions.ConnectionError('failed test secret here')
        code, message = cms._request('https://cms.example', retries=1)
        self.assertEqual(code, 'CONN_ERROR')
        self.assertNotIn(cms.get_password(), message)
        self.assertNotIn(cms.get_password(), str(cms.ERROR_LOG))

    def test_missing_credentials_make_no_request(self):
        cms.SESSION_CREDS['password'] = ''
        self.assertEqual(cms._request('https://cms.example')[0], 'NO_CREDS')
        self.session.get.assert_not_called()

    def test_successful_signin_saves_exact_password(self):
        with patch('builtins.input', return_value='student'), patch.object(cms, 'prompt_password', return_value=' new password '), patch.object(cms, 'test_connection', return_value=(True, 'OK')), patch.object(cms, 'save_current_credentials') as save, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(cms.sign_in())
            self.assertEqual(cms.get_password(), ' new password ')
            save.assert_called_once()

    def test_missing_dependencies_fail_before_signin(self):
        with patch.dict(sys.modules, {'requests_ntlm': None}), patch.object(cms, 'load_settings'), patch.object(cms, 'sign_in') as signin, patch.object(sys, 'argv', ['cms_downloader.py', '--no-pause']), contextlib.redirect_stdout(io.StringIO()) as output:
            cms.main()
        signin.assert_not_called()
        self.assertIn(sys.executable, output.getvalue())
        self.assertIn('-m pip install', output.getvalue())


class PasswordPromptTests(unittest.TestCase):
    def read(self, keys):
        chars = iter(keys)
        with patch.object(cms.os, 'name', 'nt'), patch.object(cms.sys, 'stdin', SimpleNamespace(isatty=lambda: True)), patch.dict(sys.modules, {'msvcrt': SimpleNamespace(getwch=lambda: next(chars))}), contextlib.redirect_stdout(io.StringIO()) as output:
            value = cms.prompt_password()
        return value, output.getvalue()

    def test_masking_backspace_special_keys_and_spaces(self):
        value, output = self.read(list(' secretX') + ['\b', '\x00', 'K'] + list('! ') + ['\r'])
        self.assertEqual(value, ' secret! ')
        self.assertIn('*', output)
        self.assertNotIn('secret', output)

    def test_empty_password_and_backspace(self):
        self.assertEqual(self.read(['\b', '\r'])[0], '')

    def test_cancellation(self):
        for char, error in [('\x03', KeyboardInterrupt), ('\x1a', EOFError)]:
            with self.subTest(char=char), self.assertRaises(error):
                self.read([char])

    def test_hidden_fallback_preserves_spaces(self):
        with patch.object(cms.os, 'name', 'posix'), patch.object(cms.getpass, 'getpass', return_value=' secret '), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cms.prompt_password(), ' secret ')


if __name__ == '__main__':
    unittest.main()
