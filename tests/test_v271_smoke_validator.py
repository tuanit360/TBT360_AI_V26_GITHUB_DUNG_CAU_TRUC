"""Negative tests for the Windows frozen BIM delivery smoke validator."""
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
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return output.getvalue()


class RealEXESmokeValidatorTests(unittest.TestCase):
    def setUp(self):
        self.report = {
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

    def test_missing_glb_geometry_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'GLB'):
            verify_delivery(self.report, make_archive({'schematic_walls.glb': b'no'}))

    def test_missing_dxf_end_marker_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'DXF'):
            verify_delivery(self.report, make_archive({'schematic_plan.dxf': b'incomplete'}))

    def test_empty_audit_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'audit'):
            verify_delivery(self.report, make_archive({'KIEM_TRA_MO_LAI.json': b'{}'}))

    def test_unverified_ifc_is_rejected(self):
        report = dict(self.report, ifc_export_ready=True)
        with self.assertRaisesRegex(AssertionError, 'IFC'):
            verify_delivery(report, make_archive())

    def test_only_local_file_endpoint_is_accepted(self):
        self.assertEqual(
            checked_download_url('/gradio_api/file=/tmp/report.zip'),
            'http://127.0.0.1:7861/gradio_api/file=/tmp/report.zip',
        )
        for unsafe in (
            'https://evil.example/file', '//evil.example/file',
            '/redirect?to=/gradio_api/file=foo', '/other/endpoint',
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(AssertionError):
                checked_download_url(unsafe)


if __name__ == '__main__':
    unittest.main()
