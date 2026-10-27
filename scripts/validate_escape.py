"""Build Escape hardware-test disks and reproduce the missing-floating-bus failure.

Requires the user's local taps/escape_trilogy inputs; no game data is shipped.
The probe models the relevant bus behavior, not a complete Delta-S motherboard.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests'), str(ROOT/'scripts')]
import engine
from test_escape import CASES, exercise
from skoolkit import CSimulator
from skoolkit.snapshot import Snapshot, write_snapshot
from skoolkit.simutils import from_snapshot, get_state, PC, SP, H, L, B
from skoolkit.trace import Tracer
from capture_audit_screens import render


def inspect_demo(folder, seed):
    path = ROOT/'taps/escape_trilogy/CASTESCD.trd'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != 'c895048f00675af46244ead95c4a16cf11746af5e3f4ffd59004de8fde7cee9a':
        raise ValueError('CASTESCD.trd differs from the analyzed reference')
    data = next(f.data for f in engine.read_trd(path.read_bytes()) if f.name == 'CASTESCD')
    # Execute the demo's original depacker. Substitute only its four sector
    # reads, preserving their destination, count and bank; no game patches.
    sim = from_snapshot(CSimulator, seed, registers={'PC':0x5D7B, 'SP':0x7FFF})
    for bank in sim.memory.banks:
        bank[:] = [0]*16384
    sim.memory.out7ffd(16)
    tracer = Tracer(sim, 0, 16, 0, [0]*16, 0, False)
    sim.set_tracer(tracer)
    for i, value in enumerate(data[:256]):
        sim.memory[23867+i] = value
    position = 256
    for count in (1,12,28,99):
        sim.run(stop=0x5DC8)
        r = sim.registers
        address = r[H]*256+r[L]
        assert r[B] == count
        for i, value in enumerate(data[position:position+count*256]):
            sim.memory[address+i] = value
        position += count*256
        r[PC] = sim.memory[r[SP]]+256*sim.memory[r[SP]+1]
        r[SP] += 2
    sim.run(stop=0x86BD)
    assert position == len(data)
    expected = bytes.fromhex('1100061b7ab320fb'+'00'*10+'c9')
    actual = bytes(sim.memory[a] for a in range(0x89C1,0x89C1+len(expected)))
    assert actual == expected
    ram, registers, state, machine = get_state(sim)
    write_snapshot(str(folder/'reference-demo.z80'),ram,registers,state,machine)
    return {'sha256':digest, 'wait_address':0x89C1, 'wait_bytes':actual.hex(),
            'credit':"TRD by tiboh'23", 'delay_iterations':1536,
            'method':'Original depacker executed; four disk-sector reads supplied from the TRD'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'output/escape-fixed')
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    report = {'version':engine.VERSION, 'games':[],
              'hardware_verified':False, 'full_delta_emulation':False,
              'method':'SkoolKit 10.1; unassigned port FF returns constant FF or 00; normal play/right/jump keys'}
    with tempfile.TemporaryDirectory(prefix='escape-',dir=ROOT/'.work') as tmp:
        work = Path(tmp)
        for index,(name,profile,after_wait) in enumerate(CASES):
            source = ROOT/'taps/escape_trilogy'/name
            original_dir = work/f'original-{index}'; original_dir.mkdir()
            with patch('tape_profiles.identify',return_value=None):
                engine.prepare_snapshot(source,original_dir/'game.z80','128')
            original = Snapshot.get(str(original_dir/'game.z80'))
            if index == 0:
                report['reference_demo'] = inspect_demo(out,original)
            with contextlib.redirect_stdout(io.StringIO()):
                files, info = engine.convert_game({'path':str(source),'machine':'auto'},index,work)
            snapshot = Snapshot.get(str(work/f'G{index:02X}'/f'G{index:02X}.z80'))
            slug = ('CastleEscape','ForestEscape','PyramidEscape')[index]
            snapshot.write(str(out/f'{slug}-fixed.z80'))
            next(f for f in files if f.kind == 'B').name = 'boot'
            disk = out/f'{slug}-fixed.trd'
            disk.write_bytes(engine.write_trd(files,slug))
            engine.read_trd(disk.read_bytes())
            before = exercise(original)
            assert after_wait not in before['executed'] and before['bus_reads'] > 1000
            render(before['screens'][2100]).save(out/f'{slug}-before.png')
            checks = []
            for bus in (255,0):
                capture = lambda data,frame: render(data).save(out/f'{slug}-after-{frame}.png')
                after = exercise(snapshot,bus,capture=capture if bus==255 else None)
                assert after_wait in after['executed'] and after['bus_reads']==0
                assert after['screens'][1600] != after['screens'][1800]
                checks.append({'unassigned_port_value':bus,'passed_wait':True,
                               'floating_bus_reads':after['bus_reads'],'screen_changes':True})
            report['games'].append({'name':name,'conversion':info,'disk':str(disk),
                'disk_sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
                'original_floating_bus_reads':before['bus_reads'],'checks':checks})
            print(slug, 'PASS',flush=True)
        collection = engine.build({'games':[{'path':str(ROOT/'taps/escape_trilogy'/name)}
                                  for name,_,_ in CASES], 'title':'ESCAPE TRILOGY',
                                  'output':str(out/'EscapeTrilogy-fixed.trd'),'overwrite':True})
        report['collection'] = collection['output']
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',out,flush=True)


if __name__ == '__main__':
    main()
