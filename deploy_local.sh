#!/usr/bin/env bash
# Nuwa 本地开发部署脚本（含飞书集成）
# 用法：./deploy_local.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Nuwa 本地部署启动..."
echo "📁 项目目录: $PROJECT_DIR"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未检测到 Docker，请先安装 Docker Desktop"
    echo "   下载地址: https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ 未检测到 docker compose 插件"
    exit 1
fi

echo "✅ Docker 环境就绪"

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo "⚠️  未找到 config/config.yaml"
    if [ -f "config/config.local.yaml" ]; then
        echo "📋 发现配置模板 config/config.local.yaml"
        echo "   请复制并填入你的飞书凭据："
        echo "   cp config/config.local.yaml config/config.yaml"
        echo "   然后编辑 config/config.yaml 填入真实的 App ID 和 App Secret"
        read -p "   是否现在复制模板？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp config/config.local.yaml config/config.yaml
            echo "✅ 已复制，请编辑 config/config.yaml 填入飞书凭据"
            echo "   然后重新运行此脚本"
        fi
    fi
    exit 1
fi

# 检查是否还在使用占位符
if grep -q "YOUR_FEISHU_APP_ID" config/config.yaml; then
    echo "⚠️  config/config.yaml 仍包含占位符，请先填入真实的飞书凭据"
    echo "   编辑 config/config.yaml 替换 YOUR_FEISHU_APP_ID 和 YOUR_FEISHU_APP_SECRET"
    exit 1
fi

echo "✅ 配置文件就绪"

# 确保数据目录存在
mkdir -p data logs

# 构建并启动
echo "🔨 构建 Docker 镜像..."
docker compose build --no-cache nuwa-core

echo "🚀 启动服务..."
docker compose up -d

# 等待服务启动
echo "⏳ 等待服务启动 (10s)..."
sleep 10

# 健康检查
echo "🏥 执行健康检查..."
if docker compose exec nuwa-core python health_check.py; then
    echo ""
    echo "✅ 部署成功！服务运行正常"
    echo ""
    echo "📋 服务访问地址："
    echo "   WebSocket:     ws://localhost:8766"
    echo "   指标(JSON):    http://localhost:8080/metrics"
    echo "   指标(Prometheus): http://localhost:8081/metrics"
    echo "   Grafana:       http://localhost:3000 (admin/admin123)"
    echo "   Prometheus:    http://localhost:9090"
    echo ""
    echo "📋 飞书集成测试："
    echo "   1. 在飞书开放平台配置事件订阅："
    echo "      - 接收消息、@机器人、加入群聊等事件"
    echo "      - 推送地址: http://<你的公网IP>:8766 (需公网可访问)"
    echo "   2. 本地测试可用 ngrok: ngrok http 8766"
    echo "   3. 在飞书群中 @女娲 测试对话"
    echo ""
    echo "📋 常用命令："
    echo "   查看日志:    docker compose logs -f nuwa-core"
    echo "   停止服务:    docker compose down"
    echo "   重启服务:    docker compose restart"
    echo "   进入容器:    docker compose exec nuwa-core bash"
else
    echo "❌ 健康检查失败，查看日志排查："
    docker compose logs nuwa-core --tail 50
    exit 1
fi