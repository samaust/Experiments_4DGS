"""Existing Hugging Face credentials for explicit, read-only urllib requests.

No credentials are accessed at import, refreshed, written, or logged. This
module makes no network calls. Callers receive a Request and an auth-used bool;
they must not serialize the Request's headers. Only canonical HTTPS Hub URLs
may initiate credential lookup. The optional opener preserves auth on same-Hub
redirects, without forwarding it to CDNs or keeping credential state itself.
"""
import os
from pathlib import Path
import re
import stat
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .files import safe_path


class HFAuthError(ValueError):
    """Credential/origin errors with messages that never include secret values."""


_TRUE = frozenset(('1', 'ON', 'YES', 'TRUE'))
_MAX_TOKEN_BYTES = 8192
_BEARER = re.compile(r'[A-Za-z0-9._~+/-]+=*\Z')
_VARIABLE = re.compile(r'\$(?:\{([^}]+)\}|([A-Za-z0-9_]+))')


def _url_text(url):
    if (not isinstance(url, str) or not url or '\\' in url or
            any(ord(char) <= 32 or ord(char) >= 127 for char in url)):
        raise HFAuthError('An explicit, safely encoded HTTPS URL is required')


def _https_parts(url):
    _url_text(url)
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise HFAuthError('The HTTPS URL origin is invalid') from None
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None or
            parts.password is not None or parts.fragment or port == 0):
        raise HFAuthError('An HTTPS URL without user information or fragments is required')
    return parts


def _hub_origin(parts):
    return parts.hostname == 'huggingface.co' and parts.port in (None, 443)


def _home(environ):
    value = environ.get('HOME')
    return Path(value) if value else Path.home()


def _expanded_path(value, environ):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise HFAuthError('The configured Hugging Face credential path is invalid')
    try:
        if value == '~' or value.startswith('~/'):
            value = str(_home(environ)) + value[1:]
        elif value.startswith('~'):
            value = str(Path(value).expanduser())
        # Follow the Hub's expanduser-then-expandvars path convention, using
        # only the supplied mapping when tests provide an isolated environment.
        value = _VARIABLE.sub(lambda match: environ.get(match[1] or match[2], match[0]), value)
        return safe_path(value)
    except (OSError, RuntimeError, TypeError):
        raise HFAuthError('The configured Hugging Face credential path is invalid') from None


def _token_path(environ):
    explicit = environ.get('HF_TOKEN_PATH')
    if explicit:
        return _expanded_path(explicit, environ)
    home = environ.get('HF_HOME')
    if home:
        return safe_path(_expanded_path(home, environ) / 'token')
    cache = environ.get('XDG_CACHE_HOME')
    base = _expanded_path(cache, environ) if cache else safe_path(_home(environ) / '.cache')
    return safe_path(base / 'huggingface' / 'token')


def _clean_token(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > _MAX_TOKEN_BYTES:
        raise HFAuthError('The existing Hugging Face credential has invalid formatting')
    value = value.strip(' \t\r\n')
    if not value:
        return None
    # Accept bearer-token syntax without assuming a particular HF token prefix
    # or exposing the supplied value. Internal whitespace/control bytes fail.
    if _BEARER.fullmatch(value) is None:
        raise HFAuthError('The existing Hugging Face credential has invalid formatting')
    return value


def _existing_token(environ):
    for name in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN'):
        token = _clean_token(environ.get(name))
        if token is not None:
            return token
    path = _token_path(environ)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise HFAuthError('The existing Hugging Face credential is not a regular file')
        with path.open('rb') as stream:
            data = stream.read(_MAX_TOKEN_BYTES + 1)
    except FileNotFoundError:
        return None
    except OSError as exc:
        # Preserve the errno and PermissionError type for the caller's access
        # policy, but omit the configured path and any original exception text.
        raise OSError(exc.errno, 'Unable to read the existing Hugging Face credential file') from None
    if len(data) > _MAX_TOKEN_BYTES or any(byte >= 128 for byte in data):
        raise HFAuthError('The existing Hugging Face credential has invalid formatting')
    return _clean_token(data.decode('ascii'))


def build_hf_request(url, *, environ=None):
    """Return (GET Request, auth_used_bool), using existing credentials only.

    HF_TOKEN precedes HUGGING_FACE_HUB_TOKEN, followed by HF_TOKEN_PATH or the
    token under HF_HOME / XDG_CACHE_HOME / ~/.cache/huggingface. Setting
    HF_HUB_DISABLE_IMPLICIT_TOKEN to 1/ON/YES/TRUE disables all implicit lookup.
    Pass the Request to build_hf_opener().open to retain same-origin redirects.
    """
    if not _hub_origin(_https_parts(url)):
        raise HFAuthError('Existing Hugging Face credentials require https://huggingface.co on port 443')
    environ = os.environ if environ is None else environ
    request = Request(url, method='GET')
    disabled = environ.get('HF_HUB_DISABLE_IMPLICIT_TOKEN', '')
    if isinstance(disabled, str) and disabled.strip().upper() in _TRUE:
        return request, False
    token = _existing_token(environ)
    if token is not None:
        request.add_unredirected_header('Authorization', 'Bearer ' + token)
    return request, token is not None


class HFSafeRedirectHandler(HTTPRedirectHandler):
    """Keep auth unredirected-only, and carry it solely within the HTTPS Hub."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate a redirect before inspecting the prior credential. Reject
        # downgrades, userinfo, controls and fragments even without auth.
        _url_text(newurl)
        target = urljoin(req.full_url, newurl)
        target_parts = _https_parts(target)
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is None:
            return None
        redirected.remove_header('Authorization')
        if _hub_origin(target_parts) and _hub_origin(_https_parts(req.full_url)):
            authorization = req.unredirected_hdrs.get('Authorization')
            if authorization is not None:
                redirected.add_unredirected_header('Authorization', authorization)
        return redirected


def build_hf_opener():
    """Build an opener without making requests or retaining any credential."""
    return build_opener(HFSafeRedirectHandler())
