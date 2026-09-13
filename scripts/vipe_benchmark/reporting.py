"""Render frozen comparisons once; no rescoring, fitting or model selection."""
from collections import Counter
import math

from .config import jobs, training_cameras
from .files import file_record, read_json, safe_path, verify_record, write_json


DOMAINS = ('calibration/fit', 'calibration/selection', 'reconstruction/reconstruction')
STRATA = ('all', 'occlusion', 'blur', 'tiny_ball', 'stationary_people', 'spectators', 'shadows', 'changing_displays')
MASK_BASELINES = {**{f'S{i}': 'S0' for i in range(1, 5)}, 'M1': 'M0', 'M2': 'M0'}
CORE = [('pixel', 'person', 'dice'), ('pixel', 'basketball', 'dice'),
        ('boundary', 'semantic_foreground', 'f1'), ('pixel', 'usable_static', 'dice')]


def _finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def _number(value):
    return f'{value:.6g}' if _finite(value) else 'unverified'


def _interval(value):
    return value if isinstance(value, (list, tuple)) and len(value) == 2 and all(map(_finite, value)) and value[0] <= value[1] else None


def _estimate(value, interval=None):
    limits = _interval(interval)
    return _number(value) + (f' [{_number(limits[0])}, {_number(limits[1])}]' if limits else ' [CI unverified]')


def _range(values):
    values = [v for v in values if _finite(v)]
    return [min(values), max(values)] if values else None


def _range_text(values):
    limits = _range(values)
    return '–'.join(map(_number, limits)) if limits else 'unverified'


def _cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _table(lines, headers, rows):
    lines.extend(['', '| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'])
    lines.extend('| ' + ' | '.join(_cell(value) for value in row) + ' |' for row in rows)
    lines.append('')


def _link(record, title):
    return f"[{title}](<{record['path']}>)" if record and 'path' in record else title + ' unavailable'


class Evidence:
    def __init__(self):
        self.documents = {}

    def read(self, record):
        key = record['path'], record['sha256']
        if key not in self.documents:
            self.documents[key] = read_json(verify_record(record)['path'])
        return self.documents[key]

    def optional(self, record):
        return self.read(record) if record and 'path' in record else {}


def _direction(kind, metric, field, scope):
    # Directions describe existing named metrics, never a new stack score.
    if scope != 'masks':
        return None
    if kind in ('pixel', 'boundary', 'instance', 'role_instance'):
        return -1 if field == 'negative_false_positive_pixels_per_negative_image' else 1
    if kind == 'temporal':
        return -1 if field in ('id_switch_fraction', 'missing_successor_fraction', 'area_change_error') else 1
    if kind == 'tiny_ball':
        return {'recall': 1, 'center_error_pixels': -1}.get(field)
    return {'foreground_leakage': -1, 'retained_static_area': 1, 'retained_static_features': 1,
            'automatic_sift_retention': 1, 'automatic_sift_grid_retention': 1,
            'accepted_map_observation_retention': 1}.get(metric)


def _difference(score, candidate, baseline):
    differences = score.get('differences', {})
    if candidate + '-' + baseline in differences:
        return differences[candidate + '-' + baseline]
    reverse = differences.get(baseline + '-' + candidate)
    if reverse is None:
        return {}
    interval = _interval(reverse.get('interval_95'))
    return dict(reverse, estimate=-reverse['estimate'] if _finite(reverse.get('estimate')) else None,
                interval_95=[-interval[1], -interval[0]] if interval else None)


