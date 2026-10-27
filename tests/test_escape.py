"""Regression: Escape's sprite loop must progress without a floating bus."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import engine
import load_strategies
import tape_profiles
from skoolkit import CSimulator
from skoolkit.snapshot import Snapshot, Z80
from skoolkit.simutils import from_snapshot, T
from skoolkit.trace import Tracer

CASES = (
    ('Castle Escape.tap', 'escape-castle-no-floating-bus', 0x87E5),
    ('ForestEscape.tap', 'escape-forest-no-floating-bus', 0x86B3),
    ('PyramidEscape.tap', 'escape-pyramid-no-floating-bus', 0x876F),
)


def exercise(snapshot, bus=255, frames=2150, capture=None):
    """Ordinary keys and open-bus reads; no game variables/PC are forced."""
    class NoFloatingBus(Tracer):
        bus_reads = 0

        def read_port(self, registers, port):
            if port & 255 == 255:
                self.bus_reads += 1
                return bus
            return super().read_port(registers, port)

    simulator = from_snapshot(CSimulator, snapshot)
    tracer = NoFloatingBus(simulator, snapshot.border, snapshot.out7ffd,
                          snapshot.outfffd, list(snapshot.ay), snapshot.outfe, False)
    simulator.set_tracer(tracer)
    first = simulator.registers[T] // simulator.frame_duration
    screens = {}

    def draw(screen, frame, border, keyboard):
        frame -= first
        keyboard[:] = [0]*8
        if 700 <= frame < 715 or 900 <= frame < 915:
            keyboard[4] = 1  # 0: play
        if 1700 <= frame < 1730:
            keyboard[5] = 1  # P: right
        if 1720 <= frame < 1730:
            keyboard[7] = 4  # M: jump
        if frame in (1600, 1800, 2100):
            screens[frame] = bytes(screen)
            if capture:
                capture(bytes(screen), frame)
        return True

    executed = set()
    with contextlib.redirect_stdout(io.StringIO()):
        tracer.run(snapshot.pc, None, 0, simulator.frame_duration*frames,
                   True, draw, executed, None, None, '$', '02X', '04X')
    return {'executed': executed, 'bus_reads': tracer.bus_reads, 'screens': screens}


class EscapePatchTests(unittest.TestCase):
    def test_signatures_are_checked_before_any_write(self):
        a = load_strategies.CodePatch(0x8000, '11223344', 'c9')
        b = load_strategies.CodePatch(0x8010, '55667788', '00')
        strategy = load_strategies.SnapshotStrategy('test', patches=(a, b))
        snapshot = Z80(ram=[0]*49152)
        snapshot.memory[0x8000:0x8004] = bytes.fromhex(a.before)
        before = snapshot.ram()
        with self.assertRaises(ValueError):
            strategy.adapt(snapshot, 'Test')
        self.assertEqual(snapshot.ram(), before)

    def test_patches_never_cross_rom_or_memory_boundaries(self):
        for address, before, after in ((0x3FFF, '00', 'c9'), (0xFFFF, '0000', 'c9'),
                                       (0x8000, '00', '0000')):
            with self.assertRaises(ValueError):
                load_strategies.CodePatch(address, before, after)

    def test_unknown_or_changed_tapes_are_not_patched(self):
        with tempfile.TemporaryDirectory() as d:
            for name, profile, _ in CASES:
                path = Path(d)/name
                source = ROOT/'taps/escape_trilogy'/name
                path.write_bytes(source.read_bytes()+b'changed' if source.exists() else b'unknown')
                self.assertIsNone(tape_profiles.identify(path))
            snapshot = Z80(ram=[0]*49152)
            before = snapshot.data()
            self.assertEqual(tape_profiles.adapt_snapshot(None, snapshot), {})
            self.assertEqual(snapshot.data(), before)

    @unittest.skipUnless(CSimulator, 'SkoolKit C simulator required for gameplay regression')
    def test_real_tapes_progress_with_sprites_without_floating_bus(self):
        if not all((ROOT/'taps/escape_trilogy'/name).exists() for name, _, _ in CASES):
            self.skipTest('Local Escape tapes are not distributed with the source')
        for name, profile, after_wait in CASES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                directory = Path(d)
                source = ROOT/'taps/escape_trilogy'/name
                self.assertEqual(tape_profiles.identify(source), profile)
                # The generic snapshot is our negative control. Same tape,
                # same CPU state, same banks, no hardware compatibility patch.
                with patch('tape_profiles.identify', return_value=None):
                    engine.prepare_snapshot(source, directory/'original.z80', '128')
                original = Snapshot.get(str(directory/'original.z80'))
                with contextlib.redirect_stdout(io.StringIO()):
                    info = engine.prepare_snapshot(source, directory/'fixed.z80', '128')
                fixed = Snapshot.get(str(directory/'fixed.z80'))
                self.assertEqual(original.header, fixed.header)
                changes = [i for i, (a,b) in enumerate(zip(original.ram(-1), fixed.ram(-1))) if a != b]
                spec = load_strategies.SNAPSHOTS[profile].patches[0]
                expected = [2*16384+spec.address-0x8000+i for i, value in enumerate(bytes.fromhex(spec.after))
                            if value != bytes.fromhex(spec.before)[i]]
                self.assertEqual(changes, expected)
                self.assertEqual(info['compatibility_patches'][0]['address'], spec.address)
                bad = exercise(original)
                self.assertNotIn(after_wait, bad['executed'])
                self.assertGreater(bad['bus_reads'], 1000)
                for bus in (255, 0):
                    good = exercise(fixed, bus)
                    self.assertIn(after_wait, good['executed'])
                    self.assertEqual(good['bus_reads'], 0)
                    self.assertNotEqual(good['screens'][1600], good['screens'][1800])
                    self.assertGreater(sum(bool(b) for b in good['screens'][2100][:6144]), 500)


if __name__ == '__main__':
    unittest.main()
