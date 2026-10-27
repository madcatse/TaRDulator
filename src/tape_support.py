"""Strict validation of the TZX subset executed by SkoolKit 10.1."""

from localization import tr
from pathlib import Path


def tzx_blocks(data):
    # Use the same timing parser as the emulator, with explicit bounds checks:
    # parse_tzx itself permits a short final payload and ignores some controls.
    from skoolkit.tape import _get_tzx_block
    if len(data) < 10 or data[:8] != b"ZXTape!\x1a" or data[8] != 1:
        raise ValueError(tr('Неверный заголовок или неподдерживаемая версия TZX'))
    blocks, pos, loop = [], 10, None
    expanded_bytes = expanded_blocks = 0
    allowed = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x20, 0x21, 0x22,
               0x24, 0x25, 0x2A, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x5A}
    while pos < len(data):
        if data[pos] not in allowed:
            raise ValueError(tr('Блок TZX 0x{0:02X} пока не поддерживается загрузчиком', data[pos]))
        try:
            end, block = _get_tzx_block(data, pos, len(blocks)+1, False, True)
            if end <= pos or end > len(data):
                raise ValueError(tr('Оборванный блок TZX'))
            if block.timings and block.timings.error:
                raise ValueError(block.timings.error)
            if block.block_id == 0x24:
                if loop is not None:
                    raise ValueError(tr('Вложенные циклы TZX пока не поддерживаются'))
                repetitions = int.from_bytes(block.block_data, "little")
                if not repetitions:
                    raise ValueError(tr('Нулевое число повторений TZX'))
                loop = (len(blocks), repetitions)
            elif block.block_id == 0x25:
                if loop is None:
                    raise ValueError(tr('Конец цикла TZX без начала'))
                index, repetitions = loop
                expanded_blocks += (len(blocks)-index+1) * (repetitions-1)
                expanded_bytes += sum(len(b.data or ()) for b in blocks[index:]) * (repetitions-1)
                loop = None
            expanded_bytes += len(block.data or ())
            expanded_blocks += 1
            if expanded_blocks > 10000 or expanded_bytes > 64*1024*1024:
                raise ValueError(tr('Слишком много повторяемых данных TZX'))
            blocks.append(block)
            pos = end
        except (IndexError, TypeError) as exc:
            raise ValueError(tr('Оборванный или некорректный блок TZX')) from exc
    if loop is not None:
        raise ValueError(tr('Незавершённый цикл TZX'))
    if not any(b.data for b in blocks):
        raise ValueError(tr('В TZX нет данных для загрузки'))
    return blocks


def remaining_after_stop(path: Path, machine: str):
    if path.suffix.lower() != ".tzx":
        return []
    from skoolkit.tap2sna import _get_tzx_blocks
    data = path.read_bytes()
    blocks = tzx_blocks(data)
    _, effective = _get_tzx_blocks(data, True, 1, 0, (), machine == "48")
    included = {b.number for b in effective}
    return [b.number for b in blocks if b.number not in included and
            (b.data or (b.timings and b.block_id in (0x12, 0x13, 0x15)))]
