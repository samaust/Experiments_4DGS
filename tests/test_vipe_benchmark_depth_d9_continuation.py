"""CPU request and protected transaction boundaries for grant851 continuation."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vipe_benchmark.config import load
from vipe_benchmark.files import write_json, file_record, read_json, object_hash, digest
from vipe_benchmark.ledger import Ledger


class D9ContinuationTests(unittest.TestCase):
    def test_private_ledger_continues_once_and_rechecks_current_evidence_at_worker_and_finish(self):
        """Replay real immutable ancestry into a private filesystem ledger adapter.

        New receipts below are simulated test data, not runtime qualification.
        Host GPU sampling is replaced at its system boundary; no model executes.
        """
        from vipe_benchmark.depth_admission import local_source_records
        from vipe_benchmark.depth_d9_continuation import JOB, GRANT_SHA256, SCHEMA
        from vipe_benchmark.video_depth import admitted_video_request, video_slot_guard
        from vipe_benchmark.config import ROOT
        from vipe_benchmark import files
        grant = read_json(Path(__file__).parent / 'fixtures/plan069-d9-continuation/grant851.json')
        run_root = Path(grant['request']['path']).parent.parent
        ledger_path = run_root / 'ledger.jsonl'
        if not ledger_path.is_file():
            self.skipTest('the run-specific immutable grant851 ancestry is unavailable')
        config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private_ledger = root / 'ledger.jsonl'
            private_ledger.write_bytes(ledger_path.read_bytes())
            original_open = Path.open
            original_stat = Path.stat
            original_absolute = Path.absolute
            original_safe_path = files.safe_path
            canonical_tree = Path(grant['worker']['path']).parents[1]
            artifacts = {}
            def source_path(path):
                if path in artifacts:
                    return artifacts[path]
                try:
                    relative = path.relative_to(canonical_tree)
                except ValueError:
                    return path
                return ROOT / relative if relative.parts and relative.parts[0] in (
                    'scripts', 'configs', 'docs', 'AGENTS.md', 'README.md') else path
            def isolated_open(path, *args, **kwargs):
                return original_open(private_ledger if path == ledger_path else source_path(path), *args, **kwargs)
            def isolated_stat(path, *args, **kwargs):
                return original_stat(source_path(path), *args, **kwargs)
            def isolated_absolute(path):
                return original_absolute(source_path(path))
            def canonical_source_path(path):
                path = original_safe_path(path)
                try:
                    relative = path.relative_to(ROOT)
                except ValueError:
                    return path
                return canonical_tree / relative
            for adapter in (patch.object(Path, 'open', isolated_open),
                            patch.object(Path, 'stat', isolated_stat),
                            patch.object(Path, 'absolute', isolated_absolute),
                            patch.object(files, 'safe_path', canonical_source_path)):
                adapter.start()
                self.addCleanup(adapter.stop)
            def document(name, value):
                path = root / name
                write_json(path, value)
                return file_record(path)
            current = local_source_records('D9')
            source = read_json(grant['source_review']['path'])
            source.update(local_sources=current, reviewer='CPU fixture simulated independent reviewer')
            source_record = document('source.json', source)
            admitted = read_json(grant['admission']['path'])
            assessment = read_json(admitted['commercial']['assessment']['path'])
            dependencies = read_json(assessment['dependency_manifest']['path'])
            small_dependency = root / 'cpu-fixture-dependency.bin'
            small_dependency.write_bytes(b'independent CPU fixture dependency')
            dependencies.update(record_kind='fixture', files=[file_record(small_dependency)])
            dependency_record = document('dependencies.json', dependencies)
            assessment.update(record_kind='fixture', dependency_manifest=dependency_record)
            assessment_record = document('commercial.json', assessment)
            commercial_binding = dict(admitted['commercial'], assessment=assessment_record)
            runtime = read_json(admitted['runtime']['receipt']['path'])
            runtime.update(local_sources=current, source_review=source_record,
                           dependency_manifest=dependency_record)
            runtime_record = document('runtime.json', runtime)
            bundle = read_json(admitted['qualification']['path'])
            runtime_binding = dict(admitted['runtime'], receipt=runtime_record)
            bundle.update(source_review=source_record, local_sources=current, runtime=runtime_binding,
                          commercial=commercial_binding)
            bundle_record = document('qualification.json', bundle)
            log = root / 'capture.log'; log.write_text('Simulated CPU test evidence\n')
            cpu = dict(schema='plan069-integrated-cpu-test-capture/v1', record_kind='actual',
                fixture_scope='Simulated filesystem-boundary receipts; no actual qualification',
                passed=True, within_wall_limit=True, source_bytes_unchanged=True,
                environment_bytes_unchanged=True, head_unchanged=True, head='fixture',
                head_after='fixture', sources_before=current, sources_after=current,
                commands=[dict(command=['fixture-python', '-m', 'unittest'], returncode=0,
                    timed_out=False, log=str(log), log_sha256=digest(log), cleanup=dict(
                        confirmed_no_surviving_observed_processes=True,
                        surviving_observed_owned_processes=[])),
                    dict(command=['fixture-python', '-m', 'mypy'], returncode=0,
                    timed_out=False, log=str(log), log_sha256=digest(log), cleanup=dict(
                        confirmed_no_surviving_observed_processes=True,
                        surviving_observed_owned_processes=[]))])
            cpu_record = document('cpu.json', cpu)
            ledger = Ledger(ledger_path, config)
            with patch.object(Path, 'open', isolated_open), patch('time.time', return_value=1000.):
                events = ledger.events()
                live = dict(admitted['live'], sampled_unix=1000., ledger_head_sha256=events[-1]['event_sha256'])
                admitted.update(source_review=source_record, runtime=runtime_binding,
                    qualification=bundle_record, live=live, commercial=commercial_binding)
                admission_record = document('admission.json', admitted)
                sidecar = dict(schema=SCHEMA, candidate='D9', job_id=JOB,
                    original_grant_sha256=GRANT_SHA256, original_request=grant['request'],
                    command=grant['command'], config_sha256=object_hash(config),
                    ledger_head_sha256=events[-1]['event_sha256'], new_allocations=0,
                    reset_previous_consumption=False, source_review=source_record,
                    admission=admission_record, cpu_validation=cpu_record, mypy_validation=cpu_record)
                sidecar_record = document('continuation.json', sidecar)
                changed_cpu = copy.deepcopy(cpu)
                changed_cpu['sources_after'] = []
                changed_cpu_record = document('changed-cpu.json', changed_cpu)
                changed_sidecar_record = document('changed-continuation.json', dict(sidecar,
                    cpu_validation=changed_cpu_record))
                reading = dict(grant['resource_snapshot'], device_bytes=0)
                with patch('vipe_benchmark.execution.resources', return_value=reading), \
                     patch('sys.executable', grant['command'][0]):
                    before = ledger.events()
                    with self.assertRaisesRegex(ValueError, 'unchanged current D9 sources'):
                        ledger.continue_depth_d9_attempt(changed_sidecar_record)
                    self.assertEqual(ledger.events(), before)
                    event = ledger.continue_depth_d9_attempt(sidecar_record)
                    self.assertEqual(event['event'], 'depth_d9_attempt_continued')
                    self.assertEqual(sum(row['event'] == 'depth_attempt_authorized' and
                        row.get('candidate') == 'D9' for row in ledger.events()), 1)
                    self.assertEqual(ledger.events()[:len(before)], before)
                    with self.assertRaisesRegex(ValueError, 'unstarted'):
                        ledger.continue_depth_d9_attempt(sidecar_record)
                    evidence = dict(**{key: grant[key] for key in ('review', 'authorization',
                        'source_review', 'admission', 'request', 'worker', 'executable')},
                        continuation=sidecar_record)
                    reserved = ledger.reserve(JOB, grant['command'], evidence)
                    request = read_json(grant['request']['path'])
                    with patch.dict('os.environ', VIPE_RESERVATION_START=str(reserved['monotonic_start'])):
                        admitted_video_request(request, grant['command'][-1], config,
                            ledger=ledger, request_path=grant['request']['path'])
                    fresh_source_path = Path(source_record['path'])
                    saved_source = fresh_source_path.read_text()
                    fresh_source_path.write_text(saved_source + '\n')
                    with self.assertRaisesRegex(ValueError, 'changed file'):
                        video_slot_guard(request, ledger)
                    fresh_source_path.write_text(saved_source)
                    reserved_snapshot = private_ledger.read_bytes()
                    fake_result_path = root / 'worker-result.json'
                    write_json(fake_result_path, dict(schema='plan069-video-depth-result/v1',
                        record_kind='actual', fixture_scope='Simulated public publication input',
                        status='complete', component='D9', id=JOB, context=request['context'],
                        rows=[{}] * 256, anchor_rows=[{}] * 60, sequences=[{}] * 60))
                    artifacts[run_root / 'jobs' / JOB / 'result.json'] = fake_result_path
                    result_record = file_record(run_root / 'jobs' / JOB / 'result.json')
                    clean = dict(cleanup_confirmed=True, cleanup_uncertain=False,
                                 surviving_pids=[], result=result_record)
                    finished = ledger.finish(JOB, 'complete', 1., **clean)
                    self.assertEqual(finished['event'], 'finish')
                    self.assertGreater(finished['elapsed_seconds'], 1.)
                    with self.assertRaisesRegex(ValueError, 'already consumed'):
                        ledger.reserve(JOB, grant['command'], evidence)
                    import basketball_vipe_video_publish as publisher
                    log.write_text('Changed CPU command result\n')
                    with self.assertRaisesRegex(ValueError, 'command log'):
                        publisher.publish('D9')
                    self.assertFalse((run_root / 'jobs/plan069-D9-clips-001').exists())
                    completed_ledger = private_ledger
                    private_ledger = root / 'failed-validation-ledger.jsonl'
                    private_ledger.write_bytes(reserved_snapshot)
                    failed = ledger.finish(JOB, 'complete', 1., **clean)
                    self.assertEqual(failed['status'], 'failed')
                    self.assertIn('command log', failed['continuation_validation_error'])
                    with self.assertRaisesRegex(ValueError, 'already consumed'):
                        ledger.reserve(JOB, grant['command'], evidence)
                    log.write_text('Simulated CPU test evidence\n')
                    private_ledger = root / 'overrun-ledger.jsonl'
                    private_ledger.write_bytes(reserved_snapshot)
                    with patch('time.monotonic', return_value=reserved['monotonic_start'] + 12001.):
                        overrun = ledger.finish(JOB, 'complete', 1., **clean)
                    self.assertEqual(overrun['status'], 'failed')
                    self.assertTrue(overrun['deadline_exceeded'])
                    self.assertEqual(overrun['elapsed_seconds'], 12001.)
                    private_ledger = completed_ledger
                    self.assertEqual(ledger.states()[JOB]['status'], 'complete')

    def test_request_rejects_started_finished_accounted_or_changed_original_allocation(self):
        from vipe_benchmark.depth_d9_continuation import validate_request, JOB
        grant = read_json(Path(__file__).parent / 'fixtures/plan069-d9-continuation/grant851.json')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / 'continuation.json'
            write_json(request, dict(schema='plan069-D9-unstarted-continuation/v1'))
            for event in ('reserve', 'start', 'finish', 'account'):
                with self.subTest(event=event), self.assertRaisesRegex(ValueError, 'unstarted'):
                    validate_request(file_record(request), [grant, dict(event=event, job_id=JOB)],
                                     load(), root)
            changed = copy.deepcopy(grant)
            changed['seconds'] += 1
            with self.assertRaisesRegex(ValueError, 'content changed'):
                validate_request(file_record(request), [changed], load(), root)

    def test_continuation_cannot_mint_an_allocation_without_original_grant(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = Ledger(root / 'ledger.jsonl', load())
            request = root / 'continuation.json'
            write_json(request, dict(schema='plan069-D9-unstarted-continuation/v1'))
            before = ledger.events()
            with self.assertRaisesRegex(ValueError, 'original grant851'):
                ledger.continue_depth_d9_attempt(file_record(request))
            self.assertEqual(ledger.events(), before)

    def test_unchecked_note_cannot_create_continuation_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Ledger(Path(temporary) / 'ledger.jsonl', load())
            with self.assertRaisesRegex(ValueError, 'checked ledger transition'):
                ledger.note('depth_d9_attempt_continued', candidate='D9')
            self.assertEqual(ledger.events(), [])
