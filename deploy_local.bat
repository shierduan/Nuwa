@echo off
REM Nuwa 本地开发部署脚本 (Windows版)
REM 用法：双击运行 deploy_local.bat

chcp 65001 >nul
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

echo 🚀 Nuwa 本地部署启动...
echo 📁 项目目录: %PROJECT_DIR%

REM 检查 Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Docker，请先安装 Docker Desktop
    echo    下载地址: https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 docker compose 插件
    pause
    exit /b 1
)

echo ✅ Docker 环境就绪

REM 检查配置文件
if not exist "config\config.yaml" (
    echo ⚠️  未找到 config\config.yaml
    if exist "config\config.local.yaml" (
        echo 📋 发现配置模板 config\config.local.yaml
        echo    请复制并填入你的飞书凭据和 Kilo AI API Key：
        echo    copy config\config.local.yaml config\config.yaml
        echo    然后编辑 config\config.yaml 填入真实的 App ID、App Secret 和 Kilo API Key
        set /p choice=是否现在复制模板？(y/n): 
        if /i "%choice%"=="y" (
            copy config\config.local.yaml config\config.yaml
            echo ✅ 已复制，请编辑 config\config.yaml 填入凭据
            echo    然后重新运行此脚本
        )
    )
    pause
    exit /b 1
)

REM 检查是否还在使用占位符
findstr "YOUR_" config\config.yaml >nul
if %errorlevel% equ 0 (
    echo ⚠️  config\config.yaml 仍包含占位符，请先填入真实的凭据
    echo    编辑 config\config.yaml 替换 YOUR_FEISHU_APP_ID、YOUR_FEISHU_APP_SECRET、YOUR_KILO_API_KEY
    pause
    exit /b 1
)

echo ✅ 配置文件就绪

REM 确保数据目录存在
if not exist data mkdir data
if not exist logs mkdir logs

REM 构建并启动
echo 🔨 构建 Docker 镜像...
docker compose build --no-cache nuwa-core

echo 🚀 启动服务...
docker compose up -d

REM 等待服务启动
echo ⏳ 等待服务启动 (10s)...
timeout /t 10 /nobreak >nul

REM 健康检查
echo 🏥 执行健康检查...
docker compose exec nuwa-core python health_check.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 部署成功！服务运行正常
    echo.
    echo 📋 服务访问地址：
    echo    WebSocket:     ws://localhost:8766
    echo    指标(JSON):    http://localhost:8080/metrics
    echo    指标(Prometheus): http://localhost:8081/metrics
    echo    Grafana:       http://localhost:3000 (admin/admin123)
    echo    Prometheus:    http://localhost:9090
    echo.
    echo 📋 飞书集成测试：
    echo    1. 在飞书开放平台配置事件订阅：
    echo       - 接收消息、@机器人、加入群聊等事件
    echo       - 推送地址: http://<你的公网IP>:8766 (需公网可访问)
    echo    2. 本地测试可用 ngrok: ngrok http 8766
    echo    3. 在飞书群中 @女娲 测试对话
    echo.
    echo 📋 常用命令：
    echo    查看日志:    docker compose logs -f nuwa-core
    echo    停止服务:    docker compose down
    echo    重启服务:    docker compose restart
    echo    进入容器:    docker compose exec nuwa-core bash
) else (
    echo ❌ 健康检查失败，查看日志排查：
    docker compose logs nuwa-core --tail 50
)

pause