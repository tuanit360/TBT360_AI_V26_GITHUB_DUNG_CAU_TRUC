"""Validate one common-building handoff across five IFC files."""
import hashlib
from pathlib import Path


def validate_handoff_manifest(folder, data):
    folder = Path(folder)
    options = data.get('options')
    if (data.get('schema') != 'bimai360.five_ifc_concept.v2'
            or data.get('alternatives_not_independent_houses') is not True
            or data.get('image_exported') is not False
            or data.get('engineering_verified') is not False
            or not isinstance(options, list) or len(options) != 5):
        raise ValueError('Invalid concept IFC handoff metadata')
    if [v.get('option') for v in options] != [
            'PA01', 'PA02', 'PA03', 'PA04', 'PA05']:
        raise ValueError('Five distinct numbered alternatives required')
    envelopes = {(v.get('width_m'), v.get('length_m'), v.get('height_m'))
                 for v in options}
    if len(envelopes) != 1:
        raise ValueError('Alternatives do not share one building envelope')
    variations = set()
    for option in options:
        if option.get('shared_building_reference') != data['common_building_id']:
            raise ValueError('Variant lost building identity')
        variation = option.get('variation')
        if not isinstance(variation, dict):
            raise ValueError('Variant design delta missing')
        variations.add(tuple(sorted(variation.items())))
        path = folder / (option['option'] + '.ifc')
        if not path.is_file():
            raise ValueError('Variant IFC missing')
        if hashlib.sha256(path.read_bytes()).hexdigest() != option.get('ifc_sha256'):
            raise ValueError('Variant IFC checksum mismatch')
        if option.get('engineering_verified') is not False:
            raise ValueError('False engineering certification')
    if len(variations) != 5:
        raise ValueError('Variants are identical')
    return True
