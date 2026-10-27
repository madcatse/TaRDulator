"""Refresh an existing preview's docs/sources while preserving every runtime byte."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "TaRDulator/"
DOCUMENTS = (
    "LICENSE", "README.md", "USAGE.md", "CONTRIBUTING.md", "THIRD_PARTY.md",
    "VALIDATION.md", "LOADING_STRATEGIES.md", "ESCAPE_COMPATIBILITY.md",
    "CHANGELOG.md", "LICENSING.md", "RELEASING.md",
)
LOGO = "assets/branding/tardulator-logo-readme.jpg"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-list", type=Path,
                        help="JSON array of tracked source paths; defaults to git ls-files")
    args = parser.parse_args()
    commit = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit("GITHUB_SHA must identify the documentation/source revision")
    old_digest = digest(args.archive.read_bytes())
    if old_digest != args.expected_sha256:
        raise SystemExit("Existing release archive does not match the reviewed SHA-256")
    with zipfile.ZipFile(args.archive) as archive:
        if archive.testzip() or len(archive.namelist()) != len(set(archive.namelist())):
            raise SystemExit("Invalid ZIP integrity or duplicate names")
        before = {}
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = PurePosixPath(item.filename)
            if not item.filename.startswith(PREFIX) or ".." in name.parts:
                raise SystemExit("Unexpected archive path")
            before[item.filename[len(PREFIX):]] = archive.read(item)
    original_manifest = json.loads(before["BUILD_INFO.json"])
    for name, checksum in original_manifest["files"].items():
        if name not in before or digest(before[name]) != checksum:
            raise SystemExit("Existing file manifest mismatch: " + name)
    if set(original_manifest["files"]) != set(before) - {"BUILD_INFO.json"}:
        raise SystemExit("Existing manifest is incomplete")
    if original_manifest["version"] != "0.10.1":
        raise SystemExit("This reviewed promotion is for 0.10.1 only")

    if args.source_list:
        tracked = json.loads(args.source_list.read_text(encoding="utf-8"))
    else:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").rstrip("\0").split("\0")
    sources = {}
    for name in tracked:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or ":" in name or "\\" in name:
            raise SystemExit("Unsafe source path")
        source = ROOT / name
        if not source.is_file() or source.is_symlink():
            raise SystemExit("Missing or linked source: " + name)
        sources["source/" + name] = source.read_bytes()
    # Never pass off changed application code as the previously tested binaries.
    old_app = {k: v for k, v in before.items() if k.startswith("source/src/")}
    new_app = {k: v for k, v in sources.items() if k.startswith("source/src/")}
    if not old_app or old_app != new_app:
        raise SystemExit("Application sources changed; publish a new version instead")

    after = {k: v for k, v in before.items() if not k.startswith("source/")}
    for name, data in before.items():
        if name.startswith("source/third-party/"):
            after[name] = data
    after.update(sources)
    for name in DOCUMENTS:
        after[name] = (ROOT / name).read_bytes()
    for license_file in sorted((ROOT / "licenses").glob("*.txt")):
        after.setdefault("licenses/" + license_file.name, license_file.read_bytes())
    after[LOGO] = (ROOT / LOGO).read_bytes()
    after.pop("BUILD_INFO.json")
    runtime = {k: v for k, v in before.items()
               if not k.startswith("source/") and k not in DOCUMENTS
               and k not in ("BUILD_INFO.json", LOGO)}
    for name, data in runtime.items():
        if after.get(name) != data:
            raise SystemExit("Runtime byte changed: " + name)
    if not all(name in runtime for name in (
            "TaRDulator.exe", "engine/TaRDulator.Engine.exe", "engine/Z80to.exe")):
        raise SystemExit("Runtime verification did not cover all executables")
    manifest = {
        "version": original_manifest["version"],
        "source_commit": commit,
        "binary_source_commit": original_manifest.get("binary_source_commit", original_manifest["source_commit"]),
        "previous_archive_sha256": old_digest,
        "runtime_files_preserved": len(runtime),
        "files": {k: digest(v) for k, v in sorted(after.items())},
    }
    after["BUILD_INFO.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / args.archive.name
    if output.resolve() == args.archive.resolve():
        raise SystemExit("Output must not overwrite the input archive")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(after.items()):
            info = zipfile.ZipInfo(PREFIX + name)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise SystemExit("New ZIP integrity check failed")
        for name, data in runtime.items():
            if archive.read(PREFIX + name) != data:
                raise SystemExit("Written runtime verification failed: " + name)
        for name, checksum in manifest["files"].items():
            if digest(archive.read(PREFIX + name)) != checksum:
                raise SystemExit("Written manifest verification failed: " + name)
    checksum = digest(output.read_bytes())
    (args.output_dir / "SHA256SUMS.txt").write_text(
        f"{checksum}  {output.name}\n", encoding="ascii")
    print(json.dumps({
        "archive": output.name, "sha256": checksum,
        "runtime_files_preserved": len(runtime), "files": len(after),
        "source_commit": commit, "binary_source_commit": manifest["binary_source_commit"],
    }))


if __name__ == "__main__":
    main()
