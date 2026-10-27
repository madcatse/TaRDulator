@echo off
if not exist "%~dp0.tools\fuse\fuse.exe" (
  echo Fuse is not installed in .tools\fuse.
  pause
  exit /b 1
)
if not exist "%~dp0output\FirstCollection.trd" (
  echo output\FirstCollection.trd was not found.
  pause
  exit /b 1
)
pushd "%~dp0.tools\fuse"
start "" "fuse.exe" --machine pentagon "%~dp0output\FirstCollection.trd"
popd
