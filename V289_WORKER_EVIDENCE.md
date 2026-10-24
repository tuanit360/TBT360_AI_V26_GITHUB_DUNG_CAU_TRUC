# V289 — last known isolated-worker state

CLI: BIMAI360.exe --last-worker-report
A privacy-safe, job-ID-bound last_worker_state.json is written in logs.
Stages cover boot, torch/Diffusers import, model loading, inference,
PNG and ZIP publication. It never contains prompts, images, credentials
or filesystem paths. Missing report is represented explicitly.
The UI is unchanged. An abrupt worker crash may leave the last stage
but no Python traceback. Real image inference remains unverified.
