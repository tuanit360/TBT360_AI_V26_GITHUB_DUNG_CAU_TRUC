"""Real subprocess / frozen executable transport smoke without an AI model."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from PIL import Image


def worker_probe(job_dir):
    job_dir = Path(job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    output = job_dir / 'probe.png'
    image = Image.new('RGB', (96, 64), (30, 90, 160))
    image.save(output, format='PNG')
    with Image.open(output) as check:
        check.verify()
    archive = job_dir / 'probe.zip'
    with ZipFile(archive, 'w') as bundle:
        bundle.write(output, arcname='probe.png')
    report = {
        'schema': 'bimai360.worker_transport.v1',
        'status': 'PASS_TRANSPORT_ONLY',
        'png_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (job_dir / 'probe_report.json').write_text(
        json.dumps(report), encoding='utf-8')
    return report


def parent_probe(root, timeout=60):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='bimai360_worker_') as temporary:
        working = Path(temporary)
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--worker-transport-probe', str(working)]
        else:
            command = [
                sys.executable, '-m', 'app.worker_transport_smoke',
                '--child', str(working),
            ]
        completed = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                'Isolated worker transport exited with '
                + str(completed.returncode)
            )
        report_path = working / 'probe_report.json'
        if not report_path.is_file():
            raise RuntimeError('Worker report missing')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        if report.get('schema') != 'bimai360.worker_transport.v1':
            raise RuntimeError('Worker schema mismatch')
        if report.get('status') != 'PASS_TRANSPORT_ONLY':
            raise RuntimeError('Worker did not succeed')
        image = working / 'probe.png'
        archive = working / 'probe.zip'
        if hashlib.sha256(image.read_bytes()).hexdigest() != report['png_sha256']:
            raise RuntimeError('PNG SHA256 mismatch')
        if hashlib.sha256(archive.read_bytes()).hexdigest() != report['zip_sha256']:
            raise RuntimeError('ZIP SHA256 mismatch')
        with ZipFile(archive) as bundle:
            if bundle.testzip() is not None:
                raise RuntimeError('ZIP CRC failure')
            if bundle.read('probe.png') != image.read_bytes():
                raise RuntimeError('Worker ZIP does not contain matching PNG')
        return report


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        worker_probe(sys.argv[2])
    else:
        raise SystemExit('Usage: python -m app.worker_transport_smoke --child DIR')
