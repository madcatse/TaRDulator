"""Portable bundles, independent disk builds, collisions and BASIC integrity."""
import contextlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import disk_names
import engine


def make_tape(path, marker):
    def block(data):
        checksum = 0
        for byte in data:
            checksum ^= byte
        return struct.pack("<H", len(data) + 1) + data + bytes([checksum])
    program = engine.basic_line(10, bytes([226]) + b":" + engine.token("REM") + marker.encode("ascii"))
    path.write_bytes(block(b"\0\0TEST      " + struct.pack("<HHH", len(program), 10, len(program))) + block(b"\xff" + program))
    return path


def synthetic_snapshot(path, out, machine, start):
    from skoolkit.snapshot import write_snapshot
    ram = [0] * 49152
    ram[16384:16388] = [243, 195, 0, 128]
    ram[8192] = path.read_bytes()[-3]
    write_snapshot(str(out), ram, ["pc=32768", "sp=65000"], ["iff=0"])
    return {"extra_banks_changed": False, "load_machine": "48", "warning": ""}


class NamingTests(unittest.TestCase):
    def test_rebuilds_basic_lengths_and_trailer_without_modifying_code(self):
        body = engine.disk_load("TMP.M", True)
        # Cross a sector boundary after replacing a five-character filename
        # with an eight-character one; preserve the non-default autostart.
        body += b":" + engine.token("REM") + b"x" * (250 - 5 - len(body) - 2)
        loader = engine.basic_file("TMP", engine.basic_line(10, body), 1234)
        payload = b'Binary data containing "TMP.M" must stay unchanged'
        original = [loader, engine.DiskFile("TMP.M", "C", 32768, len(payload), payload)]
        files = disk_names.rename_bundle(original, "TMP.", "7K3Q9AZ")
        self.assertEqual(files[0].sectors, 2)
        self.assertEqual(original[0].sectors, 1)
        self.assertEqual(files[0].data[-4:], b"\x80\xaa\xd2\x04")
        self.assertEqual(files[0].parameter, files[0].length)
        self.assertEqual(int.from_bytes(files[0].data[2:4], "little"), files[0].length - 4)
        self.assertIn(b'"7K3Q9AZM"', files[0].data)
        self.assertEqual(files[1].data, payload)
        self.assertEqual(original[0].name, "TMP")
        restored = engine.read_trd(engine.write_trd(files, "TEST"))
        self.assertEqual(restored[0].data[:files[0].length + 4], files[0].data)

    def test_unknown_loader_structure_fails_instead_of_corrupting_a_program(self):
        code = engine.DiskFile("TMP.M", "C", 32768, 1, b"x")
        for program in (b"broken", engine.basic_line(10, engine.disk_load("TMP.X", True)),
                        engine.basic_line(10, engine.disk_load("OTHER", True))):
            with self.subTest(program=program), self.assertRaises(ValueError):
                disk_names.rename_bundle([engine.basic_file("TMP", program), code], "TMP.", "123ABCD")

    def test_identifier_uses_all_seven_characters_and_wraps_on_collision(self):
        self.assertEqual(disk_names.short_name("0"), "0000000")
        identity = hex(disk_names.NAME_SPACE - 1)[2:]
        self.assertEqual(disk_names.short_name(identity), "ZZZZZZZ")
        self.assertEqual(disk_names.short_name(identity, 1), "0000000")


