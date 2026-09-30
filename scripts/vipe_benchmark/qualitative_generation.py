"""Bounded CPU preparation of matched component diagnostics for human review.

These overlays are component outputs, not trained reconstruction renders. Source
frames, model rows and successful ledger outcomes remain independently bound.
"""
import math
import copy
from contextvars import ContextVar
from pathlib import Path
import shutil
import subprocess
import time

from .config import ROOT, load
from .execution import result_record, resources
from .files import file_record, load_array, object_hash, read_json, safe_path, verify_record, write_json
from .ledger import Ledger
from .supervisor import directory_bytes

GROUPS = {'segmentation': ['S0','S1','S2','S3','S4'], 'motion': ['M0','M1','M2'],
          'depth': ['D0','D1','D2','D3','D4'], 'neighbors': ['N0','N1','N2']}
_PUBLICATION_DEADLINE = ContextVar('qualitative_publication_deadline', default=None)
_STORAGE_GUARD = ContextVar('qualitative_storage_guard',default=None)
_LOADED_SOURCE = Path(__file__).read_bytes()
RECIPE = 'plan067-diagnostic-recipe/v1'


def _selection(camera, frames, role, kind='frame'):
    return dict(id=f'camera{camera}-{role}-'+'-'.join(map(str,frames)), kind=kind,
                role=role,camera_id=str(camera),frame_ids=frames,timestamps=[f/25 for f in frames])


def _request(value, ledger):
    if value['schema'] != 'plan067-qualitative-generation/v1' or value['record_kind'] not in ('actual','fixture'):
        raise ValueError('invalid qualitative generation request')
    if not value['id'].strip(): raise ValueError('missing immutable generation identity')
    for name in ('config','inputs','amendment','approval'): verify_record(value['bindings'][name])
    if value['record_kind']=='actual':
        approval=read_json(value['bindings']['approval']['path'])
        if (approval.get('schema')!='plan067-implementation-approval/v1' or
                approval.get('record_kind')!='user-authorization' or not approval.get('instruction','').strip() or
                approval.get('scope',{}).get('qualitative_preparation')!='Implement and generate immutable matched diagnostic packages from valid existing results within remaining CPU and artifact ceilings.'):
            raise ValueError('actual preparation lacks explicit qualitative authorization')
        amendment=ROOT/'docs/specs/plan031-execution/qualitative-comparison-amendment.md'
        if value['bindings']['amendment']['sha256']!=file_record(amendment)['sha256']:
            raise ValueError('actual preparation amendment differs from current approved qualitative amendment')
        if not value.get('detail_regions'): raise ValueError('actual preparation requires frozen shared detail regions')
        if read_json(value['bindings']['config']['path'])!=ledger.config:
            raise ValueError('generation configuration differs from ledger allocation')
        expected=safe_path(value['local'])/'prepare/inputs.json'
        if Path(value['bindings']['inputs']['path']).resolve()!=expected.resolve():
            raise ValueError('generation must use accepted run inputs')
    for key,low,high in [('cameras',0,100),('reconstruction_frames',0,49),('depth_frames',150,199)]:
        rows=value[key]
        if not rows or rows != sorted(set(rows)) or any(type(x) is not int or not low<=x<=high for x in rows):
            raise ValueError('invalid frozen '+key)
    motion=value.get('motion_frames',value['reconstruction_frames'])
    if not motion or motion!=sorted(set(motion)) or any(type(x) is not int or not 0<=x<=49 for x in motion):
        raise ValueError('invalid frozen motion_frames')
    seconds=value['max_seconds']
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=600:
        raise ValueError('invalid CPU artifact preparation deadline')
    low,high=value['depth_range_metres']
    if not (math.isfinite(low) and math.isfinite(high) and 0<=low<high): raise ValueError('invalid shared depth color range')
    events=ledger.events()
    if any(s['event']=='reserve' for s in ledger.states(events).values()):
        raise ValueError('artifact preparation requires no active allocated job')
    if ledger.totals(events)['cpu']['elapsed_seconds']+seconds>ledger.config['cpu_prepare_score_report_seconds_limit']:
        raise ValueError('CPU preparation allocation exhausted')
    return events


def _check(deadline):
    if time.monotonic()>=deadline: raise TimeoutError('qualitative artifact preparation deadline')
    guard=_STORAGE_GUARD.get()
    if guard is not None:guard()


