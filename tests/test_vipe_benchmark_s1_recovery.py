"""Disposable CPU admission and evidence fixtures; never touch the live ledger."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import s1_recovery as s1
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import canonical, file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.execution import component_recovery_request, result_record


def synthetic_assets(root, put):
    from vipe_benchmark.backends import REQUIRED_ASSETS, SOURCE_PINS, CHECKPOINT_NAMES
    from vipe_benchmark.setup_recipes import CORE_IMPORTS
    from vipe_benchmark.runtime import TARGETS
    assets = {}
    for name in REQUIRED_ASSETS['S1']:
        if name.endswith(('_source', '_snapshot')):
            rec = put(name+'/fixture.json', {'synthetic':name})
            assets[name] = dict(path=str(root/name), files=[rec], revision=SOURCE_PINS.get(name,'a'*40))
        else:
            assets[name] = put('weights/'+CHECKPOINT_NAMES.get(name,name), {'synthetic':name})
    entries, imports, packages = [], [], []
    for module, source, symbols in CORE_IMPORTS['E1']:
        rec = put((source or 'packages')+'/'+module+('.so' if module.endswith('._C') else '.py'), {'synthetic':module})
        if source: assets[source]['files'].append(rec)
        else: packages.append(rec)
        entries.append(dict(rec, modules=[module], mapped_native_library=module.endswith('._C')))
        imports.append(dict(module=module, source_asset=source, symbols=symbols, file=rec))
    for module in ('torch','torchvision','numpy'):
        rec = put('packages/'+module+'.py', {'synthetic':module})
        packages.append(rec)
        entries.append(dict(rec, modules=[module], mapped_native_library=False))
    runtime = dict(python=sys.executable, versions=TARGETS['E1'])
    runtime['inventory'] = put('inventory.json', dict(versions=runtime['versions'], executable=sys.executable,
        packages=[dict(name='fixture',version='1',files=packages)]))
    runtime['imports'] = put('imports.json', dict(status='complete', forwards=0, cuda_context_initialized=False, modules=imports))
    runtime['dependency_lock'] = put('lock.json', {})
    correlation = put('correlation.tar.gz', {'synthetic':'archive, no build'})
    runtime['build_inputs'] = put('build_inputs.json', dict(correlation=dict(correlation, version='0.5.0',repository='spatial-correlation-sampler')))
    loaded = put('loaded.json', dict(schema='vipe-benchmark-loaded-runtime/v1',files=entries,
        interpreter=dict(invoked_executable=sys.executable, executable=file_record(sys.executable))))
    observed = dict(versions=runtime['versions'], isolation=dict(import_guard=True,subprocesses=False,source_roots=['/fixture/vipe']),
        installed_inventory=runtime['inventory'], loaded_files=loaded)
    return assets, runtime, observed


def synthetic_inputs(root, put, config):
    import cv2
    from vipe_benchmark.access import output_identities, annotation_identities
    root.mkdir(exist_ok=True, parents=True)
    valid = np.ones((540,960), bool)
    np.save(root/'valid.npy',valid)
    cv2.imwrite(str(root/'rgb.png'),np.zeros((540,960,3),np.uint8))
    rows=[dict(identity=i.record(),rgb=file_record(root/'rgb.png'),valid=file_record(root/'valid.npy'),
        K=np.eye(3).tolist(),grid='distorted-opencv-integer') for i in dict.fromkeys(output_identities(config,'calibration')+annotation_identities(config))]
    return put('inputs.json', dict(rgb=rows))


def synthetic_row(root, request, *, zero=False, skip=False):
    import cv2
    from vipe_benchmark.backends import s1_class_assignments, detection_rows, SegmentationResult
    from vipe_benchmark.s1_evidence import numeric_file, processed_rgb
    parent=read_json(request['inputs']['path'])['rgb'][0]
    rgb=cv2.cvtColor(cv2.imread(parent['rgb']['path']),cv2.COLOR_BGR2RGB)
    labels=np.zeros(rgb.shape[:2],np.int32)
    logits=np.array([[-3,-.2,-3,-.2,-3,-3]]*(2 if skip else 1),np.float32)
    if zero: logits[:]=-3
    scores=1/(1+np.exp(-logits))
    selected=np.flatnonzero(scores.max(axis=1)>.35)
    boxes=np.array([[.5,.5,2.,2.],[.5,.5,.25,.25]] if skip else [[.5,.5,.25,.25]],np.float32)
    phrases=['']*len(selected)
    ids=[101,2711,1012,3455,1012,102]
    caption=SimpleNamespace(decode=lambda tokens:{(2711,):'person',(3455,):'basketball'}[tuple(tokens)])
    assignments=s1_class_assignments(scores[selected],{'input_ids':ids},caption,phrases,.5)
    pixel=boxes[selected].astype(np.float64)*([960,540]*2)
    pixel=np.concatenate((pixel[:,:2]-pixel[:,2:]/2,pixel[:,:2]+pixel[:,2:]/2),axis=1)
    detections=detection_rows(pixel,scores[selected].max(axis=1),phrases,assignments)
    semantics={}
    if len(selected):
        d=detections[-1]; semantics={'1':dict(d,id=1,box=np.asarray(d['box']).astype(np.int64).tolist())}
        labels[200:210,400:410]=1
    arrays=dict(detector_raw_token_logits=logits,detector_raw_boxes_cxcywh=boxes,
        detector_token_scores=scores,detector_native_boxes_cxcywh=boxes[selected],
        detector_selected_scores=scores[selected].max(axis=1),detector_selected_query_indices=selected,
        detector_token_ids=np.array(ids),detector_rgb=processed_rgb(rgb),detector_native_phrase_utf8=np.array([],np.uint8),
        detector_native_phrase_offsets=np.zeros(len(selected)+1,np.int64))
    root.mkdir(exist_ok=True,parents=True)
    np.save(root/'labels.npy',labels)
    cv2.imwrite(str(root/'static.png'),SegmentationResult(labels,semantics,np.ones(labels.shape,bool),{}).static(np.zeros(labels.shape,bool)))
    row=dict(identity=parent['identity'],K=parent['K'],grid=parent['grid'],valid=parent['valid'],
        source_rgb_sha256=parent['rgb']['sha256'],instances=file_record(root/'labels.npy'),semantics=semantics,
        semantic_static=file_record(root/'static.png'),metadata=dict(detections=detections,skipped_box_indices=[0] if skip else []),
        diagnostics=numeric_file(root/'diagnostics.npz',arrays), native_group_wall_seconds=.125, group_size=1)
    return row,arrays


class ReceiptFixture:
    """Structurally coherent disposable graph; never claims observed execution."""
    def __init__(self, root, parents=None):
        from vipe_benchmark import s1_validation_contract as contract
        import datetime
        self.contract = c = contract
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.provenance = 'synthetic fixture; no execution performed'
        def save(name, data):
            path = self.root/name
            path.write_bytes(data)
            return file_record(path)
        self.stdin = save('stdin.py', c.STDIN.encode())
        self.runner = save('runner.py', c.RUNNER.read_bytes())
        self.capture = save('capture.py', c.CAPTURE.read_bytes())
        self.stdout = save('stdout.log', b'synthetic fixture only; no tests executed\n')
        self.stderr = save('stderr.log', b'')
        self.process_stdout = save('process-stdout.log', Path(self.stdout['path']).read_bytes())
        self.process_stderr = save('process-stderr.log', b'')
        def stamp(seconds):
            return dict(utc=(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=seconds)).isoformat(), monotonic=float(seconds))
        methods, declarations = c.collection()
        cases = [dict(id=name, status='passed', subtests=[dict(id=c.callback_id(name, params), parameters=copy.deepcopy(params), status='passed')
                 for params in declarations.get(name, [])]) for name in methods]
        invocation = dict(launcher_argv=list(c.ARGV), python_argv=['-'], runpy_argv=[str(c.RUNNER.resolve())],
            executable=str(ROOT/c.ARGV[0]), resolved_interpreter=str((ROOT/c.ARGV[0]).resolve()),
            thread_environment={k:'1' for k in c.THREADS}, environment=dict(c.ENVIRONMENT), cwd=str(ROOT), run_directory=str(self.root))
        sources = [file_record(p) for p in c.source_paths()]
        suites = []
        for index, name in enumerate(c.SUITES):
            rows = [r for r in cases if r['id'].startswith('test_vipe_benchmark_'+name+'.')]
            suites.append(dict(suite=name, start=stamp(index+2), end=stamp(index+2.5), elapsed_seconds=.5,
                invocation=copy.deepcopy(invocation), collected=[r['id'] for r in rows], **c.counters(rows)))
        self.inner = dict(schema='s1-cpu-aggregate/v2', provenance=self.provenance, diagnostic=False,
            suite_order=list(c.SUITES), collected=methods, declarations=declarations, cases=cases, suites=suites,
            discovery_errors=[], **c.counters(cases), expected_exit_code=0, passed=True,
            sources_before=copy.deepcopy(sources), sources_after=copy.deepcopy(sources), run_directory=str(self.root),
            start=stamp(1), end=stamp(20), elapsed_seconds=19., boot_id='00000000-0000-0000-0000-000000000000',
            stdin=self.stdin, runner=self.runner, stdout=self.stdout, stderr=self.stderr,
            interpreter=file_record(ROOT/c.ARGV[0]), invocation=invocation)
        self.outer = dict(schema='s1-cpu-execution/v1', provenance=self.provenance, requested_argv=list(c.ARGV), cwd=str(ROOT),
            environment=dict(c.ENVIRONMENT), run_directory=str(self.root), start=stamp(0), end=stamp(21), elapsed_seconds=21.,
            child_pid=123, returncode=0, timed_out=False, wait_completed=True, timeout_seconds=300,
            boot_id=self.inner['boot_id'], sources_before=copy.deepcopy(sources), sources_after=copy.deepcopy(sources),
            stdin=self.stdin, runner=self.runner, capture=self.capture, interpreter=self.inner['interpreter'],
            stdout=self.process_stdout, stderr=self.process_stderr)
        if parents is None:
            parent = save('fixture-parent.json', b'{"provenance":"synthetic parent"}\n')
            parents = {key: parent for key in ('semantic_amendment','configuration','baseline','baseline_correction','plan')}
        self.wrapper = dict(schema='plan031-s1-recovery-validation/v2', provenance=self.provenance, status='passed',
            aggregate_passed=True, receipt_milestone_complete=False, implementation_acceptance_complete=False,
            ready_for_live_admission=False, objective_complete=False, sources=copy.deepcopy(sources),
            diff_check=dict(command='git diff --check', exit_code=0, stdout='', stderr=''), **parents)
        self.publish()

    def publish(self):
        import json
        def save(name, value):
            (self.root/name).write_text(json.dumps(value, indent=2, allow_nan=True)+'\n')
            return file_record(self.root/name)
        inner = save('receipt.json', self.inner)
        self.outer['receipt'] = inner
        outer = save('execution.json', self.outer)
        self.wrapper['tests'] = [dict(receipt=inner, execution=outer)]
        self.record = save('validation.json', self.wrapper)
        return self.record

    def validate(self):
        return s1.validation_record(self.record, self.wrapper['semantic_amendment'], self.wrapper['configuration'])


class S1RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = load()
        self.ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        self.counter = 0
        self.source = self.put('source.json', {'source': True})
        # Synthetic asset bytes obey the real AssetBundle contract; no model loads.
        self.configuration = file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
        assets, runtime, self.observed = synthetic_assets(self.root, self.put)
        self.assets = self.put('assets.json', assets)
        setup = self.put('jobs/E1-setup-recovery-002/result.json', dict(status='complete',
            environment='E1', components=['S1'], runtime=runtime, assets=self.assets))
        # Fixture prerequisite events are append-only; checked recovery mutations
        # below use the production registration/reservation methods.
        for job, result in [('E1-setup-recovery-002', setup)]:
            self.append(event='finish', job_id=job, status='complete', result=result,
                        resource='setup', elapsed_seconds=0, cleanup_confirmed=True)
        inputs = synthetic_inputs(self.root, self.put, self.config)
        policy, review = self.put('policy.json', {}), self.put('review.json', {})
        from vipe_benchmark.annotations import template, HOURS, IMAGE_FLAGS
        bundle = template(read_json(inputs['path']), self.config)
        primary = self.put('primary.json', {})
        layer_path = self.root/'truth.npz'
        np.savez_compressed(layer_path, instances=np.zeros((540,960),np.int32),
            valid=np.ones((540,960),bool), changing=np.zeros((540,960),bool), ignored=np.zeros((540,960),bool))
        layers = file_record(layer_path)
        review_row = self.put('review-row.json',dict(reviewer_id='reviewer',
            primary_revision_sha256=primary['sha256'],blind_to_outputs_methods_scores=True))
        adjudication = self.put('adjudication.json',dict(review_sha256=review_row['sha256'],
            final_layers_sha256=layers['sha256'],unresolved_disagreements=0))
        bundle.update(policy=policy, contributors=dict(
            primary=dict(id='primary',kind='external_human',attestation=primary),
            independent_review=dict(id='reviewer',kind='external_human',attestation=review,record=review)))
        for row in bundle['images']:
            row.update(status='reviewed-adjudicated', primary_revision=primary,review_record=review_row,
                adjudication_record=adjudication,final_layers=layers,instances={},
                tags={k:False for k in IMAGE_FLAGS}, static_feature_review=[])
        for pair in bundle['pairs']: pair['associations']=[]
        annotations = self.put('annotations.json', bundle)
        for job, key, value in [('prepare', 'inputs', inputs), ('annotations', 'annotations', annotations)]:
            rec = self.put(job+'/result.json', dict(status='complete', **{key:value}))
            self.append(event='finish', job_id=job, status='complete', result=rec, resource='cpu', elapsed_seconds=0)
        amendment_event = self.ledger.note('annotation_amendment', policy=policy)
        from vipe_benchmark.backends import REQUIRED_ASSETS
        historical_assets = {k:self.source for name in ('S0','D0') for k in REQUIRED_ASSETS[name]}
        historical_assets['vipe_source'] = dict(path='/fixture/vipe')
        old_assets = self.put('qualification/historical-assets.json', dict(assets=historical_assets))
        existing = self.put('qualification/result.json',dict(status='complete',assets=old_assets,
            runtime=dict(E0=runtime,E8=runtime)))
        self.ledger.charge_cpu_preparation(0, existing)
        self.append(event='setup_recovery_authorized',job_id='E1-setup-recovery-002',
            original_job_id='E1-setup',environment='E1',preparation_elapsed_seconds=0,
            authorization=self.put('setup-auth.json',{}))
        self.original = dict(job_id='S1-calibration', component='S1', branch='calibration',
            inputs=inputs, runtime=runtime, assets=assets, forbidden_vipe_roots=['/fixture/vipe'])
        historical = self.put('requests/S1-calibration.json', dict(self.original, configuration=self.configuration))
        self.ledger.reserve('S1-calibration', [], dict(request=historical))
        failure = self.put('jobs/S1-calibration/failure.json', dict(status='failed', job_id='S1-calibration'))
        event = self.ledger.finish('S1-calibration', 'failed', 10, cleanup_confirmed=True, surviving_pids=[])
        self.historical_state()
        snap = dict(**file_record(self.ledger.path), events=len(self.ledger.events()), last_event_sha256=self.ledger.events()[-1]['event_sha256'])
        status = self.put('status.md', {'stage':'fixture'})
        frozen = self.put('frozen.json', {'scientific':'immutable'})
        baseline = self.put('baseline.json', dict(schema='plan032-s1-recovery-baseline/v1',
            ledger_snapshot=snap, preserved_records=[file_record(self.ledger.path), status, frozen]))
        amendment = self.put('amendment.json', dict(schema='plan031-s1-semantic-assignment-amendment/v1',
            amendment_id=s1.AMENDMENT, changes_to_semantic_protocol=True, scope=['S1-calibration'],
            frozen_parents=[self.source], verified_s0_sources=[self.source], native_predict_source=self.source,
            original_failures=[dict(branch='calibration', failure=failure, event_sha256=event['event_sha256'], cleanup_confirmed=True)]))
        plan = self.put('plan.json', {})
        correction = self.put('correction.json', dict(schema='plan033-s1-baseline-correction/v1',
            baseline=baseline, plan=plan, review=self.put('review-baseline.json', {}),
            ledger_snapshot=snap, frozen_records=[frozen], bookkeeping_baseline=status,
            bookkeeping_policy='separate immutable old/new hash transitions; never scientific evidence',
            bookkeeping_transitions=[]))
        graph = ReceiptFixture(self.root/'receipt-fixture', dict(semantic_amendment=amendment,
            configuration=self.configuration, baseline=baseline, baseline_correction=correction, plan=plan))
        self.validation = graph.wrapper
        validation = graph.record
        self.document = dict(schema=s1.SCHEMA, job_id=s1.JOB, original_job_id='S1-calibration',
            attempts_limit=1, seconds_limit=3600, gpu_total_seconds_limit=93600,
            reset_previous_consumption=False, changes_to_prescribed_configuration=True,
            unrelated_attempts_reopened=False, reconstruction_authorized=False,
            semantic_amendment_approved=True, additional_attempt_approved=True,
            authorization='Synthetic CPU fixture only', authorization_context=dict(request_date='fixture', stage='DO', scope='calibration'),
            semantic_amendment=amendment, original_failure=failure, original_failure_event_sha256=event['event_sha256'],
            repair_validation=validation, configuration=self.configuration, plan=plan, baseline=baseline,
            baseline_correction=correction, implementation_review=self.put('implementation-review.json', {}), ledger_baseline=snap,
            e1_qualification=setup, e1_assets=self.assets, e1_runtime=runtime, inputs=inputs,
            annotations=annotations, annotation_policy=policy, annotation_review=review,
            annotation_amendment_event=s1.event_ref(amendment_event), historical_request=historical,
            original_request_sha256=object_hash(self.original), resource_limits=s1.LIMITS.copy())

    def historical_state(self):
        if self._testMethodName == 'test_reduced_cumulative_deadline':
            self.append(event='finish', job_id='fixture-charge', status='failed', resource='gpu', elapsed_seconds=93500)
        elif self._testMethodName == 'test_live_cleanup_active_and_exhausted_state':
            self.ledger.reserve('S2-calibration', [], {})
        elif self._testMethodName == 'test_exhausted_state':
            self.append(event='finish', job_id='fixture-charge', status='failed', resource='gpu', elapsed_seconds=93600)

    def append(self, **event):
        with self.ledger.locked() as (stream, events):
            return self.ledger._append(stream, events, event)

    def put(self, name, value):
        path = self.root / name
        write_json(path, value)
        return file_record(path)

    def auth(self, **changes):
        self.counter += 1
        return self.put(f'auth-{self.counter}.json', dict(self.document, **changes))

    def admit(self, auth):
        doc = read_json(auth['path'])
        evidence = dict(doc, s1_recovery_authorization=auth, implementation_validation=doc['repair_validation'])
        rec = self.put(f'admission-{self.counter}.json', dict(status='admitted', evidence=evidence, resources={}))
        self.ledger.note('admission', evidence=rec)
        return rec

    def register(self):
        auth = self.auth()
        admission = self.admit(auth)
        event = self.ledger.authorize_component_recovery(auth)
        request = dict(component_recovery_request(self.root, self.config, s1.JOB), configuration=self.configuration)
        evidence = dict(request=self.put('requests/'+s1.JOB+'.json', request),
            worker=file_record(ROOT/'scripts/basketball_vipe_worker.py'), authorization=auth,
            admission=admission, authorization_event=s1.event_ref(event),
            **{k:self.document[k] for k in s1.BINDINGS if k != 'original_request_sha256'})
        return auth, request, evidence

    def command(self, evidence):
        return s1.canonical_dispatch(self.document, evidence['authorization'], evidence)

    def test_binding_historical_versus_canonical_and_no_mutation(self):
        before = self.ledger.path.read_bytes()
        auth = self.auth()
        self.assertEqual(s1.validate_binding(self.root,self.config,auth)[1], self.original)
        self.assertEqual(before,self.ledger.path.read_bytes())
        with self.assertRaisesRegex(ValueError,'canonical'):
            s1.validate_binding(self.root,self.config,self.auth(original_request_sha256=self.document['historical_request']['sha256']))

    def test_typed_scope_schema_branch_and_second_identity(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            key, value = case["key"], case["value"]
            with self.subTest(**case),self.assertRaises(ValueError):
                s1.validate_binding(self.root,self.config,self.auth(**{key:value}))

    def test_validation_missing_extra_duplicate_aliased_stale_and_failed_receipts(self):
        mutations = dict([('missing',dict(sources=[])),('extra',dict(sources=[self.source,self.document['plan']])),
            ('duplicate',dict(sources=[self.source,self.source])),('old',dict(schema='old')),
            ('no_tests',dict(tests=[])),('failed',dict(tests=[dict(self.validation['tests'][0],failures=1)])),
            ('skipped',dict(tests=[dict(self.validation['tests'][0],skipped=1)])),
            ('alias',dict(sources=[dict(self.source,path=str(self.root/'..'/self.root.name/'source.json'))])),
            ('bytes',dict(sources=[dict(self.source,bytes=1)]))])
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            label = case['label']
            change = mutations[label]
            with self.subTest(**case):
                validation=self.put(label+'.json',dict(self.validation,**change))
                with self.assertRaises(ValueError):
                    s1.validate_binding(self.root,self.config,self.auth(repair_validation=validation))
        Path(self.source['path']).write_text('{}')
        with self.assertRaises(ValueError): s1.validate_binding(self.root,self.config,self.auth())

    def test_changed_prerequisite_records_rejected(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            key = case['key']
            with self.subTest(**case), self.assertRaises(ValueError):
                s1.validate_binding(self.root,self.config,self.auth(**{key:dict(self.document[key],sha256='0'*64)}))
        with self.assertRaises(ValueError):
            s1.validate_binding(self.root,self.config,self.auth(e1_runtime={}))
        with self.assertRaises(ValueError):
            s1.validate_binding(self.root,self.config,self.auth(original_failure_event_sha256='0'*64))

    def test_live_cleanup_active_and_exhausted_state(self):
        auth=self.auth()
        with self.assertRaisesRegex(ValueError,'active'):s1.validate_binding(self.root,self.config,auth)

    def test_exhausted_state(self):
        with self.assertRaisesRegex(ValueError,'exhausted'):
            s1.validate_binding(self.root,self.config,self.auth())

    def test_registration_needs_admission_duplicate_and_reservation_consumes_once(self):
        auth=self.auth()
        with self.assertRaisesRegex(ValueError,'admission'):self.ledger.authorize_component_recovery(auth)
        auth,request,evidence=self.register()
        with self.assertRaisesRegex(ValueError,'already allocated'):self.ledger.authorize_component_recovery(auth)
        self.ledger.reserve(s1.JOB,self.command(evidence),evidence)
        with self.assertRaises(ValueError):self.ledger.reserve(s1.JOB,self.command(evidence),evidence)
        with self.assertRaisesRegex(ValueError,'consumed'):component_recovery_request(self.root,self.config,s1.JOB)

    def test_reduced_remaining_time_and_mutation_at_reservation_lock(self):
        auth,request,evidence=self.register()
        bad=copy.deepcopy(evidence);bad['authorization_event']['sequence']+=1
        with self.assertRaisesRegex(ValueError,'event'):self.ledger.reserve(s1.JOB,self.command(evidence),bad)
        Path(evidence['request']['path']).write_text('{}')
        with self.assertRaises(ValueError):self.ledger.reserve(s1.JOB,self.command(evidence),evidence)

    def test_reduced_cumulative_deadline(self):
        _,_,evidence=self.register()
        self.assertEqual(self.ledger.reserve(s1.JOB,self.command(evidence),evidence)['seconds'],90)

    def run_controller(self):
        import os, subprocess, time
        from vipe_benchmark.execution import execute_s1_recovery
        from vipe_benchmark.access import output_identities
        from vipe_benchmark.s1_evidence import qualify_row, first_record
        output=self.root/'jobs'/s1.JOB
        docs=self.root/'docs'; docs.mkdir(exist_ok=True)
        auth=self.auth()
        real_popen=subprocess.Popen
        def worker(command, **kwargs):
            request=read_json(command[command.index('--request')+1])
            self.put('jobs/'+s1.JOB+'/config.json',request)
            row,_=synthetic_row(self.root/'numeric',request)
            rows=[dict(row,identity=i.record()) for i in output_identities(self.config,'calibration')]
            import json
            from vipe_benchmark.s1_clock import ReservationClock
            reservation = self.ledger.states()[s1.JOB]
            self.clock = s1.captured_clock(self.root, self.config, reservation, command)
            self.clock.match(json.loads(kwargs['env']['VIPE_S1_RESERVATION_CLOCK']))
            first=first_record(request,output,'passed',clock=self.clock,rows=rows[:1],runtime=self.observed,
                checks=qualify_row(row,request,first=True),raw=[row['diagnostics']])
            self.put('jobs/'+s1.JOB+'/result.json',dict(status='complete',job_id=s1.JOB,
                component='S1',branch='calibration',rows=rows,runtime=self.observed,
                native_wall_seconds=sum(r['native_group_wall_seconds'] for r in rows),
                peak_allocated_bytes=1024,peak_reserved_bytes=2048,
                configuration=file_record(output/'config.json'),first_result=first,reservation_clock=self.clock.mapping()))
            if hasattr(self,'before_worker_return'):
                self.before_worker_return(request,output,reservation)
            return real_popen([sys.executable,'-c','pass'],**kwargs)
        original_read=Path.read_text
        def host_read(path,*args,**kwargs):
            return 'systemd' if str(path)=='/proc/1/comm' else original_read(path,*args,**kwargs)
        readings=dict(device_bytes=0,artifact_bytes=0,download_bytes=0,gpu_pids=[])
        with patch('vipe_benchmark.execution.gpu_reading',return_value=readings), \
             patch('vipe_benchmark.execution.resources',return_value=readings), \
             patch('vipe_benchmark.execution.s1_sampling_operation',return_value=dict(operation='constant',args=dict(value=readings))), \
             patch.object(Path,'read_text',host_read), \
             patch('vipe_benchmark.supervisor.subprocess.Popen',side_effect=worker):
            execute_s1_recovery(self.root,docs,self.config,auth)
        return auth,read_json(output/'config.json'),file_record(output/'result.json')

    def test_result_requires_supervised_cleanup_and_exact_membership(self):
        from vipe_benchmark.s1_evidence import validate_result
        auth,request,result=self.run_controller()
        finish=self.ledger.states()[s1.JOB]
        self.assertEqual(result_record(self.root,'S1-calibration'),result)
        self.assertEqual(self.ledger.states()['S1-calibration']['status'],'failed')
        receipt=read_json(finish['terminal_receipt']['path'])
        self.assertEqual(receipt['counts']['fit_qualified'],340)
        self.assertEqual(receipt['counts']['selection_qualified'],170)
        for event in self.ledger.events()[self.document['ledger_baseline']['events']:]:
            if event['event']=='admission':
                bound=read_json(event['evidence']['path'])['evidence']
            elif event['event']=='component_recovery_authorized': bound=event
            elif event['event']=='reserve': bound=event['evidence']
            else: continue
            self.assertEqual(bound['baseline_correction'],self.document['baseline_correction'])
        mutations = dict(cleanup_confirmed=False, surviving_pids=[123], deadline_exceeded=True, acceptance=None)
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            field = case['field']
            value = mutations[field]
            with self.subTest(**case), self.assertRaises((ValueError,TypeError)):
                s1.resolved_result(self.root,self.config,self.ledger.events(),dict(finish,**{field:value}))
        doc=read_json(result['path']);rows=doc['rows']
        for badrows in (rows[:-1],rows[:-1]+rows[:1],list(reversed(rows))):
            with self.assertRaises(ValueError): validate_result(dict(doc,rows=badrows),request,self.config,clock=self.clock)
        Path(result['path']).write_text('{}')
        with self.assertRaises(ValueError):result_record(self.root,'S1-calibration')

    def test_registered_authorization_and_validation_mutation_block(self):
        auth,_,evidence=self.register()
        Path(self.document['repair_validation']['path']).write_text('{}')
        with self.assertRaises(ValueError):component_recovery_request(self.root,self.config,s1.JOB)
        with self.assertRaises(ValueError):self.ledger.reserve(s1.JOB,self.command(evidence),evidence)


class FailureEvidenceTests(unittest.TestCase):
    def test_alignment_layout_pre_forward_and_no_stale_capture(self):
        from test_vipe_benchmark_s1_semantics import S1SemanticsTests
        from vipe_benchmark.access import Identity
        from vipe_benchmark.s1_evidence import preserve_failure
        fixture=S1SemanticsTests()
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            failure = case['failure']
            with self.subTest(**case),tempfile.TemporaryDirectory() as temp:
                detector=fixture.detector(failure=='alignment')
                if failure=='layout':detector.model.tokenizer=lambda _:dict(input_ids=[101,10,102])
                if failure=='before':
                    detector(np.zeros((10,20,3),np.uint8))
                    detector.transform=lambda *_: (_ for _ in ()).throw(ValueError('before forward'))
                try:detector(np.zeros((10,20,3),np.uint8))
                except Exception as exc:
                    rec=preserve_failure(dict(job_id='S1-calibration'),Path(temp),Identity('calibration',0,50),exc)
                    value=read_json(rec['path'])
                    self.assertEqual(value['forward_count'],0 if failure=='before' else 1)
                    if failure=='before':self.assertFalse(value['available_fields'])
                    else:
                        self.assertIn('detector_raw_token_logits',value['available_fields'])
                        path=value['array_records']['detector_raw_token_logits']['file']['path']
                        with np.load(path,allow_pickle=False) as arrays:self.assertFalse(arrays['detector_raw_token_logits'].dtype.hasobject)
                else:self.fail('expected original exception')

    def test_first_result_failure_stops_before_second_input(self):
        import cv2
        from vipe_benchmark.access import Identity
        from vipe_benchmark.backends import SegmentationResult
        from vipe_benchmark.stages import segment
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            kind = case['kind']
            with self.subTest(**case),tempfile.TemporaryDirectory() as temp:
                fixture = S1RecoveryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
                _, request, evidence = fixture.register()
                reservation = fixture.ledger.reserve(s1.JOB, fixture.command(evidence), evidence)
                clock = s1.captured_clock(fixture.root, fixture.config, reservation, fixture.command(evidence))
                root=Path(temp);valid=np.ones((540,960),bool)
                identities=[Identity('calibration',0,f) for f in (50,62)]
                labels=np.zeros(valid.shape,np.int32)
                prediction=SegmentationResult(labels,{},valid,{})
                if kind == 'qualification':
                    row,arrays=synthetic_row(root/'numeric',request)
                    arrays['detector_token_scores'][0,0]=.99
                    prediction=SegmentationResult(np.load(row['instances']['path']),row['semantics'],valid,
                        row['metadata'],diagnostics=arrays)
                calls=[]
                def predict(*args,**kwargs):
                    calls.append(1)
                    if kind == 'contract':
                        prediction.labels = prediction.labels.astype(np.float32)
                    return [prediction]
                backend=SimpleNamespace(segment=predict)
                cuda=SimpleNamespace(synchronize=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0)
                from contextlib import ExitStack
                with ExitStack() as stack:
                    stack.enter_context(patch.dict(sys.modules,{'torch':SimpleNamespace(cuda=cuda)}))
                    stack.enter_context(patch('vipe_benchmark.stages._model_runtime',return_value={}))
                    stack.enter_context(patch('vipe_benchmark.stages.output_identities',return_value=identities))
                    stack.enter_context(patch('vipe_benchmark.backends.build_backend',return_value=backend))
                    if kind=='serialization':stack.enter_context(patch('vipe_benchmark.stages.png_file',side_effect=ValueError('serialization failed')))
                    expected = {'contract': 'instances must be int32 on the image grid',
                                'serialization': 'serialization failed', 'qualification': 'invalid raw S1 logits/probabilities/boxes'}[kind]
                    with self.assertRaisesRegex((ValueError,KeyError), expected):
                        segment(request,root/'output',load(),clock=clock)
                self.assertEqual(len(calls),1)
                self.assertNotEqual(read_json(root/'output/first-result-qualification.json')['status'],'passed')
                self.assertEqual(len(list((root/'output').rglob('*-failure-evidence.json'))),1)
                failure = read_json(next((root/'output').rglob('*-failure-evidence.json')))
                self.assertEqual(failure['failure_stage'], {'contract':'output_contract',
                    'serialization':'serialization', 'qualification':'first_result'}[kind])
                self.assertIn('labels', failure['available_fields'])
                self.assertFalse((root/'output/result.json').exists())
                self.assertFalse((root/'output/calibration/camera0/frame62.npy').exists())





class ReceiptContractTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        graph = ReceiptFixture(Path(temporary.name))
        graph.validate()  # Every mutation starts with an independently passing graph.
        return graph

    def test_positive_complete_fixture(self):
        graph = self.fixture()
        self.assertIn('no execution performed', graph.validate()['provenance'])
        graph.contract.validate_inner(graph.inner)

    def test_typed_primitive_callbacks(self):
        from vipe_benchmark.s1_validation_contract import identity
        seen = set()
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                key = identity(case)
                self.assertNotIn(key, seen)
                seen.add(key)

    def test_declaration_parser_mutations(self):
        from vipe_benchmark.s1_validation_contract import parse_suite
        method = 'fixture.Tests.test_case'
        prefix = 'import unittest\nclass Tests(unittest.TestCase):\n    def test_case(self):\n        with self.subTest(**case): pass\n'
        good = prefix + "SUBTEST_CASES = {'fixture.Tests.test_case': [{'value': 1}]}\n"
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                self.assertEqual(parse_suite(good, 'fixture')[1], {method:[dict(value=1)]})
                label = case['mutation']
                variants = {
                    'missing': prefix,
                    'dynamic': prefix + 'SUBTEST_CASES = dict()\n',
                    'duplicate_assignment': good + 'SUBTEST_CASES = {}\n',
                    'duplicate_method': prefix + "SUBTEST_CASES = {'fixture.Tests.test_case': [{'value':1}], 'fixture.Tests.test_case': [{'value':2}]}\n",
                    'duplicate_field': prefix + "SUBTEST_CASES = {'fixture.Tests.test_case': [{'value':1, 'value':2}]}\n",
                    'extraneous': good.replace('fixture.Tests.test_case', 'fixture.Tests.test_other'),
                    'ordinary': good.replace('with self.subTest(**case): pass', 'pass'),
                    'duplicate_tuple': good.replace("[{'value': 1}]", "[{'value': 1}, {'value': 1}]"),
                    'nonprimitive': good.replace("'value': 1", "'value': []"),
                    'nonfinite': good.replace("'value': 1", "'value': 1e999"),
                    'unpacking': good.replace("{'value': 1}", "{**{'value': 1}}"),
                    'empty': good.replace("[{'value': 1}]", '[]'),
                    'indirect': good.replace('self.subTest', 'other.subTest'),
                    'getattr': good.replace('self.subTest', 'getattr(self, "subTest")'),
                    'mutation': good + "SUBTEST_CASES.update({})\n",
                    'subscript': good + "SUBTEST_CASES['extra'] = []\n",
                    'augmented': good + "SUBTEST_CASES |= {}\n",
                }
                with self.assertRaisesRegex(ValueError, case['error']):
                    parse_suite(variants[label], 'fixture')

    def test_callback_mutations(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                graph = self.fixture()
                parent = next(row for row in graph.inner['cases'] if row['id'] == 'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_typed_primitive_callbacks')
                callbacks = parent['subtests']
                label = case['mutation']
                if label == 'missing': callbacks.pop()
                elif label == 'substituted': callbacks[0] = copy.deepcopy(callbacks[-1])
                elif label == 'reordered': callbacks.reverse()
                elif label == 'duplicated': callbacks[1] = copy.deepcopy(callbacks[0])
                elif label == 'removed_field': callbacks[0]['parameters'] = {}
                elif label == 'extra_field': callbacks[0]['parameters']['extra'] = 0
                elif label == 'bool_int': callbacks[1]['parameters']['value'] = 1
                elif label == 'int_float': callbacks[3]['parameters']['value'] = 1.0
                elif label == 'null_string': callbacks[5]['parameters']['value'] = 'None'
                elif label == 'id': callbacks[0]['id'] = 'wrong'
                elif label == 'extra_ordinary':
                    next(row for row in graph.inner['cases'] if not row['subtests'])['subtests'] = [copy.deepcopy(callbacks[0])]
                elif label in ('failed', 'error', 'skipped'): callbacks[0]['status'] = label
                else: raise AssertionError(label)
                with self.assertRaisesRegex(ValueError, case['error']): graph.contract.validate_inner(graph.inner)
                graph.publish()
                with self.assertRaisesRegex(ValueError, case['error']): graph.validate()

    def test_accounting_mutations(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                graph = self.fixture()
                inner = graph.inner
                label = case['mutation']
                if label == 'missing_method': inner['collected'].pop()
                elif label == 'extra_method': inner['collected'].append('extra')
                elif label == 'reordered_method': inner['collected'].reverse()
                elif label == 'duplicate_method': inner['collected'][1] = inner['collected'][0]
                elif label == 'missing_suite': inner['suite_order'].pop()
                elif label == 'extra_suite': inner['suite_order'].append('extra')
                elif label == 'reordered_suite': inner['suite_order'].reverse()
                elif label == 'duplicate_suite': inner['suite_order'][1] = inner['suite_order'][0]
                elif label == 'discovery': inner['discovery_errors'] = ['test import failed']
                elif label == 'count': inner['tests_run'] += 1
                elif label == 'bool_count': inner['failures'] = False
                elif label == 'float_count': inner['subtests_run'] = float(inner['subtests_run'])
                elif label == 'suite_count': inner['suites'][0]['tests_run'] += 1
                elif label == 'suite_bool': inner['suites'][0]['errors'] = False
                elif label == 'suite_float': inner['suites'][0]['subtests_run'] = float(inner['suites'][0]['subtests_run'])
                elif label == 'diff_bool': graph.wrapper['diff_check']['exit_code'] = False
                elif label == 'diff_float': graph.wrapper['diff_check']['exit_code'] = 0.0
                elif label == 'schema': inner['schema'] = 's1-cpu-aggregate/v1'
                elif label == 'expected_bool': inner['expected_exit_code'] = False
                elif label == 'expected_float': inner['expected_exit_code'] = 0.0
                else: raise AssertionError(label)
                graph.publish()
                with self.assertRaisesRegex(ValueError, case['error']): graph.validate()

    def test_binding_mutations(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                graph = self.fixture()
                label = case['mutation']
                if label in ('stdin', 'runner', 'stdout', 'stderr'):
                    Path(graph.inner[label]['path']).write_bytes(b'changed fixture bytes')
                elif label == 'missing_log': Path(graph.inner['stdout']['path']).unlink()
                elif label == 'alias':
                    graph.inner['stdin']['path'] = str(graph.root/'..'/graph.root.name/'stdin.py')
                elif label == 'interpreter': graph.inner['interpreter'] = graph.stdin
                elif label == 'stale_source': graph.inner['sources_before'][0]['sha256'] = '0'*64
                elif label == 'source_bytes': graph.inner['sources_before'][0]['bytes'] += 1
                elif label == 'source_bool': graph.inner['sources_before'][0]['bytes'] = True
                elif label == 'duplicate_source': graph.inner['sources_before'].append(graph.inner['sources_before'][0])
                elif label == 'missing_source': graph.inner['sources_before'].pop()
                elif label == 'extra_source': graph.inner['sources_before'].append(graph.stdin)
                elif label == 'unequal_sources': graph.inner['sources_after'].reverse()
                elif label == 'outer_source': graph.outer['sources_after'].pop()
                elif label == 'cross_run':
                    other = self.fixture()
                    graph.outer = other.outer
                elif label == 'capture': Path(graph.outer['capture']['path']).write_text('changed snapshot')
                else: raise AssertionError(label)
                graph.publish()
                with self.assertRaisesRegex(ValueError, case['error']): graph.validate()

    def test_artifact_record_matrix(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                graph = self.fixture()
                kind, mutation = case['kind'], case['mutation']
                target = graph.inner['sources_before'][0] if kind == 'source' else graph.inner[kind]
                if mutation == 'missing': target['path'] = str(graph.root/'absent-artifact')
                elif mutation == 'stale': target['sha256'] = '0'*64
                elif mutation == 'alias':
                    path = Path(target['path'])
                    target['path'] = str(path.parent/'..'/path.parent.name/path.name)
                else: raise AssertionError(mutation)
                graph.publish()
                with self.assertRaisesRegex(ValueError, case['error']): graph.validate()

    def test_execution_mutations(self):
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                graph = self.fixture()
                inner, outer = graph.inner, graph.outer
                label = case['mutation']
                if label == 'argv': inner['invocation']['launcher_argv'].append('extra')
                elif label == 'flag': inner['invocation']['launcher_argv'][1] = '-I'
                elif label == 'python_argv': inner['invocation']['python_argv'] = ['other']
                elif label == 'runpy_argv': inner['invocation']['runpy_argv'] = ['other']
                elif label == 'interpreter': inner['invocation']['executable'] = '/usr/bin/python3'
                elif label == 'cwd': inner['invocation']['cwd'] = str(graph.root)
                elif label == 'env': inner['invocation']['environment']['OMP_NUM_THREADS'] = '2'
                elif label == 'diagnostic': inner['invocation']['environment']['S1_RECEIPT_DIAGNOSTIC'] = '1'
                elif label == 'utc': inner['start']['utc'] = 'bad'
                elif label == 'naive': inner['start']['utc'] = '2026-01-01T00:00:01'
                elif label == 'nonfinite': inner['elapsed_seconds'] = float('nan')
                elif label == 'negative': inner['start']['monotonic'] = -1
                elif label == 'reversed': inner['end']['monotonic'] = 0
                elif label == 'inconsistent': inner['elapsed_seconds'] += 1
                elif label == 'boolean_time': inner['start']['monotonic'] = True
                elif label == 'suite_overlap':
                    inner['suites'][1]['start'] = copy.deepcopy(inner['suites'][0]['start'])
                    inner['suites'][1]['elapsed_seconds'] = 1.5
                elif label == 'envelope': outer['start']['monotonic'] = 2; outer['elapsed_seconds'] = 19.
                elif label == 'boot': outer['boot_id'] = '11111111-1111-1111-1111-111111111111'
                elif label == 'wait': del outer['wait_completed']
                elif label == 'returncode': outer['returncode'] = 1
                elif label == 'bool_returncode': outer['returncode'] = False
                elif label == 'float_returncode': outer['returncode'] = 0.0
                elif label == 'timeout': outer['timed_out'] = True
                elif label == 'outer_argv': outer['requested_argv'].append('extra')
                elif label == 'outer_env': outer['environment']['VIPE_CPU_VALIDATION'] = None
                elif label == 'logs':
                    Path(outer['stdout']['path']).write_text('trailing output')
                    outer['stdout'] = file_record(outer['stdout']['path'])
                elif label == 'cap': outer['timeout_seconds'] = 1
                elif label == 'stdin_rehashed':
                    Path(inner['stdin']['path']).write_text('print("wrong stdin")\n')
                    inner['stdin'] = file_record(inner['stdin']['path'])
                elif label == 'runner_rehashed':
                    Path(inner['runner']['path']).write_text('print("wrong runner")\n')
                    inner['runner'] = file_record(inner['runner']['path'])
                else: raise AssertionError(label)
                if label in ('argv','interpreter','utc','nonfinite'):
                    with self.assertRaisesRegex(ValueError, case['error']): graph.contract.validate_inner(inner)
                graph.publish()
                with self.assertRaisesRegex(ValueError, case['error']): graph.validate()

    def test_legacy_receipts_rejected(self):
        graph = self.fixture()
        old = copy.deepcopy(graph.wrapper)
        old.update(schema='plan031-s1-recovery-validation/v1', tests=[dict(command='synthetic test-only aggregate; NOT execution evidence')])
        with self.assertRaisesRegex(ValueError, 'complete current amendment-bound'):
            graph.contract.validate_wrapper(old, old['semantic_amendment'], old['configuration'])
        old = copy.deepcopy(graph.wrapper)
        old['aggregate'] = old.pop('tests')
        with self.assertRaisesRegex(ValueError, 'alternate aggregate document'):
            graph.contract.validate_wrapper(old, old['semantic_amendment'], old['configuration'])



class ReservationClockTests(unittest.TestCase):
    def admitted(self, *, reduced=False):
        fixture = S1RecoveryTests('test_reduced_cumulative_deadline' if reduced else 'runTest')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        _, request, evidence = fixture.register()
        reservation = fixture.ledger.reserve(s1.JOB, fixture.command(evidence), evidence)
        clock = s1.captured_clock(fixture.root, fixture.config, reservation, fixture.command(evidence))
        return fixture, request, reservation, clock

    def test_context_matrix(self):
        import math
        from vipe_benchmark.s1_clock import ReservationClock
        fixture, request, reservation, clock = self.admitted()
        self.assertEqual(clock.effective_seconds, 3600)
        reduced, _, actual, short = self.admitted(reduced=True)
        self.assertEqual(short.effective_seconds, 90)
        self.assertEqual(short.cleanup_reserve_seconds, 22.5)
        self.assertTrue(clock.match(ReservationClock.from_reservation(reservation).mapping()))
        with self.assertRaisesRegex(ValueError,'captured reservation required'):
            s1.captured_clock(fixture.root,fixture.config,None,reservation['command'])
        bad=copy.deepcopy(reservation); bad['sequence']=float(bad['sequence'])
        with self.assertRaisesRegex(ValueError,'captured active reservation changed'):
            s1.captured_clock(fixture.root,fixture.config,bad,reservation['command'])
        mutations = {'null':None, 'bool':True, 'string':'1', 'nan':float('nan'),
            'infinity':float('inf'), 'negative':-1, 'zero':0}
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                value = copy.deepcopy(clock.mapping()); field, kind = case['field'], case['kind']
                if kind == 'missing': value.pop(field)
                elif kind in mutations: value[field] = mutations[kind]
                elif kind == 'changed':
                    if field == 'job_id': value[field] = 'S1-calibration'
                    elif field == 'boot_id': value[field] = 'wrong-boot'
                    elif field == 'request': value[field] = dict(value[field], bytes=True)
                    elif field == 'reservation': value[field] = dict(sequence=True,event_sha256='x'*64)
                    else: value[field] += 1
                elif kind == 'forged':
                    fake = copy.deepcopy(reservation)
                    if field == 'effective_seconds': fake['seconds'] = 90
                    elif field == 'monotonic_start': fake[field] += 10
                    elif field == 'boot_id': fake[field] = 'other-boot'
                    elif field == 'reservation': fake['sequence'] += 1
                    value = ReservationClock.from_reservation(fake).mapping()
                elif kind == 'oversized': value[field] = 3601
                elif kind == 'overflow':
                    value.update(monotonic_start=1e308, effective_seconds=3600,
                        cleanup_reserve_seconds=30., total_deadline=1e308, work_deadline=1e308)
                elif kind == 'underflow':
                    value.update(monotonic_start=0., effective_seconds=math.nextafter(0.,1.),
                        cleanup_reserve_seconds=0., total_deadline=math.nextafter(0.,1.),work_deadline=math.nextafter(0.,1.))
                elif kind == 'empty': value[field] = ''
                elif kind == 'hash': value[field]['event_sha256'] = '0'*64
                elif kind == 'request_hash': value[field]['sha256'] = '0'*64
                with self.assertRaises((ValueError, TypeError, KeyError)):
                    clock.match(value)

    def test_phase_boundaries(self):
        import math
        from vipe_benchmark import s1_clock
        _, _, _, clock = self.admitted(reduced=True)
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                kind = case['kind']; now = clock.monotonic_start
                if kind == 'before_work': now = math.nextafter(clock.work_deadline, -math.inf)
                elif kind == 'at_work': now = clock.work_deadline
                elif kind == 'after_work': now = math.nextafter(clock.work_deadline, math.inf)
                elif kind == 'at_total': now = clock.total_deadline
                elif kind == 'after_total': now = math.nextafter(clock.total_deadline, math.inf)
                elif kind == 'negative': now = -1
                elif kind == 'nan': now = float('nan')
                elif kind == 'infinity': now = float('inf')
                elif kind == 'before_start': now -= 1
                boot = 'different' if kind == 'wrong_boot' else clock.boot_id
                with patch.object(s1_clock.time, 'monotonic', return_value=now), patch.object(s1_clock, 'boot_id', return_value=boot):
                    if case['valid']:
                        seconds = clock.observe(work=case['work'])
                        self.assertEqual(seconds, now-clock.monotonic_start)
                        self.assertEqual(clock.recorded(seconds, 'passed' if case['work'] else 'failed'), seconds)
                    else:
                        with self.assertRaisesRegex((ValueError, TimeoutError), 'reservation clock'):
                            clock.observe(work=case['work'])
        with patch.object(s1_clock.time, 'monotonic', side_effect=AssertionError('historical read sampled live time')), patch.object(s1_clock, 'boot_id', side_effect=AssertionError('historical read sampled boot')):
            self.assertTrue(clock.match(clock.mapping()))
            self.assertEqual(clock.recorded(0, 'passed'),0)
            self.assertEqual(clock.recorded(90, 'failed'),90)
            with self.assertRaisesRegex(ValueError,'work deadline'): clock.recorded(67.5, 'passed')
            with self.assertRaisesRegex(ValueError,'total deadline'): clock.recorded(math.nextafter(90., math.inf),'failed')
            with self.assertRaisesRegex(ValueError,'authoritative'): clock.match(dict(clock.mapping(),boot_id='old-wrong'))

    def test_failure_reconciliation(self):
        import os
        from vipe_benchmark import s1_clock, s1_evidence
        fixture, request, reservation, clock = self.admitted(reduced=True)
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                kind=case['kind']; output=fixture.root/('failure-'+kind); output.mkdir()
                write_json(output/'config.json',request)
                observation = clock.monotonic_start + 3
                supplied = None if kind == 'unavailable' else clock
                if kind == 'late': observation = clock.total_deadline + 1
                if kind == 'nan': observation = float('nan')
                with patch.dict(os.environ,VIPE_RESERVATION_START='bogus'), patch.object(s1_clock.time,'monotonic',return_value=observation), patch.object(s1_clock,'boot_id',return_value=clock.boot_id):
                    if kind in ('unavailable','late','nan'):
                        primary=RuntimeError('original primary')
                        record=s1_evidence.preserve_failure(request,output,None,primary,clock=supplied)
                        self.assertEqual(read_json(record['path'])['error'],'original primary')
                        value=read_json(output/'first-result-qualification.json')
                        self.assertEqual(value['clock_status'],'unverified')
                        with self.assertRaises((ValueError,TypeError)):
                            s1_evidence.reconcile_first(request,output,clock=supplied,error='later error')
                        if kind=='late': self.assertEqual(value['elapsed_seconds_from_reservation'],91)
                        if kind=='unavailable': self.assertIsNone(value['elapsed_seconds_from_reservation'])
                        if kind=='nan': self.assertEqual(value['clock_observation'],'nan')
                    else:
                        if kind != 'missing':
                            raw=fixture.put(kind+'-raw.json',{'raw':'original'})
                            s1_evidence.first_record(request,output,kind,clock=clock,error='original',stage='adapter',raw=[raw])
                        before=(output/'first-result-qualification.json').read_bytes() if kind!='missing' else None
                        with patch.object(s1_clock.time,'monotonic',return_value=clock.monotonic_start+4):
                            record=s1_evidence.reconcile_first(request,output,clock=clock,error='cleanup')
                        value=read_json(record['path']); self.assertEqual(value['clock_status'],'verified')
                        self.assertEqual(value['elapsed_seconds_from_reservation'],4 if kind=='missing' else 3)
                        if before is not None: self.assertEqual(Path(record['path']).read_bytes(),before)
                        else: self.assertEqual(value['failure_stage'],'supervisor_cleanup')
        # Real helper derives the captured context, with no inherited start env.
        from vipe_benchmark.s1_cpu_helper import run
        output=fixture.root/'jobs'/s1.JOB; output.mkdir(); write_json(output/'config.json',request)
        with patch.dict(os.environ,{},clear=False):
            os.environ.pop('VIPE_RESERVATION_START',None)
            summary=run(dict(operation='reconcile',args=dict(local=str(fixture.root),config=fixture.config,
                reservation=reservation,outcome=dict(error='prelaunch failed'),deadline=clock.work_deadline)))
        self.assertEqual(summary['first_result']['status'],'verified')
        first=read_json(summary['first_result']['value']['path'])
        self.assertTrue(clock.match(first['reservation_clock']))
        self.assertGreaterEqual(first['elapsed_seconds_from_reservation'],0)

    def test_worker_bootstrap(self):
        import json, os
        import basketball_vipe_worker as worker
        from vipe_benchmark import s1_clock
        fixture, request, reservation, clock = self.admitted()
        command=reservation['command']; args=SimpleNamespace(operation='component',config=Path(command[5]),request=Path(command[7]),output=Path(command[9]))
        with patch.object(sys,'argv',command[1:]), patch.dict(os.environ,VIPE_S1_RESERVATION_CLOCK=json.dumps(clock.mapping())):
            self.assertEqual(s1.worker_clock(args,request,fixture.config),clock)
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                argv=command[1:].copy(); env={'VIPE_S1_RESERVATION_CLOCK':json.dumps(clock.mapping())}
                kind=case['kind']
                if kind=='operation': argv[2]='setup'
                elif kind=='output': argv[-1]=str(fixture.root/'wrong-output')
                elif kind=='request':
                    alternate=fixture.put('other/requests/'+s1.JOB+'.json',request); argv[6]=alternate['path']
                elif kind=='config': argv[4]=fixture.put('other-config.json',fixture.config)['path']
                elif kind=='script': argv[0]=str(fixture.root/'other-worker.py')
                elif kind=='missing': env['VIPE_S1_RESERVATION_CLOCK']='null'
                elif kind=='forged':
                    fake=copy.deepcopy(reservation); fake['monotonic_start']+=1
                    env['VIPE_S1_RESERVATION_CLOCK']=json.dumps(s1_clock.ReservationClock.from_reservation(fake).mapping())
                elif kind=='interpreter': pass
                elif kind=='duplicate': argv.extend(['--operation','component'])
                # Each invocation gets an unused failure destination. Canonical cases use
                # the real output, whose previous diagnostic files are removed between calls.
                output=Path(argv[argv.index('--output')+1])
                if output.exists():
                    import shutil; shutil.rmtree(output)
                seen=[]
                def premodel(req,out,cfg,*,clock):
                    seen.append(clock)
                    raise RuntimeError('deliberate pre-model failure')
                with patch.object(sys,'argv',argv), patch.dict(os.environ,env), patch('vipe_benchmark.stages.run',side_effect=premodel), patch.object(sys,'executable',str(fixture.root/'wrong-python') if kind=='interpreter' else sys.executable):
                    with self.assertRaises((ValueError,RuntimeError)) as caught:
                        worker.main()
                if kind=='valid':
                    self.assertEqual(str(caught.exception),'deliberate pre-model failure'); self.assertEqual(seen,[clock])
                    value=read_json(output/'first-result-qualification.json'); self.assertEqual(value['clock_status'],'verified')
                else:
                    self.assertEqual(seen,[])
                    value=read_json(output/'unavailable-input-failure-evidence.json'); self.assertEqual(value['clock_status'],'unverified')
                self.assertEqual(read_json(output/'failure.json')['status'],'failed')

    def test_real_segment_publication_barriers(self):
        import builtins
        from contextlib import ExitStack
        from vipe_benchmark import s1_clock, s1_evidence, stages
        from vipe_benchmark.access import RGBLoader
        from vipe_benchmark.backends import SegmentationResult
        fixture, request, reservation, clock = self.admitted(reduced=True)
        row, arrays = synthetic_row(fixture.root/'barrier-native',request)
        prediction=SegmentationResult(np.load(row['instances']['path']),row['semantics'],np.ones((540,960),bool),row['metadata'],diagnostics=arrays)
        real_load=RGBLoader.load; real_qualify=s1_evidence.qualify_row
        real_write=s1_evidence.write_json; real_read=s1_evidence.read_json
        real_verify=s1_evidence.verify_first; real_first=s1_evidence.first_record; real_print=builtins.print
        real_runtime=s1_evidence.qualify_runtime; real_record=s1_evidence.file_record
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                kind=case['kind']; output=fixture.root/('segment-'+kind)
                now=[clock.monotonic_start+1]; loads=[]; calls=[]; verified=[]; published=[]
                def load(loader, identity):
                    loads.append(identity.frame)
                    if identity.frame==62:
                        record=file_record(output/'first-result-qualification.json')
                        value=read_json(record['path']); real_verify(value,request,clock=clock)
                        self.assertEqual(record,published[0]); self.assertLess(now[0],clock.work_deadline)
                        raise RuntimeError('deliberate second input stop')
                    return real_load(loader,identity)
                def predict(*args,**kwargs): calls.append(1); return [prediction]
                def qualify(*args,**kwargs):
                    result=real_qualify(*args,**kwargs)
                    if kind=='qualification': now[0]=clock.work_deadline
                    return result
                def write(path,value):
                    result=real_write(path,value)
                    if Path(path).name=='first-result-qualification.json' and value['status']=='passed':
                        published.append(file_record(path))
                        if kind=='write': now[0]=clock.work_deadline
                    return result
                def read(path):
                    result=real_read(path)
                    if Path(path).name=='first-result-qualification.json' and kind=='readback': now[0]=clock.work_deadline
                    return result
                def qualify_runtime(*args,**kwargs):
                    result=real_runtime(*args,**kwargs)
                    if kind=='runtime': now[0]=clock.work_deadline
                    return result
                def record_file(path,*args,**kwargs):
                    result=real_record(path,*args,**kwargs)
                    if kind=='hash' and Path(path).name=='first-result-qualification.json': now[0]=clock.work_deadline
                    return result
                def verify(*args,**kwargs):
                    result=real_verify(*args,**kwargs); verified.append(now[0])
                    if (kind=='envelope_qualification' and len(verified)==1) or (kind=='reverify' and len(verified)==2) or (kind=='reuse' and len(verified)==3): now[0]=clock.work_deadline
                    return result
                def first(*args,**kwargs):
                    result=real_first(*args,**kwargs)
                    if kind in ('reuse','reuse_positive') and args[2]=='passed': result=real_first(*args,**kwargs)
                    return result
                def progress(*args,**kwargs):
                    result=real_print(*args,**kwargs)
                    if kind=='pre_input': now[0]=clock.work_deadline
                    return result
                cuda=SimpleNamespace(synchronize=lambda:None,max_memory_allocated=lambda:0,max_memory_reserved=lambda:0)
                with ExitStack() as stack:
                    for target, replacement in [('vipe_benchmark.s1_clock.time.monotonic',lambda:now[0]),
                        ('vipe_benchmark.s1_clock.boot_id',lambda:clock.boot_id),
                        ('vipe_benchmark.stages._model_runtime',lambda req:copy.deepcopy(fixture.observed)),
                        ('vipe_benchmark.backends.build_backend',lambda *a,**k:SimpleNamespace(segment=predict)),
                        ('vipe_benchmark.runtime_capture.loaded_runtime',lambda *a,**k:fixture.observed['loaded_files']),
                        ('vipe_benchmark.s1_evidence.qualify_row',qualify),('vipe_benchmark.s1_evidence.qualify_runtime',qualify_runtime),
                        ('vipe_benchmark.s1_evidence.file_record',record_file),('vipe_benchmark.s1_evidence.write_json',write),
                        ('vipe_benchmark.s1_evidence.read_json',read),('vipe_benchmark.s1_evidence.verify_first',verify),
                        ('vipe_benchmark.s1_evidence.first_record',first),('builtins.print',progress)]:
                        stack.enter_context(patch(target,side_effect=replacement))
                    stack.enter_context(patch.object(RGBLoader,'load',load))
                    stack.enter_context(patch.dict(sys.modules,{'torch':SimpleNamespace(cuda=cuda)}))
                    with self.assertRaisesRegex((TimeoutError,RuntimeError),'second input stop' if kind in ('positive','reuse_positive') else 'work deadline'):
                        stages.segment(request,output,fixture.config,clock=clock)
                self.assertEqual(calls,[1])
                self.assertEqual(loads.count(50),case['first_loads'])
                self.assertEqual(loads.count(62),1 if kind in ('positive','reuse_positive') else 0)
                self.assertEqual(set(loads),{50,62} if kind in ('positive','reuse_positive') else {50})
                import json
                real_print('S1_CLOCK_BARRIER '+json.dumps(dict(case=kind,loader_frames=loads,adapter_calls=len(calls),
                    qualification_observations=verified,completion_observation=now[0],work_deadline=clock.work_deadline,
                    first_publication=published[0] if published else None),sort_keys=True))
                self.assertFalse((output/'result.json').exists())
                produced=list(output.rglob('*-produced-row.json')); self.assertEqual(len(produced),1)
                self.assertEqual(s1_evidence.produced_row(read_json(produced[0]),request).frame,50)
                if published:
                    self.assertEqual(file_record(output/'first-result-qualification.json'),published[0])
                    value=read_json(published[0]['path']); self.assertEqual(value['status'],'passed')
                    self.assertTrue(real_verify(value,request,clock=clock))
                    self.assertEqual(file_record(value['raw_evidence'][0]['path']),value['raw_evidence'][0])
                    self.assertLess(value['elapsed_seconds_from_reservation'],clock.work_deadline-clock.monotonic_start)
                if kind=='positive': self.assertGreaterEqual(len(verified),2)

    def test_identical_reuse_and_conflicts(self):
        import os
        from vipe_benchmark import s1_evidence, s1_clock, stages
        fixture,request,reservation,clock=self.admitted(reduced=True)
        row,_=synthetic_row(fixture.root/'reuse-native',request)
        checks=s1_evidence.qualify_row(row,request,first=True)
        now=[clock.monotonic_start+1]
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case), patch.object(s1_clock.time,'monotonic',side_effect=lambda:now[0]), patch.object(s1_clock,'boot_id',return_value=clock.boot_id):
                now[0]=clock.monotonic_start+1
                kind=case['kind']; output=fixture.root/('reuse-'+kind); output.mkdir(); write_json(output/'config.json',request)
                kwargs=dict(clock=clock,rows=[row],runtime=fixture.observed,checks=checks,raw=[row['diagnostics']])
                if kind in ('failed','not_reached'):
                    original=s1_evidence.first_record(request,output,kind,clock=clock,error='original',stage='adapter')
                else:
                    original=s1_evidence.first_record(request,output,'passed',**kwargs)
                before=Path(original['path']).read_bytes()
                now[0]+=1
                if kind=='identical':
                    self.assertEqual(s1_evidence.first_record(request,output,'passed',**kwargs),original)
                    self.assertEqual(read_json(original['path'])['elapsed_seconds_from_reservation'],1)
                elif kind=='later_failure':
                    now[0]=clock.total_deadline+2
                    primary=RuntimeError('later original error')
                    raw=s1_evidence.preserve_failure(request,output,None,primary,clock=clock)
                    self.assertEqual(primary.s1_first_result,original)
                    self.assertEqual(read_json(raw['path'])['clock_status'],'unverified')
                elif kind=='conflict':
                    with self.assertRaisesRegex(ValueError,'conflicting'):
                        s1_evidence.first_record(request,output,'passed',**dict(kwargs,checks=[]))
                elif kind=='wrong_context':
                    fake=copy.deepcopy(reservation);fake['seconds']=91
                    with self.assertRaisesRegex(ValueError,'authoritative reservation'):
                        s1_evidence.first_record(request,output,'passed',**dict(kwargs,clock=s1_clock.ReservationClock.from_reservation(fake)))
                elif kind=='stale':
                    Path(original['path']).write_text('{}')
                    before=Path(original['path']).read_bytes()
                    with self.assertRaisesRegex(ValueError,'clock'):
                        s1_evidence.first_record(request,output,'passed',**kwargs)
                else:
                    with self.assertRaisesRegex(ValueError,'passed S1 first-result'):
                        s1_evidence.first_record(request,output,'passed',**kwargs)
                self.assertEqual(Path(original['path']).read_bytes(),before)
        with patch.dict(os.environ,VIPE_RESERVATION_START=str(clock.monotonic_start)), patch('vipe_benchmark.stages._model_runtime',side_effect=AssertionError('setup reached')):
            with self.assertRaisesRegex(ValueError,'trusted reservation clock required'):
                stages.segment(request,fixture.root/'missing-context',fixture.config)

    def test_acceptance_and_historical_authority(self):
        from vipe_benchmark import s1_clock, s1_evidence
        fixture=S1RecoveryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        active_mutations={}
        def active_checks(request,output,reservation):
            original=read_json(output/'result.json')
            for kind in ('start','boot','effective','sequence','hash'):
                fake=copy.deepcopy(reservation)
                if kind=='start': fake['monotonic_start']+=10
                elif kind=='boot': fake['boot_id']='wrong-historical-boot'
                elif kind=='effective': fake['seconds']=90
                elif kind=='sequence': fake['sequence']+=1
                else: fake['event_sha256']='0'*64
                value=copy.deepcopy(original); value['reservation_clock']=s1_clock.ReservationClock.from_reservation(fake).mapping()
                with self.assertRaisesRegex(ValueError,'authoritative reservation') as caught:
                    s1.accept_result(fixture.root,fixture.config,request,value,output,reservation=reservation)
                active_mutations[kind]=str(caught.exception)
            self.assertFalse((output/'acceptance.json').exists())
        fixture.before_worker_return=active_checks
        _,request,record=fixture.run_controller(); clock=fixture.clock
        events=fixture.ledger.events(); finish=fixture.ledger.states()[s1.JOB]
        result=read_json(record['path']); first=read_json(result['first_result']['path'])
        acceptance=read_json(finish['acceptance']['path']); terminal=read_json(finish['terminal_receipt']['path'])
        self.assertEqual(s1.resolved_result(fixture.root,fixture.config,events,finish),record)
        with patch.object(s1_clock,'boot_id',side_effect=AssertionError('historical boot sampled')), patch.object(s1_clock.time,'monotonic',side_effect=AssertionError('historical time sampled')):
            self.assertEqual(s1.resolved_result(fixture.root,fixture.config,events,finish),record)
        reservation=next(e for e in events if e.get('event')=='reserve' and e.get('job_id')==s1.JOB)
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                kind=case['kind']; self.assertIn('authoritative reservation',active_mutations[kind]); fake=copy.deepcopy(reservation)
                if kind=='start': fake['monotonic_start']+=10
                elif kind=='boot': fake['boot_id']='wrong-historical-boot'
                elif kind=='effective': fake['seconds']=90
                elif kind=='sequence': fake['sequence']+=1
                elif kind=='hash': fake['event_sha256']='0'*64
                mapping=s1_clock.ReservationClock.from_reservation(fake).mapping()
                directory=fixture.root/('clock-mutation-'+kind)
                changed_first=copy.deepcopy(first); changed_first['reservation_clock']=mapping
                write_json(directory/'first.json',changed_first)
                changed_result=copy.deepcopy(result); changed_result.update(first_result=file_record(directory/'first.json'),reservation_clock=mapping)
                with self.assertRaisesRegex(ValueError,'authoritative reservation'):
                    s1_evidence.validate_result(changed_result,request,fixture.config,clock=clock)
                write_json(directory/'result.json',changed_result)
                changed=copy.deepcopy(finish); changed['result']=file_record(directory/'result.json')
                accepted=copy.deepcopy(acceptance); accepted.update(result=changed['result'],first_result=changed_result['first_result'],reservation_clock=mapping,
                    records=s1.referenced_records([changed_result,request]))
                write_json(directory/'acceptance.json',accepted); changed['acceptance']=file_record(directory/'acceptance.json')
                receipt=copy.deepcopy(terminal); receipt['acceptance']=changed['acceptance']; receipt['outcome'].update(result=changed['result'],acceptance=changed['acceptance'])
                write_json(directory/'terminal.json',receipt); changed['terminal_receipt']=file_record(directory/'terminal.json')
                with self.assertRaisesRegex(ValueError,'authoritative reservation'):
                    s1.resolved_result(fixture.root,fixture.config,events,changed)


class NumericalEnvelopeTests(unittest.TestCase):
    def envelope(self):
        from vipe_benchmark.access import output_identities
        rows = [dict(native_group_wall_seconds=.125, group_size=1) for _ in output_identities(load(), 'calibration')]
        return dict(rows=rows, native_wall_seconds=sum(r['native_group_wall_seconds'] for r in rows),
                    peak_allocated_bytes=1024, peak_reserved_bytes=2048)

    def test_typed_numerical_fields(self):
        from vipe_benchmark.s1_evidence import validate_result_numerics
        from decimal import Decimal
        values = dict(null=None, string='1', boolean=True, nan=float('nan'), posinf=float('inf'),
            neginf=-float('inf'), negative=-1, fractional=.5, integral_float=1., zero=0,
            float_zero=0., one=1, nonzero=.125, two=2, huge=10**400,
            foreign=Decimal('1'), numpy=np.float64(1))
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                positive = self.envelope()
                self.assertTrue(validate_result_numerics(positive, load()))
                value = copy.deepcopy(positive)
                field, kind = case['field'], case['kind']
                target = value['rows'][1] if field in ('group_size', 'native_group_wall_seconds') else value
                if kind == 'missing': target.pop(field)
                else: target[field] = values[kind]
                if case['valid']:
                    if field == 'native_group_wall_seconds':
                        value['native_wall_seconds'] = sum(r['native_group_wall_seconds'] for r in value['rows'])
                    elif field == 'peak_reserved_bytes':
                        value['peak_allocated_bytes'] = 0
                    elif field == 'native_wall_seconds':
                        for row in value['rows']: row['native_group_wall_seconds'] = 0
                        value['rows'][1]['native_group_wall_seconds'] = target[field]
                    self.assertTrue(validate_result_numerics(value, load()))
                else:
                    with self.assertRaisesRegex(ValueError, field): validate_result_numerics(value, load())

    def test_sum_and_allocator_boundaries(self):
        import math
        from vipe_benchmark.s1_evidence import validate_result_numerics
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                positive = self.envelope(); config = load()
                self.assertTrue(validate_result_numerics(positive, config))
                value = copy.deepcopy(positive); kind = case['kind']
                reference = math.fsum(r['native_group_wall_seconds'] for r in value['rows'])
                ulp = math.nextafter(reference, math.inf) - reference
                boundary = len(value['rows']) + 1
                if kind.startswith(('inside_', 'on_', 'outside_')):
                    distance = {'inside': boundary-1, 'on': boundary, 'outside': boundary+1}[kind.split('_')[0]]
                    value['native_wall_seconds'] = reference + (1 if kind.endswith('plus') else -1)*distance*ulp
                elif kind in ('all_zero', 'zero_mismatch'):
                    for row in value['rows']: row['native_group_wall_seconds'] = 0.
                    value['native_wall_seconds'] = 0 if kind == 'all_zero' else math.ulp(0.)
                elif kind == 'sequential':
                    for row in value['rows']: row['native_group_wall_seconds'] = .1
                    value['native_wall_seconds'] = sum(r['native_group_wall_seconds'] for r in value['rows'])
                elif kind == 'overflow':
                    for row in value['rows']: row['native_group_wall_seconds'] = 1e308
                elif kind == 'changed_row': value['rows'][1]['native_group_wall_seconds'] *= 2
                elif kind == 'wrong_total': value['native_wall_seconds'] *= 2
                elif kind == 'allocated_gt_reserved': value['peak_allocated_bytes'] = value['peak_reserved_bytes']+1
                elif kind in ('cap', 'reserved_over_cap', 'both_over_cap', 'smaller_cap', 'smaller_cap_excess'):
                    if kind.startswith('smaller'): config = dict(config, gpu_peak_device_gib_limit=1/2**20)
                    cap = int(config['gpu_peak_device_gib_limit']*2**30)
                    value['peak_allocated_bytes'] = cap if kind in ('cap','smaller_cap') else 0
                    value['peak_reserved_bytes'] = cap + int(kind not in ('cap','smaller_cap'))
                    if kind == 'both_over_cap': value['peak_allocated_bytes'] = cap+1
                elif kind == 'empty_rows': value['rows'] = []
                elif kind == 'tuple_rows': value['rows'] = tuple(value['rows'])
                elif kind == 'nonmapping_row': value['rows'][1] = None
                if case['valid']: self.assertTrue(validate_result_numerics(value, config))
                else:
                    with self.assertRaisesRegex(ValueError, case['error']): validate_result_numerics(value, config)

    def test_produced_and_qualified_numerical_rows(self):
        from vipe_benchmark.s1_evidence import produced_row, qualify_row, reconcile_rows
        fixture = S1RecoveryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        request = fixture.original
        row, _ = synthetic_row(fixture.root/'numeric', request)
        self.assertTrue(qualify_row(row, request, first=True))
        self.assertEqual(produced_row(row, request).record(), row['identity'])
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                self.assertTrue(qualify_row(row, request, first=True))
                mutated = copy.deepcopy(row); mutated[case['field']] = case['value']
                directory = fixture.root / case['field']; directory.mkdir()
                path = directory/'numeric-produced-row.json'; write_json(path, mutated)
                serialized = read_json(path)
                self.assertEqual(produced_row(serialized, request).record(), row['identity'])
                with self.assertRaisesRegex(ValueError, case['field']): qualify_row(serialized, request, first=True)
                evidence = reconcile_rows(directory, request)
                self.assertEqual(evidence['produced_identities'], [row['identity']])
                self.assertEqual(evidence['qualified_identities'], [])
                self.assertEqual(evidence['counts']['produced_lower_bound'], 1)
                self.assertEqual(evidence['counts']['qualified'], 0)
                self.assertTrue(any(case['field'] in error['error'] for error in evidence['verification_errors']))

    def test_terminal_and_resolver_numerical_mutations(self):
        from vipe_benchmark.s1_evidence import validate_result
        fixture = S1RecoveryTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        _, request, record = fixture.run_controller()
        finish = fixture.ledger.states()[s1.JOB]; events = fixture.ledger.events()
        positive = read_json(record['path'])
        self.assertTrue(validate_result(positive, request, fixture.config, clock=fixture.clock))
        self.assertEqual(s1.resolved_result(fixture.root, fixture.config, events, finish), record)
        acceptance = read_json(finish['acceptance']['path'])
        terminal = read_json(finish['terminal_receipt']['path'])
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                # Keep the original event-bound files immutable. Each mutation has
                # its own coherent enclosing graph and the same real fixture events.
                self.assertEqual(s1.resolved_result(fixture.root, fixture.config, events, finish), record)
                value = copy.deepcopy(positive); field = case['field']
                if field == 'native_group_wall_seconds': value['rows'][1][field] = -1
                elif field == 'native_wall_seconds': value[field] += 1
                else: value[field] = True
                with self.assertRaisesRegex(ValueError, field): validate_result(value, request, fixture.config, clock=fixture.clock)
                directory = fixture.root/'mutations'/field
                paths = [directory/name for name in ('result.json','acceptance.json','receipt.json')]
                write_json(paths[0], value); changed = dict(finish, result=file_record(paths[0]))
                accepted = copy.deepcopy(acceptance)
                accepted.update(result=changed['result'], records=s1.referenced_records([value,request]))
                write_json(paths[1], accepted); changed['acceptance'] = file_record(paths[1])
                receipt = copy.deepcopy(terminal)
                receipt['acceptance'] = changed['acceptance']; receipt['outcome']['result'] = changed['result']
                receipt['outcome']['acceptance'] = changed['acceptance']
                write_json(paths[2], receipt); changed['terminal_receipt'] = file_record(paths[2])
                with self.assertRaisesRegex(ValueError, field): s1.resolved_result(fixture.root, fixture.config, events, changed)
        self.assertEqual(s1.resolved_result(fixture.root, fixture.config, events, finish), record)

    def test_direct_script_declaration_lookup(self):
        import json, os, signal, subprocess, time
        from vipe_benchmark.s1_validation_contract import parse_suite, ENVIRONMENT
        for case in SUBTEST_CASES[f"{Path(__file__).stem}.{type(self).__name__}.{self._testMethodName}"]:
            with self.subTest(**case):
                module = 'test_vipe_benchmark_' + case['suite']
                path = ROOT/'tests'/(module+'.py')
                methods, declarations = parse_suite(path.read_text(), module)
                identity = module+'.'+case['selector']
                self.assertIn(identity, methods); self.assertTrue(declarations[identity])
                argv = [sys.executable, '-B', str(path), case['selector'], '-v']
                env = os.environ.copy()
                for key, value in ENVIRONMENT.items():
                    if value is None: env.pop(key, None)
                    else: env[key] = value
                env.pop('S1_VALIDATION_RUN_DIRECTORY', None)
                start = time.monotonic(); timed_out = False; process = None
                stdout = stderr = ''; returncode = None
                try:
                    process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, start_new_session=True)
                    try: stdout, stderr = process.communicate(timeout=10)
                    except subprocess.TimeoutExpired:
                        timed_out = True; os.killpg(process.pid, signal.SIGKILL)
                        stdout, stderr = process.communicate(timeout=2)
                    returncode = process.returncode
                finally:
                    if process is not None and process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=2)
                    print('S1_SCRIPT_CHILD '+json.dumps(dict(argv=argv, cwd=str(ROOT),
                        start_monotonic=start, end_monotonic=time.monotonic(),
                        returncode=returncode, timed_out=timed_out, stdout=stdout, stderr=stderr), sort_keys=True), flush=True)
                self.assertFalse(timed_out); self.assertEqual(returncode, 0, stdout+stderr)
                self.assertIn('Ran 1 test', stderr); self.assertIn('\nOK\n', stderr)
                class_name, method = case['selector'].split('.')
                self.assertIn(method+' (__main__.'+class_name+'.'+method+') ... ok', stderr)

# Literal ordered callback contract consumed without importing this module.
SUBTEST_CASES = {
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_identical_reuse_and_conflicts': [{'kind': 'identical'}, {'kind': 'later_failure'}, {'kind': 'conflict'}, {'kind': 'wrong_context'}, {'kind': 'stale'}, {'kind': 'failed'}, {'kind': 'not_reached'}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_context_matrix': [{'field': 'monotonic_start', 'kind': 'missing'}, {'field': 'monotonic_start', 'kind': 'null'}, {'field': 'monotonic_start', 'kind': 'bool'}, {'field': 'monotonic_start', 'kind': 'string'}, {'field': 'monotonic_start', 'kind': 'nan'}, {'field': 'monotonic_start', 'kind': 'infinity'}, {'field': 'monotonic_start', 'kind': 'negative'}, {'field': 'monotonic_start', 'kind': 'changed'}, {'field': 'effective_seconds', 'kind': 'missing'}, {'field': 'effective_seconds', 'kind': 'null'}, {'field': 'effective_seconds', 'kind': 'bool'}, {'field': 'effective_seconds', 'kind': 'string'}, {'field': 'effective_seconds', 'kind': 'nan'}, {'field': 'effective_seconds', 'kind': 'infinity'}, {'field': 'effective_seconds', 'kind': 'negative'}, {'field': 'effective_seconds', 'kind': 'changed'}, {'field': 'cleanup_reserve_seconds', 'kind': 'missing'}, {'field': 'cleanup_reserve_seconds', 'kind': 'null'}, {'field': 'cleanup_reserve_seconds', 'kind': 'bool'}, {'field': 'cleanup_reserve_seconds', 'kind': 'string'}, {'field': 'cleanup_reserve_seconds', 'kind': 'nan'}, {'field': 'cleanup_reserve_seconds', 'kind': 'infinity'}, {'field': 'cleanup_reserve_seconds', 'kind': 'negative'}, {'field': 'cleanup_reserve_seconds', 'kind': 'changed'}, {'field': 'total_deadline', 'kind': 'missing'}, {'field': 'total_deadline', 'kind': 'null'}, {'field': 'total_deadline', 'kind': 'bool'}, {'field': 'total_deadline', 'kind': 'string'}, {'field': 'total_deadline', 'kind': 'nan'}, {'field': 'total_deadline', 'kind': 'infinity'}, {'field': 'total_deadline', 'kind': 'negative'}, {'field': 'total_deadline', 'kind': 'changed'}, {'field': 'work_deadline', 'kind': 'missing'}, {'field': 'work_deadline', 'kind': 'null'}, {'field': 'work_deadline', 'kind': 'bool'}, {'field': 'work_deadline', 'kind': 'string'}, {'field': 'work_deadline', 'kind': 'nan'}, {'field': 'work_deadline', 'kind': 'infinity'}, {'field': 'work_deadline', 'kind': 'negative'}, {'field': 'work_deadline', 'kind': 'changed'}, {'field': 'effective_seconds', 'kind': 'zero'}, {'field': 'effective_seconds', 'kind': 'oversized'}, {'field': 'monotonic_start', 'kind': 'overflow'}, {'field': 'effective_seconds', 'kind': 'underflow'}, {'field': 'job_id', 'kind': 'changed'}, {'field': 'request', 'kind': 'changed'}, {'field': 'reservation', 'kind': 'changed'}, {'field': 'boot_id', 'kind': 'empty'}, {'field': 'reservation', 'kind': 'hash'}, {'field': 'request', 'kind': 'request_hash'}, {'field': 'monotonic_start', 'kind': 'forged'}, {'field': 'effective_seconds', 'kind': 'forged'}, {'field': 'boot_id', 'kind': 'forged'}, {'field': 'reservation', 'kind': 'forged'}, {'field': 'reservation', 'kind': 'missing'}, {'field': 'reservation', 'kind': 'null'}, {'field': 'reservation', 'kind': 'bool'}, {'field': 'reservation', 'kind': 'string'}, {'field': 'request', 'kind': 'missing'}, {'field': 'request', 'kind': 'null'}, {'field': 'request', 'kind': 'bool'}, {'field': 'request', 'kind': 'string'}, {'field': 'boot_id', 'kind': 'missing'}, {'field': 'boot_id', 'kind': 'null'}, {'field': 'boot_id', 'kind': 'bool'}, {'field': 'boot_id', 'kind': 'string'}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_phase_boundaries': [{'kind': 'zero', 'work': True, 'valid': True}, {'kind': 'before_work', 'work': True, 'valid': True}, {'kind': 'at_work', 'work': True, 'valid': False}, {'kind': 'after_work', 'work': True, 'valid': False}, {'kind': 'at_total', 'work': False, 'valid': True}, {'kind': 'after_total', 'work': False, 'valid': False}, {'kind': 'negative', 'work': True, 'valid': False}, {'kind': 'nan', 'work': True, 'valid': False}, {'kind': 'infinity', 'work': True, 'valid': False}, {'kind': 'before_start', 'work': True, 'valid': False}, {'kind': 'wrong_boot', 'work': True, 'valid': False}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_failure_reconciliation': [{'kind': 'missing'}, {'kind': 'failed'}, {'kind': 'not_reached'}, {'kind': 'unavailable'}, {'kind': 'late'}, {'kind': 'nan'}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_worker_bootstrap': [{'kind': 'valid'}, {'kind': 'missing'}, {'kind': 'forged'}, {'kind': 'operation'}, {'kind': 'output'}, {'kind': 'request'}, {'kind': 'config'}, {'kind': 'script'}, {'kind': 'interpreter'}, {'kind': 'duplicate'}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_real_segment_publication_barriers': [{'kind': 'positive', 'first_loads': 6}, {'kind': 'reuse_positive', 'first_loads': 8}, {'kind': 'qualification', 'first_loads': 2}, {'kind': 'runtime', 'first_loads': 2}, {'kind': 'envelope_qualification', 'first_loads': 3}, {'kind': 'hash', 'first_loads': 5}, {'kind': 'write', 'first_loads': 5}, {'kind': 'readback', 'first_loads': 5}, {'kind': 'reverify', 'first_loads': 5}, {'kind': 'reuse', 'first_loads': 7}, {'kind': 'pre_input', 'first_loads': 5}],
'test_vipe_benchmark_s1_recovery.ReservationClockTests.test_acceptance_and_historical_authority': [{'kind': 'start'}, {'kind': 'boot'}, {'kind': 'effective'}, {'kind': 'sequence'}, {'kind': 'hash'}],

'test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_typed_numerical_fields': [{'field': 'native_group_wall_seconds',
                                                                                         'kind': 'missing',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'null',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'string',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'boolean',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'nan',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'posinf',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'neginf',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'negative',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'huge',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'foreign',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'numpy',
                                                                                         'valid': False},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'zero',
                                                                                         'valid': True},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'float_zero',
                                                                                         'valid': True},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'one',
                                                                                         'valid': True},
                                                                                        {'field': 'native_group_wall_seconds',
                                                                                         'kind': 'nonzero',
                                                                                         'valid': True},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'missing',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'null',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'string',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'boolean',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'nan',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'posinf',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'neginf',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'negative',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'huge',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'foreign',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'numpy',
                                                                                         'valid': False},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'zero',
                                                                                         'valid': True},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'float_zero',
                                                                                         'valid': True},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'one',
                                                                                         'valid': True},
                                                                                        {'field': 'native_wall_seconds',
                                                                                         'kind': 'nonzero',
                                                                                         'valid': True},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'missing',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'null',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'string',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'boolean',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'fractional',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'integral_float',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'zero',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'negative',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'two',
                                                                                         'valid': False},
                                                                                        {'field': 'group_size',
                                                                                         'kind': 'one',
                                                                                         'valid': True},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'missing',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'null',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'string',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'boolean',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'nan',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'posinf',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'neginf',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'negative',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'fractional',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'integral_float',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'zero',
                                                                                         'valid': True},
                                                                                        {'field': 'peak_allocated_bytes',
                                                                                         'kind': 'one',
                                                                                         'valid': True},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'missing',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'null',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'string',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'boolean',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'nan',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'posinf',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'neginf',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'negative',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'fractional',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'integral_float',
                                                                                         'valid': False},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'zero',
                                                                                         'valid': True},
                                                                                        {'field': 'peak_reserved_bytes',
                                                                                         'kind': 'one',
                                                                                         'valid': True}],
 'test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_sum_and_allocator_boundaries': [{'kind': 'inside_plus',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'inside_minus',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'on_plus',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'on_minus',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'outside_plus',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'outside_minus',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'all_zero',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'zero_mismatch',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'sequential',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'overflow',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'changed_row',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'wrong_total',
                                                                                               'valid': False,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'allocated_gt_reserved',
                                                                                               'valid': False,
                                                                                               'error': 'peak_'},
                                                                                              {'kind': 'cap',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'reserved_over_cap',
                                                                                               'valid': False,
                                                                                               'error': 'peak_'},
                                                                                              {'kind': 'both_over_cap',
                                                                                               'valid': False,
                                                                                               'error': 'peak_'},
                                                                                              {'kind': 'smaller_cap',
                                                                                               'valid': True,
                                                                                               'error': 'native_wall_seconds'},
                                                                                              {'kind': 'smaller_cap_excess',
                                                                                               'valid': False,
                                                                                               'error': 'peak_'},
                                                                                              {'kind': 'empty_rows',
                                                                                               'valid': False,
                                                                                               'error': 'numerical '
                                                                                                        'rows'},
                                                                                              {'kind': 'tuple_rows',
                                                                                               'valid': False,
                                                                                               'error': 'numerical '
                                                                                                        'rows'},
                                                                                              {'kind': 'nonmapping_row',
                                                                                               'valid': False,
                                                                                               'error': 'numerical '
                                                                                                        'rows'}],
 'test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_produced_and_qualified_numerical_rows': [{'field': 'native_group_wall_seconds',
                                                                                                        'value': -1},
                                                                                                       {'field': 'group_size',
                                                                                                        'value': 2}],
 'test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_terminal_and_resolver_numerical_mutations': [{'field': 'native_wall_seconds'},
                                                                                                           {'field': 'peak_allocated_bytes'},
                                                                                                           {'field': 'peak_reserved_bytes'},
                                                                                                           {'field': 'native_group_wall_seconds'}],
 'test_vipe_benchmark_s1_recovery.NumericalEnvelopeTests.test_direct_script_declaration_lookup': [{'suite': 's1_semantics',
                                                                                                   'selector': 'S1SemanticsTests.test_contract_rejects_missing_or_tampered_assignment'},
                                                                                                  {'suite': 's1_recovery',
                                                                                                   'selector': 'ReceiptContractTests.test_typed_primitive_callbacks'},
                                                                                                  {'suite': 'backends',
                                                                                                   'selector': 'AssetAndDetectorTests.test_phrase_ambiguity_and_capacity_fail_before_casting'},
                                                                                                  {'suite': 'contracts',
                                                                                                   'selector': 'AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected'},
                                                                                                  {'suite': 'component_recovery',
                                                                                                   'selector': 'ComponentRecoveryTests.test_scope_validation_and_cumulative_cap_are_not_relaxed'},
                                                                                                  {'suite': 'supervisor',
                                                                                                   'selector': 'HelperIntegrationTests.test_cleanup_failures'}],

    'test_vipe_benchmark_s1_recovery.S1RecoveryTests.test_typed_scope_schema_branch_and_second_identity': [
        {'key': 'schema', 'value': 'old'},
        {'key': 'job_id', 'value': 'S1-calibration-recovery-002'},
        {'key': 'original_job_id', 'value': 'S1-reconstruction'},
        {'key': 'attempts_limit', 'value': True},
        {'key': 'seconds_limit', 'value': 3600.0},
        {'key': 'changes_to_prescribed_configuration', 'value': False},
        {'key': 'additional_attempt_approved', 'value': 1},
        {'key': 'reconstruction_authorized', 'value': True},
        {'key': 'branch', 'value': 'reconstruction'},
    ],
    'test_vipe_benchmark_s1_recovery.S1RecoveryTests.test_validation_missing_extra_duplicate_aliased_stale_and_failed_receipts': [
        {'label': 'missing'},
        {'label': 'extra'},
        {'label': 'duplicate'},
        {'label': 'old'},
        {'label': 'no_tests'},
        {'label': 'failed'},
        {'label': 'skipped'},
        {'label': 'alias'},
        {'label': 'bytes'},
    ],
    'test_vipe_benchmark_s1_recovery.S1RecoveryTests.test_changed_prerequisite_records_rejected': [
        {'key': 'original_failure'},
        {'key': 'e1_qualification'},
        {'key': 'e1_assets'},
        {'key': 'inputs'},
        {'key': 'annotations'},
        {'key': 'annotation_policy'},
        {'key': 'annotation_review'},
        {'key': 'historical_request'},
        {'key': 'configuration'},
    ],
    'test_vipe_benchmark_s1_recovery.S1RecoveryTests.test_result_requires_supervised_cleanup_and_exact_membership': [
        {'field': 'cleanup_confirmed'},
        {'field': 'surviving_pids'},
        {'field': 'deadline_exceeded'},
        {'field': 'acceptance'},
    ],
    'test_vipe_benchmark_s1_recovery.FailureEvidenceTests.test_alignment_layout_pre_forward_and_no_stale_capture': [
        {'failure': 'alignment'},
        {'failure': 'layout'},
        {'failure': 'before'},
    ],
    'test_vipe_benchmark_s1_recovery.FailureEvidenceTests.test_first_result_failure_stops_before_second_input': [
        {'kind': 'contract'},
        {'kind': 'serialization'},
        {'kind': 'qualification'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_typed_primitive_callbacks': [
        {'value': False},
        {'value': True},
        {'value': 0},
        {'value': 1},
        {'value': 1.0},
        {'value': None},
        {'value': 'None'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_declaration_parser_mutations': [
        {'mutation': 'missing', 'error': 'exactly one'},
        {'mutation': 'dynamic', 'error': 'literal declaration'},
        {'mutation': 'duplicate_assignment', 'error': 'exactly one'},
        {'mutation': 'duplicate_method', 'error': 'duplicate declaration key'},
        {'mutation': 'duplicate_field', 'error': 'duplicate declaration key'},
        {'mutation': 'extraneous', 'error': 'missing or extraneous'},
        {'mutation': 'ordinary', 'error': 'missing or extraneous'},
        {'mutation': 'duplicate_tuple', 'error': 'duplicate declared'},
        {'mutation': 'nonprimitive', 'error': 'primitive parameter'},
        {'mutation': 'nonfinite', 'error': 'finite parameter'},
        {'mutation': 'unpacking', 'error': 'unpacking'},
        {'mutation': 'empty', 'error': 'nonempty declaration'},
        {'mutation': 'indirect', 'error': 'indirect'},
        {'mutation': 'getattr', 'error': 'indirect parameterization'},
        {'mutation': 'mutation', 'error': 'dynamic declaration'},
        {'mutation': 'subscript', 'error': 'dynamic declaration'},
        {'mutation': 'augmented', 'error': 'dynamic declaration'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_callback_mutations': [
        {'mutation': 'missing', 'error': 'callback multiplicity'},
        {'mutation': 'substituted', 'error': 'typed callback parameters'},
        {'mutation': 'reordered', 'error': 'typed callback parameters'},
        {'mutation': 'duplicated', 'error': 'typed callback parameters'},
        {'mutation': 'removed_field', 'error': 'typed callback parameters'},
        {'mutation': 'extra_field', 'error': 'typed callback parameters'},
        {'mutation': 'bool_int', 'error': 'typed callback parameters'},
        {'mutation': 'int_float', 'error': 'typed callback parameters'},
        {'mutation': 'null_string', 'error': 'typed callback parameters'},
        {'mutation': 'id', 'error': 'canonical callback ID'},
        {'mutation': 'extra_ordinary', 'error': 'callback multiplicity'},
        {'mutation': 'failed', 'error': 'passing callback'},
        {'mutation': 'error', 'error': 'passing callback'},
        {'mutation': 'skipped', 'error': 'passing callback'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_accounting_mutations': [
        {'mutation': 'missing_method', 'error': 'ordered method collection'},
        {'mutation': 'extra_method', 'error': 'ordered method collection'},
        {'mutation': 'reordered_method', 'error': 'ordered method collection'},
        {'mutation': 'duplicate_method', 'error': 'ordered method collection'},
        {'mutation': 'missing_suite', 'error': 'exact suite collection'},
        {'mutation': 'extra_suite', 'error': 'exact suite collection'},
        {'mutation': 'reordered_suite', 'error': 'exact suite collection'},
        {'mutation': 'duplicate_suite', 'error': 'exact suite collection'},
        {'mutation': 'discovery', 'error': 'exact suite collection'},
        {'mutation': 'count', 'error': 'exact integer receipt accounting'},
        {'mutation': 'bool_count', 'error': 'exact integer receipt accounting'},
        {'mutation': 'float_count', 'error': 'exact integer receipt accounting'},
        {'mutation': 'suite_count', 'error': 'exact integer receipt accounting'},
        {'mutation': 'suite_bool', 'error': 'exact integer receipt accounting'},
        {'mutation': 'suite_float', 'error': 'exact integer receipt accounting'},
        {'mutation': 'diff_bool', 'error': 'exact clean diff'},
        {'mutation': 'diff_float', 'error': 'exact clean diff'},
        {'mutation': 'schema', 'error': 'complete v2 aggregate'},
        {'mutation': 'expected_bool', 'error': 'passing aggregate'},
        {'mutation': 'expected_float', 'error': 'passing aggregate'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_binding_mutations': [
        {'mutation': 'stdin', 'error': 'stale file record'},
        {'mutation': 'runner', 'error': 'stale file record'},
        {'mutation': 'stdout', 'error': 'stale file record'},
        {'mutation': 'stderr', 'error': 'stale file record'},
        {'mutation': 'missing_log', 'error': 'canonical existing file'},
        {'mutation': 'alias', 'error': 'canonical existing file'},
        {'mutation': 'interpreter', 'error': 'interpreter file mismatch'},
        {'mutation': 'stale_source', 'error': 'exact current ordered sources'},
        {'mutation': 'source_bytes', 'error': 'exact current ordered sources'},
        {'mutation': 'source_bool', 'error': 'exact current ordered sources'},
        {'mutation': 'duplicate_source', 'error': 'exact current ordered sources'},
        {'mutation': 'missing_source', 'error': 'exact current ordered sources'},
        {'mutation': 'extra_source', 'error': 'exact current ordered sources'},
        {'mutation': 'unequal_sources', 'error': 'exact current ordered sources'},
        {'mutation': 'outer_source', 'error': 'exact current ordered sources'},
        {'mutation': 'cross_run', 'error': 'execution run directory mismatch'},
        {'mutation': 'capture', 'error': 'stale file record'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations': [
        {'mutation': 'argv', 'error': 'exact launcher argv'},
        {'mutation': 'flag', 'error': 'exact launcher argv'},
        {'mutation': 'python_argv', 'error': 'exact launcher argv'},
        {'mutation': 'runpy_argv', 'error': 'exact launcher argv'},
        {'mutation': 'interpreter', 'error': 'exact interpreter'},
        {'mutation': 'cwd', 'error': 'cwd/run directory'},
        {'mutation': 'env', 'error': 'exact validation environment'},
        {'mutation': 'diagnostic', 'error': 'exact validation environment'},
        {'mutation': 'utc', 'error': 'UTC timestamp'},
        {'mutation': 'naive', 'error': 'UTC timezone'},
        {'mutation': 'nonfinite', 'error': 'finite nonnegative'},
        {'mutation': 'negative', 'error': 'finite nonnegative'},
        {'mutation': 'reversed', 'error': 'inconsistent timing'},
        {'mutation': 'inconsistent', 'error': 'inconsistent timing'},
        {'mutation': 'boolean_time', 'error': 'finite nonnegative'},
        {'mutation': 'suite_overlap', 'error': 'suite intervals overlap'},
        {'mutation': 'envelope', 'error': 'outside enclosing'},
        {'mutation': 'boot', 'error': 'execution boot'},
        {'mutation': 'wait', 'error': 'actual successful wait'},
        {'mutation': 'returncode', 'error': 'actual successful wait'},
        {'mutation': 'bool_returncode', 'error': 'actual successful wait'},
        {'mutation': 'float_returncode', 'error': 'actual successful wait'},
        {'mutation': 'timeout', 'error': 'actual successful wait'},
        {'mutation': 'outer_argv', 'error': 'exact outer argv'},
        {'mutation': 'outer_env', 'error': 'exact validation environment'},
        {'mutation': 'logs', 'error': 'process/runner log'},
        {'mutation': 'cap', 'error': 'invocation cap'},
        {'mutation': 'stdin_rehashed', 'error': 'prescribed stdin'},
        {'mutation': 'runner_rehashed', 'error': 'current runner snapshot'},
    ],
    'test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_artifact_record_matrix': [
        {'kind': 'stdin', 'mutation': 'missing', 'error': 'canonical existing file'},
        {'kind': 'stdin', 'mutation': 'stale', 'error': 'stale file record'},
        {'kind': 'stdin', 'mutation': 'alias', 'error': 'canonical existing file'},
        {'kind': 'runner', 'mutation': 'missing', 'error': 'canonical existing file'},
        {'kind': 'runner', 'mutation': 'stale', 'error': 'stale file record'},
        {'kind': 'runner', 'mutation': 'alias', 'error': 'canonical existing file'},
        {'kind': 'stdout', 'mutation': 'missing', 'error': 'canonical existing file'},
        {'kind': 'stdout', 'mutation': 'stale', 'error': 'stale file record'},
        {'kind': 'stdout', 'mutation': 'alias', 'error': 'canonical existing file'},
        {'kind': 'stderr', 'mutation': 'missing', 'error': 'canonical existing file'},
        {'kind': 'stderr', 'mutation': 'stale', 'error': 'stale file record'},
        {'kind': 'stderr', 'mutation': 'alias', 'error': 'canonical existing file'},
        {'kind': 'interpreter', 'mutation': 'missing', 'error': 'canonical existing file'},
        {'kind': 'interpreter', 'mutation': 'stale', 'error': 'stale file record'},
        {'kind': 'interpreter', 'mutation': 'alias', 'error': 'canonical existing file'},
        {'kind': 'source', 'mutation': 'missing', 'error': 'exact current ordered sources'},
        {'kind': 'source', 'mutation': 'stale', 'error': 'exact current ordered sources'},
        {'kind': 'source', 'mutation': 'alias', 'error': 'exact current ordered sources'},
    ],
}


if __name__=='__main__': unittest.main()
