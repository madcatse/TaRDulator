"""Combine Spectrum Latin glyphs with the user's Windows'91 Russian font.

All 62 letters present in the source are copied exactly, with KOI-7 mapped
to Unicode. The source has a blank at '_' and copyright at DEL: hard signs
are missing. Yo and hard-sign additions derive from this same font.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = (root / "assets/font.bin").read_bytes()
assert len(base) == 768
chars = "".join(chr(c) for c in range(0x410, 0x450)) + "Ёё"
source = (root / "assets/win91-font.bin").read_bytes()
assert len(source) == 768
koi7 = "ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ"
glyphs = {}
for first, letters in ((0x40, koi7), (0x60, koi7.lower())):
    for i, c in enumerate(letters):
        offset = (first+i-32)*8
        glyphs[c] = source[offset:offset+8]
for hard, soft, row in (("Ъ", "Ь", 1), ("ъ", "ь", 2)):
    value = bytearray(glyphs[soft]); value[row] |= 0x40; glyphs[hard] = bytes(value)
upper_e = glyphs["Е"]
glyphs["Ё"] = bytes((0x24, 0, upper_e[1], upper_e[2], upper_e[3], upper_e[4], upper_e[6], 0))
value = bytearray(glyphs["е"]); value[0] = 0x28; glyphs["ё"] = bytes(value)
assert set(glyphs) == set(chars)
(root / "src/menu_font.bin").write_bytes(base + b"".join(glyphs[c] for c in chars))
