import copy
import unittest
from app.canonical_bim_contract import build_handoff
from app.bim_transaction import canonical_checksum, validate_document, apply_entity_update


class BIMAI360TransactionTests(unittest.TestCase):
    def setUp(self):
        self.document = build_handoff(
            'office_101',
            level_ids=[{'id': 'L1', 'elevation': 0.0},
                       {'id': 'L2', 'elevation': 3.2}],
            elements=[
                {'id': 'W1', 'level_id': 'L1', 'category': 'wall'},
                {'id': 'D1', 'level_id': 'L1', 'category': 'door', 'host_id': 'W1'},
            ],
        )

    def test_immutable_entity_change_preserves_others(self):
        original = copy.deepcopy(self.document)
        updated, audit = apply_entity_update(
            self.document, 'W1', {'geometry': {'origin': [1.0, 0.0, 0.0]}})
        self.assertEqual(self.document, original)
        self.assertEqual(updated['entities'][1], original['entities'][1])
        self.assertNotEqual(audit['before_sha256'], audit['after_sha256'])
        self.assertEqual(canonical_checksum(original), audit['before_sha256'])
        self.assertEqual(validate_document(updated)['entities'], updated['entities'])

    def test_invalid_orphan_and_delete_are_rejected(self):
        before = canonical_checksum(self.document)
        for changes in ({'host_id': 'missing'}, {'id': 'W2'},
                        {'geometry': {'origin': [float('nan'), 0, 0]}}):
            with self.assertRaises(ValueError):
                apply_entity_update(self.document, 'D1', changes)
        self.assertEqual(before, canonical_checksum(self.document))

    def test_canonical_hash_ignores_json_key_order(self):
        clone = copy.deepcopy(self.document)
        clone['entities'][0] = dict(reversed(list(clone['entities'][0].items())))
        self.assertEqual(canonical_checksum(clone), canonical_checksum(self.document))
