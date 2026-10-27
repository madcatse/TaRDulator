"""Local diagnostics for the new sample tapes (not shipped game data)."""
import argparse
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests'), str(ROOT/'scripts')]
from skoolkit.snapshot import Snapshot
from capture_audit_screens import render, capture
from check_audit_fuse import run


def main():
    p=argparse.ArgumentParser(); p.add_argument('directory',type=Path); p.add_argument('--fuse',action='store_true'); p.add_argument('--screens',action='store_true'); p.add_argument('--ids',nargs='*',type=int)
    args=p.parse_args()
    rows=json.loads((args.directory/'results.json').read_text(encoding='utf-8'))
    results=[]
    for i,row in enumerate(rows):
        if args.ids is not None and i not in args.ids: continue
        folder=args.directory/f'{i:02d}'
        for path in sorted((folder/'G00').glob('**/*.z80')):
            s=Snapshot.get(str(path)); ram=s.ram(-1)
            screen=ram[(7 if s.out7ffd&8 else 5)*16384:][:6912] if len(ram)>49152 else ram[:6912]
            render(screen).save(path.with_suffix('.png'))
            if path.parent.name=='G00': print(row['name'],s.machine,'pc',s.pc,'sp',s.sp,'7ffd',s.out7ffd,flush=True)
        if not row['ok'] or not Path(row.get('snapshot','')).is_file(): continue
        if args.fuse:
            result=run(row)
            results.append({'name':row['name'],**result})
            print('FUSE',row['name'],result.get('passed'),result.get('log',result.get('error')),flush=True)
        if args.screens:
            try: print(capture(row,prefix='disk',output_dir=folder),flush=True)
            except Exception as e: print('SCREEN ERROR',str(e),flush=True)
        (args.directory/'fuse-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__': main()
