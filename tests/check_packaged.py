"""Compare a packaged-engine measurement against the final example disk."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine


def main():
    disk = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "output/RussianCollection.trd"
    expected = json.loads(disk.with_suffix(".report.json").read_text(encoding="utf-8"))
    hashes = {g["path"]: hashlib.sha256(Path(g["path"]).read_bytes()).hexdigest() for g in expected["games"]}
    with tempfile.TemporaryDirectory(dir=ROOT / ".work") as temporary:
        target = Path(temporary) / "not-written.trd"
        env = {**os.environ, "TMP": temporary, "TEMP": temporary}
        request = {"action": "measure", "output": str(target), "title": expected["title"],
                   "pages": expected["pages"], "games": [
                       {"path": g["path"], "title": g["title"], "machine": g["load_machine"],
                        "start": g["start"], "transfer_mode": g["transfer_mode"]}
                       for g in expected["games"]]}
        run = subprocess.run([str(ROOT / "dist/TaRDulator/engine/TaRDulator.Engine.exe")],
                             input=json.dumps(request).encode("ascii"), capture_output=True,
                             env=env, timeout=120, check=True)
        events = [json.loads(line) for line in run.stdout.splitlines()]
        actual = next(e for e in events if e["event"] == "result")
        assert list(Path(temporary).iterdir()) == [], "Measurement left output or temporary files"
    assert actual["version"] == expected["version"] == engine.VERSION
    assert actual["used_bytes"] == expected["used_bytes"]
    assert actual["file_count"] == expected["file_count"]
    assert actual["page_count"] == expected["page_count"]
    assert actual["disk_sha256"] == hashlib.sha256(disk.read_bytes()).hexdigest()
    files = engine.read_trd(disk.read_bytes())
    for game, built in zip(actual["games"], expected["games"]):
        for field in ("tap_bytes", "ram_bytes", "bytes", "result_machine", "transfer_mode"):
            assert game[field] == built[field], (game["title"], field)
        assert game["tap_bytes"] == Path(game["path"]).stat().st_size
        assert hashes[game["path"]] == hashlib.sha256(Path(game["path"]).read_bytes()).hexdigest()
        assert game["bytes"] == sum(f.sectors * 256 for f in files if f.name.startswith(game["loader"]))
    summary = {"version": engine.VERSION, "games": len(actual["games"]), "passed": True,
               "pages": actual["page_count"], "files": actual["file_count"],
               "used_bytes": actual["used_bytes"], "disk_sha256": actual["disk_sha256"],
               "checks": ["measurement equals built disk", "sizes include sector padding and loaders",
                          "no measurement output left behind", "source TAP hashes unchanged"]}
    (ROOT / ("output/size-validation-" + disk.stem + "-0.4.json")).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

