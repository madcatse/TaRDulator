"""TaRDulator conversion engine. JSON request on stdin; NDJSON events on stdout.

Tape execution: SkoolKit 10.1. Snapshot restoration: Z80to 1.4.
This module owns validation, naming, disk assembly and the Spectrum menu.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from localization import tr, set_language
import menu_screen
import tape_support
import tape_profiles
import machine_probe
import load_strategies

from app_version import VERSION
LOAD_TIMEOUT = 1200  # Spectrum seconds; simulation usually runs much faster.
DISK_SIZE = 655360
SECTOR_SIZE = 256
PAGE_SIZE = menu_screen.PAGE_SIZE
KEYS = "123456789ABCDEFG"
TOKENS = {"CODE": 175, "VAL": 176, "USR": 192, "INKEY$": 166, "CHR$": 194, "PEEK": 190,
          "AT": 172, "THEN": 203, "OR": 197, "BORDER": 231,
          "REM": 234, "LOAD": 239, "LET": 241, "PAUSE": 242,
          "PRINT": 245, "RANDOMIZE": 249, "CLS": 251,
          "CLEAR": 253, "IF": 250, "GO TO": 236,
          "PAPER": 218, "INK": 217, "BRIGHT": 220}


def event(kind: str, **data):
    print(json.dumps({"event": kind, **data}, ensure_ascii=True), flush=True)


def safe_text(value: str, limit: int = 26) -> str:
    """Spectrum ROM text is ASCII. Never allow BASIC quotes/control injection."""
    return "".join(c if 32 <= ord(c) < 127 and c != '"' else "?"
                   for c in value)[:limit].strip() or "UNTITLED"


def inspect_tap(path: Path) -> dict:
    if path.suffix.lower() not in (".tap", ".tzx"):
        raise ValueError(tr('Поддерживаются файлы .tap и .tzx'))
    size = path.stat().st_size
    if size > 16 * 1024 * 1024:
        raise ValueError(tr('Кассетный файл превышает ограничение 16 МиБ'))
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    catalog = tape_profiles.catalog_info(path, digest)
    if path.suffix.lower() == ".tzx":
        blocks = tape_support.tzx_blocks(data)
        return {"path": str(path.resolve()), "size": len(data), "blocks": len(blocks),
                "format": "TZX", "sha256": digest, **catalog,
                "details": [{"number": b.number, "id": b.block_id, "length": len(b.data or ())}
                            for b in blocks]}
    pos = 0
    blocks = []
    pending = None
    while pos < len(data):
        if pos + 2 > len(data):
            raise ValueError(tr('Оборванная длина блока TAP'))
        length = int.from_bytes(data[pos:pos+2], "little")
        pos += 2
        if length < 2 or pos + length > len(data):
            raise ValueError(tr('Оборванный или слишком короткий блок TAP'))
        block = data[pos:pos+length]
        pos += length
        checksum = 0
        for byte in block:
            checksum ^= byte
        if checksum:
            raise ValueError(tr('Неверная контрольная сумма блока {0}', len(blocks) + 1))
        entry = {"length": length - 2, "flag": block[0]}
        if len(block) == 19 and block[0] == 0 and block[1] <= 3:
            if pending is not None:
                raise ValueError(tr('После заголовка TAP отсутствует блок данных'))
            entry.update(type=block[1], name=safe_text(block[2:12].decode("ascii", "replace")),
                         declared_length=int.from_bytes(block[12:14], "little"))
            pending = entry["declared_length"]
        elif pending is not None:
            if block[0] != 255 or len(block)-2 != pending:
                raise ValueError(tr('Данные не соответствуют заголовку TAP'))
            pending = None
        blocks.append(entry)
    if not blocks or pending is not None:
        raise ValueError(tr('Пустой TAP или отсутствует последний блок данных'))
    return {"path": str(path.resolve()), "size": len(data), "blocks": len(blocks), "format": "TAP",
            "sha256": digest, **catalog, "details": blocks}


@dataclass
class DiskFile:
    name: str
    kind: str
    parameter: int
    length: int
    data: bytes  # includes BASIC trailer and sector padding when importing

    @property
    def sectors(self):
        return (len(self.data) + 255) // 256


def read_trd(data: bytes) -> list[DiskFile]:
    if len(data) not in (163840, 327680, 655360):
        raise ValueError(tr('Неожиданный размер промежуточного TRD'))
    if data[2279] != 16 or data[2276] > 128:
        raise ValueError(tr('Некорректный служебный сектор TRD'))
    files = []
    occupied = set(range(16))
    for n in range(data[2276]):
        entry = data[n*16:n*16+16]
        if entry[0] <= 1:
            raise ValueError(tr('Неожиданная удалённая запись TRD'))
        sector = entry[15]*16 + entry[14]
        count = entry[13]
        parameter, length = struct.unpack_from("<HH", entry, 9)
        if not count or entry[14] > 15 or sector+count > len(data)//256:
            raise ValueError(tr('Некорректные границы файла TRD'))
        if length > count*256 or occupied.intersection(range(sector, sector+count)):
            raise ValueError(tr('Пересечение или неверная длина файлов TRD'))
        occupied.update(range(sector, sector+count))
        files.append(DiskFile(entry[:8].decode("ascii").rstrip(), chr(entry[8]),
                              parameter, length, data[sector*256:(sector+count)*256]))
    return files


def write_trd(files: list[DiskFile], label: str) -> bytes:
    if len(files) > 128:
        raise ValueError(tr('На диске больше 128 файлов'))
    disk = bytearray(DISK_SIZE)
    next_sector = 16
    seen = set()
    for i, f in enumerate(files):
        identity = (f.name, f.kind)
        if identity in seen:
            raise ValueError(tr('Повтор имени на диске: {0}.{1}', f.name, f.kind))
        seen.add(identity)
        if not 1 <= len(f.name) <= 8 or len(f.kind) != 1:
            raise ValueError(tr('Некорректное имя TR-DOS'))
        if not 1 <= f.sectors <= 255 or not 0 <= f.length <= 65535:
            raise ValueError(tr('Файл {0} слишком велик для TR-DOS', f.name))
        if next_sector + f.sectors > 2560:
            raise ValueError(tr('Игры не помещаются на дискету 640 КиБ. Удалите часть списка.'))
        directory = (f.name.ljust(8).encode("ascii") + f.kind.encode("ascii")
                     + struct.pack("<HHBBB", f.parameter, f.length, f.sectors,
                                   next_sector % 16, next_sector // 16))
        disk[i*16:i*16+16] = directory
        disk[next_sector*256:next_sector*256+len(f.data)] = f.data
        next_sector += f.sectors
    disk[2273:2280] = bytes((next_sector % 16, next_sector // 16, 22, len(files))) + struct.pack("<H", 2560-next_sector) + b"\x10"
    disk[2282:2291] = b" "*9
    # The catalog uses the ROM font, so Cyrillic menu titles need an ASCII label.
    label = safe_text(label, 8)
    disk[2293:2301] = ("TARDULTR" if "?" in label else label).ljust(8).encode("ascii")
    return bytes(disk)


def token(name):
    return bytes((TOKENS[name],))


def number(value):
    # VAL literals avoid ZX's hidden 5-byte numeric representation.
    return token("VAL") + f'"{value}"'.encode("ascii")


def basic_line(n, body):
    return struct.pack(">H", n) + struct.pack("<H", len(body)+1) + body + b"\r"


def basic_file(name, program, start=10):
    # TR-DOS BASIC stores 0x80, 0xAA, autostart after the declared data.
    return DiskFile(name, "B", len(program), len(program), program + b"\x80\xaa" + struct.pack("<H", start))


def disk_load(name, code=False):
    return (token("RANDOMIZE") + token("USR") + number(15619) + b":"
            + token("REM") + b":" + token("LOAD") + b'"' + name.encode("ascii") + b'"'
            + (token("CODE") if code else b""))


def menu_file(title: str, games: list[dict]) -> DiskFile:
    parts = []
    def add(n, body):
        parts.append(basic_line(n, body))
    add(10, token("CLEAR") + number(59999) + b":" + token("BORDER") + number(0)
        + b":" + token("PAPER") + number(0) + b":" + token("INK") + number(7)
        + b":" + token("BRIGHT") + number(0) + b":" + token("CLS"))
    pages = max(1, (len(games) + PAGE_SIZE - 1) // PAGE_SIZE)
    if pages > 1:
        add(15, token("LET") + b"p=" + number(0))
        for page in range(pages):
            add(20+page*10, token("IF") + b"p=" + number(page) + token("THEN") + disk_load(screen_name(page), True))
    else:
        add(20, disk_load("MENU", True))
    # MENU.C already includes all text. No ROM character encoding or PRINT
    # cursor is involved, including the bottom two rows of the screen.
    # PAUSE uses the ROM keyboard buffer; an INKEY$ polling loop can miss
    # short keystrokes while evaluating the sixteen IF statements.
    add(400, token("PAUSE") + number(0))
    add(405, token("LET") + b"k$=" + token("CHR$") + token("PEEK") + number(23560))
    def key_condition(key):
        condition = b'k$="' + key.encode() + b'"'
        if key.isalpha():
            condition += token("OR") + b'k$="' + key.lower().encode() + b'"'
        return condition
    if pages > 1:
        add(410, token("IF") + key_condition("N") + token("THEN") + token("GO TO") + number(800))
        add(420, token("IF") + key_condition("P") + token("THEN") + token("GO TO") + number(850))
        add(430, token("GO TO") + number(1000) + b"+p*" + number(200))
        add(800, token("LET") + b"p=p+" + number(1))
        add(810, token("IF") + b"p=" + number(pages) + token("THEN") + token("LET") + b"p=" + number(0))
        add(820, token("GO TO") + number(20))
        add(850, token("LET") + b"p=p-" + number(1))
        add(860, token("IF") + b"p<" + number(0) + token("THEN") + token("LET") + b"p=" + number(pages-1))
        add(870, token("GO TO") + number(20))
        for page in range(pages):
            for slot, game in enumerate(games[page*PAGE_SIZE:(page+1)*PAGE_SIZE]):
                add(1000+page*200+slot*10, token("IF") + key_condition(KEYS[slot]) + token("THEN") + disk_load(game["loader"]))
            add(1160+page*200, token("GO TO") + number(400))
    else:
        for i, game in enumerate(games):
            add(410+i*10, token("IF") + key_condition(KEYS[i]) + token("THEN") + disk_load(game["loader"]))
        add(600, token("GO TO") + number(400))
    return basic_file("boot", b"".join(parts))


def screen_name(page):
    return "MENU" if page == 0 else f"MENU{page:02X}"


def create_menu_files(background, title, games, layouts):
    files = [menu_file(title, games)]
    for page, layout in enumerate(layouts):
        screen = menu_screen.render(background, title, games[page*PAGE_SIZE:(page+1)*PAGE_SIZE],
                                    layout, page, len(layouts))
        files.append(DiskFile(screen_name(page), "C", 16384, 6912, screen))
    return files


def check_capacity(files):
    if len(files) > 128:
        raise ValueError(tr('Каталог дискеты переполнен: {0} файлов с меню, доступно 128. Удалите часть игр.', len(files)))
    size = sum(f.sectors*256 for f in files)
    if size > 651264:
        raise ValueError(tr('Игры с меню занимают {0:g} КиБ; на дискете доступно 636 КиБ. Удалите часть игр.', size / 1024))


def builtin_background() -> bytes:
    screen = bytearray(6912)
    screen[6144:] = bytes([1])*768
    # Sparse blue stars and a bright Spectrum stripe in the bottom right.
    for y in range(192):
        for x in range(256):
            stripe = y >= 176 and x >= 160 and ((x+y)//8) % 6 != 0
            star = ((x*73+y*151) % 541 == 0)
            if stripe or star:
                offset = (y//64)*2048 + (y % 8)*256 + ((y//8) % 8)*32 + x//8
                screen[offset] |= 128 >> (x % 8)
            if stripe:
                screen[6144+(y//8)*32+x//8] = 64 + [2,6,4,5,1,3][((x//8)+(y//8)) % 6]
    return bytes(screen)


def tool_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "Z80to.exe"
    return Path(__file__).resolve().parents[1] / ".tools/z80to/Z80to.exe"


def prepare_snapshot(path: Path, out: Path, machine: str, start: str = "") -> dict:
    import skoolkit.tap2sna as tape_loader
    from skoolkit.snapshot import Snapshot
    profile = tape_profiles.identify(path)
    profile_options = tape_profiles.options(profile, machine, start)
    remaining = tape_support.remaining_after_stop(path, machine)
    if remaining and not profile:
        raise ValueError(tr('TZX останавливает ленту в {0}К до блоков ', machine)
                         + ", ".join(map(str, remaining))
                         + tr('. Полный перенос требует продолжения загрузки; неполный образ не создан.'))
    # Capture RAM after the 128 ROM has booted, before the first tape block.
    # In particular bank 7 already contains ROM workspace: nonzero bytes alone
    # cannot identify a 128K game. The pinned SkoolKit API is covered by tests.
    initial_banks = {}
    original_tracer = tape_loader.LoadTracer
    class ObservedLoadTracer(original_tracer):
        def __init__(self, simulator, *args, **kwargs):
            if machine == "128":
                initial_banks.update({b: bytes(simulator.memory.banks[b]) for b in (1, 3, 4, 6, 7)})
            super().__init__(simulator, *args, **kwargs)
    # SkoolKit interprets a Windows drive letter as a URL scheme. Stage the
    # input in the private working directory and pass relative names.
    input_name = "input" + path.suffix.lower()
    shutil.copyfile(path, out.parent / input_name)
    args = ["-c", "machine=" + machine, "-c", "in-flags=4",
            "-c", f"timeout={LOAD_TIMEOUT}", *profile_options, input_name, out.name]
    if start:
        value = int(start, 0) if start.lower().startswith("0x") else int(start)
        if not 0 <= value <= 65535:
            raise ValueError(tr('Адрес старта должен быть от 0 до 65535'))
        args[0:0] = ["--start", str(value)]
    log = io.StringIO()
    previous_directory = Path.cwd()
    try:
        os.chdir(out.parent)
        tape_loader.LoadTracer = ObservedLoadTracer
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            tape_loader.main(args)
    finally:
        tape_loader.LoadTracer = original_tracer
        os.chdir(previous_directory)
    output = log.getvalue()
    if not out.is_file() or "Tape finished" not in output or "timed out" in output or "interrupted" in output:
        raise ValueError(tr('Не удалось полностью загрузить кассету в {0}К за {1} секунд Spectrum. Возможны ожидание клавиши, подгрузка или нестандартный загрузчик.\n', machine, LOAD_TIMEOUT) + output[-1600:])
    if re.search(r'Data block \(\d+ bytes\) \[skipped\]', output):
        raise ValueError(tr('Загрузчик пропустил блоки данных. Конец ленты не означает завершение загрузки; неполный образ не создан.'))
    snapshot = Snapshot.get(str(out))
    profile_info = tape_profiles.validate(profile, path, snapshot)
    adaptation = tape_profiles.adapt_snapshot(profile, snapshot)
    if adaptation:
        snapshot.write(str(out))
        profile_info.update(adaptation)
        event('info', text=adaptation['profile_note'])
    ram = snapshot.ram(-1)
    changed_banks = [b for b, initial in initial_banks.items() if bytes(ram[b*16384:(b+1)*16384]) != initial]
    return {"pc": snapshot.pc, "machine": snapshot.machine, "ram_bytes": len(ram),
            **machine_probe.observe(snapshot),
            "extra_banks_changed": changed_banks, "bank_observation": bool(initial_banks),
            "load_timeout": LOAD_TIMEOUT, **profile_info,
            "zero_bytes": ram.count(0), "log": output,
            "warning": tr('Снимок сделан внутри ROM; проверьте запуск') if snapshot.pc < 16384 else ""}


def select_snapshot(path: Path, out: Path, requested: str, start: str = "") -> dict:
    from skoolkit import SkoolKitError
    if requested not in ("auto", "48", "128"):
        raise ValueError(tr('Модель должна быть auto, 48 или 128'))
    attempts = []
    def attempt(machine):
        directory = out.parent / ("load" + machine)
        directory.mkdir()
        candidate = directory / out.name
        event("loading", machine=machine, text=tr('Проверка загрузки в {0}К: {1}', machine, path.name))
        try:
            info = prepare_snapshot(path, candidate, machine, start)
            attempts.append({"machine": machine, "ok": True,
                             "extra_banks_changed": info["extra_banks_changed"]})
            return candidate, info
        except (ValueError, SkoolKitError) as exc:
            attempts.append({"machine": machine, "ok": False, "error": str(exc)})
            return None
    chosen = attempt(requested if requested != "auto" else "128")
    reason = tr('Модель выбрана вручную.')
    if requested == "auto":
        runtime_128 = chosen and (chosen[1].get("runtime_paging") or chosen[1].get("runtime_ay"))
        if chosen and (chosen[1]["extra_banks_changed"] or not chosen[1]["bank_observation"] or runtime_128):
            reason = tr('Выбрано 128К: загрузчик изменяет дополнительные банки памяти.') if chosen[1]["bank_observation"] else tr('Выбрано 128К: использование банков не удалось проверить.')
            if runtime_128:
                reason = tr('Выбрано 128К: после загрузки программа переключает банки/экран или использует AY.')
        else:
            fallback = attempt("48")
            if fallback:
                chosen = fallback
                reason = tr('Выбрано 48К: загрузка завершена; дополнительных данных 128К не обнаружено.')
                if not attempts[0]["ok"]:
                    reason = tr('Выбрано 48К: загрузка в 128К не завершилась, в 48К завершилась.')
            elif chosen:
                reason = tr('Выбрано 128К: загрузка в 48К не завершилась.')
    if not chosen:
        raise ValueError("\n\n".join(a["machine"] + tr('К: ') + a["error"] for a in attempts))
    candidate, info = chosen
    shutil.copyfile(candidate, out)
    return {**info, "load_machine": "128" if info["machine"] == "128K" else "48",
            "requested_machine": requested, "model_reason": reason, "load_attempts": attempts}


def transfer_options(mode: str) -> list[str]:
    options = {"auto": [], "48": ["-f"], "preserve": ["-k"]}
    if mode not in options:
        raise ValueError(tr('Режим переноса должен быть auto, 48 или preserve'))
    return options[mode]


def pack_snapshot(snapshot_path: Path, mode: str) -> tuple[list[DiskFile], dict]:
    # -f and -k are per-input options; they must follow the snapshot filename.
    result = subprocess.run([str(tool_path()), "-r", snapshot_path.name, *transfer_options(mode)],
                            cwd=snapshot_path.parent, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=60,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    output = result.stdout.decode("cp1252", "replace")
    trd = snapshot_path.with_suffix(".trd")
    if result.returncode or not trd.is_file():
        raise ValueError(tr('Z80to не смог подготовить загрузчик:\n') + output[-1500:])
    files = read_trd(trd.read_bytes())
    if sum(f.kind == "B" for f in files) != 1 or not any(f.kind == "C" for f in files):
        raise ValueError(tr('Неожиданная структура загрузчика Z80to'))
    # Z80to 1.4 reports the input model followed by an optional conversion.
    # Retain the full log; an unrecognised future format must not imply 48K.
    model = re.search(r"\bV[123]-(48|128)k(?:\s+>(48|128)k)?", output)
    return files, {"transfer_mode": mode, "result_machine": (model[2] or model[1]) if model else None,
                   "converter_log": output}


def convert_native_chain(item, analysis, stem, profile):
    """One compact BASIC sequencer for any verified chain of resident parts.

    TR-DOS needs workspace below CLEAR. Repeating a full LOAD/USR line for
    every part can exhaust that space; use a variable filename instead.
    LOAD must end its line because it follows REM in TR-DOS syntax.
    """
    chain = load_strategies.CHAINS[profile]
    machine = str(item.get('machine', 'auto'))
    mode = str(item.get('transfer_mode', 'auto'))
    if machine not in ('auto', '48', '128'):
        raise ValueError(tr('Модель должна быть auto, 48 или 128'))
    if str(item.get('start', '')).strip():
        raise ValueError(tr('{0}: оставьте адрес старта пустым для переноса всей цепочки частей.', chain.label))
    if chain.required_machine == '128' and (machine == '48' or mode == '48'):
        raise ValueError(tr('{0}: требуется 128К.', chain.label))
    payloads = chain.payloads(analysis['path'])
    poke = lambda value: bytes([244]) + number(23739) + b',' + number(value)
    run_part = token('RANDOMIZE') + token('USR') + number(chain.address)
    if chain.restore_err_nr is not None:
        run_part = poke(chain.restore_err_nr) + b':' + run_part
    program = b''.join((
        basic_line(10, token('PAPER') + number(0) + b':' + token('BORDER') + number(0)
            + b':' + token('CLEAR') + number(chain.clear) + b':' + token('LET') + b'n=' + number(65)),
        basic_line(20, token('LET') + b'f$="' + stem.encode('ascii') + b'."+' + token('CHR$') + b'n:' + poke(111)),
        basic_line(30, token('RANDOMIZE') + token('USR') + number(15619)
            + b':' + token('REM') + b':' + token('LOAD') + b'f$' + token('CODE')),
        basic_line(40, run_part),
        basic_line(50, token('LET') + b'n=n+' + number(1) + b':' + token('IF') + b'n<' + number(65+len(payloads))
            + token('THEN') + token('GO TO') + number(20)),
        basic_line(60, token('LET') + b'n=' + number(65+chain.repeat_from) + b':' + token('GO TO') + number(20)),
    ))
    files = [basic_file(stem, program)] + [
        DiskFile(stem+'.'+chr(65+i), 'C', chain.address, len(data), data)
        for i, data in enumerate(payloads)]
    selected = '48' if machine == '48' or mode == '48' else '128'
    return files, {'path': analysis['path'], 'title': menu_screen.text(item.get('title') or chain.label, 29),
        'loader': stem, 'sha256': analysis['sha256'], 'tap_bytes': analysis['size'],
        'bytes': sum(f.sectors*256 for f in files), 'format': 'TAP', 'start': '',
        'requested_machine': machine, 'load_machine': selected, 'requested_transfer_mode': mode,
        'transfer_mode': 'native', 'result_machine': selected, 'machine': selected+'K',
        'ram_bytes': int(selected)*1024, 'pc': chain.address, 'warning': '',
        'tape_profile': profile, 'resident_bytes_verified': sum(map(len, payloads)),
        'part_count': len(payloads), 'repeat_from_part': chain.repeat_from+1,
        'model_reason': tr('{0}: перенос исходной цепочки загрузки частей.', chain.label),
        'profile_note': tr('{0}: сохранены все части ({1}) и переходы между ними через TR-DOS. Код частей не изменён.', chain.label, len(payloads)),
        **load_strategies.describe(profile)}


def convert_game(item: dict, index: int, work: Path) -> tuple[list[DiskFile], dict]:
    path = Path(item["path"]).resolve()
    analysis = inspect_tap(path)
    profile = tape_profiles.identify(path, analysis['sha256'])
    event('profile', index=index, sha256=analysis['sha256'],
          **tape_profiles.catalog_info(path, analysis['sha256']))
    tape_profiles.require_supported(profile)
    # Z80to uses the first three filename characters for its data files.
    # Three hex characters are unique even for duplicate source basenames.
    stem = f"G{index:02X}"
    game_dir = work / stem
    game_dir.mkdir()
    snapshot_path = game_dir / (stem + ".z80")
    machine = str(item.get("machine", "auto"))
    mode = str(item.get("transfer_mode", "auto"))
    transfer_options(mode)  # Reject invalid settings before emulating the tape.
    if profile in load_strategies.CHAINS:
        return convert_native_chain(item, analysis, stem, profile)
    if mode == '48' and profile in load_strategies.SNAPSHOTS and load_strategies.SNAPSHOTS[profile].machine == '128':
        raise ValueError(tr('{0}: требуется 128К.', tape_profiles.profile_label(profile)))
    if mode == "48" and profile == 'wec-le-mans-128':
        raise ValueError(tr('WEC Le Mans: принудительный перенос в 48К не поддерживается. Выберите «Авто» или «Сохранить 128К».'))
    start = str(item.get("start", "")).strip()
    info = select_snapshot(path, snapshot_path, machine, start)
    # Do not let the packer's separate model heuristic discard banks observed
    # being used by the tape loader. Explicit forced 48K remains available.
    effective_mode = "preserve" if mode == "auto" and (info["extra_banks_changed"] or info.get("runtime_paging") or info.get("runtime_ay")) else mode
    files, packing = pack_snapshot(snapshot_path, effective_mode)
    loaders = [f for f in files if f.kind == "B"]
    loaders[0].name = stem
    if info["load_machine"] == "128" and mode == "48":
        info["warning"] = " ".join(filter(None, [info["warning"],
            tr('Принудительный перенос в 48К: дополнительные банки отброшены, переключение памяти отключено. Проверьте игру.')]))
    return files, {"path": str(path), "title": menu_screen.text(item.get("title") or path.stem, 29),
                   "loader": stem, "sha256": analysis["sha256"], "tap_bytes": analysis["size"],
                   "bytes": sum(f.sectors*256 for f in files), "format": analysis["format"], "start": start,
                   "requested_transfer_mode": mode, **info, **packing, **load_strategies.describe(profile)}


def build(request: dict) -> dict:
    measure = request.get("action") == "measure"
    items = request.get("games", [])
    if not items:
        raise ValueError(tr('Добавьте хотя бы одну программу'))
    direct = request.get('launch_mode', 'menu') == 'direct'
    if request.get('launch_mode', 'menu') not in ('menu', 'direct'):
        raise ValueError(tr('Режим запуска должен быть menu или direct'))
    if direct and len(items) != 1:
        raise ValueError(tr('Для запуска без меню оставьте одну программу в списке.'))
    # Every supported game needs at least a BASIC loader and a CODE file.
    # This bound follows from the directory capacity, not an arbitrary limit.
    page_count = 0 if direct else (len(items)+PAGE_SIZE-1)//PAGE_SIZE
    if len(items)*2 + 1 + page_count > 128:
        raise ValueError(tr('Столько игр заведомо не помещается в каталог дискеты (128 файлов, включая меню и загрузчики).'))
    target = None if measure else Path(request["output"]).resolve()
    if target is not None:
        if target.suffix.lower() != ".trd":
            raise ValueError(tr('Выходной файл должен иметь расширение .trd'))
        if target.exists() and not request.get("overwrite", False):
            raise ValueError(tr('Файл уже существует. Выберите другое имя или подтвердите замену.'))
        if not target.parent.is_dir():
            raise ValueError(tr('Папка назначения не существует'))
    if not tool_path().is_file():
        raise ValueError(tr('Не найден Z80to.exe рядом с конвертером'))
    background = builtin_background()
    if not direct and request.get("background"):
        background = base64.b64decode(request["background"], validate=True)
        if len(background) != 6912:
            raise ValueError(tr('Фон SCR должен содержать ровно 6912 байт'))
    title = menu_screen.text(request.get("title", "КОЛЛЕКЦИЯ ИГР"))
    layouts = menu_screen.normalize_pages(None if direct else request.get("pages"), None if direct else request.get("layout"), len(items))
    menu_games = [{"title": item.get("title") or Path(item["path"]).stem, "loader": f"G{i:02X}"}
                  for i, item in enumerate(items)]
    menu_files = [] if direct else create_menu_files(background, title, menu_games, layouts)
    all_files = []
    games = []
    started = time.monotonic()
    # Intermediates never touch the source tapes or working directory.
    with tempfile.TemporaryDirectory(prefix=".tardulator-work-", dir=target.parent if target else None) as directory:
        work = Path(directory)
        for i, item in enumerate(items):
            event("progress", index=i, count=len(items), text=tr('Загрузка {0}/{1}: {2}', i + 1, len(items), Path(item['path']).name))
            try:
                files, game = convert_game(item, i, work)
            except Exception as exc:
                event('game_error', index=i, message=str(exc),
                      unsupported=isinstance(exc, tape_profiles.UnsupportedTape))
                raise ValueError(f"{Path(item['path']).name}: {exc}") from exc
            all_files.extend(files)
            games.append(game)
            event("game", index=i, **{k: v for k, v in game.items() if k not in ("log", "converter_log")})
            check_capacity(menu_files + all_files)
        if direct:
            # The first BASIC is the program's own loader, not a wrapper that
            # loads another BASIC. TR-DOS's standard RUN boots it directly.
            next(f for f in all_files if f.kind == 'B').name = 'boot'
        files = menu_files + all_files
        image = write_trd(files, title)
        read_trd(image)  # Validate exact image before committing it.
        report = {"version": VERSION, "action": "measure" if measure else "build",
                  "title": title, "games": games, "layout": layouts[0], "pages": layouts,
                  "page_count": page_count, "launch_mode": "direct" if direct else "menu",
                  "file_count": len(files), "file_capacity": 128,
                  "menu_bytes": sum(f.sectors*256 for f in menu_files),
                  "menu_sha256": hashlib.sha256(menu_files[1].data).hexdigest() if menu_files else None,
                  "menu_pages": [{"file": f.name, "sha256": hashlib.sha256(f.data).hexdigest()} for f in menu_files[1:]],
                  "used_bytes": sum(f.sectors*256 for f in files), "capacity_bytes": 651264,
                  "disk_sha256": hashlib.sha256(image).hexdigest(), "seconds": round(time.monotonic()-started, 2),
                  "note": tr('Снимки загруженных TAP/TZX. Автовыбор учитывает загрузку и дополнительные банки; это не проверка всех уровней. Произвольная подгрузка и сохранение на кассету не адаптируются. Проверяйте программы в эмуляторе.')}
        if measure:
            return report
        report["output"] = str(target)
        # Write in target directory then replace atomically. Failed conversion
        # leaves an existing disk untouched; temporary output is always removed.
        fd, temporary = tempfile.mkstemp(prefix=".tardulator-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(image)
                handle.flush()
                os.fsync(handle.fileno())
            if not request.get("overwrite", False):
                os.rename(temporary, target)  # Windows refuses existing destination.
            else:
                os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    report_path = target.with_suffix(".report.json")
    try:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report"] = str(report_path)
    except OSError as exc:
        report["report_warning"] = str(exc)
    return report


def main():
    try:
        request = json.load(sys.stdin)
        set_language(request.get("language"))
        if request.get("action") == "analyze":
            results = []
            for name in request.get("paths", []):
                try:
                    results.append({**inspect_tap(Path(name)), "ok": True})
                except Exception as exc:
                    results.append({"path": name, "ok": False, "error": str(exc)})
            event("result", files=results)
        elif request.get("action") in ("build", "measure"):
            event("result", **build(request))
        else:
            raise ValueError(tr('Неизвестная операция'))
        return 0
    except Exception as exc:
        event("error", message=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
