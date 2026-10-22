"""UI build smoke: tabs must build and register without executing AI.

Unlike text-only syntax checks, this constructs the actual Gradio Blocks
configuration and verifies each workspace tab has a real component.
"""
import importlib
import unittest


class V231RealTabSmokeTests(unittest.TestCase):
    def test_gradio_builds_all_primary_tabs(self):
        app = importlib.import_module('app.generate')
        config = app.ui.get_config_file()
        components = config.get('components', [])
        if not isinstance(components, list):
            self.fail('Gradio did not return actual UI component metadata')
        tab_labels = {
            str(component.get('props', {}).get('label', ''))
            for component in components
            if component.get('type') == 'tabitem'
        }
        expected = (
            '01 · TẠO PHƯƠNG ÁN', '02 · KIỂM TRA',
            '03 · BÀN GIAO', '04 · DỮ LIỆU',
            '05 · ĐÀO TẠO', '06 · TÀI KHOẢN',
            'Thiết kế và sinh ảnh', 'Mô hình 2D / 3D',
            'Nhận dạng AI', 'Trung tâm xuất file'
        )
        for label in expected:
            self.assertIn(label, tab_labels)
        self.assertTrue(config.get('dependencies'),
                        'No active events were registered for UI controls')
