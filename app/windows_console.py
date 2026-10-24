"""Write machine-readable JSON on Windows even with legacy console encodings."""
import json
import sys


def print_portable_json(data, output=None):
    output = sys.stdout if output is None else output
    # Default ensure_ascii=True guarantees a valid ASCII-only JSON wire format;
    # UI and UTF-8 report files continue to use full Vietnamese Unicode.
    payload = json.dumps(data, ensure_ascii=True)
    output.write(payload + '\n')
    output.flush()
