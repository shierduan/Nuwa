#!/bin/bash
# 女娲开发模式脚本 (Linux/macOS)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
NUWA_ROOT=$(dirname "$(dirname "$(realpath "$0")")")
LOG_DIR="$NUWA_ROOT/logs"
MAIN_SCRIPT="$NUWA_ROOT/main_async.py"

# 确保日志目录存在
ensure_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi
}

# 日志函数
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message"
    case $level in
        "ERROR") echo -e "${RED}[$timestamp] [$level] $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}[$timestamp] [$level] $message${NC}" ;;
        "INFO") echo -e "${BLUE}[$timestamp] [$level] $message${NC}" ;;
        "SUCCESS") echo -e "${GREEN}[$timestamp] [$level] $message${NC}" ;;
        *) echo -e "[$timestamp] [$level] $message" ;;
    esac
}

# 检查依赖
check_dependencies() {
    log "INFO" "检查依赖..."
    
    # 检查Python
    if ! command -v python3 > /dev/null; then
        log "ERROR" "Python 3 未找到"
        return 1
    fi
    
    # 检查main_async.py
    if [ ! -f "$MAIN_SCRIPT" ]; then
        log "ERROR" "main_async.py 未找到"
        return 1
    fi
    
    # 检查requirements.txt
    if [ -f "$NUWA_ROOT/requirements.txt" ]; then
        log "INFO" "检查Python依赖..."
        python3 -m pip install -r "$NUWA_ROOT/requirements.txt" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            log "WARNING" "依赖安装失败，可能会影响运行"
        else
            log "SUCCESS" "依赖安装成功"
        fi
    fi
    
    return 0
}

# 启动开发模式
start_dev() {
    ensure_log_dir
    log "INFO" "启动女娲开发模式"
    
    if ! check_dependencies; then
        return 1
    fi
    
    # 构建命令
    local cmd=(python3 "$MAIN_SCRIPT" --dev --verbose)
    
    # 添加端口和主机参数
    if [ -n "$PORT" ]; then
        cmd+=(--port "$PORT")
    fi
    
    if [ -n "$HOST" ]; then
        cmd+=(--host "$HOST")
    fi
    
    log "INFO" "运行命令: ${cmd[*]}"
    log "INFO" "开发模式已启动，按 Ctrl+C 停止"
    
    # 运行服务
    "${cmd[@]}"
}

# 主函数
main() {
    # 解析参数
    while getopts "p:h:" opt; do
        case $opt in
            p) PORT="$OPTARG" ;;
            h) HOST="$OPTARG" ;;
            *) echo "使用方法: $0 [-p 端口] [-h 主机]" ; exit 1 ;;
        esac
    done
    
    start_dev
}

# 执行主函数
main "$@"