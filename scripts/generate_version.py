"""Generate C# version metadata from src/app_version.py."""
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
version = runpy.run_path(str(ROOT / 'src/app_version.py'))['VERSION']
if not re.fullmatch(r'0|[1-9][0-9]*', version.split('.')[0]) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
    raise SystemExit('Expected a numeric MAJOR.MINOR.PATCH version')
target = ROOT / '.work/VersionInfo.cs'
target.parent.mkdir(exist_ok=True)
target.write_text(
    '[assembly: System.Reflection.AssemblyVersion("' + version + '.0")]\n'
    '[assembly: System.Reflection.AssemblyFileVersion("' + version + '.0")]\n'
    'namespace Tap2Trd { internal static class AppVersion { '
    'internal const string Value = "' + version + '"; } }\n', encoding='utf-8')
print('Application version: ' + version)
