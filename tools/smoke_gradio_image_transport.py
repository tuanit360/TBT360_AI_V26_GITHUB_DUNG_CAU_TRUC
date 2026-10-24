"""Verify frozen Gradio can deliver real inline PNG via HTML without file URLs."""
import base64
import json
import urllib.request
from tools.smoke_bim_ui import BASE


def check_image_transport():
    request = urllib.request.Request(
        BASE + '/gradio_api/call/kiem_tra_render_doc_lap',
        data=b'{"data":[]}',
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        queued = json.load(response)
    event_id = queued.get('event_id')
    if not event_id:
        raise AssertionError('Inline image event did not queue')
    with urllib.request.urlopen(
        BASE + '/gradio_api/call/kiem_tra_render_doc_lap/' + event_id,
        timeout=60,
    ) as response:
        stream = response.read().decode('utf-8')
    events = [
        json.loads(line.removeprefix('data: '))
        for line in stream.splitlines() if line.startswith('data: ')
    ]
    if not events or not isinstance(events[-1], list):
        raise AssertionError('No render data from Gradio event')
    markup = events[-1][0]
    if not isinstance(markup, str):
        raise AssertionError('HTML diagnostic result is not text')
    prefix = 'data:image/png;base64,'
    if prefix not in markup:
        raise AssertionError('Missing inline PNG in diagnostic HTML')
    payload = markup.split(prefix, 1)[1].split('"', 1)[0]
    binary = base64.b64decode(payload, validate=True)
    if binary[:8] != bytes.fromhex('89504e470d0a1a0a'):
        raise AssertionError('Inline payload does not contain a PNG')
    from PIL import Image
    from io import BytesIO
    with Image.open(BytesIO(binary)) as decoded:
        decoded.load()
        if decoded.size != (128, 96):
            raise AssertionError('Diagnostic image has incorrect size')
    print('PASS: frozen Gradio rendered and returned valid inline PNG')


if __name__ == '__main__':
    check_image_transport()
