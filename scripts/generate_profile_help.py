"""Generate RU/EN special-tape help from the runtime checksum catalog."""
import argparse
from html import escape
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tape_catalog import PROFILES
from engine import VERSION

START='<!-- BEGIN GENERATED TAPE CATALOG -->'
END='<!-- END GENERATED TAPE CATALOG -->'
TITLES={'ru':'Особые TAP/TZX: каталог профилей','en':'Special TAP/TZX: profile catalog'}
STATUS={
    'ru':{'supported':'Особая обработка','hardware-test':'Проверка на Дельте ожидается','unsupported':'Пока не поддерживается'},
    'en':{'supported':'Special handling','hardware-test':'Delta hardware test pending','unsupported':'Not supported yet'},
}


def render(language):
    ru=language=='ru'
    title=TITLES[language]
    intro=(
        'Для отдельных проверенных версий программа автоматически выбирает специальный способ переноса или исправление. '
        'Совпасть должен <strong>полный SHA-256 всего файла</strong>, а не имя игры. Переименование файла ничего не меняет; '
        'даже один изменённый байт даёт другую сумму и не включает чужой патч. Неизвестные файлы проходят обычный алгоритм.'
        if ru else
        'For individually verified versions, the converter automatically selects special handling or a compatibility patch. '
        'It matches the <strong>full SHA-256 of the entire file</strong>, not the game name. Renaming a file makes no difference; '
        'changing even one byte produces a different hash and does not enable another dump’s patch. Unknown files use the generic converter.')
    usage=(
        'Оставьте «Модель» и «Перенос» в положении «Авто», поле «Старт» — пустым. SHA-256 и найденный профиль выводятся '
        'в журнале при расчёте размера и сборке, а также сохраняются в отчёте рядом с TRD. '
        'Внутренние XOR-суммы блоков TAP проверяются отдельно: они выявляют повреждения, но не идентифицируют версию игры.'
        if ru else
        'Leave Model and Transfer on Auto and Start empty. The SHA-256 and matched profile are shown in the log during '
        'measurement/building and saved in the report beside the TRD. TAP block XOR checksums are checked separately: '
        'they detect corruption but do not identify a game version.')
    warning=(
        'Каталог не гарантирует прохождение игры на любом клоне Spectrum. Статус «Проверка на Дельте ожидается» относится '
        'к исправлениям Escape, проверенным программно без floating bus. Неподдерживаемые дампы отклоняются явно.'
        if ru else
        'This catalog does not guarantee a complete playthrough on every Spectrum clone. “Delta hardware test pending” '
        'marks Escape fixes tested in software without a floating bus. Unsupported dumps are explicitly rejected.')
    columns=('Игра / формат','SHA-256 всего файла','Сущность исправления / ограничения') if ru else ('Game / format','Full-file SHA-256','Fix / limitation')
    parts=[START, '<section id="profiles"><h2>'+escape(title)+'</h2>', '<p>'+intro+'</p>', '<p>'+usage+'</p>',
           '<p class="note">'+warning+'</p>', '<div class="table-wrap"><table class="profile-catalog"><thead><tr>'+''.join('<th scope="col">'+escape(c)+'</th>' for c in columns)+'</tr></thead><tbody>']
    for entry in PROFILES:
        parts.append('<tr data-profile="'+escape(entry.id)+'"><td><strong>'+escape(entry.title)+'</strong><br><small>'+entry.format+'</small><br><small class="profile-status '+entry.status+'">'+escape(STATUS[language][entry.status])+'</small></td><td><code class="sha256">'+entry.sha256+'</code></td><td>'+escape(entry.description(language))+'</td></tr>')
    parts.extend(['</tbody></table></div>',
        '<p>'+('Проверить сумму вручную в PowerShell:' if ru else 'Check a file hash manually in PowerShell:')+'</p>',
        '<div class="command"><code>Get-FileHash -LiteralPath "game.tap" -Algorithm SHA256</code></div>',
        '<p class="muted">'+('Таблица формируется из того же каталога, который использует конвертер. Для нового дампа добавляются его SHA-256, описание и проверенный профиль переноса.' if ru else 'This table is generated from the same catalog used by the converter. A new dump needs its SHA-256, description and verified conversion profile.')+'</p>', '</section>',END])
    return '\n'.join(parts)


def updated(content,language):
    block=render(language)
    if START in content:
        begin=content.index(START);end=content.index(END,begin)+len(END)
        content=content[:begin]+block+content[end:]
    else:
        anchor='<section id="issues">'
        if anchor not in content:raise ValueError('Missing issues section')
        content=content.replace(anchor,block+'\n'+anchor,1)
    if 'href="#profiles"' not in content:
        content=content.replace('<a href="#issues">','<a href="#profiles">'+escape(TITLES[language])+'</a><a href="#issues">',1)
    return re.sub(r'0\.10(?:\.\d+)?',VERSION,content)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for language in ('ru','en'):
        path=ROOT/'help'/f'index.{language}.html'
        content=path.read_text(encoding='utf-8-sig');result=updated(content,language)
        if args.check:
            if result!=content:raise SystemExit('Outdated generated catalog: '+str(path))
        else:path.write_text(result,encoding='utf-8')
    print('Tape catalog help: '+('current' if args.check else 'generated')+f' ({len(PROFILES)} profiles, RU/EN)')


if __name__=='__main__':main()
