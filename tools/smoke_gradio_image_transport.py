"""Check frozen EXE Gradio can return and serve a real PNG without model weights."""
import json
import struct
import urllib.request
import urllib.error
from urllib.parse import quote

from tools.smoke_bim_ui import BASE, checked_download_url


def check_image_transport():
    request = urllib.request.Request(
        BASE + '/gradio_api/call/kiem_tra_truyen_anh',
        data=b'{"data":[]}',
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        queued = json.load(response)
    if not queued.get('event_id'):
        raise AssertionError('Image test event was not queued')
    with urllib.request.urlopen(
        BASE + '/gradio_api/call/kiem_tra_truyen_anh/' + queued['event_id'],
        timeout=60,
    ) as response:
        events = response.read().decode('utf-8')
    data = [
        json.loads(line[6:]) for line in events.splitlines()
        if line.startswith('data: ')
    ]
    if not data or not isinstance(data[-1], list) or not data[-1]:
        raise AssertionError('Gradio did not return an image')
    image = data[-1][0]
    if not isinstance(image, dict) or not image.get('url'):
        raise AssertionError('Gradio did not return image URL')
    candidates = [checked_download_url(image['url'])]
    path = image.get('path') or image.get('name')
    if isinstance(path, str):
        encoded = quote(path, safe='/:')
        candidates += [
            BASE + '/gradio_api/file=' + encoded,
            BASE + '/file=' + encoded,
        ]
    failures = []
    header = None
    for url in dict.fromkeys(candidates):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read(32)
            if data[:8] == bytes.fromhex('89504e470d0a1a0a'):
                header = data
                break
            failures.append('not PNG')
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            failures.append(str(exc))
    if header is None:
        raise AssertionError('No accessible PNG file endpoint: ' + '; '.join(failures))
    if header[:8] != b'\x89PNG\r\n\x1a\n':
        raise AssertionError('Image URL was not served as PNG')
    width, height = struct.unpack('>II', header[16:24])
    if (width, height) != (128, 96):
        raise AssertionError('Gradio image pixels have unexpected dimensions')
    print('PASS: frozen EXE Gradio can serve generated PNG via local URL')


if __name__ == '__main__':
    check_image_transport()
