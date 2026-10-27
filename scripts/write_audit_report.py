"""Create the offline, evidence-linked report for games48-128.zip."""
from pathlib import Path
import hashlib,html,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/games48-128'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def esc(value):return html.escape(str(value))

def main():
    inventory=read('inventory.json')
    assert hashlib.sha256((ROOT/'taps/games48-128.zip').read_bytes()).hexdigest()==inventory['archive_sha256']
    for item in inventory['files']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
    baseline=read('baseline.json');best=read('best-load.json')
    states=read('fuse-collections.json');stack=read('fuse-chase-stack-excluded.json')
    assert len(baseline)==28 and len(states)==13
    assert all(r['passed'] for r in states if r['id'] not in (2,3))
    assert len(stack)==2 and all(r['passed'] for r in stack)
    assert len(read('fuse-playing-state.json'))==3 and all(r['passed'] for r in read('fuse-playing-state.json'))
    details={
        0:'В 48К TZX останавливается перед данными следующих уровней. В 128К загружаются все банки. Нужен увеличенный лимит времени.',
        1:'48К остаётся на STOP TAPE. В 128К загружаются все банки; прежнего лимита 300 секунд недостаточно.',
        2:'Для сборника уровней выбран 128К. В 48К остаётся экран STOP THE TAPE. Под стеком меняются 28 байт при восстановлении Z80to.',
        3:'Для сборника уровней выбран 128К. Нужен увеличенный лимит времени. Под стеком меняются 28 байт при восстановлении Z80to.',
        4:'В 48К команда TZX пропускает последний блок 16385 байт. В 128К он загружается в дополнительную память; первый игровой экран работает.',
        5:'Работает в обеих моделях; для варианта с дополнительными данными выбран 128К. Проверен выход из заставки в игру.',
        6:'Русская версия: загружается в обеих моделях. Проверен запуск 128К с сохранением дополнительных банков.',
        7:'48К доходит до меню, но автоматическая загрузка остаётся незавершённой. 128К проходит с увеличенным лимитом времени.',
        8:'Русская версия: загружается в обеих моделях. Проверен первый игровой экран в 128К.',
        9:'Проверен реальный запуск в 48К. После загрузочной картинки нужна клавиша, затем 1 в меню. Дополнительные банки игры в 128К не обнаружены.',
        10:'В 48К игра доходит до меню, оставляя последний блок TAP непрочитанным; версия 0.4 отклоняет такой результат. В 128К блок загружается, первый заезд работает.',
        11:'Поведение аналогично TAP-варианту Grand Prix 2. В 128К загрузка завершается и первый заезд работает.',
        12:'В 48К TZX останавливается перед блоками уровней. В 128К загружены все банки; проверен первый уровень. Нужен увеличенный лимит времени.',
        13:'Обе модели останавливаются на блоке 36 (пауза с длительностью 0). Блоки 37 и 39 по 7838 байт не загружены. Первый заезд работает, полный перенос не подтверждён; в сборники не включён.'
    }
    rows=[];summary=[]
    for item in inventory['files']:
        i=item['id'];model='48' if i==9 else '128'
        chosen=next(r for r in best if r['id']==i and r['machine']==model)
        original=next(r for r in baseline if r['id']==i and r['machine']=='48')
        stock=('TZX не поддерживается интерфейсом' if not item['accepted_by_0_4'] else
               ('Снимок получен при настройках по умолчанию' if original['complete'] else 'По умолчанию: тайм-аут / загрузка не завершена'))
        status='Запуск подтверждён' if i!=13 else 'Полный перенос не подтверждён'
        if i in (2,3):status+='; оговорка о стеке'
        entry={'id':i,'file':item['name'],'sha256':item['sha256'],'recommended_model':model if i!=13 else None,
               'stock_0_4':stock,'status':status,'details':details[i],
               'timeout_seconds':1200 if chosen['tag']=='long' else 300,'full_playthrough_verified':False}
        summary.append(entry)
        rows.append(f'<tr><td>{i:02d}</td><td class="filename">{esc(item["name"])}</td><td>{model+"К" if i!=13 else "не определено для полного переноса"}</td><td>{esc(stock)}</td><td>{esc(details[i])}</td></tr>')
    (OUT/'summary.json').write_text(json.dumps({'date':'2026-10-21','application_modified':False,'archive_unchanged':True,
        'files':summary,'important':'Successful tape completion or a title screen does not prove full-game compatibility.'},ensure_ascii=False,indent=2),encoding='utf-8')
    body='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка games48-128.zip</title><style>
