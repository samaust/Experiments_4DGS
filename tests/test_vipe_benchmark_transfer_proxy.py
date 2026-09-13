"""Localhost-only opaque tunnel fixtures; no external network or setup."""
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import urlsplit

from scripts.vipe_benchmark import budgets, transfer_proxy
from scripts.vipe_benchmark.files import write_json


@contextmanager
def local_server(handler):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(3)
    errors = []
    def serve():
        try:
            with listener.accept()[0] as connection:
                connection.settimeout(3)
                handler(connection)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A cap stop may close a fixture peer while it is sending.
        except BaseException as exc:
            errors.append(exc)
        finally:
            listener.close()
    thread = threading.Thread(target=serve, name='localhost-fixture-server', daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        thread.join(4)
        if thread.is_alive():
            listener.close()
            raise AssertionError('fixture server did not stop')
        if errors:
            raise errors[0]


def connect_client(proxy, port, *, request=None):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(3)
    client.connect(('127.0.0.1', urlsplit(proxy.environment['HTTPS_PROXY']).port))
    client.sendall(request or f'CONNECT 127.0.0.1:{port} HTTP/1.1\r\nHost: localhost\r\n\r\n'.encode())
    return client


def read_header(client):
    header = bytearray()
    while not header.endswith(b'\r\n\r\n'):
        block = client.recv(1)
        if not block:
            raise AssertionError('fixture proxy closed before CONNECT response')
        header.extend(block)
    return bytes(header)


def read_all(client):
    result = bytearray()
    while True:
        try:
            block = client.recv(4096)
        except ConnectionResetError:
            break
        if not block:
            break
        result.extend(block)
    return bytes(result)


class TransferProxyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def receipt(self, proxy):
        return json.loads((self.root / 'uv-transfers' / f'transfer-{proxy.transfer_id}.json').read_text())

    def test_opaque_bidirectional_tunnel_and_deduplicated_receipt(self):
        request = b'\x16\x03\x03opaque client TLS bytes\x00\xff'
        response = b'\x17\x03\x03opaque server TLS bytes\x00\xff'
        observed = []
        def serve(connection):
            received = bytearray()
            while len(received) < len(request):
                received.extend(connection.recv(len(request) - len(received)))
            observed.append(bytes(received))
            connection.sendall(response)
            connection.shutdown(socket.SHUT_WR)
        with local_server(serve) as port:
            with transfer_proxy.uv_proxy(self.root, 4096, allowed_ports=(port,)) as proxy:
                with connect_client(proxy, port) as client:
                    self.assertEqual(read_header(client), b'HTTP/1.1 200 Connection Established\r\n\r\n')
                    client.sendall(request)
                    client.shutdown(socket.SHUT_WR)
                    self.assertEqual(read_all(client), response)
                proxy.check()
        self.assertEqual(observed, [request])
        record = self.receipt(proxy)
        self.assertTrue(record['complete'])
        self.assertEqual(record['bytes_received'], len(response))
        self.assertEqual(record['reserved_bytes'], 0)
        self.assertEqual(record['upstream_connections'], 1)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], len(response))

    def test_small_cap_is_checked_before_recv_without_one_byte_probe(self):
        def serve(connection):
            connection.sendall(b'x' * 100)
            connection.shutdown(socket.SHUT_WR)
        with local_server(serve) as port:
            with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'exhausted'):
                with transfer_proxy.uv_proxy(self.root, 17, allowed_ports=(port,)) as proxy:
                    with connect_client(proxy, port) as client:
                        read_header(client)
                        self.assertLessEqual(len(read_all(client)), 17)
                    proxy.check()
        record = self.receipt(proxy)
        self.assertFalse(record['complete'])
        self.assertEqual(record['bytes_received'], 17)
        self.assertEqual(record['reserved_bytes'], 0)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 17)

    def test_prior_failed_bytes_reduce_tunnel_allocation(self):
        write_json(self.root / 'transfers/transfer-prior.json', dict(bytes_received=8, error='failed without a file'))
        def serve(connection):
            connection.sendall(b'x' * 100)
        with local_server(serve) as port:
            with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'exhausted'):
                with transfer_proxy.uv_proxy(self.root, 15, allowed_ports=(port,)) as proxy:
                    with connect_client(proxy, port) as client:
                        read_header(client)
                        read_all(client)
                    proxy.check()
        self.assertEqual(self.receipt(proxy)['bytes_received'], 7)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 15)

    def test_all_proxy_environment_spellings_and_bypass_override(self):
        with transfer_proxy.uv_proxy(self.root, 10) as proxy:
            environment = proxy.environment
            for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
                self.assertEqual(environment[name], environment['HTTPS_PROXY'])
            self.assertEqual(environment['NO_PROXY'], '')
            self.assertEqual(environment['no_proxy'], '')
        self.assertTrue(self.receipt(proxy)['complete'])

    def test_non_connect_http_is_rejected_without_an_upstream_attempt(self):
        with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'CONNECT'):
            with transfer_proxy.uv_proxy(self.root, 100) as proxy:
                with connect_client(proxy, 443, request=b'GET http://example.invalid/ HTTP/1.1\r\n\r\n') as client:
                    self.assertEqual(read_all(client), b'')
                proxy.check()
        self.assertEqual(self.receipt(proxy)['upstream_connections'], 0)
        self.assertEqual(self.receipt(proxy)['bytes_received'], 0)

    def test_default_proxy_refuses_non_https_ports(self):
        with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'port'):
            with transfer_proxy.uv_proxy(self.root, 100) as proxy:
                with connect_client(proxy, 80) as client:
                    read_all(client)
                proxy.check()
        self.assertEqual(self.receipt(proxy)['upstream_connections'], 0)

    def test_failed_command_is_retained_in_immutable_receipt(self):
        with self.assertRaisesRegex(ValueError, 'fixture command failed'):
            with transfer_proxy.uv_proxy(self.root, 100) as proxy:
                raise ValueError('fixture command failed')
        record = self.receipt(proxy)
        self.assertFalse(record['complete'])
        self.assertIn('fixture command failed', record['error'])
        with self.assertRaises(FileExistsError):
            write_json(proxy._receipt, dict(bytes_received=0))

    def test_recv_reservation_is_durable_before_transport_read(self):
        proxy = transfer_proxy.uv_proxy(self.root, 17)
        proxy._meter.parent.mkdir()
        admitted = []
        test = self
        class Upstream:
            def recv(self, count):
                record = json.loads(proxy._meter.read_text())
                test.assertEqual(record['reserved_bytes'], count)
                test.assertEqual(record['bytes_received'], 0)
                test.assertEqual(budgets.budget_snapshot(test.root)['download_bytes'], count)
                admitted.append(count)
                return b'x' * count
        with budgets.download_lock(self.root):
            self.assertEqual(proxy._recv(Upstream(), 2**20), b'x' * 17)
            with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'exhausted'):
                proxy._recv(Upstream(), 1)
        self.assertEqual(admitted, [17])
        self.assertEqual(json.loads(proxy._meter.read_text())['bytes_received'], 17)

    def test_failed_recv_keeps_full_uncertain_reservation_without_a_file(self):
        proxy = transfer_proxy.uv_proxy(self.root, 13)
        proxy._meter.parent.mkdir()
        class Upstream:
            def recv(self, count):
                raise OSError('fixture failure during receive')
        with budgets.download_lock(self.root):
            with self.assertRaisesRegex(OSError, 'fixture failure'):
                proxy._recv(Upstream(), 100)
        record = json.loads(proxy._meter.read_text())
        self.assertEqual(record['bytes_received'], 0)
        self.assertEqual(record['reserved_bytes'], 13)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 13)

    def test_would_block_releases_reservation_without_refunding_received_bytes(self):
        proxy = transfer_proxy.uv_proxy(self.root, 13)
        proxy._meter.parent.mkdir()
        class Upstream:
            def recv(self, count):
                raise BlockingIOError()
        with budgets.download_lock(self.root):
            self.assertIsNone(proxy._recv(Upstream(), 100))
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 0)
        self.assertEqual(json.loads(proxy._meter.read_text())['reserved_bytes'], 0)

    def test_many_reads_share_cached_inventory_and_monotonic_received_counter(self):
        proxy = transfer_proxy.uv_proxy(self.root, 1000)
        proxy._meter.parent.mkdir()
        published = []
        original_publish = proxy._publish
        def publish():
            original_publish()
            published.append(json.loads(proxy._meter.read_text())['bytes_received'])
        class Upstream:
            def recv(self, count):
                return b'x' * min(count, 3)
        with budgets.download_lock(self.root), mock.patch.object(proxy, '_publish', side_effect=publish), \
                mock.patch.object(budgets, '_snapshot', wraps=budgets._snapshot) as scan, \
                mock.patch.object(budgets.time, 'monotonic', return_value=10.):
            for _ in range(20):
                self.assertEqual(proxy._recv(Upstream(), 100), b'xxx')
            self.assertEqual(scan.call_count, 1)
        self.assertEqual(published, sorted(published))
        self.assertEqual(published[-1], 60)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 60)

    def test_two_tunnels_share_one_global_recv_cap(self):
        ready = threading.Barrier(2)
        def serve(connection):
            ready.wait(timeout=3)
            connection.sendall(b'x' * 100)
            connection.shutdown(socket.SHUT_WR)
        with local_server(serve) as first, local_server(serve) as second:
            with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'exhausted'):
                with transfer_proxy.uv_proxy(self.root, 19, allowed_ports=(first, second)) as proxy:
                    with connect_client(proxy, first) as a, connect_client(proxy, second) as b:
                        read_header(a)
                        read_header(b)
                        read_all(a)
                        read_all(b)
                    proxy.check()
        record = self.receipt(proxy)
        self.assertEqual(record['upstream_connections'], 2)
        self.assertEqual(record['bytes_received'], 19)
        self.assertEqual(budgets.budget_snapshot(self.root)['download_bytes'], 19)

    def test_empty_remaining_budget_never_attempts_dns_or_upstream(self):
        with mock.patch.object(transfer_proxy.socket, 'getaddrinfo', side_effect=AssertionError('unexpected DNS')):
            with self.assertRaisesRegex(transfer_proxy.TransferProxyError, 'exhausted'):
                with transfer_proxy.uv_proxy(self.root, 0) as proxy:
                    with connect_client(proxy, 443) as client:
                        read_all(client)
                    proxy.check()
        self.assertEqual(self.receipt(proxy)['upstream_connections'], 0)


if __name__ == '__main__':
    unittest.main()
