# 女娲 (Nuwa) 安装脚本 for Windows (PowerShell)
# 使用方法: iwr -useb https://nuwa.ai/install.ps1 | iex
# 或: & ([scriptblock]::Create((iwr -useb https://nuwa.ai/install.ps1)))

param(
    [string]$InstallMethod = "git",
    [string]$GitDir = "$env:USERPROFILE\nuwa",
    [switch]$NoOnboard,
    [switch]$NoGitUpdate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# 颜色定义
$ACCENT = "`e[38;2;255;77;77m"    # 珊瑚红
$SUCCESS = "`e[38;2;0;229;204m"    # 亮青色
$WARN = "`e[38;2;255;176;32m"     # 琥珀色
$ERROR = "`e[38;2;230;57;70m"     # 珊瑚中色
$MUTED = "`e[38;2;90;100;128m"    # -muted
$NC = "`e[0m"                     # 无颜色

function Write-Host {
    param([string]$Message, [string]$Level = "info")
    $msg = switch ($Level) {
        "success" { "$SUCCESS✓$NC $Message" }
        "warn" { "$WARN!$NC $Message" }
        "error" { "$ERROR✗$NC $Message" }
        default { "$MUTED·$NC $Message" }
    }
    Microsoft.PowerShell.Host\Write-Host $msg
}

function Write-Banner {
    Write-Host ""
    Write-Host "${ACCENT}  🧱 女娲安装程序$NC" -Level info
    Write-Host "${MUTED}  类人AI对话系统，包含黎曼几何语义场、自适应PID控制等高级功能$NC" -Level info
    Write-Host ""
}

function Get-ExecutionPolicyStatus {
    $policy = Get-ExecutionPolicy
    if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {
        return @{ Blocked = $true; Policy = $policy }
    }
    return @{ Blocked = $false; Policy = $policy }
}

function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-ExecutionPolicy {
    $status = Get-ExecutionPolicyStatus
    if ($status.Blocked) {
        Write-Host "PowerShell执行策略设置为: $($status.Policy)" -Level warn
        Write-Host "这会阻止脚本运行。" -Level warn
        Write-Host ""
        
        # 尝试为当前进程设置执行策略
        try {
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -ErrorAction Stop
            Write-Host "已为当前进程设置执行策略为RemoteSigned" -Level success
            return $true
        } catch {
            Write-Host "无法自动设置执行策略" -Level error
            Write-Host ""
            Write-Host "要修复此问题，请运行:" -Level info
            Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process" -Level info
            Write-Host ""
            Write-Host "或以管理员身份运行PowerShell并执行:" -Level info
            Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine" -Level info
            return $false
        }
    }
    return $true
}

function Get-PythonVersion {
    try {
        $version = python --version 2>&1
        if ($version) {
            return $version -replace '^Python ', ''
        }
    } catch { }
    return $null
}

function Install-Python {
    Write-Host "未找到Python" -Level info
    Write-Host "正在安装Python..." -Level info
    
    # 尝试使用winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  使用winget..." -Level info
        try {
            winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
            # 刷新PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  Python 3.11已安装" -Level success
            return $true
        } catch {
            Write-Host "  Winget安装失败: $_" -Level warn
        }
    }
    
    # 尝试使用chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "  使用chocolatey..." -Level info
        try {
            choco install python --version=3.11 -y 2>&1 | Out-Null
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  Python 3.11已安装" -Level success
            return $true
        } catch {
            Write-Host "  Chocolatey安装失败: $_" -Level warn
        }
    }
    
    Write-Host "无法自动安装Python" -Level error
    Write-Host "请手动从以下地址安装Python 3.11: https://www.python.org/downloads/" -Level info
    return $false
}

function Ensure-Python {
    $pythonVersion = Get-PythonVersion
    if ($pythonVersion) {
        $major = [int]($pythonVersion -split '\.')[0]
        $minor = [int]($pythonVersion -split '\.')[1]
        if ($major -eq 3 -and $minor -ge 11) {
            Write-Host "Python v$pythonVersion已找到" -Level success
            return $true
        }
        Write-Host "Python v$pythonVersion已找到，但需要v3.11+" -Level warn
    }
    return Install-Python
}

