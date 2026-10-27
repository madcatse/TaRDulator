"""Exercise normal keyboard input after tape loading; no game-code patches."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from skoolkit import CSimulator
from skoolkit.snapshot import Snapshot,write_snapshot
from skoolkit.simutils import from_snapshot,get_state,T,PC
from skoolkit.trace import Tracer
from capture_audit_screens import render

KEYS={'1':(3,1),'0':(4,1),'4':(3,8),'enter':(6,1),'space':(7,1)}


def exercise(row):
    s=Snapshot.get(row['snapshot'])
    simulator=from_snapshot(CSimulator,s)
    tracer=Tracer(simulator,s.border,s.out7ffd,s.outfffd,list(s.ay),s.outfe,False)
    simulator.set_tracer(tracer)
    first=simulator.registers[T]//simulator.frame_duration
    index=row['id']
    schedule=[(400,410,'space')]
    if index in (0,1):schedule=[(400,410,'1'),(500,510,'space'),(850,860,'space')]
    if index in (2,3):schedule=[(400,410,'enter'),(500,510,'1'),(600,610,'space'),(700,710,'0')]
    if index==9:schedule=[(400,410,'space'),(500,510,'1')]
    if index==12:schedule=[(400,410,'space'),(600,610,'1'),(850,860,'space'),(1750,1760,'space'),(2300,2310,'space')]
    if index==13:schedule=[(400,410,'4'),(500,510,'0')]
    images=[]
    def draw(scr,frame,border,keyboard):
        f=frame-first
        keyboard[:]=[0]*8
        for start,end,key in schedule:
            if start<=f<end:
                k,bit=KEYS[key];keyboard[k]|=bit
        if f in (399,499,749,999,1499,2499,2999):
            image=ROOT/'output/games48-128'/f"play-{index:02d}-{row['machine']}-{f}.png"
            render(bytes(scr)).save(image);images.append(str(image))
        return True
    frames=3000 if index in (2,3,12) else 1500
    tracer.run(s.pc,None,0,simulator.frame_duration*frames,True,draw,None,None,None,'$','02X','04X')
    memory,registers,state,machine=get_state(simulator)
    path=Path(row['directory'])/'playing.z80'
    write_snapshot(str(path),memory,registers,state,machine)
    return {'id':index,'machine':row['machine'],'keys':schedule,'frames':frames,'images':images,'pc':simulator.registers[PC],
            'snapshot':str(path),'method':'SkoolKit keyboard matrix; no tape, no game code changes'}


def main():
    rows=json.loads((ROOT/'output/games48-128/best-load.json').read_text(encoding='utf-8'))
    result_file=ROOT/'output/games48-128/keyboard-checks.json'
    results=json.loads(result_file.read_text(encoding='utf-8')) if result_file.exists() else []
    selected=[int(x) for x in sys.argv[1:]]
    for row in rows:
        if row['machine']!='128' or (selected and row['id'] not in selected):continue
        result=exercise(row)
        results=[r for r in results if (r['id'],r['machine'])!=(result['id'],result['machine'])]
        results.append(result);results.sort(key=lambda r:r['id']);print(json.dumps(result),flush=True)
        (ROOT/'output/games48-128/keyboard-checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    from PIL import Image,ImageDraw
    canvas=Image.new('RGB',(4*272,4*225),'#333333');d=ImageDraw.Draw(canvas)
    for n,r in enumerate(results):
        x=(n%4)*272+8;y=(n//4)*225+24
        canvas.paste(Image.open(r['images'][-1]),(x,y));d.text((x,y-19),f"{r['id']:02d} After normal keys",fill='white')
    canvas.save(ROOT/'output/games48-128/playing-contact.png')


if __name__=='__main__':main()
