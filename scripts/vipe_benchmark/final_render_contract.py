"""Prospective QF worker and read-only ledger admission contracts.

CPU validation can establish a consistent REVIEW proposal. Native QF geometry,
initializer conversion, training and reload/render adapters are unimplemented;
this module cannot authorize or execute those jobs or consume their identities.
"""
import copy
from dataclasses import dataclass
import hashlib
import math

from .config import ROOT
from .files import file_record, object_hash, read_json, verify_record

TRAINING_CAMERAS=tuple(c for c in range(34) if c not in (0,10,20,30))
KEYFRAMES=(0,5,10,15,25,30,35,40,45)
COMPOSITIONS={
    'QF-B':dict(segmentation='S2',depth='D4',motion='M0',neighbors='N0'),
    'QF-M1':dict(segmentation='S2',depth='D4',motion='M1',neighbors='N0'),
    'QF-M2':dict(segmentation='S2',depth='D4',motion='M2',neighbors='N0'),
    'QF-N1':dict(segmentation='S2',depth='D4',motion='M0',neighbors='N1'),
    'QF-N2':dict(segmentation='S2',depth='D4',motion='M0',neighbors='N2'),
}
PHASES={'geometry':('gpu',5400),'initializer':('cpu',900),'train':('gpu',3600),'render':('gpu',900)}
PRESET_SOURCE='fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4'
PROCESSED_MANIFEST=('.local/sync-pivot/basketball-zero/manifest.json',
    '02006f379925cbb599ed071df48b7985e40cd3995b2d24293d92ecb736c26f94',561748)
FROZEN_SCOPE={
    'proposal':('docs/specs/plan031-execution/qualitative-final-render-review-proposal-001.md',
        'fc5b3e84852ac49e029fb8ebd3f2d4514183d7631ee0db1a887d7d20e92e5f62',11220),
    'segmentation_decision':('docs/research/vipe-alternatives/plan067-execution/human-review-001/segmentation-decision.json',
        '3d2ebe52be579b131a03c1aa14f388c91e05ef81a67708cbab4a62d9d3cad2f7',8484),
    'depth_decision':('docs/research/vipe-alternatives/plan067-execution/human-depth-review-001/depth-decision.json',
        'ab7c0808b5c5aaeb570dca1da4d16d84e1ccb580c2fe0cd01f01a53daf353c6d',8825),
}
BLOCKERS=('QF native geometry/initializer/train/reload-render adapter is unimplemented and unqualified.',
          'Scene-manifest exclusion union, calibration transforms and physical normalization require a checked adapter receipt.',
          'Measured initializer storage, checkpoint retention, native memory and cleanup reserves are not established.',
          'New allocation authority and locked DO admission are not implemented; no execution is authorized.')


@dataclass(frozen=True)
class Allocation:
    id:str
    arm:str
    phase:str
    resource:str
    seconds:int


@dataclass(frozen=True)
class Request:
    id:str
    record_kind:str
    allocations:tuple[Allocation,...]
    payload:dict


@dataclass(frozen=True)
class ReviewAdmission:
    request_sha256:str
    coverage_edges_per_arm:int
    gpu_seconds:int
    cpu_seconds:int
    execution_authorized:bool
    blockers:tuple[str,...]


def _require(condition,message):
    if not condition:raise ValueError(message)


def _verify(record):
    verified=verify_record(record)
    _require(record==verified,'changed file record size/path/hash')


def _bound(record):
    _verify(record)
    return read_json(record['path'])


def allocation_specs(identity):
    """Exactly 21 fresh prospective identities, with no attempt/retry pool."""
    _require(isinstance(identity,str) and identity and all(c.isalnum() or c in '-_' for c in identity),'invalid allocation prefix')
    values=[dict(id=identity+'/'+arm+'/'+phase,arm=arm,phase=phase,resource=resource,seconds=seconds)
        for arm in COMPOSITIONS for phase,(resource,seconds) in PHASES.items()]
    values.append(dict(id=identity+'/package',arm='all',phase='package',resource='cpu',seconds=900))
    return values


