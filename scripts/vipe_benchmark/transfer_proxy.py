"""Run-scoped, byte-bounded CONNECT proxy for UV acquisition.

The tunnel forwards opaque TLS bytes; it neither terminates TLS nor records
request contents. One selector thread owns the shared download lock and every
upstream recv. Before each recv it persists a reservation; a crash retains that
charge instead of losing an unrecorded read. The received counter is monotonic.
No connection or request is retried. All UV invocations must use environment.

Wire accounting includes TLS overhead. Acquisition is the larger of cumulative
metered bytes and the retained extracted cache/managed-Python footprint. Socket
and operating-system transport buffers are not additional application reads.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import errno
import selectors
import socket
import threading
import time
import uuid

from .budgets import _publish_counter, download_lock, download_remaining
from .files import safe_path, write_json


class TransferProxyError(RuntimeError):
    pass


def _atomic_counter(path, value):
    """Replace only this session's mutable meter, durably before socket reads."""
    _publish_counter(path, value)


@dataclass(eq=False)
class _Tunnel:
    client: socket.socket
    upstream: socket.socket | None = None
    request: bytearray = field(default_factory=bytearray)
    to_client: bytearray = field(default_factory=bytearray)
    to_upstream: bytearray = field(default_factory=bytearray)
    client_eof: bool = False
    upstream_eof: bool = False
    client_write_closed: bool = False
    upstream_write_closed: bool = False


