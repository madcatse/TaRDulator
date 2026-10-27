"""Build clearly marked experimental collections from audited snapshots."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import engine,menu_screen
from skoolkit.snapshot import Snapshot
from skoolkit.tap2sna import _get_tape_blocks


def main():
    output=ROOT/'output/games48-128'
    inventory=json.loads((output/'inventory.json').read_text(encoding='utf-8'))['files']
    loaded=json.loads((output/'best-load.json').read_text(encoding='utf-8'))
    tests=[];reports=[]
    for ext in ('.tap','.tzx'):
        selected=[i for i in inventory if Path(i['path']).suffix==ext and i['id']!=13]
        games=[];files=[]
        for slot,item in enumerate(selected):
            machine='48' if item['id']==9 else '128'
            row=next(r for r in loaded if r['id']==item['id'] and r['machine']==machine)
            assert row['complete']
            tape_blocks=_get_tape_blocks([(item['name'],Path(item['path']).read_bytes())],True,1,0,(),machine=='48')
            effective={b.number for b in tape_blocks if b.data}
            remaining=[b for b in item['blocks'] if b['bytes'] and b['number'] not in effective]
            assert not remaining,(item['name'],remaining)
            stem=f'G{slot:02X}'
            folder=ROOT/'.work/games48-128/collections'/ext[1:]/stem
            folder.mkdir(parents=True,exist_ok=True)
            snapshot=folder/(stem+'.z80');shutil.copyfile(row['snapshot'],snapshot)
            packed,packing=engine.pack_snapshot(snapshot,'preserve' if machine=='128' else 'auto')
            next(f for f in packed if f.kind=='B').name=stem
            files.extend(packed)
            title=item['name'].split(' (')[0].replace(' - Fantasy World Dizzy',' 3').replace(' - Magicland Dizzy',' 4').replace(' - The Movie','')
            if item['id']==5:title='Dizzy 3 (Bruno)'
            if item['id']==6:title='Dizzy 3 RU'
            if item['id']==8:title='Dizzy 4 RU'
            games.append({'id':item['id'],'title':title[:29],'loader':stem,'machine':machine,
                          'source':item['name'],'source_sha256':item['sha256'],'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                          'bytes':sum(f.sectors*256 for f in packed),'loading_timeout':1200 if row['tag']=='long' else 300,
                          'snapshot':str(snapshot),'all_data_blocks_in_load_scope':True})
            tests.append({**row,'snapshot':str(snapshot),'menu_key':engine.KEYS[slot],
                          'directory':str(folder),'disk':str(output/('Test-'+ext[1:].upper()+'.trd'))})
        menu=engine.create_menu_files(engine.builtin_background(),'ТЕСТ '+ext[1:].upper(),games,menu_screen.normalize_pages(None,None,len(games)))
        image=engine.write_trd(menu+files,'AUDIT')
        disk=output/('Test-'+ext[1:].upper()+'.trd');disk.write_bytes(image)
        report={'experimental':True,'engine_version':engine.VERSION,'method':'Prepared audit snapshots; not an unmodified 0.4 GUI build',
                'games':games,'files':len(files+menu),'used_bytes':sum(f.sectors*256 for f in files+menu),
                'sha256':hashlib.sha256(image).hexdigest(),'output':str(disk),
                'limits':'Menu/restore and first-stage checks only. Full playthrough not verified. WEC Le Mans excluded.'}
        disk.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        reports.append(report)
        print(json.dumps({k:v for k,v in report.items() if k!='games'}))
    (output/'collection-cases.json').write_text(json.dumps(tests,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
