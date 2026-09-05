@echo off
chcp 65001 >nul
title B站弹幕工具 - 一键打包

echo ========================================
echo   B站弹幕工具 - 一键打包脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo.
    echo [错误] 未检测到Python，请先安装Python并勾选Add to PATH
    pause
    exit /b 1
)
echo Python环境正常
echo.

echo [2/3] 安装依赖（requests + pyinstaller）...
pip install requests pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo [警告] 依赖安装可能失败，尝试继续...
)
echo 依赖安装完成
echo.

echo [3/3] 开始打包（这一步需要1-2分钟，请耐心等待）...
echo.
pyinstaller --onefile --windowed --name "B站弹幕工具" --clean main_gui_pro.py
if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 生成的exe文件位置: dist\B站弹幕工具.exe
echo.
echo 你可以把 dist\B站弹幕工具.exe 复制到任何地方运行
echo 运行时会在同目录生成 accounts.json（账户数据）和 danmaku_list.txt（弹幕列表）
echo.
pause
