"""Full-rig geometry computation through injected, explicitly fixture backends.

No model loader, Torch import, dispatch, ledger write or actual execution authority.
Native use needs a separately qualified and supervised execution adapter.
"""
import math
import ast
import json
import time
from io import BytesIO
from pathlib import Path

import numpy as np

from .contracts import SHAPE, instances
from .diagnostics import evaluate_edge
from .extended_final_render_contract import parse_request
from .files import file_record, object_hash, read_json, safe_path, verify_record, write_json
from .final_render_contract import KEYFRAMES, TRAINING_CAMERAS, PHASES
from .final_render_initializer import validate_scene
from .geometry import consumer_camera


class GeometryFailure(ValueError):
    """Computation failure with an immutable, rehashable partial-output receipt."""
    def __init__(self,message,receipt,result):
        super().__init__(message)
        self.receipt = receipt
        self.result = result


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(verify_record(record) == record, 'changed geometry input record')
    return read_json(record['path'])


def _index(rows, pair=False):
    result = {}
    for row in rows:
        identity = row['identity']
        if identity['branch'] != 'reconstruction':
            continue
        key = (identity['camera'],identity['frame'],identity['pair_start']) if pair else (identity['camera'],identity['frame'])
        _require(key not in result, 'duplicate reconstruction source identity')
        result[key] = row
    return result


def _fixture_measurement(value):
    _require(isinstance(value,dict) and set(value) == {'wall_seconds','cuda_seconds'} and
        all(type(value[k]) in (int,float) and math.isfinite(value[k]) and value[k] >= 0 for k in value),
        'finite nonnegative fixture measurement required')
    _require(value['cuda_seconds'] == 0, 'fixture backend cannot claim CUDA execution')


def _matching_helpers():
    # Preserve the audited pure functions without executing the historical
    # module's Torch/model imports. Pin their complete source files in receipts.
    import cv2
    root = Path(__file__).resolve().parents[1]
    source = root/'basketball_temporal_cloud.py'
    tree = ast.parse(safe_path(source).read_text(),filename=str(source))
    selected = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('balanced_samples','query_warp')]
    _require(len(selected) == 2 and {node.name for node in selected} == {'balanced_samples','query_warp'} and
        all(not node.decorator_list for node in selected), 'audited matching helpers missing/ambiguous')
    namespace = {'np':np,'cv2':cv2}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(source),'exec'),namespace)
    pin_source = root/'edgs_source.py'
    pin_tree = ast.parse(safe_path(pin_source).read_text(),filename=str(pin_source))
    pins = {}
    for node in pin_tree.body:
        if isinstance(node,ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0],ast.Name):
            name = node.targets[0].id
            if name in ('ROMA_PIN','ROMA_WEIGHTS'):
                _require(name not in pins, 'duplicate historical RoMa pin')
                pins[name] = ast.literal_eval(node.value)
    _require(set(pins) == {'ROMA_PIN','ROMA_WEIGHTS'}, 'historical RoMa pins missing')
    return namespace['balanced_samples'],namespace['query_warp'],pins['ROMA_PIN'],pins['ROMA_WEIGHTS']


