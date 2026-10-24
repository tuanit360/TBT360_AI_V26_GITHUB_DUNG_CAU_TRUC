"""Entry point with a lightweight self-test that works in a frozen build."""
import os
import runpy
import traceback
from datetime import datetime
import sys
from pathlib import Path


def root_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main():
    root = root_directory()
    os.environ['BIMAI360_HOME'] = str(root)
    temp_folder = root / 'output' / 'gradio_temp'
    try:
        temp_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f'[BIMAI360] Cannot create runtime folder: {temp_folder} ({exc})',
            file=sys.stderr,
            flush=True,
        )
        return 3
    os.environ['GRADIO_TEMP_DIR'] = str(temp_folder)
    # Legacy environment alias retained for existing integrations.
    os.environ['TBT360_HOME'] = str(root)
    # Gradio's localhost readiness probe must bypass HTTP(S) proxies.
    # Keep existing exclusions and never enable a public share link.
    for key in ('NO_PROXY', 'no_proxy'):
        entries = [value.strip() for value in os.environ.get(key, '').split(',') if value.strip()]
        for host in ('127.0.0.1', 'localhost', '::1'):
            if host not in entries:
                entries.append(host)
        os.environ[key] = ','.join(entries)
    if '--ifc-export-child' in sys.argv:
        from app.ifc_isolated_bridge import run_ifc_child
        position = sys.argv.index('--ifc-export-child')
        if len(sys.argv) != position + 2:
            return 2
        return run_ifc_child(sys.argv[position + 1])
    if '--ifc-export-self-test' in sys.argv:
        from app.ifc_portable_smoke import test_frozen_ifc_export
        import json
        print(json.dumps(test_frozen_ifc_export(root), ensure_ascii=True), flush=True)
        return 0
    if '--last-failure-bundle' in sys.argv:
        from app.worker_diagnostic_bundle import make_worker_bundle
        print(make_worker_bundle(root), flush=True)
        return 0
    if '--last-worker-report' in sys.argv:
        from app.worker_evidence import read_report
        import json
        print(json.dumps(read_report(root), ensure_ascii=True), flush=True)
        return 0
    if '--cpu-preflight' in sys.argv:
        from tools.cpu_generation_preflight import build_cpu_preflight_report
        import json
        report = build_cpu_preflight_report(root)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        destination = root / 'logs' / 'cpu_preflight.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        return 0 if report['ready'] else 2
    if '--worker-failure-self-test' in sys.argv:
        from app.windows_console import print_portable_json
        from app.worker_failure_smoke import run_failure_contract
        print_portable_json(run_failure_contract(root))
        return 0

        import json
        from app.worker_failure_smoke import run_failure_contract
        print(json.dumps(run_failure_contract(root), ensure_ascii=False), flush=True)
        return 0
    if '--worker-runtime-child' in sys.argv:
        from app.worker_runtime_report import child_report
        import json
        print(json.dumps(child_report(root), ensure_ascii=False), flush=True)
        return 0
    if '--worker-runtime-self-test' in sys.argv:
        from app.worker_runtime_report import parent_report
        import json
        print(json.dumps(parent_report(root), ensure_ascii=False, indent=2), flush=True)
        return 0
    if '--worker-transport-probe' in sys.argv:
        from app.worker_transport_smoke import worker_probe
        index = sys.argv.index('--worker-transport-probe')
        if len(sys.argv) <= index + 1:
            return 2
        worker_probe(sys.argv[index + 1])
        return 0
    if '--worker-transport-self-test' in sys.argv:
        from app.worker_transport_smoke import parent_probe
        import json
        print(json.dumps(parent_probe(root), ensure_ascii=False), flush=True)
        return 0
    if '--worker-image' in sys.argv:
        from app.isolated_image_worker import main as worker_main
        arguments = [arg for arg in sys.argv[1:] if arg != '--worker-image']
        return worker_main(arguments)
    if '--diagnostics' in sys.argv:
        from app.diagnostic_bundle import build_diagnostic_zip
        print(build_diagnostic_zip(root), flush=True)
        return 0
    if '--self-test' in sys.argv:
        from tools.runtime_diagnostics import diagnostic_report
        import json
        report = diagnostic_report(root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['ok'] else 2
    for name in ('models', 'output', 'loras', 'dataset', 'logs'):
        folder = root / name
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f'[BIMAI360] Cannot prepare {name}: {exc}', file=sys.stderr, flush=True)
            return 3
    import logging
    from logging.handlers import RotatingFileHandler
    runtime_logger = logging.getLogger('bimai360')
    runtime_logger.setLevel(logging.INFO)
    runtime_handler = RotatingFileHandler(
        root / 'logs' / 'runtime_errors.log', maxBytes=512 * 1024,
        backupCount=2, encoding='utf-8',
    )
    runtime_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    ))
    runtime_logger.addHandler(runtime_handler)
    # Keep a native crash traceback even if Gradio/HTTP is no longer alive.
    # This file is opened independently of every browser callback.
    import faulthandler
    crash_stream = (root / 'logs' / 'python_fatal.log').open(
        'a', encoding='utf-8',
    )
    faulthandler.enable(file=crash_stream, all_threads=True)
    # Gradio/FastAPI errors often bypass the application logger, leaving
    # only a red "Error" badge in the browser. Keep their traceback locally.
    for logger_name in ('gradio', 'uvicorn.error', 'starlette'):
        framework_logger = logging.getLogger(logger_name)
        if runtime_handler not in framework_logger.handlers:
            framework_logger.addHandler(runtime_handler)
    from app.gradio_compat import install_boolean_schema_support
    install_boolean_schema_support()
    try:
        runpy.run_module('app.generate', run_name='__main__')
    except Exception:
        details = traceback.format_exc()
        print(details, file=sys.stderr, flush=True)
        try:
            log_dir = root / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / 'startup_error.log').open('a', encoding='utf-8') as handle:
                handle.write(f'\n=== {datetime.now().isoformat()} ===\n')
                handle.write(details)
        except OSError:
            pass
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
