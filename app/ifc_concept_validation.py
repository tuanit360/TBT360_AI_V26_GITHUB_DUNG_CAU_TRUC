"""IFC4 concept acceptance checks; never label concepts engineered."""
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


CATEGORIES = {
    'ARCH': ('IfcWall', 'IfcSlab', 'IfcRoof'),
    'STR': ('IfcFooting', 'IfcColumn', 'IfcBeam'),
    'ELEC': ('IfcElectricDistributionBoard', 'IfcLightFixture', 'IfcCableSegment'),
    'PLUMB': ('IfcPipeSegment', 'IfcSanitaryTerminal'),
}


def validate_concept_file(path, expected):
    import ifcopenshell
    document = ifcopenshell.open(str(path))
    if document.schema != 'IFC4':
        raise ValueError('Expected IFC4 schema')
    products = document.by_type('IfcProduct')
    if len(products) < 20:
        raise ValueError('Insufficient IFC concept products')
    if len(document.by_type('IfcBuildingStorey')) != 1:
        raise ValueError('Expected one concept building storey')
    if len(document.by_type('IfcProject')) != 1:
        raise ValueError('Expected one IFC project')
    for category, types in CATEGORIES.items():
        count = sum(len(document.by_type(name)) for name in types)
        if count != expected[category] or count == 0:
            raise ValueError('Missing or duplicated ' + category + ' elements')
    guids = [item.GlobalId for item in products]
    if len(set(guids)) != len(guids):
        raise ValueError('Duplicate IFC GlobalId')
    for product in products:
        if product.Representation is None:
            raise ValueError('Missing geometry for ' + product.is_a())
        if not product.Representation.Representations:
            raise ValueError('Missing shape representation')
        if not product.ObjectPlacement:
            raise ValueError('Missing object placement')
    return {'product_count': len(products), 'schema': document.schema}


def write_verified_archive(folder, archive_path, entries):
    folder = Path(folder)
    expected = {'reference.png', 'manifest.json'} | {
        item['option'] + '.ifc' for item in entries
    }
    if not all((folder / filename).is_file() for filename in expected):
        raise ValueError('Incomplete IFC delivery')
    import os
    partial = Path(str(archive_path) + '.part')
    try:
        with ZipFile(partial, 'w', ZIP_DEFLATED) as archive:
            for filename in sorted(expected):
                archive.write(folder / filename, arcname=filename)
        with ZipFile(partial) as check:
            if check.testzip() is not None or set(check.namelist()) != expected:
                raise ValueError('IFC delivery ZIP corrupt')
            for filename in expected:
                digest = hashlib.sha256((folder / filename).read_bytes()).digest()
                if hashlib.sha256(check.read(filename)).digest() != digest:
                    raise ValueError('IFC ZIP member mismatch')
        os.replace(partial, archive_path)
    finally:
        partial.unlink(missing_ok=True)
    return str(archive_path)
