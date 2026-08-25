@echo off
setlocal
title Package XG Resume Studio
cd /d "%~dp0"

REM Build a clean share zip: source + assets only.
REM Excluded automatically: data\ (user privacy), .venv, caches, logs.

set STAGE=%TEMP%\xg_resume_pkg
if exist "%STAGE%" rd /s /q "%STAGE%"
mkdir "%STAGE%"

for %%F in (*.py *.md *.txt *.toml *.bat *.cmd LICENSE .gitignore) do (
  if exist "%%F" copy /y "%%F" "%STAGE%" >nul
)
for %%D in (templates static resume_templates tests docs .github) do (
  if exist "%%D" xcopy "%%D" "%STAGE%\%%D\" /e /i /y >nul
)

REM strip caches that must never ship
for /d /r "%STAGE%" %%D in (__pycache__ .pytest_cache .ruff_cache) do (
  if exist "%%D" rd /s /q "%%D"
)

powershell -NoProfile -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%~dp0XG-Resume-Studio-share.zip' -Force"
rd /s /q "%STAGE%"

echo.
echo Created: XG-Resume-Studio-share.zip  (in this folder)
echo Contents = source only. data\. and .venv\ are NOT included,
echo so nothing personal leaves your machine.
pause
