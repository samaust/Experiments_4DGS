"""Checkpointable, synchronous encoder-balanced sampling of training views.

Preserves upstream shuffled-bucket/cycling policy, but routes corrected manifest
times and uses a dedicated CPU generator. Do not put this behind prefetching:
the cursor represents samples handed to the synchronous training loop.
"""
import hashlib
import json

import torch


class ManifestBalancedSampler:
    def __init__(self, scene, num_encoders, *, seed=0):
        if type(num_encoders) is not int or num_encoders < 1:
            raise ValueError('num_encoders must be a positive integer')
        self.keys = sorted(scene.training_keys())
        if not self.keys or len(set(self.keys)) != len(self.keys):
            raise ValueError('requires unique training keys')
        self.buckets = [[] for _ in range(num_encoders)]
        times = []
        for index, key in enumerate(self.keys):
            if scene.cameras[key[0]]['split'] != 'train':
                raise ValueError('held-out view in sampler')
            time = scene.frames[key]['normalized_time']
            if not 0 <= time < 1:
                raise ValueError('invalid corrected time')
            times.append(time)
            self.buckets[min(int(time * num_encoders), num_encoders - 1)].append(index)
        if any(not bucket for bucket in self.buckets):
            raise ValueError('empty encoder bucket')
        identity = dict(manifest=scene.sha256, keys=self.keys, times=times, encoders=num_encoders)
        self.identity = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        self.generator = torch.Generator(device='cpu').manual_seed(seed)
        self.order = []
        self.cursor = 0
        self.epoch = 0
        self.epoch_size = max(map(len, self.buckets)) * num_encoders

    def _start_epoch(self):
        buckets = [[bucket[i] for i in torch.randperm(len(bucket), generator=self.generator).tolist()]
                   for bucket in self.buckets]
        self.order = []
        for batch in range(max(map(len, buckets))):
            for encoder in torch.randperm(len(buckets), generator=self.generator).tolist():
                self.order.append(buckets[encoder][batch % len(buckets[encoder])])
        self.cursor = 0
        self.epoch += 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.cursor == len(self.order):
            self._start_epoch()
        key = self.keys[self.order[self.cursor]]
        self.cursor += 1
        return key

    def state_dict(self):
        return dict(schema='atgs-balanced-sampler/v1', identity=self.identity,
                    order=list(self.order), cursor=self.cursor, epoch=self.epoch,
                    generator=self.generator.get_state().clone())

    def load_state_dict(self, state):
        if state.get('schema') != 'atgs-balanced-sampler/v1' or state.get('identity') != self.identity:
            raise ValueError('sampler manifest/routing identity mismatch')
        order, cursor, epoch = state['order'], state['cursor'], state['epoch']
        if (not isinstance(order, list) or type(cursor) is not int or type(epoch) is not int
                or epoch < 0 or not 0 <= cursor <= len(order)
                or (epoch == 0 and (order or cursor))
                or (epoch > 0 and len(order) != self.epoch_size)):
            raise ValueError('invalid sampler cursor/epoch')
        if any(type(i) is not int or not 0 <= i < len(self.keys) for i in order):
            raise ValueError('invalid sampler sample index')
        routing = {i: encoder for encoder, bucket in enumerate(self.buckets) for i in bucket}
        size = len(self.buckets)
        for start in range(0, len(order), size):
            if {routing[i] for i in order[start:start + size]} != set(range(size)):
                raise ValueError('unbalanced saved sampler batch')
        # Reject malformed generator state before replacing live sampler state.
        generator = torch.Generator(device='cpu')
        generator.set_state(state['generator'].cpu())
        self.generator = generator
        self.order, self.cursor, self.epoch = list(order), cursor, epoch
