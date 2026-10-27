import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import tape_profiles
import localization
import engine


class ProfileTests(unittest.TestCase):
    def tearDown(self):
        localization.set_language('ru')

    def test_filename_alone_does_not_enable_stop_bypass(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'WEC Le Mans.tzx'
            path.write_bytes(b'not the verified dump')
            self.assertIsNone(tape_profiles.identify(path))

    def test_supported_branch_and_start_only(self):
        profile = 'wec-le-mans-128'
        self.assertIn('in-flags=4', tape_profiles.options(profile, '128', ''))
        self.assertEqual(tape_profiles.options(profile, '128', ''), tape_profiles.options(profile, '128', '0x8101'))
        with self.assertRaisesRegex(ValueError, 'не поддерживается'):
            tape_profiles.options(profile, '48', '')
        with self.assertRaisesRegex(ValueError, '33025'):
            tape_profiles.options(profile, '128', '32768')

    def test_resident_data_must_match_all_three_blocks(self):
        blocks = [SimpleNamespace(data=[]) for _ in range(39)]
        blocks[34].data = [0] + [12] * 38020 + [0]
        blocks[32].data = [0] * 29 + [34] * 8192
        blocks[33].data = [0] * 29 + [56] * 4096
        memory = [0] * 49152
        memory[0x6164-16384:0x6164-16384+38020] = [12] * 38020
        banks = [0] * 131072
        banks[6*16384:6*16384+8192] = [34] * 8192
        banks[4*16384:4*16384+4096] = [56] * 4096
        snapshot = SimpleNamespace(machine='128K', pc=33025, out7ffd=16,
                                   ram=lambda bank=None: banks if bank == -1 else memory)
        with patch('skoolkit.tape.parse_tzx', return_value=SimpleNamespace(blocks=blocks)):
            self.assertEqual(tape_profiles.validate('wec-le-mans-128', Path('input.tzx'), snapshot)['resident_bytes_verified'], 50308)
            for area, offset in ((memory, 0x6164-16384), (banks, 6*16384+8000), (banks, 4*16384+4000)):
                area[offset] ^= 1
                with self.assertRaisesRegex(ValueError, 'не пройдена'):
                    tape_profiles.validate('wec-le-mans-128', Path('input.tzx'), snapshot)
                area[offset] ^= 1

    def test_english_messages_preserve_user_data(self):
        localization.set_language('en')
        self.assertEqual(localization.tr('Проверка загрузки в {0}К: {1}', 128, 'Русское название.tzx'),
                         'Checking loading in 128K: Русское название.tzx')
        with self.assertRaisesRegex(ValueError, 'not supported'):
            tape_profiles.options('wec-le-mans-128', '48', '')
        with self.assertRaisesRegex(ValueError, 'Add at least one'):
            engine.build({'games': []})
        localization.set_language('ru')
        with self.assertRaisesRegex(ValueError, 'Добавьте'):
            engine.build({'games': []})


if __name__ == '__main__':
    unittest.main()
