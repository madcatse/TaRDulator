import argparse
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src')]
from skoolkit.snapshot import Snapshot
from check_pages_fuse import commands_for, run
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--begin',type=int,default=23296);p.add_argument('--end',type=int,default=25000);a=p.parse_args()
row=json.loads((a.folder/'result.json').read_text(encoding='utf-8'));s=Snapshot.get(row['snapshot']);ram=s.ram()
checks=' && '.join(f'z80:{reg} == {getattr(s,reg)}' for reg in ('sp','bc','de','hl','ix','iy'))
for start in range(a.begin,a.end,800):
    addresses=range(start,min(start+800,a.end))
    finish='print 333333\n'+'\n'.join(f'print ({i} * ([{i}] != {ram[i-16384]}))' for i in addresses)+'\nexit 42'
    result=run(row['disk'],commands_for('',finish,True,f'{s.pc} if '+checks))
    # run() intentionally suppresses successful logs, request a nonzero audit code.
    finish=finish.replace('exit 42','exit 41')
    result=run(row['disk'],commands_for('',finish,True,f'{s.pc} if '+checks))
    nums=[int(x,16) for x in re.findall(r'^0x([\da-fA-F]+)\s*$',result.get('log',''),re.M)]
    print(start,[n for n in nums[nums.index(333333)+1:] if n] if 333333 in nums else result,flush=True)
