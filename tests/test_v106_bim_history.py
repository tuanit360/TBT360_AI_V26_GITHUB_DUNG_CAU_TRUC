import copy
import unittest
from app.canonical_bim_contract import build_handoff
from app.bim_history import BIMHistory
from app.bim_transaction import canonical_checksum


class V106HistoryTests(unittest.TestCase):
    def setUp(self):
        self.source = build_handoff('office_106', level_ids=[{'id': 'L1', 'elevation': 0.0}],
                                    elements=[{'id': 'W1', 'category': 'wall', 'level_id': 'L1'},
                                              {'id': 'D1', 'category': 'door', 'level_id': 'L1', 'host_id': 'W1'}])

    def test_roundtrip_and_no_collateral_changes(self):
        history = BIMHistory(self.source)
        before = canonical_checksum(history.document)
        history.update('W1', {'geometry': {'origin': [1, 2, 0]}})
        after = canonical_checksum(history.document)
        self.assertNotEqual(before, after)
        self.assertEqual(history.document['entities'][1], self.source['entities'][1])
        history.undo()
        self.assertEqual(canonical_checksum(history.document), before)
        history.redo()
        self.assertEqual(canonical_checksum(history.document), after)

    def test_failure_does_not_mutate_history(self):
        history = BIMHistory(self.source)
        before = copy.deepcopy(history.document)
        with self.assertRaises(ValueError):
            history.update('W1', {'host_id': 'D1'})
        self.assertEqual(history.document, before)
        self.assertFalse(history.undo_stack)

    def test_new_valid_command_clears_redo(self):
        history = BIMHistory(self.source)
        history.update('W1', {'geometry': {'origin': [1, 2, 0]}})
        history.undo()
        history.update('W1', {'geometry': {'origin': [4, 5, 0]}})
        self.assertFalse(history.redo_stack)
        with self.assertRaises(ValueError):
            history.redo()

    def test_no_op_does_not_create_history(self):
        history = BIMHistory(self.source)
        result = history.update('W1', {'level_id': 'L1'})
        self.assertEqual(result['operation'], 'no_change')
        self.assertFalse(history.undo_stack)
