#!/bin/bash

# Nuwa 项目初始化脚本

set -e

echo "=== Nuwa 项目初始化 ==="

# 检查是否为 root 用户
if [ "$(id -u)" -eq 0 ]; then
    echo "请使用普通用户运行此脚本，sudo 权限将在需要时自动申请"
    exit 1
fi

# 检查操作系统
if [ ! -f /etc/debian_version ]; then
    echo "此脚本仅支持 Debian 系统"
    exit 1
fi

# 更新系统
echo "1. 更新系统..."
sudo apt update && sudo apt upgrade -y

# 安装依赖
echo "2. 安装依赖..."
sudo apt install -y git wget curl python3-pip python3-venv build-essential

# 创建用户和目录
echo "3. 配置用户和目录..."
if ! getent passwd nuwa > /dev/null; then
    sudo useradd -r -s /usr/sbin/nologin nuwa
fi

sudo mkdir -p /opt/nuwa
sudo chown -R $USER:$USER /opt/nuwa

cd /opt/nuwa

# 克隆项目
echo "4. 克隆项目..."
if [ -d .git ]; then
    echo "项目已存在，更新代码..."
    git pull
else
    git clone https://github.com/shierduan/Nuwa.git .
fi

# 创建虚拟环境
echo "5. 创建虚拟环境..."
if [ ! -d venv ]; then
    python3 -m venv venv
fi

# 激活虚拟环境并安装依赖
echo "6. 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 配置系统
echo "7. 配置系统..."
mkdir -p data logs monitoring/grafana/dashboards monitoring/grafana/datasources

if [ ! -f config/config.yaml ]; then
    cp config/config_example.yaml config/config.yaml
    echo "已创建默认配置文件 config/config.yaml"
fi

# 设置权限
echo "8. 设置权限..."
sudo chown -R nuwa:nuwa /opt/nuwa

# 创建 Systemd 服务
echo "9. 创建系统服务..."
cat <<EOF | sudo tee /etc/systemd/system/nuwa.service > /dev/null
[Unit]
Description=Nuwa Core Service
After=network.target

[Service]
Type=simple
User=nuwa
Group=nuwa
WorkingDirectory=/opt/nuwa
Environment=PATH=/opt/nuwa/venv/bin
ExecStart=/opt/nuwa/venv/bin/python3 /opt/nuwa/main_async.py

Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

LimitNOFILE=4096
LimitNPROC=2048

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
echo "10. 启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable nuwa
sudo systemctl start nuwa

# 检查服务状态
echo "11. 检查服务状态..."
sudo systemctl status nuwa

echo -e "\n=== 初始化完成 ==="
echo "Nuwa 服务已成功启动"
echo -e "\n服务信息："
echo "  - 服务名称: nuwa"
echo "  - 状态检查: sudo systemctl status nuwa"
echo "  - 查看日志: journalctl -u nuwa -f"
echo "  - 重启服务: sudo systemctl restart nuwa"
echo "  - 停止服务: sudo systemctl stop nuwa"
