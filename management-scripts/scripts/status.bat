@echo off
chcp 65001 >nul

:: 女娲 (Nuwa) 状态检查脚本 for Windows
:: 使用方法: status.bat

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
    echo %YELLOW%状态: 已停止%RESET%
    pause
    exit /b 0
)

:: 读取PID
set /p PID=<"%PID_FILE%"
if "%PID%" == "" (
    echo %YELLOW%状态: 已停止%RESET%
    del "%PID_FILE%"
    pause
    exit /b 0
)

:: 检查进程是否存在
tasklist /FI "PID eq %PID%" | findstr "%PID%" >nul
if %errorlevel% neq 0 (
    echo %YELLOW%状态: 已停止%RESET%
    del "%PID_FILE%"
    pause
    exit /b 0
)

:: 进程正在运行
echo %GREEN%状态: 运行中%RESET%
echo PID: %PID%

:: 检查服务是否可访问
echo %BLUE%检查服务可访问性...%RESET%
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 3; if ($response.StatusCode -eq 200) { Write-Host '服务可访问' -ForegroundColor Green } else { Write-Host '服务返回状态码: ' $response.StatusCode -ForegroundColor Yellow } } catch { Write-Host '服务暂时无法访问' -ForegroundColor Yellow }"

pause
endlocal