import argparse
import contextlib
import io
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'), str(ROOT/'scripts')]
from skoolkit import tap2sna
from skoolkit.snapshot import Snapshot
from capture_audit_screens import render

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--settle',type=float,default=0);p.add_argument('tape',type=Path);p.add_argument('out',type=Path);p.add_argument('options',nargs=argparse.REMAINDER)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    import os,shutil
    shutil.copyfile(a.tape,a.out/'input.tap');os.chdir(a.out)
    log=io.StringIO()
    if a.settle:
        original=tap2sna.LoadTracer
        class Settled(original):
            def run(self,*args):
                super().run(*args)
                if self.state[2] and self.stop is None:
                    self.stop=65537
                    self.timeout=self.simulator.registers[25]+int(3500000*a.settle)
                    super().run(self.border,self.out7ffd,self.outfffd,self.ay,self.outfe)
        tap2sna.LoadTracer=Settled
    with contextlib.redirect_stdout(log):
        tap2sna.main(['-c','machine=128','-c','in-flags=5','-c','timeout=1200']+a.options+['input.tap','game.z80'])
    clean=re.sub(r'\[[\s\d.]+%\]|\x08','',log.getvalue())
    Path('load.log').write_text(clean,encoding='utf-8');print(clean)
    s=Snapshot.get('game.z80');ram=s.ram(-1)
    screen=ram[(7 if s.out7ffd&8 else 5)*16384:][:6912] if len(ram)>49152 else ram[:6912]
    render(screen).save('game.png')
