"""Check restoration and continued execution of archived tapes in real Fuse."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
from skoolkit.snapshot import Snapshot
from check_pages_fuse import commands_for


def commands(row, frames=500, screen=None):
    s = Snapshot.get(row['snapshot'])
    ram = s.ram()
    addresses = list(range(23296,23755)) + [a for a in range(24576,65000,257) if abs(a-s.sp)>128]
    if row.get('allow_stack_scratch'):
        addresses=[a for a in addresses if not s.sp-32<=a<s.sp]
    diff = ' || '.join(f'[{a}] != {ram[a-16384]}' for a in addresses)
    checks = ' && '.join(f'z80:{reg} == {getattr(s,reg)}' for reg in ('sp','bc','de','hl','ix','iy'))
    finish = 'set $mismatch ('+diff+')\n'
    if row['machine'] == '128':
        banks = s.ram(-1)
        finish += f'set $mismatch ($mismatch | (ula:mem7ffd != {s.out7ffd}))\n'
        for bank in range(8):
            probes = [0,1,31,255,256,511,1024,2048,4096,8192,12288,16000,16383]
            # Z80to needs a few bytes below SP to restore registers.
            def near_stack(offset):
                addresses = []
                if bank == 5: addresses.append(16384+offset)
                if bank == 2: addresses.append(32768+offset)
                if bank == (s.out7ffd&7): addresses.append(49152+offset)
                return any(abs(address-s.sp) <= 128 for address in addresses)
            probes = [p for p in probes if not near_stack(p)]
            diff = ' || '.join(f'[{49152+p}] != {banks[bank*16384+p]}' for p in probes)
            finish += f'out 32765 {16+bank}\nset $mismatch ($mismatch | ({diff}))\n'
        finish += f'out 32765 {s.out7ffd}\n'
    finish += 'print 111111\nprint $mismatch\nset $begun 1\ndelete 1\ncontinue'
    if screen is not None:
        # Screen capture is separate from the restoration checks. Keep the
        # command line below Windows' 32767-character limit.
        finish = 'set $mismatch 0\nset $begun 1\ndelete 1\ncontinue'
    result = 'set $begun 0\nset $frames 0\n' + commands_for(row.get('menu_key','1'),finish,True,f'{s.pc} if '+checks)
    if not row.get('menu_key', '1'):
        result += '\nbreakpoint 0 if 0\ncommands 2\ncontinue\nend'
    result += f'\nbreakpoint time 0 if $begun == 1 && $frames < {frames}\ncommands 3\nset $frames ($frames + 1)\ncontinue\nend'
    result += f'\nbreakpoint time 0 if $frames == {frames}\ncommands 4\nprint 222222\nprint z80:pc\nprint ula:mem7ffd\n'
    if screen is not None:
        start,size=screen
        result += 'print 333333\n' + '\n'.join(f'print [{16384+i}]' for i in range(start,start+size)) + '\n'
    result += 'exit 42 + $mismatch\nend'
    return result


def run(row, frames=500, screen=None):
    directory = Path(row['directory'])
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    argv = [str(ROOT/'.tools/fuse/fuse.exe'),'--machine','pentagon','--no-sound','--speed','1000',
            '--debugger-command',commands(row,frames,screen),row['disk']]
    try:
        p = subprocess.run(argv,cwd=ROOT/'.tools/fuse',capture_output=True,timeout=35,startupinfo=startup)
        log=p.stdout.decode('utf-8','replace')+p.stderr.decode('utf-8','replace')
        (directory / ('fuse-'+str(screen[0])+'.log' if screen else 'fuse.log')).write_text(log,encoding='utf-8')
        return {'id':row['id'],'machine':row['machine'],'passed':p.returncode==42,'exit_code':p.returncode,'log':log,'frames':frames}
    except subprocess.TimeoutExpired:
        return {'id':row['id'],'machine':row['machine'],'passed':False,'error':'35-second timeout'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ids',nargs='*',type=int)
    parser.add_argument('--machine',choices=('48','128'))
    parser.add_argument('--input',default='best-load.json')
    parser.add_argument('--output',default='fuse-state.json')
    args=parser.parse_args()
    rows=json.loads((ROOT/'output/games48-128'/args.input).read_text(encoding='utf-8'))
    results=[]
    for row in rows:
        if not row.get('disk') or (args.ids is not None and row['id'] not in args.ids) or (args.machine and row['machine']!=args.machine):continue
        result=run(row);results.append(result)
        print(json.dumps(result),flush=True)
        (ROOT/'output/games48-128'/args.output).write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':main()