def _storage_guard(request, ledger, paths):
    maximum=request.get('max_new_artifact_bytes',2**30)
    if type(maximum) is not int or not 65536<maximum<=2**30:
        raise ValueError('invalid new qualitative artifact storage budget')
    if request['record_kind']=='actual' and 'max_new_artifact_bytes' not in request:
        raise ValueError('actual preparation requires explicit artifact storage budget')
    baseline=(resources(safe_path(request['local']),gpu=False)['artifact_bytes']
              if request['record_kind']=='actual' else directory_bytes(safe_path(request['local'])))
    ceiling=ledger.config.get('new_artifact_disk_gib_limit',150)*2**30
    if baseline+maximum>ceiling:raise ValueError('artifact storage allocation exhausted')
    def check():
        current=sum(directory_bytes(path) if path.is_dir() else path.stat().st_blocks*512 if path.exists() else 0 for path in paths)
        if current+65536>maximum or baseline+current+65536>ceiling:
            raise ValueError('qualitative artifact storage budget exceeded')
    return check


def _image(record):
    from PIL import Image
    verify_record(record)
    with Image.open(safe_path(record['path'])) as image: return image.convert('RGB')


def _overlay(source, row, group, depth_range):
    import numpy as np
    from PIL import Image, ImageDraw
    image=source.copy()
    if group=='neighbors':
        draw=ImageDraw.Draw(image); draw.rectangle((0,0,image.width,45),fill='black')
        draw.text((8,8),'Neighbor selection diagnostic: '+str(row['neighbors']),fill='white')
        return image
    if group=='depth':
        with load_array(row['depth']) as data:
            depth=data['depth'].copy(); valid=data['valid'].astype(bool)
        if depth.shape!=(image.height,image.width) or valid.shape!=depth.shape: raise ValueError('depth grid mismatch')
        if not np.isfinite(depth[valid]).all(): raise ValueError('nonfinite valid depth')
        low,high=depth_range; norm=np.clip((depth-low)/(high-low),0,1)
        pixels=np.stack([norm*255,(1-np.abs(norm*2-1))*255,(1-norm)*255],axis=-1)
        pixels[~valid]=0
        return Image.fromarray(pixels.astype('uint8'))
    if group=='segmentation':
        verify_record(row['semantic_static'])
        with Image.open(row['semantic_static']['path']) as mask: array=np.asarray(mask)
        mask=array==0
    else: mask=load_array(row['changing']).astype(bool)
    if mask.shape!=(image.height,image.width): raise ValueError('mask grid mismatch')
    pixels=np.asarray(image).copy(); tint=pixels[mask]*.55+np.array([255,0,0])*.45
    pixels[mask]=tint.astype('uint8')
    return Image.fromarray(pixels)


def _native_row(result, source, group):
    """Input frames have no pair context; model rows retain their actual context.

    When a frame occurs in several frozen reconstruction pairs, choose the
    lowest pair_start before reviewing outputs. Never collapse its lineage.
    """
    identity=source['identity']
    if group=='neighbors':
        return next((r for r in result['records'] if r['reference']==identity['camera'] and r['status']=='complete'),None)
    matches=[r for r in result['rows'] if all(r['identity'][key]==identity[key] for key in ('branch','camera','frame'))]
    if not matches:return None
    matches.sort(key=lambda r:-1 if r['identity']['pair_start'] is None else r['identity']['pair_start'])
    if len(matches)>1 and matches[0]['identity']==matches[1]['identity']:
        raise ValueError('duplicate native row identity')
    return matches[0]


def _media(path, selection, resolution, **lineage):
    return dict(selection_id=selection['id'],kind='frame',record=file_record(path),
                frame_ids=selection['frame_ids'],timestamps=selection['timestamps'],resolution=resolution,**lineage)


