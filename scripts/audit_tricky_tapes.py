"""Reproducible, non-destructive 48K/128K audit of the user's tape archive."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import engine
import menu_screen
from skoolkit.snapshot import Snapshot
from skoolkit.tape import parse_tap, parse_tzx

WORK = ROOT / '.work/games48-128'
OUTPUT = ROOT / 'output/games48-128'


def extract():
    archive = ROOT / 'taps/games48-128.zip'
    inputs = WORK / 'input'
    inputs.mkdir(parents=True, exist_ok=True)
    inventory = []
    with zipfile.ZipFile(archive) as z:
        for i, member in enumerate(z.infolist()):
            if member.is_dir():
                continue
            name = member.filename
            if '/' in name or '\\' in name or ':' in name or Path(name).suffix.lower() not in ('.tap', '.tzx'):
                raise ValueError('Unexpected archive member: ' + name)
            if member.file_size > 16*1024*1024:
                raise ValueError('Oversized archive member')
            data = z.read(member)
            path = inputs / name
            path.write_bytes(data)
            entry = {'id': i, 'name': name, 'path': str(path), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()}
            try:
                entry['validation'] = engine.inspect_tap(path)
                entry['accepted_by_0_4'] = True
            except ValueError as error:
                entry.update(accepted_by_0_4=False, validation_error=str(error))
            tape = parse_tap(str(path)) if path.suffix.lower() == '.tap' else parse_tzx(str(path))
            entry['blocks'] = [{'number': b.number, 'id': b.block_id, 'bytes': len(b.data) if b.data else 0}
                               for b in tape.blocks]
            inventory.append(entry)
    result = {'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': inventory}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return inventory


def load_case(item, machine, extra=(), tag='baseline'):
    case = WORK / f"{item['id']:02d}-{machine}-{tag}"
    case.mkdir(parents=True, exist_ok=True)
    source = Path(item['path'])
    tape_name = 'input' + source.suffix.lower()
    shutil.copyfile(source, case / tape_name)
    snapshot = case / 'G00.z80'
    if snapshot.exists():
        snapshot.unlink()
    command = [sys.executable, '-c', 'import sys;from skoolkit.tap2sna import main;main(sys.argv[1:])',
               '-c', 'machine='+machine, '-c', 'timeout=300', *extra, tape_name, snapshot.name]
    started = time.monotonic()
    result = {'id': item['id'], 'name': item['name'], 'machine': machine, 'tag': tag,
              'accepted_by_0_4': item['accepted_by_0_4'], 'options': list(extra), 'directory': str(case)}
    try:
        process = subprocess.run(command, cwd=case, capture_output=True, timeout=120,
                                 env={**os.environ, 'PYTHONIOENCODING':'utf-8'},
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        log = (process.stdout + process.stderr).decode('utf-8', 'replace')
        (case / 'load.log').write_text(log, encoding='utf-8')
        result.update(returncode=process.returncode, tape_finished='Tape finished' in log,
                      timed_out='timed out' in log,
                      stop=next(iter(re.findall(r'Simulation stopped[^\r\n]*', log)), ''),
                      log_file=str(case / 'load.log'))
        result['complete'] = process.returncode == 0 and snapshot.exists() and result['tape_finished'] and not result['timed_out'] and 'interrupted' not in log
        if snapshot.exists():
            s = Snapshot.get(str(snapshot))
            result.update(pc=s.pc, sp=s.sp, snapshot_machine=s.machine, ram_bytes=len(s.ram(-1)),
                          out7ffd=s.out7ffd, snapshot=str(snapshot))
            (case / 'screen.scr').write_bytes(bytes(s.ram()[:6912]))
        if result['complete']:
            files, packed = engine.pack_snapshot(snapshot, 'preserve' if machine == '128' else 'auto')
            next(f for f in files if f.kind == 'B').name = 'G00'
            games = [{'title': item['name'].split(' (')[0], 'loader': 'G00'}]
            layouts = menu_screen.normalize_pages(None, None, 1)
            menu = engine.create_menu_files(engine.builtin_background(), 'ТЕСТ ' + machine + 'К', games, layouts)
            disk = case / 'launch.trd'
            disk.write_bytes(engine.write_trd(menu+files, 'TEST'))
            result.update(disk=str(disk), disk_bytes=sum(f.sectors*256 for f in files+menu),
                          result_machine=packed['result_machine'])
            (case / 'pack.log').write_text(packed['converter_log'], encoding='utf-8')
    except Exception as error:
        result['error'] = str(error)
    result['seconds'] = round(time.monotonic()-started, 2)
    (case / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    inventory = extract()
    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(load_case, item, machine) for item in inventory for machine in ('48','128')]
        for job in as_completed(jobs):
            result = job.result()
            results.append(result)
            print(json.dumps({k:v for k,v in result.items() if k not in ('directory','snapshot','log_file','disk')}, ensure_ascii=True), flush=True)
            (OUTPUT / 'baseline.json').write_text(json.dumps(sorted(results, key=lambda r:(r['id'],int(r['machine']))), ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
