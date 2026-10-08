"""Camera preparation and lazy bindings for future admitted FreeTimeGS workers.

This low-level runtime is not a dispatcher. Its GPU methods require an externally
admitted, supervised fresh worker process. Fixture workers reject this runtime.
"""
import copy
import importlib
from pathlib import Path
import sys
import numpy as np

from .extended_final_render_contract import parse_request, validate_scene_bindings
from .files import file_record, object_hash, read_json, safe_path, verify_record
from .final_render_adapter import prepare_model_input, validate_model_input
from .final_render_inventory import validate_inventory


def prepare_camera(request, camera, frame):
    """Prepare one native camera without importing Torch or loading an image."""
    if type(camera) is not int or camera not in range(34) or type(frame) is not int or frame not in range(50):
        raise ValueError('original camera/frame required')
    request = parse_request(request)
    validate_scene_bindings(request)
    manifest = read_json(request['bindings']['scene_manifest']['path'])
    entry = next(c for c in manifest['cameras'] if c['id'] == str(camera))
    scene = read_json(request['bindings']['scene_freeze']['path'])
    matrix = np.asarray(scene['normalization'],np.float64)
    source_scale = scene['historical_reference']['scale']
    physical_scale = scene['scale']/source_scale
    linear = matrix[:3,:3]
    scale = float(np.linalg.norm(linear[:,0]))
    rotation = np.asarray(entry['world_to_camera_R'],np.float64)
    center = np.asarray(entry['center'],np.float64)
    translation = np.asarray(entry['world_to_camera_T'],np.float64)
    intrinsic = np.asarray(entry['K'],np.float64)
    if (rotation.shape != (3,3) or center.shape != (3,) or translation.shape != (3,) or
            intrinsic.shape != (3,3) or not np.isfinite(rotation).all() or not np.isfinite(center).all() or
            not np.isfinite(translation).all() or not np.isfinite(intrinsic).all() or
            not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-8) or
            not np.isclose(np.linalg.det(rotation),1.,atol=1e-8) or
            not np.allclose(translation,-rotation@center,atol=1e-8)):
        raise ValueError('rigid accepted native camera required')
    # Remove normalization scale from orientation; apply it to camera center.
    normalized_rotation = rotation@(linear/scale).T
    normalized_center = linear@(center*physical_scale)+matrix[:3,3]
    camtoworld = np.eye(4)
    camtoworld[:3,:3] = normalized_rotation.T
    camtoworld[:3,3] = normalized_center
    return dict(camtoworld=camtoworld.astype(np.float32),K=intrinsic.astype(np.float32),
        time=frame/50,resolution=[entry['width'],entry['height']],
        source_frame=next(f for f in entry['frames'] if f['frame_id'] == frame))


REPAIRED_DURATION = .2


def training_keys(request, manifest):
    """Holdout keys from the manifest, or every frame of the training rig (all-times)."""
    if request.get('training_policy') == 'all-times':
        from .final_render_contract import TRAINING_CAMERAS
        return [(str(camera),frame) for camera in TRAINING_CAMERAS for frame in range(50)]
    return [(str(c),f) for c,f in manifest['training_keys']]


def duration_target(request, data):
    """The repaired duration target: the frozen initializer's uniform 0.2 width."""
    if request.get('lifetime_policy') != 'repaired':
        return None
    durations = np.asarray(data['durations'])
    if durations.size == 0 or not np.allclose(durations,REPAIRED_DURATION,rtol=0,atol=1e-7):
        raise ValueError('repaired lifetime requires the uniform 0.2 initializer duration')
    return REPAIRED_DURATION


