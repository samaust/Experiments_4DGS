"""Independent, CPU-only integrity and recorded visual review of teacher proxies.

This module does not import the teacher, candidate implementations, or their
validators. It reads only the frozen annotation template's RGB/valid records,
the proposal, and its annotation artifacts. Visual inspection is an explicit
reviewer attestation; successful array checks cannot create that attestation.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

from .files import file_record, read_json, safe_path


SCHEMA = 'vipe-benchmark-independent-proxy-review/v1'
PRIMARY_ID = 'torchvision-maskrcnn-resnet50-fpn-v2-coco-v1-cpu'
IMAGE_FLAGS = {'stationary_people', 'spectators', 'shadows', 'changing_displays',
               'illumination_changes', 'uncertain_motion'}
ELIGIBILITY = dict(person_union=True, basketball=True, changing=False, static=False,
                   roles=False, temporal=False, boundary='proxy-only')
LIMITS = [
    'Model-produced labels and non-detections are proxies, not human ground truth.',
    'Visual sheet review can identify gross failures but does not verify mask boundaries.',
    'Tiny-ball and two-pixel boundary accuracy remain unverified.',
    'A non-detection never establishes that a ball or person is absent.',
    'Roles, changing/static labels, motion, temporal identities, occlusion and blur remain unknown.',
    'All 768 fixed feature suitability decisions remain uncertain.',
    'Teacher proposals are retained unchanged; suspected errors require separately reviewed revisions.',
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity_key(row):
    value = row['identity'] if 'identity' in row else row
    require(set(value) == {'branch', 'camera', 'frame', 'pair_start'}, 'identity fields changed')
    require(value['branch'] in ('calibration', 'reconstruction') and
            type(value['camera']) is int and type(value['frame']) is int and
            value['pair_start'] is None, 'invalid annotation identity')
    return f"{value['branch']}/camera{value['camera']}/frame{value['frame']}"


def index_rows(rows):
    result = {}
    for row in rows:
        key = identity_key(row)
        require(key not in result, 'duplicate annotation identity')
        result[key] = row
    return result


def atomic_exclusive_json(path, value):
    """Publish complete JSON exactly once, with no partially visible decision."""
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, indent=2, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Exclusive publication; existing evidence is never replaced.
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Reader:
    def __init__(self, template, proposal_path):
        self.annotation_root = safe_path(proposal_path).resolve().parent
        self.allowed_inputs = {safe_path(row[field]['path']).resolve()
                               for row in template['images'] for field in ('rgb', 'valid')}
        self.records = {}

    def record(self, record, kind):
        path = safe_path(record['path']).resolve()
        if kind == 'input':
            require(path in self.allowed_inputs, 'input outside exact annotation template')
        else:
            require(path.is_relative_to(self.annotation_root / kind), 'artifact outside review allowlist')
        if str(path) not in self.records:
            self.records[str(path)] = file_record(path)
        actual = self.records[str(path)]
        require(actual['sha256'] == record['sha256'] and actual['bytes'] == record['bytes'],
                f'file hash/size mismatch: {path}')
        return actual

    def array(self, record, kind):
        return np.load(self.record(record, kind)['path'], allow_pickle=False)

    def image(self, record, kind, size):
        with Image.open(self.record(record, kind)['path']) as image:
            require(image.format == 'PNG' and image.mode == 'RGB' and image.size == size,
                    'RGB/overlay/crop image format or dimensions changed')
            image.load()


def audit_image(row, parent, reader):
    key = identity_key(row)
    for field in ('identity', 'rgb', 'valid', 'K', 'grid', 'static_feature_locations'):
        require(row[field] == parent[field], f'{key}: template provenance changed: {field}')
    expected_grid = ('distorted-opencv-integer' if row['identity']['branch'] == 'calibration'
                     else 'undistorted-opencv-integer')
    K = np.asarray(row['K'], dtype=float)
    require(row['grid'] == expected_grid and K.shape == (3, 3) and np.isfinite(K).all()
            and K[0, 0] > 0 and K[1, 1] > 0 and np.array_equal(K[2], [0, 0, 1]),
            f'{key}: wrong grid/intrinsics')
    require(row['status'] == 'model-proposal' and row['negative_labels_verified'] is False,
            f'{key}: unverified negatives promoted')
    require(row['eligibility'] == ELIGIBILITY and row['tags'] == {k: 'unknown' for k in IMAGE_FLAGS},
            f'{key}: unknown eligibility/strata promoted')
    reader.image(row['rgb'], 'input', (960, 540))
    reader.image(row['review_overlay'], 'overlays', (960, 540))
    valid = reader.array(row['valid'], 'input')
    require(valid.dtype == np.bool_ and valid.shape == (540, 960), f'{key}: invalid source footprint')
    with reader.array(row['final_layers'], 'layers') as layers:
        require(set(layers.files) == {'instances', 'valid', 'ignored', 'changing'}, f'{key}: layer schema')
        arrays = {field: layers[field] for field in layers.files}
    require(all(a.shape == (540, 960) for a in arrays.values()), f'{key}: layer dimensions')
    labels = arrays['instances']
    require(labels.dtype == np.int32 and all(arrays[f].dtype == np.bool_
            for f in ('valid', 'ignored', 'changing')), f'{key}: layer dtypes')
    require(np.array_equal(valid, arrays['valid']) and (labels[~valid] == -1).all()
            and (labels[valid] >= 0).all(), f'{key}: footprint mismatch')
    require(not arrays['ignored'].any() and not arrays['changing'].any(),
            f'{key}: proxy cannot infer changing/ignored truth')
    ids, sizes = np.unique(labels[labels > 0], return_counts=True)
    areas = {str(int(i)): int(n) for i, n in zip(ids, sizes)}
    require(set(row['instances']) == set(areas), f'{key}: orphan/missing instance metadata')
    for iid, meta in row['instances'].items():
        require(meta['class'] in ('person', 'basketball') and meta['native_label'] ==
                (1 if meta['class'] == 'person' else 37), f'{key}/{iid}: semantic metadata')
        require(type(meta['native_index']) is int and meta['native_index'] >= 0 and
                str(meta['native_index'] + 1) == iid, f'{key}/{iid}: teacher identity metadata')
        require(math.isfinite(meta['score']) and .5 <= meta['score'] <= 1, f'{key}/{iid}: teacher score')
        box = np.asarray(meta['box'], dtype=float)
        require(box.shape == (4,) and np.isfinite(box).all() and
                0 <= box[0] <= box[2] <= 960 and 0 <= box[1] <= box[3] <= 540,
                f'{key}/{iid}: teacher box')
        require(meta['role'] == 'uncertain' and meta['role_uncertain'] is True and
                all(meta[f] == 'unknown' for f in ('visibility', 'occlusion', 'blur', 'tiny_ball')) and
                meta['source'] == 'model-inferred' and meta['independent_semantic_validation'] is False,
                f'{key}/{iid}: metadata uncertainty promoted')
        require(meta['proxy_mask_area'] == areas[iid] and meta['proxy_tiny_ball'] is
                (meta['class'] == 'basketball' and areas[iid] <= 100), f'{key}/{iid}: mask area metadata')
    features = row['static_feature_review']
    points = parent['static_feature_locations']
    require(len(features) == len(points) and len({p['index'] for p in points}) == len(points),
            f'{key}: fixed feature coverage')
    for feature, point in zip(features, points):
        require(feature == dict(index=point['index'], suitable='uncertain', source='unreviewed'),
                f'{key}: fixed feature uncertainty changed')
        uv = np.asarray(point['uv'], dtype=float)
        require(uv.shape == (2,) and np.isfinite(uv).all() and
                0 <= uv[0] < 960 and 0 <= uv[1] < 540, f'{key}: feature coordinates')
    balls = {iid for iid, meta in row['instances'].items() if meta['class'] == 'basketball'}
    require(len(row['ball_crops']) == len(balls) and {crop['id'] for crop in row['ball_crops']} == balls,
            f'{key}: ball crop coverage')
    for crop in row['ball_crops']:
        y, x = np.nonzero(labels == int(crop['id']))
        box = [max(0, int(x.min()) - 32), max(0, int(y.min()) - 32),
               min(960, int(x.max()) + 33), min(540, int(y.max()) + 33)]
        require(crop['xyxy'] == box, f'{key}: crop coordinates')
        reader.image(crop['image'], 'ball-crops', (2 * (box[2] - box[0]), box[3] - box[1]))
        with Image.open(row['rgb']['path']) as rgb, Image.open(row['review_overlay']['path']) as overlay:
            with Image.open(crop['image']['path']) as shown:
                expected = np.concatenate((np.asarray(rgb.crop(box)), np.asarray(overlay.crop(box))), axis=1)
                require(np.array_equal(np.asarray(shown), expected), f'{key}: crop pixels mismatch')
    return dict(identity=row['identity'], layers_sha256=row['final_layers']['sha256'], integrity='passed',
                unknowns_retained=True, review_mode='structural-only', visual_findings=[],
                instance_counts=dict(Counter(m['class'] for m in row['instances'].values())),
                valid_pixels=int(valid.sum()), labeled_pixels=int((labels > 0).sum()),
                uncertain_features=len(features), ball_crops=row['ball_crops'])


def audit_pairs(pairs, parents, images):
    keys = [(p['camera'], p['pair_start']) for p in pairs]
    require(len(keys) == 112 and len(set(keys)) == 112 and set(keys) ==
            {(p['camera'], p['pair_start']) for p in parents}, '112 exact unique pairs required')
    for pair in pairs:
        require(isinstance(pair['associations'], list), 'missing pair associations')
        sides = []
        for field, offset in (('first_id', 0), ('second_id', 1)):
            key = f"reconstruction/camera{pair['camera']}/frame{pair['pair_start'] + offset}"
            require(key in images, 'pair image missing')
            sides.append(images[key]['instances'])
            ids = [a[field] for a in pair['associations'] if a[field] is not None]
            require(all(type(i) is int for i in ids) and len(ids) == len(set(ids)) and
                    set(ids) == set(map(int, images[key]['instances'])), 'pair identity coverage')
        for association in pair['associations']:
            first, second = association['first_id'], association['second_id']
            require(first is not None or second is not None, 'empty pair association')
            require(association.get('eligible') is False, 'temporal uncertainty promoted')
            if first is not None and second is not None:
                require(association['status'] == 'model-inferred' and
                        sides[0][str(first)]['class'] == sides[1][str(second)]['class'] and
                        math.isfinite(association['proxy_iou']) and .5 <= association['proxy_iou'] <= 1,
                        'invalid inferred pair association')
            else:
                require(association['status'] == 'unknown', 'unmatched identity uncertainty promoted')


def audit(template_path, proposal_path):
    template_record, proposal_record = file_record(template_path), file_record(proposal_path)
    template, proposal = read_json(template_path), read_json(proposal_path)
    require(proposal.get('schema') == 'vipe-benchmark-automated-annotations/v1' and
            proposal.get('status') == 'proposal' and proposal.get('evidence_kind') == 'model-assisted-proxy'
            and proposal.get('human_ground_truth') is False and
            proposal.get('blinded_to_candidate_outputs') is True, 'proposal must remain a blinded proxy')
    require(proposal['contributors']['primary'] == dict(id=PRIMARY_ID, kind='model-cpu'), 'teacher identity changed')
    require(set(proposal['unknowns']) >= {'roles', 'motion', 'two-pixel boundary accuracy',
            'temporal identities', 'static feature suitability', 'occlusion and blur strata',
            'unseen teacher false negatives'}, 'proposal unknowns removed')
    parents, rows = index_rows(template['images']), index_rows(proposal['images'])
    require(len(rows) == len(parents) == 232 and set(rows) == set(parents), '232 exact unique images required')
    require(sum(len(r['static_feature_locations']) for r in parents.values()) == 768, '768 fixed features required')
    require(len({r['final_layers']['path'] for r in rows.values()}) == 232, 'layer path reused across images')
    reader = Reader(template, proposal_path)
    reviewed = [audit_image(row, parents[identity_key(row)], reader) for row in proposal['images']]
    audit_pairs(proposal['pairs'], template['pairs'], rows)
    require(len(proposal['review_sheets']) == 58, '58 indexed four-image sheets required')
    require(len({r['path'] for r in proposal['review_sheets']}) == 58, 'duplicate sheet record')
    for i, sheet in enumerate(proposal['review_sheets']):
        reader.image(sheet, 'sheets', (1920, 1144))
        with Image.open(sheet['path']) as image:
            for j, row in enumerate(proposal['images'][4 * i:4 * i + 4]):
                with Image.open(row['review_overlay']['path']) as overlay:
                    x, y = (j % 2) * 960, (j // 2) * 572 + 32
                    require(image.crop((x, y, x + 960, y + 540)).tobytes() == overlay.tobytes(),
                            'review sheet image ordering/pixels mismatch')
    return dict(schema=SCHEMA, status='integrity-passed', candidate_outputs_seen=False,
                template=template_record, proposal=proposal_record, images=reviewed,
                pairs=len(proposal['pairs']), uncertain_features=sum(r['uncertain_features'] for r in reviewed),
                sheet_count=58, ball_crop_count=sum(len(r['ball_crops']) for r in reviewed),
                inspected_file_hashes=list(reader.records.values()), evidence_limits=LIMITS,
                audit_source=file_record(__file__), completed_utc=datetime.now(timezone.utc).isoformat())


def rgb_sheets(template_path, review_dir):
    """Create native-resolution RGB-first sheets; no model output is used."""
    template = read_json(template_path)
    require(len(index_rows(template['images'])) == 232, '232 unique RGB inputs required')
    output = safe_path(review_dir)
    manifest = []
    for i in range(58):
        sheet = Image.new('RGB', (1920, 1144))
        draw = ImageDraw.Draw(sheet)
        identities = []
        for j, row in enumerate(template['images'][4 * i:4 * i + 4]):
            record = file_record(row['rgb']['path'], row['rgb']['sha256'])
            x, y = (j % 2) * 960, (j // 2) * 572
            key = identity_key(row)
            with Image.open(record['path']) as rgb:
                require(rgb.mode == 'RGB' and rgb.size == (960, 540), 'RGB dimensions changed')
                sheet.paste(rgb, (x, y + 32))
            draw.text((x + 8, y + 8), f'{4 * i + j:03d} {key} RGB ONLY', fill='white')
            identities.append(row['identity'])
        path = output / 'rgb-sheets' / f'sheet-{i:03d}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            sheet.save(stream, format='PNG')
        manifest.append(dict(index=i, identities=identities, image=file_record(path)))
    atomic_exclusive_json(output / 'rgb-sheets.json', dict(template=file_record(template_path), sheets=manifest))
    return manifest


def ball_sheets(proposal_path, review_dir):
    """Pack each RGB/overlay ball crop at its original pixel size, without resizing."""
    proposal = read_json(proposal_path)
    root = safe_path(proposal_path).resolve().parent
    crops = [dict(identity=row['identity'], image_index=i, **crop)
             for i, row in enumerate(proposal['images']) for crop in row['ball_crops']]
    output = safe_path(review_dir)
    sheets = []
    for i in range(0, len(crops), 12):
        batch = crops[i:i + 12]
        images = []
        for crop in batch:
            path = safe_path(crop['image']['path']).resolve()
            require(path.is_relative_to(root / 'ball-crops'), 'ball crop outside review allowlist')
            require(file_record(path) == crop['image'], 'ball crop hash changed')
            with Image.open(path) as original:
                images.append(original.copy())
        width, height = max(im.width for im in images), max(im.height for im in images) + 32
        sheet = Image.new('RGB', (3 * width, math.ceil(len(batch) / 3) * height))
        draw = ImageDraw.Draw(sheet)
        rows = []
        for j, (crop, crop_image) in enumerate(zip(batch, images)):
            x, y = (j % 3) * width, (j // 3) * height
            draw.text((x + 2, y + 8), f"{crop['image_index']:03d} id{crop['id']} RGB | proxy", fill='white')
            sheet.paste(crop_image, (x, y + 32))
            rows.append(dict(crop, displayed_xyxy=[x, y + 32, x + crop_image.width, y + 32 + crop_image.height],
                             original_pixels_preserved=True))
        path = output / 'ball-sheets' / f'sheet-{i // 12:03d}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            sheet.save(stream, format='PNG')
        sheets.append(dict(index=i // 12, image=file_record(path), crops=rows))
    atomic_exclusive_json(output / 'ball-sheets.json', dict(proposal=file_record(proposal_path), sheets=sheets,
                                                          crops=len(crops), resampling=False))
    return sheets


def finalize(audit_path, observations_path, output, reviewer_id, source_paths=()):
    """Rehash evidence, bind actual visual coverage, then publish decision LAST."""
    audit_result, observations = read_json(audit_path), read_json(observations_path)
    require(audit_result['schema'] == SCHEMA and audit_result['status'] == 'integrity-passed', 'integrity audit required')
    require(reviewer_id and reviewer_id != PRIMARY_ID, 'independent reviewer required')
    require(observations.get('reviewer_id') == reviewer_id and
            observations.get('candidate_outputs_seen') is False and
            observations.get('actual_visual_inspection') is True, 'explicit candidate-blind visual attestation required')
    require(observations['proposal_sha256'] == audit_result['proposal']['sha256'], 'visual proposal hash changed')
    audit_rows = index_rows(audit_result['images'])
    visual_rows = index_rows(observations['images'])
    require(set(visual_rows) <= set(audit_rows), 'visual observation identity outside audit')
    require(len(audit_rows) == 232 and audit_result['pairs'] == 112 and
            audit_result['uncertain_features'] == 768, 'incomplete integrity audit')
    verified_records = [audit_result['template'], audit_result['proposal'], audit_result['audit_source'],
                        *audit_result['inspected_file_hashes'], *observations['viewed_files']]
    for record in verified_records:
        require(file_record(record['path']) == record, f'evidence changed before finalization: {record["path"]}')
    require(observations['viewed_files'], 'no actually inspected visual files recorded')
    viewed = {record['sha256'] for record in observations['viewed_files']}
    result_rows = []
    for key, row in audit_rows.items():
        result = dict(row)
        if key in visual_rows:
            visual = visual_rows[key]
            require(visual['review_mode'] in ('integrity-and-native-sheet-visual',
                    'integrity-native-sheet-and-crop-visual') and visual['visual_findings'] and
                    visual['viewed_file_sha256s'] and set(visual['viewed_file_sha256s']) <= viewed,
                    'visual review requires findings and inspected file hashes')
            result.update(review_mode=visual['review_mode'], visual_findings=visual['visual_findings'],
                          viewed_file_sha256s=visual['viewed_file_sha256s'])
        result_rows.append(result)
    decision = dict(schema=SCHEMA, status='accepted-proxy-with-unknowns', reviewer_id=reviewer_id,
        proposal_sha256=audit_result['proposal']['sha256'], candidate_outputs_seen=False,
        review_scope='automated-integrity-plus-documented-visual-inspection',
        images=result_rows, pairs=112, uncertain_features_retained=768,
        actual_visual_identities=[r['identity'] for r in observations['images']],
        structural_only_identities=[r['identity'] for k, r in audit_rows.items() if k not in visual_rows],
        visual_observations=file_record(observations_path), integrity_audit=file_record(audit_path),
        inspected_file_hashes=verified_records, source_hashes=[file_record(__file__),
            *[file_record(p) for p in source_paths]], evidence_limits=LIMITS,
        gross_findings=observations.get('gross_findings', []),
        completed_utc=datetime.now(timezone.utc).isoformat())
    atomic_exclusive_json(output, decision)
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('audit')
    check.add_argument('--template', required=True)
    check.add_argument('--proposal', required=True)
    check.add_argument('--output', required=True)
    sheets = sub.add_parser('rgb-sheets')
    sheets.add_argument('--template', required=True)
    sheets.add_argument('--output', required=True)
    crops = sub.add_parser('ball-sheets')
    crops.add_argument('--proposal', required=True)
    crops.add_argument('--output', required=True)
    finish = sub.add_parser('finalize')
    finish.add_argument('--audit', required=True)
    finish.add_argument('--observations', required=True)
    finish.add_argument('--output', required=True)
    finish.add_argument('--reviewer-id', required=True)
    finish.add_argument('--source', action='append', default=[])
    args = parser.parse_args()
    if args.command == 'audit':
        result = audit(args.template, args.proposal)
        atomic_exclusive_json(args.output, result)
        print(json.dumps(dict(status=result['status'], images=len(result['images']), pairs=result['pairs'],
                              uncertain_features=result['uncertain_features'], ball_crops=result['ball_crop_count'])))
    elif args.command == 'rgb-sheets':
        print(json.dumps(dict(rgb_sheets=len(rgb_sheets(args.template, args.output)))))
    elif args.command == 'ball-sheets':
        print(json.dumps(dict(ball_sheets=len(ball_sheets(args.proposal, args.output)))))
    else:
        result = finalize(args.audit, args.observations, args.output, args.reviewer_id, args.source)
        print(json.dumps(dict(status=result['status'], images=len(result['images']),
                              visually_inspected=len(result['actual_visual_identities']))))


if __name__ == '__main__':
    main()
