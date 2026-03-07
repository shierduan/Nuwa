@echo off
chcp 65001 >nul

:: 女娲 (Nuwa) 启动脚本 for Windows
:: 使用方法: start.bat [选项]
:: 选项:
::   --daemon    后台运行
::   --port <端口>  设置服务端口
::   --host <主机>  设置服务主机

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
set "MAIN_SCRIPT=%NUWA_ROOT%\main_async.py"
set "LOG_DIR=%NUWA_ROOT%\logs"

:: 确保日志目录存在
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 解析命令行参数
set "DAEMON=false"
set "PORT="
set "HOST="

:parse_args
if "%~1" == "--daemon" (
    set "DAEMON=true"
    shift
    goto parse_args
)
if "%~1" == "--port" (
    set "PORT=%~2"
    shift
    shift
    goto parse_args
)
if "%~1" == "--host" (
    set "HOST=%~2"
    shift
    shift
    goto parse_args
)

:: 检查Python是否可用
echo %BLUE%检查Python环境...%RESET%
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%错误: 未找到Python，请先安装Python 3.11+%RESET%
    pause
    exit /b 1
)

:: 设置国内模型源
set "HF_ENDPOINT=https://hf-mirror.com"

:: 构建启动命令
set "CMD=python "%MAIN_SCRIPT%""

if "%DAEMON%" == "true" (
    :: 生成日志文件名
    for /f "tokens=2 delims==." %%a in ('wmic os get localdatetime /value') do set "DATETIME=%%a"
    set "LOG_FILE=%LOG_DIR%\nuwa_%DATETIME:~0,8%_%DATETIME:~8,6%.log"
    set "CMD=%CMD% --daemon --log "%LOG_FILE%""
)

if not "%PORT%" == "" (
    set "CMD=%CMD% --port %PORT%"
)

if not "%HOST%" == "" (
    set "CMD=%CMD% --host %HOST%"
)

:: 启动服务
echo %BLUE%启动女娲服务...%RESET%
echo 命令: %CMD%

if "%DAEMON%" == "true" (
    start "Nuwa Service" /min cmd /c "%CMD%"
    echo %GREEN%女娲服务已在后台启动%RESET%
    echo %GREEN%日志文件: %LOG_FILE%%RESET%
) else (
    %CMD%
)

endlocal