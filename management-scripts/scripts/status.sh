#!/bin/bash

# 女娲 (Nuwa) 状态检查脚本 for Linux/macOS
# 使用方法: ./status.sh

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
    echo -e "${YELLOW}状态: 已停止${RESET}"
    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE" 2>/dev/null)
if [ -z "$PID" ]; then
    echo -e "${YELLOW}状态: 已停止${RESET}"
    rm -f "$PID_FILE"
    exit 0
fi

# 检查进程是否存在
if ! kill -0 "$PID" 2>/dev/null; then
    echo -e "${YELLOW}状态: 已停止${RESET}"
    rm -f "$PID_FILE"
    exit 0
fi

# 进程正在运行
echo -e "${GREEN}状态: 运行中${RESET}"
echo "PID: $PID"

# 获取进程信息
if command -v ps >/dev/null; then
    PROCESS_INFO=$(ps -p "$PID" -o comm=,etime=,rss= 2>/dev/null)
    if [ -n "$PROCESS_INFO" ]; then
        echo "进程信息: $PROCESS_INFO"
    fi
fi

# 检查服务是否可访问
echo -e "${BLUE}检查服务可访问性...${RESET}"
if command -v curl >/dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}服务可访问${RESET}"
    else
        echo -e "${YELLOW}服务返回状态码: $RESPONSE${RESET}"
    fi
elif command -v wget >/dev/null; then
    RESPONSE=$(wget -q -O /dev/null --server-response http://localhost:8000/health 2>&1 | grep "HTTP/" | awk '{print $2}')
    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}服务可访问${RESET}"
    else
        echo -e "${YELLOW}服务返回状态码: $RESPONSE${RESET}"
    fi
else
    echo -e "${YELLOW}无法检查服务可访问性 (缺少curl或wget)${RESET}"
fi