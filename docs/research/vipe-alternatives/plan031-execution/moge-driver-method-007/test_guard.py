"""Fake-only policy/startup fixtures: never install filters or create sockets."""
import importlib.util
from pathlib import Path
import stat
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('guard007', Path(__file__).with_name('network_guard.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class FakeEntries:
    def __enter__(self):
        return iter([types.SimpleNamespace(name='0'), types.SimpleNamespace(name='9')])

    def __exit__(self, *unused):
        return False


def fake_stat(mode, inode=1):
    return types.SimpleNamespace(st_dev=1, st_ino=inode, st_mode=mode, st_rdev=0)


class GuardTests(unittest.TestCase):
    def test_exact_creation_and_all_transfer_import_denials(self):
        rules = guard.policy_rules()
        self.assertEqual(rules[:3], (('socket', 0, 'not_equal', 1),
                         ('socket', 1, 'not_equal', 524293), ('socket', 2, 'not_equal', 0)))
        names = {rule[0] for rule in rules[3:]}
        self.assertEqual(names, {'socketpair', 'connect', 'accept', 'accept4',
            'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
            'pidfd_getfd', 'io_uring_setup', 'io_uring_enter', 'io_uring_register'})
        self.assertNotIn('bind', names)
        self.assertNotIn('listen', names)

    def test_policy_behavior_for_unix_and_inet_creation(self):
        # Evaluate the declared BPF comparisons with no syscall/filter execution.
        def denied(name, args=()):
            return any(syscall == name and (operation == 'always' or
                args[argument] != value) for syscall, argument, operation, value
                in guard.policy_rules())
        self.assertFalse(denied('socket', (1, 524293, 0)))
        for domain in (2, 10, 16):
            self.assertTrue(denied('socket', (domain, 524293, 0)))
        self.assertTrue(denied('socket', (1, 5, 0)))
        self.assertTrue(denied('socket', (1, 524293, 1)))
        self.assertFalse(denied('listen', (16, 128)))
        for name in ('connect', 'accept', 'accept4', 'recvmsg', 'pidfd_getfd'):
            self.assertTrue(denied(name))

    def test_startup_order(self):
        events = []
        def snapshot():
            events.append('snapshot')
            return {0: (1, 1, stat.S_IFIFO, 0)}
        result = guard.establish_and_install(snapshot, lambda rules: events.append('install'))
        self.assertEqual(events, ['snapshot', 'snapshot', 'install', 'snapshot'])
        self.assertEqual(result['socket_descriptors'], 0)
        self.assertIs(result['unix_listen_allowed'], True)

    def test_before_install_inventory_race_rejected(self):
        install = []
        snapshots = iter([{}, {8: (1, 1, stat.S_IFREG, 0)}])
        with self.assertRaisesRegex(ValueError, 'before filter'):
            guard.establish_and_install(lambda: next(snapshots), install.append)
        self.assertEqual(install, [])

    def test_after_install_inventory_race_rejected(self):
        snapshots = iter([{}, {}, {8: (1, 1, stat.S_IFREG, 0)}])
        with self.assertRaisesRegex(ValueError, 'during filter'):
            guard.establish_and_install(lambda: next(snapshots), lambda rules: None)

    def inspect(self, stats=None, tasks=None, modules=None):
        stats = stats or [fake_stat(stat.S_IFIFO), fake_stat(stat.S_IFDIR, 9),
                          fake_stat(stat.S_IFIFO)]
        with patch.object(guard.os, 'getpid', return_value=123), \
             patch.object(guard.os, 'listdir', side_effect=tasks or [['123'], ['123']]), \
             patch.object(guard.os, 'stat', return_value=fake_stat(stat.S_IFDIR, 9)), \
             patch.object(guard.os, 'scandir', return_value=FakeEntries()), \
             patch.object(guard.os, 'fstat', side_effect=stats), \
             patch.object(guard.sys, 'modules', modules or {}):
            return guard.own_process_snapshot()

    def test_inspection_directory_omitted_but_pipe_preserved(self):
        self.assertEqual(self.inspect(), {0: (1, 1, stat.S_IFIFO, 0)})

    def test_inherited_socket_fails_without_closing(self):
        with patch.object(guard.os, 'close') as close:
            with self.assertRaisesRegex(ValueError, 'inherited socket'):
                self.inspect(stats=[fake_stat(stat.S_IFSOCK)])
            close.assert_not_called()

    def test_disappearing_descriptor_fails_closed(self):
        with self.assertRaises(OSError):
            self.inspect(stats=[OSError('descriptor disappeared')])

    def test_replaced_descriptor_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'replaced'):
            self.inspect(stats=[fake_stat(stat.S_IFIFO), fake_stat(stat.S_IFDIR, 9),
                                fake_stat(stat.S_IFREG, 2)])

    def test_multiple_threads_rejected_before_enumeration(self):
        with self.assertRaisesRegex(ValueError, 'one main thread'):
            self.inspect(tasks=[['123', '124']])

    def test_thread_set_change_rejected(self):
        with self.assertRaisesRegex(ValueError, 'thread set changed'):
            self.inspect(tasks=[['123'], ['123', '124']])

    def test_numeric_import_rejected_before_enumeration(self):
        for name in ('numpy', 'numpy.linalg', 'scipy', 'torch', 'triton', 'cv2'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'numeric imports'):
                self.inspect(modules={name: object()})

    def test_snapshot_failure_prevents_install(self):
        install = []
        def broken():
            raise OSError('own proc inaccessible')
        with self.assertRaises(OSError):
            guard.establish_and_install(broken, install.append)
        self.assertEqual(install, [])


if __name__ == '__main__':
    unittest.main()
