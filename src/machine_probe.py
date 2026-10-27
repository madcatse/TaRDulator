"""Observe a disposable copy; never advance the snapshot written to disk."""
import contextlib
import io


def observe(snapshot, frames=100):
    from skoolkit import CSimulator
    from skoolkit.simulator import Simulator
    from skoolkit.simutils import from_snapshot, PC
    from skoolkit.trace import Tracer
    if snapshot.machine != '128K':
        return {'probe_frames': 0, 'runtime_paging': False, 'runtime_ay': False}

    class Observer(Tracer):
        paging = False
        music = False

        def write_port(self, registers, port, value, offset):
            # ROM switching alone (including the 128K USR trampoline) is not
            # evidence. Observe an actual change of RAM bank or screen.
            if port & 0x8002 == 0 and self.out7ffd & 32 == 0:
                self.paging |= bool((value ^ self.out7ffd) & 15)
            if (port & 0xC002 == 0x8000 and self.outfffd < 14
                    and registers[PC] >= 16384):
                self.music |= self.ay[self.outfffd] != value
            super().write_port(registers, port, value, offset)

    simulator = from_snapshot(CSimulator or Simulator, snapshot)
    tracer = Observer(simulator, snapshot.border, snapshot.out7ffd,
                      snapshot.outfffd, list(snapshot.ay), snapshot.outfe, False)
    simulator.set_tracer(tracer)
    with contextlib.redirect_stdout(io.StringIO()):
        tracer.run(snapshot.pc, None, 0, simulator.frame_duration * frames,
                   True, None, None, None, None, '$', '02X', '04X')
    return {'probe_frames': frames, 'runtime_paging': tracer.paging,
            'runtime_ay': tracer.music}
