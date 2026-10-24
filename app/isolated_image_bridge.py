"""Launch a separate Python/EXE worker; Gradio never imports Diffusers."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from PIL import Image


def execute_image_job(root, args, *, timeout=900):
    from app.generation_stage import write_generation_stage
    root = Path(root).resolve()
    image, brief, preserve, steps, count, seed, aspect, fit_mode, memory_mode, lora, style, guidance, scale, sharpness = args
    if not isinstance(image, Image.Image):
        raise ValueError('Hãy chọn ảnh tham chiếu hợp lệ.')
    from app.architecture_preflight import inspect_reference
    inspection = inspect_reference(image)
    if not inspection['ready']:
        raise ValueError('; '.join(inspection['blocking']))
    if not 10 <= int(steps) <= 50 or not 1 <= int(count) <= 4:
        raise ValueError('Số bước hoặc số phương án không hợp lệ.')
    if not 0.15 <= float(preserve) <= 0.85:
        raise ValueError('Độ giữ cấu trúc không hợp lệ.')
    if int(scale) not in (1, 2, 4) or not 0 <= float(sharpness) <= 1:
        raise ValueError('Thông số ảnh không hợp lệ.')
    # Reuse the known prompt catalog without importing the Gradio application.
    from app.worker_prompts import build_prompt
    prompt, negative = build_prompt(brief, style)
    run_dir = root / 'output' / ('isolated_' + secrets.token_hex(8))
    run_dir.mkdir(parents=True, exist_ok=False)
    source_path = run_dir / 'reference_input.png'
    image.convert('RGB').save(source_path, format='PNG')
    request = {'schema': 'bimai360.worker.v1',
               'steps': int(steps), 'count': int(count),
               'strength': 1 - float(preserve),
               'seed': int(seed) if int(seed) >= 0 else secrets.randbelow(2**31 - 2) + 1,
               'aspect': aspect, 'fit_mode': fit_mode,
               'memory_mode': memory_mode, 'lora': lora,
               'style': style, 'prompt': prompt, 'negative': negative,
               'guidance': float(guidance), 'scale': int(scale),
               'sharpness': float(sharpness)}
    job_path = run_dir / 'job.json'
    job_path.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
    log_dir = root / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    # In a frozen build sys.executable is the real BIMAI360.exe.
    command = ([sys.executable, '--worker-image', '--job', str(job_path)]
               if getattr(sys, 'frozen', False)
               else [sys.executable, '-m', 'app.isolated_image_worker',
                     '--job', str(job_path)])
    environment = os.environ.copy()
    environment['BIMAI360_HOME'] = str(root)
    environment['TBT360_HOME'] = str(root)
    environment.setdefault('NO_PROXY', '127.0.0.1,localhost,::1')
    write_generation_stage(root, 'START', 'ISOLATED_WORKER')
    with (log_dir / 'image_worker.log').open('a', encoding='utf-8') as logfile:
        try:
            subprocess.run(
                command, cwd=root, env=environment,
                stdout=logfile, stderr=subprocess.STDOUT,
                timeout=timeout, check=True,
            )
        except subprocess.TimeoutExpired as exc:
            from app.worker_diagnostic_bundle import make_worker_bundle
            try:
                make_worker_bundle(root, job_id=run_dir.name.removeprefix('isolated_'))
            except (OSError, ValueError):
                pass
            raise RuntimeError('AI worker quá thời gian; ứng dụng chính vẫn hoạt động. Xem logs/image_worker.log') from exc
        except subprocess.CalledProcessError as exc:
            from app.worker_diagnostic_bundle import make_worker_bundle
            try:
                make_worker_bundle(root, job_id=run_dir.name.removeprefix('isolated_'))
            except (OSError, ValueError):
                pass
            from app.worker_failure import read_safe_worker_failure
            from app.worker_retry import should_retry_cpu
            report = run_dir / 'worker_failure.json'
            reason = read_safe_worker_failure(report)
            if not should_retry_cpu(report, environment):
                raise RuntimeError(
                    'AI worker thất bại (mã ' + str(exc.returncode)
                    + '). ' + reason + ' Chi tiết: logs/image_worker.log.'
                ) from exc
            from app.windows_memory import available_ram_gib
            free_ram = available_ram_gib()
            if free_ram is not None and free_ram < 7:
                raise RuntimeError(
                    'CUDA không hoạt động; CPU cần ít nhất 7 GiB RAM khả dụng.'
                ) from exc
            cpu_env = environment.copy()
            cpu_env['BIMAI360_FORCE_CPU'] = '1'
            logfile.write('\n--- RETRY_CLEAN_CPU_WORKER ---\n')
            logfile.flush()
            # Remove the first attempt's stale error receipt before retry.
            try:
                report.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                subprocess.run(
                    command, cwd=root, env=cpu_env,
                    stdout=logfile, stderr=subprocess.STDOUT,
                    timeout=timeout, check=True,
                )
            except (subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as retry_exc:
                try:
                    make_worker_bundle(root, job_id=run_dir.name.removeprefix('isolated_'))
                except (OSError, ValueError):
                    pass
                reason = read_safe_worker_failure(report)
                raise RuntimeError(
                    'CPU dự phòng không thành công. ' + reason
                    + ' Xem logs/image_worker.log.'
                ) from retry_exc
    report_path = run_dir / 'worker_result.json'
    if not report_path.is_file():
        raise RuntimeError('AI worker kết thúc mà không có báo cáo kết quả.')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    from app.worker_output_contract import verify_worker_receipt
    verify_worker_receipt(report, run_dir)
    if report.get('status') != 'PASS_REAL_INFERENCE':
        raise RuntimeError('AI worker chưa tạo được ảnh hợp lệ.')
    files = report.get('images')
    if not isinstance(files, list) or not files:
        raise RuntimeError('AI worker không có ảnh đầu ra.')
    archive = Path(report['archive']).resolve()
    if archive.parent != run_dir.parent or not archive.is_file():
        raise RuntimeError('Đường dẫn ZIP AI worker không hợp lệ.')
    for filename, _ in files:
        path = Path(filename).resolve()
        if path.parent != run_dir or not path.is_file():
            raise RuntimeError('Kết quả worker không nằm trong thư mục job.')
    return files, str(archive), (
        f'Đã sinh {len(files)} phương án bằng tiến trình AI riêng '
        f'({report["device"]}); PNG và ZIP đã được kiểm tra.'
    )