def validate_scope_bindings(bindings):
    """Bind actual REVIEW scope to proposal 001 and its exact human decisions.

    A later human choice or changed eligibility requires a new explicit proposal
    contract. Hash-valid caller-authored replacements cannot revise this scope.
    """
    for name,(relative,sha256,size) in FROZEN_SCOPE.items():
        expected=dict(path=str((ROOT/relative).resolve()),sha256=sha256,bytes=size)
        _require(bindings.get(name)==expected,'frozen proposal-001 '+name+' binding differs')
        _verify(expected)
    return dict(scope='proposal-001',bindings={name:copy.deepcopy(bindings[name]) for name in FROZEN_SCOPE})


def normalization_matrix(normalization, *, actual=False):
    """Validate the scene's complete similarity transform, including rotation."""
    import numpy as np
    if set(normalization)=={'transform'}:
        matrix=np.asarray(normalization['transform'],dtype=np.float64)
        _require(matrix.shape==(4,4) and np.isfinite(matrix).all(),'finite 4x4 normalization transform required')
        _require(np.array_equal(matrix[3],np.array([0.,0.,0.,1.])),'normalization transform must be affine')
        linear=matrix[:3,:3];gram=linear.T@linear;scale_squared=float(np.trace(gram)/3)
        _require(scale_squared>0 and np.linalg.det(linear)>0 and
            np.allclose(gram,np.eye(3)*scale_squared,rtol=1e-6,atol=1e-12),
            'normalization requires positive isotropic similarity scale and proper rotation')
        return matrix
    _require(not actual,'actual initializer normalization requires bound full transform')
    _require(set(normalization)=={'translate','radius'},'invalid fixture normalization schema')
    translation=normalization['translate'];radius=normalization['radius']
    _require(len(translation)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in translation)
        and type(radius) in (int,float) and math.isfinite(radius) and radius>0,'finite fixture normalization required')
    matrix=np.eye(4);matrix[:3,:3]/=radius;matrix[:3,3]=np.asarray(translation)/radius
    return matrix


def parse_request(value):
    _require(value.get('schema')=='plan067-final-render-request/v1','wrong QF request schema')
    _require(value.get('record_kind') in ('actual','fixture') and value.get('mode')=='REVIEW','QF contract is REVIEW only; DO adapter is unimplemented')
    if value['record_kind']=='actual':validate_scope_bindings(value['bindings'])
    _require(value.get('compositions')==COMPOSITIONS,'fixed isolated five-arm compositions required')
    _require(type(value.get('seed')) is int and value['seed']==0,'seed must equal zero')
    _require(type(value.get('iterations')) is int and value['iterations']==5000,'equal 5000 training iterations required')
    _require(value.get('preset')=='default_keyframe' and value.get('preset_source_sha256')==PRESET_SOURCE,'frozen native preset source pin required')
    _require(value.get('geometry')==dict(keyframes=list(KEYFRAMES),samples_per_edge=5000,neighbors_per_reference=3),'frozen geometry settings required')
    _require(value.get('render')==dict(cameras=[0,10,20,30],frames=list(range(50)),fps=25,resolution=[960,540]),'complete fixed held-out render coverage required')
    _require(value.get('allocations')==allocation_specs(value['id']),'distinct exact fresh allocation identities and ceilings required')
    for name,maximum in [('artifact_bytes_limit',50*2**30),('device_bytes_limit',22*2**30),('cpu_workers_limit',8)]:
        amount=value.get(name)
        _require(type(amount) is int and 0<amount<=maximum,'excessive or invalid '+name)
    initializer=value['initializer_contract']
    _require(initializer.get('schema')=='plan067-final-render-initializer/v1' and
        initializer.get('velocity_units')=='normalized-scene/normalized-time' and initializer.get('time_formula')=='frame/50',
        'initializer time/velocity units required')
    normalization_matrix(initializer['normalization'],actual=value['record_kind']=='actual')
    if 'voxel_basis' in initializer or 'voxel_basis_source' in initializer:
        _require('voxel_basis' in initializer and set(initializer.get('voxel_basis_source',{}))=={'archive','receipt'},'complete voxel basis lineage required')
        _verify(initializer['voxel_basis'])
        for record in initializer['voxel_basis_source'].values():_verify(record)
    names={'proposal','source','preset','runtime','config','qualification','scene_manifest','inputs',
        'segmentation_decision','depth_decision','S2','D4_fit','D4_check','M0','M1','M2','N0','N1','N2'}
    if value['record_kind']=='actual' or 'scene_freeze' in value['bindings']:names.add('scene_freeze')
    _require(set(value['bindings'])==names,'complete exact prerequisite bindings required')
    for record in value['bindings'].values():_verify(record)
    if value['record_kind']=='actual':
        _require(value['bindings']['source']==file_record(__file__),'current QF contract source binding required')
        _require(value['bindings']['preset']['sha256']==PRESET_SOURCE,'actual native preset bytes differ from source pin')
    return Request(value['id'],value['record_kind'],tuple(Allocation(**a) for a in value['allocations']),copy.deepcopy(value))


