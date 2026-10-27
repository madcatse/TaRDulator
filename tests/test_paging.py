import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
import menu_screen as menu


class PagingTests(unittest.TestCase):
    def test_page_boundaries_and_independent_positions(self):
        for count, sizes in ((1, [1]), (16, [16]), (17, [16, 1]), (32, [16, 16]), (33, [16, 16, 1]), (41, [16, 16, 9])):
            pages = menu.normalize_pages(None, None, count)
            self.assertEqual([len(p["items"]) for p in pages], sizes)
        pages[1]["items"][0]["x"] = 0
        self.assertEqual(pages[0]["items"][0]["x"], 2)
        with self.assertRaises(ValueError):
            menu.normalize_pages([menu.default_layout(16)], None, 17)

    def test_old_layout_preserves_single_page_pixels(self):
        legacy = menu.default_layout(1)
        for name in ("previous", "next", "page"):
            legacy.pop(name)
        legacy["version"] = 1
        legacy["title"].update(x=31, y=23, width=1)
        games = [{"title": "Ёжик"}]
        original = menu.render(engine.builtin_background(), "Ё", games, legacy)
        migrated = menu.normalize_pages(None, legacy, 1)[0]
        self.assertEqual(original, menu.render(engine.builtin_background(), "Ё", games, migrated))
        # Navigation now becomes visible and conflicts with the old placement.
        legacy["hint"]["y"] = 23
        with self.assertRaisesRegex(ValueError, "Пересечение"):
            menu.normalize_layout(legacy, 1, 2)

    def test_navigation_overlap_and_hidden_controls(self):
        page = menu.default_layout(16)
        page["previous"]["y"] = 4
        with self.assertRaisesRegex(ValueError, "Пересечение"):
            menu.normalize_layout(page, 16, 2)
        page["previous"]["visible"] = False
        menu.normalize_layout(page, 16, 2)
        for name in ("previous", "next", "page"):
            invalid = copy.deepcopy(page)
            invalid[name]["x"] = 32
            with self.assertRaises(ValueError):
                menu.normalize_layout(invalid, 16, 2)

    def test_multi_page_basic_lines_are_unique_sorted_and_bounded(self):
        games = [{"title": "Game", "loader": f"G{i:02X}"} for i in range(41)]
        file = engine.menu_file("", games)
        pos = 0; lines = []
        while pos < file.length:
            line = int.from_bytes(file.data[pos:pos+2], "big")
            length = int.from_bytes(file.data[pos+2:pos+4], "little")
            lines.append(line)
            self.assertEqual(file.data[pos+3+length], 13)
            pos += length+4
        self.assertEqual(lines, sorted(set(lines)))
        self.assertLess(max(lines), 10000)
        for name in ("MENU", "MENU01", "MENU02", "G00", "G10", "G20", "G28"):
            self.assertIn(('"' + name + '"').encode(), file.data)
        for key in ("P", "p", "N", "n"):
            self.assertIn(('k$="' + key + '"').encode(), file.data)

    def test_real_directory_limit_includes_every_menu_page_and_keeps_old_disk(self):
        def fake(item, i, work):
            name = f"G{i:02X}"
            files = [engine.basic_file(name, b"x"),
                     engine.DiskFile(name+".0", "C", 16384, 1, b"x"),
                     engine.DiskFile(name+".M", "C", 32768, 1, b"x")]
            if item.get("extra"):
                files.append(engine.DiskFile(name+".1", "C", 49152, 1, b"x"))
            return files, {"loader": name, "title": "TEST", "bytes": len(files)*256}
        with tempfile.TemporaryDirectory(dir=ROOT / ".work") as d:
            target = Path(d) / "collection.trd"
            games = [{"path": "fixture.tap"} for _ in range(41)]
            request = {"games": games, "output": str(target), "overwrite": True}
            with patch.object(engine, "convert_game", side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
                report = engine.build(request)
                self.assertEqual(report["page_count"], 3)
                self.assertEqual(report["file_count"], 127)
                games[-1]["extra"] = True
                report = engine.build(request)
                self.assertEqual(report["file_count"], 128)
                self.assertEqual(len(engine.read_trd(target.read_bytes())), 128)
                before = target.read_bytes()
                games.append({"path": "fixture.tap"})
                with self.assertRaisesRegex(ValueError, "Каталог"):
                    engine.build(request)
                self.assertEqual(before, target.read_bytes())
                self.assertEqual(len(json.loads(target.with_suffix(".report.json").read_text(encoding="utf-8"))["games"]), 41)


if __name__ == "__main__":
    unittest.main()