def _videos(candidate, selections, folder, deadline, resolution):
    # Preserve every selected image. Sparse outputs get an explicitly labeled
    # sequence. Only the consecutive prefix can become a continuous clip.
    for selection in [s for s in selections if s['kind']=='clip']:
        images=[]
        for frame in selection['frame_ids']:
            match=next((m for m in candidate['media'] if m['kind']=='frame' and
                        m['frame_ids']==[frame] and m.get('camera_id')==selection['camera_id']),None)
            if match is None: break
            images.append(match['record'])
        if len(images)!=len(selection['frame_ids']): continue
        _check(deadline)
        sequence=folder/selection['id'];sequence.mkdir()
        for index,record in enumerate(images): shutil.copyfile(record['path'],sequence/f'{index:04d}.png')
        video=folder/(selection['id']+'.mp4')
        subprocess.run(['ffmpeg','-v','error','-threads','1','-framerate','25','-i',str(sequence/'%04d.png'),
                        '-frames:v',str(len(images)),'-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(video)],
                       check=True,timeout=max(.001,deadline-time.monotonic()),capture_output=True)
        ids=selection['frame_ids']; kind='clip' if all(b==a+1 for a,b in zip(ids,ids[1:])) else 'sequence'
        candidate['media'].append(dict(selection_id=selection['id'],kind=kind,record=file_record(video),
            frame_ids=ids,timestamps=selection['timestamps'],resolution=resolution,
            limitations=('Sparse sequences cannot establish continuous motion.' if kind=='sequence' else
                f'{len(ids)/25:.2f}-second diagnostic clip is too brief to establish sustained motion quality.' if len(ids)<25 else
                'Component diagnostic motion only; final rendered motion is not evaluated.'),
            source_images=images))


def _build(request, output, events, deadline):
    inputs=read_json(request['bindings']['inputs']['path']);local=safe_path(request['local'])
    write_json(output/'ledger-prefix.json',dict(events=events))
    prefix=file_record(output/'ledger-prefix.json')
    all_inputs=inputs['rgb']+inputs['depth']; manifests={}
    for group,components in GROUPS.items():
        _check(deadline);folder=output/group;folder.mkdir()
        role='selection' if group=='depth' else 'reconstruction'
        frames=(request['depth_frames'] if group=='depth' else request.get('motion_frames',request['reconstruction_frames'])
                if group=='motion' else request['reconstruction_frames'])
        selections=[_selection(camera,[frame],role) for camera in request['cameras'] for frame in frames]
        if group!='depth' and len(frames)>1:
            for camera in request['cameras']:
                selections.append(_selection(camera,frames,role,'clip'))
                prefix_frames=[frames[0]]
                for frame in frames[1:]:
                    if frame!=prefix_frames[-1]+1: break
                    prefix_frames.append(frame)
                if 1<len(prefix_frames)<len(frames): selections.append(_selection(camera,prefix_frames,role,'clip'))
        frame_selections=[s for s in selections if s['kind']=='frame']
        source_rows={}
        for selection in frame_selections:
            _check(deadline)
            branch='depth' if group=='depth' else 'reconstruction'
            row=next((r for r in all_inputs if r['identity']['branch']==branch and
                str(r['identity']['camera'])==selection['camera_id'] and r['identity']['frame']==selection['frame_ids'][0]),None)
            if row is None: raise ValueError('accepted inputs lack frozen '+selection['id'])
            source_rows[selection['id']]=row
        first=_image(next(iter(source_rows.values()))['rgb']);resolution=list(first.size)
        for region in request.get('detail_regions',[]):
            x,y,w,h=region['crop']
            if not region['id'].strip() or any(type(v) is not int for v in (x,y,w,h)) or min(x,y)<0 or min(w,h)<=0 or x+w>resolution[0] or y+h>resolution[1]:
                raise ValueError('shared detail crop outside accepted source resolution')
        candidates=[]
        control=dict(id='source-rgb',label='Source RGB control',is_control=True,stage='accepted input',output_type='reference',
            status='available',reason='',provenance=dict(source_result=request['bindings']['inputs'],ledger_outcome=prefix,
                configuration=request['bindings']['config']),media=[])
        control_folder=folder/'source-rgb';control_folder.mkdir()
        for selection in frame_selections:
            row=source_rows[selection['id']];image=_image(row['rgb'])
            if list(image.size)!=resolution: raise ValueError('source resolution mismatch')
            path=control_folder/(selection['id']+'.png');image.save(path)
            _check(deadline)
            control['media'].append(_media(path,selection,resolution,source_input=row['rgb'],camera_id=selection['camera_id']))
        _videos(control,selections,control_folder,deadline,resolution);candidates.append(control)
        for component in components:
            _check(deadline)
            job=component+('-reconstruction' if group=='segmentation' else '-check' if group=='depth' else '')
            record=result_record(local,job)
            candidate=dict(id=component,label=component+' '+group+' component diagnostic'+(' (baseline)' if component.endswith('0') else ''),is_control=component.endswith('0'),
                stage=group+' component diagnostic',output_type='component',status='missing',
                reason='No successfully completed ledger-bound result for '+job,provenance={},media=[])
            candidates.append(candidate)
            if record is None: continue
            verify_record(record);result=read_json(record['path'])
            if result['status']!='complete' or result.get('component')!=component: raise ValueError('result component/status mismatch')
            event=next((e for e in reversed(events) if e.get('event')=='finish' and e.get('status')=='complete' and e.get('result')==record),None)
            if event is None: raise ValueError('result lacks successful immutable ledger outcome')
            destination=folder/component;destination.mkdir();write_json(destination/'outcome.json',event)
            candidate['provenance']=dict(source_result=record,ledger_outcome=file_record(destination/'outcome.json'),configuration=request['bindings']['config'])
            for selection in frame_selections:
                _check(deadline);source=source_rows[selection['id']]
                if group=='neighbors':
                    if result.get('inputs')!=request['bindings']['inputs']: raise ValueError('neighbor inputs differ')
                    row=_native_row(result,source,group)
                else:
                    row=_native_row(result,source,group)
                    if row is not None and (row['source_rgb_sha256']!=source['rgb']['sha256'] or row['K']!=source['K'] or row['grid']!=source['grid']):
                        raise ValueError('model row/input geometry lineage mismatch')
                if row is None: continue
                image=_overlay(_image(source['rgb']),row,group,request['depth_range_metres'])
                path=destination/(selection['id']+'.png');image.save(path)
                _check(deadline)
                candidate['media'].append(_media(path,selection,resolution,source_input=source['rgb'],camera_id=selection['camera_id'],
                    source_identity=source['identity'],native_identity=row.get('identity',{'reference':row.get('reference')}),
                    source_row_sha256=object_hash(row),
                    limitations='Component diagnostic only; final rendered sharpness and reconstruction appearance are not evaluated.'))
            if candidate['media']:
                candidate.update(status='available',reason='')
                _videos(candidate,selections,destination,deadline,resolution)
        candidates.append(dict(id='final-render',label='Trained reconstruction render',is_control=False,stage='downstream training/rendering',
            output_type='final-render',status='unavailable',reason='Requires actual initial human choices and separately bounded downstream generation.',provenance={},media=[]))
        manifest=dict(schema='plan067-qualitative-package/v1',id=request['id']+'-'+group,mode='qualitative',record_kind=request['record_kind'],
            bindings=dict(source=file_record(output/'source.py'),**{k:request['bindings'][k] for k in ('config','inputs','amendment')},
                request=file_record(output/'request.json'),approval=request['bindings']['approval']),
            settings=dict(fps=25,resolution=resolution,color_handling='sRGB',crop=[0,0,*resolution],detail_regions=request.get('detail_regions',[]),recipe=RECIPE,
                depth_range_metres=request['depth_range_metres'],mask_exclusion_color='45% red overlay'),selections=selections,candidates=candidates)
        path=folder/'manifest.json';write_json(path,manifest);manifests[group]=file_record(path)
    return manifests


def generate(request, output, *, ledger=None):
    """Prepare immutable outputs; charge elapsed CPU time even on failure.

    Admission rejects active model jobs and reserves cumulative CPU headroom
    before any write. The caller serializes live ledger execution. This is input
    artifact preparation under the explicit qualitative amendment, not a reset
    of any consumed aggregation/report/model allocation.
    """
    ledger=ledger or Ledger(safe_path(request['local'])/'ledger.jsonl',load())
    events=_request(request,ledger);output=safe_path(output)
    if Path(__file__).read_bytes()!=_LOADED_SOURCE:raise ValueError('generation implementation changed after import')
    guard=_storage_guard(request,ledger,[output]);output.mkdir(parents=True,exist_ok=False)
    storage_token=_STORAGE_GUARD.set(guard)
    start=time.monotonic();deadline=start+request['max_seconds'];failure=None;manifests={}
    write_json(output/'request.json',request)
    with (output/'source.py').open('xb') as stream:stream.write(_LOADED_SOURCE)
    try:
        manifests=_build(request,output,events,deadline)
        _check(deadline)
    except Exception as error: failure=error
    finally:_STORAGE_GUARD.reset(storage_token)
    result=dict(schema='plan067-qualitative-generation-result/v1',status='failed' if failure else 'complete',
        request=file_record(output/'request.json'),manifests=manifests,elapsed_seconds=time.monotonic()-start,
        source=file_record(output/'source.py'),recipe=RECIPE,
        error=str(failure) if failure else None,scope='CPU qualitative input artifact preparation')
    write_json(output/'result.json',result)
    ledger.charge_cpu_preparation(result['elapsed_seconds'],file_record(output/'result.json'))
    if failure: raise failure
    return result


def validate_actual_package(manifest, *, deadline=None):
    """Verify actual publication back to charged generation and native outputs."""
    import numpy as np
    deadline=deadline if deadline is not None else _PUBLICATION_DEADLINE.get()
    bindings=manifest['bindings']
    for name in ('generation_result','generation_manifest','request','source','approval'):
        verify_record(bindings[name])
    original=copy.deepcopy(manifest)
    for name in ('generation_result','generation_manifest'): original['bindings'].pop(name)
    if read_json(bindings['generation_manifest']['path'])!=original:
        raise ValueError('published manifest differs from immutable generated manifest')
    receipt=read_json(bindings['generation_result']['path'])
    if bindings['source']!=receipt['source'] or receipt['recipe']!=RECIPE or manifest['settings']['recipe']!=RECIPE:
        raise ValueError('generation immutable source/recipe binding differs')
    request=read_json(bindings['request']['path'])
    if receipt['status']!='complete' or receipt['request']!=bindings['request'] or request['record_kind']!='actual':
        raise ValueError('actual package lacks completed actual generation')
    group=next((key for key,record in receipt['manifests'].items() if record==bindings['generation_manifest']),None)
    if group not in GROUPS or manifest['id']!=request['id']+'-'+group: raise ValueError('generation group identity mismatch')
    for name in ('config','inputs','amendment','approval'):
        if bindings[name]!=request['bindings'][name]: raise ValueError('generation '+name+' differs')
        verify_record(bindings[name])
    ledger=Ledger(safe_path(request['local'])/'ledger.jsonl',read_json(bindings['config']['path']))
    live=ledger.events()
    if not any(e['event']=='cpu_preparation_charge' and e['evidence']==bindings['generation_result'] for e in live):
        raise ValueError('generation receipt lacks elapsed CPU charge')
    prefix_record=file_record(Path(bindings['request']['path']).parent/'ledger-prefix.json')
    prefix=read_json(prefix_record['path'])['events']
    if live[:len(prefix)]!=prefix: raise ValueError('generation ledger prefix differs from live chain')
    frames=(request['depth_frames'] if group=='depth' else request.get('motion_frames',request['reconstruction_frames'])
            if group=='motion' else request['reconstruction_frames'])
    role='selection' if group=='depth' else 'reconstruction'
    expected=[_selection(c,[f],role) for c in request['cameras'] for f in frames]
    if group!='depth' and len(frames)>1:
        for camera in request['cameras']:
            expected.append(_selection(camera,frames,role,'clip'))
            contiguous=[frames[0]]
            for frame in frames[1:]:
                if frame!=contiguous[-1]+1: break
                contiguous.append(frame)
            if 1<len(contiguous)<len(frames):expected.append(_selection(camera,contiguous,role,'clip'))
    if manifest['selections']!=expected: raise ValueError('selection differs from frozen generation request')
    if manifest['settings']['detail_regions']!=request.get('detail_regions',[]) or manifest['settings']['depth_range_metres']!=request['depth_range_metres']:
        raise ValueError('presentation settings differ from frozen generation request')
    if [c['id'] for c in manifest['candidates']]!=['source-rgb',*GROUPS[group],'final-render']:
        raise ValueError('generated candidate membership differs')
    accepted=read_json(bindings['inputs']['path']);inputs=accepted['rgb']+accepted['depth']
    selections={s['id']:s for s in expected}
    for candidate in manifest['candidates']:
        if deadline is not None: _check(deadline)
        component=candidate['id'];control=component=='source-rgb'
        stage='accepted input' if control else 'downstream training/rendering' if component=='final-render' else group+' component diagnostic'
        output_type='reference' if control else 'final-render' if component=='final-render' else 'component'
        if candidate['stage']!=stage or candidate['output_type']!=output_type or candidate['is_control']!=(control or component.endswith('0')):
            raise ValueError('candidate stage/output/control differs from generation')
        if component=='final-render' and (candidate['status']!='unavailable' or candidate['media']):
            raise ValueError('ungenerated final render cannot become available')
        if candidate['status']!='available':continue
        provenance=candidate['provenance'];result=None
        if provenance['configuration']!=bindings['config']: raise ValueError('candidate configuration differs')
        if control:
            if provenance['source_result']!=bindings['inputs'] or provenance['ledger_outcome']!=prefix_record:
                raise ValueError('source control provenance differs')
        else:
            verify_record(provenance['source_result']);verify_record(provenance['ledger_outcome'])
            outcome=read_json(provenance['ledger_outcome']['path']);result=read_json(provenance['source_result']['path'])
            if outcome not in prefix or outcome.get('event')!='finish' or outcome.get('status')!='complete' or outcome.get('result')!=provenance['source_result']:
                raise ValueError('candidate lacks successful bound finish')
            if result['status']!='complete' or result['component']!=component: raise ValueError('candidate result identity differs')
            verify_record(result['configuration']);worker=read_json(result['configuration']['path'])
            if worker['component']!=component or worker['configuration']!=bindings['config'] or worker['inputs']!=bindings['inputs']:
                raise ValueError('native worker configuration/input differs')
        for media in candidate['media']:
            if deadline is not None: _check(deadline)
            selection=selections[media['selection_id']]
            verify_record(media['record'])
            if media['kind']!='frame':
                source_images=[]
                for frame in selection['frame_ids']:
                    match=next((m for m in candidate['media'] if m['kind']=='frame' and m['frame_ids']==[frame] and m['camera_id']==selection['camera_id']),None)
                    if match is None: raise ValueError('video lacks exact generated frame lineage')
                    source_images.append(match['record'])
                if media['source_images']!=source_images: raise ValueError('video source lineage differs')
                continue
            branch='depth' if group=='depth' else 'reconstruction'
            source=next((r for r in inputs if r['identity']['branch']==branch and
                str(r['identity']['camera'])==selection['camera_id'] and r['identity']['frame']==selection['frame_ids'][0]),None)
            if source is None or media['camera_id']!=selection['camera_id'] or media['source_input']!=source['rgb']:
                raise ValueError('media camera/source input differs')
            image=_image(source['rgb'])
            if not control:
                if group=='neighbors':
                    row=_native_row(result,source,group)
                else:
                    row=_native_row(result,source,group)
                    if row is not None and (row['source_rgb_sha256']!=source['rgb']['sha256'] or row['K']!=source['K'] or row['grid']!=source['grid']):
                        raise ValueError('native row geometry/input differs')
                if row is None or media['source_row_sha256']!=object_hash(row) or media['source_identity']!=source['identity']:
                    raise ValueError('media native row binding differs')
                if media['native_identity']!=row.get('identity',{'reference':row.get('reference')}):
                    raise ValueError('media native pair/reference context differs')
                image=_overlay(image,row,group,request['depth_range_metres'])
            if not np.array_equal(np.asarray(image),np.asarray(_image(media['record']))):
                raise ValueError('generated PNG differs from declared deterministic source recipe')
    return {'actual_lineage':'verified'}


def publish_generation(manifest_record, output, *, ledger=None, publisher=None):
    """Charge bounded CPU lineage validation and viewer publication as preparation."""
    verify_record(manifest_record);manifest=read_json(manifest_record['path'])
    request=read_json(manifest['bindings']['request']['path'])
    ledger=ledger or Ledger(safe_path(request['local'])/'ledger.jsonl',load())
    output=safe_path(output);receipt_path=output.parent/(output.name+'-cpu-receipt.json')
    if output.exists() or receipt_path.exists():raise FileExistsError(str(output))
    _request(request,ledger)
    guard=_storage_guard(request,ledger,[output,receipt_path])
    manifest['bindings'].update(generation_manifest=manifest_record,
        generation_result=file_record(Path(manifest_record['path']).parent.parent/'result.json'))
    if publisher is None:
        from .qualitative_package import publish
        publisher=publish
    start=time.monotonic();deadline=start+request['max_seconds']
    token=_PUBLICATION_DEADLINE.set(deadline);failure=None;result=None
    storage_token=_STORAGE_GUARD.set(guard)
    try:
        result=publisher(manifest,output,deadline=deadline)
        _check(deadline)
    except Exception as error:failure=error
    finally:
        _PUBLICATION_DEADLINE.reset(token)
        _STORAGE_GUARD.reset(storage_token)
    receipt=dict(schema='plan067-qualitative-publication-result/v1',status='failed' if failure else 'complete',
        elapsed_seconds=time.monotonic()-start,generation_manifest=manifest_record,result=result,
        error=str(failure) if failure else None,scope='CPU qualitative input artifact validation/publication')
    write_json(receipt_path,receipt);ledger.charge_cpu_preparation(receipt['elapsed_seconds'],file_record(receipt_path))
    if failure:raise failure
    return dict(result, cpu_receipt=file_record(receipt_path))
