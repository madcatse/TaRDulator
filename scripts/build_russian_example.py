"""Build the local example using the packaged engine, without redistributing TAPs."""
from pathlib import Path
import base64
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
import engine
import menu_screen

names = ["Зевс", "Бильярд", "Диверсант", "Брюс Ли", "Джофар", "Это Spectrum", "Весна 2024", "Windows 91"]
paths = [root / "taps" / name for name in (
    "A7_zeus.tap", "B3_POOL.tap", "B6_SABOTEUR.tap", "BruceLeeRX.tap",
    "jophar.tap", "this_is.tap", "Vesna_24.tap", "win91.tap")]
layout = menu_screen.default_layout(len(names))
for i, item in enumerate(layout["items"]): item["y"] = 4+i*2
request = {"action": "build", "output": str(root / "output/RussianCollection.trd"), "overwrite": True,
           "title": "КОЛЛЕКЦИЯ ИГР", "layout": layout,
           "games": [{"path": str(path), "title": name, "machine": "48"} for path, name in zip(paths, names)]}
result = subprocess.run([str(root / "dist/Tap2Trd/engine/Tap2Trd.Engine.exe")], input=json.dumps(request).encode("ascii"),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
(root / ".work/russian-build.log").write_bytes(result.stdout)
report = json.loads((root / "output/RussianCollection.report.json").read_text(encoding="utf-8"))
screen = next(f for f in engine.read_trd((root / "output/RussianCollection.trd").read_bytes()) if f.name == "MENU").data[:6912]
assert screen == (root / ".work/russian-preview.scr").read_bytes()
print(json.dumps({"games": len(report["games"]), "used_bytes": report["used_bytes"], "menu_matches_preview": True}))
# Template includes unused slots, positioned in the gaps between the eight games.
for i in range(8): layout["items"].append(menu_screen.style(2, 5+i*2))
template = {"version": 2, "title": request["title"], "pages": [layout],
            "background": base64.b64encode(engine.builtin_background()).decode("ascii")}
(root / "output/RussianMenu.t2menu").write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