def paired_rows(comparisons, baselines, source, *, scope):
    """Copy saved equal-camera comparisons and interpret their existing intervals."""
    result = []
    for group, comparison in sorted(comparisons.items()):
        parts = group.split('/')
        if len(parts) != 5:
            continue
        branch, window, stratum, kind, metric = parts
        for field, score in sorted(comparison.get('scores', {}).items()):
            for candidate, baseline in baselines.items():
                diff = _difference(score, candidate, baseline)
                interval = _interval(diff.get('interval_95'))
                eligible = comparison.get('status') == 'complete' and not any(
                    m in comparison.get('ineligible', {}) for m in (candidate, baseline)) and all(
                    _finite(score.get('estimates', {}).get(m)) for m in (candidate, baseline))
                direction = _direction(kind, metric, field, scope)
                if not eligible or not _finite(diff.get('estimate')) or not interval:
                    conclusion = 'unverified'
                elif interval[0] <= 0 <= interval[1]:
                    conclusion = 'inconclusive'
                elif direction is None:
                    conclusion = 'increase' if interval[0] > 0 else 'decrease'
                else:
                    favorable = interval[0] > 0 if direction > 0 else interval[1] < 0
                    conclusion = 'improvement' if favorable else 'regression'
                result.append(dict(scope=scope, domain=branch+'/'+window, stratum=stratum, kind=kind,
                    metric=metric, field=field, candidate=candidate, baseline=baseline,
                    estimate=diff.get('estimate') if eligible else None, interval_95=interval if eligible else None,
                    conclusion=conclusion, defined_resamples=diff.get('defined_resamples'),
                    estimates={m: score.get('estimates', {}).get(m) for m in (baseline, candidate)},
                    estimate_intervals={m: score.get('interval_95', {}).get(m) for m in (baseline, candidate)},
                    per_camera={m: score.get('per_camera', {}).get(m) for m in (baseline, candidate)},
                    per_camera_extrema={m: score.get('per_camera_extrema', {}).get(m) for m in (baseline, candidate)},
                    undefined_cameras={m: score.get('undefined_cameras', {}).get(m) for m in (baseline, candidate)},
                    unavailable={m: comparison.get('ineligible', {}).get(m) for m in (baseline, candidate)},
                    evidence_kinds=comparison.get('evidence_kinds', []), source=source, source_group=group,
                    interpretation='named saved metric only; correlated fields are not independent wins or a combined ranking'))
    return result


def _score(comparisons, domain, kind, metric, field, method):
    comparison = comparisons.get(f'{domain}/all/{kind}/{metric}', {})
    if comparison.get('status') != 'complete' or method in comparison.get('ineligible', {}):
        return {}
    return comparison.get('scores', {}).get(field, {})


def _worst(score, method):
    cameras = score.get('per_camera', {}).get(method, {})
    defined = {c: v for c, v in cameras.items() if _finite(v)}
    undefined = score.get('undefined_cameras', {}).get(method)
    if not defined:
        return 'unverified'
    lowest = min(defined.values())
    ids = ','.join(str(c) for c, v in defined.items() if v == lowest)
    return f'{_number(lowest)} (camera {ids}; undefined {len(undefined) if undefined is not None else "unverified"})'


def _mask_report(lines, masks, paired, aggregate, reader):
    comparisons = masks.get('comparisons', {})
    lines += ['## Masks and motion', '',
        f"Generated primary mask rows: {masks.get('generated_primary_mask_rows', 'unverified')} / 6750; "
        f"scored unique annotation images: {masks.get('scored_unique_annotation_images', 'unverified')} / 232. "
        'Tracker-pair contexts remain distinct. Numbers below are equal-camera estimates with saved 95% intervals; '
        'undefined cameras are excluded explicitly, never assigned zero.']
    for domain in DOMAINS:
        lines += ['', domain + ':']
        rows = []
        for method in [f'S{i}' for i in range(5)] + [f'M{i}' for i in range(3)]:
            scores = [_score(comparisons, domain, *definition, method) for definition in CORE]
            values = [_estimate(s.get('estimates', {}).get(method), s.get('interval_95', {}).get(method)) if s else 'unverified / undefined' for s in scores]
            rows.append([method, *values, _worst(scores[0], method)+'; '+_worst(scores[1], method)])
        _table(lines, ['Method', 'Person Dice', 'Ball Dice', 'Foreground boundary F1', 'Static Dice', 'Worst person; ball'], rows)
    primary = {(r['domain'], r['candidate'], r['kind'], r['metric'], r['field']): r for r in paired
               if r['scope'] == 'masks' and r['stratum'] == 'all'}
    rows = []
    for domain in DOMAINS:
        for candidate, baseline in MASK_BASELINES.items():
            cells = []
            for definition in CORE:
                row = primary.get((domain, candidate, *definition), {})
                cells.append(_estimate(row.get('estimate'), row.get('interval_95')) + '; ' + row.get('conclusion', 'unverified'))
            rows.append([domain, candidate+' − '+baseline, *cells])
    _table(lines, ['Domain', 'Paired change', 'Person Dice Δ', 'Ball Dice Δ', 'Boundary F1 Δ', 'Static Dice Δ'], rows)
    rows = []
    for domain in DOMAINS:
        available, unavailable = [], []
        for stratum in STRATA:
            groups = [v for k, v in comparisons.items() if k.startswith(domain+'/'+stratum+'/')]
            defined = sum(any(_finite(value) for value in s.get('estimates', {}).values())
                          for group in groups for s in group.get('scores', {}).values())
            (available if defined else unavailable).append(stratum + (f' ({defined} fields)' if defined else ''))
        rows.append([domain, ', '.join(available) or 'none', ', '.join(unavailable) or 'none'])
    _table(lines, ['Domain', 'Strata with defined fields', 'Unverified / absent strata'], rows)
    lines += ['A defined stratum can still have unavailable individual fields. '
        'Class precision/recall/IoU/Dice, two-pixel boundary F1, instance matching, role precision bounds, '
        'tiny-ball recall/center/area, negative-image false positives, temporal switches/births/disappearances, '
        'static leakage, SIFT/grid and accepted-map retention remain in '+_link(aggregate['mask_metrics'], 'full mask metrics')+
        ' and '+_link(masks.get('raw_counts'), 'raw numerators/denominators')+'.']
    manifest = reader.optional(masks.get('final_static_masks'))
    if manifest:
        lines += ['', 'Final static artifacts: '+str(manifest.get('generated_rows', 'unverified'))+' / '+
                  str(manifest.get('expected_rows', 'unverified'))+' generated; '+
                  str(manifest.get('unavailable_rows', 'unverified'))+' unavailable. '+
                  _link(masks['final_static_masks'], 'Every static PNG and its exact segmentation/motion sources')+
                  ' is annotation-independent derived output, not static ground truth.']


