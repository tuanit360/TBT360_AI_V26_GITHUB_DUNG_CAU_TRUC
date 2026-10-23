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
    temp_folder.mkdir(parents=True, exist_ok=True)
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
        (root / name).mkdir(parents=True, exist_ok=True)
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
                handle.write(f'\\n=== {datetime.now().isoformat()} ===\\n')
                handle.write(details)
        except OSError:
            pass
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
