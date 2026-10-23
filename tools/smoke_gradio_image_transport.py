"""Check frozen EXE Gradio can return and serve a real PNG without model weights."""
import json
import struct
import urllib.request

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
    url = checked_download_url(image['url'])
    with urllib.request.urlopen(url, timeout=30) as response:
        header = response.read(32)
    if header[:8] != b'\x89PNG\r\n\x1a\n':
        raise AssertionError('Image URL was not served as PNG')
    width, height = struct.unpack('>II', header[16:24])
    if (width, height) != (128, 96):
        raise AssertionError('Gradio image pixels have unexpected dimensions')
    print('PASS: frozen EXE Gradio can serve generated PNG via local URL')


if __name__ == '__main__':
    check_image_transport()
