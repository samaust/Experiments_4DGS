"""Read frozen native observations without reprocessing or execution authority.

The geometry worker verifies membership in the request's accepted input/native
results before invoking load_observation. This boundary verifies decoded bytes
and numeric contracts; it performs no model inference, resizing or unit changes.
"""
import hashlib
from io import BytesIO
import zipfile

import numpy as np
from PIL import Image

from .contracts import SHAPE, instances, validate_static
from .files import safe_path


MAX_INPUT_BYTES = 64*2**20


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bytes(record):
    _require(isinstance(record,dict) and set(record) == {'path','sha256','bytes'} and
        type(record['bytes']) is int and 0 < record['bytes'] <= MAX_INPUT_BYTES,
        'bounded exact file record required')
    # Hash the same bounded bytes passed to the decoder, avoiding a hash/open race.
    with safe_path(record['path']).open('rb') as stream:
        raw=stream.read(record['bytes']+1)
    _require(len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'],
        'changed native input file')
    return raw


def _decode_array(raw, dtype):
    stream=BytesIO(raw)
    version=np.lib.format.read_magic(stream)
    _require(version in ((1,0),(2,0)), 'supported non-pickled NPY version required')
    reader=np.lib.format.read_array_header_1_0 if version == (1,0) else np.lib.format.read_array_header_2_0
    shape,_,actual_dtype=reader(stream)
    _require(shape == SHAPE and actual_dtype == np.dtype(dtype),
        'native array header grid/dtype differs; int32 instances and boolean masks required')
    _require(len(raw)-stream.tell() == SHAPE[0]*SHAPE[1]*actual_dtype.itemsize,
        'native array data length differs')
    return np.load(BytesIO(raw),allow_pickle=False)


def _array(record, dtype):
    return _decode_array(_bytes(record),dtype)


def _image(record, mode):
    with Image.open(BytesIO(_bytes(record))) as image:
        _require(image.mode == mode and image.size == (SHAPE[1],SHAPE[0]) and
            getattr(image,'n_frames',1) == 1, 'native image mode/grid differs')
        return np.asarray(image).copy()


def load_observation(source, segmentation, motion):
    """Existing worker loader seam: return exact RGB/valid/labels/changing arrays."""
    identity=source['identity']
    _require(identity['branch'] == 'reconstruction' and source['grid'] == 'undistorted-opencv-integer',
        'accepted reconstruction grid required')
    for row in (segmentation,motion):
        native=row['identity']
        _require(all(native[key] == identity[key] for key in ('branch','camera','frame')) and
            native['pair_start'] == segmentation['identity']['pair_start'] and
            row['source_rgb_sha256'] == source['rgb']['sha256'] and row['K'] == source['K'] and
            row['grid'] == source['grid'] and row['valid'] == source['valid'],
            'native identity/calibration/footprint differs')
    rgb=_image(source['rgb'],'RGB');valid=_array(source['valid'],np.bool_)
    labels=_array(segmentation['instances'],np.int32);changing=_array(motion['changing'],np.bool_)
    instances(labels,segmentation['semantics'],valid)
    _require(changing.dtype == np.bool_ and changing.shape == SHAPE,
        'boolean changing mask on accepted grid required')
    static=_image(segmentation['semantic_static'],'L')
    validate_static(static,valid)
    _require(np.array_equal(static,(valid & (labels == 0)).astype(np.uint8)*255),
        'semantic static mask differs from exact instances')
    return dict(rgb=rgb,valid=valid,labels=labels,changing=changing)


