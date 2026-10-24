# V287 — safe worker failure reason through Gradio contract

Fixes swallowed worker reasons: the image-generation contract previously walked to the chained CalledProcessError, losing the parent bridge's allowlisted worker explanation. It now classifies that safe bridge error without exposing traceback, secrets or filesystem paths. Regression tests verify missing-checkpoint and redaction. No UI changes. Successful SD1.5 inference on user hardware still requires separate verification.
