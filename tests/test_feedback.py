import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import engine
import machine_probe


class FeedbackTests(unittest.TestCase):
    def test_runtime_detection_does_not_advance_snapshot(self):
        from skoolkit.snapshot import Snapshot, write_snapshot
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'probe.z80'
            banks = [[0] * 16384 for _ in range(8)]
            # Switch the shadow screen, then loop. No additional bank data
            # exists at load completion, the counterexample to the old rule.
            banks[2][:10] = [1, 253, 127, 62, 24, 237, 121, 195, 7, 128]
            write_snapshot(str(path), banks, ['pc=32768'], ['7ffd=16', 'iff=0'])
            snapshot = Snapshot.get(str(path)); before = path.read_bytes()
            ram = snapshot.ram(-1)
            self.assertTrue(machine_probe.observe(snapshot)['runtime_paging'])
            self.assertEqual(snapshot.ram(-1), ram)
            self.assertEqual(snapshot.pc, 32768)
            self.assertEqual(path.read_bytes(), before)
            banks[2][:10] = [1, 253, 127, 62, 0, 237, 121, 195, 7, 128]
            write_snapshot(str(path), banks, ['pc=32768'], ['7ffd=16', 'iff=0'])
            self.assertFalse(machine_probe.observe(Snapshot.get(str(path)))['runtime_paging'])

    def test_milky_retains_both_original_compressed_parts(self):
        from skoolkit.tape import parse_tap
        path = ROOT / 'taps/tricky_roms/MILKY2.TAP'
        if not path.exists(): self.skipTest('Local sample not distributed')
        before = path.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            files, info = engine.convert_game({'path': str(path)}, 0, Path(d))
        blocks = parse_tap(str(path)).blocks
        for f, index in zip(files[1:], (3, 5)):
            self.assertEqual(f.data, bytes(blocks[index].data[1:-1]))
            self.assertEqual(f.parameter, 25000)
        self.assertEqual(info['tape_profile'], 'milky2-disk-chain')
        self.assertEqual([f.name for f in files[1:]], ['G00.A', 'G00.B'])
        self.assertEqual(info['part_count'], 2)
        self.assertEqual(info['repeat_from_part'], 2)
        self.assertEqual(path.read_bytes(), before)
        for option in ({'machine': '48'}, {'transfer_mode': '48'}, {'start': '25000'}):
            with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
                engine.convert_game({'path': str(path), **option}, 0, Path(d))

    def test_direct_disk_uses_actual_loader_and_has_no_menu(self):
        def convert(*args):
            return [engine.basic_file('G00', b'PAYLOAD'), engine.DiskFile('G00.M', 'C', 32768, 1, b'x')], {'title': 'Demo'}
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'direct.trd'
            request = {'launch_mode': 'direct', 'games': [{'path': 'demo.tap'}],
                       'output': str(target), 'title': 'РУССКИЙ'}
            with patch.object(engine, 'convert_game', side_effect=convert), contextlib.redirect_stdout(io.StringIO()):
                result = engine.build(request)
                measured = engine.build({**request, 'action': 'measure'})
            files = engine.read_trd(target.read_bytes())
            self.assertEqual([(f.name, f.kind) for f in files], [('boot', 'B'), ('G00.M', 'C')])
            self.assertEqual(files[0].data[:7], b'PAYLOAD')
            self.assertEqual(result['menu_bytes'], 0)
            self.assertEqual(result['page_count'], 0)
            self.assertEqual(measured['disk_sha256'], result['disk_sha256'])
            self.assertEqual(target.read_bytes()[2293:2301], b'TARDULTR')
            with self.assertRaises(ValueError):
                engine.build({**request, 'games': request['games'] * 2})


if __name__ == '__main__': unittest.main()
