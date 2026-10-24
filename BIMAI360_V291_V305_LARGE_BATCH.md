# V291–V305 internal hardening batch (one push/CI)

One aggregate source change, not fifteen claimed successful releases.

Implemented work items:
1. Retain job payload until result publication succeeds.
2. Retain reference input until result publication succeeds.
3. Prevent private reference image entering ZIP.
4. Prevent job request JSON entering ZIP.
5. Whitelist output files when creating ZIP.
6. Refuse duplicate output member names.
7. Refuse unsafe output file names.
8. Refuse missing/empty output files.
9. Verify ZIP CRC before public rename.
10. Verify output content SHA256 before publication.
11. Write worker receipt through atomic JSON.
12. Check ZIP SHA256 on parent receipt validation.
13. Reopen generated PNG to verify integrity on parent.
14. Check exact PNG bytes match output ZIP contents.
15. Prevent stale CUDA failure receipt from contaminating CPU retry.
16. Capture CPU retry failure evidence.
17. Use real log newlines for CPU retry separator.

Quality gates: GitHub Windows regression/build and extracted ZIP checks;
real SD1.5 hardware inference is NOT yet verified. Existing UI/buttons
unchanged. Do not promote to production without real PNG generation evidence.
