"""Build a local compatibility report from recorded emulator checks."""
import html
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/tricky-0.10'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
esc=html.escape


def main():
    source=read(ROOT/'.work/tricky-0.10/release/results.json')
    fuse=read(OUT/'fuse.json');frozen=read(OUT/'frozen.json');refused=read(OUT/'unsupported.json')
    regression=read(ROOT/'output/release-0.10-regression/fuse.json')
    assert len(fuse)==len(frozen)==22
    assert all(r['fuse']['passed'] for r in fuse) and all(r['passed'] for r in frozen+refused)
    assert len(regression)==24 and all(r['passed'] or r.get('with_stack_scratch',{}).get('passed') for r in regression)
    assert (OUT/'New_View_48K-last-6000.scr').read_bytes()==(ROOT/'.work/tricky-0.10/baseline/10/source-6000.scr').read_bytes()
    reasons={
        'Dizzy_7_NEW.tap':'Исправлено: снимок после распаковки устраняет ошибку упаковщика.',
        'Fearzone48_2018.tap':'Исправлено: опрос клавиатуры больше не пропускает блоки игры; все 14 блоков обработаны.',
        'yazzie128.tap':'Исправлено: проверка таймингов выполнена до снимка; устранён сброс на Pentagon.',
        'New_View_48K.tap':'Исправлено: все пять частей загружаются с дискеты по порядку, исходные CODE-блоки сохранены.',
        'MILKY2.TAP':'Общий загрузчик цепочки: вступление и основная часть сохранены; проверены 6000 кадров основной части.',
        'ECLIPSE.TAP':'Прежняя поддержка сохранена; выбран 128К с переключением экрана.',
    }
    records=[];table=[]
    for row in source:
        name=row['name'];good=row['ok'];info=row.get('info',{})
        reason=reasons.get(name,'Запуск проверен; дополнительных настроек профиля не требуется.') if good else row['error']
        modes=[r for r in fuse if r['name']==name]
        links=' · '.join(f'<a href="{esc(Path(r["disk"]).name)}">{r["mode"]}.trd</a>' for r in modes)
        record={'name':name,'sha256':row['sha256'],'supported':good,'model':info.get('load_machine'),
            'strategy':info.get('strategy'),'reason':reason,'disk_kib':info.get('bytes',0)/1024,
            'fuse_modes':[r['mode'] for r in modes if r['fuse']['passed']]}
        records.append(record)
        table.append('<tr><td>'+esc(name)+'<br><small>'+row['sha256'][:16]+'…</small></td><td class="'+('ok' if good else 'no')+'">'+('Проверен' if good else 'Не поддерживается')+'</td><td>'+str(record['model'] or '—')+'</td><td>'+esc(reason)+(('<p>'+links+'</p>') if good else '')+'</td></tr>')
    summary={'version':'0.10.0','date':'2026-10-26','files':14,'supported':11,'new_files':12,
        'new_supported':9,'unsupported':3,'fuse_launches':22,'regression_cases':24,
        'scope':'Запуск, восстановление состояния и последовательность частей демо; не полное прохождение игр.',
        'records':records}
    (OUT/'compatibility.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    pictures=read(OUT/'screens.json')+[
        {'name':'MILKY2: основная часть, 6000 кадров','path':'MILKY2-last-6000.png'},
        {'name':'New View: финал, как у оригинала','path':'New_View_48K-last-6000.png'}]
    gallery=''.join('<figure><img src="'+esc(Path(r['path']).name)+'" width="256" height="192"><figcaption>'+esc(r['name'])+'</figcaption></figure>' for r in pictures)
    page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ТаРДулятор 0.10 — проверка сложных кассет</title><style>
