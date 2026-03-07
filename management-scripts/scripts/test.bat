@echo off
chcp 65001 >nul
title 女娲测试脚本

:: 全局变量
set "SCRIPT_DIR=%~dp0"
set "NUWA_ROOT=%SCRIPT_DIR%..\.."
set "TEST_DIR=%NUWA_ROOT%\tests"
set "LOG_DIR=%NUWA_ROOT%\logs"
set "TEST_REPORT=%LOG_DIR%\test_report.log"

:: 确保日志目录存在
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: 日志函数
:log
set "level=%1"
set "message=%2"
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "date=%%c-%%a-%%b"
for /f "tokens=1-3 delims=:,. " %%a in ('time /t') do set "time=%%a:%%b:%%c"
set "timestamp=%date% %time%"

echo [%timestamp%] [%level%] %message% >> "%TEST_REPORT%"

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
call :log INFO "检查测试依赖..."

:: 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log ERROR "Python 未找到"
    exit /b 1
)

:: 检查pytest
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log INFO "安装pytest..."
    python -m pip install pytest >nul 2>&1
    if %errorlevel% neq 0 (
        call :log ERROR "pytest 安装失败"
        exit /b 1
    )
)

:: 检查测试目录
if not exist "%TEST_DIR%" (
    call :log ERROR "测试目录不存在: %TEST_DIR%"
    exit /b 1
)

exit /b 0

:: 运行测试
:run_tests
call :log INFO "运行女娲测试"

call :check_dependencies
if %errorlevel% neq 0 (
    exit /b 1
)

call :log INFO "测试目录: %TEST_DIR%"
call :log INFO "测试报告: %TEST_REPORT%"

:: 运行测试
call :log INFO "开始运行测试..."

python -m pytest "%TEST_DIR%" -v --tb=short >> "%TEST_REPORT%"
set "test_result=%errorlevel%"

if %test_result% equ 0 (
    call :log SUCCESS "所有测试通过"
) else (
    call :log ERROR "测试失败"
)

call :log INFO "测试完成，结果已保存到: %TEST_REPORT%"

:: 显示测试报告
if exist "%TEST_REPORT%" (
    echo 测试报告内容:
    type "%TEST_REPORT%"
)

exit /b %test_result%

:: 运行特定测试
:run_specific_test
set "test_file=%1"
call :log INFO "运行特定测试: %test_file%"

call :check_dependencies
if %errorlevel% neq 0 (
    exit /b 1
)

if not exist "%test_file%" (
    call :log ERROR "测试文件不存在: %test_file%"
    exit /b 1
)

call :log INFO "开始运行测试..."

python -m pytest "%test_file%" -v --tb=short >> "%TEST_REPORT%"
set "test_result=%errorlevel%"

if %test_result% equ 0 (
    call :log SUCCESS "测试通过"
) else (
    call :log ERROR "测试失败"
)

:: 显示测试报告
if exist "%TEST_REPORT%" (
    echo 测试报告内容:
    type "%TEST_REPORT%"
)

exit /b %test_result%

:: 主函数
if "%1" neq "" (
    :: 运行特定测试
    call :run_specific_test "%1"
) else (
    :: 运行所有测试
    call :run_tests
)

pause