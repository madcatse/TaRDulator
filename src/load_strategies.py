"""Reusable loading mechanisms; tape identity and game-specific data live elsewhere.

Strategies never guess that a missing block is optional. A tape profile opts
into a mechanism only after its entry point and resident data are verified.
"""
from dataclasses import dataclass
from localization import tr


@dataclass(frozen=True)
class CodePatch:
    address: int
    before: str
    after: str

    def __post_init__(self):
        before, after = bytes.fromhex(self.before), bytes.fromhex(self.after)
        if not (16384 <= self.address < self.address + len(before) <= 65536
                and 0 < len(after) <= len(before)):
            raise ValueError('Invalid resident code patch')


# Same 1536-iteration delay as CASTESCD.trd (tiboh, 2023), with an early RET
# instead of the demo's ten padding NOPs. It never reads a floating-bus port.
ESCAPE_DELAY = '1100061b7ab320fbc9'


@dataclass(frozen=True)
class SnapshotStrategy:
    family: str
    in_flags: int = 4
    start: int | None = None
    machine: str | None = None
    sp: int | None = None
    port: int | None = None
    signatures: tuple = ()
    patches: tuple = ()

    def options(self, machine, start, label):
        if self.machine and machine != self.machine:
            raise ValueError(tr('{0}: требуется {1}К.', label, self.machine))
        if self.start is not None and start:
            value = int(start, 16 if start.lower().startswith('0x') else 10)
            if value != self.start:
                raise ValueError(tr('{0}: проверенный адрес старта — {1}. Оставьте поле старта пустым.', label, self.start))
        args = ['-c', f'in-flags={self.in_flags}']
        if self.start is not None:
            args += ['--start', str(self.start), '-c', 'finish-tape=1']
        return args

    def validate(self, snapshot, label):
        ram = snapshot.ram()
        checks = [self.machine is None or snapshot.machine == self.machine+'K',
                  self.start is None or snapshot.pc == self.start,
                  self.sp is None or snapshot.sp == self.sp,
                  self.port is None or snapshot.out7ffd == self.port]
        checks += [bytes(ram[address-16384:address-16384+len(bytes.fromhex(data))]) == bytes.fromhex(data)
                   for address, data in (*self.signatures, *((p.address, p.before) for p in self.patches))]
        if not all(checks):
            raise ValueError(tr('{0}: проверка точки сохранения не пройдена; образ не создан.', label))

    def adapt(self, snapshot, label):
        # Validate every original signature before changing any memory. Addressed
        # writes preserve all CPU state and correctly map 48K/128K physical RAM.
        self.validate(snapshot, label)
        result = []
        for patch in self.patches:
            data = bytes.fromhex(patch.after)
            snapshot.memory[patch.address:patch.address+len(data)] = data
            result.append({'address': patch.address, 'before': patch.before,
                           'after': patch.after, 'bytes_written': len(data)})
        return result


@dataclass(frozen=True)
class NativeChain:
    label: str
    blocks: tuple
    sizes: tuple
    address: int
    clear: int
    repeat_from: int = 0
    restore_err_nr: int | None = None
    required_machine: str | None = None

    def payloads(self, path):
        from skoolkit.tape import parse_tap
        blocks = parse_tap(str(path)).blocks
        result = []
        for index, size in zip(self.blocks, self.sizes):
            if index >= len(blocks) or index == 0:
                raise ValueError(tr('{0}: неверная структура цепочки частей.', self.label))
            header, data = bytes(blocks[index-1].data), bytes(blocks[index].data)
            if (len(header) != 19 or header[:2] != b'\0\3' or data[0] != 255
                    or len(data)-2 != size or int.from_bytes(header[12:14], 'little') != size
                    or int.from_bytes(header[14:16], 'little') != self.address):
                raise ValueError(tr('{0}: неверная структура цепочки частей.', self.label))
            result.append(data[1:-1])
        return result


SNAPSHOTS = {
    'escape-castle-no-floating-bus': SnapshotStrategy('snapshot-with-compatibility-patch',
        signatures=((0x87E2, 'cdb089'),), patches=(CodePatch(0x89B0,
            '3a530bfe7e280c1140022b7bdbffbac2ba89c9', ESCAPE_DELAY),)),
    'escape-forest-no-floating-bus': SnapshotStrategy('snapshot-with-compatibility-patch',
        signatures=((0x86B0, 'cd2496'),), patches=(CodePatch(0x9624,
            '573a530bfe7eca38961e402b7bdbffbac22f96c9', ESCAPE_DELAY),)),
    'escape-pyramid-no-floating-bus': SnapshotStrategy('snapshot-with-compatibility-patch',
        signatures=((0x876C, 'cd6893'),), patches=(CodePatch(0x9368,
            '573a530bfe7e280b1e402b7bdbffbac27293c9', ESCAPE_DELAY),)),
    # Suppress keyboard INs as tape reads, retain ROM's real LOADs.
    'fearzone-2018': SnapshotStrategy('rom-load-keyboard-safe', in_flags=2),
    # Both games use the same mechanism: reach a verified stable entry point.
    'dizzy7-unpacked': SnapshotStrategy('snapshot-after-initialization', start=29437,
        machine='128', sp=49152, signatures=((29437, '7621fc72e521067306'),)),
    'yazzie-initialized': SnapshotStrategy('snapshot-after-initialization', start=24573,
        machine='128', sp=24499, port=16, signatures=((24573, '76cd5e7dcd9d8520f7'),)),
}

CHAINS = {
    'milky2-disk-chain': NativeChain('MILKY2', (3, 5), (6400, 26112), 25000, 24499,
                                    repeat_from=1, required_machine='128'),
    'new-view-disk-chain': NativeChain('New View', (3, 5, 7, 9, 11),
        (37662, 14009, 3626, 11997, 8052), 24576, 24575, restore_err_nr=244),
}

FAMILY_NAMES = {
    'snapshot-with-compatibility-patch': 'Снимок с проверенным исправлением совместимости',
    'snapshot': 'Обычный снимок после загрузки',
    'rom-load-keyboard-safe': 'ROM-загрузка с отдельным опросом клавиатуры',
    'snapshot-after-initialization': 'Снимок после распаковки и инициализации',
    'native-basic-chain': 'Последовательные части с загрузкой через TR-DOS',
    'verified-resident-branch': 'Проверенная ветка загрузки в память',
    'unresolved-late-data': 'Необработанные блоки после запуска программы',
}


def describe(profile):
    if profile in SNAPSHOTS: family = SNAPSHOTS[profile].family
    elif profile in CHAINS: family = 'native-basic-chain'
    elif profile == 'wec-le-mans-128': family = 'verified-resident-branch'
    elif profile and profile.startswith('unsupported-'): family = 'unresolved-late-data'
    else: family = 'snapshot'
    return {'strategy': family, 'strategy_name': tr(FAMILY_NAMES[family]),
            'strategy_match': 'verified-sha256' if profile else 'generic'}
