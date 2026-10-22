"""Negative tests for the Windows frozen BIM delivery smoke validator."""
import hashlib
import io
import json
import unittest
import zipfile

from tools.smoke_bim_ui import checked_download_url, verify_delivery


def make_archive(overrides=None):
    model = {'levels': [{}, {}, {}], 'entities': [{'id': 'A'}]}
    contents = {
        'canonical_bim_handoff.json': json.dumps(model).encode(),
        'schematic_walls.glb': b'glTF' + bytes(32),
        'schematic_plan.dxf': b'0\nSECTION\n0\nENDSEC\n0\nEOF\n',
        'plan.svg': b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        'front_elevation.svg': b'<svg></svg>',
        'KIEM_TRA_HINH_HOC.json': b'{"ok": true}',
        'KIEM_TRA_MO_LAI.json': b'{"ok": true}',
    }
    if overrides:
        contents.update(overrides)
    hashes = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in contents.items()
        if name not in ('KIEM_TRA_MO_LAI.json', 'KIEM_TRA_HINH_HOC.json')
    }
    contents['KIEM_TRA_MO_LAI.json'] = json.dumps({
        'sha256_tung_tep': hashes,
        'so_mat_tam_giac_glb': 10,
    }).encode()
    if overrides and 'KIEM_TRA_MO_LAI.json' in overrides:
        contents['KIEM_TRA_MO_LAI.json'] = overrides['KIEM_TRA_MO_LAI.json']
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return output.getvalue()


class RealEXESmokeValidatorTests(unittest.TestCase):
    def setUp(self):
        model = {'levels': [{}, {}, {}], 'entities': [{'id': 'A'}]}
        checksum = hashlib.sha256(json.dumps(
            model, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False,
        ).encode()).hexdigest()
        self.report = {
            'model_checksum': checksum,
            'kiem_tra_mo_lai': json.loads(zipfile.ZipFile(
                io.BytesIO(make_archive())
            ).read('KIEM_TRA_MO_LAI.json')),
            'levels': 3,
            'entity_count': 1,
            'source': 'explicit_user_constraints',
            'ifc_export_ready': False,
        }

    def test_valid_delivery(self):
        verify_delivery(self.report, make_archive())

    def test_wrong_entity_count_is_rejected(self):
        report = dict(self.report, entity_count=9)
        with self.assertRaisesRegex(AssertionError, 'entity count'):
            verify_delivery(report, make_archive())

    def test_wrong_model_checksum_is_rejected(self):
        report = dict(self.report, model_checksum='invalid')
        with self.assertRaisesRegex(AssertionError, 'checksum'):
            verify_delivery(report, make_archive())

    def test_missing_glb_geometry_is_rejected(self):
        archive = make_archive({'schematic_walls.glb': b'no'})
        report = dict(self.report, kiem_tra_mo_lai=json.loads(
            zipfile.ZipFile(io.BytesIO(archive)).read('KIEM_TRA_MO_LAI.json')
        ))
        with self.assertRaisesRegex(AssertionError, 'GLB'):
            verify_delivery(report, archive)

    def test_missing_dxf_end_marker_is_rejected(self):
        archive = make_archive({'schematic_plan.dxf': b'incomplete'})
        report = dict(self.report, kiem_tra_mo_lai=json.loads(
            zipfile.ZipFile(io.BytesIO(archive)).read('KIEM_TRA_MO_LAI.json')
        ))
        with self.assertRaisesRegex(AssertionError, 'DXF'):
            verify_delivery(report, archive)

    def test_tampered_reopen_hash_is_rejected(self):
        old_audit = json.dumps(self.report['kiem_tra_mo_lai']).encode()
        altered = make_archive({
            'schematic_plan.dxf': b'0\\nEOF\\n',
            'KIEM_TRA_MO_LAI.json': old_audit,
        })
        with self.assertRaisesRegex(AssertionError, 'checksum mismatch'):
            verify_delivery(self.report, altered)

    def test_empty_audit_is_rejected(self):
        report = dict(self.report, kiem_tra_mo_lai={})
        with self.assertRaisesRegex(AssertionError, 'audit'):
            verify_delivery(report, make_archive({'KIEM_TRA_MO_LAI.json': b'{}'}))

    def test_unverified_ifc_is_rejected(self):
        report = dict(self.report, ifc_export_ready=True)
        with self.assertRaisesRegex(AssertionError, 'IFC'):
            verify_delivery(report, make_archive())

    def test_only_local_file_endpoint_is_accepted(self):
        self.assertEqual(
            checked_download_url('/gradio_api/file=/tmp/report.zip'),
            'http://127.0.0.1:7861/gradio_api/file=/tmp/report.zip',
        )
        self.assertEqual(
            checked_download_url('/file=/tmp/report.zip'),
            'http://127.0.0.1:7861/file=/tmp/report.zip',
        )
        for valid in ('/gradio_api/file/abc.zip', '/file/abc.zip'):
            self.assertEqual(checked_download_url(valid), 'http://127.0.0.1:7861' + valid)
        for unsafe in (
            'https://evil.example/file', '//evil.example/file',
            '/../private/file.zip', '/file/../../private/file.zip',
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(AssertionError):
                checked_download_url(unsafe)


if __name__ == '__main__':
    unittest.main()
