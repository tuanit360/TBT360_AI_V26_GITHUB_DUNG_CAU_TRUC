"""V102–V106 safe history for one canonical BIM document.

Each command is validated against the shared canonical contract. A failed
operation does not modify the current document or the undo/redo stacks.
"""
from copy import deepcopy
from app.bim_transaction import apply_entity_update, canonical_checksum, validate_document


class BIMHistory:
    def __init__(self, document, max_entries=100):
        validate_document(document)
        if not 1 <= int(max_entries) <= 1000:
            raise ValueError('History size out of range')
        self.document = deepcopy(document)
        self.max_entries = int(max_entries)
        self.undo_stack = []
        self.redo_stack = []

    def update(self, entity_id, changes):
        before = deepcopy(self.document)
        after, audit = apply_entity_update(before, entity_id, changes)
        if audit['before_sha256'] == audit['after_sha256']:
            return {'operation': 'no_change', 'sha256': audit['before_sha256']}
        self.undo_stack.append(before)
        self.undo_stack = self.undo_stack[-self.max_entries:]
        self.redo_stack.clear()
        self.document = after
        return audit

    def undo(self):
        if not self.undo_stack:
            raise ValueError('No operation to undo')
        candidate = self.undo_stack[-1]
        validate_document(candidate)
        self.redo_stack.append(deepcopy(self.document))
        self.document = self.undo_stack.pop()
        return {'operation': 'undo', 'sha256': canonical_checksum(self.document)}

    def redo(self):
        if not self.redo_stack:
            raise ValueError('No operation to redo')
        candidate = self.redo_stack[-1]
        validate_document(candidate)
        self.undo_stack.append(deepcopy(self.document))
        self.undo_stack = self.undo_stack[-self.max_entries:]
        self.document = self.redo_stack.pop()
        return {'operation': 'redo', 'sha256': canonical_checksum(self.document)}
