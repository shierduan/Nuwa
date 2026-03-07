#!/bin/bash

# 女娲 (Nuwa) 启动脚本 for Linux/macOS
# 使用方法: ./start.sh [选项]
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
MAIN_SCRIPT="$NUWA_ROOT/main_async.py"
LOG_DIR="$NUWA_ROOT/logs"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

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

# 检查Python是否可用
echo -e "${BLUE}检查Python环境...${RESET}"
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 未找到Python，请先安装Python 3.11+${RESET}"
    exit 1
fi

# 构建启动命令
CMD="python3 \"$MAIN_SCRIPT\""

if [ "$DAEMON" = true ]; then
    # 生成日志文件名
    LOG_FILE="$LOG_DIR/nuwa_$(date +"%Y%m%d_%H%M%S").log"
    CMD="$CMD --daemon --log \"$LOG_FILE\""
fi

if [ -n "$PORT" ]; then
    CMD="$CMD --port $PORT"
fi

if [ -n "$HOST" ]; then
    CMD="$CMD --host $HOST"
fi

# 启动服务
echo -e "${BLUE}启动女娲服务...${RESET}"
echo "命令: $CMD"

if [ "$DAEMON" = true ]; then
    # 后台运行
    eval "$CMD" &
    PID=$!
    echo $PID > "$NUWA_ROOT/nuwa.pid"
    echo -e "${GREEN}女娲服务已在后台启动，PID: $PID${RESET}"
    echo -e "${GREEN}日志文件: $LOG_FILE${RESET}"
else
    # 前台运行
    eval "$CMD"
fi