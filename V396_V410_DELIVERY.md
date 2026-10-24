# V396–V410 delivery contract recovery

This aggregated batch restores an accidentally lost worker fix: never
delete job.json/reference_input.png until ZIP and atomic receipt have been
published, and never include those private inputs in ZIP. The bridge
must verify the actual ZIP SHA256, CRC, member names, generated PNG bytes
and decoding before reporting AI success. The CI test uses a synthetic PNG
to validate transport, not fake AI inference. UI/buttons unchanged.
