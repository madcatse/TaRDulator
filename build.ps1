param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.tools\python-packages'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'Install .NET Framework 4.8 development tools.' }
if (-not (Test-Path -LiteralPath '.tools\z80to\Z80to.exe')) { throw 'Run setup.ps1 first.' }
New-Item -ItemType Directory -Force 'assets','.work','output','dist\TaRDulator\engine','dist\TaRDulator\licenses' | Out-Null
& $Python scripts\generate_version.py
if ($LASTEXITCODE -ne 0) { throw 'Version generation failed.' }
if (-not (Test-Path -LiteralPath '.tools\sources\skoolkit-10.1.tar.gz')) { throw 'SkoolKit corresponding source is required. Run setup.ps1.' }
$romBytes = [System.IO.File]::ReadAllBytes((Join-Path $env:PYTHONPATH 'skoolkit\resources\48.rom'))
[System.IO.File]::WriteAllBytes((Join-Path $PSScriptRoot 'assets\font.bin'), $romBytes[15616..16383])
& $Python scripts\make_font.py
if ($LASTEXITCODE -ne 0) { throw 'Font build failed.' }
& $compiler /nologo /target:exe /out:.work\MakeIcon.exe /reference:System.Drawing.dll scripts\MakeIcon.cs
if ($LASTEXITCODE -ne 0) { throw 'Icon builder compilation failed.' }
& '.\.work\MakeIcon.exe' 'assets\branding\tardulator-logo-v3-delta-cartoon.png' 'assets\branding\TaRDulator.ico'
if ($LASTEXITCODE -ne 0) { throw 'Icon build failed.' }
$brandingResources = @('/resource:assets\branding\tardulator-logo-v3-delta-cartoon.png,branding.ru', '/resource:assets\branding\tardulator-logo-v5-en-clean.png,branding.en', '/resource:assets\branding\TaRDulator.ico,branding.icon')
& $Python scripts\generate_profile_help.py
if ($LASTEXITCODE -ne 0) { throw 'Profile help generation failed.' }
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $compiler /nologo /target:winexe /optimize+ /out:dist\TaRDulator\TaRDulator.exe /win32icon:assets\branding\TaRDulator.ico @brandingResources /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /resource:src\menu_font.bin,spectrum.font /resource:src\ui.en.json,ui.en.json .\.work\VersionInfo.cs .\src\App.cs .\src\Branding.cs .\src\LanguageMenu.cs .\src\GameOptions.cs .\src\MenuEditor.cs .\src\MenuLayout.cs .\src\SpectrumScreen.cs .\src\UiText.cs
if ($LASTEXITCODE -ne 0) { throw 'GUI build failed. Close ТаРДулятор before building.' }
& $compiler /nologo /target:exe /out:.work\ScreenTests.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /resource:src\menu_font.bin,spectrum.font /resource:src\ui.en.json,ui.en.json .\tests\ScreenTests.cs .\src\MenuLayout.cs .\src\SpectrumScreen.cs .\src\UiText.cs
if ($LASTEXITCODE -ne 0) { throw 'Graphics check compilation failed.' }
& '.\.work\ScreenTests.exe'
if ($LASTEXITCODE -ne 0) { throw 'Graphics checks failed.' }
& $compiler /nologo /target:exe /main:Tap2Trd.UiTests /out:.work\UiTests.exe @brandingResources /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /resource:src\menu_font.bin,spectrum.font /resource:src\ui.en.json,ui.en.json .\tests\UiTests.cs .\.work\VersionInfo.cs .\src\App.cs .\src\Branding.cs .\src\LanguageMenu.cs .\src\GameOptions.cs .\src\MenuEditor.cs .\src\MenuLayout.cs .\src\SpectrumScreen.cs .\src\UiText.cs
if ($LASTEXITCODE -ne 0) { throw 'UI checks compilation failed.' }
& '.\.work\UiTests.exe'
if ($LASTEXITCODE -ne 0) { throw 'UI checks failed.' }
& $Python -m PyInstaller --noconfirm --onedir --name TaRDulator.Engine --distpath .work/frozen --workpath .work/pyinstaller --specpath .work --add-data ((Join-Path $PSScriptRoot 'src\menu_font.bin') + ';.') --add-data ((Join-Path $PSScriptRoot 'src\engine.en.json') + ';.') --collect-all skoolkit src/engine.py
if ($LASTEXITCODE -ne 0) { throw 'Engine build failed.' }
Copy-Item -Path '.work\frozen\TaRDulator.Engine\*' -Destination 'dist\TaRDulator\engine' -Recurse -Force
Copy-Item -LiteralPath '.tools\z80to\Z80to.exe' -Destination 'dist\TaRDulator\engine\Z80to.exe'
Copy-Item -LiteralPath '.tools\z80to\LICENSE' -Destination 'dist\TaRDulator\licenses\Z80to-MIT.txt'
Copy-Item -LiteralPath '.tools\python-packages\skoolkit-10.1.dist-info\licenses\COPYING' -Destination 'dist\TaRDulator\licenses\SkoolKit-GPL-3.0.txt'
Copy-Item -Path 'licenses\*' -Destination 'dist\TaRDulator\licenses' -Force
Copy-Item -LiteralPath 'README.md','USAGE.md','CONTRIBUTING.md','THIRD_PARTY.md','VALIDATION.md','LOADING_STRATEGIES.md','ESCAPE_COMPATIBILITY.md','CHANGELOG.md','LICENSING.md','RELEASING.md' -Destination 'dist\TaRDulator'
New-Item -ItemType Directory -Force 'dist\TaRDulator\help' | Out-Null
Copy-Item -Path 'help\*' -Destination 'dist\TaRDulator\help' -Force
New-Item -ItemType Directory -Force 'dist\TaRDulator\source\src','dist\TaRDulator\source\tests','dist\TaRDulator\source\licenses','dist\TaRDulator\source\third-party' | Out-Null
New-Item -ItemType Directory -Force 'dist\TaRDulator\source\assets','dist\TaRDulator\source\scripts' | Out-Null
New-Item -ItemType Directory -Force 'dist\TaRDulator\source\help' | Out-Null
Copy-Item -Path 'help\*' -Destination 'dist\TaRDulator\source\help' -Force
New-Item -ItemType Directory -Force 'dist\TaRDulator\source\assets\branding' | Out-Null
Copy-Item -LiteralPath 'assets\branding\tardulator-logo-v3-delta-cartoon.png','assets\branding\tardulator-logo-v5-en-clean.png','assets\branding\TaRDulator.ico' -Destination 'dist\TaRDulator\source\assets\branding' -Force
Copy-Item -LiteralPath 'assets\win91-font.bin','assets\win91-font.json','assets\font.bin' -Destination 'dist\TaRDulator\source\assets' -Force
Copy-Item -Path 'scripts\*.py','scripts\*.cs' -Destination 'dist\TaRDulator\source\scripts' -Force
Copy-Item -LiteralPath 'src\menu_font.bin','src\ui.en.json','src\engine.en.json' -Destination 'dist\TaRDulator\source\src' -Force
Copy-Item -Path 'src\*.cs','src\*.py' -Destination 'dist\TaRDulator\source\src' -Force
Copy-Item -Path 'tests\*.cs','tests\*.py' -Destination 'dist\TaRDulator\source\tests' -Force
Copy-Item -Path 'dist\TaRDulator\licenses\*' -Destination 'dist\TaRDulator\source\licenses' -Force
Copy-Item -LiteralPath 'build.ps1','setup.ps1','requirements-build.txt','README.md','USAGE.md','CONTRIBUTING.md','THIRD_PARTY.md','VALIDATION.md','LOADING_STRATEGIES.md','ESCAPE_COMPATIBILITY.md','CHANGELOG.md','LICENSING.md','RELEASING.md' -Destination 'dist\TaRDulator\source' -Force
Copy-Item '.tools\sources\skoolkit-10.1.tar.gz' 'dist\TaRDulator\source\third-party' -Force
Write-Host 'Ready: dist\TaRDulator\TaRDulator.exe'

foreach ($folder in @('.github', 'releases')) {
    Copy-Item -LiteralPath $folder -Destination 'dist\TaRDulator\source' -Recurse -Force
}
Copy-Item -LiteralPath '.gitignore','.gitattributes','OpenExample.cmd' -Destination 'dist\TaRDulator\source' -Force
