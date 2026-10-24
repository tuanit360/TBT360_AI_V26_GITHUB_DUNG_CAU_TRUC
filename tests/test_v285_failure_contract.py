import unittest
from pathlib import Path
from app.worker_failure_smoke import run_failure_contract


class FrozenWorkerFailureContract(unittest.TestCase):
    def test_actual_subprocess_failure_has_json_reason(self):
        report = run_failure_contract(Path(__file__).resolve().parents[1])
        self.assertEqual(report['status'], 'PASS_FAILURE_CONTRACT_ONLY')
        self.assertFalse(report['real_ai_inference_verified'])
        self.assertNotEqual(report['worker_exit'], 0)


if __name__ == '__main__':
    unittest.main()
