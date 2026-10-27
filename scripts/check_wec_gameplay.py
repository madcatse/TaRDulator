"""Exercise the verified WEC snapshot with emulated keys, without a tape.

Fuse restoration/startup is checked independently by validate_release06.py.
This check uses SkoolKit's keyboard matrix and never patches game code.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from skoolkit import CSimulator
from skoolkit.snapshot import Snapshot
from skoolkit.simutils import from_snapshot, T, PC
from skoolkit.trace import Tracer
from capture_audit_screens import render


def main():
    rows = json.loads((ROOT/'output/release-0.6/source.json').read_text(encoding='utf-8'))
    row = next(r for r in rows if r['id'] == 13)
    snapshot = Snapshot.get(row['snapshot'])
    simulator = from_snapshot(CSimulator, snapshot)
    tracer = Tracer(simulator, snapshot.border, snapshot.out7ffd, snapshot.outfffd,
                    list(snapshot.ay), snapshot.outfe, False)
    simulator.set_tracer(tracer)
    first = simulator.registers[T] // simulator.frame_duration
    output = ROOT/'output/wec-0.6'
    output.mkdir(parents=True, exist_ok=True)
    images = []
    def draw(screen, frame, border, keyboard):
        frame -= first
        keyboard[:] = [0]*8
        if 200 <= frame < 300:
            keyboard[3] |= 8  # 4: keyboard controls
        if 400 <= frame < 500:
            keyboard[4] |= 1  # 0: start
        if 900 <= frame < 2500:
            keyboard[0] |= 2  # Z
        if frame in (199, 399, 599, 999, 1499, 2499):
            path = output/f'keyboard-{frame}.png'
            render(bytes(screen)).save(path)
            images.append(str(path))
            print(frame, simulator.registers[PC], flush=True)
        return True
    tracer.run(snapshot.pc, None, 0, simulator.frame_duration*2500, True, draw,
               None, None, None, '$', '02X', '04X')
    (output/'keyboard.json').write_text(json.dumps({
        'snapshot': row['snapshot'], 'method': 'SkoolKit keyboard matrix; no tape or code changes',
        'keys': [[200, 300, '4'], [400, 500, '0'], [900, 2500, 'Z']],
        'images': images,
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
