"""Validate real IFC authoring from the frozen EXE without any online models."""
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile

from PIL import Image


def test_frozen_ifc_export(root):
    import ifcopenshell
    from app.five_concept_ifc import export_five_concepts
    # Use a bounded reference; avoids torch, CUDA, Diffusers and network.
    with tempfile.TemporaryDirectory(prefix='bimai360-ifc-probe-') as directory:
        archive, message = export_five_concepts(
            Image.new('RGB', (96, 96), (125, 156, 184)),
            directory,
        )
        with ZipFile(archive) as bundle:
            required = {'manifest.json'} | {
                'PA%02d.ifc' % i for i in range(1, 6)
            }
            actual = set(bundle.namelist())
            if actual != required or bundle.testzip() is not None:
                raise RuntimeError('IFC bundle missing members or invalid ZIP')
            manifest = json.loads(bundle.read('manifest.json'))
            if len(manifest.get('options', [])) != 5:
                raise RuntimeError('IFC manifest missing variants')
            counts = {}
            for i in range(1, 6):
                filename = 'PA%02d.ifc' % i
                candidate = Path(directory) / ('probe-' + filename)
                candidate.write_bytes(bundle.read(filename))
                model = ifcopenshell.open(str(candidate))
                if model.schema != 'IFC4':
                    raise RuntimeError('Invalid IFC4 model')
                for kind in ('IfcWall', 'IfcColumn', 'IfcLightFixture',
                             'IfcPipeSegment'):
                    if not model.by_type(kind):
                        raise RuntimeError(filename + ' missing ' + kind)
                counts[filename] = len(model.by_type('IfcElement'))
        return {'status': 'PASS_REAL_IFC_EXPORT', 'models': 5,
                'ifcopenshell': ifcopenshell.version,
                'element_counts': counts}
