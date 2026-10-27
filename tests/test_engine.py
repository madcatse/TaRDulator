import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine


class DiskTests(unittest.TestCase):
    def test_basic_trailer_survives_sector_boundary(self):
        f = engine.basic_file("boot", b"a"*255, 10)
        disk = engine.write_trd([f], "TEST")
        restored = engine.read_trd(disk)[0]
        self.assertEqual(len(disk), 655360)
        self.assertEqual(restored.sectors, 2)
        self.assertEqual(restored.data[255:259], b"\x80\xaa\x0a\x00")
        self.assertEqual(struct.unpack_from("<H", disk, 2277)[0], 2542)

    def test_exact_capacity_and_overflow(self):
        files = [engine.DiskFile(f"F{i}", "C", 32768, 65280, b"a"*65280) for i in range(9)]
        files.append(engine.DiskFile("TAIL", "C", 32768, 63744, b"b"*63744))
        disk = engine.write_trd(files, "FULL")
        self.assertEqual(struct.unpack_from("<H", disk, 2277)[0], 0)
        self.assertEqual(len(engine.read_trd(disk)), 10)
        with self.assertRaisesRegex(ValueError, "помещаются"):
            engine.write_trd(files+[engine.DiskFile("EXTRA", "C", 32768, 1, b"x")], "OVERFLOW")

    def test_duplicate_files_rejected(self):
        f = engine.DiskFile("SAME", "C", 32768, 1, b"x")
        with self.assertRaisesRegex(ValueError, "Повтор"):
            engine.write_trd([f, f], "TEST")

    def test_overlapping_disk_files_rejected(self):
        disk = bytearray(engine.write_trd([engine.DiskFile("A", "C", 1, 1, b"a"), engine.DiskFile("B", "C", 1, 1, b"b")], "TEST"))
        disk[30:32] = disk[14:16]
        with self.assertRaises(ValueError): engine.read_trd(disk)

    def test_menu_lines_and_all_keys(self):
        games = [{"title": f"Game {i}", "loader": f"G{i:02X}"} for i in range(16)]
        f = engine.menu_file('Title "\r\n', games)
        body = f.data[:f.length]
        pos = 0; lines = []
        while pos < len(body):
            number = int.from_bytes(body[pos:pos+2], "big")
            length = int.from_bytes(body[pos+2:pos+4], "little")
            lines.append(number)
            self.assertEqual(body[pos+3+length], 13)
            pos += 4+length
        self.assertEqual(pos, len(body))
        self.assertEqual(lines, sorted(set(lines)))
        self.assertIn(b'"G0F"', body)
        self.assertIn(b'k$="g"', body)
        self.assertEqual(engine.safe_text('"\n'), '??')