def _geometry_details(document):
    rows, contexts = document.get('rows', []), document.get('contexts', [])
    details = {}
    for region in ('static', 'person', 'ball'):
        classes = [r.get('classes', {}).get(region, {}) for r in rows]
        histograms = [c.get('supporting_camera_histogram') for c in classes]
        histogram = {key: sum(h.get(key, 0) for h in histograms)
                     for key in sorted({key for h in histograms for key in h})} if histograms and all(h is not None for h in histograms) else None
        marginal = [0, 0, 0]
        marginal_complete = bool(contexts)
        for context in contexts:
            values = context.get('classes', {}).get(region, {}).get('marginal_coverage', [])
            if context.get('status') != 'complete' or len(values) != 3:
                marginal_complete = False
                continue
            for rank, value in enumerate(values):
                marginal[rank] += value['new_cells']
        details[region] = dict(supporting_camera_histogram=histogram,
            edge_parallax_ranges={field: _range([c.get('parallax_degrees', {}).get(field) for c in classes])
                                   for field in ('min', 'median', 'p95')},
            marginal_new_reference_cells_by_rank=marginal if marginal_complete else None)
    details['overlap'] = {name: _range([r.get('raw_normalized_overlap', {}).get(name) for r in rows])
                          for name in ('shared', 'jaccard')}
    details['sampling_shortage'] = sum(r['sampling']['shortage'] for r in rows) if rows and all('sampling' in r for r in rows) else None
    details['rejections'] = {key: sum(r['stages'].get(key, {}).get('rejected', 0) for r in rows)
                             for key in sorted({key for r in rows for key in r['stages']})} if rows and all('stages' in r for r in rows) else None
    return details


