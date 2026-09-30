"""Immutable qualitative presentation packages; no inferred human judgments."""
import json
import math
import subprocess
import time

from .files import file_record, safe_path, write_json

SCHEMA = 'plan067-qualitative-package/v1'


def _record(record):
    actual = file_record(record['path'], record['sha256'])
    if actual != record:
        raise ValueError('record hash/size/path mismatch')
    return safe_path(actual['path'])


def _crop(crop, resolution):
    if len(crop) != 4 or any(type(x) is not int for x in crop):
        raise ValueError('invalid crop')
    x, y, w, h = crop
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > resolution[0] or y+h > resolution[1]:
        raise ValueError('crop outside full frame')


def _remaining(deadline):
    if deadline is None:
        return 30
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('qualitative package publication deadline')
    return min(30, remaining)


def _media(media, selection, resolution, deadline):
    _remaining(deadline)
    if media['frame_ids'] != selection['frame_ids'] or media['timestamps'] != selection['timestamps']:
        raise ValueError('media frame/time identity mismatch')
    if media['resolution'] != resolution:
        raise ValueError('media resolution mismatch')
    path = _record(media['record'])
    kind = media['kind']
    if kind in ('frame', 'diagnostic'):
        if len(selection['frame_ids']) != 1:
            raise ValueError('frame must have one timestamp')
        from PIL import Image
        with Image.open(path) as image:
            if image.format != 'PNG' or list(image.size) != resolution:
                raise ValueError('PNG resolution/format mismatch')
            image.load()
    elif kind in ('clip', 'sequence'):
        completed = subprocess.run(['ffprobe', '-v', 'error', '-threads', '1', '-select_streams', 'v:0',
            '-count_frames', '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames',
            '-of', 'json', str(path)], capture_output=True, text=True, timeout=_remaining(deadline), check=True)
        streams = json.loads(completed.stdout)['streams']
        if len(streams) != 1:
            raise ValueError('missing video stream')
        stream = streams[0]
        numerator, denominator = map(int, stream['avg_frame_rate'].split('/'))
        if [stream['width'], stream['height']] != resolution or int(stream['nb_read_frames']) != len(selection['frame_ids']):
            raise ValueError('video frame count/resolution mismatch')
        if denominator == 0 or numerator / denominator != 25:
            raise ValueError('video must preserve 25 fps')
        contiguous = all(b == a+1 for a,b in zip(selection['frame_ids'], selection['frame_ids'][1:]))
        if kind == 'clip' and not contiguous:
            raise ValueError('sparse predictions must be labeled sequence')
        # Full decode rejects truncated/corrupt packets even when headers still parse.
        subprocess.run(['ffmpeg','-v','error','-xerror','-threads','1','-i',str(path),'-threads','1','-f','null','-'],
            capture_output=True, timeout=_remaining(deadline), check=True)
    else:
        raise ValueError('unknown media kind')
    _remaining(deadline)


