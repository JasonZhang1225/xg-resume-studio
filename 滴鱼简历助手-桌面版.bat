@echo off
setlocal
title 滴鱼简历助手 - 桌面窗口版
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 首次使用桌面版：正在自动配置环境，可能需要几分钟，请勿关闭窗口......
    call :setup_env || goto :nopython
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" /b ".venv\Scripts\pythonw.exe" desktop.py
    exit /b
)
echo [错误] 环境不完整，pythonw.exe 缺失。
echo 请删除本目录下的 .venv 文件夹后重新运行本脚本。
pause
exit /b 1

:setup_env
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY exit /b 1
%PY% -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo 默认源安装失败，自动改用清华镜像重试......
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)
exit /b

:nopython
echo [错误] 未检测到 Python 3.10 或更高版本，环境配置失败。
echo 请先双击「滴鱼简历助手.bat」按提示安装 Python 后重试。
echo 详细说明见docs 文件夹内docs 文件夹内《运行环境配置说明.txt》。
pause
exit /b 1
