param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force '.tools\python-packages','.tools\z80to','.tools\sources' | Out-Null
& $Python -m pip install --disable-pip-version-check --target .tools/python-packages -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
$archive = Join-Path $PSScriptRoot '.tools\z80to\Z80to_v1.4_x64.zip'
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/TomDDG/Z80to/main/Z80to_v1.4_x64.zip' -OutFile $archive
$expected = '3176ff13f6d2d6196e69e9afcf62475a24a038e0adcdb570aa7f3bb9908264f3'
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Z80to archive checksum mismatch.' }
Expand-Archive -LiteralPath $archive -DestinationPath '.tools\z80to' -Force
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/TomDDG/Z80to/main/LICENSE' -OutFile '.tools\z80to\LICENSE'
$metadata = Invoke-RestMethod -Uri 'https://pypi.org/pypi/skoolkit/10.1/json'
$source = $metadata.urls | Where-Object packagetype -EQ 'sdist' | Select-Object -First 1
$sourcePath = Join-Path $PSScriptRoot '.tools\sources\skoolkit-10.1.tar.gz'
Invoke-WebRequest -Uri $source.url -OutFile $sourcePath
if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'e71f0bac2bd38de1eacbb58650e95d43082351a1e9ecb8edecb11da112d02383') { throw 'SkoolKit source checksum mismatch.' }
Write-Host 'Dependencies installed in .tools. Run build.ps1 next.'
