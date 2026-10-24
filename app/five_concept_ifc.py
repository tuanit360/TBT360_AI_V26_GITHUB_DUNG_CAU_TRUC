"""Five independent IFC4 *concept* house schemes from one reference photo.

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


SCHEMES = (
    ('PA01', 9.0, 12.0, 3.3, 'Compact garden home'),
    ('PA02', 10.0, 13.5, 3.4, 'Extended living space'),
    ('PA03', 9.0, 12.5, 3.5, 'Flexible loft concept'),
    ('PA04', 11.5, 11.0, 3.3, 'Wide frontage'),
    ('PA05', 10.0, 14.0, 3.4, 'Garden-oriented wing'),
)


def _build_ifc(path, identifier, width, length, height, title):
    try:
        import ifcopenshell
    except ImportError as exc:
        raise RuntimeError(
            'Cần cài IfcOpenShell để xuất IFC thật. '
            'Cài từ requirements-runtime.txt và build lại Windows.'
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
    t = 0.20
    box('IfcSlab', 'Architectural floor', 'ARCH',
        (0, 0, 0.05), (width, length, 0.16))
    for name, xyz, size in (
        ('West perimeter wall', (0, 0, 0.21), (t, length, height)),
        ('East perimeter wall', (width-t, 0, 0.21), (t, length, height)),
        ('North perimeter wall', (0, length-t, 0.21), (width, t, height)),
        ('South perimeter wall', (0, 0, 0.21), (width, t, height)),
        ('Concept partition', (width*0.55, 0.2, 0.21),
         (0.12, length*0.55, height)),
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
        (0.5, length*.62, 0.3), (width*.55, 0.05, 0.05))
    box('IfcPipeSegment', 'Wastewater run', 'PLUMB',
        (0.5, length*.63, -0.15), (width*.55, 0.11, 0.11))
    box('IfcSanitaryTerminal', 'Concept wash basin', 'PLUMB',
        (width*.64, length*.65, 0.4), (0.55, 0.45, 0.22))

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
    normalized = image.convert('RGB')
    normalized.thumbnail((1600, 1600))
    reference = destination / 'reference.png'
    normalized.save(reference)
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
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
            'engineering_verified': False,
            'reference_sha256': digest,
        })
    manifest = destination / 'manifest.json'
    manifest.write_text(
        json.dumps({
            'schema': 'bimai360.five_ifc_concept.v1',
            'image_usage': 'style_reference_only',
            'source_dimensions': 'NOT_INFERRED_FROM_IMAGE',
            'ifc_schema': 'IFC4',
            'engineering_verified': False,
            'options': entries,
        }, ensure_ascii=False, indent=2), encoding='utf-8',
    )
    archive = destination.with_suffix('.zip')
    with ZipFile(archive, 'w', ZIP_DEFLATED) as bundle:
        for path in sorted(destination.iterdir()):
            if path.is_file():
                bundle.write(path, arcname=path.name)
    # Check IFC parsing with the same IFC SDK used to write the files.
    import ifcopenshell
    for identifier, *_ in SCHEMES:
        target = destination / (identifier + '.ifc')
        inspected = ifcopenshell.open(str(target))
        if inspected.schema != 'IFC4' or len(inspected.by_type('IfcProduct')) < 10:
            raise RuntimeError(identifier + ' failed IFC parser verification')
    with ZipFile(archive) as check:
        if check.testzip() is not None:
            raise RuntimeError('IFC ZIP checksum invalid')
    return str(archive), (
        'Đã tạo 5 IFC4 concept: Kiến trúc, Kết cấu, Điện, Cấp/thoát nước. '
        'Kích thước và các tuyến MEP là giả định; chưa thẩm tra kỹ thuật.'
    )
