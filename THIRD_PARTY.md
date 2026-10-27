# Сторонние компоненты / Third-party notices

- **SkoolKit 10.1**, Richard Dymond и участники проекта — GPL-3.0-or-later.
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
- **Python 3.12**, Python Software Foundation и участники проекта — PSF License; https://www.python.org/psf/license/
  Runtime включён в автономный конвертер PyInstaller. Лицензия: `licenses/Python.txt`.
- **OpenSSL 3.x**, The OpenSSL Project, Eric A. Young, Tim J. Hudson — Apache-2.0.
  https://www.openssl.org/ · https://github.com/openssl/openssl
  Библиотеки libssl и libcrypto входят в упакованную среду Python.
  Лицензия: `licenses/OpenSSL-Apache-2.0.txt`; уведомление об авторстве:
  `licenses/OpenSSL-NOTICE.txt`. Компоненты Microsoft runtime и остальные
  уведомления Python описаны в `licenses/Python.txt`.
- **PyInstaller 6.16.0**, авторы и участники PyInstaller — GPL с исключением для загрузчика,
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

## English: components and acknowledgments

TaRDulator's own code is GPL-3.0-or-later; see [LICENSE](LICENSE) and
[LICENSING.md](LICENSING.md). This does not replace the terms below.

- **SkoolKit 10.1**, Richard Dymond and contributors — GPL-3.0-or-later.
  [Website](https://skoolkit.ca/) · [Source](https://github.com/skoolkid/skoolkit).
  Used for TAP/TZX loader emulation and Z80 snapshots. The portable application
  contains SkoolKit modules, extensions and resources.
  License: `licenses/SkoolKit-GPL-3.0.txt`. Corresponding sources from PyPI
  are included as `source/third-party/skoolkit-10.1.tar.gz`.
- **Z80to 1.4**, Tom Dalby (TomDDG) — MIT.
  [Source](https://github.com/TomDDG/Z80to).
  Runs as a separate process to compress snapshots and generate disk loaders.
  License: `licenses/Z80to-MIT.txt`. Original x64 ZIP SHA-256:
  `3176ff13f6d2d6196e69e9afcf62475a24a038e0adcdb570aa7f3bb9908264f3`.
- **Python 3.12**, Python Software Foundation and contributors.
  The runtime is bundled with the frozen converter.
  [PSF licensing](https://www.python.org/psf/license/); the full set of included
  notices is in `licenses/Python.txt`.
- **OpenSSL 3.x**, The OpenSSL Project, Eric A. Young, Tim J. Hudson — Apache-2.0.
  [Website](https://www.openssl.org/) · [Source](https://github.com/openssl/openssl).
  The libssl and libcrypto libraries are bundled with Python.
  License: `licenses/OpenSSL-Apache-2.0.txt`; copyright notice:
  `licenses/OpenSSL-NOTICE.txt`. Microsoft runtime components and the other
  Python notices are covered in `licenses/Python.txt`.
- **PyInstaller 6.16.0**, PyInstaller authors and contributors.
  [Website](https://pyinstaller.org/). Used for standalone packaging.
  GPL with a bootloader exception; see `licenses/PyInstaller.txt`.
- **Sinclair ZX Spectrum ROMs** are included among SkoolKit's resources.
  The standard menu font also uses 768 bytes from the ROM.
  Copyright remains with the respective owners. The notices supplied with
  Fuse are preserved in `licenses/Spectrum-ROM.txt`; these resources are not
  relicensed under the application's GPL.

**Windows’91 Cyrillic font.** The glyphs were extracted from data block 6
of `win91_optimized.tap`: 768 bytes in KOI-7 encoding. The original block
is `assets/win91-font.bin`; provenance and hashes are in
`assets/win91-font.json`. The supplied tape does not identify the font's
author or license. Rights remain with the respective owners; no GPL grant
is made for these glyphs. The 62 available letters are copied unchanged;
missing Ё/ё and Ъ/ъ are constructed from Е/е and Ь/ь. The complete tape
is not distributed.

**Local development tools, not shipped with the application:**

- **Fuse 1.6.0**, the Fuse authors — GPL-2.0-or-later.
  [Website](https://fuse-emulator.sourceforge.net/).
  The Windows ZIP came from official SourceForge distribution. SHA-256:
  `e31a12104fd5ad40b5dc2b8072a76c879cc9689e159694070ebabb754ea0e1b1`.
- Pentagon and TR-DOS ROMs used locally with Fuse came from
  `releases/boot.rom` in
  [ZX-Spectrum_MISTer](https://github.com/MiSTer-devel/ZX-Spectrum_MISTer).
  The 16 KiB slices at 0x4000, 0x8000 and 0xC000 are TR-DOS, 128p-0 and 128p-1;
  their hashes are recorded in the Russian section above.

Game tapes, local emulator installations and those development ROMs are
not included in the application archive. Thanks to the component authors
and the Spectrum community for making these tools and resources available.
