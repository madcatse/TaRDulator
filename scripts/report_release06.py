"""Build the local 0.6 validation report from completed checks."""
from pathlib import Path
import html
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/release-0.6'
rows = json.loads((OUT/'frozen.json').read_text(encoding='utf-8'))
fuse = {r['id']: r for r in json.loads((OUT/'fuse.json').read_text())}
collection = json.loads((OUT/'collection-fuse.json').read_text())
assert len(rows) == len(fuse) == len(collection) == 24
assert all(r['frozen_ok'] for r in rows)
assert all(r['passed'] or r.get('with_stack_scratch', {}).get('passed') for r in [*fuse.values(), *collection])
wec = next(r for r in rows if r['id'] == 13)
target = OUT/'WEC-Le-Mans-128.trd'
shutil.copyfile(wec['disk'], target)
report = wec['frozen_report'].copy()
report['output'] = str(target)
report.pop('report', None)
target.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
table = ''
for row in rows:
    status = 'Пройдено' if fuse[row['id']]['passed'] else 'Пройдено с исключением стека Z80to'
    table += f"<tr><td>{html.escape(row['name'])}</td><td>{row['machine']}К</td><td>{row['info']['bytes']/1024:g} КиБ</td><td>{status}</td></tr>"
page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>ТаРДулятор 0.6 — проверка</title>
<style>body{font:16px/1.5 Segoe UI,Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#213040;background:#f8fafc}h1{color:#146c9c}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #d5dfe6;padding:9px;text-align:left}img{width:384px;image-rendering:pixelated;max-width:100%}figure{display:inline-block;margin:12px 20px 12px 0}a{color:#096d9e}.ok{padding:16px;background:#e0f1e7;border-radius:8px}</style>
<h1>ТаРДулятор / TaRDulator 0.6</h1><p>21 октября 2026 · Windows 11 · Fuse 1.6.0 / Pentagon</p>
<p class="ok">24 кассеты → 24 совпавших образа исходного и автономного конвертера → запуск отдельных дискет и каждого пункта сборников в Fuse.</p>
<h2>WEC Le Mans</h2><p>Поддержана 128К-ветка файла из games48-128.zip. Исправлено чтение AY при проверке модели; загружены блоки 33–35. Перед переносом проверяются все 50 308 байт основного кода и дополнительных данных. Блоки 37/39 относятся к 48К-подгрузке. Версия 48К и принудительное сокращение до 48К не поддерживаются.</p>
<p><a href="WEC-Le-Mans-128.trd">Отдельная дискета WEC</a> · <a href="../wec-0.6/ANALYSIS.md">Подробный разбор</a></p>
<figure><img src="../wec-0.6/fuse-13-128.png"><figcaption>Fuse: меню после загрузки TRD, 500 кадров</figcaption></figure>
<figure><img src="../wec-0.6/keyboard-999.png"><figcaption>SkoolKit: старт гонки без кассеты</figcaption></figure>
<p>Проверены загрузка и начало игры. Полное прохождение и поздние состояния не проверены. Профиль распознаёт только предоставленный дамп по полному SHA-256; общий обход остановок TZX не включён.</p>
<h2>Интерфейс</h2><p>Опции → Язык интерфейса → Русский / English. Название в шапке и окне меняется вместе с интерфейсом. Выбор сохраняется после перезапуска. Макеты, страницы и ваши надписи не меняются. Светлая системная тема сохранена.</p>
<h2>Сборники</h2><ul><li><a href="Archive-TAP.trd">Archive-TAP</a>: 7 игр, 441 КиБ, 53 файла</li><li><a href="Archive-TZX.trd">Archive-TZX</a>: 7 игр, 489,75 КиБ, 58 файлов, включая WEC</li><li><a href="Random-TAP.trd">Random-TAP</a>: 10 программ, 158,25 КиБ, 32 файла</li></ul>
<p>В Fuse проверяются регистры, системная область и выборочные байты RAM/банков, затем выполняются 500 кадров. 22 строгие проверки проходят; два Chase H.Q. требуют прежнего исключения 32 байт перед SP, используемых загрузчиком Z80to. WEC проходит без исключения. Для каждого пункта сборников результат тот же.</p>
<table><thead><tr><th>Кассета</th><th>Модель</th><th>Файлы игры</th><th>Fuse</th></tr></thead><tbody>''' + table + '''</tbody></table>
<p>35 тестов Python; графические проверки C#; переключение RU ↔ EN с сохранением двух страниц, пользовательских текстов и параметров. Английские сообщения готового EXE проверены. Исходные кассеты и ZIP не изменены.</p>
<p><a href="selection.json">Выборка и хеши</a> · <a href="frozen.json">Результаты EXE</a> · <a href="fuse.json">Отдельные TRD в Fuse</a> · <a href="collection-fuse.json">Пункты сборников в Fuse</a></p></html>'''
(OUT/'REPORT.html').write_text(page, encoding='utf-8')
print('Report and standalone WEC disk ready')