def validate(manifest, *, deadline=None):
    """Verify frozen selection, matched membership, provenance and media bytes."""
    _remaining(deadline)
    if manifest['schema'] != SCHEMA or manifest['mode'] != 'qualitative':
        raise ValueError('wrong package mode/schema')
    if manifest['record_kind'] not in ('actual','fixture') or not manifest['id'].strip():
        raise ValueError('invalid package identity')
    for key in ('source','config','inputs','amendment'):
        _record(manifest['bindings'][key])
    if manifest['record_kind'] == 'actual':
        for key in ('request','generation_result','generation_manifest'):
            if key not in manifest['bindings']:
                raise ValueError('actual package requires trusted generation receipts')
            _record(manifest['bindings'][key])
        from .qualitative_generation import validate_actual_package
        validate_actual_package(manifest, deadline=deadline)
    settings = manifest['settings']
    resolution = settings['resolution']
    if len(resolution) != 2 or any(type(x) is not int or x <= 0 for x in resolution) or settings['fps'] != 25 or not settings['color_handling'].strip():
        raise ValueError('invalid shared presentation settings')
    _crop(settings['crop'], resolution)
    detail_ids = set()
    for region in settings['detail_regions']:
        if region['id'] in detail_ids:
            raise ValueError('duplicate detail region')
        detail_ids.add(region['id'])
        _crop(region['crop'], resolution)
    selections = {}
    ranges = {'reconstruction':(0,49),'calibration':(50,149),'selection':(150,199)}
    for row in manifest['selections']:
        if not row['id'] or row['id'] in selections or row['kind'] not in ('frame','clip') or not str(row['camera_id']).strip():
            raise ValueError('invalid selection identity')
        ids, times = row['frame_ids'], row['timestamps']
        low, high = ranges[row['role']]
        if not ids or len(ids) != len(times) or ids != sorted(set(ids)) or any(type(x) is not int or not low <= x <= high for x in ids):
            raise ValueError('selection outside accepted role/frame range')
        if any(type(t) not in (int,float) or not math.isfinite(t) or abs(t-f/25)>1e-9 for f,t in zip(ids,times)):
            raise ValueError('selection timestamp mismatch')
        if row['kind'] == 'frame' and len(ids) != 1:
            raise ValueError('frame selection must contain one frame')
        selections[row['id']] = row
    if not selections:
        raise ValueError('no frozen selections')
    candidates = set()
    comparable = []
    for candidate in manifest['candidates']:
        identity = candidate['id']
        if not identity or identity in candidates or not candidate['label'].strip() or type(candidate['is_control']) is not bool:
            raise ValueError('invalid candidate identity')
        candidates.add(identity)
        if not candidate['stage'].strip() or candidate['output_type'] not in ('reference','component','final-render'):
            raise ValueError('invalid stage/output type')
        status = candidate['status']
        if status not in ('available','failed','blocked','missing','unavailable'):
            raise ValueError('unknown candidate state')
        if status != 'available' and not candidate['reason'].strip():
            raise ValueError('unavailable candidate needs reason')
        if status == 'available':
            for key in ('source_result','ledger_outcome','configuration'):
                _record(candidate['provenance'][key])
        seen = set()
        available = set()
        for media in candidate['media']:
            key = (media['selection_id'],media['kind'])
            if key in seen or media['selection_id'] not in selections:
                raise ValueError('duplicate/undeclared media selection')
            seen.add(key)
            selection = selections[media['selection_id']]
            if media['kind'] == 'frame' and selection['kind'] != 'frame' or media['kind'] in ('clip','sequence') and selection['kind'] != 'clip':
                raise ValueError('media kind/selection mismatch')
            if status != 'available' and media['kind'] != 'diagnostic':
                raise ValueError('partial failed output must be diagnostic')
            _media(media,selection,resolution,deadline)
            if media['kind'] != 'diagnostic':
                available.add(key)
        if status == 'available' and not available:
            raise ValueError('available candidate has no generated outputs')
        comparable.append((candidate['is_control'],available))
    ready = any(control and frames & other for control,frames in comparable for other_control,other in comparable if not other_control)
    return dict(readiness='ready-for-human-review' if ready else 'readiness-inventory', candidate_ids=sorted(candidates), selection_ids=sorted(selections))

validate_package = validate


