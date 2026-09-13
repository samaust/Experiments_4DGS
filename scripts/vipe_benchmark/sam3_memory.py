"""Bounded S3 lifecycle measurements; diagnostic outputs are not benchmark results."""
import gc
import json
from pathlib import Path
import time

import numpy as np

from .files import file_record, read_json, verify_record, write_json

CLEANUP = 'release-gc-empty-cache-v1'
DIAGNOSTIC = 'S3-memory-diagnostic-001'


class MemoryObserver:
    def __init__(self, torch, output, *, diagnostic):
        self.torch = torch
        self.output = Path(output)
        self.diagnostic = diagnostic
        self.pair = None
        self.events = self.output / 'memory-events.jsonl'
        self.events.touch(exist_ok=False)
        self.snapshots = []
        self.highwater = 0
        self.seconds = 0.
        if diagnostic:
            torch.cuda.memory._record_memory_history(enabled='all', context='all', stacks='python', max_entries=4096)
        self.phase('observer_started')

    def snapshot(self, phase):
        if not self.diagnostic or len(self.snapshots) >= 12:
            return
        path = self.output / f'memory-snapshot-{len(self.snapshots):03d}.json'
        write_json(path, dict(phase=phase, pair=self.pair, snapshot=self.torch.cuda.memory._snapshot()))
        self.snapshots.append(file_record(path))

    def phase(self, phase, semantic=None):
        started = time.monotonic()
        cuda = self.torch.cuda
        cuda.synchronize()
        free, total = cuda.mem_get_info()
        stats = cuda.memory_stats()
        row = dict(phase=phase, pair=self.pair, semantic=semantic, monotonic=time.monotonic(),
            allocated_bytes=cuda.memory_allocated(), reserved_bytes=cuda.memory_reserved(),
            peak_allocated_bytes=cuda.max_memory_allocated(), peak_reserved_bytes=cuda.max_memory_reserved(),
            cuda_device_used_bytes=total-free, cuda_free_bytes=free,
            allocation_retries=stats.get('num_alloc_retries', 0), allocator_ooms=stats.get('num_ooms', 0),
            inactive_split_bytes=stats.get('inactive_split_bytes.all.current', 0))
        with self.events.open('a') as stream:
            stream.write(json.dumps(row, sort_keys=True)+'\n')
            stream.flush()
        if self.diagnostic:
            if phase == 'observer_started' or (self.pair == 1 and semantic == 'person' and phase in
                    ('after_reset', 'after_release', 'after_gc', 'after_empty_cache')):
                self.snapshot(phase)
            elif row['cuda_device_used_bytes'] >= 20*2**30 and row['cuda_device_used_bytes'] > self.highwater+2**30:
                self.snapshot('high_memory_'+phase)
        self.highwater = max(self.highwater, row['cuda_device_used_bytes'])
        self.seconds += time.monotonic()-started
        return row

    def cleanup(self, semantic=None):
        self.phase('after_release', semantic)
        started = time.monotonic()
        gc.collect()
        self.seconds += time.monotonic()-started
        self.phase('after_gc', semantic)
        started = time.monotonic()
        self.torch.cuda.empty_cache()
        self.seconds += time.monotonic()-started
        self.phase('after_empty_cache', semantic)

    def finish(self):
        self.phase('finished')
        self.snapshot('finished')
        if self.diagnostic:
            self.torch.cuda.memory._record_memory_history(enabled=None)
        path = self.output / 'memory-summary.json'
        write_json(path, dict(status='complete', diagnostic=self.diagnostic, cleanup=CLEANUP,
            events=file_record(self.events), snapshots=self.snapshots, observation_and_cleanup_seconds=self.seconds,
            cuda_device_metric='cudaMemGetInfo total minus free; supervisor independently samples nvidia-smi total device memory'))
        return file_record(path)


def compare_partial(rows, original_output):
    """Compare saved arrays/pixels without rescoring or changing label identities."""
    import cv2
    comparisons = []
    from .access import Identity
    for row in rows:
        stem = Path(original_output) / Identity(**row['identity']).key()
        if not stem.with_suffix('.npy').exists():
            continue
        old_array = np.load(stem.with_suffix('.npy'), allow_pickle=False)
        new_array = np.load(verify_record(row['instances'])['path'], allow_pickle=False)
        old_mask = cv2.imread(str(stem.with_suffix('.png')), cv2.IMREAD_UNCHANGED)
        new_mask = cv2.imread(verify_record(row['semantic_static'])['path'], cv2.IMREAD_UNCHANGED)
        if old_mask is None or new_mask is None or old_array.shape != new_array.shape or old_mask.shape != new_mask.shape:
            raise ValueError('partial output comparison grid mismatch')
        comparisons.append(dict(identity=row['identity'], instance_disagreements=int(np.count_nonzero(old_array != new_array)),
            mask_disagreements=int(np.count_nonzero(old_mask != new_mask)),
            previous_instances=file_record(stem.with_suffix('.npy')), previous_mask=file_record(stem.with_suffix('.png'))))
    return dict(status='identical' if len(comparisons)==82 and all(
        r['instance_disagreements']==r['mask_disagreements']==0 for r in comparisons) else 'requires-review',
        expected_overlap=82, comparisons=comparisons)


def validate_diagnostic_review(record):
    review = read_json(verify_record(record)['path'])
    if review.get('status') != 'passed' or review.get('cleanup') != CLEANUP:
        raise ValueError('full reconstruction requires a passed memory diagnostic review')
    if not review.get('cleanup_sources'):
        raise ValueError('diagnostic review must bind the validated cleanup implementation')
    for source in review['cleanup_sources']:
        verify_record(source)
    result = read_json(verify_record(review['diagnostic_result'])['path'])
    if (result.get('status') != 'complete' or result.get('job_id') != DIAGNOSTIC or len(result.get('rows', [])) != 96 or
            result.get('partial_comparison', {}).get('status') != 'identical' or
            len(result['partial_comparison']['comparisons']) != 82 or
            any(r['instance_disagreements'] or r['mask_disagreements'] for r in result['partial_comparison']['comparisons'])):
        raise ValueError('diagnostic did not complete 48 pairs with identical overlap')
    summary = read_json(verify_record(result['memory'])['path'])
    verify_record(summary['events'])
    for snapshot in summary['snapshots']:
        verify_record(snapshot)
    if (review.get('cleanup_confirmed') is not True or not review.get('memory_behavior_validated') or
            not 0 <= review.get('peak_device_bytes', float('inf')) <= 22*2**30):
        raise ValueError('diagnostic memory behavior or cleanup unverified')
    return review
