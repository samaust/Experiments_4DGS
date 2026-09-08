#!/usr/bin/env python3
"""Audit the fixed final SelfCap profile; stdlib/Pillow only, no model execution."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

METHODS = ('stg-lite', 'stg-full', 'freetimegs', 'atgs')
PROFILE = '.local/data/selfcap/dance1-processed-20260906'
RUNS = '.local/runs'
FRAMES = list(range(4120, 4180))
CROPS = {'hair_motion': [330,300,1020,820], 'face_hair_boundary': [620,470,900,750],
         'hands_body_boundary': [610,830,1030,1061], 'static_book_text': [850,350,1030,515]}

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def close(a, b):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-9

def membership(values, expected):
    return len(values) == len(expected) and len(set(values)) == len(values) and set(values) == set(expected)

def validate_times(camera, timing, fps):
    frames = camera['frames']
    return all(close(f['timestamp_seconds'], f['frame_id']/fps-camera['synchronization_offset_seconds'])
               and close(f['normalized_time'], (f['timestamp_seconds']-timing['origin_seconds'])/timing['duration_seconds'])
               for f in frames) and all(a['timestamp_seconds'] < b['timestamp_seconds'] and a['normalized_time'] < b['normalized_time']
                                       for a,b in zip(frames,frames[1:]))

def metric_means(metrics):
    return {k:sum(f[k] for f in metrics['per_frame'])/len(metrics['per_frame']) for k in metrics['aggregate']}

def validate_sweep(observed, expected):
    return observed == expected and expected.get('start_camera') == '0015' and expected.get('end_camera') == '0014' and expected.get('intrinsics_camera') == '0015' and expected.get('frame_id') == 4150 and len(expected.get('poses', [])) == 20

def completed_reload_stages(evaluation, commands, method):
    required_script = 'render-' + ('stg' if method.startswith('stg') else method) + '-manifest.py'
    return evaluation.get('status') == 'completed' and all(
        any(stage.get('label') == label and stage.get('status') == 'completed'
            and stage.get('exit_code') == 0
            and required_script in [Path(x).name for x in stage.get('command', [])]
            for stage in commands) for label in ('reload-a', 'reload-b'))

def new_destinations(root, output, assets):
    paths = [Path(output).resolve(), Path(assets).resolve()]
    for p in paths:
        if p.exists():
            raise ValueError('refusing existing output: '+str(p))
        for protected in [root/'.local/data', *[root/RUNS/f'{m}-selfcap-final{suffix}-20260906' for m in METHODS for suffix in ('','-evaluation','-measurement')]]:
            if p == protected or protected in p.parents or p in protected.parents:
                raise ValueError('output overlaps an input: '+str(p))
    if paths[0] in paths[1].parents or paths[1] in paths[0].parents or paths[0] == paths[1]:
        raise ValueError('output destinations overlap')
    return paths

class Audit:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.files = {}; self.checks = []; self.records = {}
        self.mh=None; self.manifest={}; self.frame_map={}; self.train=set()
    def path(self,p):
        p=Path(p)
        if 'prompts' in p.parts: raise ValueError('forbidden path')
        return p if p.is_absolute() else self.root/p
    def label(self,p):
        return os.path.relpath(self.path(p),self.root)
    def check(self, key, ok, expected=None, observed=None, reason='', criteria=('SC-05',)):
        self.checks.append(dict(id=key,criteria=list(criteria),status='unavailable' if ok is None else 'passed' if ok else 'failed',expected=expected,observed=observed,reason=reason))
        return ok
    def file(self,p,sha=None,size=None,image_size=None):
        p=self.path(p); key=self.label(p)
        if key not in self.files:
            if not p.is_file():
                self.files[key]=dict(path=key,present=False)
            else:
                self.files[key]=dict(path=key,present=True,sha256=digest(p),bytes=p.stat().st_size)
        item=self.files[key]
        self.check('file:'+key, item['present'] and (sha is None or item.get('sha256')==sha) and (size is None or item.get('bytes')==size),dict(sha256=sha,bytes=size),item)
        if image_size and item['present']:
            with Image.open(p) as im:
                self.check('image:'+key,im.mode=='RGB' and list(im.size)==list(image_size),dict(mode='RGB',size=image_size),dict(mode=im.mode,size=list(im.size)))
        return item
    def read(self,p):
        item=self.file(p)
        if not item['present']: return {}
        return json.loads(self.path(p).read_text())
    def source(self,p,sha):
        item=self.file(p,sha)
        if item.get('sha256') == sha: return
        # Read-only retained git object search; never restore or change a checkout.
        matches=[]
        for base in [self.root, self.root/'.local/SpacetimeGaussians',self.root/'.local/ATGS',self.root/'.local/FreeTimeGsVanilla']:
            path=self.path(p)
            if base not in path.parents or not (base/'.git').exists(): continue
            rel=str(path.relative_to(base))
            result=subprocess.run(['git','log','--format=%H','--',rel],cwd=base,capture_output=True,text=True,check=True)
            for revision in result.stdout.splitlines():
                blob=subprocess.run(['git','show',revision+':'+rel],cwd=base,capture_output=True)
                if blob.returncode==0 and hashlib.sha256(blob.stdout).hexdigest()==sha:
                    matches.append(dict(repository=self.label(base),revision=revision,path=rel,sha256=sha));break
        self.check('historical-source:'+self.label(p),bool(matches),sha,matches,'Current bytes differ; matching git object is evidence only, not restored.')
    def inputs(self):
        manifest=self.read(PROFILE+'/manifest.json'); self.manifest=manifest
        if not manifest:return
        mh=self.files[PROFILE+'/manifest.json']['sha256']; self.mh=mh
        cameras=manifest['cameras']; self.train={c['id'] for c in cameras if c['split']=='train'}
        self.check('profile',manifest['frames']==[4120,4180] and manifest['source_fps']==60 and membership([c['id'] for c in cameras],[f'{i:04d}' for i in range(24)]) and len(self.train)==23 and [c['id'] for c in cameras if c['split']=='test']==['0015'],criteria=('SC-01',))
        self.frame_map={(c['id'],f['frame_id']):f for c in cameras for f in c['frames']}
        sync=self.read('.local/data/selfcap/hair-calib/optimized/sync.json')
        for name,sha in manifest['calibration'].items():self.file('.local/data/selfcap/hair-calib/optimized/'+name,sha)
        self.file('scripts/prepare-selfcap.py')
        offsets=[c['synchronization_offset_seconds'] for c in cameras]
        self.check('time-normalization',close(manifest['time']['origin_seconds'],4120/60-max(offsets)) and close(manifest['time']['duration_seconds'],1+max(offsets)-min(offsets)),reason='prepare-selfcap.py: origin=start/fps-max(offsets); duration=(end-start)/fps+max-min.')
        self.videos=[]
        for c in cameras:
            self.check('camera-membership:'+c['id'],membership([f['frame_id'] for f in c['frames']],FRAMES))
            self.check('camera-time:'+c['id'],validate_times(c,manifest['time'],60) and c['synchronization_offset_seconds']==sync.get(c['id']))
            self.videos.append(dict(path=self.label(c['source_video']),recorded_sha256=c['source_video_sha256'],present=self.path(c['source_video']).is_file(),rehash=False))
            for f in c['frames']:self.file(Path(PROFILE)/f['path'],f['sha256'],image_size=[c['width'],c['height']])
        self.check('heldout-dimensions',[(c['width'],c['height']) for c in cameras if c['id']=='0015']==[(1890,1061)])
        sparse='.local/data/selfcap/dance1-initialization-20260906'
        for name in ('inputs.json','result.json'):
            record=self.read(sparse+'/'+name);self.initialization_inputs(record,4150,name)
        self.file(sparse+'/initialization.ply')
        dense='.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906'
        d=self.read(dense+'/result.json');self.file(dense+'/initialization.npz',d.get('archive_sha256'))
        self.check('dense-cloud-membership',membership([c['frame_id'] for c in d.get('clouds',[])],[i+j for i in range(4120,4180,5) for j in (0,1)]))
        for c in d.get('clouds',[]):
            directory=self.path(c['directory']);r=self.read(directory/'result.json');self.file(directory/'result.json',c['evidence_sha256'])
            self.file(directory/'cloud.npz',c['archive_sha256']);self.initialization_inputs(r,c['frame_id'],'dense-'+str(c['frame_id']))
    def initialization_inputs(self,r,frame,key):
        records=r.get('inputs',[])
        ok=r.get('manifest_sha256')==self.mh and membership([f['camera_id'] for f in records],self.train)
        for f in records:
            original=self.frame_map.get((f['camera_id'],frame),{})
            ok=ok and all(f.get(k)==original.get(k) for k in ('frame_id','path','sha256','timestamp_seconds','normalized_time'))
        self.check('initialization:'+key,ok,reason='Training-camera membership and exact manifest image/time binding.',criteria=('SC-01',))
    def method(self,m):
        run=Path(RUNS)/f'{m}-selfcap-final-20260906'; ev=Path(RUNS)/f'{m}-selfcap-final-evaluation-20260906'
        e=self.read(ev/'evaluation.json');commands=self.read(ev/'commands.json');p=self.read(run/'provenance.json');config=self.read(run/'training-config.json')
        records={name:self.read(run/name) for name in ('result.json','worker-result.json')}
        for name in ('checkpoints.json','adapted_train.py','cfg_args'):
            if self.path(run/name).exists():self.file(run/name)
        measure=self.read(Path(RUNS)/f'{m}-selfcap-final-measurement-20260906/measurement.json')
        self.read(Path(RUNS)/f'{m}-selfcap-final-measurement-20260906/command.json')
        self.check(m+':manifest',e.get('manifest_sha256')==self.mh and (p.get('manifest_sha256')==self.mh or p.get('files',{}).get(str(self.path(PROFILE+'/manifest.json')))==self.mh))
        self.check(m+':stages',completed_reload_stages(e,commands,m),observed=commands,reason='Completed saved commands; offline isolation is checked separately from argv.')
        renders=[self.read(ev/reload/'render.json') for reload in ('reload-a','reload-b')]
        model=run/('checkpoint-061008-011/bundle.json' if m=='atgs' else 'checkpoint-042061.pt' if m=='freetimegs' else 'checkpoint.pt')
        if m=='atgs':
            bundle=self.read(model);self.check('atgs:bundle',len(bundle.get('files',{}))==11 and all(r.get('bundle')==bundle for r in renders))
            for f,info in bundle.get('files',{}).items():self.file(model.parent/f,info['sha256'],info['bytes'])
            self.check('atgs:component-total',sum(x['bytes'] for x in bundle['files'].values())==e['checkpoint_bytes'])
            self.check('atgs:updates',bundle['update_count']==20336)
        else:
            sha=e.get('checkpoint_sha256') or renders[0].get('bundle',{}).get('checkpoint_sha256')
            self.check(m+':required-checkpoint-hash',isinstance(sha,str) and len(sha)==64,observed=sha)
            self.file(model,sha,e['checkpoint_bytes'])
            self.check(m+':model-records',all((r.get('checkpoint_sha256') or r.get('bundle',{}).get('checkpoint_sha256'))==sha and r.get('checkpoint_bytes')==e['checkpoint_bytes'] for r in renders),observed=sha)
        self.check(m+':progress',e['iteration']=={'stg-lite':30000,'stg-full':30000,'freetimegs':42061,'atgs':61008}[m] and e['incomplete_training']==(m in ('freetimegs','atgs')),observed=dict(iteration=e['iteration'],incomplete=e['incomplete_training']))
        for ri,r in enumerate(renders):
            reload=('reload-a','reload-b')[ri];iso=r.get('network_isolation',{})
            if isinstance(iso,str):iso=json.loads(iso)
            self.check(m+':'+reload+':offline',iso.get('probes',{}).get('AF_INET')=='EPERM (expected offline self-test)' and iso.get('probes',{}).get('AF_INET6')=='EPERM (expected offline self-test)',observed=iso,reason='Historical process record; no new reload.')
            self.check(m+':'+reload+':sweep',validate_sweep(r.get('sweep'),self.manifest['sweep']) and self.manifest['sweep']['normalized_time']==self.frame_map[('0015',4150)]['normalized_time'])
            self.check(m+':'+reload+':frame-membership',membership([(f['camera'],f['frame_id']) for f in r['frames']],[('0015',f) for f in FRAMES]))
            for f in r['frames']:
                original=self.frame_map.get((f['camera'],f['frame_id']),{})
                self.check(m+':'+reload+':time:'+str(f['frame_id']),f['normalized_time']==original.get('normalized_time') and f['path']==original.get('path'))
                self.file(ev/reload/f['path'],f['sha256'],image_size=[1890,1061])
            if 'sweep_frames' in r:
                self.check(m+':'+reload+':sweep-membership',membership([f['index'] for f in r['sweep_frames']],range(20)))
                for f in r['sweep_frames']:
                    self.check(m+':'+reload+':sweep-time:'+str(f['index']),f['normalized_time']==self.manifest['sweep']['normalized_time'] and f['path']==f"sweep/{f['index']:05d}.png")
                    self.file(ev/reload/f['path'],f['sha256'],image_size=[1890,1061])
        for kind,folder,names in [('heldout','images/0015',[f'{f:06d}.png' for f in FRAMES]),('sweep','sweep',[f'{i:05d}.png' for i in range(20)])]:
            comp=self.read(ev/f'compare-{kind}.json')
            self.check(m+':'+kind+':comparison-membership',membership([f['filename'] for f in comp['per_frame']],names))
            for reload in ('reload-a','reload-b'):
                self.check(m+':'+reload+':'+kind+':files',membership([x.name for x in self.path(ev/reload/folder).glob('*.png')],names))
            for f in comp['per_frame']:
                a=self.file(ev/'reload-a'/folder/f['filename'],f['first_sha256'],image_size=[1890,1061]);b=self.file(ev/'reload-b'/folder/f['filename'],f['second_sha256'],image_size=[1890,1061])
                self.check(m+':'+kind+':equality:'+f['filename'],a.get('sha256')==b.get('sha256')==f['first_sha256']==f['second_sha256'])
        if m in ('freetimegs','atgs'):
            self.check(m+':historical-floats',all([f['float_sha256'] for f in renders[0][k]]==[f['float_sha256'] for f in renders[1][k]] for k in ('frames','sweep_frames')),reason='Saved raw-float hashes only; raw arrays not recomputed.')
        for path,sha in p.get('files',{}).items():self.source(path,sha)
        for name,sha in e.get('helpers_sha256',{}).items():self.source('scripts/'+name,sha)
        for name,sha in config.get('adapters',{}).items():self.source('scripts/'+name,sha)
        for name,sha in config.get('sources',{}).items():self.source('scripts/'+name[8:] if name.startswith('adapter/') else '.local/ATGS/'+name,sha)
        key='configuration_sha256' if m=='freetimegs' else 'config_sha256'
        if key in p:self.check(m+':configuration',hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()==p[key])
        if m.startswith('stg'):
            self.check(m+':historical-native-binaries',None,reason='STG saved provenance has no historical extension-binary attestation.')
        else:
            self.source('scripts/render-'+m+'-manifest.py',renders[0]['renderer_sha256'])
            self.check(m+':runtime-across-reloads',renders[0]['runtime']==renders[1]['runtime'],observed=renders[0]['runtime'])
            self.runtime(m,renders[0]['runtime'],config,p)
            if m=='freetimegs':self.freetime_source(renders,config,p)
        metrics=self.read(ev/'metrics.json');means=metric_means(metrics)
        self.check(m+':metric-membership',membership([f['frame'] for f in metrics['per_frame']],[f'{i:06d}' for i in FRAMES]) and metrics['count']==60)
        self.check(m+':metric-averages',all(close(v,metrics['aggregate'][k]) and close(v,e['metrics'][k]) for k,v in means.items()),expected=metrics['aggregate'],observed=means)
        benchmark=e['benchmark'];self.check(m+':benchmark',benchmark['warmups']==10 and benchmark['timed_renders']==len(benchmark['seconds'])==100 and all(t>0 for t in benchmark['seconds']) and close(100/sum(benchmark['seconds']),benchmark['fps']) and benchmark['camera']=='0015' and benchmark['frame_id']==4150 and benchmark['dimensions']==[1890,1061],observed=benchmark)
        self.records[m]=dict(model=self.label(model),evaluation=self.label(ev),provenance=p,configuration=config,training_records=records,measurement=measure,metrics=metrics,benchmark=benchmark,checkpoint_bytes=e['checkpoint_bytes'],commands=commands)
    def runtime(self,m,runtime,config,p):
        site=self.path('.local/envs/'+m+'/lib/python3.14/site-packages')
        if m=='atgs':
            for name,info in runtime['extensions'].items():self.file(site/name,info['sha256'],info['bytes'])
            packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions(path=[str(site)])}
            for name,version in runtime['packages'].items():self.check('atgs:package:'+name,packages.get(name)==version,version,packages.get(name))
            tree=ast.parse(self.path('.local/ATGS/train_long.py').read_text());names=('optimizer_parameters','sanitize_accumulated_gradients','average_accumulated_gradients','clip_accumulated_gradients','step_accumulated_gradients');functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
            sha=hashlib.sha256(ast.dump(ast.Module(body=[functions[n] for n in names],type_ignores=[])).encode()).hexdigest();self.check('atgs:helper-AST',sha==p['helper_ast_sha256'],p['helper_ast_sha256'],sha)
            rev=subprocess.run(['git','rev-parse','HEAD'],cwd=self.path('.local/ATGS'),capture_output=True,text=True,check=True).stdout.strip();self.check('atgs:revision',rev==p['source_revision'],p['source_revision'],rev)
        else:
            # Exact installed paths indexed by the retained runtime record.
            for key,value in runtime.items():
                if isinstance(value,dict) and 'sha256' in value and 'path' in value:self.file(value['path'],value['sha256'])
            for key,sha in config['binaries'].items():
                paths=list(site.glob('gsplat/csrc*.so' if key=='gsplat' else 'fused_ssim_cuda*.so'))
                self.check('freetimegs:binary-path:'+key,len(paths)==1,observed=[self.label(x) for x in paths])
                for path in paths:self.file(path,sha)
    def freetime_source(self,renders,config,provenance):
        bundle=renders[0]['bundle'];self.check('freetimegs:bundle',bundle==renders[1]['bundle'] and bundle['provenance']==provenance)
        identities=bundle['source_digests'];base=self.path('.local/FreeTimeGsVanilla')
        trainer=base/'src/simple_trainer_freetime_4d_pure_relocation.py';self.source(trainer,identities['source_sha256'])
        tree=ast.parse(trainer.read_text());runner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FreeTime4DRunner')
        def module_hash(body):return hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[])).encode()).hexdigest()
        names={'compute_temporal_opacity','compute_positions_at_time','compute_4d_regularization','rasterize_splats'}
        self.check('freetimegs:render-AST',module_hash([n for n in runner.body if isinstance(n,ast.FunctionDef) and n.name in names])==identities['render'])
        selected=[]
        for path,names in [(base/'src/utils.py',{'knn','rgb_to_sh'}),(trainer,{'create_splats_with_optimizers_4d'})]:
            self.file(path);selected.extend(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names)
        selected.insert(0,ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0))
        self.check('freetimegs:initializer-AST',module_hash(selected)==identities['initializer'])
        normalize=base/'datasets/normalize.py';source=config['normalization']['source'];self.source(normalize,source['source_sha256'])
        names={'similarity_from_cameras','align_principle_axes','transform_points','transform_cameras'}
        self.check('freetimegs:normalization-AST',module_hash([n for n in ast.parse(normalize.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names])==source['normalization_ast_sha256'])
        # Reconstruct identity only: never compile/execute native statements.
        cfg=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Config')
        preset=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='configs' for t in n.targets))
        methods=[n for n in runner.body if isinstance(n,ast.FunctionDef) and n.name in {'relocate_gaussians','prune_gaussians','budget_prune_gaussians'}]
        train=next(n for n in runner.body if isinstance(n,ast.FunctionDef) and n.name=='train');loop=next(n for n in train.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='step')
        def assignment(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
        start=next(i for i,n in enumerate(loop.body) if assignment(n,'progress'));stop=next(i for i,n in enumerate(loop.body) if assignment(n,'phase'))
        helper=ast.parse(self.path('scripts/freetimegs_training.py').read_text())
        fragments=[n.args[0].value for n in ast.walk(helper) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='ast' and n.func.attr=='parse' and n.args and isinstance(n.args[0],ast.Constant)]
        wrapper=ast.parse(next(x for x in fragments if 'def training_step' in x)).body[0]
        wrapper.body.extend(loop.body[start:stop]);wrapper.body.extend(ast.parse(next(x for x in fragments if 'return dict(loss' in x)).body)
        self.check('freetimegs:training-AST',module_hash([cfg,preset,*methods,wrapper])==identities['training_ast_sha256'])
        norm=config['normalization'];dense='.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906'
        self.file(dense+'/result.json',norm['initialization_report_sha256']);self.file(dense+'/initialization.npz',norm['initialization_sha256'])
        ref=norm['reference_cloud'];self.file(Path(ref['directory'])/'initialization.ply',ref['ply_sha256']);self.file(Path(ref['directory'])/'result.json',ref['evidence_sha256'])
    def budget(self):
        ledger=self.read(RUNS+'/plan-004-training-budget.json');charges=defaultdict(float)
        for a in ledger['attempts']:
            charges[a['key'][0]]+=a.get('charged_seconds',0)
            self.check('budget-attempt:'+str(len(self.checks)),a['status']!='running' and a.get('overrun_seconds',0)==0 and a.get('charged_seconds',0)<=a['reserved_seconds'],observed=a)
        total=sum(charges.values());self.check('budget-total',abs(total-22523.417254)<0.000001,22523.417254,total)
        self.check('budget-allocations',all(v<=7200 for v in charges.values()) and total<=86400,observed=dict(charges))
        self.charges=dict(charges)
        protocols=[v['metrics']['protocol'] for v in self.records.values()];self.check('shared-metric-protocol',all(p==protocols[0] for p in protocols),observed=protocols[0])
        comparisons=[('stg-selfcap-final-comparison-20260906.json','stg-lite','stg-full')]+[(f'{m}-vs-{b}-selfcap-final-20260906.json','stg-'+b,m) for m in ('freetimegs','atgs') for b in ('lite','full')]
        for name,a,b in comparisons:
            d=self.read(Path(RUNS)/name);expected={k:self.records[b]['metrics']['aggregate'][k]-v for k,v in self.records[a]['metrics']['aggregate'].items()}
            self.check('delta:'+name,all(close(v,d['delta_second_minus_first'][k]) for k,v in expected.items()),expected,d['delta_second_minus_first'])


def presentation(a,output,assets):
    crops=a.read('configs/detail-crops.selfcap-dance1.json')
    if not a.check('crop-config',crops['crops']==CROPS and crops['selection_frame']==4150 and crops['selection_image_sha256']==a.frame_map[('0015',4150)]['sha256']):return None
    names=['reference',*METHODS];windows=[list(range(4120,4123)),list(range(4148,4153)),list(range(4177,4180))]
    index=dict(schema='selfcap-inspection/v1',methods=names,crops=CROPS,frames=[],sheets=[],sweep=a.manifest['sweep'],note='Saved PNG presentation, not fresh rendering. Sheets downsample only when tile width exceeds 480 pixels; HTML crops use original pixels.')
    def source(name,frame,sweep=False):
        return a.path(Path(PROFILE)/f'images/0015/{frame:06d}.png' if name=='reference' else Path(RUNS)/f'{name}-selfcap-final-evaluation-20260906/reload-a'/('sweep/'+f'{frame:05d}.png' if sweep else f'images/0015/{frame:06d}.png'))
    for frame in FRAMES:
        record=a.frame_map[('0015',frame)]
        index['frames'].append(dict(frame_id=frame,timestamp_seconds=record['timestamp_seconds'],normalized_time=record['normalized_time'],sources={n:dict(path=os.path.relpath(source(n,frame),output),sha256=a.files[a.label(source(n,frame))]['sha256']) for n in names}))
    sheets=assets/'sheets';sheets.mkdir(parents=True)
    def sheet(frames,crop=None,sweep=False):
        labels=names[1:] if sweep else names;bounds=CROPS[crop] if crop else [0,0,1890,1061];w,h=bounds[2]-bounds[0],bounds[3]-bounds[1];scale=min(1,480/w);tw,th=round(w*scale),round(h*scale)
        im=Image.new('RGB',(len(frames)*tw+115,len(labels)*(th+25)), 'white');draw=ImageDraw.Draw(im);sources=[]
        for y,n in enumerate(labels):
            draw.text((2,y*(th+25)+20),n,fill='black')
            for x,frame in enumerate(frames):
                p=source(n,frame,sweep)
                with Image.open(p) as pic:tile=pic.crop(bounds).resize((tw,th),Image.Resampling.LANCZOS)
                im.paste(tile,(115+x*tw,y*(th+25)+25));draw.text((115+x*tw,y*(th+25)+4),str(frame),fill='black');sources.append(dict(method=n,frame_or_pose=frame,path=os.path.relpath(p,output),sha256=a.files[a.label(p)]['sha256']))
        name=('sweep' if sweep else crop or 'full')+'-'+str(frames[0])+'-'+str(frames[-1])+'.png';path=sheets/name;im.save(path)
        index['sheets'].append(dict(path=os.path.relpath(path,output),sha256=digest(path),frames_or_poses=frames,crop=crop,bounds=bounds,scale=scale,sources=sources))
    sheet([4120,4150,4179])
    for window in windows:
        sheet(window)
        for crop in CROPS:sheet(window,crop)
    sheet([0,10,19],sweep=True)
    index['sweep_sources']=[dict(index=i,normalized_time=a.manifest['sweep']['normalized_time'],sources={n:dict(path=os.path.relpath(source(n,i,True),output),sha256=a.files[a.label(source(n,i,True))]['sha256']) for n in METHODS}) for i in range(20)]
    (output/'inspection.json').write_text(json.dumps(index,indent=2)+'\n')
    page='''<!doctype html><meta charset="utf-8"><title>SelfCap saved evidence</title><style>body{font:16px sans-serif}#views{display:flex;gap:8px;align-items:start;overflow:auto}.view{flex:none}canvas{border:1px solid #bbb}input{width:400px}</style><h1>Saved SelfCap evidence</h1><p>Original saved PNGs; fixed crops. Zoom changes display only. Sweep interior poses have no ground truth. No new render or metrics.</p><label>Mode <select id="mode"><option>heldout</option><option>sweep</option></select></label><label>Frame/pose <input id="frame" type="range" min="0" max="59" value="0"></label><select id="crop"><option value="">full</option></select><label>Zoom <select id="zoom"><option>0.25</option><option selected>0.5</option><option>1</option><option>2</option></select></label><p id="time"></p><div id="views"></div><h2>Inspection sheets</h2>'''
    page+=''.join('<p><a href="'+html.escape(s['path'])+'">'+html.escape(Path(s['path']).name)+'</a></p>' for s in index['sheets'])
    page+='<script>const data='+json.dumps(index)+';'+'''const mode=document.querySelector('#mode'),slider=document.querySelector('#frame'),crop=document.querySelector('#crop'),zoom=document.querySelector('#zoom');for(const n of Object.keys(data.crops)){let o=document.createElement('option');o.value=n;o.textContent=n;crop.append(o)}function update(){const sweep=mode.value==='sweep';slider.max=sweep?19:59;const f=(sweep?data.sweep_sources:data.frames)[Math.min(+slider.value,+slider.max)];document.querySelector('#time').textContent=sweep?`Pose ${f.index}, normalized time ${f.normalized_time}, midpoint frame 4150`:`Frame ${f.frame_id}, timestamp_seconds ${f.timestamp_seconds}, normalized_time ${f.normalized_time}`;let views=document.querySelector('#views');views.replaceChildren();for(const [name,s]of Object.entries(f.sources)){let d=document.createElement('div');d.className='view';let a=document.createElement('a');a.href=s.path;a.textContent=name+' original';d.append(a,document.createElement('br'));let c=document.createElement('canvas');d.append(c);views.append(d);let image=new Image();image.onload=()=>{const b=data.crops[crop.value]||[0,0,image.width,image.height];c.width=b[2]-b[0];c.height=b[3]-b[1];c.style.width=c.width*(+zoom.value)+'px';c.style.height=c.height*(+zoom.value)+'px';c.getContext('2d').drawImage(image,b[0],b[1],c.width,c.height,0,0,c.width,c.height)};image.src=s.path}}for(const el of [mode,slider,crop,zoom])el.oninput=update;update();</script>'''
    (output/'inspection.html').write_text(page)
    return index

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path('.'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--assets-output',type=Path,required=True);args=parser.parse_args()
    root=args.root.resolve();output,assets=new_destinations(root,args.output,args.assets_output);output.mkdir(parents=True);assets.mkdir(parents=True)
    a=Audit(root)
    for label,work in [('inputs',a.inputs),*[(m,lambda m=m:a.method(m)) for m in METHODS],('budget',a.budget)]:
        try:work()
        except (KeyError,ValueError,FileNotFoundError,ZeroDivisionError,IndexError,AttributeError,TypeError) as exc:a.check('incomplete:'+label,False,reason=repr(exc))
    image_failures=[c for c in a.checks if c['status']=='failed' and (c['id'].startswith(('image:','camera-','profile','heldout','incomplete:')) or '.png' in c['id'] or ':time:' in c['id'] or ':sweep' in c['id'])]
    if not image_failures:
        try:presentation(a,output,assets)
        except (KeyError,ValueError,FileNotFoundError,TypeError) as exc:a.check('presentation',False,reason=repr(exc))
    else:a.check('presentation',None,reason='Image binding failed; do not present unverified evidence.')
    report=dict(schema='selfcap-evidence-audit/v1',command=sys.argv,auditor_sha256=digest(__file__),scope='Retained files and historical records only; no model deserialization, new reload, raw-float recomputation, metric inference, training or network.',checks=a.checks,files=list(a.files.values()),methods=a.records,source_videos=getattr(a,'videos',[]),charges=getattr(a,'charges',{}))
    (output/'audit.json').write_text(json.dumps(report,indent=2)+'\n');counts=Counter(c['status'] for c in a.checks)
    lines=['# Retained SelfCap evidence audit','',report['scope'],'',str(dict(counts)),'','[Machine-readable checks, file hashes and records](audit.json). [Saved-image inspection](inspection.html).','','Failed/unavailable checks:','']
    lines += [f"- `{c['id']}`: **{c['status']}**. {c['reason']} Expected `{c['expected']}`; observed `{c['observed']}`." for c in a.checks if c['status']!='passed']
    (output/'audit.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(counts)));return 1 if counts['failed'] else 0
if __name__=='__main__':sys.exit(main())
