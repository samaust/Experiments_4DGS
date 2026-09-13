"""Candidate-independent CPU pseudo-labels with separately evidenced review.

This schema deliberately cannot satisfy the original human-truth validator.
Model agreement is a proxy; unknown roles, motion, boundaries and identities
are retained as unknown, including in otherwise mechanically valid images.
"""
import copy
from pathlib import Path
import time

import numpy as np

from .access import Identity
from .annotations import IMAGE_FLAGS, template
from .files import file_record, load_array, object_hash, read_json, verify_record, write_json
from .metrics import instance_matching

SCHEMA = 'vipe-benchmark-automated-annotations/v1'
PRIMARY_ID = 'torchvision-maskrcnn-resnet50-fpn-v2-coco-v1-cpu'


def check_policy(record):
    verify_record(record)
    policy = read_json(record['path'])
    if (policy.get('schema') != 'vipe-benchmark-automated-annotation-policy/v1' or
            policy.get('evidence_kind') != 'model-assisted-proxy' or
            policy.get('human_ground_truth') is not False or not policy.get('authorization')):
        raise ValueError('explicit automated-annotation amendment required')
    for field in ('original_plan', 'original_protocol', 'historical_authorization'):
        verify_record(policy[field])
    primary = policy['primary']
    expected = dict(device='cpu', dtype='float32', batch_size=1, threads=8,
                    score_threshold=.5, mask_threshold=.5, min_size=800, max_size=1333,
                    maximum_attempts=1, architecture='maskrcnn_resnet50_fpn_v2', weights='COCO_V1')
    if any(primary.get(k) != v for k, v in expected.items()):
        raise ValueError('teacher configuration differs from the approved fixed solution')
    return policy


def merge_teacher(prediction, valid):
    """Resolve overlaps by probability, score, then native detection order."""
    labels = np.zeros(valid.shape, np.int32)
    best = np.full(valid.shape, -.1, np.float32)
    scores = np.asarray(prediction['scores'])
    classes = np.asarray(prediction['labels'])
    masks = np.asarray(prediction['masks'])
    if masks.ndim == 4 and masks.shape[1] == 1:
        masks = masks[:, 0]
    if masks.shape != (len(scores), *valid.shape) or len(classes) != len(scores):
        raise ValueError('teacher output shape mismatch')
    if not np.isfinite(masks).all() or not np.isfinite(scores).all():
        raise ValueError('nonfinite teacher probability')
    ids = [i for i in range(len(scores)) if scores[i] >= .5 and classes[i] in (1, 37)]
    ids.sort(key=lambda i: (-float(scores[i]), i))
    metadata = {}
    for i in ids:
        iid = i + 1
        take = valid & (masks[i] >= .5) & (masks[i] > best)
        labels[take] = iid
        best[take] = masks[i][take]
        metadata[str(iid)] = dict(**{'class': 'person' if classes[i] == 1 else 'basketball'},
            role='uncertain', role_uncertain=True, native_label=int(classes[i]), native_index=i,
            score=float(scores[i]), box=np.asarray(prediction['boxes'][i]).tolist(),
            visibility='unknown', occlusion='unknown', blur='unknown', tiny_ball='unknown',
            source='model-inferred', independent_semantic_validation=False)
    labels[~valid] = -1
    visible = {str(int(i)) for i in np.unique(labels) if i > 0}
    metadata = {i: v for i, v in metadata.items() if i in visible}
    for iid, row in metadata.items():
        row['proxy_mask_area'] = int((labels == int(iid)).sum())
        row['proxy_tiny_ball'] = row['class'] == 'basketball' and row['proxy_mask_area'] <= 100
    return labels, metadata


def pair_proposals(images, pairs):
    lookup = {Identity(**r['identity']).key(): r for r in images}
    results = []
    for pair in pairs:
        rows = [lookup[Identity('reconstruction', pair['camera'], pair['pair_start'] + d).key()]
                for d in (0, 1)]
        arrays = []
        for row in rows:
            with load_array(row['final_layers']) as data:
                arrays.append({k: data[k] for k in ('instances', 'valid')})
        associations = []
        for semantic in ('person', 'basketball'):
            ids = [[int(i) for i, m in r['instances'].items() if m['class'] == semantic] for r in rows]
            matched = instance_matching(arrays[1]['instances'], arrays[0]['instances'], ids[1], ids[0],
                                        arrays[0]['valid'] & arrays[1]['valid'])
            associations += [dict(first_id=m['truth_id'], second_id=m['prediction_id'],
                                  proxy_iou=m['iou'], status='model-inferred', eligible=False)
                             for m in matched['matches']]
            associations += [dict(first_id=i, second_id=None, status='unknown', eligible=False)
                             for i in matched['unmatched_truth']]
            associations += [dict(first_id=None, second_id=i, status='unknown', eligible=False)
                             for i in matched['unmatched_predictions']]
        results.append(dict(camera=pair['camera'], pair_start=pair['pair_start'], associations=associations,
                            source='same-class fixed IoU>=0.5 matching; births/absence/identity unverified'))
    return results