def _geometry_report(lines, aggregate, reader, states):
    details = {}
    for field, title in [('isolated_geometry_metrics', 'Isolated geometry'), ('combined_geometry_metrics', 'Combined geometry interactions')]:
        record = aggregate.get(field)
        lines += ['', '## '+title]
        if not record:
            lines += ['', 'Unverified: saved geometry metrics unavailable.']
            continue
        geometry = reader.read(record)
        overview, classes, costs = [], [], []
        for arm, slot in geometry.get('slots', {}).items():
            document = reader.optional(slot.get('result'))
            summary = slot.get('summary') or {}
            detail = _geometry_details(document)
            details[arm] = dict(detail, result=slot.get('result'), status=slot.get('status', 'unverified'))
            resource = document.get('resources', {})
            ledger_state = states.get(slot.get('reused_from') or arm, {})
            failures = summary.get('neighbor_failures')
            overview.append([arm, slot.get('status', 'unverified'),
                str(summary.get('complete_contexts', 'unverified'))+'/'+str(summary.get('expected_contexts', 64)),
                _number(summary.get('full_image_matches'))+'/'+_number(summary.get('crop_matches')),
                len(failures) if failures is not None else 'unverified',
                _number(summary.get('reciprocal_directed_edges'))+'/'+_number(summary.get('reciprocal_pairs')),
                _number(summary.get('foreground_reference_cells')),
                slot.get('reason') or _link(slot.get('result'), 'raw edges/contexts')])
            for region in ('static', 'person', 'ball'):
                counts = summary.get('classes', {}).get(region, {})
                hist = detail[region]['supporting_camera_histogram']
                parallax = detail[region]['edge_parallax_ranges']
                marginal = detail[region]['marginal_new_reference_cells_by_rank']
                velocity = 'not applicable' if region == 'static' else _number(counts.get('velocity_valid'))+'/'+_number(counts.get('accepted'))
                acceptance = _score(geometry.get('comparisons', {}), DOMAINS[2], 'fraction', 'accepted_'+region, 'fraction', arm)
                classes.append([arm, region, _number(counts.get('accepted'))+'/'+_number(counts.get('attempted')),
                    _estimate(acceptance.get('estimates', {}).get(arm), acceptance.get('interval_95', {}).get(arm)),
                    ', '.join(f'{k}:{v}' for k, v in hist.items()) if hist is not None else 'unverified', velocity,
                    ' / '.join('–'.join(map(_number, parallax[k])) if parallax[k] else 'unverified' for k in ('min', 'median', 'p95')),
                    '/'.join(map(str, marginal)) if marginal is not None else 'unverified'])
            costs.append([arm, _number(ledger_state.get('elapsed_seconds')), _number(document.get('wall_seconds')),
                _number(document.get('loading', {}).get('wall_seconds'))+'/'+_number(document.get('loading', {}).get('cuda_seconds')),
                _number(summary.get('synchronized_cuda_seconds')),
                '/'.join(_number(v / 2**30 if _finite(v) else None) for v in (
                    resource.get('peak_allocated_bytes'), resource.get('peak_reserved_bytes'), ledger_state.get('peak', {}).get('device_bytes'))),
                _number(document.get('input_bytes_unique'))+'/'+_number(document.get('output_bytes_before_result')),
                _number(detail['sampling_shortage'])])
        _table(lines, ['Arm', 'Status', 'Contexts', 'Full/crop matches', 'Neighbor failures', 'Reciprocal edges/pairs',
                       'Mean foreground cells', 'Evidence / reason'], overview)
        _table(lines, ['Arm', 'Class', 'Accepted/attempted', 'Equal-camera acceptance [95% CI]', 'Camera support histogram',
                       'Velocity-valid/accepted', 'Accepted parallax min/median/p95 edge ranges (°)', 'Marginal cells by rank'], classes)
        _table(lines, ['Arm', 'Supervised wall s', 'Worker wall s', 'Loading wall/CUDA s', 'Match/crop/solver CUDA s', 'Allocated/reserved/device GiB',
                       'Input/output bytes', 'Sample shortage'], costs)
        lines += ['Counts above retain directed-edge duplication. Parallax ranges summarize saved per-edge quantiles; '
            'they are not pooled point quantiles. Marginal counts sum newly covered reference cells by neighbor rank. '
            'Output bytes exclude the result manifest; supervised wall includes setup/loading, serialization and cleanup. '
            'The supervisor device peak is distinct from allocated/reserved memory. '+_link(record, 'Full equal-camera geometry comparisons')+
            ' preserves acceptance, velocity-valid fraction, spatial coverage and timing intervals. Raw edge links retain '
            'parallax, all support/rejection stages, shared/Jaccard overlap, candidate coverage and exact failures.']
    return details


