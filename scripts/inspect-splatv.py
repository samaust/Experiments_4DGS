"""Capture splaTV controls and scenes using an isolated automated browser."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.local/tools/playwright')
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--scene', default='model.splatv')
p.add_argument('--angle', default='gl')
p.add_argument('--skip-sequence', action='store_true')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / '.local/splaTV'))
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
result = dict(scene=a.scene, viewport=[1352,1014], device_pixel_ratio=1, requests=[], errors=[])
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=[f'--use-angle={a.angle}', '--ignore-gpu-blocklist',
                                      '--enable-webgl', '--enable-unsafe-swiftshader'])
        result['browser'] = browser.version
        context = browser.new_context(viewport={'width':1352,'height':1014}, device_scale_factor=1)
        page = context.new_page()
        page.on('pageerror', lambda e: result['errors'].append(str(e)))
        page.on('request', lambda r: result['requests'].append(r.url))
        start = time.monotonic()
        page.goto(url+'?url='+url+a.scene, wait_until='networkidle', timeout=120000)
        page.wait_for_function("document.getElementById('spinner').style.display === 'none'", timeout=120000)
        result['load_seconds'] = time.monotonic()-start
        page.keyboard.press('0')
        page.wait_for_timeout(1500)
        result['webgl'] = page.evaluate("""() => {const gl=document.querySelector('canvas').getContext('webgl2');
          const ext=gl.getExtension('WEBGL_debug_renderer_info');return {renderer:gl.getParameter(ext.UNMASKED_RENDERER_WEBGL),
          vendor:gl.getParameter(ext.UNMASKED_VENDOR_WEBGL),version:gl.getParameter(gl.VERSION)}}""")
        result['camera'] = page.evaluate('({camera, viewMatrix, cameraCount:cameras.length})')
        def seek(t):
            page.locator('#scene-time').evaluate('(el,t)=>{el.value=t;el.dispatchEvent(new Event("input",{bubbles:true}))}', t)
            page.wait_for_timeout(700)
        for t,label in [(0,'start'),(.5,'middle'),(.98,'end'),(1,'endpoint')]:
            seek(t)
            page.screenshot(path=str(a.output / (label+'.png')))
        (a.output/'sequence').mkdir()
        for i in range(0 if a.skip_sequence else 20):
            seek(i/20)
            page.screenshot(path=str(a.output/'sequence'/f'{i:05d}.png'))
        seek(.5)
        before = page.evaluate('viewMatrix.slice()')
        page.mouse.move(670,450)
        page.mouse.down()
        page.mouse.move(770,450,steps=20)
        page.mouse.up()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(a.output/'orbit.png'))
        result['orbit'] = dict(time=page.locator('#scene-time-value').inner_text(),
                               matrix_changed=before != page.evaluate('viewMatrix.slice()'))
        page.keyboard.press('0')
        seek(0)
        page.locator('#scene-play').click()
        fps=[]
        for i in range(10):
            page.wait_for_timeout(250)
            fps.append(page.locator('#fps').inner_text())
        page.locator('#scene-play').click()
        result['playback'] = dict(final_time=page.locator('#scene-time-value').inner_text(),displayed_fps=fps)
        before = page.evaluate('viewMatrix.slice()')
        page.locator('#scene-duration').fill('6')
        page.locator('#scene-duration').press('ArrowUp')
        page.locator('#scene-duration').press('Tab')
        after = page.evaluate('viewMatrix.slice()')
        result['editing_matrix_max_abs_delta'] = max(abs(x-y) for x,y in zip(before,after))
        result['editing_keeps_camera'] = result['editing_matrix_max_abs_delta'] < 1e-9
        page.locator('#scene-restart').click()
        result['restart_time'] = page.locator('#scene-time-value').inner_text()
        # Disable cache and deny all external requests, retaining loopback.
        cdp = context.new_cdp_session(page)
        cdp.send('Network.enable')
        cdp.send('Network.setCacheDisabled', {'cacheDisabled':True})
        blocked=[]
        def local_only(route):
            if route.request.url.startswith(url): route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()
        context.route('**/*', local_only)
        page.reload(wait_until='networkidle')
        page.wait_for_function("document.getElementById('spinner').style.display === 'none'", timeout=120000)
        page.keyboard.press('0')
        seek(.5)
        page.screenshot(path=str(a.output/'offline-middle.png'))
        result['offline_reload'] = dict(passed=True, blocked_external=blocked)
        if a.scene != 'model.splatv':
            # Match the half-resolution native STG reference focal lengths.
            page.evaluate('camera.fx /= 2; camera.fy /= 2; window.dispatchEvent(new Event("resize"))')
            result['native_match_camera'] = page.evaluate('({camera, viewMatrix})')
            for t,label in [(0,'start'),(.5,'middle'),(.98,'end')]:
                seek(t)
                page.screenshot(path=str(a.output/('native-match-'+label+'.png')))
        browser.close()
finally:
    server.shutdown()
    (a.output/'browser.json').write_text(json.dumps(result,indent=2)+'\n')
