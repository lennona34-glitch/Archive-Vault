@echo off
title Create ArchiveVault Desktop Shortcut
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop');" ^
    "$shortcutPath = Join-Path $desktop 'ArchiveVault.lnk';" ^
    "$appDir = '%~dp0'.TrimEnd('\');" ^
    "$target = Join-Path $appDir '.venv\Scripts\pythonw.exe';" ^
    "$ico = Join-Path $appDir 'assets\archivevault.ico';" ^
    "$wsh = New-Object -ComObject WScript.Shell;" ^
    "$s = $wsh.CreateShortcut($shortcutPath);" ^
    "$s.TargetPath = $target;" ^
    "$s.Arguments = 'run.py';" ^
    "$s.WorkingDirectory = $appDir;" ^
    "$s.IconLocation = \"$ico, 0\";" ^
    "$s.Description = 'ArchiveVault - Internet Archive Downloader & Explorer';" ^
    "$s.Save();" ^
    "Write-Host 'Desktop shortcut successfully created at:' $shortcutPath -ForegroundColor Green"

echo.
echo Done! You can now launch ArchiveVault from your Desktop.
pause
