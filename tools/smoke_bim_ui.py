"""Real Windows EXE Gradio event smoke, not merely checking HTTP 200.

Calls the same named event as the user's TẠO BIM button and checks a
downloadable result. Stdlib-only: runs beside the frozen executable.
"""
import json
import io
import zipfile
import sys
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:7861'
EVENT = 'tao_bim'


def get_json(url, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url, data=body, headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode('utf-8')


def run_smoke():
    try:
        posted = json.loads(get_json(
            BASE + '/gradio_api/call/' + EVENT,
            {'data': ['office_smoke_271', 12, 8, 3.2, 3]},
        ))
    except urllib.error.HTTPError as exc:
        raise AssertionError('BIM UI event HTTP failure: ' + str(exc.code)) from exc
    event_id = posted.get('event_id')
    if not event_id:
        raise AssertionError('Gradio did not enqueue BIM generation event')
    result = get_json(BASE + '/gradio_api/call/' + EVENT + '/' + event_id)
    events = [
        json.loads(line.removeprefix('data: '))
        for line in result.splitlines()
        if line.startswith('data: ')
    ]
    if not events:
        raise AssertionError('No data returned from BIM button')
    output = events[-1]
    if not isinstance(output, list) or len(output) != 2:
        raise AssertionError('BIM callback failed or returned invalid outputs')
    download, report = output
    if not isinstance(report, dict) or report.get('levels') != 3:
        raise AssertionError('BIM button returned no valid 3-floor report: ' + str(report)[:300])
    if not isinstance(download, dict) or not (
        download.get('path') or download.get('name')
    ):
        raise AssertionError('BIM button returned no downloadable ZIP: ' + str(download)[:300])
    # Gradio file outputs expose a local server URL. Retrieve the ZIP and
    # examine its contents instead of accepting a filename as proof.
    download_url = download.get('url')
    if not isinstance(download_url, str) or not download_url.startswith('/'):
        raise AssertionError('No relative local file URL in Gradio ZIP output')
    with urllib.request.urlopen(BASE + download_url, timeout=60) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as package:
        expected = {
            'canonical_bim_handoff.json', 'schematic_walls.glb',
            'schematic_plan.dxf', 'plan.svg', 'front_elevation.svg',
            'KIEM_TRA_HINH_HOC.json', 'KIEM_TRA_MO_LAI.json',
        }
        missing = expected.difference(package.namelist())
        if missing:
            raise AssertionError('ZIP lacks BIM files: ' + ', '.join(sorted(missing)))
        model = json.loads(package.read('canonical_bim_handoff.json'))
        if len(model['levels']) != 3:
            raise AssertionError('ZIP BIM model does not have three levels')
        if package.read('schematic_walls.glb')[:4] != b'glTF':
            raise AssertionError('ZIP lacks actual GLB binary geometry')
    print('PASS: real frozen Gradio BIM button returned ZIP with canonical model, GLB and QA')


if __name__ == '__main__':
    run_smoke()
