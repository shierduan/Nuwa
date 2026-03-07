#!/bin/bash
# 女娲测试脚本 (Linux/macOS)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
NUWA_ROOT=$(dirname "$(dirname "$(realpath "$0")")")
TEST_DIR="$NUWA_ROOT/tests"
LOG_DIR="$NUWA_ROOT/logs"
TEST_REPORT="$LOG_DIR/test_report.log"

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
    echo "[$timestamp] [$level] $message" >> "$TEST_REPORT"
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
    log "INFO" "检查测试依赖..."
    
    # 检查Python
    if ! command -v python3 > /dev/null; then
        log "ERROR" "Python 3 未找到"
        return 1
    fi
    
    # 检查pytest
    if ! python3 -m pytest --version > /dev/null 2>&1; then
        log "INFO" "安装pytest..."
        python3 -m pip install pytest > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            log "ERROR" "pytest 安装失败"
            return 1
        fi
    fi
    
    # 检查测试目录
    if [ ! -d "$TEST_DIR" ]; then
        log "ERROR" "测试目录不存在: $TEST_DIR"
        return 1
    fi
    
    return 0
}

# 运行测试
run_tests() {
    ensure_log_dir
    log "INFO" "运行女娲测试"
    
    if ! check_dependencies; then
        return 1
    fi
    
    log "INFO" "测试目录: $TEST_DIR"
    log "INFO" "测试报告: $TEST_REPORT"
    
    # 运行测试
    log "INFO" "开始运行测试..."
    
    python3 -m pytest "$TEST_DIR" -v --tb=short | tee -a "$TEST_REPORT"
    local test_result=$?
    
    if [ $test_result -eq 0 ]; then
        log "SUCCESS" "所有测试通过"
    else
        log "ERROR" "测试失败"
    fi
    
    log "INFO" "测试完成，结果已保存到: $TEST_REPORT"
    
    return $test_result
}

# 运行特定测试
run_specific_test() {
    local test_file="$1"
    ensure_log_dir
    log "INFO" "运行特定测试: $test_file"
    
    if ! check_dependencies; then
        return 1
    fi
    
    if [ ! -f "$test_file" ]; then
        log "ERROR" "测试文件不存在: $test_file"
        return 1
    fi
    
    log "INFO" "开始运行测试..."
    
    python3 -m pytest "$test_file" -v --tb=short | tee -a "$TEST_REPORT"
    local test_result=$?
    
    if [ $test_result -eq 0 ]; then
        log "SUCCESS" "测试通过"
    else
        log "ERROR" "测试失败"
    fi
    
    return $test_result
}

# 主函数
main() {
    if [ $# -eq 1 ]; then
        # 运行特定测试
        run_specific_test "$1"
    else
        # 运行所有测试
        run_tests
    fi
}

# 执行主函数
main "$@"