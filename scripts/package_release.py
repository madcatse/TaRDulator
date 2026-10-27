"""Package a clean portable build, with its sources and SHA-256 manifest."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / 'src/app_version.py'))['VERSION']
REQUIRED = (
    'TaRDulator.exe', 'engine/TaRDulator.Engine.exe', 'engine/Z80to.exe',
    'help/index.ru.html', 'help/index.en.html', 'help/help.css',
    'licenses/SkoolKit-GPL-3.0.txt', 'licenses/Z80to-MIT.txt',
    'licenses/Python.txt', 'licenses/PyInstaller.txt', 'licenses/Spectrum-ROM.txt',
    'LICENSING.md', 'THIRD_PARTY.md', 'CHANGELOG.md', 'USAGE.md',
    'source/.github/workflows/windows.yml', 'source/releases/v' + VERSION + '.md',
    'source/src/tape_catalog.py', 'source/src/menu_font.bin',
    'source/assets/win91-font.bin', 'source/assets/win91-font.json',
    'source/build.ps1', 'source/setup.ps1', 'source/requirements-build.txt',
    'source/src/engine.py', 'source/src/app_version.py',
    'source/scripts/generate_version.py',
    'source/third-party/skoolkit-10.1.tar.gz',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'dist/TaRDulator')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'releases-out')
    args = parser.parse_args()
    directory = args.build_dir.resolve()
    missing = [name for name in REQUIRED if not (directory / name).is_file()]
    if missing:
        raise SystemExit('Incomplete portable build: ' + ', '.join(missing))
    source_version = runpy.run_path(str(directory / 'source/src/app_version.py'))['VERSION']
    if source_version != VERSION:
        raise SystemExit('Packaged source version does not match the working source')
    entries = sorted(p for p in directory.rglob('*') if p.is_file())
    for path in entries:
        relative = path.relative_to(directory)
        if (path.is_symlink() or path.suffix.lower() in
            {'.tap', '.tzx', '.trd', '.scl', '.sna', '.z80', '.szx', '.pyc'} or
            '__pycache__' in relative.parts or path.name.lower() == 'settings.json'):
            raise SystemExit('Clean build required; unexpected file: ' + str(relative))
    commit = os.environ.get('GITHUB_SHA')
    if commit and not re.fullmatch(r'[0-9a-fA-F]{40}', commit):
        raise SystemExit('Invalid GITHUB_SHA')
    manifest = {'version': VERSION, 'source_commit': commit,
                'files': {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in entries}}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / f'TaRDulator-v{VERSION}-win-x64.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in entries:
            info = zipfile.ZipInfo('TaRDulator/' + path.relative_to(directory).as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, path.read_bytes())
        output.writestr('TaRDulator/BUILD_INFO.json', json.dumps(manifest, indent=2) + '\n')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (args.output_dir / 'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise SystemExit('ZIP integrity check failed')
    print(json.dumps({'version': VERSION, 'archive': str(archive), 'sha256': digest,
                      'files': len(entries) + 1, 'bytes': archive.stat().st_size}))


if __name__ == '__main__':
    main()