def _decision(record,candidate,actual):
    value=_bound(record)
    _require(value.get('schema')=='plan067-qualitative-decision/v1' and value.get('status')=='ready'
        and value.get('selected_candidate_ids')==[candidate],'actual selected '+candidate+' decision required')
    _require(value.get('actual_human_review') is actual,'decision actual/fixture mismatch')
    if not actual:
        _require(value.get('record_kind')=='fixture','synthetic decision must be labeled fixture')
        return
    from .qualitative_review import validate_review
    imported=_bound(value['review'])
    if imported.get('schema')=='plan067-qualitative-review-result/v1':
        submission=_bound(imported['submission'])
        _require(imported['actual_human_review'] is True and imported['review']==submission and imported['package']==submission['package'],'actual review import substitution')
    else:submission=imported
    review=validate_review(submission,actual=True)
    _require(value['package']==review['package'] and value['reviewer']==review['reviewer'],'decision human/package binding differs')
    eligibility=value['engineering_eligibility'][candidate]
    _require(eligibility['eligible'] is True and bool(eligibility['reason'].strip()),'decision engineering eligibility missing')
    choice=value['human_choice']
    if choice is not None:
        _require(choice['candidate_ids']==[candidate] and choice['reviewer']==review['reviewer'] and bool(choice['reason'].strip()),'explicit human choice mismatch')
    else:
        preference=review['criteria']['overall']['preference']
        _require(preference['outcome']=='preferred' and preference['candidate_ids']==[candidate],'decision differs from actual human preference')


def _completed(record,component,events,bindings,actual):
    result=_bound(record)
    _require(result.get('status')=='complete' and result.get('component')==component,'complete '+component+' prerequisite required')
    _require(any(e.get('event')=='finish' and e.get('status')=='complete' and e.get('result')==record for e in events),'prerequisite lacks successful ledger-bound result')
    if actual:
        worker=_bound(result['configuration'])
        _require(worker['component']==component and worker['configuration']==bindings['config'] and worker['inputs']==bindings['inputs'],'prerequisite worker configuration/input binding differs')
    return result


