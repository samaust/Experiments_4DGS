# Failed operation used in inline python3 -B commands. Evidence filename was
# torch-cu121-range-failure.json, then torch-cu121-range-retry-failure.json.
import urllib.request
import json
import time
from pathlib import Path

url = 'https://download-r2.pytorch.org/whl/cu121/torch-2.1.1%2Bcu121-cp311-cp311-linux_x86_64.whl'
start = time.monotonic()
out = Path('.local/video-metadata-001')
try:
    req = urllib.request.Request(url, headers={'Range': 'bytes=-65536'})
    with urllib.request.urlopen(req, timeout=20) as response:
        headers = dict(response.headers)
        status = response.status
        data = response.read(65537)
        assert status == 206 and len(data) <= 65536, 'range unsupported or over cap'
    (out / 'torch-cu121-tail.bin').write_bytes(data)
    (out / 'torch-cu121-range.json').write_text(json.dumps({
        'url': url, 'status': status, 'headers': headers, 'bytes': len(data),
        'elapsed': time.monotonic() - start}, indent=2) + '\n')
except Exception as error:
    (out / 'torch-cu121-range-failure.json').write_text(json.dumps({
        'url': url, 'error': str(error), 'elapsed': time.monotonic() - start}) + '\n')
    raise