def run(request, arm, output, backend, observation_loader=None, *, tracker=None, clock=time.monotonic):
    """Compute 810 fixture edges, publish immutable NPZs and a bound result.

    Backend supplies match/crop/triangulate, sample_thresh and record_kind=fixture.
    observation_loader(source, S2_row, M_row) returns rgb/valid/labels/changing
    arrays; semantic classes come from the exact S2 row. The default loader
    verifies frozen file bytes and native array contracts without preprocessing.
    The default temporal tracker is unchanged OpenCV LK; CPU fixtures may
    inject known endpoints.
    """
    _require(request.get('record_kind') == 'fixture', 'actual geometry requires supervised native qualification')
    _require(getattr(backend,'record_kind',None) == 'fixture', 'explicit fixture backend required')
    verified_loader = observation_loader is None
    if verified_loader:
        from .final_render_loaders import load_observation
        observation_loader = load_observation
    request = parse_request(request)
    _require(arm in request['compositions'], 'unknown final-render arm')
    balanced_samples,query_warp,ROMA_PIN,ROMA_WEIGHTS = _matching_helpers()
    from basketball_temporal_geometry import projection, track_lk, velocity_from_support
    tracker = track_lk if tracker is None else tracker
    bindings = request['bindings']; composition = request['compositions'][arm]
    scene,matrix = validate_scene(request,bindings['scene_freeze'])
    cameras = {int(c):camera for c,camera in scene['cameras'].items()}
    neighbors = _bound(bindings[composition['neighbors']])
    _require(neighbors.get('status') == 'complete' and neighbors.get('component') == composition['neighbors'] and
        neighbors.get('inputs') == bindings['inputs'], 'neighbor result/input lineage differs')
    ranked = {}
    for row in neighbors['records']:
        c,others = row['reference'],row['neighbors']
        _require(type(c) is int and c in TRAINING_CAMERAS and c not in ranked and row['status'] == 'complete' and
            len(others) == len(set(others)) == 3 and c not in others and
            all(type(other) is int and other in TRAINING_CAMERAS for other in others), 'invalid three training neighbors')
        ranked[c] = others
    _require(set(ranked) == set(TRAINING_CAMERAS), 'incomplete full-rig neighbors')
    inputs = _bound(bindings['inputs']); sources = _index(inputs['rgb'])
    native = {}
    for name in ('S2',composition['motion']):
        result = _bound(bindings[name])
        _require(result.get('status') == 'complete' and result.get('component') == name, 'incomplete/wrong native prerequisite')
        native[name] = _index(result['rows'],True)
    manifest = _bound(bindings['scene_manifest'])
    accepted = {(int(c['id']),f['frame_id']):f for c in manifest['cameras'] for f in c['frames']}
    expected = {(c,f,pair) for c in TRAINING_CAMERAS for pair in KEYFRAMES for f in (pair,pair+1)}
    for key in sorted(expected):
        c,f,pair = key; source = sources.get((c,f))
        _require(source is not None, 'missing accepted RGB source')
        for name in native:
            row = native[name].get(key)
            _require(row is not None and row['source_rgb_sha256'] == source['rgb']['sha256'] == accepted[c,f]['sha256'] and
                row['K'] == source['K'] == cameras[c]['K'] and row['grid'] == source['grid'], 'native source identity/calibration differs')
    threshold = getattr(backend,'sample_thresh',None)
    _require(type(threshold) in (float,int) and math.isfinite(threshold) and 0 <= threshold <= 1, 'finite matcher sampling threshold required')
    output = safe_path(output)
    started = clock()
    _require(type(started) in (int,float) and math.isfinite(started), 'finite geometry clock required')
    output.mkdir(parents=True,exist_ok=False)
    rng = np.random.default_rng(0); rows = []; cache = {}
    last = started; artifacts = []
    allocation = next(a for a in request['allocations'] if a['arm'] == arm and a['phase'] == 'geometry')
    deadline = PHASES['geometry'][1]
    artifact_bytes = 0

    def check_budget():
        nonlocal last
        now = clock()
        _require(type(now) in (int,float) and math.isfinite(now) and now >= last, 'finite monotonic geometry clock required')
        last = now
        _require(last-started <= deadline, 'geometry wall limit exceeded; partial files preserved')
        _require(artifact_bytes <= request['artifact_bytes_limit'], 'geometry artifact limit exceeded; partial files preserved')

    def observation(c,f,pair):
        key = (c,f,pair)
        if key not in cache:
            source,mask,change = sources[c,f],native['S2'][key],native[composition['motion']][key]
            loaded = observation_loader(source,mask,change)
            _require(isinstance(loaded,dict) and set(loaded) == {'rgb','valid','labels','changing'}, 'exact loaded observation arrays required')
            rgb,valid,labels,changing = (np.asarray(loaded[k]) for k in ('rgb','valid','labels','changing'))
            _require(rgb.dtype == np.uint8 and rgb.shape == (*SHAPE,3), 'uint8 RGB on accepted grid required')
            instances(labels,mask['semantics'],valid)
            _require(changing.dtype == np.bool_ and changing.shape == SHAPE, 'boolean changing mask on accepted grid required')
            cache[key] = dict(rgb=rgb,valid=valid,labels=labels,changing=changing,semantics=mask['semantics'])
        return cache[key]

    try:
        for frame in KEYFRAMES:
            for reference in TRAINING_CAMERAS:
                check_budget()
                ids = [reference,*ranked[reference]]
                first = {c:observation(c,frame,frame) for c in ids}
                second = {c:observation(c,frame+1,frame) for c in ids}
                images = {c:first[c]['rgb'] for c in ids}
                labels = {c:dict(labels=first[c]['labels'],semantics=first[c]['semantics']) for c in ids}
                changing = {c:first[c]['changing'] | second[c]['changing'] for c in ids}
                P = np.asarray([projection(consumer_camera(cameras[c])) for c in ids])
                centers = np.asarray([cameras[c]['center'] for c in ids])
                warps = {}; candidates = []
                for pair,other in enumerate(ids[1:],1):
                    (warp,confidence),matching = backend.match(images[reference],images[other])
                    (warp,confidence,crops),cropping = backend.crop(warp,confidence,images,labels,[reference,other])
                    warp,confidence = np.asarray(warp),np.asarray(confidence)
                    _require(warp.ndim == 3 and warp.shape[2] == 4 and confidence.shape == warp.shape[:2], 'matcher warp/confidence grid differs')
                    _require(isinstance(crops,list) and len(crops) <= 255 and
                        len({r['source_instance'] for r in crops}) == len(crops), 'person crop cap/uniqueness differs')
                    for crop in crops:
                        for camera,field in ((reference,'source_instance'),(other,'target_instance')):
                            if field in crop:
                                instance = crop[field]
                                _require(type(instance) is int and labels[camera]['semantics'].get(str(instance),{}).get('class') == 'person',
                                    'crop semantic person identity differs')
                    for measurement in (matching,cropping):
                        _fixture_measurement(measurement)
                    warps[other] = warp
                    uv0 = (warp[...,:2].reshape(-1,2)+1)*[480,270]
                    probability = confidence.reshape(-1).copy()
                    probability[~np.isfinite(probability)] = 0
                    probability[probability > threshold] = 1
                    from basketball_temporal_geometry import labels_at
                    sampled = labels_at(labels[reference]['labels'],uv0)
                    probability[sampled < 0] = 0
                    chosen = balanced_samples(probability,sampled,
                        {k:v['class'] for k,v in labels[reference]['semantics'].items()},5000,rng)
                    uv1 = (warp[...,2:].reshape(-1,2)[chosen]+1)*[480,270]
                    candidates.append((pair,uv0[chosen],uv1,matching,cropping,crops))
                source_rows = {name:[object_hash(native[name][c,f,frame]) for c in ids for f in (frame,frame+1)] for name in native}
                for pair,uv0,uv1,matching,cropping,crops in candidates:
                    check_budget(); other = ids[pair]
                    (xyz,numerical),triangulation = backend.triangulate(P[0],P[pair],uv0,uv1)
                    _fixture_measurement(triangulation)
                    xyz = np.asarray(xyz)
                    all_uv = np.asarray([uv0]+[uv1 if c == other or not len(uv0) else query_warp(warps[c],uv0) for c in ids[1:]])
                    arrays,diagnostic = evaluate_edge(xyz,numerical,all_uv,ids,pair,cameras,labels,changing)
                    kept = arrays['accepted']; X = xyz[kept]; UV = all_uv[:,kept]
                    support = arrays['candidate_support'][:,kept]; region = arrays['candidate_region'][kept]
                    world_velocity = np.zeros_like(X); measured = np.zeros(len(X),bool)
                    fg = np.flatnonzero(region > 0); lk = {}
                    if len(fg):
                        endpoints = []; valid = []
                        for k,c in enumerate(ids):
                            end,ok = tracker(images[c],second[c]['rgb'],UV[k,fg],first[c]['labels'],second[c]['labels'])
                            end,ok = np.asarray(end),np.asarray(ok)
                            _require(end.shape == (len(fg),2) and ok.shape == (len(fg),) and ok.dtype == np.bool_, 'LK endpoint/validity shapes differ')
                            endpoints.append(end); valid.append(ok & support[k,fg])
                            lk[str(c)] = dict(attempted=len(fg),lk_valid=int(ok.sum()),supported_valid=int(valid[-1].sum()))
                        # The unchanged gate computes (endpoint-start)/.04. Identity
                        # and duration1 expose physical metres/sec before normalization.
                        world_velocity[fg],measured[fg] = velocity_from_support(X[fg],np.asarray(endpoints),P,centers,
                            np.asarray(valid),ids,np.eye(4),duration_seconds=1.)
                    xy = np.floor(UV[0]).astype(int)
                    colors = images[reference][xy[:,1],xy[:,0]]/255.
                    arrays.update(world_positions=X.astype(np.float32),world_velocities=world_velocity.astype(np.float32),
                        positions=(X@matrix[:3,:3].T+matrix[:3,3]).astype(np.float32),
                        velocities=(world_velocity@matrix[:3,:3].T*2.).astype(np.float32),velocity_valid=measured,
                        colors=colors.astype(np.float32),times=np.full((len(X),1),frame/50,np.float32),
                        durations=np.full((len(X),1),.2,np.float32),region=region.astype(np.int32),camera_ids=np.asarray(ids),uv=UV,support=support)
                    path = output/f'pair{frame}-ref{reference}-other{other}.npz'
                    buffer = BytesIO()
                    np.savez_compressed(buffer,**arrays)
                    _require(artifact_bytes+buffer.tell() <= request['artifact_bytes_limit'], 'geometry artifact limit exceeded; partial files preserved')
                    with path.open('xb') as stream:
                        stream.write(buffer.getbuffer())
                    artifact = file_record(path); artifacts.append(artifact)
                    artifact_bytes += artifact['bytes']; check_budget()
                    rows.append(dict(pair_start=frame,reference=reference,other=other,artifact=artifact,source_rows=source_rows,
                        sampling=dict(requested=5000,obtained=len(xyz),shortage=5000-len(xyz)),matching=matching,cropping=cropping,
                        crops=crops,triangulation=triangulation,lk=lk,gates=diagnostic,physical_velocity_valid=int(measured.sum())))
        names = ('S2','D_fit','D_check','depth_decision',composition['motion'],composition['neighbors'])
        script_root = Path(__file__).resolve().parents[1]
        recipe = dict(mode='person-cropped',seed=0,samples_per_edge=5000,reprojection_pixels=2,parallax_degrees=1,
            minimum_foreground_support_cameras=3,lk_forward_backward_pixels=1,frame_seconds=.04,
            roma_revision=ROMA_PIN,expected_roma_weights=ROMA_WEIGHTS,native_model_verified=False,
            observation_loader='verified-native-files' if verified_loader else 'injected-fixture',
            sources=[file_record(path) for path in (Path(__file__),script_root/'basketball_temporal_cloud.py',
                script_root/'basketball_temporal_geometry.py',script_root/'vipe_benchmark/diagnostics.py',script_root/'edgs_source.py')])
        if verified_loader:
            recipe['sources'].append(file_record(script_root/'vipe_benchmark/final_render_loaders.py'))
        geometry = dict(schema='plan069-final-render-geometry/v1',status='complete',record_kind='fixture',arm=arm,
            request_sha256=object_hash(request),composition=composition,scene=bindings['scene_freeze'],rows=rows,
            prerequisites={name:bindings[name] for name in names},recipe=recipe,execution_authorized=False,native_adapter_qualified=False)
        payload_bytes = len((json.dumps(geometry,indent=2,allow_nan=False)+'\n').encode())
        _require(artifact_bytes+payload_bytes <= request['artifact_bytes_limit'], 'geometry artifact limit exceeded; partial files preserved')
        write_json(output/'geometry.json',geometry)
        geometry_record = file_record(output/'geometry.json'); artifacts.append(geometry_record)
        artifact_bytes += geometry_record['bytes'];check_budget()
        return dict(schema='plan069-final-render-geometry-worker/v1',record_kind='fixture',status='complete',arm=arm,
            request_sha256=object_hash(request),composition=composition,allocation_id=allocation['id'],geometry=geometry_record,
            coverage_edges=len(rows),artifact_bytes=artifact_bytes,elapsed_seconds=last-started,
            peak_device_bytes=0,cpu_workers_used=1,execution_authorized=False,native_adapter_qualified=False)
    except PermissionError:
        # Keep host-access denial distinct from a corrected application retry.
        raise
    except Exception as error:
        failure = dict(schema='plan069-final-render-geometry-failure/v1',record_kind='fixture',status='failed',
            arm=arm,composition=composition,request_sha256=object_hash(request),allocation_id=allocation['id'],
            reason=f'{type(error).__name__}: {error}',artifacts=artifacts,artifact_bytes=sum(r['bytes'] for r in artifacts),
            elapsed_seconds=last-started,peak_device_bytes=0,cpu_workers_used=1,
            execution_authorized=False,native_adapter_qualified=False)
        # Include the control receipt itself in published-byte accounting.
        control_bytes = artifact_bytes
        while True:
            failure['artifact_bytes'] = control_bytes
            payload_bytes = len((json.dumps(failure,indent=2,allow_nan=False)+'\n').encode())
            total = artifact_bytes+payload_bytes
            if total == control_bytes:
                break
            control_bytes = total
        result_record = None
        if control_bytes <= request['artifact_bytes_limit']:
            write_json(output/'failure.json',failure)
            result_record = file_record(output/'failure.json')
        else:
            failure['artifact_bytes'] = artifact_bytes
        raise GeometryFailure(str(error),failure,result_record) from error
