"""Bounded child-process IFC export: protects Gradio from native IFC crashes."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import traceback

from PIL import Image


def run_ifc_child(job_path):
    job = Path(job_path).resolve()
    try:
        if job.name != 'request.json':
            return 2
        config = json.loads(job.read_text(encoding='utf-8'))
        source = job.parent / 'reference.png'
        if source.is_symlink() or source.stat().st_size > 25 * 1024 * 1024:
            raise ValueError('Invalid IFC reference file')
        with Image.open(source) as image:
            image.load()
            from app.five_concept_ifc import export_five_concepts
            archive, message = export_five_concepts(
                image.convert('RGB'), config['root'],
            )
        result = {'status': 'OK', 'archive': archive, 'message': message}
        (job.parent / 'result.json').write_text(
            json.dumps(result, ensure_ascii=False), encoding='utf-8',
        )
        return 0
    except Exception:
        (job.parent / 'error.txt').write_text(
            traceback.format_exc()[-8000:], encoding='utf-8',
        )
        return 1


def export_isolated_ifc(image, root):
    if not isinstance(image, Image.Image):
        return None, 'Hãy tải ảnh công trình tham chiếu trước khi xuất IFC.'
    root = Path(root).resolve()
    work = root / 'output' / 'ifc_jobs' / secrets.token_hex(12)
    work.mkdir(parents=True, exist_ok=False)
    reference = work / 'reference.png'
    image.convert('RGB').save(reference)
    job = work / 'request.json'
    job.write_text(json.dumps({'root': str(root)}), encoding='utf-8')
    command = (
        [sys.executable, '--ifc-export-child', str(job)]
        if getattr(sys, 'frozen', False)
        else [sys.executable, '-m', 'app.ifc_isolated_cli', str(job)]
    )
    logfile = root / 'logs' / 'ifc_export.log'
    logfile.parent.mkdir(parents=True, exist_ok=True)
    try:
        with logfile.open('a', encoding='utf-8') as log:
            attempt = subprocess.run(
                command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                timeout=180, check=False,
            )
        if attempt.returncode != 0:
            error_file = work / 'error.txt'
            if error_file.is_file():
                with logfile.open('a', encoding='utf-8') as log:
                    log.write('\\n--- IFC CHILD ERROR ---\\n')
                    log.write(error_file.read_text(encoding='utf-8')[-8000:])
            return None, (
                'Worker IFC thất bại hoặc bị ngắt (mã '
                + str(attempt.returncode) + '). Xem logs/ifc_export.log.'
            )
        receipt = work / 'result.json'
        if not receipt.is_file() or receipt.stat().st_size > 8192:
            return None, 'Worker IFC không trả báo cáo hợp lệ.'
        result = json.loads(receipt.read_text(encoding='utf-8'))
        archive = Path(str(result.get('archive', ''))).resolve()
        if (result.get('status') != 'OK' or not archive.is_file()
                or archive.suffix.lower() != '.zip'
                or archive.parent != root / 'output'):
            return None, 'Worker IFC xuất kết quả không hợp lệ.'
        return str(archive), str(result['message'])[:500]
    except subprocess.TimeoutExpired:
        return None, 'Xuất IFC quá thời gian. Gradio vẫn hoạt động; xem logs/ifc_export.log.'
    except (OSError, ValueError, KeyError, TypeError):
        return None, 'Lỗi kết nối tiến trình xuất IFC. Xem logs/ifc_export.log.'
    finally:
        for item in (reference, job, work / 'result.json', work / 'error.txt'):
            try:
                item.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            work.rmdir()
        except OSError:
            pass
