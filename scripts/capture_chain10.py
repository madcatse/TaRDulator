"""Capture the last native part, after verifying all preceding part entries."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from validate_tricky10 import ROOT, OUT, chain_commands
sys.path.insert(0, str(ROOT/'scripts'))
from capture_audit_screens import render

p=argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--frames', type=int, default=500)
a=p.parse_args()
row=next(r for r in json.loads((OUT/'fuse.json').read_text(encoding='utf-8'))
         if r['name']==a.name and r['mode']=='direct')
pixels=[]
startup=subprocess.STARTUPINFO();startup.dwFlags=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
for offset in range(0,6912,1024):
    screen='print 333333\n'+'\n'.join(f'print [{16384+n}]' for n in range(offset,min(6912,offset+1024)))
    cmd=chain_commands(row,a.frames).replace('exit 42\n',
        'print z80:sp\nprint [65535]\n'+screen+'\nexit 42\n')
    proc=subprocess.run([str(ROOT/'.tools/fuse/fuse.exe'),'--machine','pentagon','--no-sound',
        '--speed','5000','--debugger-command',cmd,row['disk']],cwd=ROOT/'.tools/fuse',
        capture_output=True,timeout=90,startupinfo=startup)
    assert proc.returncode==42,proc.stderr
    nums=[int(x,16) for x in re.findall(rb'^0x([\da-fA-F]+)\s*$',proc.stdout,re.M)]
    pos=nums.index(333333)
    print('state',nums[:pos],flush=True)
    pixels.extend(nums[pos+1:])
target=OUT/(Path(a.name).stem+f'-last-{a.frames}.png')
render(pixels).save(target)
target.with_suffix('.scr').write_bytes(bytes(pixels))
print(target,flush=True)