class NativeFreeTimeRuntime:
    """Audited native model/update/save/restore/render binding; not qualified yet.

Construction checks immutable CPU inputs only. No production entrypoint or DO
authority is supplied by this module. Never call GPU methods in CPU qualification.
"""
    record_kind = 'actual'

    def __init__(self, request, arm, checkout):
        if request.get('record_kind') != 'actual':
            raise ValueError('actual request required by native runtime; fixtures cannot be promoted')
        self.request = parse_request(request)
        validate_scene_bindings(self.request)
        if arm not in self.request['compositions']:
            raise ValueError('unknown native arm')
        self.arm, self.checkout = arm, safe_path(checkout).resolve()
        trainer = self.checkout/'src/simple_trainer_freetime_4d_pure_relocation.py'
        if file_record(trainer) != self.request['bindings']['preset']:
            raise ValueError('native checkout differs from exact bound preset')
        self.inventory = read_json(self.request['bindings']['runtime']['path'])
        scene = read_json(self.request['bindings']['scene_freeze']['path'])
        validate_inventory(self.inventory,checkout=self.checkout,
            environment_prefix=sys.prefix,interpreter=sys.executable,
            normalization=self.request['initializer_contract']['normalization'],
            scene_scale=scene['historical_reference']['normalization']['scene_scale'],
            installed_dependencies=True)
        self.model = self.sampler = self.torch = None
        self.is_fresh = True
        self.closed = False
        self.scene = read_json(self.request['bindings']['scene_freeze']['path'])
        self.manifest = read_json(self.request['bindings']['scene_manifest']['path'])
        self.cameras = {c:prepare_camera(self.request,c,0) for c in range(34)}
        self.frames = {(int(c['id']),f['frame_id']):f for c in self.manifest['cameras'] for f in c['frames']}
        self.keys = training_keys(self.request,self.manifest)
        self.key_set = set(self.keys)
        self.usage = dict(peak_device_bytes=0,cpu_workers_used=0)

    def _load(self, request, arm, data, receipt, provenance):
        if (not self.is_fresh or self.closed or object_hash(request) != object_hash(self.request) or arm != self.arm or
                provenance.get('record_kind') != 'actual' or provenance.get('request_sha256') != object_hash(request) or
                provenance.get('arm') != arm or provenance.get('native_input_sha256') != object_hash(receipt)):
            raise ValueError('fresh exact native runtime/input/provenance required')
        parse_request(request)
        verify_record(self.request['bindings']['runtime'])
        validate_inventory(self.inventory,checkout=self.checkout,
            environment_prefix=sys.prefix,interpreter=sys.executable,
            normalization=request['initializer_contract']['normalization'],
            scene_scale=self.scene['historical_reference']['normalization']['scene_scale'],
            installed_dependencies=True)
        validate_model_input(data,receipt)
        if receipt.get('record_kind') != 'actual' or receipt.get('arm') != arm or receipt.get('request_sha256') != object_hash(request):
            raise ValueError('actual same-arm native input required')
        initializer = provenance.get('initializer')
        if type(initializer) is not dict or verify_record(initializer) != initializer:
            raise ValueError('exact actual initializer record required')
        bundle = read_json(initializer['path'])
        if (bundle.get('schema') != 'plan069-final-render-prepared-initializer/v1' or
                bundle.get('record_kind') != 'actual' or bundle.get('arm') != arm or
                bundle.get('request_sha256') != object_hash(request) or
                verify_record(bundle['archive']) != bundle['archive']):
            raise ValueError('actual initializer provenance differs')
        with np.load(safe_path(bundle['archive']['path']),allow_pickle=False) as archive:
            arrays = {name:archive[name].copy() for name in archive.files}
        expected_data, expected_receipt = prepare_model_input(request,arm,bundle['initializer_receipt'],arrays)
        if receipt != expected_receipt or any(not np.array_equal(data[k],expected_data[k]) for k in data):
            raise ValueError('native input differs from immutable actual initializer')
        # Restrict networking before libraries can request uncached assets.
        import runpy
        runpy.run_path(str(Path(__file__).resolve().parents[1]/'offline-python.py'))['restrict_network']()
        import random
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; native runtime has no CPU fallback')
        self.torch = torch
        # The supervisor's bounded resource helper runs alongside this pool.
        torch.set_num_threads(max(1, request['cpu_workers_limit'] - 1))
        for module, key in [('gsplat.csrc','gsplat'),('fused_ssim_cuda','fused_ssim')]:
            if file_record(importlib.import_module(module).__file__) != self.inventory['binaries'][key]:
                raise ValueError('loaded native binary differs: '+key)
        random.seed(0);np.random.seed(0);torch.manual_seed(0);torch.cuda.manual_seed_all(0)
        torch.hub.set_dir(str(safe_path(self.inventory['lpips_checkpoint']['path']).parent.parent))
        from freetimegs_training import load_training
        from dataclasses import asdict
        self.cfg, _, _ = load_training(self.checkout)
        self.cfg.start_frame,self.cfg.end_frame = 0,50
        self.scene_scale = self.scene['historical_reference']['normalization']['scene_scale']
        configuration = dict(native=asdict(self.cfg),normalization=request['initializer_contract']['normalization'],
            scene_scale=self.scene_scale)
        if read_json(self.inventory['resolved_config']['path']) != configuration:
            raise ValueError('resolved native configuration differs from frozen recipe')
        # Repair after the frozen-recipe check: the -1 sentinel must not reach the
        # duration penalty (docs/multicamera-freetimegs-workflow.md, step 5.5).
        self.duration_target = duration_target(request,data)
        if self.duration_target is not None:
            self.cfg.init_duration = self.duration_target
        self.provenance = copy.deepcopy(provenance)
        self.is_fresh = False
        return torch

    def training_keys(self):
        return list(self.keys)

    def _project_durations(self):
        from basketball_crossing_repair import project_duration_parameter_
        return project_duration_parameter_(self.model.splats['durations'],self.model.optimizers['durations'])

    def camera(self, camera, frame, *, load_image=False):
        from types import SimpleNamespace
        torch = self.torch
        if torch is None or (camera,frame) not in self.frames:
            raise ValueError('prepared native camera required')
        calibrated = self.cameras[camera]
        transform = torch.from_numpy(calibrated['camtoworld'].copy()).cuda()
        pixels = None
        if load_image:
            from PIL import Image
            source = self.frames[camera,frame]
            directory = safe_path(self.request['bindings']['scene_manifest']['path']).parent
            path = safe_path(directory/source['path']).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError('native RGB path escapes processed manifest')
            if file_record(path)['sha256'] != source['sha256']:
                raise ValueError('native training RGB changed')
            with Image.open(path) as image:
                if image.mode != 'RGB' or image.size != (960,540):
                    raise ValueError('accepted native RGB dimensions/mode differ')
                pixels = torch.from_numpy(np.asarray(image).copy()).cuda().float()[None]/255
        return SimpleNamespace(camtoworlds=transform[None],viewmats=torch.linalg.inv(transform)[None],
            Ks=torch.from_numpy(calibrated['K'].copy()).cuda()[None],width=960,height=540,t=frame/50,pixels=pixels)

    def prepare_training(self, request, arm, data, receipt, provenance):
        torch = self._load(request,arm,data,receipt,provenance)
        from freetimegs_model import NativeFreeTimeModel
        from atgs_sampler import ManifestBalancedSampler
        from types import SimpleNamespace
        from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
        lpips = LearnedPerceptualImagePatchSimilarity(net_type='alex',normalize=True).cuda()
        self.model = NativeFreeTimeModel(self.checkout,self.cfg,{k:torch.from_numpy(v.copy()) for k,v in data.items()},
            scene_scale=self.scene_scale,device='cuda')
        self.model.enable_training(self.checkout,scene_scale=self.scene_scale,device='cuda',lpips=lpips)
        sampler_scene = SimpleNamespace(training_keys=self.training_keys,
            sha256=request['bindings']['scene_manifest']['sha256'],
            cameras={c['id']:c for c in self.manifest['cameras']},
            frames={(str(c),f):row for (c,f),row in self.frames.items()})
        self.sampler = ManifestBalancedSampler(sampler_scene,1,seed=0)
        self.iteration = 0
        if self.duration_target is not None:
            print('initial duration projection', self._project_durations(), flush=True)

    def training_step(self, iteration):
        if self.closed or self.model is None or type(iteration) is not int or iteration != self.iteration or iteration >= self.request['iterations']:
            raise ValueError('sequential native training update required')
        camera,frame = next(self.sampler)
        if (camera,frame) not in self.key_set:
            raise ValueError('native sampler selected excluded observation')
        metrics = self.model.training_step(iteration,self.camera(int(camera),frame,load_image=True),self.model.schedulers)
        self.torch.cuda.synchronize()
        if self.duration_target is not None:
            metrics['duration_projection_changed'] = self._project_durations()['changed_entries']
        self.iteration += 1
        return {key:float(value.detach()) if isinstance(value,self.torch.Tensor) else value for key,value in metrics.items()}

    def save_checkpoint(self, path, iteration):
        if self.closed or self.model is None or iteration != self.iteration:
            raise ValueError('completed native iteration boundary required')
        from freetimegs_checkpoint import save_checkpoint
        self.torch.cuda.synchronize()
        save_checkpoint(path,self.model,iteration=iteration,
            loop_state={'sampler':self.sampler.state_dict()},provenance=self.provenance)

    def checkpoint_metadata(self, path):
        import torch
        state = torch.load(safe_path(path),map_location='cpu',weights_only=True)
        if state.get('schema') != 'freetimegs-training/v1' or type(state.get('iteration')) is not int:
            raise ValueError('complete native checkpoint required')
        return dict(iteration=state['iteration'],provenance=state['provenance'])

    def reload_checkpoint(self, checkpoint, request, arm, data, receipt, provenance, restored_path):
        # Construct a fresh native model skeleton; no initializer or optimizer update.
        torch = self._load(request,arm,data,receipt,provenance)
        from types import MethodType
        from freetimegs_model import NativeFreeTimeModel
        from freetimegs_source import load_initializer,load_temporal_methods
        from freetimegs_training import load_training
        from freetimegs_checkpoint import restore_checkpoint,save_checkpoint
        from basketball_study_resume_check import differences
        methods, render_digest = load_temporal_methods(self.checkout,include_render=True)
        _, init_digest = load_initializer(self.checkout)
        _, _, training_source = load_training(self.checkout)
        model = NativeFreeTimeModel.__new__(NativeFreeTimeModel)
        model.cfg = self.cfg;model.device = 'cuda'
        model.source_digests = dict(initializer=init_digest,render=render_digest,**training_source)
        for name, method in methods.items():
            setattr(model,name,MethodType(method,model))
        iteration, loop = restore_checkpoint(safe_path(checkpoint['path']),model,provenance=self.provenance)
        self.model,self.iteration = model,iteration
        save_checkpoint(restored_path,model,iteration=iteration,loop_state=loop,provenance=self.provenance)
        original = torch.load(safe_path(checkpoint['path']),map_location='cpu',weights_only=True)
        restored = torch.load(safe_path(restored_path),map_location='cpu',weights_only=True)
        changed = differences(original,restored)
        return dict(iteration=iteration,provenance=self.provenance,restored_state_equal=not changed)

    def render_frame(self, camera, frame):
        if self.closed or self.model is None or self.iteration != self.request['iterations'] or camera not in (0,10,20,30):
            raise ValueError('reloaded exact endpoint and held-out camera required')
        degree = min((self.iteration-1)//self.cfg.sh_degree_interval,self.cfg.sh_degree)
        with self.torch.no_grad():
            pixels = self.model.render(self.camera(camera,frame),sh_degree=degree)[0][0,...,:3]
            self.torch.cuda.synchronize()
            return pixels.detach().cpu().numpy().astype(np.float32)

    def resource_usage(self):
        if self.torch is not None:
            free,total = self.torch.cuda.mem_get_info()
            self.usage['peak_device_bytes'] = max(self.usage['peak_device_bytes'],total-free,
                self.torch.cuda.max_memory_reserved())
            self.usage['cpu_workers_used'] = self.torch.get_num_threads()
        return dict(self.usage)

    def close(self):
        self.model = self.sampler = None
        if self.torch is not None:
            self.torch.cuda.synchronize();self.torch.cuda.empty_cache()
        self.closed = True