def _save_png(path, array):
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or not cv2.imwrite(str(path), array):
        raise ValueError('review image already exists or could not be saved')
    return file_record(path)


def generate(output, inputs, config, policy_record, checkpoint_record):
    import cv2
    import torch
    import torchvision
    from torchvision.models.detection import maskrcnn_resnet50_fpn_v2
    policy = check_policy(policy_record)
    verify_record(checkpoint_record)
    if not checkpoint_record['sha256'].startswith(policy['primary']['sha256_prefix']):
        raise ValueError('teacher checkpoint differs from policy')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'layers').mkdir()
    torch.set_num_threads(8)
    cv2.setNumThreads(8)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    model = maskrcnn_resnet50_fpn_v2(weights=None, weights_backbone=None,
                                    min_size=800, max_size=1333).to('cpu').float().eval()
    state = torch.load(checkpoint_record['path'], map_location='cpu', weights_only=True)
    model.load_state_dict(state, strict=True)
    del state
    bundle = template(inputs, config)
    bundle.update(schema=SCHEMA, status='proposal', evidence_kind='model-assisted-proxy',
        human_ground_truth=False, policy=policy_record, checkpoint=checkpoint_record,
        truth_source='independent teacher pseudo-labels; no human ground truth',
        contributors={'primary': dict(id=PRIMARY_ID, kind='model-cpu')},
        runtime=dict(torch=torch.__version__, torchvision=torchvision.__version__, device='cpu',
                     cpu_threads=8, deterministic_algorithms=True),
        unknowns=['unseen teacher false negatives', 'roles', 'motion', 'two-pixel boundary accuracy',
                  'temporal identities', 'static feature suitability', 'occlusion and blur strata'])
    sheet_rows, sheets = [], []
    started = time.monotonic()
    for index, row in enumerate(bundle['images']):
        rgb_record = verify_record(row['rgb'])
        bgr = cv2.imread(rgb_record['path'], cv2.IMREAD_COLOR)
        valid = load_array(row['valid'])
        if bgr is None or bgr.shape != (540, 960, 3) or valid.shape != (540, 960):
            raise ValueError('annotation image/footprint changed')
        tick = time.monotonic()
        tensor = torch.from_numpy(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float() / 255.
        with torch.inference_mode():
            prediction = {k: v.cpu().numpy() for k, v in model([tensor])[0].items()}
        labels, metadata = merge_teacher(prediction, valid)
        key = f'image-{index:03d}'
        layers = output / 'layers' / (key + '.npz')
        with layers.open('xb') as stream:
            np.savez_compressed(stream, instances=labels, valid=valid,
                                changing=np.zeros_like(valid), ignored=np.zeros_like(valid))
        row.update(final_layers=file_record(layers), instances=metadata,
            tags={k: 'unknown' for k in IMAGE_FLAGS},
            static_feature_review=[dict(index=p['index'], suitable='uncertain', source='unreviewed')
                                   for p in row['static_feature_locations']],
            eligibility=dict(person_union=True, basketball=True, changing=False, static=False,
                             roles=False, temporal=False, boundary='proxy-only'),
            status='model-proposal', primary_wall_seconds=time.monotonic() - tick,
            negative_labels_verified=False, native_detections=len(prediction['scores']))
        overlay = bgr.copy()
        for iid, record in metadata.items():
            color = (0, 230, 255) if record['class'] == 'basketball' else (80, 230, 60)
            mask = labels == int(iid)
            overlay[mask] = (.6 * overlay[mask] + .4 * np.asarray(color)).astype(np.uint8)
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, color, 1)
            yy, xx = np.nonzero(mask)
            cv2.putText(overlay, iid, (int(xx.min()), int(yy.min())), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
        row['review_overlay'] = _save_png(output / 'overlays' / (key + '.png'), overlay)
        row['ball_crops'] = []
        for iid, record in metadata.items():
            if record['class'] != 'basketball':
                continue
            yy, xx = np.nonzero(labels == int(iid))
            box = [max(0, int(xx.min()) - 32), max(0, int(yy.min()) - 32),
                   min(960, int(xx.max()) + 33), min(540, int(yy.max()) + 33)]
            x0, y0, x1, y1 = box
            crop = np.concatenate([bgr[y0:y1, x0:x1], overlay[y0:y1, x0:x1]], axis=1)
            row['ball_crops'].append(dict(id=iid, xyxy=box,
                image=_save_png(output / 'ball-crops' / f'{key}-id{iid}.png', crop)))
        title = np.zeros((32, 960, 3), np.uint8)
        caption = f"{index:03d} {Identity(**row['identity']).key()} people={sum(m['class']=='person' for m in metadata.values())} ball={len(row['ball_crops'])}"
        cv2.putText(title, caption, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
        sheet_rows.append(np.concatenate([title, overlay], axis=0))
        if len(sheet_rows) == 4 or index == len(bundle['images']) - 1:
            while len(sheet_rows) < 4:
                sheet_rows.append(np.zeros_like(sheet_rows[0]))
            sheet = np.concatenate([np.concatenate(sheet_rows[:2], axis=1),
                                    np.concatenate(sheet_rows[2:], axis=1)], axis=0)
            sheets.append(_save_png(output / 'sheets' / f'sheet-{len(sheets):03d}.png', sheet))
            sheet_rows = []
        print(f'annotation {index + 1}/{len(bundle["images"])} {caption} wall={time.monotonic()-tick:.2f}s', flush=True)
    del model
    bundle['pairs'] = pair_proposals(bundle['images'], bundle['pairs'])
    bundle['review_sheets'] = sheets
    bundle['primary_wall_seconds'] = time.monotonic() - started
    write_json(output / 'proposal.json', bundle)
    return bundle


def validate(bundle, inputs, config):
    """Require complete, hash-bound automated review without upgrading evidence."""
    if (bundle.get('schema') != SCHEMA or bundle.get('evidence_kind') != 'model-assisted-proxy' or
            bundle.get('human_ground_truth') is not False or bundle.get('status') != 'reviewed-proxy'):
        raise ValueError('reviewed proxy schema required; human-truth claims prohibited')
    check_policy(bundle['policy'])
    verify_record(bundle['checkpoint'])
    verify_record(bundle['proposal'])
    proposal = read_json(bundle['proposal']['path'])
    if proposal.get('schema') != SCHEMA or proposal['policy'] != bundle['policy']:
        raise ValueError('proposal amendment provenance changed')
    expected = template(inputs, config)
    parents = {Identity(**r['identity']).key(): r for r in expected['images']}
    primary_rows = {Identity(**r['identity']).key(): r for r in proposal['images']}
    rows = {Identity(**r['identity']).key(): r for r in bundle['images']}
    if len(rows) != 232 or len(bundle['images']) != 232 or set(rows) != set(parents):
        raise ValueError('all 232 images required exactly once')
    reviewer = bundle['contributors']['independent_review']
    if not reviewer.get('id') or reviewer['id'] == PRIMARY_ID or reviewer.get('kind') != 'independent-agent-and-script':
        raise ValueError('separate independent automated reviewer required')
    verify_record(reviewer['record'])
    decision = read_json(reviewer['record']['path'])
    if (decision.get('proposal_sha256') != bundle['proposal']['sha256'] or
            decision.get('reviewer_id') != reviewer['id'] or
            decision.get('candidate_outputs_seen') is not False or
            decision.get('review_scope') != 'automated-integrity-plus-documented-visual-inspection' or
            decision.get('status') != 'accepted-proxy-with-unknowns'):
        raise ValueError('missing independent candidate-blind decision')
    reviews = {Identity(**r['identity']).key(): r for r in decision['images']}
    if len(reviews) != 232 or len(decision['images']) != 232 or set(reviews) != set(rows):
        raise ValueError('all 232 per-image independent review records required')
    for key, row in rows.items():
        for field in ('rgb', 'K', 'grid', 'valid', 'static_feature_locations'):
            if row[field] != parents[key][field]:
                raise ValueError('changed annotation image/grid/feature provenance')
        if row['final_layers'] != primary_rows[key]['final_layers'] or row['instances'] != primary_rows[key]['instances']:
            raise ValueError('unexpected correction; a separately reviewed revision is required')
        review = reviews[key]
        if (review.get('layers_sha256') != row['final_layers']['sha256'] or
                review.get('integrity') != 'passed' or not review.get('unknowns_retained') or
                row.get('status') != 'reviewed-proxy' or row.get('negative_labels_verified') is not False):
            raise ValueError('unreviewed image or improperly resolved teacher uncertainty')
        if row['eligibility'] != primary_rows[key]['eligibility']:
            raise ValueError('review cannot silently upgrade unknown eligibility')
        with load_array(row['final_layers']) as layers:
            if set(layers.files) != {'instances', 'valid', 'ignored', 'changing'}:
                raise ValueError('incomplete proxy layers')
            valid = load_array(row['valid'])
            labels = layers['instances']
            if any(layers[k].shape != (540, 960) for k in layers.files) or labels.dtype != np.int32:
                raise ValueError('proxy shape/dtype mismatch')
            if any(layers[k].dtype != np.bool_ for k in ('valid', 'ignored', 'changing')):
                raise ValueError('proxy validity dtype mismatch')
            if not np.array_equal(valid, layers['valid']) or (labels[~valid] != -1).any() or (labels[valid] < 0).any():
                raise ValueError('proxy footprint mismatch')
            if {str(int(i)) for i in np.unique(labels) if i > 0} != set(row['instances']):
                raise ValueError('missing proxy instance metadata')
        features = row['static_feature_review']
        if len(features) != len(parents[key]['static_feature_locations']) or any(
                f['index'] != p['index'] or f.get('suitable') != 'uncertain'
                for f, p in zip(features, parents[key]['static_feature_locations'])):
            raise ValueError('feature uncertainty changed without individual review')
    if bundle['pairs'] != proposal['pairs'] or len(bundle['pairs']) != 112:
        raise ValueError('pair association proposal changed or incomplete')
    for pair in bundle['pairs']:
        for field, offset in [('first_id', 0), ('second_id', 1)]:
            key = Identity('reconstruction', pair['camera'], pair['pair_start'] + offset).key()
            ids = [a[field] for a in pair['associations'] if a[field] is not None]
            if len(ids) != len(set(ids)) or set(ids) != set(map(int, rows[key]['instances'])):
                raise ValueError('pair proposal must cover each visible proxy ID once')
        if any(a.get('eligible') is not False for a in pair['associations']):
            raise ValueError('inferred temporal identity cannot be scored as reviewed truth')
    return dict(status='reviewed-proxy', evidence_kind='model-assisted-proxy', human_ground_truth=False,
                images=232, pairs=112, frozen_annotation_sha256=object_hash(bundle),
                reviewer=reviewer, policy=bundle['policy'], unknowns=bundle['unknowns'])


def finish_review(output, inputs, config):
    output = Path(output)
    proposal_record = file_record(output / 'proposal.json')
    bundle = read_json(proposal_record['path'])
    decision_record = file_record(output / 'review/decision.json')
    decision = read_json(decision_record['path'])
    bundle.update(status='reviewed-proxy', proposal=proposal_record)
    bundle['contributors']['independent_review'] = dict(id=decision['reviewer_id'],
        kind='independent-agent-and-script', record=decision_record)
    for row in bundle['images']:
        row.update(status='reviewed-proxy', primary_revision=row['final_layers'],
                   review_record=decision_record,
                   adjudication=dict(action='retain proposal and unresolved uncertainties',
                                     review_sha256=decision_record['sha256'],
                                     final_layers_sha256=row['final_layers']['sha256']))
    validation = validate(bundle, inputs, config)
    write_json(output / 'annotations.json', bundle)
    write_json(output / 'validation.json', validation)
    write_json(output / 'result.json', dict(status='complete', evidence_kind='model-assisted-proxy',
               annotations=file_record(output / 'annotations.json'), validation=file_record(output / 'validation.json')))


def run(request, output, config):
    verify_record(request['inputs'])
    inputs = read_json(request['inputs']['path'])
    generate(output, inputs, config, request['policy'], request['checkpoint'])
    print('Primary proposals frozen; waiting for independent review/decision.json', flush=True)
    while not (Path(output) / 'review/decision.json').exists():
        time.sleep(1.)
    finish_review(output, inputs, config)
