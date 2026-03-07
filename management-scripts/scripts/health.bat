@echo off
chcp 65001 >nul

:: 女娲 (Nuwa) 健康检查脚本 for Windows
:: 使用方法: health.bat

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

:: 打印标题
echo %BLUE%女娲服务健康检查%RESET%
echo ------------------------

:: 检查服务状态
if not exist "%PID_FILE%" (
    echo %RED%错误: 服务未运行%RESET%
    pause
    exit /b 1
)

set /p PID=<"%PID_FILE%"
if "%PID%" == "" (
    echo %RED%错误: 服务未运行%RESET%
    del "%PID_FILE%"
    pause
    exit /b 1
)

:: 检查进程是否存在
tasklist /FI "PID eq %PID%" | findstr "%PID%" >nul
if %errorlevel% neq 0 (
    echo %RED%错误: 服务未运行%RESET%
    del "%PID_FILE%"
    pause
    exit /b 1
)

:: 服务运行状态
echo %GREEN%✓ 服务运行中 (PID: %PID%)%RESET%

:: 检查HTTP健康端点
echo %BLUE%检查服务健康端点...%RESET%
powershell -Command "try { 
    $response = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 5;
    if ($response.StatusCode -eq 200) {
        Write-Host '✓ 健康端点可访问' -ForegroundColor Green;
        $healthData = $response.Content | ConvertFrom-Json;
        Write-Host '详细信息:' -ForegroundColor Blue;
        $healthData | ForEach-Object { 
            foreach ($property in $_.PSObject.Properties) {
                Write-Host ('  ' + $property.Name + ': ' + $property.Value) -ForegroundColor Cyan;
            }
        }
    } else {
        Write-Host '✗ 健康端点返回状态码: ' $response.StatusCode -ForegroundColor Red;
    }
} catch {
    Write-Host '✗ 健康端点无法访问: ' $_.Exception.Message -ForegroundColor Red;
}"

:: 检查系统资源
echo %BLUE%检查系统资源...%RESET%
powershell -Command "
$process = Get-Process -Id $env:PID -ErrorAction SilentlyContinue;
if ($process) {
    Write-Host ('✓ 内存使用: ' + [math]::Round($process.WorkingSet64 / 1MB, 2) + ' MB') -ForegroundColor Green;
    Write-Host ('✓ CPU使用率: ' + [math]::Round($process.CPU, 1) + '%') -ForegroundColor Green;
} else {
    Write-Host '✗ 无法获取进程信息' -ForegroundColor Red;
}

$systemMemory = Get-WmiObject -Class Win32_OperatingSystem;
$totalMemory = [math]::Round($systemMemory.TotalVisibleMemorySize / 1MB, 2);
$freeMemory = [math]::Round($systemMemory.FreePhysicalMemory / 1MB, 2);
$usedMemory = $totalMemory - $freeMemory;
$memoryUsage = [math]::Round(($usedMemory / $totalMemory) * 100, 1);
Write-Host ('✓ 系统内存: ' + $usedMemory + ' MB / ' + $totalMemory + ' MB (' + $memoryUsage + '%)') -ForegroundColor Green;

$cpuUsage = (Get-WmiObject -Class win32_processor | Measure-Object -Property LoadPercentage -Average).Average;
Write-Host ('✓ 系统CPU使用率: ' + $cpuUsage + '%') -ForegroundColor Green;
"

:: 检查磁盘空间
echo %BLUE%检查磁盘空间...%RESET%
powershell -Command "
$drive = Get-WmiObject -Class Win32_LogicalDisk -Filter 'DeviceID="C:"';
if ($drive) {
    $totalSize = [math]::Round($drive.Size / 1GB, 2);
    $freeSpace = [math]::Round($drive.FreeSpace / 1GB, 2);
    $usedSpace = $totalSize - $freeSpace;
    $spaceUsage = [math]::Round(($usedSpace / $totalSize) * 100, 1);
    Write-Host ('✓ C盘空间: ' + $usedSpace + ' GB / ' + $totalSize + ' GB (' + $spaceUsage + '%)') -ForegroundColor Green;
} else {
    Write-Host '✗ 无法获取磁盘空间信息' -ForegroundColor Red;
}
"

:: 检查端口状态
echo %BLUE%检查端口状态...%RESET%
powershell -Command "
try {
    $tcpListeners = netstat -an | Select-String 'LISTENING' | Select-String '8000';
    if ($tcpListeners) {
        Write-Host '✓ 端口 8000 已监听' -ForegroundColor Green;
    } else {
        Write-Host '✗ 端口 8000 未监听' -ForegroundColor Red;
    }
} catch {
    Write-Host '✗ 无法检查端口状态' -ForegroundColor Red;
}"

echo %BLUE%------------------------%RESET%
echo %GREEN%健康检查完成%RESET%

pause
endlocal