@echo off
setlocal enabledelayedexpansion
title 滴鱼简历助手 - 局域网直传
cd /d "%~dp0"

set "FIRST_RUN=0"
if not exist ".venv\Scripts\python.exe" set "FIRST_RUN=1"

REM ---------- 1. locate Python 3.10+ ----------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

REM ---------- 2. first run: create venv and install deps ----------
if "%FIRST_RUN%"=="1" (
    echo [1/2] 首次运行：正在创建虚拟环境......
    %PY% -m venv .venv
    if errorlevel 1 goto :venvfail
    echo [2/2] 正在安装依赖，可能需要几分钟 —— 请勿关闭窗口......
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 call :install_mirror || goto :pipfail
    echo.
    echo 环境配置完成！
)

".venv\Scripts\python.exe" -c "import uvicorn, fastapi" >nul 2>nul
if errorlevel 1 goto :broken

REM ---------- 3. pick a free port ----------
set PORT=8000
:portloop
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>nul
if not errorlevel 1 (
    set /a PORT+=1
    if !PORT! leq 8010 goto :portloop
    goto :portfail
)

set RESUME_LAN=1
echo 正在以局域网模式启动：http://127.0.0.1:!PORT!
echo 手机需连接同一 Wi-Fi，扫首页二维码并输入配对码（见下方窗口输出）。
echo 首次运行如弹出防火墙提示，请点击「允许访问」。
start "" /b cmd /c "ping -n 8 127.0.0.1 >nul & start http://127.0.0.1:!PORT!"
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port !PORT!
echo.
echo 服务已退出。如有报错，请把上方文字拍照发给开发者（邮箱见《运行环境配置说明.txt》）。
pause
exit /b

:install_mirror
echo 默认源安装失败，自动改用清华镜像重试......
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
exit /b %errorlevel%

:nopython
echo [错误] 未检测到 Python 3.10 ~ 3.14。
echo 请先到 https://www.python.org/downloads/ 安装 Python，
echo 安装时务必勾选「Add Python to PATH」，然后重新双击本脚本。
echo 详细说明见同目录《运行环境配置说明.txt》。
pause
exit /b 1

:venvfail
echo [错误] 创建虚拟环境失败。请确认 Python 安装完整、磁盘可写后重试。
pause
exit /b 1

:pipfail
echo.
echo [错误] 依赖安装失败，多为网络问题。处理办法：
echo   ① 关闭代理/加速器后重新双击本脚本，已完成步骤会自动跳过；
echo   ② 或在本目录打开 cmd 手动执行：
echo      .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo 更多帮助见《运行环境配置说明.txt》。
pause
exit /b 1

:broken
echo [错误] 环境不完整。请在本目录打开 cmd 执行：
echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1

:portfail
echo [错误] 8000 ~ 8010 端口均被占用，请关闭占用端口的程序后重试。
pause
exit /b 1
