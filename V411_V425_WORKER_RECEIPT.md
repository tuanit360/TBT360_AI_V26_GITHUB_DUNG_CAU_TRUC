# V411–V425 aggregate receipt finalization

Single cumulative patch: remove unnecessary dynamic __import__ in the
real worker's ZIP hash computation (the helper is already statically
imported). Preserve the parent worker receipt verification gate while
reporting a safe PNG/ZIP failure if verification raises. Add static
regressions for the exact production entrypoints. Gradio layout and
buttons are unchanged. GitHub CI build is separate from real SD1.5
inference on the user's workstation.
