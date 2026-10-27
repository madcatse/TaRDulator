"""Read every screen byte through Fuse's debugger after the actual disk boots.

Checks the shipped Russian example and a fixture with text in the bottom-right
cell. Runs in chunks to stay within the Windows command-line size limit.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine


def main():
    work = ROOT / ".work/menu-fuse"
    work.mkdir(parents=True, exist_ok=True)
    edge_screen = (ROOT / ".work/menu-vector-2.scr").read_bytes()
    edge_image = engine.write_trd([engine.menu_file("", []), engine.DiskFile("MENU", "C", 16384, 6912, edge_screen)], "EDGE")
    edge_path = work / "edge.trd"; edge_path.write_bytes(edge_image)
    paths = [ROOT / "output/RussianCollection.trd", edge_path]
    results = []
    for path in paths:
        menu = next(f for f in engine.read_trd(path.read_bytes()) if f.name == "MENU" and f.kind == "C").data[:6912]
        for begin in range(0, 6912, 1152):
            differs = " || ".join(f"[{16384+i}] != {menu[i]}" for i in range(begin, begin+1152))
            commands = ("tbreakpoint 7997 if [23621] == 144 && [23622] == 1\ncommands 1\nexit 42 + ("
                        + differs + ")\nend")
            startup = subprocess.STARTUPINFO(); startup.dwFlags = subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
            p = subprocess.Popen([str(ROOT / ".tools/fuse/fuse.exe"), "--machine", "pentagon", "--no-sound", "--speed", "1000",
                                  "--debugger-command", commands, str(path)], cwd=ROOT / ".tools/fuse", startupinfo=startup,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                output, _ = p.communicate(timeout=30)
                passed = p.returncode == 42
            except subprocess.TimeoutExpired:
                p.kill(); output, _ = p.communicate(); passed = False
            result = {"image": path.name, "screen_offset": begin, "bytes": 1152, "passed": passed, "exit_code": p.returncode}
            results.append(result); print(json.dumps(result), flush=True)
            if not passed:
                print(output.decode("utf-8", "replace"), flush=True)
                break
    (work / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if len(results) == 12 and all(r["passed"] for r in results) else 1


if __name__ == "__main__": raise SystemExit(main())
