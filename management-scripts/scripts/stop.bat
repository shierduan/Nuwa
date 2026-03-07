@echo off
chcp 65001 >nul

:: 女娲 (Nuwa) 停止脚本 for Windows
:: 使用方法: stop.bat

setlocal

:: 定义颜色
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

:: 脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "NUWA_ROOT=%SCRIPT_DIR%\..\.."
set "PID_FILE=%NUWA_ROOT%\nuwa.pid"

:: 检查PID文件是否存在
if not exist "%PID_FILE%" (
    echo %YELLOW%警告: 未找到PID文件，女娲服务可能未运行%RESET%
    pause
    exit /b 0
)

:: 读取PID
set /p PID=<"%PID_FILE%"
if "%PID%" == "" (
    echo %YELLOW%警告: PID文件为空，女娲服务可能未运行%RESET%
    del "%PID_FILE%"
    pause
    exit /b 0
)

:: 检查进程是否存在
tasklist /FI "PID eq %PID%" | findstr "%PID%" >nul
if %errorlevel% neq 0 (
    echo %YELLOW%警告: 进程 %PID% 不存在，女娲服务可能已停止%RESET%
    del "%PID_FILE%"
    pause
    exit /b 0
)

:: 停止服务
echo %BLUE%停止女娲服务 (PID: %PID%)...%RESET%
taskkill /PID %PID% /F
if %errorlevel% eq 0 (
    echo %GREEN%女娲服务已成功停止%RESET%
    del "%PID_FILE%"
) else (
    echo %RED%停止服务失败%RESET%
)

pause
endlocal