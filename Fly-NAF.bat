@echo off
cd /d "%~dp0"
uv run python run.py %*
if errorlevel 1 pause
