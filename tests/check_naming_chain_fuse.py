"""Copy a synthetic native chain between disks and execute A,B,C,B,C in Fuse."""
from pathlib import Path
import json
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import disk_names
import engine
import load_strategies


def main():
    directory = ROOT / ".work/naming-chain-fuse"
    directory.mkdir(parents=True, exist_ok=True)
    payloads = []
    for part in range(3):
        # Record the part at 24577 and the visit count at 24576. All return
        # at 32780; the first part initializes the counter and is not repeated.
        counter = bytes([62, 1, 0, 0]) if part == 0 else bytes([58, 0, 96, 60])
        payloads.append(bytes([62, part, 50, 1, 96]) + counter + bytes([50, 0, 96, 201]))
    chain = load_strategies.NativeChain("TEST", (0, 1, 2), (13, 13, 13), 32768, 32767, repeat_from=1)
    analysis = {"path": "synthetic.tap", "sha256": "0" * 64, "size": 39}
    with patch.dict(load_strategies.CHAINS, {"test": chain}), patch.object(load_strategies.NativeChain, "payloads", return_value=payloads):
        files, info = engine.convert_native_chain({}, analysis, "TMP", "test")
    identity = disk_names.bundle_id(files, analysis["sha256"], {})
    stem = disk_names.short_name(identity)
    files = disk_names.rename_bundle(files, "TMP.", stem)
    files = list(reversed(engine.read_trd(engine.write_trd(files, "SOURCE"))))
    results = []
    for launch in ("menu", "direct"):
        if launch == "menu":
            games = [{"title": "CHAIN", "loader": stem}]
            startup_files = engine.create_menu_files(engine.builtin_background(), "TEST", games, [None])
        else:
            loader = next(f for f in files if f.kind == "B")
            startup_files = [engine.DiskFile("boot", "B", loader.parameter, loader.length, loader.data)]
        disk = directory / (launch + ".trd")
        disk.write_bytes(engine.write_trd(startup_files + files, "MOVED"))
        commands = ("set $mismatch 0\n"
                    "tbreakpoint 7997 if [23621] == 144 && [23622] == 1\n"
                    "commands 1\nset 23560 49\nset 23611 ([23611] | 32)\ncontinue\nend\n"
                    "tbreakpoint 32780 if [24576] == 5\n"
                    "commands 2\nexit 42 + $mismatch + ([24577] != 2)\nend\n"
                    "breakpoint 32780 if [24576] < 5\ncommands 3\n"
                    "set $mismatch ($mismatch | (([24576] == 1) && ([24577] != 0)) | "
                    "((([24576] == 2) || ([24576] == 4)) && ([24577] != 1)) | "
                    "(([24576] == 3) && ([24577] != 2)))\ncontinue\nend")
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        process = subprocess.Popen([str(ROOT / ".tools/fuse/fuse.exe"), "--machine", "pentagon",
            "--no-sound", "--speed", "1000", "--debugger-command", commands, str(disk)],
            cwd=ROOT / ".tools/fuse", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startup)
        try:
            output, _ = process.communicate(timeout=30)
            result = {"launch_mode": launch, "passed": process.returncode == 42,
                      "exit_code": process.returncode, "sequence": "A,B,C,B,C", "loader": stem,
                      "log": output.decode("utf-8", "replace")}
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            result = {"launch_mode": launch, "passed": False, "error": "timeout"}
        results.append(result)
        print(json.dumps(result), flush=True)
    (directory / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
