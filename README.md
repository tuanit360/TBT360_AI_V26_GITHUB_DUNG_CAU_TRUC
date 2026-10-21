# TBT360 GitHub Actions diagnostic patch

Confirmed from job 119274651587: unit tests failed on `Asset SHA256 mismatch` in evaluation/metric_gate.py. The precise changed asset(s) are not visible without the full logs. Repo `.gitattributes` uses `* text=auto`, so Git EOL normalization is one possible cause, **not confirmed**.

## Apply
Copy `.github/workflows/windows-build.yml` and `tools/diagnose_asset_hashes.py` to the same relative paths in your GitHub repository, then commit. This is a diagnostic/build-tools patch, **not** a fix for corrupted data, and it is not the full application source.

The workflow adds a pinned Python version, explicit PyInstaller installation, the SHA256 diagnostic, and failed-job upload of its JSON report. It does not disable any existing unit tests or checksum validation.

After running Actions, download `SHA256_DIAGNOSTICS` if available. Check `only_line_ending_difference` for mismatches. If true, decide whether the repository should preserve binary bytes (`-text`) for that specific *immutable data file* or regenerate its hash from verified canonical bytes. Do not blindly replace hashes to force passing tests. If no mismatch appears in the report, obtain the full Actions test log: some tests alter assets in temporary folders not visible in repository manifests.

This workflow still uses the repo's existing EXE build strategy, which has **not** been verified to work with all the runtime AI dependencies. Expect follow-up packaging fixes based on actual Windows build results.
