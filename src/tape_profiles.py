"""Narrow, verified exceptions for tapes with alternate loading branches.

Never identify a loader by its filename or simply ignore a TZX stop. A profile
must match the whole tape and validate the resulting resident bytes.
"""

from localization import tr
import hashlib
import load_strategies

import tape_catalog
import localization

WEC_SHA256 = tape_catalog.BY_ID['wec-le-mans-128'].sha256
MILKY2_SHA256 = tape_catalog.BY_ID['milky2-disk-chain'].sha256
TAP_PROFILES = {entry.sha256:entry.id for entry in tape_catalog.PROFILES if entry.format == 'TAP'}


def profile_label(profile):
    entry = tape_catalog.BY_ID.get(profile)
    return entry.title if entry else profile


def catalog_info(path, digest):
    entry = tape_catalog.match(path.suffix, digest)
    return {'tape_profile': entry.id if entry else None,
            'profile_title': entry.title if entry else '',
            'profile_status': entry.status if entry else 'generic',
            'profile_description': entry.description(localization.language) if entry else ''}



class UnsupportedTape(ValueError):
    """A known dump whose complete transfer has not been implemented."""


def require_supported(profile):
    if profile in ('unsupported-castlevania-en', 'unsupported-castlevania-ru'):
        raise UnsupportedTape(tr('Castlevania: эта версия пока не поддерживается. После запуска остаётся блок 24; полный перенос с поздней подгрузкой не реализован. Неполный образ не создан.'))
    if profile == 'unsupported-dizzy8':
        raise UnsupportedTape(tr('Dizzy 8: эта версия пока не поддерживается. После запуска остаётся блок 10; полный перенос с поздней подгрузкой не реализован. Неполный образ не создан.'))

    entry = tape_catalog.BY_ID.get(profile)
    if entry and entry.status == 'unsupported':
        raise UnsupportedTape(entry.description(localization.language))


def identify(path, digest=None):
    digest = digest or hashlib.sha256(path.read_bytes()).hexdigest()
    entry = tape_catalog.match(path.suffix, digest)
    return entry.id if entry else None


def options(profile, machine, start):
    require_supported(profile)
    if profile in load_strategies.SNAPSHOTS:
        return load_strategies.SNAPSHOTS[profile].options(machine, start, profile_label(profile))
    if profile != 'wec-le-mans-128':
        return []
    if machine != '128':
        raise ValueError(tr('WEC Le Mans: перенос версии 48К с подгрузкой не поддерживается. Выберите «Авто» или 128К.'))
    if start and int(start, 16 if start.lower().startswith('0x') else 10) != 33025:
        raise ValueError(tr('WEC Le Mans: проверенный адрес старта — 33025. Оставьте поле старта пустым.'))
    # AY detection needs real IN r,(C) reads. Blocks 33/34 install banked
    # data, 35 replaces the 48K main program. Stop 36 terminates this branch.
    return ['-c', 'in-flags=4', '--tape-stop', '36', '--start', '33025']


def validate(profile, path, snapshot):
    if profile in load_strategies.SNAPSHOTS:
        load_strategies.SNAPSHOTS[profile].validate(snapshot, profile_label(profile))
    if profile == 'yazzie-initialized':
        return {'tape_profile': profile,
                'profile_note': tr('Yazzie 128: проверка таймингов выполнена до снимка; предотвращён сброс при запуске на Pentagon/TR-DOS.')}
    if profile == 'dizzy7-unpacked':
        return {'tape_profile': profile,
                'profile_note': tr('Dizzy 7: снимок создаётся после распаковки, чтобы избежать ограничения упаковщика.')}
    if profile == 'fearzone-2018':
        return {'tape_profile': profile,
                'profile_note': tr('Fearzone: опрос клавиатуры во вступлении отделён от чтения ленты; загружены все части.')}
    if profile != 'wec-le-mans-128':
        return {}
    from skoolkit.tape import parse_tzx
    blocks = parse_tzx(str(path)).blocks
    ram, banks = snapshot.ram(), snapshot.ram(-1)
    checks = (
        snapshot.machine == '128K', snapshot.pc == 33025, snapshot.out7ffd == 16,
        bytes(ram[0x6164-16384:0x6164-16384+38020]) == bytes(blocks[34].data[1:-1]),
        bytes(banks[6*16384:6*16384+8192]) == bytes(blocks[32].data[29:29+8192]),
        bytes(banks[4*16384:4*16384+4096]) == bytes(blocks[33].data[29:29+4096]),
    )
    if not all(checks):
        raise ValueError(tr('WEC Le Mans: проверка загруженных данных 128К не пройдена; неполный образ не создан.'))
    return {'tape_profile': profile, 'resident_bytes_verified': 50308,
            'branch_end_block': 35, 'unused_alternate_blocks': [37, 39],
            'profile_note': tr('WEC Le Mans: загружена и побайтно проверена ветка 128К. Блоки 37/39 относятся к подгрузке 48К и для этой ветки не используются.')}


def adapt_snapshot(profile, snapshot):
    strategy = load_strategies.SNAPSHOTS.get(profile)
    if not strategy or not strategy.patches:
        return {}
    patches = strategy.adapt(snapshot, profile_label(profile))
    return {'tape_profile': profile, 'compatibility_patches': patches,
            'profile_note': tr('{0}: ожидание floating bus заменено программной задержкой по образцу CASTESCD.trd; требуется проверка темпа и плавности на реальной машине.', profile_label(profile))}
