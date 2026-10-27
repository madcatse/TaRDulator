"""Interface messages only. User filenames, game titles and layouts are data."""
import json
from pathlib import Path

language = 'ru'
_english = json.loads(Path(__file__).with_name('engine.en.json').read_text(encoding='utf-8'))


def set_language(value):
    global language
    language = 'en' if value == 'en' else 'ru'


def tr(message, *args):
    template = _english.get(message, message) if language == 'en' else message
    return template.format(*args) if args else template
