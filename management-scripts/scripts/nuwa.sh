#!/bin/bash
# 女娲统一管理入口 (Linux/macOS)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 全局变量
SCRIPT_DIR=$(dirname "$(realpath "$0")")
NUWA_ROOT=$(dirname "$SCRIPT_DIR")
NUWACTL_PATH="$SCRIPT_DIR/nuwactl.py"

# 确保脚本有执行权限
ensure_executable() {
    if [ ! -x "$NUWACTL_PATH" ]; then
        chmod +x "$NUWACTL_PATH"
    fi
}

# 显示欢迎信息
display_welcome() {
    echo -e "${BLUE}"
    echo -e "=================================================="
    echo -e "🧱 女娲管理工具"
    echo -e "=================================================="
    echo -e "${GREEN}统一管理入口${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    echo -e "输入 'help' 查看可用命令，'exit' 退出"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    echo -e ""
}

# 主函数
main() {
    ensure_executable
    display_welcome
    
    # 启动交互式管理工具
    python3 "$NUWACTL_PATH"
}

# 执行主函数
main