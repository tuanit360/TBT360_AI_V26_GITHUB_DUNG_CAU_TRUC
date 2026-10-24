# V282 — Explain child-worker failures in the existing Gradio status

Previous V281 only forwarded CalledProcessError and preserved a traceback in
logs/image_worker.log, forcing the user to locate the child-process failure.
V282 adds an atomic, minimal worker_failure.json with an allowlisted error
code. The parent maps the code to a safe Vietnamese message without exposing
filesystem paths, prompts, tokens or traceback in the browser.

If Windows kills the process with no Python exception, no status file exists:
the UI explicitly reports that the child ended without a report. The full
traceback remains in the local log when Python can produce one. This patch
does not fake an AI output, enable a missing checkpoint or guarantee working
inference on every Windows machine. The UI layout/buttons remain unchanged.
