import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
import engine
from skoolkit.snapshot import Snapshot
from check_audit_fuse import run
p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
folder=a.out or a.snapshot.parent/'packed';folder.mkdir(parents=True,exist_ok=True)
path=folder/'G00.z80';shutil.copyfile(a.snapshot,path)
try:
    files,info=engine.pack_snapshot(path,'preserve')
    next(f for f in files if f.kind=='B').name='boot'
    disk=folder/'game.trd';disk.write_bytes(engine.write_trd(files,'TRICKY'))
    s=Snapshot.get(str(path));row={'id':0,'snapshot':str(path.resolve()),'disk':str(disk.resolve()),'directory':str(folder.resolve()),'machine':'128' if s.machine=='128K' else '48','menu_key':'','ok':True,'name':a.snapshot.name}
    (folder/'result.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    print(info)
    print(run(row))
except Exception as e: print(type(e).__name__,e)
