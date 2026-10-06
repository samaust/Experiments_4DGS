"""Aggregate a complete QUALIFY arm into the production native qualification record."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.final_render_contract import PHASES

PRODUCTION = 'plan069-final-render-D8-001'
QUALIFY = 'plan069-final-render-D8-qualification-001'


class FakeLedger:
    def __init__(self, events):
        self._events = events

    def events(self):
        return self._events

    def states(self, events):
        states = {}
        for event in events:
            if 'job_id' in event and event['event'] in ('reserve', 'finish'):
                states[event['job_id']] = event
        return states


class NativeQualificationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        bindings = dict(runtime=self.record('runtime', dict(schema='runtime')),
                        proposal=self.record('proposal', dict(id=PRODUCTION)))
        allocations = [dict(id=f'{PRODUCTION}/{arm}/{phase}', arm=arm, phase=phase, resource=resource, seconds=seconds)
                       for arm in ('QF-B', 'QF-M1') for phase, (resource, seconds) in PHASES.items()]
        allocations.append(dict(id=f'{PRODUCTION}/package', arm='all', phase='package', resource='cpu', seconds=900))
        self.production = dict(schema='plan069-final-render-request/v1', record_kind='actual', mode='REVIEW',
            id=PRODUCTION, iterations=5000, allocations=allocations, bindings=bindings,
            compositions={'QF-B': {}, 'QF-M1': {}})
        self.production_record = self.record('production-request', self.production)
        qualify = copy.deepcopy(self.production)
        qualify['id'] = QUALIFY
        for allocation in qualify['allocations']:
            allocation['id'] = allocation['id'].replace(PRODUCTION, QUALIFY, 1)
        qualify['bindings']['proposal'] = self.record('qualify-proposal', dict(id=QUALIFY))
        self.qualify = qualify
        self.qualify_record = self.record('qualify-request', qualify)
        self.sources = [self.record('source', dict(schema='source'))]
        self.commands = {f'QF-B/{phase}': ['/env/bin/python', 'worker', phase] for phase in PHASES}
        self.envelope = self.record('envelope', dict(schema='plan069-final-render-do/v1', record_kind='actual',
            mode='QUALIFY', request=self.qualify_record, qualification=None, commands=self.commands,
            source_files=self.sources, interpreter=self.record('interpreter', dict(schema='interpreter')),
            matcher_runtime=self.record('matcher', dict(schema='matcher'))))
        self.events = []
        for phase in PHASES:
            self.complete(phase)

    def record(self, name, payload):
        path = self.root/f'{name}-{len(list(self.root.iterdir()))}.json'
        write_json(path, payload)
        return file_record(path)

    def complete(self, phase, **finish):
        job = f'{QUALIFY}/QF-B/{phase}'
        output = self.root/phase
        output.mkdir()
        result = dict(status='complete', phase=phase, allocation_id=job, elapsed_seconds=100.,
                      artifact_bytes=2**20*(3 if phase == 'initializer' else 1))
        if phase == 'train':
            (output/'checkpoint-005000.pt').write_bytes(b'x'*4096)
            checkpoint = file_record(output/'checkpoint-005000.pt')
            write_json(output/'checkpoint-timing.json', dict(schema='plan069-final-render-checkpoint-timing/v1',
                checkpoint=checkpoint, save_seconds=2.5))
            result.update(checkpoint=checkpoint,
                          artifacts=[checkpoint, file_record(output/'checkpoint-timing.json')])
        write_json(output/'result.json', result)
        supervision = self.record(f'{phase}-supervision', dict(status='complete', peak_device_bytes=2**30,
                                                                peak_cpu_workers=4))
        command = self.commands[f'QF-B/{phase}']
        self.events.append(dict(event='reserve', job_id=job, command=command,
            evidence=dict(schema='plan069-final-render-reservation-binding/v1', role='native-qualification',
                          record_kind='actual', envelope=self.envelope, request=self.qualify_record,
                          arm='QF-B', phase=phase)))
        event = dict(event='finish', job_id=job, status='complete', elapsed_seconds=112.,
            cleanup_confirmed=True, cleanup_uncertain=False, deadline_exceeded=False,
            result=file_record(output/'result.json'), supervision=supervision)
        event.update(finish)
        self.events.append(event)

    def build(self, events=None):
        from vipe_benchmark.final_render_native_qualification import build
        return build(self.production_record, self.envelope, FakeLedger(self.events if events is None else events),
                     self.root/'qualification')

    def test_complete_clean_arm_publishes_passed_receipts_and_measured_reserves(self):
        record = self.build()
        qualification = read_json(record['path'])
        self.assertEqual(qualification['schema'], 'plan069-final-render-native-qualification/v1')
        self.assertEqual(qualification['status'], 'passed')
        self.assertEqual(qualification['request'], self.production_record)
        self.assertEqual(qualification['runtime'], self.production['bindings']['runtime'])
        self.assertEqual(set(qualification['runs']), set(PHASES))
        self.assertEqual(qualification['initializer_bytes'], 3*2**20)
        self.assertEqual(qualification['checkpoint_bytes'], 4096)
        self.assertEqual(qualification['checkpoint_seconds'], 2.5)
        self.assertAlmostEqual(qualification['cleanup_seconds'], 12.)
        for phase, run_record in qualification['runs'].items():
            run = read_json(run_record['path'])
            self.assertEqual((run['schema'], run['status'], run['phase']),
                             ('plan069-final-render-qualify-phase-receipt/v1', 'passed', phase))
            self.assertEqual(run['job_id'], f'{QUALIFY}/QF-B/{phase}')
            self.assertEqual(run['request'], self.production_record)
            self.assertEqual(run['qualification_request'], self.qualify_record)
            self.assertEqual(run['command'], self.commands[f'QF-B/{phase}'])
            self.assertEqual((run['peak_device_bytes'], run['cpu_workers_used']), (2**30, 4))

    def test_failed_or_uncleaned_phase_cannot_qualify(self):
        for change in (dict(status='failed'), dict(cleanup_confirmed=False), dict(deadline_exceeded=True)):
            events = copy.deepcopy(self.events)
            events[-1].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'cleaned successful'):
                self.build(events)

    def test_missing_phase_cannot_qualify(self):
        with self.assertRaisesRegex(ValueError, 'cleaned successful'):
            self.build(self.events[:-2])

    def test_qualification_must_use_distinct_identity_with_identical_settings(self):
        changed = copy.deepcopy(self.qualify)
        changed['iterations'] = 10
        envelope = read_json(self.envelope['path'])
        envelope['request'] = self.record('changed-request', changed)
        self.envelope = self.record('changed-envelope', envelope)
        with self.assertRaisesRegex(ValueError, 'settings'):
            self.build()
        envelope['request'] = self.production_record
        self.envelope = self.record('production-envelope', envelope)
        with self.assertRaisesRegex(ValueError, 'distinct'):
            self.build()

    def test_verify_accepts_only_the_ledger_derived_record(self):
        from vipe_benchmark.final_render_native_qualification import verify
        record = self.build()
        ledger = FakeLedger(self.events)
        self.assertEqual(verify(record, self.production_record, self.events, ledger.states(self.events))['status'],
                         'passed')
        tampered = read_json(record['path'])
        tampered['checkpoint_seconds'] = 0.001
        with self.assertRaisesRegex(ValueError, 'ledger evidence'):
            verify(self.record('tampered', tampered), self.production_record, self.events, ledger.states(self.events))

    def test_compatibility_or_foreign_reservation_cannot_qualify(self):
        for change in (dict(schema='plan069-final-render-qualification-reservation-binding/v1'),
                       dict(role='production'), dict(arm='QF-M1')):
            events = copy.deepcopy(self.events)
            events[0]['evidence'].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'QUALIFY envelope reservation'):
                self.build(events)

    def test_unmeasured_cpu_usage_cannot_qualify(self):
        events = copy.deepcopy(self.events)
        events[1]['supervision'] = self.record('zero-cpu', dict(status='complete', peak_device_bytes=0,
                                                                 peak_cpu_workers=0))
        with self.assertRaisesRegex(ValueError, 'CPU worker'):
            self.build(events)

    def test_partial_or_multi_arm_commands_cannot_qualify(self):
        envelope = read_json(self.envelope['path'])
        for commands in ({k: v for k, v in self.commands.items() if not k.endswith('/render')},
                         dict(self.commands, **{'QF-M1/geometry': ['/env/bin/python', 'worker', 'geometry']})):
            envelope['commands'] = commands
            self.envelope = self.record('commands-envelope', envelope)
            with self.subTest(commands=sorted(commands)), self.assertRaisesRegex(ValueError, 'qualification'):
                self.build()

    def test_production_envelope_is_not_a_qualification(self):
        envelope = read_json(self.envelope['path'])
        envelope['mode'] = 'DO'
        self.envelope = self.record('do-envelope', envelope)
        with self.assertRaisesRegex(ValueError, 'QUALIFY'):
            self.build()


class QualifyAdmissionTests(unittest.TestCase):
    request = dict(compositions={'QF-B': {}, 'QF-M1': {}},
                   allocations=[dict(id=f'R/{arm}/{phase}', arm=arm, phase=phase)
                                for arm in ('QF-B', 'QF-M1') for phase in PHASES] +
                               [dict(id='R/package', arm='all', phase='package')],
                   cpu_workers_limit=8, device_bytes_limit=21*2**30, artifact_bytes_limit=12*2**30)

    def test_command_keys_cover_every_arm_for_do_and_one_arm_for_qualify(self):
        from vipe_benchmark.final_render_admission import command_keys
        every = {f'{arm}/{phase}' for arm in ('QF-B', 'QF-M1') for phase in PHASES}
        self.assertEqual(command_keys(dict(mode='DO', commands={}), self.request), every)
        one = {f'QF-B/{phase}' for phase in PHASES}
        self.assertEqual(command_keys(dict(mode='QUALIFY', commands=dict.fromkeys(one)), self.request), one)
        for commands in (dict.fromkeys(every), dict.fromkeys({'QF-X/geometry'})):
            with self.assertRaisesRegex(ValueError, 'one qualification arm'):
                command_keys(dict(mode='QUALIFY', commands=commands), self.request)

    def test_measured_reserves_must_fit_the_150_second_train_reserve(self):
        import time
        from vipe_benchmark.final_render_admission import _live
        live = dict(artifact_bytes=0, download_bytes=0, free_disk_bytes=2**40, device_bytes=2**28, gpu_pids=[],
                    cpu_workers_used=0, cleanup_confirmed=True, observed_unix=time.time())
        config = dict(cpu_max_workers=8, gpu_peak_device_gib_limit=22)
        reserves = dict(initializer_bytes=2**28, checkpoint_bytes=2**31, checkpoint_seconds=20., cleanup_seconds=40.)
        self.assertEqual(_live(live, self.request, config, reserves)['free_disk_bytes'], 2**40)
        with self.assertRaisesRegex(ValueError, '150 s reserve'):
            _live(live, self.request, config, dict(reserves, cleanup_seconds=140.))


if __name__ == '__main__':
    unittest.main()
