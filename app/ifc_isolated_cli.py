"""Entrypoint for source-runtime isolated IFC export."""
import sys
from app.ifc_isolated_bridge import run_ifc_child


if __name__ == '__main__':
    raise SystemExit(run_ifc_child(sys.argv[1]) if len(sys.argv) == 2 else 2)
