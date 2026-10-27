import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts')]
from check_audit_fuse import commands
from capture_audit_screens import render
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--frames',type=int,default=500);p.add_argument('--snapshot',action='store_true');p.add_argument('--shadow',action='store_true');p.add_argument('--boot',action='store_true');a=p.parse_args()
row=json.loads((a.folder/'result.json').read_text(encoding='utf-8'))
if a.snapshot:row['disk']=row['snapshot']
startinfo=subprocess.STARTUPINFO();startinfo.dwFlags=subprocess.STARTF_USESHOWWINDOW;startinfo.wShowWindow=0
pixels=[];pcs=[]
for begin in range(0,6912,1024):
    if a.boot:
        cmd=f'set $frames 0\nbreakpoint time 0 if $frames < {a.frames}\ncommands 1\nset $frames ($frames+1)\ncontinue\nend\nbreakpoint time 0 if $frames == {a.frames}\ncommands 2\nprint 222222\nprint z80:pc\nprint 333333\nprint [16384]\nexit 42\nend'
    else:
        cmd=commands(row,a.frames,(0,1))
    # A paging change is for debugger reads only, after the observation point.
    body='out 32765 23\n' if a.shadow else ''
    body+='\n'.join(f'print [{(49152 if a.shadow else 16384)+n}]' for n in range(begin,min(begin+1024,6912)))+'\n'
    cmd=cmd.replace('print [16384]\n',body)
    try:
        pr=subprocess.run([str(ROOT/'.tools/fuse/fuse.exe'),'--machine','pentagon','--no-sound','--speed','1000','--debugger-command',cmd,row['disk']],cwd=ROOT/'.tools/fuse',capture_output=True,timeout=40,startupinfo=startinfo)
    except subprocess.TimeoutExpired as exc:
        print('Timeout',exc.stdout,exc.stderr);raise SystemExit(1)
    if pr.returncode!=42:raise RuntimeError(pr.stdout+pr.stderr)
    nums=[int(x,16) for x in re.findall(rb'^0x([\da-fA-F]+)\s*$',pr.stdout,re.M)]
    pixels+=nums[nums.index(333333)+1:];pcs.append(nums[nums.index(222222)+1])
out=a.folder/('source' if a.snapshot else 'disk')
out=out.with_name(out.name+f'-{a.frames}.png')
render(pixels).save(out);out.with_suffix('.scr').write_bytes(bytes(pixels))
print(str(out),pcs,flush=True)
