"""Single catalog of exact tape dumps requiring individual handling.

Add a distinct record for each verified dump, then configure its mechanism in
load_strategies/tape_profiles. Runtime recognition and generated help use this
same table. No file-name heuristics and no executable code in external files.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TapeProfile:
    id: str
    title: str
    sha256: str
    format: str
    status: str
    ru: str
    en: str

    def description(self, language='ru'):
        return self.en if language == 'en' else self.ru


PROFILES = (
    TapeProfile('escape-castle-no-floating-bus', 'Castle Escape',
        'c200b9b98727ad84166dc3d168583b820989d553123d89c2bb115ebed2b1b623', 'TAP', 'hardware-test',
        'Ожидание floating bus заменено задержкой по образцу CASTESCD.trd. Исправляет остановку перед отрисовкой спрайтов на машинах без floating bus. Проверка на Дельте ожидается.',
        'Floating-bus wait replaced by a delay based on CASTESCD.trd. Fixes the stall before sprite drawing on machines without a floating bus. Delta hardware testing is pending.'),
    TapeProfile('unsupported-castlevania-en', 'Castlevania: Spectral Interlude (EN)',
        '9729f85965060d043d25599345d217b2051f596564fea8dcc51d9cc806d1e4b8', 'TAP', 'unsupported',
        'Перенос заблокирован: после запуска остаётся блок 24. Полная поздняя подгрузка пока не реализована; неполный образ не создаётся.',
        'Conversion blocked: block 24 remains after startup. Complete late loading is not implemented; no incomplete image is created.'),
    TapeProfile('unsupported-castlevania-ru', 'Castlevania: Spectral Interlude (RU)',
        'e166d103a7db6340948e80aeb23390a3898e810c2e6e392350aa23dd37b7e7e8', 'TAP', 'unsupported',
        'Перенос заблокирован: после запуска остаётся блок 24. Полная поздняя подгрузка пока не реализована; неполный образ не создаётся.',
        'Conversion blocked: block 24 remains after startup. Complete late loading is not implemented; no incomplete image is created.'),
    TapeProfile('dizzy7-unpacked', 'Dizzy 7 NEW',
        'eaca5e82219f6ace5e154c7e590e7273ee9bf539e65f327cc98905c1201cfe47', 'TAP', 'supported',
        'Снимок создаётся после распаковки, по адресу 29437. Это обходит ограничение упаковщика; проверяются точка входа, стек и инструкции.',
        'Snapshot taken after decompression at address 29437, avoiding a packer limitation. Entry point, stack and instructions are checked.'),
    TapeProfile('unsupported-dizzy8', 'Dizzy 8',
        '93934b371e128a52c1b31bdfa267184d2200fe2d916932a6be991b6dd6ed2d18', 'TAP', 'unsupported',
        'Перенос заблокирован: после запуска остаётся блок 10. Полная поздняя подгрузка пока не реализована; неполный образ не создаётся.',
        'Conversion blocked: block 10 remains after startup. Complete late loading is not implemented; no incomplete image is created.'),
    TapeProfile('fearzone-2018', 'Fearzone 2018',
        '771474aaae6e0cff6ec899ad9f306cb1302b3a0b1d47b773445524d6553f0209', 'TAP', 'supported',
        'Опрос клавиатуры во вступлении отделён от чтения ленты (in-flags=2), чтобы загрузить все части через ROM LOAD.',
        'Intro keyboard polling is separated from tape reads (in-flags=2), allowing all parts to load through ROM LOAD.'),
    TapeProfile('escape-forest-no-floating-bus', 'Forest Escape',
        'be2d3d792aab209930a0b76644aa4e7a2df6479beca28fbe21f97a54750f7d8b', 'TAP', 'hardware-test',
        'Ожидание floating bus заменено задержкой; отрисовка игрока и врагов продолжается без чтения видеошины. Проверка на Дельте ожидается.',
        'Floating-bus wait replaced by a delay; player and enemy drawing continues without reading the video bus. Delta hardware testing is pending.'),
    TapeProfile('milky2-disk-chain', 'MILKY2',
        'b5ab90057f6541cb783a19af14648c47ef663570e320a5e0846e7394aaf83d0a', 'TAP', 'supported',
        'Обе части сохранены: вступление и основная часть. Переходы перенесены на TR-DOS, исходные сжатые блоки не изменяются. Требуется 128К.',
        'Both intro and main part are retained. Transitions use TR-DOS, keeping the original compressed blocks unchanged. Requires 128K.'),
    TapeProfile('new-view-disk-chain', 'New View',
        'bb0aee3c804cafe64c87174d74ad0319cdf2cde9cdb3bf6897b9551e1d134480', 'TAP', 'supported',
        'Все пять частей загружаются последовательно через TR-DOS; сохранён возврат к первой части. Проверяются заголовки, размеры и адреса CODE.',
        'All five parts load sequentially through TR-DOS, then return to the first part. CODE headers, lengths and addresses are checked.'),
    TapeProfile('escape-pyramid-no-floating-bus', 'Pyramid Escape',
        'ea744d146644e4b03372e6bfd81d8d8d8b81f838477a0632551ba7a5f3bc1a34', 'TAP', 'hardware-test',
        'Ожидание floating bus заменено задержкой; отрисовка игрока и врагов продолжается без чтения видеошины. Проверка на Дельте ожидается.',
        'Floating-bus wait replaced by a delay; player and enemy drawing continues without reading the video bus. Delta hardware testing is pending.'),
    TapeProfile('wec-le-mans-128', 'WEC Le Mans 128K',
        'e96ebadfd2e22e23f5e50338c8e2cfc7e3e7aed65ad9312c03725bf80892cf5c', 'TZX', 'supported',
        'Выбирается полностью резидентная ветка 128К до блока 35. Побайтно проверяются 50 308 байт; блоки 37/39 относятся к альтернативной ветке 48К.',
        'Uses the fully resident 128K branch through block 35. Verifies 50,308 bytes; blocks 37/39 belong to the alternative 48K branch.'),
    TapeProfile('yazzie-initialized', 'Yazzie 128',
        'd45056463fa45e33de6d472519330f0087a7f59065ba39c3ed049310f133de32', 'TAP', 'supported',
        'Снимок после проверки таймингов, по адресу 24573: предотвращает сброс на Pentagon/TR-DOS. Проверяются регистры, порт и код; игра не патчится.',
        'Snapshot after the timing check at address 24573 prevents reset on Pentagon/TR-DOS. Registers, paging port and code are checked; game code is unchanged.'),
)


def validate(profiles):
    ids, digests = set(), set()
    for entry in profiles:
        if (not re.fullmatch(r'[a-z0-9-]+', entry.id)
                or not re.fullmatch(r'[0-9a-f]{64}', entry.sha256)
                or entry.format not in ('TAP','TZX')
                or entry.status not in ('supported','hardware-test','unsupported')
                or not all((entry.title,entry.ru,entry.en))
                or entry.id in ids or entry.sha256 in digests):
            raise ValueError('Invalid or duplicate tape catalog entry: '+entry.id)
        ids.add(entry.id); digests.add(entry.sha256)


validate(PROFILES)
BY_ID = {entry.id:entry for entry in PROFILES}
BY_DIGEST = {(entry.format,entry.sha256):entry for entry in PROFILES}


def match(suffix, digest):
    return BY_DIGEST.get((suffix.lstrip('.').upper(),digest.lower()))