@unittest.skipUnless(engine.tool_path().is_file(), "Local Z80to not installed")
class NamingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.tapes = [make_tape(self.work / (name + ".tap"), name) for name in ("ONE", "TWO")]
        self.patch = patch.object(engine, "select_snapshot", side_effect=synthetic_snapshot)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def build(self, names, **options):
        request = {"action": "measure", "games": [{"path": str(p)} for p in names], **options}
        with contextlib.redirect_stdout(io.StringIO()):
            return engine.build(request)

    def test_names_survive_reordering_source_rename_and_title_changes(self):
        original = self.build(self.tapes)
        reverse = self.build(self.tapes[::-1])
        for a, b in zip(original["games"], reversed(reverse["games"])):
            self.assertEqual(a["files"], b["files"])
            self.assertEqual(a["file_id"], b["file_id"])
        renamed = self.work / "renamed.tap"
        renamed.write_bytes(self.tapes[0].read_bytes())
        single = self.build([renamed], games=[{"path": str(renamed), "title": "Another title"}])
        self.assertEqual(single["games"][0]["files"], original["games"][0]["files"])
        self.assertNotEqual(original["games"][0]["loader"], original["games"][1]["loader"])

    def test_options_and_changed_packed_payload_get_different_names(self):
        base = self.build(self.tapes[:1])["games"][0]
        forced = self.build([], games=[{"path": str(self.tapes[0]), "transfer_mode": "48"}])["games"][0]
        self.assertNotEqual(base["loader"], forced["loader"])
        with patch.object(engine, "select_snapshot", side_effect=lambda path, *args: synthetic_snapshot(self.tapes[1], *args)):
            changed = self.build(self.tapes[:1])["games"][0]
        self.assertNotEqual(base["loader"], changed["loader"])

    def test_duplicates_and_forced_hash_collisions_keep_loaders_consistent(self):
        normal_short_name = disk_names.short_name
        with patch.object(disk_names, "short_name", side_effect=lambda identity, collision=0: normal_short_name("0", collision)):
            report = self.build([self.tapes[0], self.tapes[1], self.tapes[0]], action="build", output=str(self.work / "collision.trd"))
        self.assertEqual([g["loader"] for g in report["games"]], ["0000000", "0000001", "0000002"])
        self.check_references(self.work / "collision.trd", report)

    def check_references(self, path, report):
        files = engine.read_trd(path.read_bytes())
        names = {f.name for f in files}
        boot = next(f for f in files if f.name == "boot")
        for game in report["games"]:
            self.assertIn(('"' + game["loader"] + '"').encode(), boot.data)
            loader = next(f for f in files if f.name == game["loader"])
            self.assertIn(('"' + game["file_prefix"] + '"').encode(), loader.data)
            self.assertIn(('"' + game["file_prefix"] + 'M"').encode(), loader.data)
            self.assertTrue(all(f["name"] in names for f in game["files"]))
        return files

    def test_separately_built_disks_can_be_mixed_without_renaming(self):
        bundles, games = [], []
        for i, tape in enumerate(self.tapes):
            path = self.work / f"disk{i}.trd"
            report = self.build([tape], action="build", output=str(path))
            source_files = self.check_references(path, report)
            game = report["games"][0]
            names = {f["name"] for f in game["files"]}
            bundles.extend(f for f in source_files if f.name in names)
            games.append(game)
        combined = engine.write_trd([engine.menu_file("MIXED", games)] + list(reversed(bundles)), "MIXED")
        moved = engine.read_trd(combined)
        self.assertEqual(len(moved), 1 + len(bundles))
        for f in bundles:
            other = next(g for g in moved if (g.name, g.kind) == (f.name, f.kind))
            self.assertEqual(other.data, f.data)

    def test_direct_boot_alias_leaves_a_portable_bundle_and_measurement_matches(self):
        path = self.work / "direct.trd"
        report = self.build(self.tapes[:1], action="build", launch_mode="direct", output=str(path))
        measured = self.build(self.tapes[:1], launch_mode="direct")
        self.assertEqual(report["disk_sha256"], measured["disk_sha256"])
        self.assertEqual(report["used_bytes"], measured["used_bytes"])
        game = report["games"][0]
        files = engine.read_trd(path.read_bytes())
        named = next(f for f in files if f.name == game["loader"])
        self.assertEqual(files[0].name, "boot")
        self.assertEqual(files[0].data, named.data)
        self.assertEqual(game["bytes"], sum(f["bytes"] for f in game["files"]))
        self.assertEqual(report["used_bytes"], game["bytes"] + files[0].sectors * 256)
        self.assertNotIn("boot", [f["name"] for f in game["files"]])


if __name__ == "__main__":
    unittest.main()
