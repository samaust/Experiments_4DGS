"""Final-render review package for #34: matched held-out clips, a local viewer and review import.

The package shows the held-out reference camera beside each arm's accepted render
result, as synchronized 25 fps clips built from the exact published PNGs. An arm
without a complete render result is listed as unavailable with its reason. The
viewer exports a review JSON; `import_review` binds it to the exact package.

Usage:
  final_render_review.py build --request R --output DIR ARM=RESULT_JSON|ARM=failed:REASON ...
  final_render_review.py import --package P --review R --output OUT
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vipe_benchmark.files import file_record, read_json, verify_record, write_json  # noqa: E402

SCHEMA = 'plan069-final-render-review-package/v1'
REVIEW = 'plan069-final-render-review/v1'
IMPORTED = 'plan069-final-render-review-import/v1'
COMPARISONS = dict(motion=('QF-B', 'QF-M1', 'QF-M2'), neighbors=('QF-B', 'QF-N1', 'QF-N2'))
OUTCOMES = ('tie', 'unclear')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'}, 'exact file record required')
    verify_record(record)  # Raises 'changed file' on any byte change.
    return record


def _encode(sources, output, fps, resolution):
    """Encode exactly len(sources) frames, in order, as a browser-playable H.264 clip."""
    width, height = resolution
    command = ['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}',
               '-framerate', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'slow',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-threads', '2', str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for record in sources:
            with Image.open(_bound(record)['path']) as image:
                _require(image.mode == 'RGB' and list(image.size) == resolution, 'matched RGB frame size required')
                process.stdin.write(np.asarray(image).tobytes())
    finally:
        process.stdin.close()
    _require(process.wait() == 0, 'clip encoding failed: '+str(output))
    return file_record(output)


def _reference(request, cameras, frames):
    manifest_record = _bound(request['bindings']['scene_manifest'])
    manifest = read_json(manifest_record['path'])
    root = Path(manifest_record['path']).parent
    sources = {}
    for camera in manifest['cameras']:
        if int(camera['id']) in cameras:
            rows = {row['frame_id']: row for row in camera['frames']}
            records = []
            for frame in frames:
                record = file_record(root/rows[frame]['path'])
                _require(record['sha256'] == rows[frame]['sha256'], 'reference frame changed: '+rows[frame]['path'])
                records.append(record)
            sources[int(camera['id'])] = records
    _require(set(sources) == set(cameras), 'reference coverage for every held-out camera required')
    return sources


def _rendered(result_record, cameras, frames, render):
    result = read_json(_bound(result_record)['path'])
    _require(result.get('status') == 'complete' and result.get('phase') == 'render' and
        result.get('render_settings') == render, 'complete matched render result required')
    rows = {(row['camera'], row['frame']): row['rgb'] for row in result['rendered_frames']}
    _require(set(rows) == {(c, f) for c in cameras for f in frames} and len(rows) == len(result['rendered_frames']),
        'render coverage of every held-out camera/frame required')
    return {camera: [_bound(rows[camera, frame]) for frame in frames] for camera in cameras}


# Plain-language meaning of each method code (benchmark-protocol.md, table of
# M and N methods), shown in every caption so reviewers need no lookup.
MOTION = {'M0': 'frame-difference mask (frame t vs t+1)',
          'M1': '9-frame median-background mask',
          'M2': 'MOG2 background-subtraction mask'}
NEIGHBORS = {'N0': 'most shared feature tracks',
             'N1': 'highest Jaccard co-visibility',
             'N2': 'greedy coverage/parallax selection'}


def arm_label(arm, composition):
    """Caption: arm id, then its motion-mask and neighbor-camera methods in words."""
    motion, neighbors = composition['motion'], composition['neighbors']
    role = ' (baseline)' if (motion, neighbors) == ('M0', 'N0') else ''
    return (f"{arm}{role} \u2014 motion {motion}: {MOTION.get(motion, motion)}; "
            f"neighbors {neighbors}: {NEIGHBORS.get(neighbors, neighbors)}")


def build_package(request_record, results, output):
    """Publish package.json, clips and index.html; return the package file record."""
    request = read_json(_bound(request_record)['path'])
    render = request['render']
    cameras, frames, fps, resolution = render['cameras'], render['frames'], render['fps'], render['resolution']
    plans = [dict(id='reference', label='Real video from the held-out camera (ground truth)', composition=None, output_type='reference',
                  result=None, sources=_reference(request, cameras, frames))]
    for arm, composition in request['compositions'].items():
        outcome = results.get(arm, dict(status='failed', reason='no render result supplied'))
        plan = dict(id=arm, label=arm_label(arm, composition), composition=composition,
                    output_type='final-render')
        if set(outcome) == {'path', 'sha256', 'bytes'}:
            plan.update(result=outcome, sources=_rendered(outcome, cameras, frames, render))
        else:
            _require(outcome.get('status') == 'failed' and bool(outcome.get('reason', '').strip()),
                'unavailable arm needs an explicit reason')
            plan.update(result=None, sources=None, reason=outcome['reason'])
        plans.append(plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'clips').mkdir()
    candidates = []
    for plan in plans:
        candidate = dict(id=plan['id'], label=plan['label'], composition=plan['composition'],
                         output_type=plan['output_type'], result=plan['result'], clips={})
        if plan['sources'] is None:
            candidate.update(status='unavailable', reason=plan['reason'])
        else:
            candidate['status'] = 'available'
            for camera in cameras:
                clip = _encode(plan['sources'][camera], output/'clips'/f"{plan['id']}-camera{camera}.mp4", fps, resolution)
                candidate['clips'][str(camera)] = dict(frame_ids=list(frames), record=clip,
                                                       sources=plan['sources'][camera])
        candidates.append(candidate)
    available = {c['id'] for c in candidates if c['status'] == 'available'}
    package = dict(schema=SCHEMA, record_kind='actual', request=request_record,
        settings=dict(cameras=cameras, frames=frames, fps=fps, resolution=resolution,
                      encoding='H.264 CRF 12 yuv420p from the exact published lossless PNGs'),
        candidates=candidates,
        comparisons={name: [arm for arm in arms if arm in request['compositions']] for name, arms in COMPARISONS.items()},
        available=sorted(available),
        notes=['Final renders are research outputs (research-use licence decision, 2026-10-05).',
               'Held-out cameras 0/10/20/30 were never used for training.'])
    write_json(output/'package.json', package)
    record = file_record(output/'package.json')
    (output/'index.html').write_text(_viewer(package, record))
    return record


def validate_package(record):
    package = read_json(_bound(record)['path'])
    _require(package.get('schema') == SCHEMA, 'final-render review package schema required')
    _bound(package['request'])
    for candidate in package['candidates']:
        if candidate['status'] != 'available':
            _require(not candidate['clips'] and bool(candidate.get('reason', '').strip()), 'unavailable arm needs reason')
            continue
        if candidate['result'] is not None:
            _bound(candidate['result'])
        _require(sorted(candidate['clips']) == sorted(str(c) for c in package['settings']['cameras']),
            'clip for every held-out camera required')
        for clip in candidate['clips'].values():
            _bound(clip['record'])
            for source in clip['sources']:
                _bound(source)
    return package


def import_review(package_record, review_record, output):
    """Bind an exported human review to the exact package; return the import record."""
    package = validate_package(package_record)
    review = read_json(_bound(review_record)['path'])
    _require(review.get('schema') == REVIEW, 'final-render review schema required')
    _require(review.get('record_kind') == 'human', 'actual human review required')
    _require(type(review.get('reviewer')) is str and bool(review['reviewer'].strip()), 'named reviewer required')
    _require(review.get('package') == package_record, 'review must bind this exact package')
    available = set(package['available'])
    cameras, frames = set(package['settings']['cameras']), set(package['settings']['frames'])
    comparisons = review.get('comparisons')
    _require(type(comparisons) is dict and set(comparisons) == set(package['comparisons']), 'every comparison required')
    for name, comparison in comparisons.items():
        expected = [arm for arm in package['comparisons'][name] if arm in available]
        _require(sorted(comparison.get('candidates', [])) == sorted(expected), 'comparison candidates differ: '+name)
        _require(comparison.get('preference') in (*expected, *OUTCOMES), 'unknown preference: '+name)
        for row in comparison.get('observations', []):
            _require(row.get('candidate') in available | {'reference'}, 'observation candidate unknown')
            _require(row.get('camera') in cameras, 'observation camera must be a held-out camera')
            _require(row.get('frame') in frames, 'observation frame outside the rendered frames')
            _require(type(row.get('text')) is str and bool(row['text'].strip()), 'observation text required')
    overall = review.get('overall', {})
    _require(overall.get('preference') in (*sorted(available - {'reference'}), *OUTCOMES), 'unknown overall preference')
    write_json(output, dict(schema=IMPORTED, status='imported', record_kind='human', package=package_record,
                            review_record=review_record, review=review))
    return file_record(output)


def _intro(package):
    """Explain what every clip shows, from the bound request's real settings."""
    request = read_json(package['request']['path'])
    from vipe_benchmark.extended_final_render_contract import policies
    effective = policies(request)
    training = ('all 50 frames of the 30 training cameras' if effective['training_policy'] == 'all-times'
                else 'the training cameras, without frames 20\u201324')
    depth = request.get('depth_candidate', 'D*')
    rows = ''.join(f'<tr><td>{code}</td><td>{text}</td></tr>' for code, text in [*MOTION.items(), *NEIGHBORS.items()])
    return (f"<p>Every video shows the <b>same held-out camera</b> (chosen with the Camera menu; cameras 0/10/20/30 "
            f"were never used for training) over the same 50 frames at 25 fps. The first video is the <b>real "
            f"footage</b>; each other video is one <b>arm</b>: a FreeTimeGS model trained for {request['iterations']:,} "
            f"steps on {training}, then rendered from that camera. All arms share S2 segmentation and {depth} depth. "
            f"They differ in one method each: the <b>motion mask</b> (M) that marks moving pixels for the initializer, "
            f"or the <b>neighbor cameras</b> (N) each camera is matched against for geometry. QF-B (M0/N0) is the "
            f"baseline; QF-M1/M2 change only M, QF-N1/N2 change only N. Research outputs only.</p>"
            f"<table class=legend>{rows}</table>")


