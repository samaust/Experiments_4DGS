"""Fake-credential fixtures only; prohibit real credential reads and sockets."""
import errno
import io
import logging
from pathlib import Path
import socket
import tempfile
import traceback
import unittest
from unittest import mock
from urllib.request import HTTPRedirectHandler, Request

from scripts.vipe_benchmark import hf_auth


class HFAuthTests(unittest.TestCase):
    URL = 'https://huggingface.co/facebook/sam3/resolve/pinned/model.safetensors'
    TOKEN = 'hf_fixturePrimary123'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.environ = {'HOME': str(self.root)}
        original_open = Path.open
        root = self.root
        def temporary_paths_only(path, *args, **kwargs):
            if not path.resolve().is_relative_to(root):
                raise AssertionError('fixture attempted to open a file outside its temporary directory')
            return original_open(path, *args, **kwargs)
        guard = mock.patch.object(Path, 'open', new=temporary_paths_only)
        guard.start()
        self.addCleanup(guard.stop)
        sockets = mock.patch.object(socket, 'create_connection', side_effect=AssertionError('network access prohibited'))
        self.connection = sockets.start()
        self.addCleanup(sockets.stop)

    def token_file(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode())
        return path

    def build(self, url=None, **environment):
        return hf_auth.build_hf_request(url or self.URL, environ={**self.environ, **environment})

    def assert_auth(self, request, token):
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + token)
        self.assertNotIn('Authorization', request.headers)
        self.assertEqual(request.unredirected_hdrs['Authorization'], 'Bearer ' + token)

    def test_allowed_origin_creates_a_get_with_unredirected_auth_only(self):
        request, used = self.build(HF_TOKEN=self.TOKEN)
        self.assertIsInstance(request, Request)
        self.assertIs(used, True)
        self.assertEqual(request.get_method(), 'GET')
        self.assertIsNone(request.data)
        self.assertEqual(request.full_url, self.URL)
        self.assert_auth(request, self.TOKEN)
        self.connection.assert_not_called()

    def test_origin_validation_precedes_any_environment_or_secret_access(self):
        class ForbiddenLookup(dict):
            def get(self, *args):
                raise AssertionError('credential lookup occurred before origin validation')
        urls = (
            'http://huggingface.co/model', 'https://example.invalid/model',
            'https://huggingface.co.evil.invalid/model', 'https://www.huggingface.co/model',
            'https://huggingface.co:444/model', 'https://huggingface.co./model',
            'https://user:password@huggingface.co/model', 'https://huggingface.co/model#fragment',
            '\nhttps://huggingface.co/model', 'https://huggingface.co/model\r\nHeader:value',
            'https://huggingface.co\\@evil.invalid/model', 'https://huggingface%2eco/model',
            '//huggingface.co/model', 'file:///tmp/token', 'https://huggingface.co:bad/model',
        )
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(hf_auth.HFAuthError):
                    hf_auth.build_hf_request(url, environ=ForbiddenLookup())

    def test_canonical_origin_accepts_case_and_explicit_https_port(self):
        request, used = self.build('https://HUGGINGFACE.CO:443/model', HF_TOKEN=self.TOKEN)
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_primary_environment_token_precedes_legacy_and_file(self):
        path = self.token_file('configured-token', 'hf_fixtureFile')
        request, used = self.build(HF_TOKEN=self.TOKEN, HUGGING_FACE_HUB_TOKEN='hf_fixtureLegacy', HF_TOKEN_PATH=str(path))
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_legacy_environment_token_precedes_file(self):
        path = self.token_file('configured-token', 'hf_fixtureFile')
        request, used = self.build(HF_TOKEN='', HUGGING_FACE_HUB_TOKEN='hf_fixtureLegacy', HF_TOKEN_PATH=str(path))
        self.assertTrue(used)
        self.assert_auth(request, 'hf_fixtureLegacy')

    def test_environment_token_does_not_resolve_or_read_file(self):
        with mock.patch.object(hf_auth, '_token_path', side_effect=AssertionError('unexpected path lookup')):
            request, used = self.build(HF_TOKEN=self.TOKEN)
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_absent_token_returns_plain_request_and_boolean_false(self):
        request, used = self.build()
        self.assertIs(used, False)
        self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(request.unredirected_hdrs, {})

    def test_disable_flag_prevents_environment_and_file_credential_lookup(self):
        for value in ('1', 'ON', 'yes', 'TrUe', ' true '):
            with self.subTest(value=value):
                class DisabledEnvironment(dict):
                    def get(self, key, default=None):
                        if key == 'HF_HUB_DISABLE_IMPLICIT_TOKEN':
                            return value
                        raise AssertionError('disabled auth accessed a credential source')
                request, used = hf_auth.build_hf_request(self.URL, environ=DisabledEnvironment())
                self.assertIs(used, False)
                self.assertIsNone(request.get_header('Authorization'))

    def test_false_disable_values_allow_existing_auth(self):
        for value in ('', '0', 'false', 'OFF', 'no'):
            with self.subTest(value=value):
                request, used = self.build(HF_TOKEN=self.TOKEN, HF_HUB_DISABLE_IMPLICIT_TOKEN=value)
                self.assertTrue(used)
                self.assert_auth(request, self.TOKEN)

    def test_explicit_token_path_precedes_hf_home_and_xdg(self):
        path = self.token_file('explicit/token-file', self.TOKEN)
        self.token_file('hub-home/token', 'hf_fixtureHome')
        self.token_file('xdg/huggingface/token', 'hf_fixtureXdg')
        request, used = self.build(HF_TOKEN_PATH=str(path), HF_HOME=str(self.root / 'hub-home'),
                                   XDG_CACHE_HOME=str(self.root / 'xdg'))
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_hf_home_precedes_xdg_and_default(self):
        self.token_file('hub-home/token', self.TOKEN)
        self.token_file('xdg/huggingface/token', 'hf_fixtureXdg')
        self.token_file('.cache/huggingface/token', 'hf_fixtureDefault')
        request, used = self.build(HF_HOME=str(self.root / 'hub-home'), XDG_CACHE_HOME=str(self.root / 'xdg'))
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_xdg_cache_home_precedes_default(self):
        self.token_file('xdg/huggingface/token', self.TOKEN)
        self.token_file('.cache/huggingface/token', 'hf_fixtureDefault')
        request, used = self.build(XDG_CACHE_HOME=str(self.root / 'xdg'))
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)

    def test_default_token_file_uses_only_the_supplied_temporary_home(self):
        path = self.token_file('.cache/huggingface/token', self.TOKEN)
        before = path.read_bytes()
        request, used = self.build()
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)
        self.assertEqual(path.read_bytes(), before)

    def test_tilde_and_environment_variables_follow_file_path_conventions(self):
        self.token_file('expanded/token', self.TOKEN)
        configurations = (
            dict(HF_TOKEN_PATH='~/expanded/token'),
            dict(HF_TOKEN_PATH='${HOME}/expanded/token'),
            dict(HF_HOME='$HOME/expanded'),
            dict(HF_HOME='~/expanded'),
        )
        for configuration in configurations:
            with self.subTest(configuration=configuration):
                request, used = self.build(**configuration)
                self.assertTrue(used)
                self.assert_auth(request, self.TOKEN)

    def test_trim_outer_newlines_and_spaces_but_reject_internal_separators(self):
        path = self.token_file('trimmed', ' \r\n\t' + self.TOKEN + '\r\n ')
        request, used = self.build(HF_TOKEN_PATH=str(path))
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)
        request, used = self.build(HF_TOKEN='\r\n ' + self.TOKEN + '\n')
        self.assertTrue(used)
        self.assert_auth(request, self.TOKEN)
        for value in ('hf_fixture\nother', 'hf_fixture\rHeader:value', 'hf_fixture token',
                      'hf_fixture\tother', 'hf_fixture\x00other', 'hf_fixture:other', '\u00e9secret'):
            with self.subTest(value=value):
                with self.assertRaises(hf_auth.HFAuthError) as caught:
                    self.build(HF_TOKEN=value)
                self.assertNotIn(value, str(caught.exception))

    def test_malformed_explicit_token_fails_without_falling_back_to_file(self):
        with mock.patch.object(hf_auth, '_token_path', side_effect=AssertionError('unexpected fallback')):
            with self.assertRaises(hf_auth.HFAuthError):
                self.build(HF_TOKEN='hf_fixture\nInjected:value', HUGGING_FACE_HUB_TOKEN='hf_validFake')

    def test_bearer_syntax_allows_existing_legacy_or_oauth_formats(self):
        for token in ('api_org_fixture', 'abc.def_ghi-jkl', 'abc+/~=='):
            with self.subTest(token=token):
                request, used = self.build(HF_TOKEN=token)
                self.assertTrue(used)
                self.assert_auth(request, token)

    def test_empty_file_and_empty_environment_tokens_remain_unauthenticated(self):
        path = self.token_file('empty-token', '\r\n ')
        request, used = self.build(HF_TOKEN='', HUGGING_FACE_HUB_TOKEN=' ', HF_TOKEN_PATH=str(path))
        self.assertFalse(used)
        self.assertIsNone(request.get_header('Authorization'))

    def test_oversized_or_non_ascii_file_is_rejected_without_secret_details(self):
        for index, value in enumerate((b'x' * (hf_auth._MAX_TOKEN_BYTES + 1), b'hf_fixture\xff')):
            with self.subTest(index=index):
                path = self.token_file(f'bad-{index}', value)
                with self.assertRaises(hf_auth.HFAuthError) as caught:
                    self.build(HF_TOKEN_PATH=str(path))
                self.assertNotIn('hf_fixture', repr(caught.exception))

    def test_prompts_token_paths_and_aliases_are_rejected_before_open(self):
        forbidden = self.root / 'prompts'
        forbidden.mkdir()
        alias = self.root / 'token-alias'
        alias.symlink_to(forbidden / 'token')
        with mock.patch.object(Path, 'open', side_effect=AssertionError('forbidden credential opened')):
            for path in (forbidden / 'token', alias):
                with self.subTest(path=path.name):
                    with self.assertRaisesRegex(ValueError, 'prompts'):
                        self.build(HF_TOKEN_PATH=str(path))

    def test_file_permission_error_keeps_errno_but_redacts_original_details(self):
        path = self.token_file('permission-token', self.TOKEN)
        with mock.patch.object(Path, 'open', side_effect=PermissionError(errno.EACCES, self.TOKEN)):
            with self.assertRaises(PermissionError) as caught:
                self.build(HF_TOKEN_PATH=str(path))
        self.assertEqual(caught.exception.errno, errno.EACCES)
        rendered = ''.join(traceback.format_exception(caught.exception))
        self.assertNotIn(self.TOKEN, rendered)
        self.assertNotIn(str(path), rendered)

    def test_request_metadata_repr_and_logging_do_not_reveal_credential(self):
        request, used = self.build(HF_TOKEN=self.TOKEN)
        self.assertIs(type(used), bool)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger('hf-auth-fixture')
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        logger.warning('request=%r metadata=%r', request, {'auth_used': used})
        self.assertNotIn(self.TOKEN, repr((request, used)))
        self.assertNotIn(self.TOKEN, str(request))
        self.assertNotIn(self.TOKEN, stream.getvalue())

    def test_default_urllib_redirect_does_not_forward_unredirected_auth(self):
        request, _ = self.build(HF_TOKEN=self.TOKEN)
        redirected = HTTPRedirectHandler().redirect_request(
            request, None, 302, 'Found', {}, 'https://cdn.example.invalid/model')
        self.assertIsNone(redirected.get_header('Authorization'))
        self.connection.assert_not_called()

    def test_same_hub_absolute_and_relative_redirects_keep_auth_unredirected(self):
        request, _ = self.build(HF_TOKEN=self.TOKEN)
        targets = (
            ('https://huggingface.co/next', 'https://huggingface.co/next'),
            ('https://HUGGINGFACE.CO:443/next', 'https://HUGGINGFACE.CO:443/next'),
            ('/next', 'https://huggingface.co/next'),
            ('../next', 'https://huggingface.co/facebook/sam3/resolve/next'),
        )
        handler = hf_auth.HFSafeRedirectHandler()
        for code in (301, 302, 303, 307, 308):
            for target, expected in targets:
                with self.subTest(code=code, target=target):
                    redirected = handler.redirect_request(request, None, code, 'Redirect', {}, target)
                    self.assertEqual(redirected.full_url, expected)
                    self.assert_auth(redirected, self.TOKEN)
        self.connection.assert_not_called()

    def test_cdn_third_party_and_other_port_redirects_never_receive_auth(self):
        request, _ = self.build(HF_TOKEN=self.TOKEN)
        handler = hf_auth.HFSafeRedirectHandler()
        for target in ('https://cdn-lfs.huggingface.co/file', 'https://cas-bridge.xethub.hf.co/file',
                       'https://third-party.invalid/file', 'https://huggingface.co:444/file', '//other.invalid/file'):
            with self.subTest(target=target):
                redirected = handler.redirect_request(request, None, 302, 'Found', {}, target)
                self.assertIsNone(redirected.get_header('Authorization'))
                self.assertNotIn(self.TOKEN, repr(redirected.header_items()))
        self.connection.assert_not_called()

    def test_cross_origin_bounce_cannot_restore_credential(self):
        request, _ = self.build(HF_TOKEN=self.TOKEN)
        handler = hf_auth.HFSafeRedirectHandler()
        outside = handler.redirect_request(request, None, 302, 'Found', {}, 'https://cdn.example.invalid/file')
        returned = handler.redirect_request(outside, None, 302, 'Found', {}, '/relative')
        back = handler.redirect_request(returned, None, 302, 'Found', {}, self.URL)
        self.assertIsNone(back.get_header('Authorization'))
        self.assertNotIn(self.TOKEN, repr(handler.__dict__))

    def test_redirect_discards_ordinary_authorization_header_even_on_hub(self):
        request = Request(self.URL, headers={'Authorization': 'Bearer ' + self.TOKEN})
        redirected = hf_auth.HFSafeRedirectHandler().redirect_request(request, None, 302, 'Found', {}, '/next')
        self.assertIsNone(redirected.get_header('Authorization'))

    def test_unsafe_redirects_fail_before_accessing_prior_credential(self):
        request, _ = self.build(HF_TOKEN=self.TOKEN)
        class ForbiddenHeaders(dict):
            def get(self, *args):
                raise AssertionError('unsafe redirect accessed a credential')
        request.unredirected_hdrs = ForbiddenHeaders()
        handler = hf_auth.HFSafeRedirectHandler()
        for target in ('http://huggingface.co/next', 'ftp://other.invalid/file',
                       'https://user@huggingface.co/next', '/next#fragment',
                       '\nhttps://huggingface.co/next', 'https://huggingface.co\\@other.invalid/next'):
            with self.subTest(target=target):
                with self.assertRaises(hf_auth.HFAuthError):
                    handler.redirect_request(request, None, 302, 'Found', {}, target)

    def test_opener_installs_one_safe_redirect_handler_without_network(self):
        with mock.patch('urllib.request.getproxies', return_value={}):
            opener = hf_auth.build_hf_opener()
        redirects = [handler for handler in opener.handlers if isinstance(handler, HTTPRedirectHandler)]
        self.assertEqual(len(redirects), 1)
        self.assertIsInstance(redirects[0], hf_auth.HFSafeRedirectHandler)
        self.connection.assert_not_called()


if __name__ == '__main__':
    unittest.main()
