@echo off
chcp 65001 >nul
title B站工具箱 - 一键打包
rem v6.7.16: 已移动到 scripts/ 子目录，改用 PyInstaller spec 文件打包
rem            （原脚本引用已删除的 main_gui_pro.py，已废弃）
cd /d "%~dp0.."
echo ========================================
echo   B站工具箱 - 一键打包
echo ========================================
echo.
echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo.
    echo [错误] 未检测到Python，请先安装并勾选Add to PATH
    pause
    exit /b 1
)
echo Python环境正常
echo.
echo [2/3] 检查依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo [3/3] 开始打包（需要1-2分钟）...
echo.
rem 自动找最新的 spec 文件
set SPEC=
for /f "delims=" %%f in ('dir /b /o-d "B站工具箱_v*.spec" 2^>nul') do (
    if not defined SPEC set SPEC=%%f
)
if not defined SPEC (
    echo [错误] 未找到 spec 文件
    pause
    exit /b 1
)
echo 使用 spec: %SPEC%
python -m PyInstaller %SPEC% --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)
echo.
echo ========================================
echo   打包完成！产物在 dist\ 目录
echo ========================================
pause