body{font:16px/1.6 system-ui,sans-serif;color:#202733;background:#f5f7fa;margin:0}main{max-width:1160px;margin:auto;padding:32px}
h1{line-height:1.2}h2{margin-top:32px}a{color:#075fc5}table{border-collapse:collapse;width:100%;background:white;font-size:14px}
td,th{padding:12px;border:1px solid #d8dfe8;text-align:left;vertical-align:top}td p{margin-bottom:0}small{color:#687383}
.ok{color:#116d3b}.no{color:#a73627}.lead{font-size:21px}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
figure{margin:0;padding:12px;background:white}img{image-rendering:pixelated;max-width:100%;height:auto}figcaption{font-size:13px}.scroll{overflow:auto}
li{margin-bottom:8px}</style><main>
<p>26 октября 2026 · Windows 11 x64 · Fuse 1.6.0 / Pentagon 128K</p>
<h1>ТаРДулятор 0.10: сложные TAP</h1>
<p class="lead">11 из 14 кассет создают проверенные диски. Среди 12 новых файлов работают 9; три конкретных дампа явно отмечены как неподдерживаемые.</p>
<p>Исправлены Dizzy 7 NEW, Fearzone 2018, Yazzie 128 и New View. Castlevania EN/RU и Dizzy 8 отклоняются с причиной: полный перенос оставшихся блоков не подтверждён. Профиль определяется по полному SHA-256, а не имени файла.</p>
<h2>Результат по каждому файлу</h2><div class="scroll"><table><thead><tr><th>Кассета / SHA-256</th><th>Статус</th><th>Модель</th><th>Результат и диски</th></tr></thead><tbody>'''+''.join(table)+'''</tbody></table></div>
<h2>Что проверено</h2><ul>
<li>Все 11 дисковых вариантов запущены напрямую и через меню — 22 запуска без подключённой ленты. Для снимков проверены регистры, системная область, выборки памяти и банков, затем 500 кадров исполнения.</li>
<li>New View: данные каждой из пяти частей проверены при входе; ещё 6000 кадров после последней. Финальный экран побайтно совпал с исходным снимком в Fuse. Полный оригинальный TAP также прошёл все части на 48К и Pentagon; проверена 131 точка финального экрана. Последняя часть оригинала и TRD не возвращается в BASIC; повтор всей цепочки не считается проверенным.</li>
<li>MILKY2: обе исходные части и 6000 кадров основной части. New View и MILKY2 используют один настраиваемый механизм последовательной загрузки.</li>
<li>22 образа готового EXE побайтно совпали с проверенными исходными сборками. Все три неподдерживаемых дампа проверены в RU/EN; существующий TRD при отказе сохранён.</li>
<li>45 тестов Python и проверки C# пройдены. Прежние 24 кассеты (архив games48-128.zip и десять ранее случайно выбранных TAP) прошли преобразование, сравнение с EXE и запуск в Fuse. Для двух Chase H.Q. сохраняется прежнее исключение 32 байт перед SP, нужных восстановителю Z80to.</li>
<li>Исходные 14 TAP не изменены. Проверка запуска не означает прохождения всех уровней; произвольная поздняя подгрузка пока не переводится автоматически.</li></ul>
<h2>Общие механизмы</h2><p>Обычный снимок, ROM-загрузка с отдельным опросом клавиатуры, снимок после инициализации, цепочка самостоятельных частей и проверенная резидентная ветка. Параметры игры отделены от реализации. Для нового аналогичного загрузчика можно добавить профиль и проверки, используя готовый механизм.</p>
<p><a href="../../LOADING_STRATEGIES.md">Каталог стратегий и порядок расширения</a> · <a href="../../VALIDATION.md">История проверок</a> · <a href="compatibility.json">Итоговый JSON с полными хешами</a> · <a href="fuse.json">Протокол Fuse</a> · <a href="frozen.json">Сравнение готового EXE</a> · <a href="unsupported.json">Проверки отказов RU/EN</a></p>
<h2>Экраны из Fuse</h2><p>После 500 кадров для игр и после 6000 кадров заключительных частей демо. Второй экран 128К учтён.</p><div class="gallery">'''+gallery+'''</div></main></html>'''
    (OUT/'REPORT.html').write_text(page,encoding='utf-8')
    for name in ('VALIDATION.md','README.md','LOADING_STRATEGIES.md'):
        for folder in (ROOT/'dist/TaRDulator',ROOT/'dist/TaRDulator/source'):
            shutil.copyfile(ROOT/name,folder/name)
    shutil.copyfile(Path(__file__),ROOT/'dist/TaRDulator/source/scripts'/Path(__file__).name)
    print('Report ready:',OUT/'REPORT.html')


if __name__=='__main__':main()
