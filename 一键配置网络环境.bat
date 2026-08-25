@echo off
setlocal enabledelayedexpansion
title 滴鱼简历助手 - 一键配置网络环境
cd /d "%~dp0"

echo ==================================================
echo   滴鱼简历助手 —— 一键配置网络环境
echo   本脚本只负责联网下载并安装全部运行依赖，
echo   完成后日常启动请双击「滴鱼简历助手.bat」。
echo ==================================================
echo.

REM ---------- 1. locate Python 3.10+ ----------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython

REM ---------- 2. create venv ----------
if exist ".venv\Scripts\python.exe" (
    echo [1/3] 已存在运行环境，直接进入依赖检查。
    goto :netcheck
)
echo [1/3] 正在创建虚拟环境......
%PY% -m venv .venv
if errorlevel 1 goto :venvfail

:netcheck
echo [2/3] 正在检测官方 PyPI 连通性......
set "PIPARGS="
curl -s -m 8 -o nul https://pypi.org/simple/ >nul 2>nul
if errorlevel 1 (
    echo       官方源不可达，将自动改用清华镜像。
    set "PIPARGS=-i https://pypi.tuna.tsinghua.edu.cn/simple"
) else (
    echo       官方源连接正常。
)

REM ---------- 3. install deps ----------
echo [3/3] 正在安装依赖，可能需要几分钟 —— 请勿关闭窗口......
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt %PIPARGS%
if errorlevel 1 (
    echo       首选源安装失败，换备用源重试......
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 goto :pipfail
)

REM ---------- verify ----------
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, jinja2, docx, pdfplumber, qrcode, PIL, rapidocr_onnxruntime" >nul 2>nul
if errorlevel 1 goto :broken
echo.
echo ==================================================
echo   全部运行资源已就绪！
echo   日常使用请双击「滴鱼简历助手.bat」启动。
echo ==================================================
pause
exit /b

:nopython
echo [错误] 未检测到 Python 3.10 ~ 3.14。
echo 请先到 https://www.python.org/downloads/ 安装 Python，
echo 安装时务必勾选「Add Python to PATH」，然后重新运行本脚本。
pause
exit /b 1

:venvfail
echo [错误] 创建虚拟环境失败。请确认 Python 安装完整、磁盘可写后重试。
pause
exit /b 1

:pipfail
echo.
echo [错误] 依赖安装失败。处理办法：
echo   ① 关闭代理/加速器后重新运行本脚本；
echo   ② 手动执行：
echo      .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pause
exit /b 1

:broken
echo [错误] 依赖已安装但自检未通过，请删除 .venv 文件夹后重新运行本脚本。
pause
exit /b 1
