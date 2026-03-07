@echo off
chcp 65001 >nul
title 女娲开发模式脚本

:: 全局变量
set "SCRIPT_DIR=%~dp0"
set "NUWA_ROOT=%SCRIPT_DIR%..\.."
set "LOG_DIR=%NUWA_ROOT%\logs"
set "MAIN_SCRIPT=%NUWA_ROOT%\main_async.py"
set "PORT="
set "HOST="

:: 确保日志目录存在
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 日志函数
:log
set "level=%1"
set "message=%2"
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "date=%%c-%%a-%%b"
for /f "tokens=1-3 delims=:,. " %%a in ('time /t') do set "time=%%a:%%b:%%c"
set "timestamp=%date% %time%"

echo [%timestamp%] [%level%] %message%

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

:: 检查依赖
:check_dependencies
call :log INFO "检查依赖..."

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log ERROR "Python 未找到"
    exit /b 1
)

:: 检查main_async.py
if not exist "%MAIN_SCRIPT%" (
    call :log ERROR "main_async.py 未找到"
    exit /b 1
)

:: 检查requirements.txt
if exist "%NUWA_ROOT%\requirements.txt" (
    call :log INFO "检查Python依赖..."
    python -m pip install -r "%NUWA_ROOT%\requirements.txt" >nul 2>&1
    if %errorlevel% neq 0 (
        call :log WARNING "依赖安装失败，可能会影响运行"
    ) else (
        call :log SUCCESS "依赖安装成功"
    )
)

exit /b 0

:: 启动开发模式
:start_dev
call :log INFO "启动女娲开发模式"

call :check_dependencies
if %errorlevel% neq 0 (
    exit /b 1
)

:: 构建命令
set "cmd=python "%MAIN_SCRIPT%" --dev --verbose"

:: 添加端口和主机参数
if not "%PORT%"=="" (
    set "cmd=%cmd% --port %PORT%"
)

if not "%HOST%"=="" (
    set "cmd=%cmd% --host %HOST%"
)

call :log INFO "运行命令: %cmd%"
call :log INFO "开发模式已启动，按 Ctrl+C 停止"

:: 运行服务
%cmd%
exit /b 0

:: 主函数
:main
:: 解析参数
:parse_args
if "%1"=="-p" (
    set "PORT=%2"
    shift
    shift
    goto parse_args
) else if "%1"=="-h" (
    set "HOST=%2"
    shift
    shift
    goto parse_args
) else if not "%1"=="" (
    echo 使用方法: %0 [-p 端口] [-h 主机]
    exit /b 1
)

call :start_dev
exit /b 0

:: 执行主函数
call :main %*

pause