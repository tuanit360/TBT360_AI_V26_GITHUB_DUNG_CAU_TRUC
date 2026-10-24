"""One consistent contract for image generation and copyable diagnostics.

The UI always receives HTML, a safe status string and a log transcript.
A ZIP is only returned for successful generation. No fake image is created.
"""
from datetime import datetime, timezone
import logging
import hashlib
import uuid
from pathlib import Path
from zipfile import ZipFile, BadZipFile

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
        archive_path = Path(archive)
        if not archive_path.is_file():
            raise ValueError('Generated ZIP archive does not exist')
        try:
            with ZipFile(archive_path) as bundle:
                if bundle.testzip() is not None:
                    raise ValueError('Generated ZIP failed CRC check')
                included = set(bundle.namelist())
                if len(images) > 4:
                    raise ValueError('Generated image count exceeds UI limit')
                for filename, _label in images:
                    image_path = Path(filename)
                    if not image_path.is_file():
                        raise ValueError('Generated image is missing on disk')
                    if image_path.name not in included:
                        raise ValueError('Generated ZIP missing an output image')
                    archive_info = bundle.getinfo(image_path.name)
                    if archive_info.file_size == 0:
                        raise ValueError('Generated ZIP contains an empty image')
                    if archive_info.file_size != image_path.stat().st_size:
                        raise ValueError('Generated ZIP image size differs from output file')
                    source_digest = hashlib.sha256()
                    with image_path.open('rb') as source_stream:
                        for chunk in iter(lambda: source_stream.read(1024 * 1024), b''):
                            source_digest.update(chunk)
                    zip_digest = hashlib.sha256()
                    with bundle.open(archive_info) as zip_stream:
                        for chunk in iter(lambda: zip_stream.read(1024 * 1024), b''):
                            zip_digest.update(chunk)
                    if source_digest.digest() != zip_digest.digest():
                        raise ValueError('Generated ZIP image checksum differs from output file')
        except BadZipFile as exc:
            raise ValueError('Generated ZIP is not a valid archive') from exc
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
        root_cause = exc
        seen = set()
        while (root_cause.__cause__ or root_cause.__context__) and id(root_cause) not in seen:
            seen.add(id(root_cause))
            root_cause = root_cause.__cause__ or root_cause.__context__
        from app.generation_failures import explain_generation_failure
        # CalledProcessError is an implementation detail. Preserve only the
        # safe, allowlisted worker reason supplied by our own bridge.
        public_error = (
            exc if str(exc).startswith('AI worker thất bại (mã ')
            else root_cause
        )
        classified = explain_generation_failure(public_error)
        log('FAIL | ' + type(exc).__name__ + ' | ROOT_CAUSE=' + type(root_cause).__name__)
        log('PUBLIC_REASON | ' + classified)
        return (
            '<p>Không tạo được ảnh AI. Xem thông báo và log bên dưới.</p>',
            None,
            classified,
            '\n'.join(events) + '\nChi tiết kỹ thuật: logs/runtime_errors.log',
        )
