"""Guard the actual T600 Windows target profile against misreading shared RAM as VRAM."""
import json
import unittest
from pathlib import Path


class UserT600TargetProfileTests(unittest.TestCase):
    def test_dedicated_vram_is_four_gib_not_shared_eleven_point_eight(self):
        root = Path(__file__).resolve().parents[1]
        profile = json.loads(
            (root / 'config' / 'hardware_profiles' /
             'user_windows_t600_4gb.json').read_text(encoding='utf-8')
        )
        self.assertEqual(profile['gpu_for_cuda']['name'], 'NVIDIA T600 Laptop GPU')
        self.assertEqual(profile['gpu_for_cuda']['dedicated_vram_gib'], 4)
        self.assertFalse(profile['gpu_for_cuda']['shared_memory_is_dedicated_vram'])
        self.assertEqual(profile['system_ram_gib'], 16)
        self.assertEqual(profile['cpu']['logical_processors'], 20)
        self.assertEqual(profile['sd15_inference']['memory_strategy'],
                         'model_cpu_offload')
        self.assertEqual(profile['sd15_lora_training']['status'],
                         'not_proven_on_this_machine')


if __name__ == '__main__':
    unittest.main()
