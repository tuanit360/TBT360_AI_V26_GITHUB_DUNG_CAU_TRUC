"""Five IFC4 design alternatives of ONE conceptual building from one photo.

Photo provides aesthetic context, NOT dimensions, hidden floor layouts or
engineering facts. All geometry and MEP routing are openly assumed.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import secrets
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image


# Same origin, envelope and building identity for every alternative.
# Differences are internal layout and schematic equipment positioning.
BASE_WIDTH_M = 9.0
BASE_LENGTH_M = 12.0
BASE_HEIGHT_M = 3.3
SCHEMES = (
    ('PA01', BASE_WIDTH_M, BASE_LENGTH_M, BASE_HEIGHT_M, 'Original zoning concept'),
    ('PA02', BASE_WIDTH_M, BASE_LENGTH_M, BASE_HEIGHT_M, 'Open living room option'),
    ('PA03', BASE_WIDTH_M, BASE_LENGTH_M, BASE_HEIGHT_M, 'Flexible bedroom option'),
    ('PA04', BASE_WIDTH_M, BASE_LENGTH_M, BASE_HEIGHT_M, 'Service core option'),
    ('PA05', BASE_WIDTH_M, BASE_LENGTH_M, BASE_HEIGHT_M, 'Accessible circulation option'),
)
SCHEME_LAYOUTS = {
    'PA01': (0.55, 0.55, 0.62),
    'PA02': (0.68, 0.42, 0.70),
    'PA03': (0.48, 0.72, 0.55),
    'PA04': (0.62, 0.60, 0.78),
    'PA05': (0.52, 0.45, 0.60),
}


def _build_ifc(path, identifier, width, length, height, title):
    try:
        import ifcopenshell
    except ImportError as exc:
        raise RuntimeError(
            'Phiên bản Portable này thiếu thành phần xuất IFC. '
            'Hãy dùng bản Windows mới có kiểm thử IFC; không cần cài thêm.'
        ) from exc

    f = ifcopenshell.file(schema='IFC4')
    guid = ifcopenshell.guid.new
    origin = f.createIfcCartesianPoint((0.0, 0.0, 0.0))
    zaxis = f.createIfcDirection((0.0, 0.0, 1.0))
    xaxis = f.createIfcDirection((1.0, 0.0, 0.0))
    world = f.createIfcAxis2Placement3D(origin, zaxis, xaxis)
    context = f.createIfcGeometricRepresentationContext(
        ContextIdentifier='Body', ContextType='Model',
        CoordinateSpaceDimension=3, Precision=1e-5,
        WorldCoordinateSystem=world,
    )
    meters = f.createIfcSIUnit(UnitType='LENGTHUNIT', Name='METRE')
    area = f.createIfcSIUnit(UnitType='AREAUNIT', Name='SQUARE_METRE')
    volume = f.createIfcSIUnit(UnitType='VOLUMEUNIT', Name='CUBIC_METRE')
    units = f.createIfcUnitAssignment([meters, area, volume])
    project = f.createIfcProject(
        GlobalId=guid(), Name=identifier + ' ' + title,
        RepresentationContexts=[context], UnitsInContext=units,
        Description='Concept only; assumptions not inferred from one photograph',
    )
    site = f.createIfcSite(GlobalId=guid(), Name='Concept site')
    building = f.createIfcBuilding(GlobalId=guid(), Name='Concept building')
    storey = f.createIfcBuildingStorey(
        GlobalId=guid(), Name='Ground floor', Elevation=0.0,
    )
    for parent, child in ((project, site), (site, building), (building, storey)):
        f.createIfcRelAggregates(
            GlobalId=guid(), RelatingObject=parent, RelatedObjects=[child],
        )

    def point(values):
        return f.createIfcCartesianPoint(tuple(float(v) for v in values))

    def loc(x, y, z):
        axis = f.createIfcAxis2Placement3D(
            point((x, y, z)), zaxis, xaxis,
        )
        return f.createIfcLocalPlacement(None, axis)

    by_discipline = {'ARCH': [], 'STR': [], 'ELEC': [], 'PLUMB': []}

    def box(ifc_type, name, discipline, xyz, size):
        x, y, z = (float(v) for v in xyz)
        sx, sy, sz = (float(v) for v in size)
        if min(sx, sy, sz) <= 0:
            raise ValueError('Concept BIM dimensions must be positive')
        profile = f.createIfcRectangleProfileDef(
            ProfileType='AREA', XDim=sx, YDim=sy,
        )
        solid = f.createIfcExtrudedAreaSolid(
            SweptArea=profile,
            Position=f.createIfcAxis2Placement3D(
                point((0, 0, 0)), zaxis, xaxis,
            ),
            ExtrudedDirection=zaxis, Depth=sz,
        )
        shape = f.createIfcShapeRepresentation(
            context, 'Body', 'SweptSolid', [solid],
        )
        representation = f.createIfcProductDefinitionShape(
            None, None, [shape],
        )
        entity = f.create_entity(
            ifc_type, GlobalId=guid(), Name=name,
            Description='UNVERIFIED CONCEPT; assumed geometry and routing',
            ObjectPlacement=loc(x, y, z),
            Representation=representation,
        )
        by_discipline[discipline].append(entity)
        return entity

    # Architectural envelope: indicative only (no surveyed openings).
    partition_x, partition_length, services_y = SCHEME_LAYOUTS[identifier]
    t = 0.20
    box('IfcSlab', 'Architectural floor', 'ARCH',
        (0, 0, 0.05), (width, length, 0.16))
    for name, xyz, size in (
        ('West perimeter wall', (0, 0, 0.21), (t, length, height)),
        ('East perimeter wall', (width-t, 0, 0.21), (t, length, height)),
        ('North perimeter wall', (0, length-t, 0.21), (width, t, height)),
        ('South perimeter wall', (0, 0, 0.21), (width, t, height)),
        ('Concept partition', (width*partition_x, 0.2, 0.21),
         (0.12, length*partition_length, height)),
    ):
        box('IfcWall', name, 'ARCH', xyz, size)
    # A gabled form is approximated by two thin roof volumes; pitch is
    # documented as conceptual rather than a verified geometric hip/gable.
    box('IfcRoof', 'Roof concept shell (not surveyed pitch)', 'ARCH',
        (-0.35, -0.35, height + 0.21),
        (width + 0.7, length + 0.7, 0.18))

    # Structural members: positions indicative; NOT engineered/sized.
    for i, x in enumerate((0.35, width-0.6)):
        for j, y in enumerate((0.35, length-0.6)):
            box('IfcFooting', f'Footing {i}{j}', 'STR',
                (x-0.22, y-0.22, -0.60), (0.75, 0.75, 0.45))
            box('IfcColumn', f'Column {i}{j}', 'STR',
                (x, y, 0.21), (0.25, 0.25, height))
    box('IfcBeam', 'Front structural beam', 'STR',
        (0.3, 0.35, height-0.1), (width-0.6, 0.25, 0.3))
    box('IfcBeam', 'Rear structural beam', 'STR',
        (0.3, length-0.6, height-0.1), (width-0.6, 0.25, 0.3))

    # Electric devices/cable routing: preliminary schematic locations.
    box('IfcElectricDistributionBoard', 'Concept electrical panel', 'ELEC',
        (0.25, 0.35, 1.2), (0.45, 0.16, 0.7))
    for i, (x, y) in enumerate(((width*.25, length*.25),
                                 (width*.75, length*.25),
                                 (width*.25, length*.75),
                                 (width*.75, length*.75)), start=1):
        box('IfcLightFixture', f'Ceiling light {i}', 'ELEC',
            (x, y, height-0.15), (0.25, 0.25, 0.08))
    box('IfcCableSegment', 'Illustrative cable tray', 'ELEC',
        (0.6, 0.7, height-0.32), (width-1.2, 0.04, 0.04))

    # Water and sanitary equipment: schematic paths, not hydraulic design.
    box('IfcPipeSegment', 'Cold water run', 'PLUMB',
        (0.5, length*services_y, 0.3), (width*.55, 0.05, 0.05))
    box('IfcPipeSegment', 'Wastewater run', 'PLUMB',
        (0.5, length*(services_y+0.01), -0.15), (width*.55, 0.11, 0.11))
    box('IfcSanitaryTerminal', 'Concept wash basin', 'PLUMB',
        (width*.64, length*(services_y+0.03), 0.4), (0.55, 0.45, 0.22))

    for discipline, entities in by_discipline.items():
        if entities:
            f.createIfcRelContainedInSpatialStructure(
                GlobalId=guid(),
                Name=discipline + ' concept elements',
                RelatingStructure=storey,
                RelatedElements=entities,
            )
    f.write(str(path))
    return {key: len(values) for key, values in by_discipline.items()}


def export_five_concepts(image, root):
    if not isinstance(image, Image.Image):
        raise ValueError('Hãy tải ảnh công trình tham chiếu trước.')
    if image.width < 32 or image.height < 32:
        raise ValueError('Ảnh tham chiếu quá nhỏ.')
    root = Path(root).resolve()
    destination = root / 'output' / ('ifc_concept_' + secrets.token_hex(8))
    destination.mkdir(parents=True, exist_ok=False)
    # Bind the alternatives to a source without exporting the private photo.
    normalized = image.convert('RGB')
    digest = hashlib.sha256(normalized.tobytes()).hexdigest()
    entries = []
    for identifier, width, length, height, title in SCHEMES:
        filename = identifier + '.ifc'
        counts = _build_ifc(
            destination / filename,
            identifier, width, length, height, title,
        )
        entries.append({
            'option': identifier, 'width_m': width, 'length_m': length,
            'height_m': height, 'title': title, 'disciplines': counts,
            'verification': 'concept_geometry_only',
            'shared_building_reference': 'ONE_BUILDING_FROM_REFERENCE',
            'variation': {
                'partition_x_fraction': SCHEME_LAYOUTS[identifier][0],
                'partition_length_fraction': SCHEME_LAYOUTS[identifier][1],
                'services_y_fraction': SCHEME_LAYOUTS[identifier][2],
            },
            'engineering_verified': False,
            'reference_sha256': digest,
        })
    # Validate the actual IFC files before publishing one canonical manifest.
    from app.ifc_concept_validation import validate_concept_file
    for entry in entries:
        target = destination / (entry['option'] + '.ifc')
        result = validate_concept_file(target, entry['disciplines'])
        entry['verification'] = 'ifc4_reopen_and_geometry_representation'
        entry['ifc_entities_verified'] = result['product_count']
        entry['ifc_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()

    manifest = destination / 'manifest.json'
    payload = {
        'schema': 'bimai360.five_ifc_concept.v2',
        'image_usage': 'visual_reference_only_no_dimensions_inferred',
        'common_building_id': 'ONE_BUILDING_FROM_REFERENCE',
        'alternatives_not_independent_houses': True,
        'image_exported': False,
        'source_dimensions': 'NOT_INFERRED_FROM_IMAGE',
        'ifc_schema': 'IFC4',
        'engineering_verified': False,
        'discipline_status': 'schematic_assumed_not_engineered',
        'options': entries,
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8',
    )
    from app.ifc_handoff_manifest import validate_handoff_manifest
    validate_handoff_manifest(destination, payload)
    archive = destination.with_suffix('.zip')
    from app.ifc_concept_validation import write_verified_archive
    write_verified_archive(destination, archive, entries)
    return str(archive), (
        'Đã tạo 5 phương án IFC4 cho CÙNG MỘT công trình: Kiến trúc, Kết cấu, Điện, Cấp/thoát nước. '
        'Kích thước và các tuyến MEP là giả định; chưa thẩm tra kỹ thuật.'
    )
