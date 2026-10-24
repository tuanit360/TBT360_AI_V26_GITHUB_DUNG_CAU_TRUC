import json
import tempfile
import unittest
from pathlib import Path

from app.canonical_bim_contract import build_handoff
from app.bim_persistence import save_project, open_project
from app.bim_history import BIMHistory
from app.bim_transaction import canonical_checksum


class V111PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.document = build_handoff(
            'office_111', level_ids=[{'id': 'L01', 'elevation': 0}],
            elements=[{'id': 'W1', 'level_id': 'L01', 'category': 'wall'}])

    def test_save_reopen_undo_redo_checksum(self):
        history = BIMHistory(self.document)
        before = canonical_checksum(history.document)
        history.update('W1', {'geometry': {'origin': [1, 2, 0]}})
        after = canonical_checksum(history.document)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'project.json'
            report = save_project(history.document, path)
            reopened = open_project(path, report['sha256'])
            self.assertEqual(canonical_checksum(reopened), after)
            history.undo()
            self.assertEqual(canonical_checksum(history.document), before)
            history.redo()
            self.assertEqual(canonical_checksum(history.document), after)

    def test_corruption_does_not_pass_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'project.json'
            report = save_project(self.document, path)
            path.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                open_project(path, report['sha256'])

    def test_reject_bad_schema_and_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_project(self.document, Path(folder) / 'not_a_project.txt')
            broken = dict(self.document, ifc_export_ready=True)
            with self.assertRaises(ValueError):
                save_project(broken, Path(folder) / 'project.json')

    def test_saved_content_is_canonical(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'project.json'
            save_project(self.document, path)
            content = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(content['entities'], self.document['entities'])
            self.assertFalse(content['ifc_export_ready'])
