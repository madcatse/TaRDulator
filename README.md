# ТаРДулятор / TaRDulator

<img src="assets/branding/tardulator-logo-v3-delta-cartoon.png" alt="ТаРДулятор — Дельта-С, кассета и дискета" width="560">

**TAP/TZX → TR-DOS для ZX Spectrum: сборники с редактируемым меню и запуск отдельных программ.**

Portable Windows application that converts ZX Spectrum tapes to TR-DOS disk images, with a visual menu editor and Russian / English interface.

[![Windows build](https://github.com/madcatse/TaRDulator/actions/workflows/windows.yml/badge.svg)](https://github.com/madcatse/TaRDulator/actions/workflows/windows.yml)

[Скачать / Download](https://github.com/madcatse/TaRDulator/releases) · [Руководство](USAGE.md) · [English](#english) · [Изменения](CHANGELOG.md) · [Разработка и релизы](RELEASING.md)

Текущая версия: **0.10.1**. Репозиторий закрытый; версия выпущена как **предварительная**. Статус лицензии собственного кода и происхождение ресурсов описаны в [LICENSING.md](LICENSING.md) и [THIRD_PARTY.md](THIRD_PARTY.md).

## Быстрый старт

1. В [Releases](https://github.com/madcatse/TaRDulator/releases) скачайте `TaRDulator-v0.10.1-win-x64.zip`.
2. Распакуйте **всю папку** `TaRDulator` и запустите `TaRDulator.exe`. Нужна Windows 10/11 x64 с .NET Framework 4.8; Python устанавливать не требуется.
3. Добавьте TAP/TZX, задайте подписи и расположение пунктов меню. Для одной игры можно выбрать **«Одна программа без меню»**.
4. Нажмите **«Рассчитать размер»**, затем **«Создать TRD»**.
5. Загрузите диск на компьютере или в эмуляторе с Beta Disk / TR-DOS. Из TR-DOS выполните `RUN "boot"`, если автозапуск не сработал.

Для обычной конвертации оставьте модель и перенос **«Авто»**, а поле **«Старт»** пустым. Кнопка **«Помощь»** или F1 открывает подробное руководство без подключения к сети.

Игры в комплект не входят. Исходные TAP/TZX не изменяются. Файл `.report.json` рядом с TRD содержит хеши исходников, настройки, журнал и сведения о переносе.

## Возможности

- TAP и поддерживаемые TZX, загрузка в режиме 48К / 128К, сохранение состояния AY.
- TRD на 640 КиБ: число программ ограничено свободным местом и каталогом; до 16 пунктов на страницу меню.
- Редактор фона, цветов и размещения надписей; кириллица; сохранение макетов `.t2menu`.
- Русский и английский интерфейс и автономная справка.
- Каталог особых лент: точная SHA-256 определяет профиль загрузки или исправление; патчи дополнительно проверяют исходные инструкции.
- Перенос известных многозагрузочных программ и явный отказ для известных неподдерживаемых дампов.

## Что нового в 0.10.1

Исправления проверенных дампов **Castle Escape, Forest Escape и Pyramid Escape** заменяют ожидание floating bus программной задержкой. Добавлены общий каталог SHA-256 и таблицы специальных профилей в справке. Подробности: [CHANGELOG.md](CHANGELOG.md) и [ESCAPE_COMPATIBILITY.md](ESCAPE_COMPATIBILITY.md).

**Проверка Escape на реальной Дельте 128К + AY ещё требуется.** Автоматические проверки при отсутствии floating bus проходят; успешный запуск на Fuse или Spectaculator/Pentagon не доказывает совместимость с Дельтой.

Не всякая ленточная программа переносится универсально. Поздняя подгрузка, нестандартные загрузчики и зависимости от конкретного железа требуют отдельных профилей. Проверенные Castlevania EN/RU и Dizzy 8 пока отклоняются. Полные хеши и ограничения — в [каталоге справки](help/index.ru.html#profiles) и [описании стратегий](LOADING_STRATEGIES.md).

## Документация и состав проекта

| Раздел | Содержание |
| --- | --- |
| [USAGE.md](USAGE.md) | Работа с программой, параметры, меню и JSON-интерфейс движка |
| [help/](help/) | Автономная справка на русском и английском |
| [src/](src/) | C# / WinForms интерфейс и Python-движок |
| [tests/](tests/) | Проверки форматов, загрузки, патчей, графики и интерфейса |
| [assets/](assets/) | Шрифты, логотипы и иконка |
| [scripts/](scripts/) | Проверки, генерация справки и упаковка релиза |
| [VALIDATION.md](VALIDATION.md) | Результаты предыдущих проверок и их ограничения |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Изменения кода и сообщения об ошибках |
| [RELEASING.md](RELEASING.md) | Сборка, проверки и порядок выпуска версий |
| [THIRD_PARTY.md](THIRD_PARTY.md) / [licenses/](licenses/) | Сторонние компоненты и тексты лицензий |

Готовая программа распространяется через Releases. Игры, локальные тестовые ROM, эмуляторы, зависимости и промежуточные файлы в Git не включены. Ресурсы ROM, входящие в SkoolKit и необходимые движку, описаны в THIRD_PARTY.md.

## Сборка из исходников

Windows x64, Python 3.12 x64 с pip и .NET Framework 4.8:

```powershell
.\setup.ps1
.\build.ps1
$env:PYTHONPATH = "$PWD\.tools\python-packages"
python scripts/check_release.py
python scripts/package_release.py
```

Если `python` не находится, передайте путь к интерпретатору через `-Python` в оба PowerShell-скрипта и используйте его в остальных командах. `build.ps1` запускает Python-тесты, проверки графики и WinForms, затем собирает автономный движок. Локальные проверки с игровыми TAP пропускаются, если коллекция отсутствует.

GitHub Actions повторяет сборку на чистой Windows, проверяет переносимый движок и создаёт ZIP с исходниками, лицензиями, `BUILD_INFO.json` и отдельной SHA-256. Условия публикации описаны в [RELEASING.md](RELEASING.md).

## English

Download the **win-x64 ZIP** from [Releases](https://github.com/madcatse/TaRDulator/releases), extract the complete folder, and run `TaRDulator.exe`. Requires Windows 10/11 x64 and .NET Framework 4.8. Python is bundled. Select **English** beside the logo.

Add your TAP/TZX files, edit the disk menu, and choose **Create TRD**. For one title, select **One program without a menu**. Keep model and transfer on **Auto** and leave **Start** blank unless the compatibility documentation specifies otherwise. Load the disk using Beta Disk / TR-DOS and run `RUN "boot"` if needed.

Version **0.10.1** adds exact-hash compatibility profiles and floating-bus patches for the verified Escape trilogy dumps. **Physical Delta 128K + AY testing remains pending.** Not every tape is supported; filename matching is never sufficient to apply a special patch.

The application works offline and does not modify input tapes. No games are included. Use **Help / F1** for the bundled English manual; see [release notes](releases/v0.10.1.md), [third-party notices](THIRD_PARTY.md) and [license status](LICENSING.md). This is a preliminary release in a private repository.
