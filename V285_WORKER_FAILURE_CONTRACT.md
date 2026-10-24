# V285 — frozen child-worker failure acceptance gate

V281 through V284 test worker execution and dependency imports, but did not
invoke the real `--worker-image` failure-handling path from the frozen EXE.
V285 executes a deliberately invalid job in a separate process and requires:
non-zero worker exit, worker_failure.json with safe allowlisted error code,
parent-readable Vietnamese message, and a surviving application process.

Use `BIMAI360.exe --worker-failure-self-test`. No model is imported or
downloaded and no AI image is fabricated. CI PASS proves only the failure
contract and packaging; real SD1.5 PNG/ZIP generation still requires
checkpoint and device verification on the user machine.
