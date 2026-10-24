"""Exercise the ACTUAL Gradio IFC event, not an EXE-only CLI probe."""
import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

from gradio_client import Client, handle_file
from PIL import Image


def run():
    with tempfile.TemporaryDirectory() as temp:
        photo = Path(temp) / 'photo.png'
        Image.new('RGB', (96, 96), (110, 150, 175)).save(photo)
        client = Client('http://127.0.0.1:7861/', verbose=False)
        result = client.predict(
            handle_file(str(photo)),
            api_name='/xuat_5_phuong_an_ifc',
        )
        if not isinstance(result, (list, tuple)) or len(result) != 2:
            raise AssertionError('IFC UI did not return file and status')
        artifact, status = result
        if not artifact or not isinstance(status, str):
            raise AssertionError('IFC UI callback failed: ' + str(status))
        if isinstance(artifact, dict):
            local_path = artifact.get('path') or artifact.get('name')
        else:
            local_path = artifact
        archive = Path(str(local_path))
        if not archive.is_file():
            raise AssertionError('Gradio did not return downloadable IFC ZIP')
        with ZipFile(archive) as z:
            expected = {'manifest.json'} | {
                'PA%02d.ifc' % i for i in range(1, 6)
            }
            if set(z.namelist()) != expected or z.testzip() is not None:
                raise AssertionError('Gradio returned invalid IFC ZIP')
            manifest = json.loads(z.read('manifest.json'))
            if (manifest.get('alternatives_not_independent_houses') is not True
                    or len(manifest.get('options', [])) != 5):
                raise AssertionError('IFC variants have invalid handoff metadata')
        # The UI must still be responsive immediately after the IFC callback.
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:7861/', timeout=10) as response:
            if response.status != 200:
                raise AssertionError('Gradio died during IFC export')
        print('PASS: frozen Gradio IFC click, five model ZIP, UI still responsive')


if __name__ == '__main__':
    run()
