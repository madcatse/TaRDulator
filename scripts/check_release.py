"""Exercise the frozen engine without an external game collection or Python path."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import engine


def main():
    executable = ROOT / 'dist/TaRDulator/engine/TaRDulator.Engine.exe'
    def checksum(data):
        value = 0
        for byte in data:
            value ^= byte
        return data + bytes([value])
    with tempfile.TemporaryDirectory(dir=ROOT / '.work') as temporary:
        work = Path(temporary)
        tape = work / 'synthetic.tap'
        program = engine.basic_line(10, bytes([226]))  # BASIC STOP
        blocks = [checksum(b'\0\0TEST      ' + struct.pack('<HHH', len(program), 10, len(program))),
                  checksum(b'\xff' + program)]
        tape.write_bytes(b''.join(struct.pack('<H', len(b)) + b for b in blocks))
        original = tape.read_bytes()
        env = {key: value for key, value in os.environ.items() if key not in ('PYTHONPATH', 'PYTHONHOME')}
        env.update(TEMP=temporary, TMP=temporary)
        for mode in ('menu', 'direct'):
            request = {'action': 'build', 'output': str(work / (mode + '.trd')),
                       'launch_mode': mode, 'title': 'SMOKE TEST',
                       'games': [{'path': str(tape), 'title': 'TEST', 'machine': 'auto'}]}
            run = subprocess.run([str(executable)], input=json.dumps(request).encode('ascii'),
                                 capture_output=True, env=env, cwd=work, timeout=120)
            events = [json.loads(line) for line in run.stdout.splitlines()]
            if run.returncode:
                raise RuntimeError({'events': events, 'stderr': run.stderr.decode(errors='replace')})
            actual = next(e for e in events if e['event'] == 'result')
            disk = (work / (mode + '.trd')).read_bytes()
            request.update(action='measure')
            with contextlib.redirect_stdout(io.StringIO()):
                expected = engine.build(request)
            assert actual['version'] == expected['version'] == engine.VERSION
            assert actual['disk_sha256'] == expected['disk_sha256'] == hashlib.sha256(disk).hexdigest()
            assert actual['launch_mode'] == mode
            assert tape.read_bytes() == original
            print('PASS: frozen engine equals source, launch mode=' + mode)
    print('Portable engine smoke checks passed.')


if __name__ == '__main__':
    main()
