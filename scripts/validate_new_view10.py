"""Verify every original New View part at its TR-DOS entry point in Fuse."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src')]
from skoolkit.tape import parse_tap
from check_pages_fuse import commands_for
p=argparse.ArgumentParser();p.add_argument('--stage',type=int,default=5);p.add_argument('--frames',type=int,default=30000);a=p.parse_args()
folder=ROOT/'.work/tricky-0.10/fixes1/02'
row=json.loads((folder/'result.json').read_text(encoding='utf-8'))
blocks=parse_tap(str(ROOT/'taps/tricky_roms/New_View_48K.tap')).blocks
cmd='set $stage 0\nset $frames 0\nbreakpoint 24576\ncommands 1\n'
for part,index in enumerate((3,5,7,9,11)):
    data=blocks[index].data[1:-1]
    offsets=list(range(48))+list(range(100,len(data),251))+[len(data)-1]
    checks=' && '.join(f'[{24576+n}] == {data[n]}' for n in offsets)
    cmd+=f'set $stage ($stage + (($stage == {part}) && ({checks})))\n'
cmd+=f'print $stage\ncontinue\nend\nbreakpoint time 0 if $stage == {a.stage}\ncommands 2\nexit 42\nend'
cmd+=f'\nbreakpoint time 0 if $frames < {a.frames}\ncommands 3\nset $frames ($frames+1)\ncontinue\nend\nbreakpoint time 0 if $frames == {a.frames}\ncommands 4\nprint $stage\nprint z80:pc\nexit 43\nend'
si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
try:
    proc=subprocess.run([str(ROOT/'.tools/fuse/fuse.exe'),'--machine','pentagon','--no-sound','--speed','5000','--debugger-command',cmd,row['disk']],cwd=ROOT/'.tools/fuse',capture_output=True,timeout=90,startupinfo=si)
    result={'passed':proc.returncode==42,'exit_code':proc.returncode,'log':(proc.stdout+proc.stderr).decode('utf-8','replace')}
except subprocess.TimeoutExpired as exc:
    result={'passed':False,'timeout':180,'log':(exc.stdout or b'').decode('utf-8','replace')}
(folder/'native-fuse.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
