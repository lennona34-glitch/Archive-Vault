@echo off
title ArchiveVault - Internet Archive Downloader
cd /d "%~dp0"

echo ========================================================
echo   ArchiveVault - Internet Archive Downloader & Explorer
echo ========================================================
echo Starting application...

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" run.py
) else (
    uv run python run.py
)