def _coverage(request,events):
    bindings=request.payload['bindings'];actual=request.record_kind=='actual'
    inputs=_bound(bindings['inputs']);sources={}
    for row in inputs['rgb']:
        identity=row['identity'];key=(identity['branch'],identity['camera'],identity['frame'])
        _require(key not in sources,'duplicate accepted RGB identity')
        sources[key]=row
    # Both frames of all nine pairs are required. No dropped missing rows or
    # fabricated contiguous-frame interpolation may substitute for coverage.
    required={(camera,frame,pair) for camera in TRAINING_CAMERAS for pair in KEYFRAMES for frame in (pair,pair+1)}
    for component in ('S2','M0','M1','M2'):
        result=_completed(bindings[component],component,events,bindings,actual)
        rows={}
        for row in result['rows']:
            identity=row['identity']
            if identity['branch']!='reconstruction':continue
            key=(identity['camera'],identity['frame'],identity['pair_start'])
            _require(key not in rows,'duplicate native '+component+' identity')
            rows[key]=row
        _require(required<=set(rows),'missing full-rig '+component+' coverage')
        for camera,frame,pair in required:
            row=rows[(camera,frame,pair)];source=sources.get(('reconstruction',camera,frame))
            _require(source is not None and row['source_rgb_sha256']==source['rgb']['sha256'] and row['K']==source['K'] and row['grid']==source['grid'],component+' native input geometry mismatch')
            if actual:
                verify_record(source['rgb']);verify_record(row['valid'])
                verify_record(row['semantic_static'] if component=='S2' else row['changing'])
    for component in ('N0','N1','N2'):
        result=_completed(bindings[component],component,events,bindings,actual)
        _require(result['inputs']==bindings['inputs'],'neighbor inputs differ')
        rows={}
        for row in result['records']:
            _require(row['reference'] not in rows,'duplicate neighbor reference')
            rows[row['reference']]=row
        _require(set(TRAINING_CAMERAS)<=set(rows),'missing neighbor full-rig coverage')
        for camera in TRAINING_CAMERAS:
            row=rows[camera];neighbors=row['neighbors']
            _require(row['status']=='complete' and len(neighbors)==3 and len(set(neighbors))==3 and camera not in neighbors
                and set(neighbors)<=set(TRAINING_CAMERAS),'invalid or held-out neighbor membership')
    fit=_completed(bindings['D4_fit'],'D4',events,bindings,actual)
    check=_completed(bindings['D4_check'],'D4',events,bindings,actual)
    scale=_bound(fit['scale'])
    _require(scale.get('status')=='passed' and type(scale.get('scale')) in (int,float) and math.isfinite(scale['scale']) and scale['scale']>0,'passing frozen D4 scale required')
    # Check receipts may copy the frozen fit record under a new immutable path.
    check_scale=_bound(check['scale'])
    _require(check_scale.get('status')=='passed' and check_scale.get('scale')==scale['scale'],'D4 check scale differs from frozen fit')
    if actual:
        _require(_bound(check['configuration'])['frozen_fit']==fit['scale'],'D4 check worker did not consume frozen successful fit')
    for result,frame in [(fit,100),(check,175)]:
        cameras=[r['identity']['camera'] for r in result['rows'] if r['identity']['branch']=='depth' and r['identity']['frame']==frame]
        _require(set(cameras)==set(TRAINING_CAMERAS) and len(cameras)==30,'D4 fit/check coverage differs')
    return 30*len(KEYFRAMES)*3


def _processed_scene_validation(value,scene_record):
    # This independent pure adapter checks the existing processed manifest,
    # union exclusions, D4 scale, historical normalization, cameras and units.
    # Lazy loading avoids a contract/adapter import cycle and has no GPU path.
    from .final_render_initializer import validate_scene
    scene,matrix=validate_scene(value,scene_record)
    return dict(schema='plan067-final-render-scene-validation/v1',status='passed',
        manifest=value['bindings']['scene_manifest'],scene_freeze=scene_record,
        transform=matrix.tolist(),native_execution_qualified=False)


