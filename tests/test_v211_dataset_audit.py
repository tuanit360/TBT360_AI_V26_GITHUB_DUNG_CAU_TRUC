import tempfile
import unittest
import zipfile
from pathlib import Path
from training.audit_uploaded_archives import audit_archives


class V211DatasetAuditTests(unittest.TestCase):
    def test_real_zip_inventory_never_fabricates_bim_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'user_architecture.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('P001/front.png', b'fake pixels')
                archive.writestr('P001/plan.dxf', b'0\nEOF\n')
                archive.writestr('P001/model.glb', b'glTF')
            result = audit_archives([path])
            self.assertEqual(result['totals']['image_unlabeled'], 1)
            self.assertEqual(result['totals']['model_unverified'], 1)
            self.assertFalse(result['training_ready'])
            self.assertFalse(any(e['label_verified'] for e in result['files']))

    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'malicious.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('../outside.jpg', b'x')
            result = audit_archives([path])
            self.assertEqual(result['files'], [])
            self.assertEqual(len(result['uninspected_archives']), 1)
