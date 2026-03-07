#!/bin/bash

# 女娲 (Nuwa) 健康检查脚本 for Linux/macOS
# 使用方法: ./health.sh

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

# 打印标题
echo -e "${BLUE}女娲服务健康检查${RESET}"
echo "------------------------"

# 检查服务状态
if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}错误: 服务未运行${RESET}"
    exit 1
fi

PID=$(cat "$PID_FILE" 2>/dev/null)
if [ -z "$PID" ]; then
    echo -e "${RED}错误: 服务未运行${RESET}"
    rm -f "$PID_FILE"
    exit 1
fi

# 检查进程是否存在
if ! kill -0 "$PID" 2>/dev/null; then
    echo -e "${RED}错误: 服务未运行${RESET}"
    rm -f "$PID_FILE"
    exit 1
fi

# 服务运行状态
echo -e "${GREEN}✓ 服务运行中 (PID: $PID)${RESET}"

# 检查HTTP健康端点
echo -e "${BLUE}检查服务健康端点...${RESET}"
if command -v curl >/dev/null; then
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}✓ 健康端点可访问${RESET}"
        # 尝试获取详细信息
        HEALTH_DATA=$(curl -s http://localhost:8000/health 2>/dev/null)
        if [ -n "$HEALTH_DATA" ]; then
            echo -e "${BLUE}详细信息:${RESET}"
            echo "$HEALTH_DATA" | jq -r 'to_entries[] | "  \(.key): \(.value)"' 2>/dev/null || echo "  $HEALTH_DATA"
        fi
    else
        echo -e "${RED}✗ 健康端点返回状态码: $RESPONSE${RESET}"
    fi
elif command -v wget >/dev/null; then
    RESPONSE=$(wget -q -O /dev/null --server-response http://localhost:8000/health 2>&1 | grep "HTTP/" | awk '{print $2}')
    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}✓ 健康端点可访问${RESET}"
    else
        echo -e "${RED}✗ 健康端点返回状态码: $RESPONSE${RESET}"
    fi
else
    echo -e "${YELLOW}✗ 无法检查健康端点 (缺少curl或wget)${RESET}"
fi

# 检查系统资源
echo -e "${BLUE}检查系统资源...${RESET}"

# 进程资源使用
if command -v ps >/dev/null; then
    PROCESS_MEM=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{print $1/1024}')
    if [ -n "$PROCESS_MEM" ]; then
        echo -e "${GREEN}✓ 内存使用: $(printf "%.2f" "$PROCESS_MEM") MB${RESET}"
    else
        echo -e "${YELLOW}✗ 无法获取进程内存信息${RESET}"
    fi
    
    PROCESS_CPU=$(ps -o %cpu= -p "$PID" 2>/dev/null | awk '{print $1}')
    if [ -n "$PROCESS_CPU" ]; then
        echo -e "${GREEN}✓ CPU使用率: $(printf "%.1f" "$PROCESS_CPU")%${RESET}"
    else
        echo -e "${YELLOW}✗ 无法获取进程CPU信息${RESET}"
    fi
else
    echo -e "${YELLOW}✗ 无法获取进程资源信息 (缺少ps)${RESET}"
fi

# 系统内存使用
if command -v free >/dev/null; then
    MEMORY_INFO=$(free -m | grep Mem:)
    TOTAL_MEM=$(echo "$MEMORY_INFO" | awk '{print $2}')
    USED_MEM=$(echo "$MEMORY_INFO" | awk '{print $3}')
    MEMORY_USAGE=$(echo "scale=1; $USED_MEM / $TOTAL_MEM * 100" | bc)
    echo -e "${GREEN}✓ 系统内存: ${USED_MEM} MB / ${TOTAL_MEM} MB (${MEMORY_USAGE}%)${RESET}"
elif command -v vm_stat >/dev/null; then
    # macOS 内存信息
    TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print $1/1024/1024}')
    FREE_MEM=$(vm_stat | grep "Pages free:" | awk '{print $3 * 4096 / 1024/1024}')
    USED_MEM=$(echo "$TOTAL_MEM - $FREE_MEM" | bc)
    MEMORY_USAGE=$(echo "scale=1; $USED_MEM / $TOTAL_MEM * 100" | bc)
    echo -e "${GREEN}✓ 系统内存: $(printf "%.0f" "$USED_MEM") MB / $(printf "%.0f" "$TOTAL_MEM") MB (${MEMORY_USAGE}%)${RESET}"
else
    echo -e "${YELLOW}✗ 无法获取系统内存信息${RESET}"
fi

# 系统CPU使用率
if command -v top >/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
        CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    else
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    fi
    if [ -n "$CPU_USAGE" ]; then
        echo -e "${GREEN}✓ 系统CPU使用率: $(printf "%.1f" "$CPU_USAGE")%${RESET}"
    else
        echo -e "${YELLOW}✗ 无法获取系统CPU使用率${RESET}"
    fi
else
    echo -e "${YELLOW}✗ 无法获取系统CPU使用率 (缺少top)${RESET}"
fi

# 检查磁盘空间
echo -e "${BLUE}检查磁盘空间...${RESET}"
if command -v df >/dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS 磁盘信息
        DISK_INFO=$(df -h / | tail -n 1)
    else
        # Linux 磁盘信息
        DISK_INFO=$(df -h / | tail -n 1)
    fi
    if [ -n "$DISK_INFO" ]; then
        USED_SPACE=$(echo "$DISK_INFO" | awk '{print $3}')
        TOTAL_SPACE=$(echo "$DISK_INFO" | awk '{print $2}')
        USAGE_PERCENT=$(echo "$DISK_INFO" | awk '{print $5}')
        echo -e "${GREEN}✓ 磁盘空间: ${USED_SPACE} / ${TOTAL_SPACE} (${USAGE_PERCENT})${RESET}"
    else
        echo -e "${YELLOW}✗ 无法获取磁盘空间信息${RESET}"
    fi
else
    echo -e "${YELLOW}✗ 无法获取磁盘空间信息 (缺少df)${RESET}"
fi

# 检查端口状态
echo -e "${BLUE}检查端口状态...${RESET}"
if command -v netstat >/dev/null; then
    if netstat -tuln | grep -q ":8000 "; then
        echo -e "${GREEN}✓ 端口 8000 已监听${RESET}"
    else
        echo -e "${RED}✗ 端口 8000 未监听${RESET}"
    fi
elif command -v lsof >/dev/null; then
    if lsof -i :8000 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ 端口 8000 已监听${RESET}"
    else
        echo -e "${RED}✗ 端口 8000 未监听${RESET}"
    fi
else
    echo -e "${YELLOW}✗ 无法检查端口状态 (缺少netstat或lsof)${RESET}"
fi

echo -e "${BLUE}------------------------${RESET}"
echo -e "${GREEN}健康检查完成${RESET}"