import argparse
import contextlib
import io
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from skoolkit import CSimulator
from skoolkit.snapshot import Snapshot,write_snapshot
from skoolkit.simutils import from_snapshot,get_state,PC
from skoolkit.trace import Tracer
from skoolkit.traceutils import disassemble
from capture_audit_screens import render

p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('--frames',type=int,default=0);p.add_argument('--address',type=lambda x:int(x,0));p.add_argument('--size',type=int,default=100);p.add_argument('--key',type=int);a=p.parse_args()
s=Snapshot.get(str(a.snapshot));sim=from_snapshot(CSimulator,s)
tracer=Tracer(sim,s.border,s.out7ffd,s.outfffd,list(s.ay),s.outfe,False)
if a.key is not None:
    tracer.keyboard=[0]*8;tracer.keyboard[7]=1 # SPACE
sim.set_tracer(tracer, True)
if a.frames:
    with contextlib.redirect_stdout(io.StringIO()):
        tracer.run(s.pc,None,0,sim.frame_duration*a.frames,True,None,None,None,None,'$','02X','04X')
    ram,regs,state,machine=get_state(sim)
    out=a.snapshot.with_name(a.snapshot.stem+f'-{a.frames}'+('-key' if a.key is not None else '')+'.z80')
    write_snapshot(str(out),ram,regs,state,machine)
    s=Snapshot.get(str(out))
    ram=s.ram(-1)
    screen=ram[(7 if s.out7ffd&8 else 5)*16384:][:6912] if len(ram)>49152 else ram[:6912]
    render(screen).save(out.with_suffix('.png'))
print('PC',s.pc,'SP',s.sp,'7ffd',s.out7ffd,'IY',s.iy,'IX',s.ix,'HL',s.hl,'BC',s.bc,'DE',s.de)
print('stack',bytes(sim.memory[i%65536] for i in range(s.sp,s.sp+40)).hex())
start=a.address if a.address is not None else max(0,s.pc-20)
end=min(65536,start+a.size)
while start<end:
    text,size=disassemble(sim.memory,start)
    print(f'{start:04X}',text)
    start+=size
