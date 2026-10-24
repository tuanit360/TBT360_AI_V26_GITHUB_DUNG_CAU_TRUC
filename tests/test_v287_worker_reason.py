import tempfile
import unittest
from pathlib import Path
from app.generation_failures import explain_generation_failure
from app.image_generation_contract import image_generation_contract


class V287WorkerReasonTests(unittest.TestCase):
    def test_worker_reason_not_replaced_by_called_process_error(self):
        def fake_generator(*args, progress=None):
            try:
                raise RuntimeError('CalledProcessError mock')
            except RuntimeError as child:
                raise RuntimeError(
                    'AI worker thất bại (mã 1). Checkpoint SD1.5 thiếu hoặc không hợp lệ.'
                ) from child
        with tempfile.TemporaryDirectory() as directory:
            result = image_generation_contract(
                Path(directory), fake_generator, (), offline=False
            )
        self.assertIn('checkpoint SD1.5', result[2])
        self.assertIsNone(result[1])

    def test_unknown_worker_text_not_leaked(self):
        error = RuntimeError(
            'AI worker thất bại (mã 1). SECRET_ACCESS_TOKEN=private'
        )
        reason = explain_generation_failure(error)
        self.assertNotIn('private', reason)
        self.assertIn('image_worker.log', reason)


if __name__ == '__main__':
    unittest.main()
