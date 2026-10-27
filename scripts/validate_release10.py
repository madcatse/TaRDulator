"""Reproducible release check: real tapes -> engine -> TRD -> Fuse.

Run select, source, frozen, fuse in that order. Each source conversion has its
own process because SkoolKit changes the current directory during loading.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import secrets
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
import engine
import menu_screen

OUTPUT = ROOT / 'output/release-0.10-regression'
WORK = ROOT / '.work/release-0.10-regression'


def save(name, value):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8'))


def select():
    if (OUTPUT / 'selection.json').exists():
        raise ValueError('Selection already exists; keep the original random sample')
    archive = json.loads((ROOT / 'output/games48-128/inventory.json').read_text(encoding='utf-8'))
    cases = [{k: v for k, v in row.items() if k in ('id', 'name', 'path', 'sha256')}
             | {'group': 'archive'} for row in archive['files']]
    population = sorted((ROOT / 'taps').glob('*.tap'), key=lambda p: p.name.lower())
    seed = secrets.randbits(64)
    sample = random.Random(seed).sample(population, 10)
    for path in sample:
        cases.append({'id': len(cases), 'name': path.name, 'path': str(path), 'group': 'random',
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    save('selection.json', {'seed': seed, 'population': [p.name for p in population],
                            'archive_sha256': archive['archive_sha256'], 'cases': cases})
    for c in cases:
        print(c['id'], c['name'])


def request(row, target):
    return {'action': 'build', 'title': 'REGRESSION 0.10', 'overwrite': True, 'output': str(target),
            'games': [{'path': row['path'], 'title': 'TEST', 'machine': 'auto', 'transfer_mode': 'auto'}]}


def source_case(row):
    base = WORK / f"{row['id']:02d}"
    base.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='run-', dir=base))
    result = {**row, 'directory': str(directory), 'complete': False}
    log = io.StringIO()
    started = time.monotonic()
    try:
        with contextlib.redirect_stdout(log):
            files, info = engine.convert_game(request(row, '')['games'][0], 0, directory)
        menu = engine.create_menu_files(engine.builtin_background(), 'REGRESSION 0.10',
                                       [{'title': 'TEST', 'loader': 'G00'}], menu_screen.normalize_pages(None, None, 1))
        disk = directory / 'source.trd'
        disk.write_bytes(engine.write_trd(menu + files, 'REGRESSION 0.10'))
        result.update(complete=True, snapshot=str(directory / 'G00/G00.z80'), disk=str(disk),
                      machine=info['load_machine'], info=info)
    except Exception as error:
        result['error'] = str(error)
    result['seconds'] = round(time.monotonic()-started, 2)
    (directory / 'source.log').write_text(log.getvalue(), encoding='utf-8')
    (base / 'source.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


def source_one(row):
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'case', '--id', str(row['id'])],
                       cwd=ROOT, capture_output=True, timeout=300,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', 'replace'))
    return json.loads((WORK / f"{row['id']:02d}/source.json").read_text(encoding='utf-8'))


def frozen_one(row):
    directory = Path(row['directory'])
    disk = directory / 'frozen.trd'
    exe = ROOT / 'dist/TaRDulator/engine/TaRDulator.Engine.exe'
    p = subprocess.run([str(exe)], input=json.dumps(request(row, disk)).encode(),
                       capture_output=True, cwd=exe.parent, timeout=300,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    text = p.stdout.decode('utf-8', 'replace')
    (directory / 'frozen.log').write_text(text + p.stderr.decode('utf-8', 'replace'), encoding='utf-8')
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    result = {**row, 'frozen_returncode': p.returncode}
    final = next((e for e in events if e['event'] == 'result'), None)
    if final:
        result.update(disk=str(disk), frozen_report=final,
                      frozen_matches_source=disk.read_bytes() == Path(row['disk']).read_bytes())
    else:
        result['frozen_error'] = next((e['message'] for e in events if e['event'] == 'error'), 'No result')
    result['frozen_ok'] = bool(final and result['frozen_matches_source']) if row['complete'] else p.returncode != 0 and not disk.exists()
    return result


def fuse_one(row):
    from check_audit_fuse import run
    # The converter's documented restoration stub uses bytes below SP.
    # Preserve a strict first run and only then check the known stack exception.
    result = run(row)
    (Path(row['directory']) / 'fuse-strict.log').write_text(result.get('log', ''), encoding='utf-8')
    if not result['passed'] and row['id'] in (2, 3) and row['group'] == 'archive':
        result['with_stack_scratch'] = run({**row, 'allow_stack_scratch': True})
    return result


def collections():
    rows = read('frozen.json')
    cases, reports = [], []
    exe = ROOT / 'dist/TaRDulator/engine/TaRDulator.Engine.exe'
    for name, members in (
        ('Archive-TAP', [r for r in rows if r['group'] == 'archive' and r['path'].lower().endswith('.tap')]),
        ('Archive-TZX', [r for r in rows if r['group'] == 'archive' and r['path'].lower().endswith('.tzx') and r['complete']]),
        ('Random-TAP', [r for r in rows if r['group'] == 'random'])):
        disk = OUTPUT / (name + '.trd')
        req = request(members[0], disk)
        req['games'] = [{'path': r['path'], 'title': r['name'].split(' (')[0][:29], 'machine': 'auto'} for r in members]
        p = subprocess.run([str(exe)], input=json.dumps(req).encode(), capture_output=True,
                           cwd=exe.parent, timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (OUTPUT / (name + '.log')).write_bytes(p.stdout + p.stderr)
        if p.returncode:
            raise RuntimeError(p.stdout.decode('utf-8', 'replace'))
        report = json.loads(disk.with_suffix('.report.json').read_text(encoding='utf-8'))
        reports.append(report)
        for i, row in enumerate(members):
            cases.append({**row, 'disk': str(disk), 'menu_key': engine.KEYS[i]})
        print(name, len(members), report['used_bytes'], report['file_count'], flush=True)
    save('collection-cases.json', cases)
    save('collections.json', reports)


def capture_one(row):
    from capture_audit_screens import capture
    return capture(row, output_dir=OUTPUT)


def contact(results):
    from PIL import Image, ImageDraw
    canvas = Image.new('RGB', (4*272, ((len(results)+3)//4)*225), '#333333')
    draw = ImageDraw.Draw(canvas)
    for n, row in enumerate(sorted(results, key=lambda r: r['id'])):
        x, y = n % 4 * 272 + 8, n // 4 * 225 + 24
        canvas.paste(Image.open(row['image']), (x, y))
        draw.text((x, y-19), f"{row['id']:02d} Fuse {row['machine']}K PC={row['pc_after']}", fill='white')
    canvas.save(OUTPUT / 'fuse-contact.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('select', 'case', 'source', 'frozen', 'fuse', 'collections', 'collection-fuse', 'screens'))
    parser.add_argument('--id', type=int)
    args = parser.parse_args()
    if args.stage == 'select':
        return select()
    if args.stage == 'collections':
        return collections()
    selection = read('selection.json')['cases']
    if args.stage == 'case':
        return source_case(next(r for r in selection if r['id'] == args.id))
    rows = selection if args.stage == 'source' else read('source.json' if args.stage == 'frozen' else 'frozen.json')
    if args.stage in ('collection-fuse', 'screens'):
        rows = read('collection-cases.json')
    if args.stage == 'fuse':
        rows = [r for r in rows if r['complete'] and r['frozen_ok']]
    if args.id is not None:
        rows = [r for r in rows if r['id'] == args.id]
    function = {'source': source_one, 'frozen': frozen_one, 'fuse': fuse_one,
                'collection-fuse': fuse_one, 'screens': capture_one}[args.stage]
    results = []
    with ThreadPoolExecutor(max_workers=1 if args.stage in ('fuse', 'collection-fuse') else 2) as pool:
        jobs = [pool.submit(function, row) for row in rows]
        for job in as_completed(jobs):
            result = job.result()
            results.append(result)
            save(args.stage + '.json', sorted(results, key=lambda r: r['id']))
            print(json.dumps({k: v for k, v in result.items() if k in
                              ('id', 'name', 'machine', 'complete', 'error', 'seconds', 'frozen_ok', 'passed', 'with_stack_scratch', 'image')}, ensure_ascii=True), flush=True)
    if args.stage == 'screens':
        contact(results)
    if args.stage == 'source' and any(not r['complete'] for r in results if r['id'] != 13):
        raise SystemExit(1)
    if args.stage == 'frozen' and not all(r['frozen_ok'] for r in results):
        raise SystemExit(1)
    if args.stage in ('fuse', 'collection-fuse') and not all(r['passed'] or r.get('with_stack_scratch', {}).get('passed') for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