class TapeTests(unittest.TestCase):
    def test_supplied_tapes_are_valid_and_unchanged(self):
        paths = list((ROOT / "taps").glob("*.tap"))
        if not paths: self.skipTest("No local sample tapes")
        for path in paths:
            before = path.read_bytes()
            result = engine.inspect_tap(path)
            self.assertGreater(result["blocks"], 0)
            self.assertEqual(hashlib.sha256(before).hexdigest(), result["sha256"])
            self.assertEqual(path.read_bytes(), before)

    def test_corruption_and_truncation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            path = Path(d)/"bad.tap"
            for data in (b"", b"\x00", b"\x01\x00\x00", b"\x03\x00\xff\x01\xff", b"\x40\x00\x00\x00"):
                path.write_bytes(data)
                with self.subTest(data=data):
                    with self.assertRaises(ValueError): engine.inspect_tap(path)

    def test_failure_does_not_replace_existing_disk(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            target = Path(d)/"keep.trd"; target.write_bytes(b"IMPORTANT")
            request = {"games": [{"path": "missing.tap"}], "output": str(target), "overwrite": True}
            with contextlib.redirect_stdout(io.StringIO()), patch.object(engine, "convert_game", side_effect=ValueError("test failure")):
                with self.assertRaises(ValueError): engine.build(request)
            self.assertEqual(target.read_bytes(), b"IMPORTANT")
            self.assertEqual(list(Path(d).iterdir()), [target])

    def test_no_implicit_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            target = Path(d)/"keep.trd"; target.write_bytes(b"KEEP")
            with self.assertRaisesRegex(ValueError, "существует"):
                engine.build({"games": [{"path": "missing.tap"}], "output": str(target)})
            self.assertEqual(target.read_bytes(), b"KEEP")


class PackingTests(unittest.TestCase):
    def test_transfer_modes_and_bank_reduction_with_real_converter(self):
        if not engine.tool_path().is_file():
            self.skipTest("Local Z80to not installed")
        from skoolkit.snapshot import Snapshot, write_snapshot
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            path = Path(d) / "TST.z80"
            banks = [[bank + 1] * 16384 for bank in range(8)]
            banks[2][:4] = [243, 195, 0, 128]
            write_snapshot(str(path), banks, ["pc=32768", "sp=65000"], ["7ffd=16", "iff=0"])
            self.assertEqual(len(Snapshot.get(str(path)).ram(-1)), 131072)
            sizes = {}
            for mode, expected in (("auto", "128"), ("preserve", "128"), ("48", "48")):
                files, info = engine.pack_snapshot(path, mode)
                self.assertEqual(info["result_machine"], expected)
                sizes[mode] = sum(f.sectors * 256 for f in files)
            self.assertLess(sizes["48"], sizes["preserve"])
            write_snapshot(str(path), [0] * 49152, ["pc=32768", "sp=65000"], ["iff=0"])
            for mode in ("auto", "preserve", "48"):
                self.assertEqual(engine.pack_snapshot(path, mode)[1]["result_machine"], "48")
            with self.assertRaises(ValueError):
                engine.pack_snapshot(path, "discard-everything")

    def test_measure_matches_build_and_never_writes_requested_output(self):
        # Sector padding and the BASIC trailer count towards the displayed
        # size. Measurement must use the same complete disk layout as build.
        files = [engine.basic_file("G00", b"a" * 255),
                 engine.DiskFile("G00.M", "C", 32768, 257, b"x" * 257)]
        game = {"title": "TEST", "loader": "G00", "bytes": 1024}
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            target = Path(d) / "keep.trd"
            target.write_bytes(b"KEEP")
            request = {"action": "measure", "games": [{"path": "fixture.tap"}],
                       "output": str(target), "overwrite": True}
            with patch.object(engine, "convert_game", return_value=(files, game)), patch.object(tempfile, "tempdir", d), contextlib.redirect_stdout(io.StringIO()):
                measured = engine.build(request)
                self.assertEqual(target.read_bytes(), b"KEEP")
                self.assertEqual(list(Path(d).iterdir()), [target])
                self.assertNotIn("output", measured)
                request["action"] = "build"
                built = engine.build(request)
            actual = sum(f.sectors * 256 for f in engine.read_trd(target.read_bytes()))
            self.assertEqual(measured["used_bytes"], actual)
            self.assertEqual(measured["used_bytes"], built["used_bytes"])
            self.assertEqual(measured["disk_sha256"], built["disk_sha256"])

    def test_128_snapshot_counts_all_banks(self):
        from skoolkit.snapshot import write_snapshot
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            directory = Path(d)
            source = directory / "source.tap"
            source.write_bytes(b"dummy tape")
            def fake_load(args):
                write_snapshot(args[-1], [[bank] * 16384 for bank in range(8)],
                               ["pc=32768"], ["7ffd=16"])
                print("Tape finished")
            with patch("skoolkit.tap2sna.main", side_effect=fake_load):
                info = engine.prepare_snapshot(source, directory / "snapshot.z80", "128")
            self.assertEqual(info["ram_bytes"], 131072)
            self.assertEqual(info["zero_bytes"], 16384)


if __name__ == "__main__":
    unittest.main()
