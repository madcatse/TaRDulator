"""Exercise Z80to's transfer policies through the real menu and TR-DOS.

Synthetic snapshots deliberately put executable code at 23296 and distinct
data in every 128K bank. Requires local Fuse; no user TAP files are needed.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine
import menu_screen
from skoolkit.snapshot import write_snapshot


def main():
    results = []
    cases = [(model, mode, False) for model, mode in
             (("48", "auto"), ("128", "auto"), ("128", "preserve"), ("128", "48"))]
    cases.append(("128", "preserve", True))
    for model, mode, negative_control in cases:
        directory = ROOT / ".work/transfer-fuse" / (model + "-" + mode + ("-negative" if negative_control else ""))
        directory.mkdir(parents=True, exist_ok=True)
        ram = [0] * 49152
        ram[6912:7371] = [(i * 37 + 19) % 256 for i in range(459)]
        ram[6912:6916] = [243, 195, 0, 91]  # DI: JP 23296, inside printer buffer
        banks = [[0] * 16384 for _ in range(8)]
        banks[5], banks[2], banks[0] = ram[:16384], ram[16384:32768], ram[32768:]
        for b in (1, 3, 4, 6, 7):
            banks[b][:512] = [(b * 29 + i * 7) % 256 for i in range(512)]
        snapshot = directory / "TST.z80"
        write_snapshot(str(snapshot), ram if model == "48" else banks,
                       ["pc=23296", "sp=65000", "bc=4660", "de=23456", "hl=34567", "ix=45678"],
                       ["7ffd=16", "iff=0"])
        original = snapshot.read_bytes()
        files, info = engine.pack_snapshot(snapshot, mode)
        assert snapshot.read_bytes() == original
        loader = next(f.name for f in files if f.kind == "B")
        games = [{"title": "MEMORY TEST", "loader": loader}]
        screen = menu_screen.render(engine.builtin_background(), "TEST", games)
        disk = directory / "test.trd"
        disk.write_bytes(engine.write_trd([engine.menu_file("TEST", games),
            engine.DiskFile("MENU", "C", 16384, 6912, screen)] + files, "TEST"))
        addresses = list(range(23296, 23755)) + [24576, 32768, 49152, 60000, 65535]
        differences = " || ".join(f"[{a}] != {ram[a-16384]}" for a in addresses)
        commands = ("tbreakpoint 7997 if [23621] == 144 && [23622] == 1\n"
                    "commands 1\nset 23560 49\nset 23611 ([23611] | 32)\ncontinue\nend\n"
                    "breakpoint 23296 if z80:sp == 65000 && z80:bc == 4660 && z80:de == 23456 && z80:hl == 34567 && z80:ix == 45678\n"
                    f"commands 2\nset $mismatch ({differences})\n")
        bank_probes = 0
        if info["result_machine"] == "128":
            commands += "set $mismatch ($mismatch | (ula:mem7ffd != 16))\n"
            for b in range(8):
                offsets = list(range(0, 512, 31)) + [1024, 8192, 16383]
                # One deliberately wrong expectation proves bank comparisons
                # can detect a mismatch (including debugger-variable syntax).
                diff = " || ".join(f"[{49152+a}] != {banks[b][a] ^ int(negative_control and b == 1 and a == 0)}" for a in offsets)
                commands += f"out 32765 {16+b}\nset $mismatch ($mismatch | ({diff}))\n"
                bank_probes += len(offsets)
        else:
            commands += "set $mismatch ($mismatch | ((ula:mem7ffd & 32) == 0))\n"
        commands += "exit 42 + $mismatch\nend"
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        process = subprocess.Popen([str(ROOT / ".tools/fuse/fuse.exe"), "--machine", "pentagon",
            "--no-sound", "--speed", "1000", "--debugger-command", commands, str(disk)],
            cwd=ROOT / ".tools/fuse", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            output, _ = process.communicate(timeout=30)
            result = {"source": model, "transfer_mode": mode, "result_machine": info["result_machine"],
                      "passed": process.returncode == (43 if negative_control else 42), "exit_code": process.returncode,
                      "negative_control": negative_control,
                      "printer_and_system_bytes": 459, "extra_ram_probes": 5,
                      "bank_probes": bank_probes, "log": output.decode("utf-8", "replace")}
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate()
            result = {"source": model, "transfer_mode": mode, "passed": False, "error": "timeout"}
        results.append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "log"}), flush=True)
    (ROOT / ".work/transfer-fuse/results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
