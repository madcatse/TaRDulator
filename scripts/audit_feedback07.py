"""Compare new user-supplied demos against the 0.6 conversion path."""
from pathlib import Path
import contextlib
import io
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts'), str(ROOT/'tests')]
import engine
import menu_screen
from skoolkit.tape import parse_tap
from skoolkit.basic import BasicLister
from skoolkit.snapshot import Snapshot
from capture_audit_screens import render, capture
from check_audit_fuse import run

WORK = ROOT/'.work/feedback-0.7'
OUT = ROOT/'output/feedback-0.7'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, path in enumerate(sorted((ROOT/'taps/tricky_roms').glob('*.TAP'))):
        inventory = engine.inspect_tap(path)
        blocks = parse_tap(str(path)).blocks
        basic = [0]*23755 + list(blocks[1].data[1:-1]) + [128]
        basic[23635:23637] = [203,92]
        inventory['basic'] = BasicLister().list_basic(basic)
        print(path.name, inventory['basic'], flush=True)
        (OUT/(path.stem+'-inventory.json')).write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
        for machine in ('48','128'):
            directory = WORK/(path.stem+'-'+machine)
            directory.mkdir(parents=True, exist_ok=True)
            snapshot = directory/'G00.z80'
            row = {'id': i, 'name': path.name, 'machine': machine,
                   'directory': str(directory), 'snapshot': str(snapshot)}
            try:
                info = engine.prepare_snapshot(path, snapshot, machine)
                row['info'] = info
                (directory/'tape.log').write_text(info['log'],encoding='utf-8')
                files, packing = engine.pack_snapshot(snapshot, 'preserve' if machine=='128' else 'auto')
                next(f for f in files if f.kind == 'B').name = 'G00'
                row['packing'] = packing
                menu = engine.create_menu_files(engine.builtin_background(),path.stem,[{'title':path.stem,'loader':'G00'}],menu_screen.normalize_pages(None,None,1))
                disk=directory/'baseline.trd'
                disk.write_bytes(engine.write_trd(menu+files,path.stem))
                row['disk'] = str(disk)
                snap = Snapshot.get(str(snapshot))
                row['sp'] = snap.sp
                render(bytes(snap.ram()[:6912])).save(OUT/(path.stem+'-'+machine+'-snapshot.png'))
                row['fuse'] = run(row)
                row['screen'] = capture(row, prefix='baseline', output_dir=OUT)
            except Exception as error:
                row['error'] = str(error)
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k in ('name','machine','error','sp')}),flush=True)
            print('PC',row.get('info',{}).get('pc'),'Fuse',row.get('fuse',{}).get('passed'),flush=True)
            (OUT/'baseline.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
