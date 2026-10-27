"""Verify the fixed tricky tapes in Fuse, with direct and menu startup.

Requires audit_tricky10.py --out .work/tricky-0.10/release first.
The emulator receives a disk only; no tape is mounted.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
import engine
import load_strategies
import menu_screen
from check_audit_fuse import run as snapshot_check
from check_pages_fuse import commands_for

OUT = ROOT/'output/tricky-0.10'


def chain_commands(row, settled_frames=500, repeat=False):
    profile = row['info']['tape_profile']
    chain = load_strategies.CHAINS[profile]
    parts = chain.payloads(ROOT/'taps/tricky_roms'/row['name'])
    order = list(range(len(parts))) + ([chain.repeat_from] if repeat else [])
    body = ''
    # Descending order prevents advancing twice at one breakpoint, even when
    # consecutive parts begin with identical code.
    for stage in reversed(range(len(order))):
        data = parts[order[stage]]
        offsets = sorted(set(range(48)) | set(range(0, len(data), 251)) | {len(data)-1})
        checks = ' && '.join(f'[{chain.address+n}] == {data[n]}' for n in offsets)
        body += f'set $stage ($stage + (($stage == {stage}) && ({checks})))\n'
    body += 'continue'
    cmd = 'set $stage 0\nset $elapsed 0\nset $settled 0\n' + commands_for(
        row['menu_key'], body, True, str(chain.address))
    if not row['menu_key']:
        cmd += '\nbreakpoint 0 if 0\ncommands 2\ncontinue\nend'
    cmd += f'\nbreakpoint time 0 if $settled == {settled_frames}\ncommands 3\nprint $stage\nprint z80:pc\nexit 42\nend'
    cmd += '\nbreakpoint time 0 if $elapsed == 60000\ncommands 4\nprint $stage\nprint z80:pc\nexit 43\nend'
    cmd += ('\nbreakpoint time 0 if $elapsed < 60000\ncommands 5\nset $elapsed ($elapsed+1)\n'
            f'set $settled ($settled + ($stage == {len(order)}))\ncontinue\nend')
    return cmd


def check_chain(row):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    repeat = False
    frames = 6000
    try:
        p = subprocess.run([str(ROOT/'.tools/fuse/fuse.exe'), '--machine', 'pentagon',
            '--no-sound', '--speed', '5000', '--debugger-command',
            chain_commands(row, frames, repeat), row['disk']], cwd=ROOT/'.tools/fuse',
            capture_output=True, timeout=100, startupinfo=startup)
        return {'passed': p.returncode == 42, 'exit_code': p.returncode,
                'log': (p.stdout+p.stderr).decode('utf-8', 'replace'),
                'parts': len(load_strategies.CHAINS[row['info']['tape_profile']].blocks),
                'repeat_checked': repeat, 'frames_after_last_part': frames}
    except subprocess.TimeoutExpired as exc:
        return {'passed': False, 'error': '100-second timeout',
                'log': (exc.stdout or b'').decode('utf-8', 'replace')}


def check(row):
    result = check_chain(row) if row['info'].get('tape_profile') in load_strategies.CHAINS else snapshot_check(row)
    print(row['name'], row['mode'], 'PASS' if result['passed'] else {k:v for k,v in result.items() if k != 'log'}, flush=True)
    return {**row, 'fuse': result}


def frozen(row):
    exe = ROOT/'dist/TaRDulator/engine/TaRDulator.Engine.exe'
    target = Path(row['disk']).with_suffix('.frozen.trd')
    request = {'action': 'build', 'title': 'TRICKY', 'launch_mode': row['mode'],
        'output': str(target), 'overwrite': True, 'games': [{'path': str(ROOT/'taps/tricky_roms'/row['name']),
        'title': Path(row['name']).stem, 'machine': 'auto', 'transfer_mode': 'auto'}]}
    p = subprocess.run([str(exe)], input=json.dumps(request).encode(), cwd=exe.parent,
        capture_output=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW)
    target.with_suffix('.log').write_bytes(p.stdout+p.stderr)
    match = p.returncode == 0 and target.exists() and target.read_bytes() == Path(row['disk']).read_bytes()
    print(row['name'], row['mode'], 'frozen', match, flush=True)
    return {'name': row['name'], 'mode': row['mode'], 'passed': match, 'returncode': p.returncode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen', action='store_true')
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT/'.work/tricky-0.10/release/results.json').read_text(encoding='utf-8'))
    cases = []
    for i, row in enumerate(rows):
        if not row['ok'] or (args.names and row['name'] not in args.names):
            continue
        for mode in ('direct', 'menu'):
            files = engine.read_trd(Path(row['disk']).read_bytes())
            next(f for f in files if f.kind == 'B').name = 'boot' if mode == 'direct' else 'G00'
            menu = [] if mode == 'direct' else engine.create_menu_files(engine.builtin_background(),
                'TRICKY', [{'title': Path(row['name']).stem, 'loader': 'G00'}],
                menu_screen.normalize_pages(None, None, 1))
            disk = OUT/f'{i:02d}-{Path(row["name"]).stem}-{mode}.trd'
            disk.write_bytes(engine.write_trd(menu+files, 'TRICKY'))
            cases.append({**row, 'disk': str(disk), 'mode': mode, 'menu_key': '' if mode == 'direct' else '1'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = []
        for result in pool.map(frozen if args.frozen else check, cases):
            results.append(result)
            (OUT/('frozen.json' if args.frozen else 'fuse.json')).write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    assert all(r['passed'] if args.frozen else r['fuse']['passed'] for r in results)


if __name__ == '__main__':
    main()
