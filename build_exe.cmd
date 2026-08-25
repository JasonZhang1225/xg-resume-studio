@echo off
setlocal
title Build XG Resume Studio EXE
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run the dev setup first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [1/2] Installing PyInstaller ...
  ".venv\Scripts\python.exe" -m pip install pyinstaller || goto :fail
)

echo [2/2] Building EXE (this may take 5~15 minutes) ...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --name ?????? launcher.py ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "resume_templates;resume_templates" ^
  --collect-all rapidocr_onnxruntime ^
  --collect-all onnxruntime ^
  --collect-all pypdfium2 ^
  --exclude-module pywebview ^
  --exclude-module pytest ^
  --exclude-module ruff ^
  || goto :fail

echo.
echo Done. Output folder: dist\??????\
echo Test it, then zip that folder for distribution.
pause
exit /b

:fail
echo.
echo [ERROR] Build failed. Read the log above.
pause
exit /b 1
