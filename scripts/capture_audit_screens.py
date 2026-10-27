"""Read displayed Spectrum screen memory through Fuse's supported debugger."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,re,sys
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src')]
from check_audit_fuse import run


def render(data):
    image=Image.new('RGB',(256,192));pixels=image.load()
    for y in range(192):
        for x in range(256):
            attr=data[6144+(y//8)*32+x//8]
            value=data[(y//64)*2048+(y%8)*256+((y//8)%8)*32+x//8]
            c=(attr&7) if value&(128>>(x%8)) else ((attr>>3)&7)
            level=255 if attr&64 else 205
            pixels[x,y]=(level if c&2 else 0,level if c&4 else 0,level if c&1 else 0)
    return image


def capture(row,prefix='fuse',output_dir=None):
    data=[];states=[]
    for offset in range(0,6912,2048):
        count=min(2048,6912-offset)
        result=run(row,500,(offset,count))
        assert result['passed'],result
        numbers=[int(v,16) for v in re.findall(r'^0x([a-fA-F0-9]+)\s*$',result['log'],re.M)]
        marker=numbers.index(333333)
        chunk=numbers[marker+1:]
        assert len(chunk)==count,(len(chunk),count)
        states.append(numbers[:marker]);data.extend(chunk)
    # Separate deterministic starts can land a few instructions apart at a
    # frame boundary; record this instead of claiming an exact CPU replay.
    assert all(s[2]==states[0][2] for s in states),states
    assert states[0][2]&8==0,'Shadow screen is active; capture bank 7 instead'
    path=Path(output_dir or ROOT/'output/games48-128')/f"{prefix}-{row['id']:02d}-{row['machine']}.png"
    render(data).save(path)
    path.with_suffix('.scr').write_bytes(bytes(data))
    return {'id':row['id'],'machine':row['machine'],'pc_after':states[0][1],'chunk_pcs':[s[1] for s in states],
            'port_after':states[0][2],'image':str(path),'note':'Four debugger memory chunks from independent starts after 500 frames'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('ids',nargs='*',type=int)
    parser.add_argument('--input',default='best-load.json')
    parser.add_argument('--prefix',default='fuse')
    args=parser.parse_args()
    rows=json.loads((ROOT/'output/games48-128'/args.input).read_text(encoding='utf-8'))
    ids=args.ids
    rows=[r for r in rows if r['machine']=='128' and (not ids or r['id'] in ids)]
    results=[]
    with ThreadPoolExecutor(max_workers=2) as p:
        for job in as_completed([p.submit(capture,r,args.prefix) for r in rows]):
            r=job.result();results.append(r);print(json.dumps(r),flush=True)
    results.sort(key=lambda r:r['id'])
    canvas=Image.new('RGB',(4*272,((len(results)+3)//4)*225),'#333333');draw=ImageDraw.Draw(canvas)
    for n,r in enumerate(results):
        x=(n%4)*272+8;y=(n//4)*225+24
        canvas.paste(Image.open(r['image']),(x,y))
        draw.text((x,y-19),f"{r['id']:02d} Fuse 128K PC={r['pc_after']}",fill='white')
    canvas.save(ROOT/'output/games48-128'/f'{args.prefix}-contact.png')
    (ROOT/'output/games48-128'/f'{args.prefix}-screens.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


if __name__=='__main__':main()
