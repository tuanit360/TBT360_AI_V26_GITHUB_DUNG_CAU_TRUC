"""One consistent contract for image generation and copyable diagnostics.

The UI always receives HTML, a safe status string and a log transcript.
A ZIP is only returned for successful generation. No fake image is created.
"""
from datetime import datetime, timezone
import logging
import uuid

from app.diagnostic_image_render import render_image_gallery
from app.generation_failures import explain_generation_failure


def image_generation_contract(root, generator, arguments, *, progress=None,
                              offline=False, readiness=None):
    from app.local_workspace import record_operation
    attempt = uuid.uuid4().hex[:12]
    stamp = datetime.now(timezone.utc).isoformat()
    events = [f'{stamp} | IMAGE_GENERATION | attempt={attempt} | START']
    def log(status):
        events.append(f'{datetime.now(timezone.utc).isoformat()} | {status}')
    try:
        record_operation(root, 'generate', 'started')
        if offline and readiness is not None and not readiness.get('model_files_complete'):
            record_operation(root, 'generate', 'blocked_missing_model')
            message = ('Chưa có checkpoint SD1.5 cục bộ đầy đủ. '
                       'Kiểm tra models/sd15 hoặc tắt chế độ offline nếu có mạng.')
            log('BLOCKED_MISSING_MODEL')
            return '<p>Chưa tạo ảnh AI.</p>', None, message, '\n'.join(events)
        result = generator(*arguments, progress=progress)
        if not isinstance(result, tuple) or len(result) != 3:
            raise ValueError('Generator returned invalid output contract')
        images, archive, status = result
        if not images or not archive:
            raise ValueError('Generator produced no deliverable image and archive')
        markup = render_image_gallery(images)
        record_operation(root, 'generate', 'completed')
        log('PASS | images=' + str(len(images)))
        return markup, archive, str(status), '\n'.join(events)
    except Exception as exc:
        logging.getLogger('bimai360').exception(
            'Image generation attempt %s failed', attempt
        )
        try:
            record_operation(root, 'generate', 'failed')
        except (OSError, ValueError):
            logging.getLogger('bimai360').exception('Operation log unavailable')
        log('FAIL | ' + type(exc).__name__)
        return (
            '<p>Không tạo được ảnh AI. Xem thông báo và log bên dưới.</p>',
            None,
            explain_generation_failure(exc),
            '\n'.join(events) + '\nChi tiết kỹ thuật: logs/runtime_errors.log',
        )
