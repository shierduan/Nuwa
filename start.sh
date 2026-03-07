#!/bin/bash
# 女娲启动脚本 (Linux)
# 用于在 Linux 系统上启动女娲服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查 Python 版本
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "未找到 Python 3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python 版本：$PYTHON_VERSION"
}

# 检查虚拟环境
check_venv() {
    if [ ! -d ".venv" ]; then
        log_warning "虚拟环境不存在，正在创建..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        source .venv/bin/activate
        log_success "虚拟环境已激活"
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查关键依赖..."
    
    MISSING_DEPS=()
    
    # 检查 pyarrow
    if ! python3 -c "import pyarrow" 2>/dev/null; then
        MISSING_DEPS+=("pyarrow")
    fi
    
    # 检查 lancedb
    if ! python3 -c "import lancedb" 2>/dev/null; then
        MISSING_DEPS+=("lancedb")
    fi
    
    # 检查 sentence-transformers
    if ! python3 -c "import sentence_transformers" 2>/dev/null; then
        MISSING_DEPS+=("sentence-transformers")
    fi
    
    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        log_error "缺少依赖包：${MISSING_DEPS[*]}"
        log_info "请运行 ./install_deps_linux.sh 安装依赖"
        exit 1
    fi
    
    log_success "所有依赖已安装"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    mkdir -p data logs management-scripts/scripts/data/nuwa
}

# 启动服务
start_service() {
    log_info "启动女娲核心服务..."
    
    # 设置环境变量
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    export NUWA_ENV=production
    export LOG_LEVEL=INFO
    
    # 启动主程序
    python3 main_async.py
}

# 显示帮助
show_help() {
    echo "用法：./start.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --help, -h     显示帮助信息"
    echo "  --install      安装依赖后启动"
    echo "  --dev          开发模式启动"
    echo ""
    echo "示例:"
    echo "  ./start.sh              # 正常启动"
    echo "  ./start.sh --install    # 安装依赖后启动"
    echo "  ./start.sh --dev        # 开发模式启动"
}

# 主函数
main() {
    echo "============================================================"
    echo "🧱 女娲管理工具 - Linux 启动脚本"
    echo "============================================================"
    
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --install)
            log_info "安装依赖..."
            chmod +x install_deps_linux.sh
            ./install_deps_linux.sh
            ;;
        --dev)
            log_info "开发模式启动..."
            export NUWA_ENV=development
            ;;
    esac
    
    check_python
    check_venv
    check_dependencies
    create_directories
    start_service
}

# 执行主函数
main "$@"