body{font:16px/1.55 system-ui,Segoe UI,sans-serif;color:#202a33;background:#f3f5f7;margin:0}main{max-width:1200px;margin:auto;padding:36px 24px 60px}h1{font-size:32px;margin:6px 0 12px}h2{font-size:23px;margin-top:32px}p{max-width:1000px}.date{color:#61717f}.card{background:white;border:1px solid #dce2e7;border-radius:12px;padding:20px;margin:18px 0}.notice{border-left:5px solid #cb7a13;background:#fff8eb}a{color:#1464aa}table{width:100%;border-collapse:collapse;font-size:14px;background:white}td,th{padding:12px;border:1px solid #dce2e7;vertical-align:top;text-align:left}th{background:#eaf0f5}.filename{min-width:210px;overflow-wrap:anywhere}td:nth-child(5){min-width:260px}.scroll{overflow-x:auto}.gallery{display:flex;gap:18px;flex-wrap:wrap}.gallery figure{margin:0;flex:1;min-width:256px}.gallery img{width:100%;max-width:512px;image-rendering:pixelated;background:black}figcaption{font-size:14px;color:#52616d}code{font-size:.9em;background:#eef1f3;padding:2px 5px}li{margin:8px 0}.metric{display:inline-block;padding:9px 14px;margin:4px;border-radius:6px;background:#edf4fb}small{color:#52616d}</style><main>
<div class="date">21 октября 2026 · TAP2TRD 0.4 · SkoolKit 10.1 · Fuse 1.6.0 / Pentagon</div>
<h1>Проверка games48-128.zip</h1>
<p>Для 13 файлов подготовлены экспериментальные TR-DOS диски с подтверждённым запуском. Для WEC Le Mans подтверждён только первый заезд: часть ленты остаётся за командой остановки. Автоматическую поддержку всего архива в обычной версии 0.4 считать готовой нельзя.</p>
<div><span class="metric">14 файлов: 7 TAP + 7 TZX</span><span class="metric">28 первичных загрузок: 48К и 128К</span><span class="metric">2 тестовые дискеты</span></div>
<div class="card notice"><b>Это отчёт о проверке, не новая версия программы.</b> EXE и исходный конвертер 0.4 не изменялись. Тестовые сборники созданы из отдельно подготовленных снимков с выбранной моделью и, где потребовалось, лимитом 1200 эмулируемых секунд вместо 300. В интерфейсе 0.4 по умолчанию стоит 48К, автоматического определения модели нет, TZX не принимается.</div>
<h2>Что проверялось</h2><ol>
<li>Проверены все члены ZIP и структура семи TAP; исходный архив и извлечённые файлы сохранены без изменений. Каждый файл загружен в моделях 48К и 128К. Неудачные длинные загрузки повторены с лимитом 1200 эмулируемых секунд.</li>
<li>Подготовленные снимки упакованы Z80to и запущены через настоящее меню и TR-DOS в Fuse без кассеты. Проверены исходный PC, SP/BC/DE/HL/IX/IY, 459 байт буфера принтера и системных переменных, выборочные байты остальной RAM и пробы во всех восьми банках 128К. После восстановления выполнено ещё 500 кадров.</li>
<li>Обычные нажатия клавиш для выхода из заставки и запуска первого уровня проверены отдельно через клавиатурную матрицу SkoolKit, без ленты и без изменений кода игр. Затем состояния первых уровней Batman, Chase H.Q. и RoboCop дополнительно упакованы на TR-DOS, восстановлены и продолжены в Fuse.</li>
<li>Проверены все 13 пунктов окончательных двух тестовых дискет. Для 11 совпали все проверяемые байты; для обоих Chase H.Q. выявлена и отдельно исследована рабочая область Z80to под стеком.</li></ol>
<p>Доступ к окну Fuse через средство управления окнами не подтвердился вовремя, поэтому проверка выполнена через поддерживаемый отладчик Fuse. Иллюстрации ниже получены чтением видеопамяти Fuse в четырёх запусках после 500 кадров; они показывают состояние игры, но не являются видеозаписью или доказательством полного прохождения.</p>
<h2>Первый уровень после переноса: Fuse</h2><div class="gallery">
<figure><img src="fuse-playing-01-128.png" alt="Batman в Fuse"><figcaption>Batman: первый уровень после восстановления состояния игры.</figcaption></figure>
<figure><img src="fuse-playing-03-128.png" alt="Chase HQ в Fuse"><figcaption>Chase H.Q.: первый заезд после восстановления состояния игры.</figcaption></figure>
<figure><img src="fuse-playing-12-128.png" alt="RoboCop в Fuse"><figcaption>RoboCop: первый уровень после восстановления состояния игры.</figcaption></figure></div>
<h2>Результат по каждому файлу</h2><p>Рекомендованная модель относится именно к этим файлам и их SHA-256. Надпись «48K–128K» в имени не является способом автоматического определения модели. Для Dizzy и Grand Prix 2 выбран 128К для сохранения дополнительных данных; это не означает, что сами игры принципиально не могут работать в 48К.</p>
<div class="scroll"><table><thead><tr><th>ID</th><th>Файл</th><th>Модель для тестового переноса</th><th>Обычная версия 0.4</th><th>Что установлено</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<h2>Оговорка о Chase H.Q.</h2><p>У обоих вариантов при снятии начального снимка SP = 23544. Z80to меняет 28 байт по адресам 23516–23543, непосредственно под стеком. Это рабочий код восстановления, а не потеря целого банка. Строгая проверка намеренно сохраняет результат «несовпадение». Дополнительная проверка с исключением 32 байт ниже SP прошла: остальные проверяемые байты и банки совпали. Первый заезд работает. Полную побайтовую идентичность снимку заявлять нельзя.</p>
<h2>Почему WEC Le Mans пока исключён</h2><p>В обеих моделях загрузчик достигает блока 36 TZX: паузы с длительностью 0. Сообщение <code>Tape finished</code> относится к этой части ленты. Блоки 37 и 39, каждый по 7838 байт, в снимок не попадают. Первый заезд запускается, но назначение и последующее использование оставшихся блоков в игре не подтверждены. Принудительное игнорирование паузы само по себе не докажет, что игра загрузила эти данные. Этот файл не включён в тестовые сборники.</p>
<h2>Что нужно доработать в программе</h2><ul>
<li>Дать длинным загрузчикам достаточное время и показывать разницу между тайм-аутом, ожиданием клавиши и остановкой ленты.</li>
<li>Добавить отдельную поддержку TZX с учётом команд остановки и оставшихся блоков; не сводить TZX к TAP простым переименованием.</li>
<li>Для проверенных файлов использовать профили по хешам. Общий автоматический выбор модели должен уметь сообщать «требуется проверка», а не угадывать по имени файла или одному сообщению о конце ленты.</li>
<li>Сохранять все необходимые банки 128К и проверять продолжение исполнения. Для многоуровневых игр следующим этапом остаётся проверка переходов между уровнями.</li></ul>
<h2>Тестовые дискеты и доказательства</h2>
<p><a href="Test-TAP.trd">Test-TAP.trd</a> — семь TAP, 441 КиБ, 53 файла. <a href="Test-TZX.trd">Test-TZX.trd</a> — шесть TZX без WEC Le Mans, 444,5 КиБ, 50 файлов. Загрузка: Pentagon с TR-DOS, <code>RUN "boot"</code>. Выбор пункта: <code>1–7</code> / <code>1–6</code>. Exolon после заставки ждёт клавишу.</p>
<p>Сборники содержат стартовые снимки после загрузки кассеты, а не состояния уже начатой игры. Это экспериментальные образцы; полного прохождения всех игр, переходов через все уровни, физического дисковода и всех вариантов аппаратуры не проверялось.</p>
<p><a href="summary.json">Сводка и хеши</a> · <a href="baseline.json">28 исходных загрузок</a> · <a href="long-load.json">Длинные загрузчики</a> · <a href="tape-stop-analysis.json">Оставшиеся блоки TZX</a> · <a href="fuse-collections.json">Окончательные дискеты в Fuse</a> · <a href="chase-stack.json">28 изменённых байт Chase H.Q.</a> · <a href="fuse-chase-stack-excluded.json">Проверка остальной памяти Chase H.Q.</a> · <a href="fuse-playing-state.json">Игровые состояния в Fuse</a></p>
<small>Архив SHA-256: '''+inventory['archive_sha256']+'''</small></main></html>'''
    (OUT/'REPORT.html').write_text(body,encoding='utf-8')
    # Portable evidence bundle, with relative links and no temporary paths needed
    # to view the report or use the two TRD images.
    destination=ROOT/'output/games48-128-audit.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(OUT.iterdir()):
            if path.suffix in ('.html','.json','.png','.trd'):
                archive.write(path,'games48-128/'+path.name)
    with zipfile.ZipFile(destination) as archive:assert archive.testzip() is None
    print(json.dumps({'report':str(OUT/'REPORT.html'),'bundle':str(destination),'bytes':destination.stat().st_size,'source_archive_unchanged':True}))


if __name__=='__main__':main()
