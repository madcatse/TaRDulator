"""Static menu rasterizer shared by the disk builder and verified against C#.

Text is baked into a normal SCR, so Cyrillic works with an unmodified ROM.
Coordinates and widths use the Spectrum's 32 x 24 character cells.
"""

from localization import tr
from pathlib import Path
import copy

KEYS = "123456789ABCDEFG"
PAGE_SIZE = len(KEYS)
FONT = Path(__file__).with_name("menu_font.bin").read_bytes()
if len(FONT) != 1296:
    raise ValueError(tr('Неверный размер шрифта меню'))


def supported(c):
    return 32 <= ord(c) <= 126 or "А" <= c <= "я" or c in "Ёё"


def text(value, limit=32):
    return "".join(c if supported(c) else "?" for c in str(value)).strip()[:limit]


def glyph(c):
    if "А" <= c <= "я":
        return 96 + ord(c) - ord("А")
    if c in "Ёё":
        return 160 + (c == "ё")
    return ord(c) - 32 if 32 <= ord(c) <= 126 else ord("?") - 32


def style(x, y, width=28, ink=7, bright=False):
    return dict(x=x, y=y, width=width, ink=ink, paper=0, bright=bright, visible=True)


def default_layout(count):
    if not 0 <= count <= PAGE_SIZE:
        raise ValueError(tr('На одной странице может быть до 16 пунктов'))
    return {"version": 2, "title": style(2, 1, ink=5, bright=True),
            "hint": {**style(2, 21, ink=6), "text": "НАЖМИТЕ КЛАВИШУ ИГРЫ"},
            "previous": {**style(2, 23, width=12, ink=6), "text": "P НАЗАД"},
            "next": {**style(18, 23, width=12, ink=6), "text": "N ДАЛЕЕ"},
            "page": {**style(2, 2, ink=5), "text": "СТРАНИЦА {page}/{pages}"},
            "items": [style(2, 4+i) for i in range(count)]}


def normalize_layout(value, count, page_count=1):
    result = default_layout(count)
    value = {} if value is None else value
    if not isinstance(value, dict) or value.get("version", 1) not in (1, 2):
        raise ValueError(tr('Неизвестный формат макета меню'))
    for name in ("title", "hint", "previous", "next", "page"):
        if name in value:
            if not isinstance(value[name], dict):
                raise ValueError(tr('Неверные параметры надписи меню'))
            result[name].update(value[name])
    if "items" in value:
        if not isinstance(value["items"], list) or len(value["items"]) != count:
            raise ValueError(tr('Число позиций меню не совпадает с числом игр'))
        for target, source in zip(result["items"], value["items"]):
            if not isinstance(source, dict):
                raise ValueError(tr('Неверная позиция пункта меню'))
            target.update(source)
    entries = [(tr('Заголовок'), result["title"], False), (tr('Подсказка'), result["hint"], False)]
    entries += [(tr('Назад (P)'), result["previous"], False), (tr('Далее (N)'), result["next"], False),
                (tr('Номер страницы'), result["page"], False)]
    entries += [(tr('Пункт {0}', i + 1), s, True) for i, s in enumerate(result["items"])]
    occupied = {}
    for name, s, item in entries:
        for field, low, high in (("x", 0, 31), ("y", 0, 23), ("width", 4 if item else 1, 32),
                                 ("ink", 0, 7), ("paper", 0, 7)):
            if type(s[field]) is not int or not low <= s[field] <= high:
                raise ValueError(tr('{0}: недопустимое значение {1}', name, field))
        if type(s["visible"]) is not bool or type(s["bright"]) is not bool:
            raise ValueError(tr('{0}: неверный переключатель', name))
        if item and not s["visible"]:
            raise ValueError(tr('Пункты выбора игры нельзя скрывать'))
        if s["x"] + s["width"] > 32:
            raise ValueError(tr('{0} выходит за край экрана', name))
        if not s["visible"] or (page_count <= 1 and name in (tr('Назад (P)'), tr('Далее (N)'), tr('Номер страницы'))):
            continue
        if s["ink"] == s["paper"]:
            raise ValueError(tr('{0}: цвет текста совпадает с фоном', name))
        for x in range(s["x"], s["x"] + s["width"]):
            cell = x, s["y"]
            if cell in occupied:
                raise ValueError(tr('Пересечение: {0} и {1}', occupied[cell], name))
            occupied[cell] = name
    for name in ("hint", "previous", "next", "page"):
        result[name]["text"] = text(result[name]["text"])
    return result


def normalize_pages(values, legacy, count):
    pages = max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE)
    if values is not None and (not isinstance(values, list) or len(values) != pages):
        raise ValueError(tr('Число макетов не совпадает с числом страниц меню'))
    result = []
    for i in range(pages):
        size = min(PAGE_SIZE, count - i * PAGE_SIZE)
        layout = values[i] if values is not None else legacy
        # Old requests have a single layout. Its 16 slots can be reused on
        # each page, including a final partial page.
        if values is None and isinstance(layout, dict) and isinstance(layout.get("items"), list):
            layout = copy.deepcopy(layout)
            layout["items"] = layout["items"][:size]
        try:
            result.append(normalize_layout(layout, size, pages))
        except ValueError as exc:
            raise ValueError(tr('Страница {0}: {1}', i + 1, exc)) from exc
    return result


def print_text(screen, s, value):
    if not s["visible"]:
        return
    value = text(value)[:s["width"]].ljust(s["width"])
    for i, c in enumerate(value):
        x, row = s["x"] + i, s["y"]
        for line in range(8):
            y = row*8 + line
            offset = (y//64)*2048 + (y % 8)*256 + ((y//8) % 8)*32 + x
            screen[offset] = FONT[glyph(c)*8 + line]
        screen[6144 + row*32 + x] = s["ink"] + s["paper"]*8 + int(s["bright"])*64


def render(background, title, games, layout=None, page_index=0, page_count=1):
    if len(background) != 6912:
        raise ValueError(tr('Фон SCR должен содержать ровно 6912 байт'))
    layout = normalize_layout(layout, len(games), page_count)
    screen = bytearray(background)
    print_text(screen, layout["title"], title)
    for i, game in enumerate(games):
        print_text(screen, layout["items"][i], KEYS[i] + "  " + text(game["title"], 29))
    print_text(screen, layout["hint"], layout["hint"]["text"])
    if page_count > 1:
        for name in ("previous", "next", "page"):
            value = layout[name]["text"].replace("{page}", str(page_index+1)).replace("{pages}", str(page_count))
            print_text(screen, layout[name], value)
    return bytes(screen)