def _controls_report(lines, masks, aggregate, reader, expected_cameras):
    lines += ['', '## Implementation controls and fixed repeats', '',
              'Controls compare implementations on matching RGB; S0/D0 are comparators, not annotation truth. '
              'Repeats are fixed repeatability checks and never select a method.']
    segmentation = reader.optional(masks.get('segmentation_control'))
    rows = [r for r in segmentation.get('rows', []) if r.get('status') == 'complete']
    if rows:
        lines += ['', f"S1/S0: {len(rows)} matched output contexts; instance-ID pixel disagreements "
            f"{sum(r['instance_id_pixel_disagreements'] for r in rows)}; person/ball union disagreements "
            f"{sum(r['semantic_union_disagreements']['person'] for r in rows)}/"
            f"{sum(r['semantic_union_disagreements']['basketball'] for r in rows)}. "
            'Local IDs are arbitrary; the semantic unions are separate comparisons.']
        fields = ('detector_rgb', 'detector_raw_token_logits', 'detector_raw_boxes_cxcywh',
                  'detector_selected_boxes_xyxy', 'detector_selected_scores')
        values = []
        for field in fields:
            items = [r.get('intermediate_arrays', {}).get(field, {}) for r in rows
                     if r.get('intermediate_arrays', {}).get('status') != 'not-applicable']
            values.append([field, sum(r.get('status') == 'complete' for r in items),
                sum(r.get('status') == 'recorded' for r in items), sum(r.get('status') not in ('complete', 'recorded') for r in items),
                _range_text([r.get('max_abs_difference') for r in items])])
        _table(lines, ['Native intermediate', 'Comparable contexts', 'Native rows recorded', 'Unavailable/different grids', 'Per-context max-abs difference range'], values)
    else:
        lines += ['', 'S1/S0 control unverified: matching completed outputs unavailable.']
    lines += [_link(masks.get('segmentation_control'), 'Full S1/S0 processor, phrase, overlap and actual intermediate evidence')+
              ' retains mismatched shapes and successor keyframe sources; selected boxes receive no guessed association.']
    depth = reader.optional(aggregate.get('depth_control'))
    values = []
    for stage in ('fit', 'check'):
        record = depth.get(stage, {})
        complete = [r for r in record.get('rows', []) if r.get('status') == 'complete']
        values.append([stage, f'{len(complete)}/{expected_cameras}',
            _range_text([r.get('mean_abs_depth') for r in complete]),
            _range_text([r.get('camera_scale_ratio_difference') for r in complete]),
            _range_text([r.get('camera_scale_ratio_relative_difference') for r in complete]),
            sum(r['sparse_validity_disagreement'] for r in complete) if complete else 'unverified'])
    _table(lines, ['D1/D0 phase', 'Compared cameras', 'Per-camera mean absolute depth difference range (m)',
                   'Camera ratio Δ range', 'Relative ratio Δ range', 'Sparse validity disagreements'], values)
    lines += [_link(aggregate.get('depth_control'), 'All D1/D0 per-camera support and ratios')+
              ' retains missing cameras; these ratios use frozen sparse samples and add no scale fit.']
    repeat_rows = []
    for name in ('R-S', 'R-D', 'R-G'):
        row = aggregate.get('repeats', {}).get(name, {})
        repeat = row.get('repeat')
        if row.get('status') != 'complete' or repeat is None:
            repeat_rows.append([name, row.get('status', 'unverified'), row.get('reason') or 'fixed repeat unavailable'])
        elif name == 'R-S':
            repeat_rows.extend([name, f"camera {r['identity']['camera']} frame {r['identity']['frame']}",
                f"{r['differing_pixels']} instance-ID pixel disagreements"] for r in repeat)
        elif name == 'R-D':
            repeat_rows.append([name, 'camera 1 frame 100',
                f"mean absolute depth Δ {_number(repeat.get('mean_abs_depth'))} m; validity disagreements "
                f"{_number(repeat.get('validity_disagreement'))}; camera ratio Δ {_number(repeat.get('camera_scale_ratio_difference'))}; "
                f"relative ratio Δ {_number(repeat.get('camera_scale_ratio_relative_difference'))}"])
        else:
            repeat_rows.extend([name, f"pair 20 reference 1 → {r['other']}",
                f"accepted {r['original_accepted']} → {r['repeated_accepted']}; count Δ {r['accepted_count_difference']}; "
                f"pointwise acceptance disagreements {_number(r.get('acceptance_disagreements'))}; "
                f"same sampled reference coordinates {r['same_sampled_reference_coordinates']}"] for r in repeat.get('edges', []))
    _table(lines, ['Repeat', 'Fixed context / status', 'Saved differences'], repeat_rows)


