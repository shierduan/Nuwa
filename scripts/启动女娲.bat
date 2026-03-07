@echo off
chcp 65001 >nul
title 女娲数字生命

echo ========================================
echo    女娲数字生命 - 统一启动器
echo ========================================
echo.

:: 检查环境
where python >nul 2>nul || (
    echo [错误] 未找到Python
    pause
    exit /b 1
)

where node >nul 2>nul || (
    echo [错误] 未找到Node.js
    pause
    exit /b 1
)

:: 检查文件
if not exist "server_async.py" (
    echo [错误] 缺少 server_async.py
    pause
    exit /b 1
)

:: 安装Electron如果需要
if not exist "node_modules\electron" (
    echo [安装] Electron...
    call npm install electron --save-dev >nul 2>&1
)

:: 启动系统
echo [启动] 女娲系统...
python nuwa_main.py

pause
