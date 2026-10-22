"""Exercise the real frozen Windows EXE Gradio BIM event and inspect its delivery.

Stdlib-only so it can run on the Windows runner beside the packaged executable.
"""
import hashlib
import io
import json
import zipfile
import urllib.error
import urllib.request
from urllib.parse import urlsplit

BASE = 'http://127.0.0.1:7861'
EVENT = 'tao_bim'
MAX_ARCHIVE_BYTES = 80 * 1024 * 1024


def get_json(url, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        url, data=body, headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read().decode('utf-8')


def checked_download_url(relative_url):
    if not isinstance(relative_url, str):
        raise AssertionError('Gradio returned no download URL')
    parsed = urlsplit(relative_url)
    if parsed.scheme or parsed.netloc:
        if (
            parsed.scheme != 'http'
            or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.port != 7861
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise AssertionError('Gradio download URL points outside local server')
        normalized = BASE + parsed.path + (
            ('?' + parsed.query) if parsed.query else ''
        )
    else:
        if not relative_url.startswith('/') or relative_url.startswith('//'):
            raise AssertionError('Gradio download URL is not a local path')
        normalized = BASE + relative_url
    if (
        not parsed.path
        or '..' in parsed.path.split('/')
        or any(ord(char) < 32 for char in relative_url)
        or parsed.fragment
    ):
        raise AssertionError('Unsafe Gradio download URL')
    return normalized


def verify_delivery(report, archive_bytes):
    if not isinstance(report, dict):
        raise AssertionError('BIM report is not a JSON object')
    if report.get('levels') != 3 or report.get('source') != 'explicit_user_constraints':
        raise AssertionError('BIM report does not describe the requested three-floor model')
    if report.get('ifc_export_ready') is not False:
        raise AssertionError('Unverified IFC capability was incorrectly advertised')
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as package:
        expected = {
            'canonical_bim_handoff.json', 'schematic_walls.glb',
            'schematic_plan.dxf', 'plan.svg', 'front_elevation.svg',
            'KIEM_TRA_HINH_HOC.json', 'KIEM_TRA_MO_LAI.json',
        }
        names = package.namelist()
        if len(names) != len(set(names)):
            raise AssertionError('ZIP contains duplicate entries')
        if any(
            name.startswith('/') or '..' in name.split('/') or '\\' in name
            for name in names
        ):
            raise AssertionError('ZIP contains unsafe entry paths')
        missing = expected.difference(names)
        if missing:
            raise AssertionError('ZIP lacks BIM files: ' + ', '.join(sorted(missing)))
        for name in expected:
            if package.getinfo(name).file_size <= 0:
                raise AssertionError('BIM delivery has empty file: ' + name)
        if package.testzip() is not None:
            raise AssertionError('ZIP member CRC is invalid')
        model = json.loads(package.read('canonical_bim_handoff.json'))
        if len(model.get('levels', [])) != 3:
            raise AssertionError('Canonical model does not have three levels')
        if report.get('entity_count') != len(model.get('entities', [])):
            raise AssertionError('Report entity count differs from canonical model')
        checksum = hashlib.sha256(json.dumps(
            model, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False,
        ).encode('utf-8')).hexdigest()
        if report.get('model_checksum') != checksum:
            raise AssertionError('Report checksum differs from canonical BIM JSON')
        reopen_audit = None
        for audit_name in ('KIEM_TRA_HINH_HOC.json', 'KIEM_TRA_MO_LAI.json'):
            audit = json.loads(package.read(audit_name))
            if not isinstance(audit, dict) or not audit:
                raise AssertionError('Invalid or empty audit: ' + audit_name)
            if audit_name == 'KIEM_TRA_MO_LAI.json':
                reopen_audit = audit
        if reopen_audit != report.get('kiem_tra_mo_lai'):
            raise AssertionError('Reopen audit in ZIP differs from Gradio report')
        file_hashes = reopen_audit.get('sha256_tung_tep')
        if not isinstance(file_hashes, dict) or not file_hashes:
            raise AssertionError('Reopen audit lacks file checksums')
        for filename, recorded_sha in file_hashes.items():
            if filename not in names:
                raise AssertionError('Reopen audit references missing file: ' + filename)
            actual_sha = hashlib.sha256(package.read(filename)).hexdigest()
            if actual_sha != recorded_sha:
                raise AssertionError('Reopen audit checksum mismatch: ' + filename)
        if package.read('schematic_walls.glb')[:4] != b'glTF':
            raise AssertionError('Missing GLB binary geometry')
        if b'EOF' not in package.read('schematic_plan.dxf')[-128:]:
            raise AssertionError('DXF is missing its end marker')
        for svg_name in ('plan.svg', 'front_elevation.svg'):
            if b'<svg' not in package.read(svg_name)[:2048]:
                raise AssertionError('Invalid SVG file: ' + svg_name)


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
    if not isinstance(download, dict) or not (download.get('path') or download.get('name')):
        raise AssertionError('No downloadable ZIP in BIM button response')
    url = checked_download_url(download.get('url'))
    with urllib.request.urlopen(url, timeout=60) as response:
        archive_bytes = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise AssertionError('Unexpectedly large ZIP from three-floor smoke test')
    verify_delivery(report, archive_bytes)
    print('PASS: frozen Gradio BIM event, three floors, complete ZIP and model/report consistency')


if __name__ == '__main__':
    run_smoke()
