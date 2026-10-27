import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
import menu_screen as menu


class MenuTests(unittest.TestCase):
    def test_cyrillic_all_letters_and_yo_are_real_glyphs(self):
        chars = "".join(chr(c) for c in range(0x410, 0x450)) + "Ёё"
        self.assertEqual(menu.text(chars, 100), chars)
        for c in chars:
            bitmap = menu.FONT[menu.glyph(c)*8:menu.glyph(c)*8+8]
            self.assertEqual(len(bitmap), 8)
            self.assertNotEqual(bitmap, bytes(8), c)
            self.assertNotEqual(bitmap, menu.FONT[menu.glyph("?")*8:menu.glyph("?")*8+8], c)
        self.assertNotEqual(menu.glyph("Е"), menu.glyph("Ё"))
        self.assertNotEqual(menu.glyph("е"), menu.glyph("ё"))

    def test_win91_source_glyphs_are_preserved_exactly(self):
        import hashlib
        source = (ROOT / "assets/win91-font.bin").read_bytes()
        metadata = json.loads((ROOT / "assets/win91-font.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(source).hexdigest(), metadata["font_sha256"])
        letters = "ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ"
        for start, chars in ((0x40, letters), (0x60, letters.lower())):
            for i, c in enumerate(chars):
                self.assertEqual(menu.FONT[menu.glyph(c)*8:menu.glyph(c)*8+8], source[(start+i-32)*8:(start+i-31)*8], c)

    def test_hidden_labels_leave_background_unchanged(self):
        layout = menu.default_layout(0)
        layout["title"]["visible"] = False
        layout["hint"]["visible"] = False
        background = engine.builtin_background()
        self.assertEqual(menu.render(background, "Русский", [], layout), background)

    def test_invalid_layouts_rejected(self):
        cases = [("x", -1), ("y", 24), ("width", 31), ("width", 3), ("x", 1.5),
                 ("x", True), ("ink", 8), ("paper", 7), ("visible", False), ("bright", "yes")]
        for key, value in cases:
            layout = menu.default_layout(1); layout["items"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): menu.normalize_layout(layout, 1)
        layout = menu.default_layout(1); layout["items"][0]["y"] = 1
        with self.assertRaisesRegex(ValueError, "Пересечение"): menu.normalize_layout(layout, 1)
        with self.assertRaises(ValueError): menu.normalize_layout({"items": []}, 1)

    def test_clipping_and_bottom_right_cell(self):
        layout = menu.default_layout(0)
        layout["hint"]["visible"] = False
        layout["title"].update(x=31, y=23, width=1, ink=2, paper=1, bright=True)
        result = menu.render(bytes(6912), "ЁЖ", [], layout)
        # Last character cell: bitmap bytes are in ZX's non-linear screen order.
        for y in range(184, 192):
            offset = (y//64)*2048 + (y % 8)*256 + ((y//8) % 8)*32 + 31
            self.assertEqual(result[offset], menu.FONT[menu.glyph("Ё")*8 + y%8])
        self.assertEqual(result[-1], 74)
        self.assertEqual(len(result), 6912)

    def test_cross_language_render_vectors(self):
        """Generate vectors that ScreenTests.cs must reproduce byte for byte."""
        work = ROOT / ".work"; work.mkdir(exist_ok=True)
        vectors = []
        alphabet = "".join(chr(c) for c in range(32, 127)) + "".join(chr(c) for c in range(0x410, 0x450)) + "Ёё"
        for case in range(8):
            games = [{"title": alphabet[i*26:(i+1)*26]} for i in range(7)]
            if case in (3, 4, 5):
                games = [{"title": "Русская игра Ёжик " + str(i)} for i in range(16)]
            elif case >= 6:
                games = [{"title": "Последняя игра"}]
            layout = menu.default_layout(len(games))
            if case == 1:
                layout["title"]["visible"] = False
                layout["hint"].update(x=0, y=23, width=32, text='Кавычки "Ёё" и русский текст')
                for i, entry in enumerate(layout["items"]):
                    entry.update(x=i%3, y=3+i*2, width=29-i, ink=(i+1)%8, paper=i%8, bright=i%2 == 0)
            elif case == 2:
                layout["title"].update(x=31, y=23, width=1)
                layout["hint"]["visible"] = False
            elif case == 3:
                for i, entry in enumerate(layout["items"]): entry.update(x=1+(i//8)*16, y=4+(i%8)*2, width=14)
            elif case == 5:
                layout["previous"].update(x=0, y=22, width=16, text="P: предыдущая", ink=3)
                layout["next"].update(x=16, y=22, width=16, text="N: следующая", ink=4)
                layout["page"].update(x=10, y=23, width=12, text="{page} из {pages}")
            elif case == 7:
                layout["previous"]["visible"] = layout["next"]["visible"] = False
                layout["page"].update(x=28, y=23, width=4, text="{page}/{pages}")
            title = 'Ёжик "ИГРЫ"'
            page_index, page_count = (min(case-4, 2), 3) if case >= 4 else (0, 1)
            expected = menu.render(engine.builtin_background(), title, games, layout, page_index, page_count)
            name = f"menu-vector-{case}.scr"; (work / name).write_bytes(expected)
            vectors.append({"title": title, "games": [g["title"] for g in games], "layout": layout, "expected": name,
                            "pageIndex": page_index, "pageCount": page_count})
        (work / "menu-vectors.json").write_text(json.dumps(vectors, ensure_ascii=True), encoding="utf-8")

    def test_basic_does_not_embed_display_text(self):
        games = [{"title": 'Ёжик: "\r\n"', "loader": "G00"}]
        file = engine.menu_file('Русский "заголовок"', games)
        self.assertIn(b'"MENU"', file.data)
        self.assertIn(b'"G00"', file.data)
        self.assertNotIn('Ёжик'.encode('utf-8'), file.data)


if __name__ == "__main__": unittest.main()
