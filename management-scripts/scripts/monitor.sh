#!/bin/bash
# 女娲监控脚本 (Linux/macOS)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
NUWA_ROOT=$(dirname "$(dirname "$(realpath "$0")")")
LOG_DIR="$NUWA_ROOT/logs"
MONITOR_LOG="$LOG_DIR/monitor.log"
PID_FILE="$NUWA_ROOT/nuwa.pid"
HEALTH_URL="http://localhost:8000/health"

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
    echo "[$timestamp] [$level] $message" >> "$MONITOR_LOG"
    case $level in
        "ERROR") echo -e "${RED}[$timestamp] [$level] $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}[$timestamp] [$level] $message${NC}" ;;
        "INFO") echo -e "${BLUE}[$timestamp] [$level] $message${NC}" ;;
        "SUCCESS") echo -e "${GREEN}[$timestamp] [$level] $message${NC}" ;;
        *) echo -e "[$timestamp] [$level] $message" ;;
    esac
}

# 检查服务状态
check_service_status() {
    if [ ! -f "$PID_FILE" ]; then
        log "ERROR" "PID文件不存在，服务可能未运行"
        return 1
    fi
    
    local pid=$(cat "$PID_FILE")
    if ! ps -p "$pid" > /dev/null 2>&1; then
        log "ERROR" "进程 $pid 不存在，服务可能已崩溃"
        return 1
    fi
    
    return 0
}

# 检查服务健康状态
check_health() {
    if ! curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" | grep -q "200"; then
        log "ERROR" "服务健康检查失败"
        return 1
    fi
    
    log "SUCCESS" "服务健康状态正常"
    return 0
}

# 发送通知
send_notification() {
    local message="$1"
    # 这里可以添加通知逻辑，如邮件、短信或其他通知方式
    log "INFO" "发送通知: $message"
    
    # 示例：发送到系统通知
    if command -v notify-send > /dev/null; then
        notify-send "女娲监控" "$message"
    fi
}

# 启动监控
start_monitor() {
    ensure_log_dir
    log "INFO" "启动女娲监控"
    
    # 检查是否已在运行
    if [ -f "$NUWA_ROOT/monitor.pid" ]; then
        local monitor_pid=$(cat "$NUWA_ROOT/monitor.pid")
        if ps -p "$monitor_pid" > /dev/null 2>&1; then
            log "WARNING" "监控已在运行，PID: $monitor_pid"
            return 1
        fi
    fi
    
    # 后台运行监控
    (while true; do
        log "INFO" "开始监控检查"
        
        if check_service_status; then
            if ! check_health; then
                send_notification "女娲服务健康检查失败"
            fi
        else
            send_notification "女娲服务未运行或已崩溃"
        fi
        
        # 每60秒检查一次
        sleep 60
    done) &
    
    local monitor_pid=$!
    echo "$monitor_pid" > "$NUWA_ROOT/monitor.pid"
    log "SUCCESS" "监控已启动，PID: $monitor_pid"
    echo "监控已启动，PID: $monitor_pid"
}

# 停止监控
stop_monitor() {
    if [ -f "$NUWA_ROOT/monitor.pid" ]; then
        local monitor_pid=$(cat "$NUWA_ROOT/monitor.pid")
        if ps -p "$monitor_pid" > /dev/null 2>&1; then
            kill "$monitor_pid"
            rm "$NUWA_ROOT/monitor.pid"
            log "SUCCESS" "监控已停止"
            echo "监控已停止"
        else
            rm "$NUWA_ROOT/monitor.pid"
            log "WARNING" "监控进程不存在，已清理PID文件"
            echo "监控进程不存在，已清理PID文件"
        fi
    else
        log "WARNING" "监控未运行"
        echo "监控未运行"
    fi
}

# 查看监控状态
status_monitor() {
    if [ -f "$NUWA_ROOT/monitor.pid" ]; then
        local monitor_pid=$(cat "$NUWA_ROOT/monitor.pid")
        if ps -p "$monitor_pid" > /dev/null 2>&1; then
            log "SUCCESS" "监控正在运行，PID: $monitor_pid"
            echo "监控正在运行，PID: $monitor_pid"
        else
            log "WARNING" "监控PID文件存在但进程不存在"
            echo "监控PID文件存在但进程不存在"
        fi
    else
        log "INFO" "监控未运行"
        echo "监控未运行"
    fi
}

# 主函数
main() {
    case "$1" in
        "start")
            start_monitor
            ;;
        "stop")
            stop_monitor
            ;;
        "status")
            status_monitor
            ;;
        "check")
            ensure_log_dir
            log "INFO" "手动检查服务状态"
            check_service_status
            check_health
            ;;
        *)
            echo "使用方法: $0 {start|stop|status|check}"
            echo "  start   - 启动监控"
            echo "  stop    - 停止监控"
            echo "  status  - 查看监控状态"
            echo "  check   - 手动检查服务状态"
            ;;
    esac
}

# 执行主函数
main "$@"