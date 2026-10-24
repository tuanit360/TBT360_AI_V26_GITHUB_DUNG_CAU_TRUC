# V321–V335 — single batch for low-memory result transport

This one-push internal batch replaces full read_bytes() of generated PNG/ZIP
with streaming SHA256 and streaming ZIP/file byte comparisons. Archive
writing now uses ZipFile.write rather than loading every image fully into
memory. Generated gallery previews are capped at 640 px, while archived
originals retain full resolution. Regression covers actual PNG-to-ZIP
roundtrip and previews. No UI buttons are moved, removed or renamed.

The change lowers peak post-inference memory consumption. It does not
guarantee sufficient memory to load SD1.5 nor demonstrate real inference
on the user's PC. 15-version range is an internal batch label, not 15
verified product releases.
