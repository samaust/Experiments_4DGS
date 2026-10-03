"""Exercise the worker's real admission gate with accepted temporary setup history."""
import copy
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

import test_vipe_benchmark_depth_admission as fixtures
import test_vipe_benchmark_depth_map_allowance as allowance_fixtures
from vipe_benchmark import depth_admission
from vipe_benchmark.depth_single_run import _actual_gate
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.config import ROOT
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.moge_setup import source_tree_records


class ActualStageGateTests(unittest.TestCase):
    tearDown = fixtures.DepthAdmissionTests.tearDown
    prepare_completed_setup = allowance_fixtures.MapAllowanceTests.prepare_completed_setup

    def replace_json(self, path, document):
        path = Path(path)
        path.unlink()
        write_json(path, document)

    def setUp(self):
        fixtures.DepthAdmissionTests.setUp(self)
        self.config.update(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        self.expected['path'] = self.assets[0]['path'] = 'model.pt'
        self.replace_json(self.inventory, dict(candidates={'D5': dict(files=[self.expected])}))
        self.proposal['required_assets'] = file_record(self.inventory)
        self.proposal['allocation']['artifact_bytes'] = 2**20
        self.approval['proposal_sha256'] = object_hash(self.proposal)
        self.prepare_completed_setup()
        approved = read_json(self.authorization['path'])
        approved.update(cap_amendment=file_record(depth_admission.CAP_AMENDMENT),
            cap_approval=dict(schema='plan069-depth-cap-approval/v1', status='approved',
                amendment_sha256=object_hash(read_json(depth_admission.CAP_AMENDMENT))))
        self.replace_json(self.authorization['path'], approved)
        self.authorization = file_record(self.authorization['path'])
        setup_request_path = self.root / 'requests/plan069-D5-setup-001.json'
        setup_request = read_json(setup_request_path)
        setup_request['authorization'] = self.authorization
        self.replace_json(setup_request_path, setup_request)
        source = self.setup_root / 'source'
        source.mkdir()
        (source / 'model.py').write_text('# inert source fixture\n')
        archive = self.setup_root / 'source.tar.gz'
        archive.write_bytes(b'inert archive receipt')
        setup = read_json(self.setup)
        setup.update(authorization=self.authorization, source_archive=file_record(archive),
            source_dir=str(source), source_tree=source_tree_records(source),
            checkpoint=self.assets[0]['record'])
        self.replace_json(self.setup, setup)
        runtime_path = Path(self.runtime['receipt']['path'])
        runtime = read_json(runtime_path)
        runtime.update(setup=file_record(self.setup), python_executable=str(Path(sys.executable).absolute()))
        self.replace_json(runtime_path, runtime)
        self.runtime['receipt'] = file_record(runtime_path)
        qualified_path = self.root / 'map-qualification.json'
        write_json(qualified_path, dict(commercial=self.commercial, assets=self.assets, runtime=self.runtime))
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        initial = dict(gpu_pids=[], device_bytes=0,
            download_bytes=self.config['new_download_gib_limit'] * 2**30 - 30,
            artifact_bytes=self.config['new_artifact_disk_gib_limit'] * 2**30 - 2**20 - 10)
        setup_evidence = dict(request=file_record(setup_request_path), review=self.review,
            authorization=self.authorization)
        with patch('vipe_benchmark.execution.resources', return_value=initial):
            self.ledger.authorize_depth_setup('D5', self.review, self.authorization, self.source_review)
            self.ledger.reserve('plan069-D5-setup-001', ['inert-setup-command'], setup_evidence)
            self.ledger.finish('plan069-D5-setup-001', 'complete', 1., result=file_record(self.setup),
                cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[])
        events = self.ledger.events()
        self.live.update(sampled_unix=time.time(), ledger_head_sha256=events[-1]['event_sha256'])
        for key, cap in [('download_bytes', 'new_download_gib_limit'),
                         ('artifact_bytes', 'new_artifact_disk_gib_limit')]:
            self.live['used'][key] = self.config[cap] * 2**30 - self.proposal['allocation'][key] + 1
        self.admission_path = self.root / 'map-admission.json'
        write_json(self.admission_path, dict(schema='plan069-depth-admission-result/v1', status='passed',
            candidate='D5', proposal_sha256=object_hash(self.proposal), review=self.review,
            authorization=self.authorization, source_review=self.source_review,
            qualification=file_record(qualified_path), commercial=self.commercial, assets=self.assets,
            runtime=self.runtime, live=self.live, completed_setup=file_record(self.setup)))
        self.request_path = self.root / 'requests/plan069-D5-maps-001.json'
        self.request = dict(candidate='D5', job_id='plan069-D5-maps-001', record_kind='actual',
            ledger_path=str(self.ledger.path), review=self.review, authorization=self.authorization,
            source_review=self.source_review, admission=file_record(self.admission_path),
            qualification=file_record(qualified_path), setup=file_record(self.setup))
        write_json(self.request_path, self.request)
        self.output = self.root / 'jobs/plan069-D5-maps-001'
        worker = file_record(ROOT / 'scripts/basketball_vipe_depth_single_maps.py')
        command = [sys.executable, worker['path'], '--request', str(self.request_path), '--output', str(self.output)]
        evidence = {key: self.request[key] for key in ('review', 'authorization', 'source_review', 'admission')}
        evidence.update(request=file_record(self.request_path), worker=worker, executable=file_record(sys.executable))
        reading = dict(initial, download_bytes=self.live['used']['download_bytes'],
            artifact_bytes=self.live['used']['artifact_bytes'])
        self.reading = reading
        with patch('vipe_benchmark.execution.resources', return_value=reading):
            self.ledger.authorize_depth_attempt('D5', self.review, self.authorization, self.source_review,
                self.request['admission'], command=command, request=evidence['request'],
                worker=worker, executable=evidence['executable'])
            self.reservation = self.ledger.reserve(self.request['job_id'], command, evidence)

    def gate(self):
        with patch.dict(os.environ, VIPE_RESERVATION_START=str(self.reservation['monotonic_start'])), \
             patch('vipe_benchmark.budgets.budget_snapshot', return_value=self.reading):
            return _actual_gate(self.request, self.request_path, self.output)

    def test_worker_rechecks_remaining_stage_instead_of_original_allocation(self):
        blockers = depth_admission.review(self.proposal, config=self.config, commercial=self.commercial,
            assets=self.assets, runtime=self.runtime, live=self.live, source_review=self.source_review,
            approval=self.approval, cap_amendment=file_record(depth_admission.CAP_AMENDMENT),
            cap_approval=read_json(self.authorization['path'])['cap_approval'],
            ledger_head_sha256=self.live['ledger_head_sha256'])
        self.assertTrue(any('download_bytes allocation' in reason for reason in blockers))
        before = self.ledger.events()
        deadline, setup = self.gate()
        self.assertGreater(deadline, time.monotonic())
        self.assertEqual(setup, read_json(self.setup))
        self.assertEqual(self.ledger.events(), before)

    def test_missing_or_changed_setup_proof_cannot_pass_worker_gate(self):
        before = self.ledger.events()
        original_admission = read_json(self.admission_path)
        for changed in (None, self.assets[0]['record']):
            with self.subTest(proof=changed):
                altered = copy.deepcopy(original_admission)
                if changed is None:
                    altered.pop('completed_setup')
                else:
                    altered['completed_setup'] = changed
                self.replace_json(self.admission_path, altered)
                self.request['admission'] = file_record(self.admission_path)
                # Reconcile only the local fixture reservation binding, leaving
                # the accepted setup transitions unchanged. No production ledger is used.
                self.replace_json(self.request_path, self.request)
                state = copy.deepcopy(self.reservation)
                state['evidence']['request'] = file_record(self.request_path)
                state['evidence']['admission'] = self.request['admission']
                with patch.object(Ledger, 'states', return_value={self.request['job_id']: state}):
                    with self.assertRaisesRegex(ValueError, 'allocation|credited admission'):
                        self.gate()
        self.assertEqual(self.ledger.events(), before)


    def test_output_headroom_rejects_saved_row_before_opening_file(self):
        import numpy as np
        from vipe_benchmark.depth_single_run import _actual_output_guard, _npz_write_bound
        guard = _actual_output_guard(self.request,self.output)
        with self.assertRaisesRegex(ValueError,'headroom'):
            guard(_npz_write_bound(np.zeros((540,960,3),np.float32)))
        self.assertFalse(self.output.exists())

    def test_npz_bound_covers_incompressible_native_arrays(self):
        import io
        import numpy as np
        from vipe_benchmark.depth_single_run import _npz_write_bound
        generator = np.random.default_rng(42)
        values = generator.integers(0,256,size=(540,960,8),dtype=np.uint8)
        points = generator.integers(0,256,size=(540,960,12),dtype=np.uint8)
        valid = generator.integers(0,2,size=(540,960),dtype=np.uint8).astype(bool)
        output = io.BytesIO()
        np.savez_compressed(output,depth=values,raw_values=values,native_points=points,valid=valid)
        self.assertLess(len(output.getbuffer()),_npz_write_bound(values,values,points,valid))
