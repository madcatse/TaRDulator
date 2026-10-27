"""Exercise both supplied demos in real Fuse, from menu and directly."""
from pathlib import Path
import argparse
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests'), str(ROOT/'scripts')]
import engine
import menu_screen
from skoolkit.tape import parse_tap
from check_pages_fuse import commands_for
from check_audit_fuse import run as check_snapshot
from capture_audit_screens import capture, render

OUT = ROOT/'output/feedback-0.7'
WORK = ROOT/'.work/feedback-0.7'


def fuse(disk, cmd):
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = 0
    try:
        p = subprocess.run([str(ROOT/'.tools/fuse/fuse.exe'), '--machine', 'pentagon',
                            '--no-sound', '--speed', '1000', '--debugger-command', cmd, str(disk)],
                           cwd=ROOT/'.tools/fuse', capture_output=True, startupinfo=startup, timeout=50)
        return {'passed': p.returncode == 42, 'exit_code': p.returncode,
                'log': (p.stdout + p.stderr).decode('utf-8', 'replace')}
    except subprocess.TimeoutExpired:
        return {'passed': False, 'error': '50-second timeout'}


def native_commands(keys, stage, frames, screen=None):
    blocks = parse_tap(str(ROOT/'taps/tricky_roms/MILKY2.TAP')).blocks
    checks = []
    for i in (3, 5):
        data = blocks[i].data[1:-1]
        checks.append(' || '.join(f'[{25000+n}] != {data[n]}' for n in range(0, len(data), 97)))
    finish = ('set $mismatch ($mismatch | (($part == 0) && (' + checks[0] + '))'
              + ' | (($part == 1) && (' + checks[1] + ')))\nset $part ($part+1)\ncontinue')
    cmd = 'set $part 0\nset $mismatch 0\nset $frames 0\n' + commands_for(keys, finish, True, '25000')
    if not keys:
        cmd += '\nbreakpoint 0 if 0\ncommands 2\ncontinue\nend'
    cmd += f'\nbreakpoint time 0 if $part == {stage} && $frames < {frames}\ncommands 3\nset $frames ($frames+1)\ncontinue\nend'
    cmd += f'\nbreakpoint time 0 if $frames == {frames}\ncommands 4\nprint 111111\nprint $part\nprint $mismatch\nprint z80:pc\nprint ula:mem7ffd\n'
    if screen is not None:
        offset, size = screen
        cmd += 'print 333333\n' + '\n'.join(f'print [{16384+n}]' for n in range(offset, offset+size)) + '\n'
    cmd += 'exit 42 + $mismatch\nend'
    return cmd


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--frozen', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True, parents=True)
    results = []
    for name in ('ECLIPSE', 'MILKY2'):
        path = ROOT/'taps/tricky_roms'/(name+'.TAP')
        directory = Path(tempfile.mkdtemp(prefix=name+'-verified-', dir=WORK))
        item = {'path': str(path), 'title': name, 'machine': 'auto', 'transfer_mode': 'auto'}
        with contextlib.redirect_stdout(io.StringIO()): files, info = engine.convert_game(item, 0, directory)
        for mode in ('menu', 'direct'):
            menu = [] if mode == 'direct' else engine.create_menu_files(engine.builtin_background(), name,
                [{'title': name, 'loader': 'G00'}], menu_screen.normalize_pages(None, None, 1))
            next(f for f in files if f.kind == 'B').name = 'boot' if mode == 'direct' else 'G00'
            disk = OUT/(name+'-'+mode+'.trd')
            expected = engine.write_trd(menu+files, name)
            disk.write_bytes(expected)
            row = {'id': 0, 'name': name, 'mode': mode, 'machine': info['load_machine'],
                   'directory': str(directory), 'snapshot': str(directory/'G00/G00.z80'),
                   'disk': str(disk), 'menu_key': '' if mode == 'direct' else '1', 'info': info}
            if args.frozen:
                exe = ROOT/'dist/TaRDulator/engine/TaRDulator.Engine.exe'
                req = {'action': 'build', 'title': name, 'games': [item], 'launch_mode': mode,
                       'output': str(disk), 'overwrite': True}
                p = subprocess.run([str(exe)], input=json.dumps(req).encode(), capture_output=True,
                                   cwd=exe.parent, timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
                (OUT/(name+'-'+mode+'-engine.log')).write_bytes(p.stdout+p.stderr)
                row['frozen_matches_source'] = p.returncode == 0 and disk.read_bytes() == expected
                assert row['frozen_matches_source'], p.stdout
            if name == 'ECLIPSE':
                row['fuse'] = check_snapshot(row)
                assert row['fuse']['passed'], row
                row['screen'] = capture(row, prefix='ECLIPSE-'+mode, output_dir=OUT)
            else:
                row['stages'] = []
                for stage, frames in ((1, 100), (2, 500), (2, 6000)):
                    result = fuse(disk, native_commands(row['menu_key'], stage, frames))
                    row['stages'].append({'part': stage, 'frames': frames, **result})
                    assert result['passed'], result
                    if mode != 'direct' or frames == 6000: continue
                    data = []
                    for offset in range(0, 6912, 1024):
                        size = min(1024, 6912-offset)
                        part = fuse(disk, native_commands('', stage, frames, (offset, size)))
                        assert part['passed'], part
                        numbers = [int(x,16) for x in re.findall(r'^0x([\da-fA-F]+)\s*$', part['log'], re.M)]
                        chunk = numbers[numbers.index(333333)+1:]
                        assert len(chunk) == size
                        data.extend(chunk)
                    render(data).save(OUT/f'MILKY2-part{stage}.png')
                    (OUT/f'MILKY2-part{stage}.scr').write_bytes(bytes(data))
            results.append(row)
            (OUT/'verified.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(name, mode, 'PASS', flush=True)


if __name__ == '__main__': main()
