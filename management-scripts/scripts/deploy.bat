@echo off
chcp 65001 >nul

:: 女娲 (Nuwa) 部署脚本 for Windows
:: 使用方法: deploy.bat [选项]
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
set "STOP_SCRIPT=%SCRIPT_DIR%\stop.bat"
set "START_SCRIPT=%SCRIPT_DIR%\start.bat"

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

:: 打印标题
echo %BLUE%女娲服务部署%RESET%
echo ------------------------

:: 停止当前服务
echo %BLUE%停止当前服务...%RESET%
call "%STOP_SCRIPT%"

:: 拉取最新代码
echo %BLUE%拉取最新代码...%RESET%
cd "%NUWA_ROOT%"
git pull
if %errorlevel% neq 0 (
    echo %RED%错误: 拉取代码失败%RESET%
    pause
    exit /b 1
)

:: 更新依赖
echo %BLUE%更新依赖...%RESET%
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo %RED%错误: 更新依赖失败%RESET%
    pause
    exit /b 1
)

:: 构建启动命令
set "START_ARGS="
if "%DAEMON%" == "true" (
    set "START_ARGS=%START_ARGS% --daemon"
)
if not "%PORT%" == "" (
    set "START_ARGS=%START_ARGS% --port %PORT%"
)
if not "%HOST%" == "" (
    set "START_ARGS=%START_ARGS% --host %HOST%"
)

:: 启动服务
echo %BLUE%启动服务...%RESET%
call "%START_SCRIPT%" %START_ARGS%
if %errorlevel% neq 0 (
    echo %RED%错误: 启动服务失败%RESET%
    pause
    exit /b 1
)

:: 等待服务启动
echo %BLUE%等待服务启动...%RESET%
timeout /t 5 >nul

:: 检查服务状态
echo %BLUE%检查服务状态...%RESET%
call "%SCRIPT_DIR%\status.bat"

echo %BLUE%------------------------%RESET%
echo %GREEN%部署完成%RESET%

pause
endlocal