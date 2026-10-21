"""Entry point with a lightweight self-test that works in a frozen build."""
import os
import runpy
import sys
from pathlib import Path


def root_directory():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main():
    root = root_directory()
    os.environ['TBT360_HOME'] = str(root)
    # Gradio's localhost readiness probe must bypass HTTP(S) proxies.
    # Keep existing exclusions and never enable a public share link.
    for key in ('NO_PROXY', 'no_proxy'):
        entries = [value.strip() for value in os.environ.get(key, '').split(',') if value.strip()]
        for host in ('127.0.0.1', 'localhost', '::1'):
            if host not in entries:
                entries.append(host)
        os.environ[key] = ','.join(entries)
    if '--self-test' in sys.argv:
        from tools.runtime_diagnostics import diagnostic_report
        import json
        report = diagnostic_report(root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['ok'] else 2
    for name in ('models', 'output', 'loras', 'dataset', 'logs'):
        (root / name).mkdir(parents=True, exist_ok=True)
    from app.gradio_compat import install_boolean_schema_support
    install_boolean_schema_support()
    runpy.run_module('app.generate', run_name='__main__')
    return 0


if __name__ == '__main__':
    sys.exit(main())
