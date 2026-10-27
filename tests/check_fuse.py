"""Integration check against the actual Fuse CPU, Beta Disk and TR-DOS ROM.

Runs each disk loader to the original snapshot PC and checks core registers
and sampled RAM. This is a launch-state check, not a gameplay test.
Requires the optional local Fuse installation and the user's sample TAPs.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
from skoolkit.snapshot import Snapshot
from check_pages_fuse import commands_for


def main():
    image = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "output/FirstCollection.trd"
    files = engine.read_trd(image.read_bytes())
    report = json.loads(image.with_suffix(".report.json").read_text(encoding="utf-8"))
    work = ROOT / ".work/fuse-check"
    work.mkdir(parents=True, exist_ok=True)
    results = []
    for i, game in enumerate(report["games"]):
        if len(sys.argv) > 2 and i not in [int(n)-1 for n in sys.argv[2].split(",")]:
            continue
        directory = work / game["loader"]
        directory.mkdir(exist_ok=True)
        snapshot_file = directory / "original.z80"
        engine.prepare_snapshot(Path(game["path"]), snapshot_file,
                                game.get("load_machine", game.get("machine", "48").replace("K", "")),
                                game.get("start", ""))
        s = Snapshot.get(str(snapshot_file))
        ram = s.ram()
        checks = [f"z80:sp == {s.sp}", f"z80:bc == {s.bc}", f"z80:de == {s.de}",
                  f"z80:hl == {s.hl}", f"z80:ix == {s.ix}", f"z80:iy == {s.iy}"]
        addresses = [a for a in range(24576, 65000, 1237) if abs(a-s.sp) > 256]
        # Every byte of the printer buffer and system variables, not only a
        # probe at 23296. Keep these out of the breakpoint condition so a
        # mismatch is a failure, rather than silently waiting for a later PC.
        addresses = sorted(set(addresses) | set(range(23296, 23755)))
        differences = " || ".join(f"[{a}] != {ram[a-16384]}" for a in addresses)
        disk = directory / "launch.trd"
        disk.write_bytes(image.read_bytes())
        # Feed a key into the ROM keyboard buffer only once the actual menu
        # is waiting in PAUSE at BASIC line 400. The rest runs unmodified.
        keys = "N" * (i // engine.PAGE_SIZE) + engine.KEYS[i % engine.PAGE_SIZE]
        commands = commands_for(keys, f"exit 42 + ({differences})", True,
                                f"{s.pc} if " + " && ".join(checks))
        argv = [str(ROOT / ".tools/fuse/fuse.exe"), "--machine", "pentagon", "--no-sound",
                "--speed", "1000", "--debugger-command", commands, str(disk)]
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        p = subprocess.Popen(argv, cwd=ROOT / ".tools/fuse", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            output, _ = p.communicate(timeout=30)
            result = {"title": game["title"], "game": i+1, "page": i//16+1, "keys": keys,
                      "pc": s.pc, "passed": p.returncode == 42,
                      "exit_code": p.returncode, "ram_samples": len(addresses), "registers": 6,
                      "printer_buffer_bytes": 256, "system_variable_bytes": 203,
                      "log": output.decode("utf-8", "replace")}
        except subprocess.TimeoutExpired:
            p.kill(); p.communicate()
            result = {"title": game["title"], "pc": s.pc, "passed": False, "error": "30-second timeout"}
        results.append(result)
        print(json.dumps(result, ensure_ascii=True), flush=True)
        (work / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