def load_metric_depth(source, native):
    """Load one frozen metric anchor; metres are already converted by its producer.

    Membership in D*'s frozen generation is checked by load_selected_depth.
    Original RGB lineage is accepted for video producers whose depth is already
    remapped to the accepted scale grid. No pixel resampling or scale is applied.
    """
    from .contracts import depth as validate_depth
    identity=source['identity']
    _require(identity['branch'] == 'depth' and source['grid'] == 'scale-opencv-integer' and
        (native['camera'],native['frame']) == (identity['camera'],identity['frame']) and
        native['domain'] == 'camera_z_metres' and
        native.get('grid',source['grid']) == source['grid'] and
        native.get('K',source['K']) == source['K'], 'metric anchor identity/grid/calibration/domain differs')
    if 'inference_rgb' in native:
        _require(native['inference_rgb'] == source['rgb'], 'metric anchor inference RGB differs')
    else:
        _require(native.get('source_rgb') in (source['rgb'],source.get('source_rgb')) and
            native.get('source_rgb') is not None, 'metric anchor source RGB differs')
    raw=_bytes(native.get('prediction',native.get('depth')))
    with zipfile.ZipFile(BytesIO(raw)) as compressed:
        members=compressed.infolist()
        _require(len(members) <= 16 and len({entry.filename for entry in members}) == len(members) and
            sum(entry.file_size for entry in members) <= MAX_INPUT_BYTES,
            'expanded native archive limit exceeded or duplicate members')
        names={entry.filename for entry in members}
        _require({'depth.npy','valid.npy'} <= names, 'metric depth/valid arrays required')
        values=_decode_array(compressed.read('depth.npy'),np.float32)
        valid=_decode_array(compressed.read('valid.npy'),np.bool_)
        confidence=_decode_array(compressed.read('confidence.npy'),np.float32) if 'confidence.npy' in names else None
    image_valid=_array(source['valid'],np.bool_)
    validate_depth(values,valid,image_valid,confidence)
    return dict(depth=values,valid=valid)


def load_selected_depth(request, camera, frame):
    """Read an existing frozen D* anchor, never synthesize reconstruction maps.

    Geometry derives metric camera units from the passing frozen D* scale;
    anchors are supporting inputs/diagnostics, not a new depth fusion algorithm.
    This CPU reader alone cannot admit an actual geometry/model execution.
    """
    import json
    from .depth_review import validate_decision
    _require(request.get('record_kind') in ('actual','fixture') and type(camera) is int and
        type(frame) is int, 'explicit request mode and integer anchor identity required')
    bindings=request['bindings']
    decision=validate_decision(bindings['depth_decision'],actual=request['record_kind'] == 'actual')
    candidate=request['depth_candidate']
    _require(decision['status'] == 'ready' and decision['selected_candidate_ids'] == [candidate],
        'selected-depth decision differs')
    evidence=decision['engineering_eligibility'][candidate]['evidence']
    _require(decision['engineering_eligibility'][candidate]['eligible'] is True and
        all(bindings[key] == evidence[name] for key,name in
            (('inputs','inputs'),('D_fit','fit'),('D_check','check'))), 'selected-depth exact input/scale evidence differs')
    inputs=json.loads(_bytes(bindings['inputs']))
    sources=[row for row in inputs['depth'] if
        (row['identity']['camera'],row['identity']['frame']) == (camera,frame)]
    _require(len(sources) == 1, 'missing exact selected-depth anchor input')
    generation=json.loads(_bytes(evidence['generation']))
    rows=[row for row in generation.get('rows',[]) if (row['camera'],row['frame']) == (camera,frame)]
    if not rows and candidate == 'D2' and frame in (100,175):
        # D2 publishes 4 clips; the remaining anchors are exact historical rows
        # already verified by the frozen metric decision, not newly inferred maps.
        original=json.loads(_bytes(evidence['historical_fit' if frame == 100 else 'historical_check']))
        for row in original.get('rows',[]):
            identity=row['identity']
            if (identity['camera'],identity['frame']) == (camera,frame):
                rows.append(dict(camera=camera,frame=frame,K=row['K'],grid=row['grid'],
                    domain='camera_z_metres',inference_rgb=sources[0]['rgb'],depth=row['depth']))
                _require(row['source_rgb_sha256'] == sources[0]['rgb']['sha256'], 'historical D2 anchor RGB differs')
    _require(len(rows) == 1, 'missing exact selected-depth anchor prediction')
    return load_metric_depth(sources[0],rows[0])