class _UVProxy:
    _CHUNK = 2**20
    _BUFFER = 2**21
    _HEADERS = 2**16

    def __init__(self, run_root, download_limit, artifact_limit=None, *, allowed_ports=(443,)):
        self.run_root = safe_path(run_root).resolve()
        if type(download_limit) is not int or download_limit < 0:
            raise ValueError('download_limit must be a nonnegative integer')
        if artifact_limit is not None and (type(artifact_limit) is not int or artifact_limit < 0):
            raise ValueError('artifact_limit must be a nonnegative integer')
        self.download_limit, self.artifact_limit = download_limit, artifact_limit
        self.allowed_ports = frozenset(allowed_ports)
        if not self.allowed_ports or any(type(p) is not int or not 1 <= p <= 65535 for p in self.allowed_ports):
            raise ValueError('allowed_ports must contain valid TCP ports')
        self.transfer_id = uuid.uuid4().hex
        self.received = self.reserved = self.connections = 0
        self._ready, self._stop = threading.Event(), threading.Event()
        self._thread = self._selector = self._listener = None
        self._tunnels = set()
        self._error = self._command_error = None
        self._environment = None
        self._start = time.monotonic()
        self._started_utc = datetime.now(timezone.utc).isoformat()
        self._meter = self.run_root / 'uv-transfers' / f'active-{self.transfer_id}.json'
        self._receipt = self.run_root / 'uv-transfers' / f'transfer-{self.transfer_id}.json'

    @property
    def environment(self):
        if self._environment is None:
            raise TransferProxyError('proxy environment is unavailable before context entry')
        return dict(self._environment)

    def _record(self):
        return dict(transfer_id=self.transfer_id, bytes_received=self.received,
                    reserved_bytes=self.reserved, started_utc=self._started_utc,
                    wall_seconds=time.monotonic() - self._start,
                    transport='opaque-TLS-over-HTTP-CONNECT', automatic_retries=0,
                    upstream_connections=self.connections, worker_threads=1)

    def _publish(self):
        _atomic_counter(self._meter, self._record())

    def _remaining(self):
        return download_remaining(self.run_root, self.download_limit,
            uv_transfer_id=self.transfer_id, bytes_received=self.received + self.reserved,
            artifact_limit=self.artifact_limit)

    def _recv(self, upstream, count):
        available = self._remaining()
        if available <= 0:
            raise TransferProxyError('download or artifact allocation exhausted before upstream recv')
        count = min(count, available)
        self.reserved = count
        self._publish()  # A crash after this point keeps the full admitted read.
        try:
            block = upstream.recv(count)
        except BlockingIOError:
            self.reserved = 0  # A nonblocking would-block result consumed no bytes.
            self._publish()
            return None
        if len(block) > count:
            raise TransferProxyError('upstream returned more than the reserved byte count')
        self.received += len(block)
        self.reserved = 0
        self._publish()  # Publish actual bytes before forwarding them to UV.
        return block

    def _connect(self, tunnel):
        request, remainder = bytes(tunnel.request).split(b'\r\n\r\n', 1)
        try:
            method, authority, version = request.split(b'\r\n', 1)[0].decode('ascii').split(' ')
            if method != 'CONNECT' or version not in ('HTTP/1.0', 'HTTP/1.1'):
                raise ValueError('only HTTP CONNECT is supported')
            if authority.startswith('['):
                host, suffix = authority[1:].split(']', 1)
                if not suffix.startswith(':'):
                    raise ValueError('CONNECT must specify a port')
                port = int(suffix[1:])
            else:
                host, raw_port = authority.rsplit(':', 1)
                port = int(raw_port)
            if not host or any(c in host for c in '/\\@?#\t\r\n ') or port not in self.allowed_ports:
                raise ValueError('CONNECT target or port is not admitted')
        except (ValueError, UnicodeDecodeError) as exc:
            raise TransferProxyError(f'invalid CONNECT request: {exc}') from exc
        if self._remaining() <= 0:
            raise TransferProxyError('download or artifact allocation exhausted before CONNECT')
        # Exactly one address/connection attempt. No hidden multi-address retry.
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not addresses:
            raise TransferProxyError('CONNECT target has no stream address')
        family, kind, protocol, _, address = addresses[0]
        upstream = socket.socket(family, kind, protocol)
        tunnel.upstream = upstream
        upstream.settimeout(5)
        self.connections += 1
        upstream.connect(address)
        upstream.setblocking(False)
        tunnel.to_client.extend(b'HTTP/1.1 200 Connection Established\r\n\r\n')
        tunnel.to_upstream.extend(remainder)
        tunnel.request.clear()

    def _registration(self, endpoint, events, data):
        try:
            self._selector.get_key(endpoint)
        except KeyError:
            if events:
                self._selector.register(endpoint, events, data)
        else:
            if events:
                self._selector.modify(endpoint, events, data)
            else:
                self._selector.unregister(endpoint)

    @staticmethod
    def _shutdown_write(tunnel, side):
        try:
            getattr(tunnel, side).shutdown(socket.SHUT_WR)
        except OSError as exc:
            if exc.errno != errno.ENOTCONN:
                raise
            # The opposite direction reached EOF and this output queue has
            # drained. A peer close can finish before our half-close; retire
            # the disconnected direction without another send or recv.
            setattr(tunnel, side + '_eof', True)
        setattr(tunnel, side + '_write_closed', True)

    def _sync(self, tunnel):
        if tunnel.upstream is None:
            self._registration(tunnel.client, selectors.EVENT_READ, (tunnel, 'client'))
            return
        if tunnel.client_eof and not tunnel.to_upstream and not tunnel.upstream_write_closed:
            self._shutdown_write(tunnel, 'upstream')
        if tunnel.upstream_eof and not tunnel.to_client and not tunnel.client_write_closed:
            self._shutdown_write(tunnel, 'client')
        if tunnel.client_eof and tunnel.upstream_eof and not tunnel.to_client and not tunnel.to_upstream:
            self._close(tunnel)
            return
        client_events = selectors.EVENT_READ if not tunnel.client_eof and len(tunnel.to_upstream) < self._BUFFER else 0
        upstream_events = selectors.EVENT_READ if not tunnel.upstream_eof and len(tunnel.to_client) < self._BUFFER else 0
        if tunnel.to_client:
            client_events |= selectors.EVENT_WRITE
        if tunnel.to_upstream:
            upstream_events |= selectors.EVENT_WRITE
        self._registration(tunnel.client, client_events, (tunnel, 'client'))
        self._registration(tunnel.upstream, upstream_events, (tunnel, 'upstream'))

    def _close(self, tunnel):
        self._tunnels.discard(tunnel)
        for endpoint in (tunnel.client, tunnel.upstream):
            if endpoint is None:
                continue
            try:
                self._selector.unregister(endpoint)
            except KeyError:
                pass
            endpoint.close()

    def _event(self, tunnel, side, events):
        endpoint = getattr(tunnel, side)
        # A different endpoint's event in this selector batch may already
        # have closed a direction. Do not act on its stale readiness flags.
        if events & selectors.EVENT_WRITE and not getattr(tunnel, side + '_write_closed'):
            queue = tunnel.to_client if side == 'client' else tunnel.to_upstream
            try:
                sent = endpoint.send(queue)
            except BlockingIOError:
                sent = 0
            del queue[:sent]
        if events & selectors.EVENT_READ and not getattr(tunnel, side + '_eof'):
            if side == 'client':
                count = min(self._CHUNK, self._BUFFER - len(tunnel.to_upstream))
                if tunnel.upstream is None:
                    count = min(count, self._HEADERS - len(tunnel.request))
                    if count <= 0:
                        raise TransferProxyError('CONNECT headers exceed the admitted size')
                try:
                    block = endpoint.recv(count)
                except BlockingIOError:
                    block = None
            else:
                block = self._recv(endpoint, min(self._CHUNK, self._BUFFER - len(tunnel.to_client)))
            if block == b'':
                if side == 'client' and tunnel.upstream is None:
                    raise TransferProxyError('client ended before completing CONNECT')
                setattr(tunnel, side + '_eof', True)
            elif block:
                if side == 'client' and tunnel.upstream is None:
                    tunnel.request.extend(block)
                    if b'\r\n\r\n' in tunnel.request:
                        self._connect(tunnel)
                else:
                    (tunnel.to_upstream if side == 'client' else tunnel.to_client).extend(block)
        self._sync(tunnel)

    def _serve_locked(self):
        if self._meter.parent.is_symlink():
            raise TransferProxyError('UV meter directory cannot use a symbolic link')
        self._meter.parent.mkdir(parents=True, exist_ok=True)
        self._publish()
        self._selector = selectors.DefaultSelector()
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(('127.0.0.1', 0))
        self._listener.listen(16)
        self._listener.setblocking(False)
        self._selector.register(self._listener, selectors.EVENT_READ, None)
        proxy_url = f'http://127.0.0.1:{self._listener.getsockname()[1]}'
        self._environment = {key: proxy_url for key in
                            ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')}
        self._environment.update(NO_PROXY='', no_proxy='')
        self._ready.set()
        while not self._stop.is_set():
            for key, events in self._selector.select(.1):
                if self._stop.is_set():
                    break
                if key.data is None:
                    try:
                        client, _ = self._listener.accept()
                    except BlockingIOError:
                        continue
                    client.setblocking(False)
                    tunnel = _Tunnel(client)
                    self._tunnels.add(tunnel)
                    self._sync(tunnel)
                else:
                    tunnel, side = key.data
                    if tunnel in self._tunnels:
                        self._event(tunnel, side, events)

    def _serve(self):
        try:
            with download_lock(self.run_root, cancel_event=self._stop):
                try:
                    self._serve_locked()
                except BaseException as exc:
                    self._error = exc
                finally:
                    for tunnel in list(self._tunnels):
                        self._close(tunnel)
                    if self._listener is not None:
                        self._listener.close()
                    if self._selector is not None:
                        self._selector.close()
                    if self._meter.exists():
                        record = self._record()
                        error = self._error or self._command_error
                        record.update(complete=error is None, error=str(error) if error else None)
                        write_json(self._receipt, record)
        except BaseException as exc:
            self._error = self._error or exc
        finally:
            self._ready.set()

    def check(self):
        if self._error is not None:
            raise TransferProxyError(f'UV transfer proxy failed: {type(self._error).__name__}: {self._error}') from self._error
        if self._thread is not None and not self._thread.is_alive() and not self._stop.is_set():
            raise TransferProxyError('UV transfer proxy stopped unexpectedly')

    def __enter__(self):
        if self._thread is not None:
            raise TransferProxyError('a proxy context cannot be reused')
        self._thread = threading.Thread(target=self._serve, name='uv-transfer-meter', daemon=True)
        self._thread.start()
        try:
            while not self._ready.wait(.1):
                self.check()
            self.check()
            return self
        except BaseException:
            self._stop.set()
            self._thread.join(6)
            raise

    def __exit__(self, kind, value, traceback):
        if value is not None:
            self._command_error = f'{kind.__name__}: {value}'
        self._stop.set()
        self._thread.join(6)
        if self._thread.is_alive():
            raise TransferProxyError('UV transfer proxy did not stop; receipt remains incomplete')
        if kind is None:
            self.check()
        elif self._error is not None and hasattr(value, 'add_note'):
            value.add_note(f'UV transfer proxy also failed: {self._error}')
        return False


def uv_proxy(run_root, download_limit, artifact_limit=None, *, allowed_ports=(443,)):
    """Context for one UV command; call check after its subprocess completes.

    Passing the environment is mandatory. Non-443 allowed_ports are intended
    only for explicit localhost fixture tests; production defaults admit HTTPS.
    The proxy consumes one worker thread while the command runs.
    """
    return _UVProxy(run_root, download_limit, artifact_limit, allowed_ports=allowed_ports)
