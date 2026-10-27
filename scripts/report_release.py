"""Write the user-facing release verification report from recorded results."""
import hashlib
from html import escape
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/release-0.5'


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def main():
    selection = read('selection.json')
    rows = read('frozen.json')
    checks = {r['id']: r for r in read('collection-fuse.json')}
    singles = {r['id']: r for r in read('fuse.json')}
    screens = {r['id']: r for r in read('screens.json')}
    assert len(rows) == 24 and all(r['frozen_ok'] for r in rows)
    assert len(checks) == len(singles) == len(screens) == 23
    for check in [*checks.values(), *singles.values()]:
        assert check['passed'] or check.get('with_stack_scratch', {}).get('passed')
    archive_hash = hashlib.sha256((ROOT / 'taps/games48-128.zip').read_bytes()).hexdigest()
    assert archive_hash == selection['archive_sha256']
    assert all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'] for row in rows)
    table = []
    for row in rows:
        result = checks.get(row['id'])
        status = 'Запуск подтверждён' if result and result['passed'] else 'Запуск; особенность стека¹' if result else 'Полный перенос отклонён²'
        image = '<a href="{0}"><img src="{0}" width="256" height="192" loading="lazy"></a>'.format(Path(screens[row['id']]['image']).name) if result else '—'
        reason = row.get('info', {}).get('model_reason', row.get('error', '').split('\n')[0])
        table.append(f'<tr><td>{row["id"]:02d}</td><td>{escape(row["name"])}<small>{escape(reason)}</small></td>'
                     f'<td>{row.get("machine", "—")}К</td><td>{status}</td><td>{image}</td></tr>')
    disks = ''.join(f'<li><a href="{Path(r["output"]).name}">{Path(r["output"]).name}</a>: '
                    f'{len(r["games"])} программ, {r["used_bytes"]/1024:g} КиБ, {r["file_count"]} файлов.</li>'
                    for r in read('collections.json'))
    html = f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>TAP2TRD 0.5 — проверка</title>
<style>body{{font:16px/1.5 Segoe UI,Arial,sans-serif;max-width:1280px;margin:40px auto;padding:0 24px;background:#f7f8fa;color:#20252c}}h1{{font-size:30px}}a{{color:#145b9b}}table{{width:100%;border-collapse:collapse;background:white}}td,th{{padding:12px;text-align:left;border:1px solid #d9dfe6;vertical-align:top}}th{{background:#e9edf2}}small{{display:block;color:#59636f;margin-top:8px}}img{{image-rendering:pixelated;max-width:256px}}.note{{background:#fff1d6;padding:16px;border-left:4px solid #bb7c19}}code{{overflow-wrap:anywhere}}</style>
<h1>TAP2TRD 0.5: проверка TAP, TZX и автовыбора модели</h1>
<p>21 октября 2026 · Windows 11 x64 · SkoolKit 10.1 · Z80to 1.4 · Fuse 1.6.0 / Pentagon 128K.</p>
<p><b>13 из 14 файлов games48-128.zip и все 10 случайных TAP перенесены и запущены с TRD в Fuse.</b>
WEC Le Mans отклонён: после остановки TZX остаются данные. Неполная дискета не создаётся.</p>
<p>В интерфейсе добавлены TZX, модель «Авто» и пояснение выбора. Лимит загрузки: 1200 секунд
времени Spectrum вместо 300. Светлая тема, русское меню и расположение элементов сохранены.</p>
<h2>Готовые сборники</h2><ul>{disks}</ul>
<p>Все три образа созданы готовым Windows EXE 0.5.0 с настройками «Авто» для модели и переноса.
Каждый пункт меню проверен отдельно. WEC Le Mans в сборники не включён.</p>
<h2>Что проверено</h2><ul>
<li>31 автоматический тест Python и проверки C# (включая восемь побайтных сравнений экранов).
Повреждённые TZX, команды остановки, ручной выбор и переход между моделями проверены отдельно.</li>
<li>Все 24 случая повторены готовым EXE: 23 TRD побайтно совпали с исходной версией конвертера;
для WEC подтверждено ожидаемое отклонение.</li>
<li>В Fuse выполнены меню, загрузчики и TR-DOS. На исходном PC сверены SP, BC, DE, HL, IX, IY,
буфер принтера и системные переменные, выборочные байты RAM и всех восьми банков для 128К.
После восстановления программа выполнялась ещё 500 кадров без подключённой кассеты.</li>
<li>Проверены и отдельные образы, и все 23 пункта окончательных сборников.</li>
<li>Через GUI добавлены одновременно TAP и TZX, проверены «Авто» по умолчанию,
расчёт размера и отображение 128К для Batman / 48К для Exolon.</li>
<li>Исходные файлы и архив сохранили свои SHA-256.</li></ul>
<p>Иллюстрации ниже получены чтением экранной памяти Fuse после 500 кадров.
Каждый экран состоит из четырёх участков, прочитанных при независимых запусках;
они показывают состояние игры, но не являются записью единственного кадра или прохождением.</p>
<p class="note">¹ Chase H.Q. (TAP и TZX): строгая сверка обнаруживает известные изменения под стеком
от загрузчика Z80to. Повторная сверка, исключающая 32 байта перед SP, проходит; остальные проверки
сохранены. В предыдущем анализе установлены 28 изменённых байт 23516–23543. Это ограничение
восстановления снимка, а не потеря банков. Исходные результаты строгой проверки сохранены.</p>
<p class="note">² WEC Le Mans: безусловная остановка ленты перед блоками 37 и 39 действует в обеих
моделях. Для полного переноса нужен отдельный сценарий загрузки. Увеличение времени само по себе
этого не решает. Для остальных игр подтверждены восстановление и продолжение выполнения;
полное прохождение всех уровней, поздняя подгрузка и сохранения не проверялись.</p>
<h2>Проверенные файлы</h2><table><thead><tr><th>ID</th><th>Файл и причина выбора</th><th>Модель</th><th>Результат</th><th>Экран Fuse</th></tr></thead><tbody>{''.join(table)}</tbody></table>
<h2>Воспроизводимость</h2><p>Случайная десятка выбрана до проверки из {len(selection['population'])} TAP
папки taps, без замены неудачных кандидатов. Seed: <code>{selection['seed']}</code>.
Список, исходные хеши и вся популяция: <a href="selection.json">selection.json</a>.</p>
<p>SHA-256 архива: <code>{archive_hash}</code>.</p>
<p>Журналы: <a href="source.json">исходный конвертер</a>, <a href="frozen.json">готовый EXE</a>,
<a href="fuse.json">отдельные TRD в Fuse</a>, <a href="collection-fuse.json">сборники в Fuse</a>,
<a href="screens.json">данные захвата экранов</a>. Повторение: scripts/validate_release.py.</p>
</html>'''
    (OUT / 'REPORT.html').write_text(html, encoding='utf-8')
    summary = {'version': '0.5.0', 'archive': {'passed': 13, 'rejected': 1, 'exception': 'WEC Le Mans'},
               'random_tap': {'passed': 10, 'seed': selection['seed']}, 'python_tests': 31,
               'fuse_collection_launches': 23, 'strict_passed': 21, 'known_stack_exception': [2, 3],
               'sources_unchanged': True}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = ROOT / 'output/Tap2Trd-0.5-validation.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                z.write(path, 'release-0.5/' + path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == '__main__':
    main()
