#!/bin/bash

# 女娲 (Nuwa) 停止脚本 for Linux/macOS
# 使用方法: ./stop.sh

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
PID_FILE="$NUWA_ROOT/nuwa.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}警告: 未找到PID文件，女娲服务可能未运行${RESET}"
    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE" 2>/dev/null)
if [ -z "$PID" ]; then
    echo -e "${YELLOW}警告: PID文件为空，女娲服务可能未运行${RESET}"
    rm -f "$PID_FILE"
    exit 0
fi

# 检查进程是否存在
if ! kill -0 "$PID" 2>/dev/null; then
    echo -e "${YELLOW}警告: 进程 $PID 不存在，女娲服务可能已停止${RESET}"
    rm -f "$PID_FILE"
    exit 0
fi

# 停止服务
echo -e "${BLUE}停止女娲服务 (PID: $PID)...${RESET}"
kill -SIGTERM "$PID"

# 等待进程结束
for i in {1..10}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}女娲服务已成功停止${RESET}"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果进程仍在运行，强制终止
echo -e "${YELLOW}进程未正常退出，尝试强制终止${RESET}"
kill -SIGKILL "$PID"
sleep 1

if ! kill -0 "$PID" 2>/dev/null; then
    echo -e "${GREEN}女娲服务已强制停止${RESET}"
    rm -f "$PID_FILE"
else
    echo -e "${RED}停止服务失败${RESET}"
    exit 1
fi