"""Reproducible local compatibility audit; one converter process per tape."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def inventory(path):
    data = path.read_bytes()
    blocks, pos = [], 0
    while pos + 2 <= len(data):
        size = int.from_bytes(data[pos:pos+2], 'little')
        payload = data[pos+2:pos+2+size]
        checksum = 0
        for b in payload: checksum ^= b
        blocks.append({'number': len(blocks)+1, 'offset': pos, 'size': size,
                       'flag': payload[0] if payload else None, 'xor': checksum,
                       'head': payload[:20].hex()})
        pos += size + 2
    return {'name': path.name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'blocks': blocks, 'end': pos}


def worker(path, directory):
    import engine
    directory.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = inventory(path)
    try:
        files, info = engine.convert_game({'path': str(path), 'title': path.stem,
            'machine': 'auto', 'transfer_mode': 'auto'}, 0, directory)
        next(f for f in files if f.kind == 'B').name = 'boot'
        disk = directory / 'game.trd'
        disk.write_bytes(engine.write_trd(files, 'TRICKY'))
        result.update(ok=True, info=info, disk=str(disk), directory=str(directory),
                      snapshot=str(directory/'G00/G00.z80'), machine=info['load_machine'],
                      id=0, menu_key='')
    except Exception as exc:
        result.update(ok=False, error=str(exc), error_type=type(exc).__name__)
    result['seconds'] = round(time.monotonic()-started, 2)
    (directory / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.out)
        return
    paths = sorted((ROOT/'taps/tricky_roms').glob('*.[tT][aA][pP]'))
    if args.names: paths = [p for p in paths if p.name in args.names]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'inventory.json').write_text(json.dumps([inventory(p) for p in paths], indent=2), encoding='utf-8')
    def run(pair):
        index, path = pair
        folder = args.out / f'{index:02d}'
        folder.mkdir(exist_ok=True)
        with (folder/'console.log').open('wb') as log:
            proc = subprocess.run([sys.executable, __file__, '--worker', str(path), '--out', str(folder)],
                stdout=log, stderr=subprocess.STDOUT, timeout=360, creationflags=subprocess.CREATE_NO_WINDOW)
        result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
        print(path.name, 'OK' if result['ok'] else result.get('error', '')[-900:], result['seconds'], flush=True)
        return result
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(run, enumerate(paths)):
            results.append(result)
            (args.out/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