def validate_scene_bindings(value):
    """Validate the actual accepted processed manifest through its existing seam."""
    bindings=value['bindings'];scene=_bound(bindings['scene_manifest'])
    if value['record_kind']=='actual':
        relative,sha256,size=PROCESSED_MANIFEST
        expected=dict(path=str((ROOT/relative).resolve()),sha256=sha256,bytes=size)
        _require(bindings['scene_manifest']==expected,'accepted processed manifest path/hash/size differs')
        _verify(expected)
        _require(scene.get('schema')=='basketball-processed/v1','actual accepted processed manifest required')
    if scene.get('schema')=='basketball-processed/v1':
        _require('scene_freeze' in bindings,'processed manifest requires bound scene_freeze')
        _verify(bindings['scene_freeze'])
        return _processed_scene_validation(value,bindings['scene_freeze'])
    _require(value['record_kind']=='fixture','actual accepted processed manifest required')
    _require(scene['schema']=='dynamic-gaussian-scene/v1' and scene['evaluation']['training_cameras']==[str(c) for c in TRAINING_CAMERAS]
        and set(scene['evaluation']['held_out_cameras'])=={'0','10','20','30'},'exact fixture train/held-out camera split required')
    _require(scene['frames']['ids']==list(range(50)) and scene['frames']['count']==50 and
        scene['frames']['normalized_time']['formula']=='frame_offset / count' and scene['source']['frame_rate']==25,'fixture scene time normalization mismatch')
    if 'normalization' in scene:
        normalization=value['initializer_contract']['normalization']
        if 'transform' in normalization:
            _require(scene['normalization'].get('transform')==normalization['transform'],'initializer full transform differs from bound scene manifest')
        else:_require(scene['normalization']==normalization,'initializer normalization differs from bound scene manifest')
    consumed_keys={(str(c),f) for c in TRAINING_CAMERAS for k in KEYFRAMES for f in (k,k+1)}
    exclusions={(str(r['camera']),r['frame']) for r in scene.get('excluded_observations',[])}
    _require(not consumed_keys & exclusions,'scene manifest exclusion intersects frozen initialization coverage')
    return dict(schema='plan067-final-render-scene-validation/v1',status='passed',record_kind='fixture',native_execution_qualified=False)


def admit_review(value,ledger,storage):
    """Check prospective scope against a ledger snapshot without writing it."""
    request=parse_request(value);events=ledger.events();bindings=request.payload['bindings']
    _require(_bound(bindings['config'])==ledger.config,'allocation configuration differs from ledger')
    _require(not any(s['event']=='reserve' for s in ledger.states(events).values()),'active allocated job blocks QF admission')
    consumed={e.get('job_id') for e in events if e.get('event') in ('reserve','finish','account','checkpoint','checkpoint_resume')}
    _require(not consumed & {a.id for a in request.allocations},'consumed allocation identity cannot be reused')
    _decision(bindings['segmentation_decision'],'S2',request.record_kind=='actual')
    _decision(bindings['depth_decision'],'D4',request.record_kind=='actual')
    qualification=_bound(bindings['qualification'])
    if request.record_kind=='actual':
        from .s1_validation_contract import validate_wrapper
        validate_wrapper(qualification,qualification['semantic_amendment'],bindings['config'])
    else:_require(qualification.get('status')=='passed' and qualification.get('record_kind')=='fixture','passing CPU fixture qualification required')
    validate_scene_bindings(value)
    coverage=_coverage(request,events)
    totals=ledger.totals(events);gpu=sum(a.seconds for a in request.allocations if a.resource=='gpu');cpu=sum(a.seconds for a in request.allocations if a.resource=='cpu')
    for resource,seconds,key in [('gpu',gpu,'gpu_total_seconds_limit'),('cpu',cpu,'cpu_prepare_score_report_seconds_limit')]:
        _require(totals[resource]['elapsed_seconds']+totals[resource]['reserved_seconds']+seconds<=ledger.config[key],resource.upper()+' cumulative ceiling exhausted')
    _require(totals['setup']['elapsed_seconds']+totals['setup']['reserved_seconds']<=ledger.config['setup_wall_seconds_limit'],'setup cumulative ceiling exhausted')
    _require(value['cpu_workers_limit']<=ledger.config['cpu_max_workers'] and
        value['device_bytes_limit']<=ledger.config['gpu_peak_device_gib_limit']*2**30,'original worker/device ceiling exceeded')
    for key in ('artifact_bytes','download_bytes','free_disk_bytes'):
        _require(type(storage[key]) is int and storage[key]>=0,'invalid live storage reading')
    _require(storage['artifact_bytes']+value['artifact_bytes_limit']<=ledger.config['new_artifact_disk_gib_limit']*2**30,'artifact cumulative ceiling exhausted')
    _require(storage['free_disk_bytes']>=value['artifact_bytes_limit'],'insufficient free disk for declared artifacts')
    _require(storage['download_bytes']<=ledger.config['new_download_gib_limit']*2**30,'download cumulative ceiling exhausted')
    return ReviewAdmission(object_hash(value),coverage,gpu,cpu,False,BLOCKERS)


