"""Build a paged example from the user's current collection in taps/."""
from pathlib import Path
import argparse
import base64
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
import menu_screen

parser = argparse.ArgumentParser()
parser.add_argument("--exclude", nargs="*", default=[], help="Explicit TAP filenames to omit from this example")
options = parser.parse_args()
paths = sorted((p for p in (ROOT / "taps").glob("*.tap") if p.name not in options.exclude), key=lambda p: p.name.lower())
assert len(paths) > 16, "This example needs more than sixteen TAPs"
games = [{"path": str(path), "title": path.stem, "machine": "48"} for path in paths]
pages = menu_screen.normalize_pages(None, None, len(games))
pages[1]["previous"].update(x=0, y=22, width=16, text="P: предыдущая", ink=3)
pages[1]["next"].update(x=16, y=22, width=16, text="N: следующая", ink=4)
pages[1]["page"].update(x=10, y=23, width=12, text="{page} из {pages}")
request = {"action": "build", "output": str(ROOT / "output/PagesExample.trd"), "overwrite": True,
           "title": "КОЛЛЕКЦИЯ ПРОГРАММ", "pages": pages, "games": games}
result = subprocess.run([str(ROOT / "dist/Tap2Trd/engine/Tap2Trd.Engine.exe")],
                        input=json.dumps(request).encode("ascii"), capture_output=True, timeout=120)
(ROOT / ".work/pages-build.log").write_bytes(result.stdout+result.stderr)
result.check_returncode()
report = json.loads(Path(request["output"]).with_suffix(".report.json").read_text(encoding="utf-8"))
files = engine.read_trd(Path(request["output"]).read_bytes())
for i, layout in enumerate(pages):
    expected = menu_screen.render(engine.builtin_background(), request["title"], games[i*16:(i+1)*16], layout, i, len(pages))
    assert next(f for f in files if f.name == engine.screen_name(i)).data[:6912] == expected
# Templates retain 16 editable slots on the final partial page.
pages[-1]["items"] = menu_screen.default_layout(16)["items"]
template = {"version": 2, "title": request["title"], "pages": pages,
            "background": base64.b64encode(engine.builtin_background()).decode("ascii")}
(ROOT / "output/PagesMenu.t2menu").write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"games": len(games), "pages": report["page_count"], "files": report["file_count"],
                  "used_bytes": report["used_bytes"], "screens_match": True, "excluded": options.exclude}))
