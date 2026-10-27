"""Navigate three pages and start distinct snapshots through real TR-DOS."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
import menu_screen
from skoolkit.snapshot import write_snapshot

# PAUSE visits this instruction more than once. Do not overwrite an injected
# key before ROM consumes it; wait for the next empty keyboard buffer.
WAIT = "7997 if [23621] == 144 && [23622] == 1 && ([23611] & 32) == 0"


def commands_for(keys, finish, game=False, game_break="32768 if z80:sp == 65000"):
    commands = "set $step 0\n"
    if game:
        commands += "breakpoint " + game_break + "\n"
    else:
        commands += f"breakpoint {WAIT} && $step == {len(keys)}\n"
    commands += "commands 1\n" + finish + "\nend\n"
    if keys:
        key = " + ".join(f"($step == {i}) * {ord(k)}" for i, k in enumerate(keys))
        commands += (f"breakpoint {WAIT} && $step < {len(keys)}\ncommands 2\n"
                     f"set 23560 ({key})\nset 23611 ([23611] | 32)\n"
                     "set $step ($step + 1)\ncontinue\nend")
    return commands.rstrip()


def run(disk, commands):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    p = subprocess.Popen([str(ROOT / ".tools/fuse/fuse.exe"), "--machine", "pentagon", "--no-sound",
                          "--speed", "1000", "--debugger-command", commands, str(disk)],
                         cwd=ROOT / ".tools/fuse", startupinfo=startup,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        log, _ = p.communicate(timeout=30)
        return {"passed": p.returncode == 42, "exit_code": p.returncode,
                "log": log.decode("utf-8", "replace") if p.returncode != 42 else ""}
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate()
        return {"passed": False, "error": "30-second timeout"}


def main():
    work = ROOT / ".work/pages-fuse"
    work.mkdir(parents=True, exist_ok=True)
    games, files = [], []
    for i in range(33):
        directory = work / f"G{i:02X}"; directory.mkdir(exist_ok=True)
        snapshot = directory / f"G{i:02X}.z80"
        ram = [0] * 49152
        ram[8192] = i
        ram[16384:16388] = [243, 195, 0, 128]
        write_snapshot(str(snapshot), ram, ["pc=32768", "sp=65000", f"bc={1000+i}"], ["iff=0"])
        packed, _ = engine.pack_snapshot(snapshot, "auto")
        next(f for f in packed if f.kind == "B").name = f"G{i:02X}"
        files.extend(packed)
        games.append({"title": f"ПРОГРАММА {i+1}", "loader": f"G{i:02X}"})
    pages = menu_screen.normalize_pages(None, None, len(games))
    pages[1]["previous"].update(x=0, y=22, width=16, text="P: предыдущая", ink=3)
    pages[1]["next"].update(x=16, y=22, width=16, text="N: следующая", ink=4)
    pages[1]["page"].update(x=10, y=23, width=12, text="{page} из {pages}")
    menu = engine.create_menu_files(engine.builtin_background(), "ТЕСТ СТРАНИЦ", games, pages)
    disk = work / "pages.trd"; disk.write_bytes(engine.write_trd(menu+files, "PAGES"))
    results = []
    # First/last key on full pages, wrap in both directions, lower-case keys,
    # ignored empty slot on the last page, and repeated page changes.
    cases = [("1", 0), ("G", 15), ("N1", 16), ("ng", 31), ("NN1", 32),
             ("P1", 32), ("NNN1", 0), ("NpG", 15), ("NNG1", 32), ("NPN1", 16)]
    for keys, index in cases:
        finish = f"exit 42 + (z80:bc != {1000+index} || [24576] != {index})"
        result = {"test": "launch", "keys": keys, "game": index+1,
                  **run(disk, commands_for(keys, finish, True))}
        results.append(result); print(json.dumps(result), flush=True)
        if not result["passed"]: break
    if all(r["passed"] for r in results) and "--quick" not in sys.argv:
        for page, keys in enumerate(("", "N", "NN")):
            screen = menu[page+1].data
            for begin in range(0, 6912, 1152):
                diff = " || ".join(f"[{16384+i}] != {screen[i]}" for i in range(begin, begin+1152))
                result = {"test": "screen", "page": page+1, "offset": begin, "bytes": 1152,
                          **run(disk, commands_for(keys, "exit 42 + (" + diff + ")"))}
                results.append(result); print(json.dumps(result), flush=True)
                if not result["passed"]: break
    (work / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