def _viewer(package, record):
    payload = json.dumps(dict(package=package, record=record)).replace('<', '\\u003c')
    intro = _intro(package)
    return ("""<!doctype html><html><head><meta charset="utf-8"><title>Final render review</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui,sans-serif;margin:16px;background:#111;color:#eee}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0;position:sticky;top:0;background:#111;padding:6px 0;z-index:2}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:10px}
figure{margin:0;background:#000;overflow:hidden;position:relative}
figcaption{font-size:14px;padding:6px 8px;background:#222;font-weight:600;position:relative;z-index:1}
.viewport{overflow:hidden;position:relative}
.legend td{padding:2px 10px 2px 0;vertical-align:top}
video{width:100%;display:block;transform-origin:var(--ox,50%) var(--oy,50%);cursor:grab}
.grid.pixelated video{image-rendering:pixelated}
.grid.dragging video{cursor:grabbing}
.unavailable{padding:24px;color:#f99}
textarea,input,select,button{font:inherit}
textarea{width:100%;min-height:60px}
fieldset{margin:12px 0;border:1px solid #444}
</style></head><body>
<h1>Final render review: motion and neighbor effects</h1>
@@INTRO@@
<div class="controls">
 <label>Camera <select id="camera"></select></label>
 <label>Compare <select id="set"><option value="motion">Motion: M0 / M1 / M2</option>
 <option value="neighbors">Neighbors: N0 / N1 / N2</option><option value="all">All arms</option></select></label>
 <button id="play">Play/Pause</button><button id="back">◀ frame</button><button id="next">frame ▶</button>
 <label>Frame <input id="frame" type="range" min="0" max="49" value="0"></label><span id="frameLabel">0</span>
 <label>Speed <select id="rate"><option>0.25</option><option>0.5</option><option selected>1</option></select></label>
 <label>Zoom <select id="zoom"><option>1</option><option>1.5</option><option>2</option><option>3</option><option>4</option>
 <option>6</option><option>8</option><option>12</option><option>16</option></select></label>
 <label><input type="checkbox" id="pixelated"> Sharp pixels</label>
 <button id="center">Recenter</button>
 <span class="hint">Drag, click or scroll on any video: all videos pan and zoom together.</span>
</div>
<div class="grid" id="grid"></div>
<h2>Review</h2><form id="form"></form>
<button id="export">Download review JSON</button>
<script>
const DATA = """ + payload + """;
const P = DATA.package, fps = P.settings.fps;
const byId = Object.fromEntries(P.candidates.map(c => [c.id, c]));
const cameraSel = document.getElementById('camera');
P.settings.cameras.forEach(c => cameraSel.add(new Option('Camera ' + c, c)));
let videos = [];
function members() {
  const set = document.getElementById('set').value;
  const arms = set === 'all' ? P.candidates.filter(c => c.id !== 'reference').map(c => c.id) : P.comparisons[set];
  return ['reference', ...arms];
}
function render() {
  const grid = document.getElementById('grid'); grid.replaceChildren(); videos = [];
  for (const id of members()) {
    const c = byId[id], fig = document.createElement('figure'), cap = document.createElement('figcaption');
    cap.textContent = c.label; fig.append(cap);
    if (c.status !== 'available') {
      const d = document.createElement('div'); d.className = 'unavailable';
      d.textContent = 'Unavailable: ' + c.reason; fig.append(d);
    } else {
      const v = document.createElement('video');
      v.src = 'clips/' + c.clips[cameraSel.value].record.path.split('/').pop();
      v.muted = true; v.preload = 'auto'; v.playsInline = true; v.loop = true;
      linkView(v);
      // The zoomed video is clipped to its own viewport so it never covers the caption.
      const port = document.createElement('div'); port.className = 'viewport';
      port.append(v); fig.append(port); videos.push(v);
    }
    grid.append(fig);
  }
  applyZoom(); seek(+document.getElementById('frame').value);
}
function seek(f) {
  f = Math.max(0, Math.min(P.settings.frames.length - 1, f));
  document.getElementById('frame').value = f; document.getElementById('frameLabel').textContent = f;
  videos.forEach(v => { v.pause(); v.currentTime = (f + 0.5) / fps; });
}
// One shared view for every video: zoom factor and transform origin (percent).
// With scale(z) about the origin, origin 0% shows the left/top edge and 100% the
// right/bottom edge, so the same origin shows the same scene area in every clip.
const view = {ox: 50, oy: 50};
function setView(ox, oy) {
  view.ox = Math.max(0, Math.min(100, ox)); view.oy = Math.max(0, Math.min(100, oy));
  const grid = document.getElementById('grid');
  grid.style.setProperty('--ox', view.ox + '%'); grid.style.setProperty('--oy', view.oy + '%');
}
// Scene point (0..1) under screen fraction f for origin o and zoom z: o + (f - o) / z.
// Origin that puts scene point p at screen fraction f under zoom z: (p - f / z) / (1 - 1 / z).
function originFor(p, f, z) { return z > 1 ? (p - f / z) / (1 - 1 / z) * 100 : 50; }
function sceneAt(f, o, z) { return o / 100 + (f - o / 100) / z; }
// Pointer position as a fraction of the visible (unscaled, clipped) video area.
function frac(v, e) { const r = v.parentElement.getBoundingClientRect();
  return [(e.clientX - r.left - v.offsetLeft) / v.offsetWidth, (e.clientY - r.top - v.offsetTop) / v.offsetHeight]; }
function zoomSteps() { return [...document.getElementById('zoom').options].map(o => +o.value); }
function linkView(v) {
  let drag = null;
  v.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, ox: view.ox, oy: view.oy, moved: false};
    v.setPointerCapture(e.pointerId); document.getElementById('grid').classList.add('dragging'); });
  v.addEventListener('pointermove', e => { if (!drag) return;
    const z = +document.getElementById('zoom').value, w = v.offsetWidth, h = v.offsetHeight;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
    if (z > 1) setView(drag.ox - dx / (w * (z - 1)) * 100, drag.oy - dy / (h * (z - 1)) * 100); });
  v.addEventListener('pointerup', e => { const d = drag; drag = null;
    document.getElementById('grid').classList.remove('dragging');
    if (d && !d.moved) { const z = +document.getElementById('zoom').value;
      // Click: center the shared view on the clicked scene point.
      const [fx, fy] = frac(v, e);
      setView(originFor(sceneAt(fx, view.ox, z), .5, z), originFor(sceneAt(fy, view.oy, z), .5, z)); } });
  v.addEventListener('wheel', e => { e.preventDefault();
    const steps = zoomSteps(), sel = document.getElementById('zoom');
    const i = steps.indexOf(+sel.value), j = Math.max(0, Math.min(steps.length - 1, i + (e.deltaY < 0 ? 1 : -1)));
    if (j !== i) { const z = steps[i], next = steps[j];
      const [fx, fy] = frac(v, e);
      // Keep the scene point under the cursor fixed while zooming.
      setView(originFor(sceneAt(fx, view.ox, z), fx, next), originFor(sceneAt(fy, view.oy, z), fy, next));
      sel.value = String(next); applyZoom(); } }, {passive: false});
}
function applyZoom() { const z = document.getElementById('zoom').value;
  videos.forEach(v => v.style.transform = 'scale(' + z + ')'); }
document.getElementById('play').onclick = () => {
  const lead = videos[0]; if (!lead) return;
  if (lead.paused) { const t = lead.currentTime; videos.forEach(v => { v.currentTime = t;
    v.playbackRate = +document.getElementById('rate').value; v.play(); }); }
  else videos.forEach(v => v.pause()); };
setInterval(() => { const lead = videos[0]; if (!lead || lead.paused) return;
  videos.slice(1).forEach(v => { if (Math.abs(v.currentTime - lead.currentTime) > 0.05) v.currentTime = lead.currentTime; });
  const f = Math.floor(lead.currentTime * fps); document.getElementById('frame').value = f;
  document.getElementById('frameLabel').textContent = f; }, 100);
document.getElementById('back').onclick = () => seek(+document.getElementById('frame').value - 1);
document.getElementById('next').onclick = () => seek(+document.getElementById('frame').value + 1);
document.getElementById('frame').oninput = e => seek(+e.target.value);
document.getElementById('zoom').onchange = applyZoom;
document.getElementById('center').onclick = () => setView(50, 50);
document.getElementById('pixelated').onchange = e => document.getElementById('grid').classList.toggle('pixelated', e.target.checked);
cameraSel.onchange = render; document.getElementById('set').onchange = render;
const form = document.getElementById('form');
function field(parent, label, el) { const l = document.createElement('label'); l.textContent = label + ' ';
  l.append(el); parent.append(l, document.createElement('br')); return el; }
const inputs = {};
form.append(Object.assign(document.createElement('p'), {textContent:
  'Observations: one per line as "candidate camera frame: text", e.g. "QF-M1 10 23: less ghosting on the moving player".'}));
inputs.reviewer = field(form, 'Reviewer', Object.assign(document.createElement('input'), {value: 'samaust'}));
for (const [name, arms] of Object.entries(P.comparisons)) {
  const fs = document.createElement('fieldset'); fs.append(Object.assign(document.createElement('legend'),
    {textContent: name === 'motion' ? 'Motion methods (M0/M1/M2)' : 'Neighbor methods (N0/N1/N2)'}));
  const available = arms.filter(a => byId[a] && byId[a].status === 'available');
  const sel = document.createElement('select');
  [...available, 'tie', 'unclear'].forEach(o => sel.add(new Option(o === 'tie' || o === 'unclear' ? o : byId[o].label, o)));
  inputs[name] = {candidates: available, preference: field(fs, 'Preference', sel),
    observations: field(fs, 'Observations', document.createElement('textarea')),
    tradeoffs: field(fs, 'Tradeoffs', document.createElement('textarea'))};
  form.append(fs);
}
const overall = document.createElement('select');
[...P.candidates.filter(c => c.id !== 'reference' && c.status === 'available').map(c => c.id), 'tie', 'unclear']
  .forEach(o => overall.add(new Option(o, o)));
inputs.overall = field(form, 'Overall preference', overall);
inputs.overallTradeoffs = field(form, 'Overall tradeoffs', document.createElement('textarea'));
function parse(text) { return text.split('\\n').map(s => s.trim()).filter(Boolean).map(line => {
  const m = line.match(/^(\\S+)\\s+(\\d+)\\s+(\\d+)\\s*:\\s*(.+)$/);
  if (!m) throw new Error('Cannot parse observation: ' + line);
  return {candidate: m[1], camera: +m[2], frame: +m[3], text: m[4]}; }); }
document.getElementById('export').onclick = () => {
  try {
    const comparisons = {};
    for (const name of Object.keys(P.comparisons)) { const i = inputs[name];
      comparisons[name] = {candidates: i.candidates, preference: i.preference.value,
        observations: parse(i.observations.value), tradeoffs: i.tradeoffs.value}; }
    const review = {schema: 'plan069-final-render-review/v1', record_kind: 'human', reviewer: inputs.reviewer.value,
      reviewed_at: new Date().toISOString(), package: DATA.record, comparisons,
      overall: {preference: inputs.overall.value, tradeoffs: inputs.overallTradeoffs.value}};
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(review, null, 2)], {type: 'application/json'}));
    a.download = 'final-render-review.json'; a.click();
  } catch (e) { alert(e.message); }
};
render();
</script></body></html>
""").replace('@@INTRO@@', intro, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--request', required=True)
    build.add_argument('--output', required=True)
    build.add_argument('results', nargs='+')
    imported = commands.add_parser('import')
    imported.add_argument('--package', required=True)
    imported.add_argument('--review', required=True)
    imported.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'build':
        results = {}
        for item in args.results:
            arm, value = item.split('=', 1)
            results[arm] = (dict(status='failed', reason=value[len('failed:'):]) if value.startswith('failed:')
                            else file_record(value))
        print(build_package(file_record(args.request), results, args.output))
    else:
        print(import_review(file_record(args.package), file_record(args.review), Path(args.output)))


if __name__ == '__main__':
    main()
