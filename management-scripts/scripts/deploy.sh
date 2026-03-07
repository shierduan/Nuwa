#!/bin/bash

# 女娲 (Nuwa) 部署脚本 for Linux/macOS
# 使用方法: ./deploy.sh [选项]
# 选项:
#   --daemon    后台运行
#   --port <端口>  设置服务端口
#   --host <主机>  设置服务主机

set -e

# 颜色定义
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
BLUE='\033[94m'
RESET='\033[0m'

# 脚本所在目录
SCRIPT_DIR="$(dirname "$0")"
NUWA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STOP_SCRIPT="$SCRIPT_DIR/stop.sh"
START_SCRIPT="$SCRIPT_DIR/start.sh"

# 解析命令行参数
DAEMON=false
PORT=""
HOST=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --daemon)
            DAEMON=true
            shift
            ;;
        --port)
            PORT="$2"
            shift
            shift
            ;;
        --host)
            HOST="$2"
            shift
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# 打印标题
echo -e "${BLUE}女娲服务部署${RESET}"
echo "------------------------"

# 停止当前服务
echo -e "${BLUE}停止当前服务...${RESET}"
"$STOP_SCRIPT"

# 拉取最新代码
echo -e "${BLUE}拉取最新代码...${RESET}"
cd "$NUWA_ROOT"
git pull
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 拉取代码失败${RESET}"
    exit 1
fi

# 更新依赖
echo -e "${BLUE}更新依赖...${RESET}"
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 更新依赖失败${RESET}"
    exit 1
fi

# 构建启动命令
START_ARGS=""
if [ "$DAEMON" = true ]; then
    START_ARGS="$START_ARGS --daemon"
fi
if [ -n "$PORT" ]; then
    START_ARGS="$START_ARGS --port $PORT"
fi
if [ -n "$HOST" ]; then
    START_ARGS="$START_ARGS --host $HOST"
fi

# 启动服务
echo -e "${BLUE}启动服务...${RESET}"
"$START_SCRIPT" $START_ARGS
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 启动服务失败${RESET}"
    exit 1
fi

# 等待服务启动
echo -e "${BLUE}等待服务启动...${RESET}"
sleep 5

# 检查服务状态
echo -e "${BLUE}检查服务状态...${RESET}"
"$SCRIPT_DIR/status.sh"

echo -e "${BLUE}------------------------${RESET}"
echo -e "${GREEN}部署完成${RESET}"