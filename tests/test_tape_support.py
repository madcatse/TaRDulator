import contextlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import engine
import tape_support

HEADER = b'ZXTape!\x1a\x01\x14'
DATA = b'\x10' + struct.pack('<HH', 1000, 2) + b'\xff\xff'


class TzxTests(unittest.TestCase):
    def test_valid_and_truncated_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'example.TZX'
            path.write_bytes(HEADER + DATA)
            self.assertEqual(engine.inspect_tap(path)['format'], 'TZX')
            for length in range(len(HEADER + DATA)):
                with self.subTest(length=length):
                    with self.assertRaises(ValueError):
                        tape_support.tzx_blocks((HEADER + DATA)[:length])

    def test_stops_do_not_claim_complete_tape(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'example.tzx'
            for stop, expected in ((b'\x20\0\0', {'48': [3], '128': [3]}),
                                   (b'\x2a\0\0\0\0', {'48': [3], '128': []})):
                path.write_bytes(HEADER + DATA + stop + DATA)
                for machine, remaining in expected.items():
                    self.assertEqual(tape_support.remaining_after_stop(path, machine), remaining)
                    if remaining:
                        with self.assertRaisesRegex(ValueError, 'Полный перенос'):
                            engine.prepare_snapshot(path, Path(d) / 'no.z80', machine)
                        self.assertFalse((Path(d) / 'no.z80').exists())
            path.write_bytes(HEADER + DATA + b'\x20\0\0')
            self.assertEqual(tape_support.remaining_after_stop(path, '128'), [])

    def test_unsupported_controls_and_runaway_loops(self):
        for suffix in (b'\x23\x01\0', b'\x25', b'\x24\x02\0',
                       b'\x24\x02\0\x24\x02\0\x25\x25',
                       b'\x24\xff\xff' + DATA + b'\x25'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                tape_support.tzx_blocks(HEADER + DATA + suffix)


class ModelTests(unittest.TestCase):
    def selection(self, results, requested='auto'):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'G00.z80'
            def load(path, candidate, machine, start):
                calls.append(machine)
                result = results[machine]
                if isinstance(result, Exception):
                    raise result
                candidate.write_bytes(machine.encode())
                return {'machine': machine+'K', 'extra_banks_changed': result, 'bank_observation': machine == '128'}
            with patch.object(engine, 'prepare_snapshot', side_effect=load), contextlib.redirect_stdout(io.StringIO()):
                info = engine.select_snapshot(Path('test.tap'), out, requested)
            self.assertEqual(out.read_bytes(), info['load_machine'].encode())
            return calls, info

    def test_extra_bank_retains_128(self):
        calls, info = self.selection({'128': [3]})
        self.assertEqual(calls, ['128'])
        self.assertEqual(info['load_machine'], '128')

    def test_48_verified_before_selecting(self):
        calls, info = self.selection({'128': [], '48': []})
        self.assertEqual(calls, ['128', '48'])
        self.assertEqual(info['load_machine'], '48')

    def test_fallback_both_directions_and_manual_override(self):
        calls, info = self.selection({'128': ValueError('timeout'), '48': []})
        self.assertEqual(info['load_machine'], '48')
        calls, info = self.selection({'128': [], '48': ValueError('timeout')})
        self.assertEqual(info['load_machine'], '128')
        calls, info = self.selection({'48': []}, '48')
        self.assertEqual(calls, ['48'])
        with self.assertRaisesRegex(ValueError, '128К.*timeout'):
            self.selection({'128': ValueError('timeout'), '48': ValueError('incomplete')})

    def test_real_loader_observes_rom_baseline_not_just_nonzero_banks(self):
        # ROM workspace in bank 7 must not misclassify a tiny 48K program.
        from skoolkit.tape import write_tap
        program = engine.basic_line(10, engine.token('STOP')) if 'STOP' in engine.TOKENS else engine.basic_line(10, bytes([226]))
        header = b'\0\0TEST      ' + struct.pack('<HHH', len(program), 10, len(program))
        def checksum(data):
            value = 0
            for byte in data: value ^= byte
            return data + bytes([value])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'test.tap'
            write_tap(str(path), [checksum(header), checksum(b'\xff' + program)])
            result = engine.prepare_snapshot(path, Path(d) / 'G00.z80', '128')
            self.assertTrue(result['bank_observation'])
            self.assertEqual(result['extra_banks_changed'], [])
            self.assertEqual(result['load_timeout'], 1200)


if __name__ == '__main__':
    unittest.main()
