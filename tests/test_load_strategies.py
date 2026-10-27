import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import engine
import load_strategies as strategies
import tape_profiles


class StrategyTests(unittest.TestCase):
    def test_initialization_strategy_is_reusable_and_checks_entry(self):
        strategy = strategies.SnapshotStrategy('snapshot-after-initialization', start=32768,
            machine='128', sp=60000, port=16, signatures=((32768, 'f37618fd'),))
        options = strategy.options('128', '0x8000', 'Another game')
        self.assertIn('finish-tape=1', options)
        self.assertEqual(options[options.index('--start')+1], '32768')
        for machine, start in (('48', ''), ('128', '32769')):
            with self.assertRaises(ValueError): strategy.options(machine, start, 'Another game')
        ram = [0]*49152; ram[16384:16388] = bytes.fromhex('f37618fd')
        snapshot = SimpleNamespace(machine='128K', pc=32768, sp=60000, out7ffd=16, ram=lambda:ram)
        strategy.validate(snapshot, 'Another game')
        ram[16384] ^= 1
        with self.assertRaises(ValueError): strategy.validate(snapshot, 'Another game')

    def test_profile_options_override_defaults_and_require_all_tape(self):
        from skoolkit.snapshot import write_snapshot
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d); source=folder/'test.tap';source.write_bytes(b'fixture')
            seen=[]
            def fake(args):
                seen.extend(args)
                write_snapshot(args[-1], [0]*49152, ['pc=32768'], ['iff=0'])
                print('Tape finished')
            with patch('tape_profiles.identify', return_value='fearzone-2018'), patch('tape_profiles.validate',return_value={}), patch('skoolkit.tap2sna.main',side_effect=fake):
                engine.prepare_snapshot(source,folder/'out.z80','48')
            flags=[arg for arg in seen if arg.startswith('in-flags=')]
            self.assertEqual(flags[-1], 'in-flags=2')

    def test_end_of_tape_with_skipped_data_is_not_success(self):
        from skoolkit.snapshot import write_snapshot
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);source=folder/'test.tap';source.write_bytes(b'fixture')
            def fake(args):
                write_snapshot(args[-1],[0]*49152,['pc=32768'],['iff=0'])
                print('Data block (4096 bytes) [skipped]\nTape finished')
            with patch('skoolkit.tap2sna.main',side_effect=fake), self.assertRaisesRegex(ValueError,'пропустил'):
                engine.prepare_snapshot(source,folder/'out.z80','48')

    def test_compact_native_sequencer_scales_without_eating_workspace(self):
        # Same sequencer with an unrelated ten-part program: no per-game code.
        chain=strategies.NativeChain('Synthetic demo', tuple(range(10)), (1,)*10, 24576, 24575,
                                     repeat_from=3, restore_err_nr=244)
        analysis={'path':'not-read.tap','sha256':'test','size':100}
        with patch.dict(strategies.CHAINS, {'test-chain':chain}), patch.object(strategies.NativeChain,'payloads',return_value=[bytes([i]) for i in range(10)]):
            files,info=engine.convert_native_chain({},analysis,'G7F','test-chain')
        self.assertLess(files[0].length,200)
        self.assertEqual([f.name for f in files[1:]], ['G7F.'+chr(65+i) for i in range(10)])
        self.assertEqual([f.data for f in files[1:]], [bytes([i]) for i in range(10)])
        self.assertEqual(info['repeat_from_part'],4)
        self.assertEqual(info['strategy'],'native-basic-chain')
        # LOAD follows REM and ends its line; USR of the part is on another.
        data=files[0].data[:files[0].length];pos=0
        while pos<len(data):
            length=int.from_bytes(data[pos+2:pos+4],'little');line=data[pos+4:pos+4+length]
            if engine.token('REM') in line:
                self.assertTrue(line.endswith(engine.token('CODE')+b'\r'))
            pos+=4+length

    def test_native_parts_validate_headers_not_only_sizes(self):
        chain=strategies.NativeChain('Test',(1,),(4,),25000,24499)
        header=bytearray(19);header[1]=3;header[12:14]=(4).to_bytes(2,'little');header[14:16]=(25000).to_bytes(2,'little')
        blocks=[SimpleNamespace(data=header),SimpleNamespace(data=b'\xffabcd\xff')]
        with patch('skoolkit.tape.parse_tap',return_value=SimpleNamespace(blocks=blocks)):
            self.assertEqual(chain.payloads('test.tap'),[b'abcd'])
            header[14]^=1
            with self.assertRaises(ValueError):chain.payloads('test.tap')

    def test_unsupported_versions_do_not_silently_drop_last_block(self):
        for profile in ('unsupported-castlevania-en','unsupported-castlevania-ru','unsupported-dizzy8'):
            with self.subTest(profile=profile),self.assertRaisesRegex(ValueError,'пока не поддерживается'):
                tape_profiles.options(profile,'128','')
        self.assertEqual(strategies.describe(None)['strategy_match'],'generic')
        self.assertEqual(strategies.describe('dizzy7-unpacked')['strategy'],strategies.describe('yazzie-initialized')['strategy'])

    def test_unsupported_build_marks_row_and_preserves_existing_disk(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'existing.trd';target.write_bytes(b'original disk')
            output=io.StringIO()
            with patch.object(engine,'convert_game',side_effect=tape_profiles.UnsupportedTape('Known unsupported dump')), contextlib.redirect_stdout(output), self.assertRaises(ValueError):
                engine.build({'games':[{'path':'demo.tap'}],'output':str(target),'overwrite':True})
            self.assertEqual(target.read_bytes(),b'original disk')
            events=[json.loads(line) for line in output.getvalue().splitlines()]
            failure=next(e for e in events if e['event']=='game_error')
            self.assertEqual(failure['index'],0)
            self.assertTrue(failure['unsupported'])
            self.assertEqual(failure['message'],'Known unsupported dump')


if __name__=='__main__': unittest.main()