def validate_initializer(value,arm,receipt,arrays):
    """Reuse the audited pure native-array validator; never relax load_frozen."""
    request=parse_request(value)
    _require(arm in COMPOSITIONS,'unknown QF initializer arm')
    expected=dict(value['initializer_contract'],arm=arm,composition=COMPOSITIONS[arm])
    _require({key:receipt.get(key) for key in expected}==expected,'initializer arm, isolation, transform or velocity units differ')
    from basketball_dense_fusion import validate
    validate(arrays)
    _require(set(receipt)==set(expected)|{'arrays_sha256','prerequisites','scene_manifest'},'complete initializer array/provenance receipt required')
    _require(receipt['arrays_sha256']==initializer_arrays_hash(arrays),'initializer arrays differ from bound receipt')
    composition=COMPOSITIONS[arm]
    prerequisite_names={'S2','D4_fit','D4_check',composition['motion'],composition['neighbors']}
    _require(receipt['prerequisites']=={name:value['bindings'][name] for name in prerequisite_names}
        and receipt['scene_manifest']==value['bindings']['scene_manifest'],'initializer prerequisite or scene lineage differs')
    return dict(schema='plan067-final-render-initializer-validation/v1',arm=arm,point_count=len(arrays['positions']),
        request_sha256=object_hash(request.payload),status='passed',native_adapter_qualified=False)


def initializer_arrays_hash(arrays):
    """Hash array names, dtypes, shapes and bytes independently of NPZ encoding."""
    import numpy as np
    checksum=hashlib.sha256()
    for name in sorted(arrays):
        value=np.asarray(arrays[name]);_require(not value.dtype.hasobject,'initializer object arrays forbidden')
        header=dict(name=name,dtype=value.dtype.str,shape=list(value.shape))
        checksum.update(object_hash(header).encode());checksum.update(value.tobytes(order='C'))
    return checksum.hexdigest()


def validate_worker_result(value,arm,phase,result):
    """Validate CPU fake-worker outcomes while native dispatch remains absent."""
    request=parse_request(value)
    _require(arm in COMPOSITIONS and phase in PHASES,'unknown QF worker phase')
    _require(result.get('schema')=='plan067-final-render-worker-result/v1' and result.get('arm')==arm and result.get('phase')==phase,'worker result identity mismatch')
    _require(result.get('record_kind')=='fixture' and request.record_kind=='fixture','native QF execution adapter is unimplemented')
    _require(result['allocation_id']==value['id']+'/'+arm+'/'+phase,'worker allocation identity mismatch')
    _require(result['request_sha256']==object_hash(value),'worker result request binding differs')
    elapsed=result['elapsed_seconds'];limit=PHASES[phase][1]
    _require(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<=elapsed<=limit,'worker exceeded finite deadline')
    _require(result['status'] in ('complete','failed','blocked'),'invalid worker outcome')
    if result['status']=='complete':
        _require(bool(result['artifacts']),'completed worker lacks immutable artifacts')
        for artifact in result['artifacts']:_verify(artifact)
        if phase=='train':_require(result['completed_iterations']==5000,'worker training iterations unequal')
        if phase=='render':
            keys=[(r['camera'],r['frame']) for r in result['rendered_frames']]
            _require(len(keys)==200 and set(keys)=={(c,f) for c in (0,10,20,30) for f in range(50)},'worker render coverage incomplete')
    else:_require(bool(result.get('reason','').strip()),'unavailable worker requires reason')
    return copy.deepcopy(result)
