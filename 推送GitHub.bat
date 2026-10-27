@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   B站工具箱 - 推送待提交到 GitHub
echo ========================================
echo.
echo 待推送提交：
git log --oneline origin/master..HEAD
echo.
echo 开始推送（最多重试5次）...
echo.
set /a n=0
:retry
set /a n+=1
echo [第 %n% 次尝试]
git push origin master
if %errorlevel%==0 goto success
if %n% GEQ 5 goto failed
echo   失败，等待15秒后重试...
timeout /t 15 /nobreak >nul
goto retry

:success
echo.
echo ✓ 推送成功！
echo.
git log --oneline -1
git rev-list --count origin/master..HEAD
pause
exit /b 0

:failed
echo.
echo ✗ 推送失败（已重试5次）
echo.
echo 可能原因：
echo   1. GitHub 网络被阻断（TCP 443 连接失败）
echo   2. 需要配置代理
echo.
echo 提交已安全保存在本地，稍后可再运行本脚本。
echo 如需代理，先执行：
echo   git config --global http.proxy http://127.0.0.1:7890
echo   git config --global https.proxy http://127.0.0.1:7890
echo.
pause
exit /b 1