"""Extract the user's Windows'91 KOI-7 font without modifying the TAP.

The source is optional for normal builds: the exact 768-byte font is stored
in assets/win91-font.bin. Only this font block is included in the app sources.
"""
from pathlib import Path
import functools
import hashlib
import json
import operator
import struct
import sys

root = Path(__file__).resolve().parents[1]
path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "win91_optimized.tap"
data = path.read_bytes()
blocks = []; pos = 0
while pos < len(data):
    if pos+2 > len(data): raise ValueError("Truncated TAP length")
    length = struct.unpack_from("<H", data, pos)[0]
    block = data[pos+2:pos+2+length]
    if len(block) != length or length < 2 or functools.reduce(operator.xor, block):
        raise ValueError("Invalid TAP block")
    blocks.append(block); pos += length+2
fonts = []
for i, header in enumerate(blocks[:-1]):
    if len(header) == 19 and header[:2] == b"\x00\x03":
        length, address = struct.unpack_from("<HH", header, 12)
        following = blocks[i+1]
        if length == 768 and address == 24078 and len(following) == 770 and following[0] == 255:
            fonts.append((i+2, following[1:-1]))
if len(fonts) != 1: raise ValueError("Expected one Windows'91 font at address 24078")
block_number, font = fonts[0]
(root / "assets/win91-font.bin").write_bytes(font)
metadata = {"source": path.name, "tap_sha256": hashlib.sha256(data).hexdigest(),
            "data_block": block_number, "header_load_address": 24078, "bytes": len(font),
            "font_sha256": hashlib.sha256(font).hexdigest(), "encoding": "KOI-7",
            "missing_glyphs": ["Ё", "ё", "Ъ", "ъ"]}
(root / "assets/win91-font.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(metadata, ensure_ascii=True))