def _viewer(manifest, record):
    # JSON is protected against closing the script tag; labels use textContent.
    payload = json.dumps(dict(manifest=manifest,record=record)).replace('<','\\u003c')
    return '''<!doctype html><meta charset="utf-8"><title>Qualitative comparison</title>
<style>body{font:16px system-ui;margin:20px}.cards{display:flex;gap:20px;flex-wrap:wrap}.card{flex:1;min-width:300px}.viewport{overflow:auto;max-width:100%;max-height:70vh}img,video{max-width:none}textarea{width:100%;height:90px}section{border-top:1px solid #aaa;padding:16px 0}label{margin-right:20px}</style>
<h1>Qualitative comparison</h1><p id="status"></p><p>Component diagnostics are not final rendered appearance. Sparse sequences cannot establish continuous motion quality. This viewer writes only an exported review download.</p>
<label>Selection <select id="selection"></select></label><label>Shared zoom <input id="zoom" type="range" min="0.25" max="4" step="0.25" value="0.25"></label><label>Shared crop <select id="crop"></select></label><button id="play">Play synchronized clips</button><button id="pause">Pause</button><input id="seek" type="range" min="0" step="0.04" value="0"><div class="cards" id="cards"></div>
<h2>Human observations</h2><label>Name/handle <input id="name"></label><label>Date <input id="date" type="date"></label><p>Each criterion needs your observation and exact examples. Examples are JSON objects with candidate_id, selection_id and frame_id, or start_time/end_time. Empty records remain awaiting review.</p><div id="criteria"></div><label>Tradeoffs<textarea id="tradeoffs"></textarea></label><button id="export">Export review JSON</button><script>
const data=PAYLOAD, m=data.manifest, $=id=>document.getElementById(id);
$('status').textContent=`Package ${m.id} (${m.record_kind}); SHA256 ${data.record.sha256}`;
for(const s of m.selections){let o=new Option(s.id,s.id);$('selection').add(o)}
$('crop').add(new Option('Original full frame','full'));$('crop').add(new Option('Frozen presentation crop','default'));for(const r of m.settings.detail_regions)$('crop').add(new Option(r.id,r.id));
function videos(){return [...document.querySelectorAll('video')]}
function draw(){ $('cards').replaceChildren();const sid=$('selection').value,s=m.selections.find(x=>x.id===sid);$('seek').max=(s.frame_ids.length-1)/25;
 for(const c of m.candidates){const card=document.createElement('div');card.className='card';const h=document.createElement('h2');h.textContent=c.label+(c.is_control?' (control)':'');card.append(h);const p=document.createElement('p');p.textContent=c.output_type+' / '+c.stage+' / '+c.status+' '+c.reason;card.append(p);
 const items=c.media.filter(x=>x.selection_id===sid);if(!items.length){let p=document.createElement('p');p.textContent='Unavailable for this selection; unable to judge';card.append(p)}
 for(const a of items){let title=document.createElement('p');title.textContent=a.kind+' — frames '+a.frame_ids.join(',')+'; original times '+a.timestamps.join(',')+' — SHA256 '+a.record.sha256;card.append(title);let viewport=document.createElement('div');viewport.className='viewport';let el=document.createElement(a.kind==='clip'?'video':a.kind==='sequence'?'video':'img');el.src='file://'+a.record.path.split('/').map(encodeURIComponent).join('/');if(el.tagName==='VIDEO'){el.controls=true;el.preload='metadata';if(a.kind==='sequence'){el.dataset.sequence='true';title.textContent+=' (sparse slideshow; motion unjudgeable)'}}else{el.alt=c.label+' '+sid}viewport.append(el);card.append(viewport);let original=document.createElement('a');original.textContent='Original full frame / media';original.href=el.src;original.target='_blank';card.append(original)}$('cards').append(card)}apply()}
function apply(){let crop=$('crop').value==='full'?[0,0,...m.settings.resolution]:$('crop').value==='default'?m.settings.crop:m.settings.detail_regions.find(r=>r.id===$('crop').value).crop;const z=Number($('zoom').value);for(const v of document.querySelectorAll('.viewport')){v.style.width=crop[2]*z+'px';v.style.height=crop[3]*z+'px';const e=v.firstChild;e.style.width=m.settings.resolution[0]*z+'px';e.style.height=m.settings.resolution[1]*z+'px';v.scrollLeft=crop[0]*z;v.scrollTop=crop[1]*z}}
$('selection').onchange=draw;$('crop').onchange=apply;$('zoom').oninput=apply;
$('play').onclick=async()=>{const vs=videos().filter(v=>!v.dataset.sequence);vs.forEach(v=>{v.currentTime=Number($('seek').value);v.playbackRate=1});await Promise.all(vs.map(v=>v.play()));};$('pause').onclick=()=>videos().forEach(v=>v.pause());$('seek').oninput=()=>videos().forEach(v=>v.currentTime=Number($('seek').value));
setInterval(()=>{const vs=videos().filter(v=>!v.paused&&!v.dataset.sequence);if(vs.length){const t=vs[0].currentTime;$('seek').value=t;for(const v of vs.slice(1))if(Math.abs(v.currentTime-t)>0.04)v.currentTime=t}},40);
const keys=['frozen_frame','motion','artifacts','sharpness','overall'];for(const key of keys){const section=document.createElement('section'),h=document.createElement('h3');h.textContent=key;section.append(h);let obs=document.createElement('textarea');obs.id=key+'-observation';obs.placeholder='Your observations';section.append(obs);let pref=document.createElement('select');pref.id=key+'-preference';for(const outcome of ['unjudgeable','preferred','tie','unclear','not_applicable'])pref.add(new Option(outcome,outcome));section.append(pref);let ids=document.createElement('input');ids.id=key+'-ids';ids.placeholder='Preferred/tied candidate IDs, comma separated';section.append(ids);let ex=document.createElement('textarea');ex.id=key+'-examples';ex.value='[]';section.append(ex);let exampleCandidate=document.createElement('select');for(const c of m.candidates)exampleCandidate.add(new Option(c.label,c.id));section.append(exampleCandidate);let add=document.createElement('button');add.textContent='Add current frame/time';add.onclick=()=>{try{const examples=JSON.parse(ex.value),s=m.selections.find(x=>x.id===$('selection').value),item={candidate_id:exampleCandidate.value,selection_id:s.id};if(s.kind==='frame')item.frame_id=s.frame_ids[0];else{const t=Math.min(s.timestamps.at(-1),s.timestamps[0]+Number($('seek').value));item.start_time=Math.round(t*1000)/1000;item.end_time=item.start_time}examples.push(item);ex.value=JSON.stringify(examples,null,2)}catch(e){alert('Fix examples JSON first: '+e.message)}};section.append(add);$('criteria').append(section)}
$('export').onclick=()=>{try{const review={schema:'plan067-qualitative-review/v1',record_kind:'human',reviewer:{name:$('name').value,reviewed_at:$('date').value},package:data.record,candidate_ids:m.candidates.map(c=>c.id),criteria:{},tradeoffs:$('tradeoffs').value};for(const k of keys)review.criteria[k]={observation:$(k+'-observation').value,preference:{outcome:$(k+'-preference').value,candidate_ids:$(k+'-ids').value.split(',').map(x=>x.trim()).filter(Boolean)},examples:JSON.parse($(k+'-examples').value)};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(review,null,2)],{type:'application/json'}));a.download=m.id+'-review.json';a.click();URL.revokeObjectURL(a.href)}catch(e){alert('Invalid examples JSON: '+e.message)}};draw();
</script>'''.replace('PAYLOAD',payload)


def publish(manifest, output_directory, *, deadline=None):
    """Publish once into a new directory; assets remain hash-bound in place."""
    summary = validate(manifest, deadline=deadline)
    _remaining(deadline)
    output = safe_path(output_directory)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'package.json',manifest)
    record = file_record(output/'package.json')
    # Exclusive directory ownership and exclusive file creation prevent overwrite.
    with (output/'viewer.html').open('x') as stream:
        stream.write(_viewer(manifest,record))
    result = dict(schema='plan067-qualitative-package-result/v1', package=record,
        viewer=file_record(output/'viewer.html'), **summary)
    _remaining(deadline)
    write_json(output/'result.json',result)
    _remaining(deadline)
    return result
