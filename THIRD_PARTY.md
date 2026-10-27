# Сторонние компоненты

- **SkoolKit 10.1**, Richard Dymond — GPL-3.0-or-later.
  https://skoolkit.ca/ · https://github.com/skoolkid/skoolkit
  Используется для выполнения загрузчиков TAP/TZX и сохранения Z80-снимков.
  В автономной сборке находятся модули, расширения и ресурсы SkoolKit.
  Текст лицензии: `licenses/SkoolKit-GPL-3.0.txt`.
  Соответствующие исходники включены в `source/third-party/skoolkit-10.1.tar.gz`
  переносимой сборки; исходный архив получен с PyPI.
  При распространении сборки соблюдайте требования GPL к предоставлению исходников.
- **Z80to 1.4**, Tom Dalby — MIT.
  https://github.com/TomDDG/Z80to
  Используется как отдельный процесс для создания дисковых загрузчиков снимков.
  Текст лицензии: `licenses/Z80to-MIT.txt`.
  SHA-256 исходного x64 ZIP:
  `3176ff13f6d2d6196e69e9afcf62475a24a038e0adcdb570aa7f3bb9908264f3`.
- **Python 3.12** — PSF License; https://www.python.org/psf/license/
  Runtime включён в автономный конвертер PyInstaller. Лицензия: `licenses/Python.txt`.
- **PyInstaller 6.16.0** — GPL с исключением для загрузчика,
  https://pyinstaller.org/; используется только для упаковки. Лицензия: `licenses/PyInstaller.txt`.
- **ROM Sinclair Spectrum** входят в ресурсы SkoolKit. Из стандартного ROM также
  берутся 768 байт шрифта для меню и точного предпросмотра. Права принадлежат их владельцам;
  сведения из дистрибутива Fuse приведены в `licenses/Spectrum-ROM.txt`.

Русский шрифт извлечён по запросу пользователя из предоставленного файла
`win91_optimized.tap`: блок данных № 6, 768 байт, кодировка КОИ-7.
Исходный блок хранится в `assets/win91-font.bin`, контрольные суммы и сведения
об извлечении — в `assets/win91-font.json`. Автор и лицензия шрифта в TAP не указаны;
права принадлежат соответствующим владельцам. 62 присутствующие буквы копируются
без изменений; отсутствующие Ё/ё и Ъ/ъ построены из Е/е и Ь/ь этого же шрифта.
Полный исходный TAP в переносимую папку не включается.

Только для локальной проверки, не в `dist/TaRDulator`:

- **Fuse 1.6.0**, авторы Fuse — GPL-2.0-or-later;
  https://fuse-emulator.sourceforge.net/ . Portable Windows ZIP получен с
  официального SourceForge. SHA-256:
  `e31a12104fd5ad40b5dc2b8072a76c879cc9689e159694070ebabb754ea0e1b1`.
- ROM Pentagon и TR-DOS для Fuse взяты из пакета `releases/boot.rom` проекта
  https://github.com/MiSTer-devel/ZX-Spectrum_MISTer . Срезы по 16 КиБ:
  `0x4000` — TR-DOS, `0x8000` — 128p-0, `0xC000` — 128p-1.
  SHA-1 TR-DOS: `e1575ef62fcd1751ebf2205b2f8db00c1d578fd1`;
  SHA-1 128p-0: `d07fcdeca892ee80494d286ea9ea5bf3928a1aca`;
  SHA-1 128p-1: `80080644289ed93d71a1103992a154cc9802b2fa`.

Пользовательские TAP не включаются в переносимую папку приложения.
