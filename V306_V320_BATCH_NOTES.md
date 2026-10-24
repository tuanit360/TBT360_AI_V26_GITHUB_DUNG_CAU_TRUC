# V306–V320 aggregate quality gate, single push

Fixes Windows cp1252 regression by reading the UTF-8 worker receipt
with an explicit UTF-8 decoder. Strengthens published ZIP boundaries,
limits unexpected output files, and rejects extra unreported PNGs.
No change to existing Gradio layout, command buttons, BIM data or
model inference. The version range is an internal batch label, not
15 independently verified releases.

Windows CI regression, executable packaging, extracted ZIP smoke
and real user-machine SD1.5 inference remain separate proof levels.
