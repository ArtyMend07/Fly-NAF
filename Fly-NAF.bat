@echo off
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

where uv >nul 2>nul
if not errorlevel 1 goto run

echo Installing uv, the tool that prepares Python for Fly-NAF. This happens once.
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
where uv >nul 2>nul
if errorlevel 1 goto nouv

:run
uv run python run.py %*
if errorlevel 1 pause
exit /b

:nouv
echo uv could not be installed. Install it from https://docs.astral.sh/uv/getting-started/installation/ and open this file again.
pause
exit /b 1
