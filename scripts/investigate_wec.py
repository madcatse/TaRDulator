"""Load the supplied WEC tape past its stop, without altering the input."""
from pathlib import Path
import hashlib, json, os, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from skoolkit.tape import parse_tzx
from skoolkit.snapshot import Snapshot
from capture_audit_screens import render

source = next((ROOT/'.work/games48-128/input').glob('WEC*.tzx'))
blocks = parse_tzx(str(source), info=True, timings=True).blocks
out = ROOT/'output/wec-0.6'
out.mkdir(parents=True, exist_ok=True)
inventory = []
for b in blocks:
    inventory.append({'number': b.number, 'id': b.block_id, 'bytes':len(b.data or ()),
                      'info':b.info,
                      'sha256':hashlib.sha256(bytes(b.data)).hexdigest() if b.data else ''})
(out/'blocks.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')
for row in inventory:
    print(row, flush=True)
for machine in ('128','48'):
    work = ROOT/'.work/wec-0.6'/('full'+machine)
    work.mkdir(parents=True,exist_ok=True)
    (work/'input.tzx').write_bytes(source.read_bytes())
    args = [sys.executable,'-c','import sys;from skoolkit.tap2sna import main;main(sys.argv[1:])',
            '-c','machine='+machine,'-c','timeout=1200','--tape-stop',str(len(blocks)+1),'input.tzx','G00.z80']
    p=subprocess.run(args,cwd=work,capture_output=True,timeout=120,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    log=(p.stdout+p.stderr).decode('utf-8','replace')
    (work/'load.log').write_text(log,encoding='utf-8')
    print(machine,log[-600:],flush=True)
    if (work/'G00.z80').exists():
        s=Snapshot.get(str(work/'G00.z80'))
        render(bytes(s.ram()[:6912])).save(out/('full'+machine+'.png'))
        print('snapshot',machine,s.pc,s.out7ffd,flush=True)
