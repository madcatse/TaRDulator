# Участие в разработке / Contributing

Изменения готовятся в тематической ветке и проходят pull request в `main`.
Перед отправкой запустите `build.ps1` и `scripts/check_release.py`; порядок
установки зависимостей и выпуска описан в [RELEASING.md](RELEASING.md).

При ошибке укажите версию, ожидаемое и фактическое поведение, журнал конвертации
и параметры. Для проблем с играми используйте шаблон **Tape compatibility**:
нужны полный SHA-256 TAP/TZX, модель компьютера, расширения RAM/AY и TR-DOS.
Не прикладывайте игровые образы, ROM, локальные настройки или персональные данные.

Новый особый дамп добавляется в `src/tape_catalog.py` по полной SHA-256.
Проверяйте сигнатуры кода перед патчем, добавляйте содержательную регрессионную
проверку и обновляйте справку командой `python scripts/generate_profile_help.py`.
Отмечайте отдельно проверки в эмуляторе и на реальном железе.

Own code is licensed under GPL-3.0-or-later; see [LICENSING.md](LICENSING.md). Do not add
third-party code or assets without recording their origin and license.
Use a topic branch and a pull request. Include relevant validation results
and exact tape hashes in compatibility reports; do not upload game images.