function Get-GitVersion {
    try {
        $version = git --version 2>$null
        if ($version) {
            return $version
        }
    } catch { }
    return $null
}

function Install-Git {
    Write-Host "未找到Git" -Level info
    
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  通过winget安装Git..." -Level info
        try {
            winget install Git.Git --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "  Git已安装" -Level success
            return $true
        } catch {
            Write-Host "  Winget安装失败" -Level warn
        }
    }
    
    Write-Host "请从以下地址安装Git for Windows: https://git-scm.com" -Level error
    return $false
}

function Ensure-Git {
    $gitVersion = Get-GitVersion
    if ($gitVersion) {
        Write-Host "$gitVersion已找到" -Level success
        return $true
    }
    return Install-Git
}

function Install-NuwaGit {
    param([string]$RepoDir, [switch]$Update)
    
    Write-Host "从git安装女娲..." -Level info
    
    if (!(Test-Path $RepoDir)) {
        Write-Host "  克隆仓库..." -Level info
        git clone https://github.com/nuwa-ai/nuwa-core.git $RepoDir 2>&1
    } elseif ($Update) {
        Write-Host "  更新仓库..." -Level info
        git -C $RepoDir pull --rebase 2>&1
    }
    
    # 安装依赖
    Write-Host "  安装依赖..." -Level info
    python -m pip install -r "$RepoDir\requirements.txt" 2>&1
    
    # 创建包装器
    $wrapperDir = "$env:USERPROFILE\.local\bin"
    if (!(Test-Path $wrapperDir)) {
        New-Item -ItemType Directory -Path $wrapperDir -Force | Out-Null
    }
    
    @"
@echo off
python "%~dp0..\nuwa\main_async.py" %*
"@ | Out-File -FilePath "$wrapperDir\nuwa.cmd" -Encoding ASCII -Force
    
    Write-Host "女娲已安装" -Level success
    return $true
}

function Add-ToPath {
    param([string]$Path)
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$Path*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$Path", "User")
        Write-Host "已将$Path添加到用户PATH" -Level info
    }
}

# 主函数
function Main {
    Write-Banner
    
    Write-Host "Windows已检测到" -Level success
    
    # 首先检查执行策略，在任何pip调用之前
    if (!(Ensure-ExecutionPolicy)) {
        Write-Host ""
        Write-Host "由于执行策略限制，安装无法继续" -Level error
        exit 1
    }
    
    if (!(Ensure-Python)) {
        exit 1
    }
    
    if ($InstallMethod -eq "git") {
        if (!(Ensure-Git)) {
            exit 1
        }
        
        if ($DryRun) {
            Write-Host "[DRY RUN] 将从git安装女娲到 $GitDir" -Level info
        } else {
            Install-NuwaGit -RepoDir $GitDir -Update:(-not $NoGitUpdate)
        }
    } else {
        # 本地安装方式
        Write-Host "使用本地安装方式..." -Level info
        if (!(Ensure-Git)) {
            Write-Host "Git是本地安装的推荐工具。请安装Git后重试。" -Level warn
        }
        
        # 检查当前目录是否为女娲项目
        if (Test-Path ".\requirements.txt") {
            Write-Host "  在当前目录安装依赖..." -Level info
            python -m pip install -r requirements.txt 2>&1
            Write-Host "女娲依赖已安装" -Level success
        } else {
            Write-Host "错误: 当前目录不是女娲项目目录，缺少requirements.txt文件" -Level error
            exit 1
        }
    }
    
    # 尝试添加Python Scripts到PATH
    try {
        $pythonScripts = python -c "import sys; print(sys.prefix + '\\Scripts')" 2>$null
        if ($pythonScripts) {
            Add-ToPath -Path $pythonScripts
        }
    } catch { }
    
    if (!$NoOnboard -and !$DryRun) {
        Write-Host ""
        Write-Host "运行 'python main_async.py' 启动女娲服务" -Level info
        Write-Host "访问 http://localhost:8000 查看服务状态" -Level info
    }
    
    Write-Host ""
    Write-Host "🧱 女娲安装成功!" -Level success
}

Main