def run(request, output, config):
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    reader = Evidence()
    documents = {name: reader.read(request[name])
                 for name in ('inputs', 'annotations', 'aggregate', 'accounting', 'components', 'validation')}
    aggregate, annotations = documents['aggregate'], documents['annotations']
    if aggregate.get('status') != 'complete':
        raise ValueError('report requires the completed final aggregation checkpoint')
    schema = annotations.get('schema')
    proxy = schema == 'vipe-benchmark-automated-annotations/v1'
    if schema not in ('vipe-benchmark-annotations/v1', 'vipe-benchmark-automated-annotations/v1') or (
            proxy and (annotations.get('human_ground_truth') is not False or annotations.get('evidence_kind') != 'model-assisted-proxy')):
        raise ValueError('report annotation evidence is unknown or misrepresents human ground truth')
    if annotations.get('status') not in ('reviewed', 'complete', 'reviewed-adjudicated', 'reviewed-proxy'):
        raise ValueError('report requires reviewed annotation evidence')
    masks, frozen = reader.read(aggregate['mask_metrics']), reader.read(aggregate['finalists'])
    if masks.get('status') != 'complete' or frozen.get('status') != 'frozen' or frozen.get('mask_metrics') != aggregate['mask_metrics']:
        raise ValueError('report selections do not bind completed frozen mask metrics')
    if proxy and (masks.get('human_ground_truth') is not False or masks.get('evidence_kind') != 'model-assisted-proxy'):
        raise ValueError('proxy mask comparisons cannot claim human ground truth')
    if masks.get('annotations') and masks['annotations'] != request['annotations']:
        raise ValueError('report annotation evidence differs from the scored bundle')
    states = documents['accounting']['jobs']
    recoveries = documents['accounting'].get('setup_recovery_authorizations', [])
    reconstruction_recoveries = documents['accounting'].get('reconstruction_recovery_authorizations', [])
    expected = (set(jobs(config)) | {event['job_id'] for event in recoveries + reconstruction_recoveries}) - {'report'}
    unresolved = sorted(job for job in expected if states.get(job, {}).get('status') != 'complete')
    paired = paired_rows(masks.get('comparisons', {}), MASK_BASELINES, aggregate['mask_metrics'], scope='masks')
    for field, scope, baseline in [('isolated_geometry_metrics', 'isolated-geometry', 'G-S0'),
                                    ('combined_geometry_metrics', 'combined-interactions', 'C0')]:
        if aggregate.get(field):
            geometry = reader.read(aggregate[field])
            paired += paired_rows(geometry.get('comparisons', {}),
                {arm: baseline for arm in geometry.get('slots', {}) if arm != baseline}, aggregate[field], scope=scope)
    lines = ['# Plan 031 Basketball component comparison', '',
        f"{'Incomplete matrix' if unresolved else 'All allocated prerequisite slots completed'}: "
        f"{len(unresolved)} failed, blocked, skipped or unverified slots before report finalization. "
        'This bounded diagnostic does not establish production readiness or physical accuracy.', '',
        f"Annotation evidence: {'candidate-independent model-assisted proxy' if proxy else 'reviewed external annotations'}; "
        f"{len(annotations['images'])} images and {len(annotations['pairs'])} pair records."]
    if recoveries:
        lines += ['', 'The user separately authorized one SAM3 setup recovery after gated access was granted. '
            'The original E3 failure remains failed; both processes and the resumed asset acquisition '
            'remain charged against the unchanged cumulative setup limit.']
    if reconstruction_recoveries:
        lines += ['', 'The user authorized one additional S3 reconstruction attempt of at most 5,400 seconds '
            'after native-helper isolation repair. Original failure and elapsed charges remain intact; '
            'the cumulative GPU ceiling is unchanged.']
    if proxy:
        lines += ['', 'The user authorized automated labeling because human contributors were unavailable. '
            'Pixel and boundary scores measure agreement with the frozen CPU Mask R-CNN teacher, including uncertain '
            'teacher nondetections. Improvements/regressions below refer only to named proxy-agreement or retention '
            'metrics. Human boundary accuracy, uncertain roles, independent changing/static truth and temporal identity '
            'remain unverified; unknown layers are excluded.']
    lines += ['', '## Frozen combinations']
    _table(lines, ['Family', 'Choice', 'Status', 'Reason'], [[family, row.get('selected') or 'none', row['status'], row.get('reason') or 'prespecified ranking; exact tie terms linked']
          for family, row in frozen['finalists'].items()])
    combined_rows = []
    for slot, title in [('C0', 'reference'), ('C1', 'primary'), ('C2', 'commercial-use/non-AGPL preference'), ('C3', 'fallback')]:
        selected = frozen.get('combined', {}).get(slot, {})
        outcome = aggregate.get('combined', {}).get(slot, {})
        reasons = list(dict.fromkeys(selected.get('reasons', []) + outcome.get('reasons', [])))
        combined_rows.append([slot+' '+title, ' + '.join(str(c) for c in selected.get('components', [])) or 'unverified',
            selected.get('status', 'unverified'), outcome.get('status', 'unverified'),
            '; '.join(reasons) or outcome.get('reason') or _link(outcome.get('result'), 'result')])
    _table(lines, ['Slot', 'Frozen components', 'Eligibility', 'Outcome', 'Reason / evidence'], combined_rows)
    lines += ['Unverified baseline defaults are not measured winners. No D3/D4 substitution or result-driven reranking is made. '+
              _link(aggregate['finalists'], 'Frozen rankings, tie terms and gates')+'.']
    _mask_report(lines, masks, paired, aggregate, reader)
    lines += ['', '## Paired conclusions', '',
        'A 95% interval containing zero is inconclusive, including an endpoint at zero. '
        'Intervals use the saved PCG64 seed-0, 10,000 camera/temporal-group resamples and linear percentiles. '
        'Overlapping crossing pairs retain their shared 20–26 temporal group. Combined changes describe interactions; '
        'geometry acceptance/support/coverage changes do not verify physical correctness.']
    counts = Counter(r['conclusion'] for r in paired)
    lines += ['', '; '.join(f'{name}: {counts[name]}' for name in ('improvement', 'regression', 'increase', 'decrease', 'inconclusive', 'unverified'))+
        '. These are correlated named fields across domains/strata, not independent wins or a stack score.']
    detail_lines = ['# Every saved paired field', '', 'Candidate minus baseline. All intervals and camera summaries are copied from frozen aggregation; no resampling or refitting occurs.', '',
                    'For proxy annotations, named improvements/regressions describe proxy agreement only. Missing/undefined evidence remains unverified.']
    _table(detail_lines, ['Scope/domain/stratum', 'Candidate − baseline', 'Metric', 'Δ [95% CI]', 'Conclusion', 'Source'],
        [[r['scope']+'/'+r['domain']+'/'+r['stratum'], r['candidate']+' − '+r['baseline'], r['kind']+'/'+r['metric']+'.'+r['field'],
          _estimate(r['estimate'], r['interval_95']), r['conclusion'], _link(r['source'], r['source_group'])] for r in paired])
    (output/'paired-comparisons.md').write_text('\n'.join(detail_lines)+'\n')
    write_json(output/'report-comparisons.json', dict(schema='vipe-benchmark-report-comparisons/v1', rows=paired,
        unavailable_mask_groups={key: value for key, value in masks.get('comparisons', {}).items()
                                 if value.get('status') != 'complete' or not value.get('scores')},
        evidence_kind=annotations.get('evidence_kind', 'reviewed-human'), human_ground_truth=not proxy,
        no_rescoring=True, no_resampling=True, no_model_selection=True))
    lines += ['', _link(file_record(output/'paired-comparisons.md'), 'Every paired metric, stratum, gain and regression')+'; '+
        _link(file_record(output/'report-comparisons.json'), 'machine-readable paired fields, worst-camera ranges and undefined cameras')+'.']
    lines += ['', '## Depth scale consistency']
    scale_rows = []
    for component in (f'D{i}' for i in range(5)):
        gate = frozen.get('depth_gates', {}).get(component, {})
        for stage in ('fit', 'check'):
            record = gate.get(stage+'_record')
            scale = reader.optional(record)
            cameras = scale.get('cameras', [])
            scale_rows.append([component, stage, gate.get(stage, 'unverified'),
                _estimate(scale.get('scale'), scale.get('bootstrap_95_interval')) if stage == 'fit' else _number(scale.get('scale')),
                _estimate(scale.get('diagnostic_window_scale'), scale.get('bootstrap_95_interval')),
                f'{len(cameras)}/{len(training_cameras(config))}', _range_text([r.get('points') for r in cameras]),
                '; '.join(scale.get('blockers', []) + gate.get('reasons', [])) or _link(record, 'scale evidence')])
    _table(lines, ['Depth', 'Phase', 'Gate', 'Applied scale', 'Diagnostic scale [95% CI]', 'Cameras', 'Points/camera range', 'Reason / evidence'], scale_rows)
    lines += ['Frame 100 fits one global multiplicative scale; frame 175 checks the unchanged fit. '
              'Passing consistency gates is not an independent measurement of physical accuracy.']
    geometry_details = _geometry_report(lines, aggregate, reader, states)
    write_json(output/'report-geometry-details.json', dict(schema='vipe-benchmark-report-geometry-details/v1', slots=geometry_details,
        physical_accuracy='unverified', interpretation='descriptive summaries of saved directed-edge evidence; no new geometry evaluation'))
    lines += ['', _link(file_record(output/'report-geometry-details.json'), 'Support, overlap/Jaccard, marginal coverage, parallax ranges, shortages and rejection totals')+'.']
    _controls_report(lines, masks, aggregate, reader, len(training_cameras(config)))
    lines += ['', '## Engineering and license evidence']
    component_rows, dependency_removal = [], {}
    for component in [f'S{i}' for i in range(5)] + [f'D{i}' for i in range(5)] + [f'M{i}' for i in range(3)] + [f'N{i}' for i in range(3)]:
        row = documents['components'].get(component, {})
        records = row.get('qualification_results', [])
        results = [reader.read(record) for record in records]
        standalone = component.startswith(('S', 'D')) and component not in ('S0', 'D0')
        def guarded(result):
            isolation = result.get('runtime', {}).get('isolation', {})
            if isolation.get('import_guard') is not True:
                return False
            if isolation.get('subprocesses') is False:
                return True
            helpers = isolation.get('native_helpers') or {}
            if isolation.get('subprocesses') != 'confined-native-helpers' or not helpers.get('completed'):
                return False
            completed = reader.read(helpers['completed'])
            policy = reader.read(completed['policy'])
            if completed.get('status') != 'complete' or not policy.get('inherited_process_group'):
                return False
            for command in completed['commands']:
                reader.read(command['request'])
                reader.read(command['started'])
                if reader.read(command['result'])['returncode'] != 0:
                    return False
            return True
        isolated = standalone and row.get('status') == 'qualified' and bool(results) and all(
            r.get('status') == 'complete' and r.get('runtime', {}).get('isolation', {}).get('import_guard') is True and
            guarded(r) for r in results)
        conclusion = 'qualified on completed guarded outputs' if isolated else 'reference wrapper' if component in ('S0', 'D0') else 'unverified'
        dependency_removal[component] = dict(status='qualified' if isolated else 'unverified', reason=conclusion, evidence=records)
        license_evidence = row.get('license_evidence', {})
        license_record = license_evidence.get('assessment')
        if license_record:
            reader.read(license_record)
        component_rows.append([component, row.get('status', 'unverified'), conclusion,
            row.get('commercial_permission', 'unverified'), row.get('non_agpl', 'unverified'),
            _link(license_record, 'assessment') if license_record else '; '.join(license_evidence.get('reasons', [])) or 'closure evidence unavailable'])
    _table(lines, ['Component', 'Engineering qualification', 'ViPE dependency removal', 'Commercial permission', 'Non-AGPL preference', 'License evidence'], component_rows)
    lines += ['The two license preferences are separate assessments of exact code, weights and resolved dependencies. '
        'Unverified evidence does not exclude a research comparison, but blocks C2. '+_link(request['components'], 'Full component inventories and reviewed license evidence')+
        '. Completed guarded outputs support dependency removal only within the recorded Python-audit limitation; '
        'engineering qualification alone establishes no measured quality gain.', '',
        'Physical accuracy: **unverified**. These result contracts contain no completed independent physical-accuracy '
        'evaluation. Scale repeatability, accepted triangulations and proxy agreement cannot replace that evidence.', '',
        '## Execution and limits']
    _table(lines, ['Slot', 'Outcome', 'Seconds', 'Evidence / reason'], [[job,
        states.get(job, {}).get('status', 'unverified'), _number(states.get(job, {}).get('elapsed_seconds')),
        _link(states[job].get('result'), 'result') if job in states and states[job].get('result') else
        states.get(job, {}).get('reason') or states.get(job, {}).get('error') or 'no completed slot evidence'] for job in sorted(expected)])
    _table(lines, ['Allocation', 'Attempts', 'Charged seconds', 'Reserved seconds'], [[name, row.get('attempts', 'unverified'),
        _number(row.get('elapsed_seconds')), _number(row.get('reserved_seconds'))]
        for name, row in documents['accounting'].get('consumption', {}).items()])
    lines += ['Accounting is the saved pre-report checkpoint; report wall time is added by the supervisor afterward. '
        'Unavailable arms and saved time authorize no replacement attempts. An interrupted or blocked matrix is not '
        'a successful full benchmark. '+_link(request['accounting'], 'Append-only execution accounting')+'; '+
        _link(request['aggregate'], 'frozen final aggregate')+'; '+_link(request['annotations'], 'annotation review')+'; '+
        _link(request['validation'], 'implementation validation')+'.']
    report = output/'report.md'
    report.write_text('\n'.join(lines)+'\n')
    result = dict(status='complete', report=file_record(report), evidence={k: request[k] for k in documents},
        paired_comparisons=file_record(output/'report-comparisons.json'), paired_comparisons_readable=file_record(output/'paired-comparisons.md'),
        geometry_details=file_record(output/'report-geometry-details.json'), unavailable_or_failed_slots=unresolved,
        comparison_fully_executed=not unresolved, evidence_kind=annotations.get('evidence_kind', 'reviewed-human'),
        human_ground_truth=not proxy, physical_accuracy='unverified', dependency_removal=dependency_removal,
        overall_plan_success='requires final criteria assessment; report completion alone is insufficient')
    write_json(output/'result.json', result)
    return result
