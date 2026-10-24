"""Minimal stage breadcrumbs independent of Gradio queue or ML libraries."""
from datetime import datetime, timezone
from pathlib import Path
import os


def write_generation_stage(root, stage, detail):
    """Best effort only: diagnostics must never break the generation request."""
    if stage not in {
        'START', 'MODEL_LOAD', 'LORA', 'INFERENCE',
        'PNG_SAVE', 'ZIP_EXPORT', 'FAILED',
    }:
        return
    try:
        log_dir = Path(root) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        # Bounds payload and avoids leaking model names, prompts or user paths.
        safe_detail = ''.join(
            char for char in str(detail)[:72]
            if char.isalnum() or char in ' =_-'
        )
        line = f'{stamp} | pid={os.getpid()} | {stage} | {safe_detail}\n'
        with (log_dir / 'generation_stage.log').open('a', encoding='utf-8') as handle:
            handle.write(line)
            handle.flush()
    except OSError:
        pass
