import json
import tempfile
import unittest
from pathlib import Path

from app.local_workspace import (
    save_local_profile, record_operation, read_runtime_log,
)


class V221WorkspaceNavigationTests(unittest.TestCase):
    def test_gradio_source_compiles_and_has_expected_workflow(self):
        source = (Path(__file__).resolve().parents[1] / 'app' / 'generate.py').read_text(encoding='utf-8')
        compile(source, 'app/generate.py', 'exec')
        for label in ('TẠO PHƯƠNG ÁN', 'KIỂM TRA', 'BÀN GIAO',
                      'DỮ LIỆU', 'ĐÀO TẠO', 'TÀI KHOẢN'):
            self.assertIn(label, source)
        self.assertIn('Trung tâm xuất file', source)
        self.assertIn('Nhật ký hoạt động', source)

    def test_local_workspace_is_not_fake_server_login(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = save_local_profile(folder, 'Kiến trúc 360')
            self.assertFalse(profile['server_authenticated'])
            self.assertFalse(profile['credentials_stored'])
            self.assertNotIn('password', json.dumps(profile).lower())
            self.assertFalse((Path(folder) / 'credentials.json').exists())
            record_operation(folder, 'export_file', 'completed')
            log = read_runtime_log(folder)
            self.assertIn('workspace_open', log)
            self.assertIn('export_file', log)

    def test_log_handle_released_before_windows_temp_cleanup(self):
        import shutil
        from app.local_workspace import setup_runtime_log
        folder = Path(tempfile.mkdtemp(prefix='bimai360_log_test_'))
        try:
            setup_runtime_log(folder)
            for _ in range(8):
                record_operation(folder, 'generate', 'completed')
            self.assertEqual(
                read_runtime_log(folder).count('generate | completed'), 8)
        finally:
            # Windows raises PermissionError / WinError 32 here if a
            # process-global FileHandler is still keeping the file open.
            shutil.rmtree(folder)

    def test_invalid_local_account_name_and_unknown_action_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_local_profile(folder, '../secret')
            with self.assertRaises(ValueError):
                record_operation(folder, 'login_password', 'completed')
