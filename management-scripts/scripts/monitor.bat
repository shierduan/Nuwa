@echo off
chcp 65001 >nul
title 女娲监控脚本

:: 全局变量
set "SCRIPT_DIR=%~dp0"
set "NUWA_ROOT=%SCRIPT_DIR%..\.."
set "LOG_DIR=%NUWA_ROOT%\logs"
set "MONITOR_LOG=%LOG_DIR%\monitor.log"
set "PID_FILE=%NUWA_ROOT%\nuwa.pid"
set "HEALTH_URL=http://localhost:8000/health"
set "MONITOR_PID_FILE=%NUWA_ROOT%\monitor.pid"

:: 确保日志目录存在
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 日志函数
:log
set "level=%1"
set "message=%2"
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "date=%%c-%%a-%%b"
for /f "tokens=1-3 delims=:,. " %%a in ('time /t') do set "time=%%a:%%b:%%c"
set "timestamp=%date% %time%"

echo [%timestamp%] [%level%] %message% >> "%MONITOR_LOG%"

if "%level%"=="ERROR" (
    echo [ERROR] %message%
) else if "%level%"=="WARNING" (
    echo [WARNING] %message%
) else if "%level%"=="INFO" (
    echo [INFO] %message%
) else if "%level%"=="SUCCESS" (
    echo [SUCCESS] %message%
) else (
    echo [%level%] %message%
)
goto :eof

:: 检查服务状态
:check_service_status
if not exist "%PID_FILE%" (
    call :log ERROR "PID文件不存在，服务可能未运行"
    exit /b 1
)

set /p pid=<"%PID_FILE%"
tasklist /FI "PID eq %pid%" | findstr "%pid%" >nul
if %errorlevel% neq 0 (
    call :log ERROR "进程 %pid% 不存在，服务可能已崩溃"
    exit /b 1
)

exit /b 0

:: 检查服务健康状态
:check_health
powershell -Command "try { $response = Invoke-WebRequest -Uri '%HEALTH_URL%' -TimeoutSec 5; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %errorlevel% neq 0 (
    call :log ERROR "服务健康检查失败"
    exit /b 1
)

call :log SUCCESS "服务健康状态正常"
exit /b 0

:: 发送通知
:send_notification
set "message=%1"
call :log INFO "发送通知: %message%"

:: 示例：发送到系统通知
powershell -Command "[System.Windows.Forms.MessageBox]::Show('%message%', '女娲监控', 0)"
exit /b 0

:: 启动监控
:start_monitor
call :log INFO "启动女娲监控"

:: 检查是否已在运行
if exist "%MONITOR_PID_FILE%" (
    set /p monitor_pid=<"%MONITOR_PID_FILE%"
    tasklist /FI "PID eq %monitor_pid%" | findstr "%monitor_pid%" >nul
    if %errorlevel% equ 0 (
        call :log WARNING "监控已在运行，PID: %monitor_pid%"
        echo 监控已在运行，PID: %monitor_pid%
        exit /b 1
    )
)

:: 后台运行监控
start /b cmd /c "%SCRIPT_DIR%monitor.bat _run_monitor"
echo %errorlevel% > "%MONITOR_PID_FILE%"
call :log SUCCESS "监控已启动"
echo 监控已启动
exit /b 0

:: 监控运行函数
:_run_monitor
:monitor_loop
call :log INFO "开始监控检查"

call :check_service_status
if %errorlevel% equ 0 (
    call :check_health
    if %errorlevel% neq 0 (
        call :send_notification "女娲服务健康检查失败"
    )
) else (
    call :send_notification "女娲服务未运行或已崩溃"
)

:: 每60秒检查一次
timeout /t 60 /nobreak >nul
goto monitor_loop

:: 停止监控
:stop_monitor
if exist "%MONITOR_PID_FILE%" (
    set /p monitor_pid=<"%MONITOR_PID_FILE%"
    tasklist /FI "PID eq %monitor_pid%" | findstr "%monitor_pid%" >nul
    if %errorlevel% equ 0 (
        taskkill /PID %monitor_pid% /F >nul
        del "%MONITOR_PID_FILE%"
        call :log SUCCESS "监控已停止"
        echo 监控已停止
    ) else (
        del "%MONITOR_PID_FILE%"
        call :log WARNING "监控进程不存在，已清理PID文件"
        echo 监控进程不存在，已清理PID文件
    )
) else (
    call :log WARNING "监控未运行"
    echo 监控未运行
)
exit /b 0

:: 查看监控状态
:status_monitor
if exist "%MONITOR_PID_FILE%" (
    set /p monitor_pid=<"%MONITOR_PID_FILE%"
    tasklist /FI "PID eq %monitor_pid%" | findstr "%monitor_pid%" >nul
    if %errorlevel% equ 0 (
        call :log SUCCESS "监控正在运行，PID: %monitor_pid%"
        echo 监控正在运行，PID: %monitor_pid%
    ) else (
        call :log WARNING "监控PID文件存在但进程不存在"
        echo 监控PID文件存在但进程不存在
    )
) else (
    call :log INFO "监控未运行"
    echo 监控未运行
)
exit /b 0

:: 主函数
if "%1"=="start" (
    call :start_monitor
) else if "%1"=="stop" (
    call :stop_monitor
) else if "%1"=="status" (
    call :status_monitor
) else if "%1"=="check" (
    call :log INFO "手动检查服务状态"
    call :check_service_status
    call :check_health
) else if "%1"=="_run_monitor" (
    call :_run_monitor
) else (
    echo 使用方法: %0 {start^|stop^|status^|check}
    echo   start   - 启动监控
    echo   stop    - 停止监控
    echo   status  - 查看监控状态
    echo   check   - 手动检查服务状态
)

pause