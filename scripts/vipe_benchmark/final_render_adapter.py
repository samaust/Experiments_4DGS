"""Pure QF initializer conversion for the NativeFreeTimeModel data boundary.

This prepares arrays only. It neither constructs a native model nor establishes
runtime qualification, allocation authority, measured device use or final media.
"""
import copy

import numpy as np

from .files import object_hash
from .final_render_contract import initializer_arrays_hash, validate_initializer

NATIVE_FIELDS = ('positions', 'colors', 'velocities', 'times', 'durations')
SIDECAR_FIELDS = ('region', 'velocity_valid')
ASSEMBLY_IDS = ('physical_static_id', 'foreground_observation_id')


def prepare_model_input(request, arm, initializer_receipt, arrays):
    """Return independently owned native arrays and their CPU provenance receipt.

    NativeFreeTimeModel expects the five arrays unchanged in normalized scene
    units and normalized time. A future admitted worker can convert these arrays
    to Torch tensors explicitly. Sidecars remain in the bound initializer; they
    are never accidentally passed to the native constructor or interpreted as
    native trainable fields. Byte totals describe these CPU arrays only.
    """
    request = copy.deepcopy(request)
    initializer_receipt = copy.deepcopy(initializer_receipt)
    sidecars = SIDECAR_FIELDS
    if set(arrays) == set(NATIVE_FIELDS + SIDECAR_FIELDS + ASSEMBLY_IDS):
        sidecars += ASSEMBLY_IDS
    elif set(arrays) != set(NATIVE_FIELDS + SIDECAR_FIELDS):
        raise ValueError('exact native initialization and provenance sidecars required')
    snapshot = {name: np.array(value, copy=True, order='C') for name, value in arrays.items()}
    schema = request.get('schema')
    if schema == 'plan067-final-render-request/v1':
        checked = validate_initializer(request, arm, initializer_receipt, snapshot)
    elif schema == 'plan069-final-render-request/v1':
        from .extended_final_render_contract import validate_initializer as validate_extended
        checked = validate_extended(request, arm, initializer_receipt, snapshot)
    else:
        raise ValueError('unsupported final render request schema')
    if ASSEMBLY_IDS[0] in snapshot:
        count = len(snapshot['positions'])
        for name in ASSEMBLY_IDS:
            if snapshot[name].shape != (count,) or snapshot[name].dtype.kind != 'i':
                raise ValueError('signed per-point assembly provenance IDs required')
        static = snapshot['region'] == 0
        physical = snapshot[ASSEMBLY_IDS[0]]
        foreground = snapshot[ASSEMBLY_IDS[1]]
        if (np.any(physical[static] < 0) or np.any(physical[~static] != -1) or
                np.any(foreground[static] != -1) or np.any(foreground[~static] < 0) or
                len(np.unique(foreground[~static])) != int((~static).sum())):
            raise ValueError('assembly provenance IDs disagree with static/foreground regions')
    data = {name: snapshot[name] for name in NATIVE_FIELDS}
    receipt = dict(schema='plan069-final-render-native-input/v1', status='prepared',
        record_kind=request['record_kind'], arm=arm, composition=request['compositions'][arm],
        request_sha256=object_hash(request), initializer_receipt=initializer_receipt,
        initializer_validation=checked, point_count=len(data['positions']),
        arrays_sha256=initializer_arrays_hash(snapshot), native_arrays_sha256=initializer_arrays_hash(data),
        native_fields=list(NATIVE_FIELDS), native_array_bytes=sum(data[name].nbytes for name in NATIVE_FIELDS),
        sidecar_fields=list(sidecars), sidecar_array_bytes=sum(snapshot[name].nbytes for name in sidecars),
        execution_authorized=False, native_adapter_qualified=False)
    return data, receipt


def validate_model_input(data, receipt):
    """Detect changes before tensor conversion; this grants no job authority.

    The caller must separately verify the admitted source initializer receipt and
    all live execution gates. This check binds only the prepared native arrays.
    """
    if (receipt.get('schema') != 'plan069-final-render-native-input/v1' or
            receipt.get('status') != 'prepared' or receipt.get('execution_authorized') is not False or
            receipt.get('native_adapter_qualified') is not False or set(data) != set(NATIVE_FIELDS)):
        raise ValueError('prepared nonauthorizing native model input required')
    count = receipt.get('point_count')
    if type(count) is not int or count <= 0:
        raise ValueError('positive native point count required')
    for name in NATIVE_FIELDS:
        value = data[name]
        if (not isinstance(value, np.ndarray) or value.dtype != np.float32 or
                value.shape != (count, 3 if name in NATIVE_FIELDS[:3] else 1) or not np.isfinite(value).all()):
            raise ValueError('changed or invalid native model array: ' + name)
    digest = initializer_arrays_hash(data)
    if digest != receipt.get('native_arrays_sha256'):
        raise ValueError('prepared native model arrays changed')
    return digest
