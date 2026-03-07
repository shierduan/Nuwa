#!/bin/bash
set -euo pipefail

# 女娲 (Nuwa) 安装脚本 for macOS and Linux
# 使用方法: curl -fsSL --proto '=https' --tlsv1.2 https://nuwa.ai/install.sh | bash

BOLD='\033[1m'
ACCENT='\033[38;2;255;77;77m'       # 珊瑚红
INFO='\033[38;2;136;146;176m'       # 次要文本
SUCCESS='\033[38;2;0;229;204m'      # 亮青色
WARN='\033[38;2;255;176;32m'        # 琥珀色
ERROR='\033[38;2;230;57;70m'        # 珊瑚中色
MUTED='\033[38;2;90;100;128m'       # 静音文本
NC='\033[0m' # 无颜色

DEFAULT_TAGLINE="🧱 女娲 - 类人AI对话系统"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=11
PYTHON_MIN_VERSION="${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}"

ORIGINAL_PATH="${PATH:-}"

TMPFILES=()
cleanup_tmpfiles() {
    local f
    for f in "${TMPFILES[@]:-}"; do
        rm -rf "$f" 2>/dev/null || true
    done
}
trap cleanup_tmpfiles EXIT

mktempfile() {
    local f
    f="$(mktemp)"
    TMPFILES+=("$f")
    echo "$f"
}

DOWNLOADER=""
detect_downloader() {
    if command -v curl &> /dev/null; then
        DOWNLOADER="curl"
        return 0
    fi
    if command -v wget &> /dev/null; then
        DOWNLOADER="wget"
        return 0
    fi
    ui_error "缺少下载工具 (需要curl或wget)"
    exit 1
}

download_file() {
    local url="$1"
    local output="$2"
    if [[ -z "$DOWNLOADER" ]]; then
        detect_downloader
    fi
    if [[ "$DOWNLOADER" == "curl" ]]; then
        curl -fsSL --proto '=https' --tlsv1.2 --retry 3 --retry-delay 1 --retry-connrefused -o "$output" "$url"
        return
    fi
    wget -q --https-only --secure-protocol=TLSv1_2 --tries=3 --timeout=20 -O "$output" "$url"
}

run_remote_bash() {
    local url="$1"
    local tmp
    tmp="$(mktempfile)"
    download_file "$url" "$tmp"
    /bin/bash "$tmp"
}

is_non_interactive_shell() {
    if [[ "${NO_PROMPT:-0}" == "1" ]]; then
        return 0
    fi
    if [[ ! -t 0 || ! -t 1 ]]; then
        return 0
    fi
    return 1
}

ui_info() {
    local msg="$*"
    echo -e "${MUTED}·${NC} ${msg}"
}

ui_warn() {
    local msg="$*"
    echo -e "${WARN}!${NC} ${msg}"
}

ui_success() {
    local msg="$*"
    echo -e "${SUCCESS}✓${NC} ${msg}"
}

ui_error() {
    local msg="$*"
    echo -e "${ERROR}✗${NC} ${msg}"
}

ui_section() {
    local title="$1"
    echo ""
    echo -e "${ACCENT}${BOLD}${title}${NC}"
}

ui_kv() {
    local key="$1"
    local value="$2"
    echo -e "${MUTED}${key}:${NC} ${value}"
}

ui_panel() {
    local content="$1"
    echo "$content"
}

show_install_plan() {
    local detected_checkout="$1"

    ui_section "安装计划"
    ui_kv "操作系统" "$OS"
    ui_kv "安装方式" "$INSTALL_METHOD"
    if [[ "$INSTALL_METHOD" == "git" ]]; then
        ui_kv "Git目录" "$GIT_DIR"
        ui_kv "Git更新" "$GIT_UPDATE"
    fi
    if [[ -n "$detected_checkout" ]]; then
        ui_kv "检测到的检出" "$detected_checkout"
    fi
    if [[ "$DRY_RUN" == "1" ]]; then
        ui_kv "模拟运行" "是"
    fi
    if [[ "$NO_ONBOARD" == "1" ]]; then
        ui_kv "引导" "跳过"
    fi
}

show_footer_links() {
    local faq_url="https://docs.nuwa.ai/start/faq"
    echo ""
    echo -e "FAQ: ${INFO}${faq_url}${NC}"
}

ui_celebrate() {
    local msg="$1"
    echo -e "${SUCCESS}${BOLD}${msg}${NC}"
}

is_shell_function() {
    local name="${1:-}"
    [[ -n "$name" ]] && declare -F "$name" >/dev/null 2>&1
}

run_with_spinner() {
    local title="$1"
    shift

    "$@"
}

run_quiet_step() {
    local title="$1"
    shift

    if [[ "$VERBOSE" == "1" ]]; then
        run_with_spinner "$title" "$@"
        return $?
    fi

    local log
    log="$(mktempfile)"

    if "$@" >"$log" 2>&1; then
        return 0
    fi

    ui_error "${title} 失败 — 重新运行时使用 --verbose 查看详细信息"
    if [[ -s "$log" ]]; then
        tail -n 80 "$log" >&2 || true
    fi
    return 1
}

detect_os_or_die() {
    OS="unknown"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
        OS="linux"
    fi

    if [[ "$OS" == "unknown" ]]; then
        ui_error "不支持的操作系统"
        echo "此安装程序支持 macOS 和 Linux (包括 WSL)。"
        echo "对于 Windows，请使用: iwr -useb https://nuwa.ai/install.ps1 | iex"
        exit 1
    fi

    ui_success "检测到: $OS"
}

# 检测Arch-based发行版 (Arch Linux, Manjaro, EndeavourOS等)
is_arch_linux() {
    if [[ -f /etc/os-release ]]; then
        local os_id
        os_id="$(grep -E '^ID=' /etc/os-release 2>/dev/null | cut -d'=' -f2 | tr -d '"' || true)"
        case "$os_id" in
            arch|manjaro|endeavouros|arcolinux|garuda|archarm|cachyos|archcraft)
                return 0
                ;;
        esac
        # 也检查ID_LIKE以获取Arch衍生版
        local os_id_like
        os_id_like="$(grep -E '^ID_LIKE=' /etc/os-release 2>/dev/null | cut -d'=' -f2 | tr -d '"' || true)"
        if [[ "$os_id_like" == *arch* ]]; then
            return 0
        fi
    fi
    # 回退: 检查pacman
    if command -v pacman &> /dev/null; then
        return 0
    fi
    return 1
}

install_build_tools_linux() {
    require_sudo

    if command -v apt-get &> /dev/null; then
        if is_root; then
            run_quiet_step "更新软件包索引" apt-get update -qq
            run_quiet_step "安装构建工具" apt-get install -y -qq build-essential python3-dev
        else
            run_quiet_step "更新软件包索引" sudo apt-get update -qq
            run_quiet_step "安装构建工具" sudo apt-get install -y -qq build-essential python3-dev
        fi
        return 0
    fi

    if command -v pacman &> /dev/null || is_arch_linux; then
        if is_root; then
            run_quiet_step "安装构建工具" pacman -Sy --noconfirm base-devel python
        else
            run_quiet_step "安装构建工具" sudo pacman -Sy --noconfirm base-devel python
        fi
        return 0
    fi

    if command -v dnf &> /dev/null; then
        if is_root; then
            run_quiet_step "安装构建工具" dnf install -y -q gcc gcc-c++ make python3-devel
        else
            run_quiet_step "安装构建工具" sudo dnf install -y -q gcc gcc-c++ make python3-devel
        fi
        return 0
    fi

    if command -v yum &> /dev/null; then
        if is_root; then
            run_quiet_step "安装构建工具" yum install -y -q gcc gcc-c++ make python3-devel
        else
            run_quiet_step "安装构建工具" sudo yum install -y -q gcc gcc-c++ make python3-devel
        fi
        return 0
    fi

    if command -v apk &> /dev/null; then
        if is_root; then
            run_quiet_step "安装构建工具" apk add --no-cache build-base python3-dev
        else
            run_quiet_step "安装构建工具" sudo apk add --no-cache build-base python3-dev
        fi
        return 0
    fi

    ui_warn "无法检测到包管理器来自动安装构建工具"
    return 1
}

install_build_tools_macos() {
    local ok=true

    if ! xcode-select -p >/dev/null 2>&1; then
        ui_info "安装Xcode命令行工具 (需要make/clang)"
        xcode-select --install >/dev/null 2>&1 || true
        if ! xcode-select -p >/dev/null 2>&1; then
            ui_warn "Xcode命令行工具尚未准备好"
            ui_info "完成安装对话框，然后重新运行此安装程序"
            ok=false
        fi
    fi

    if ! command -v make >/dev/null 2>&1; then
        ui_warn "make仍然不可用"
        ok=false
    fi

    [[ "$ok" == "true" ]]
}

parse_python_version_components() {
    if ! command -v python3 &> /dev/null; then
        return 1
    fi
    local version major minor
    version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    major="${version%%.*}"
    minor="${version#*.}"

    if [[ ! "$major" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    if [[ ! "$minor" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    echo "${major} ${minor}"
    return 0
}

python_major_version() {
    local version_components major minor
    version_components="$(parse_python_version_components || true)"
    read -r major minor <<< "$version_components"
    if [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]]; then
        echo "$major"
        return 0
    fi
    return 1
}

python_is_at_least_required() {
    local version_components major minor
    version_components="$(parse_python_version_components || true)"
    read -r major minor <<< "$version_components"
    if [[ ! "$major" =~ ^[0-9]+$ || ! "$minor" =~ ^[0-9]+$ ]]; then
        return 1
    fi
    if [[ "$major" -gt "$PYTHON_MIN_MAJOR" ]]; then
        return 0
    fi
    if [[ "$major" -eq "$PYTHON_MIN_MAJOR" && "$minor" -ge "$PYTHON_MIN_MINOR" ]]; then
        return 0
    fi
    return 1
}

print_active_python_paths() {
    if ! command -v python3 &> /dev/null; then
        return 1
    fi
    local python_path python_version pip_path pip_version
    python_path="$(command -v python3 2>/dev/null || true)"
    python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null || true)"
    ui_info "活跃的Python: ${python_version:-unknown} (${python_path:-unknown})"

    if command -v pip3 &> /dev/null; then
        pip_path="$(command -v pip3 2>/dev/null || true)"
        pip_version="$(pip3 --version 2>/dev/null | cut -d' ' -f2 || true)"
        ui_info "活跃的pip: ${pip_version:-unknown} (${pip_path:-unknown})"
    fi
    return 0
}

check_python() {
    if command -v python3 &> /dev/null; then
        if python_is_at_least_required; then
            ui_success "Python v$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")') 已找到"
            print_active_python_paths || true
            return 0
        else
            ui_info "Python $(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') 已找到，需要升级到 v${PYTHON_MIN_VERSION}+"
            return 1
        fi
    else
        ui_info "未找到Python，现在安装"
        return 1
    fi
}

# 安装Python
install_python() {
    if [[ "$OS" == "macos" ]]; then
        ui_info "通过Homebrew安装Python"
        run_quiet_step "安装python@3.11" brew install python@3.11
        brew link python@3.11 --overwrite --force 2>/dev/null || true
        ui_success "Python已安装"
        print_active_python_paths || true
    elif [[ "$OS" == "linux" ]]; then
        require_sudo

        ui_info "安装Linux构建工具 (make/g++/python3-dev)"
        if install_build_tools_linux; then
            ui_success "构建工具已安装"
        else
            ui_warn "继续而不自动安装构建工具"
        fi

        # Arch-based发行版: 使用pacman与官方仓库
        if command -v pacman &> /dev/null || is_arch_linux; then
            ui_info "通过pacman安装Python (检测到Arch-based发行版)"
            if is_root; then
                run_quiet_step "安装Python" pacman -Sy --noconfirm python python-pip
            else
                run_quiet_step "安装Python" sudo pacman -Sy --noconfirm python python-pip
            fi
            ui_success "Python已安装"
            print_active_python_paths || true
            return 0
        fi

        # Ubuntu/Debian
        if command -v apt-get &> /dev/null; then
            ui_info "通过apt安装Python"
            if is_root; then
                run_quiet_step "更新软件包索引" apt-get update -qq
                run_quiet_step "安装Python" apt-get install -y -qq python3.11 python3.11-dev python3-pip
            else
                run_quiet_step "更新软件包索引" sudo apt-get update -qq
                run_quiet_step "安装Python" sudo apt-get install -y -qq python3.11 python3.11-dev python3-pip
            fi
        # RHEL/CentOS
        elif command -v dnf &> /dev/null; then
            ui_info "通过dnf安装Python"
            if is_root; then
                run_quiet_step "安装Python" dnf install -y -q python3.11 python3.11-devel python3-pip
            else
                run_quiet_step "安装Python" sudo dnf install -y -q python3.11 python3.11-devel python3-pip
            fi
        # 其他Linux
        else
            ui_error "无法检测到包管理器"
            echo "请手动安装Python ${PYTHON_MIN_VERSION}+: https://www.python.org"
            exit 1
        fi

        ui_success "Python已安装"
        print_active_python_paths || true
    fi
}

# 检查Git
check_git() {
    if command -v git &> /dev/null; then
        ui_success "Git已安装"
        return 0
    fi
    ui_info "未找到Git，现在安装"
    return 1
}

is_root() {
    [[ "$(id -u)" -eq 0 ]]
}

# 仅在非root时使用sudo运行命令
maybe_sudo() {
    if is_root; then
        "$@"
    else
        sudo "$@"
    fi
}

require_sudo() {
    if [[ "$OS" != "linux" ]]; then
        return 0
    fi
    if is_root; then
        return 0
    fi
    if command -v sudo &> /dev/null; then
        if ! sudo -n true >/dev/null 2>&1; then
            ui_info "需要管理员权限; 请输入密码"
            sudo -v
        fi
        return 0
    fi
    ui_error "在Linux上进行系统安装需要sudo"
    echo "  安装sudo或以root身份重新运行。"
    exit 1
}

install_git() {
    if [[ "$OS" == "macos" ]]; then
        run_quiet_step "安装Git" brew install git
    elif [[ "$OS" == "linux" ]]; then
        require_sudo
        if command -v apt-get &> /dev/null; then
            if is_root; then
                run_quiet_step "更新软件包索引" apt-get update -qq
                run_quiet_step "安装Git" apt-get install -y -qq git
            else
                run_quiet_step "更新软件包索引" sudo apt-get update -qq
                run_quiet_step "安装Git" sudo apt-get install -y -qq git
            fi
        elif command -v pacman &> /dev/null || is_arch_linux; then
            if is_root; then
                run_quiet_step "安装Git" pacman -Sy --noconfirm git
            else
                run_quiet_step "安装Git" sudo pacman -Sy --noconfirm git
            fi
        elif command -v dnf &> /dev/null; then
            if is_root; then
                run_quiet_step "安装Git" dnf install -y -q git
            else
                run_quiet_step "安装Git" sudo dnf install -y -q git
            fi
        elif command -v yum &> /dev/null; then
            if is_root; then
                run_quiet_step "安装Git" yum install -y -q git
            else
                run_quiet_step "安装Git" sudo yum install -y -q git
            fi
        else
            ui_error "无法检测到Git的包管理器"
            exit 1
        fi
    fi
    ui_success "Git已安装"
}

# 修复pip权限（Linux）
fix_pip_permissions() {
    if [[ "$OS" != "linux" ]]; then
        return 0
    fi

    local pip_prefix
    pip_prefix="$(python3 -m pip config get prefix 2>/dev/null || true)"
    if [[ -z "$pip_prefix" ]]; then
        return 0
    fi

    if [[ -w "$pip_prefix" || -w "$pip_prefix/lib" ]]; then
        return 0
    fi

    ui_info "配置pip用于用户本地安装"
    mkdir -p "$HOME/.local/bin"
    python3 -m pip config set prefix "$HOME/.local"

    # 添加到PATH
    if [[ "$SHELL" == *bash* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    elif [[ "$SHELL" == *zsh* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    fi

    # 为当前会话更新PATH
export PATH="$HOME/.local/bin:$PATH"
    ui_success "pip权限已修复"
}

install_nuwa_git() {
    local repo_dir="$1"
    local update="$2"

    ui_info "从git安装女娲..."

    if [[ ! -d "$repo_dir" ]]; then
        ui_info "  克隆仓库..."
        git clone https://github.com/nuwa-ai/nuwa-core.git "$repo_dir"
    elif [[ "$update" == "1" ]]; then
        ui_info "  更新仓库..."
        git -C "$repo_dir" pull --rebase
    fi

    # 安装依赖
    ui_info "  安装依赖..."
    python3 -m pip install -r "$repo_dir/requirements.txt"

    # 创建包装器
    local wrapper_dir="$HOME/.local/bin"
    mkdir -p "$wrapper_dir"

    cat > "$wrapper_dir/nuwa" << 'EOF'
#!/bin/bash
python3 "$(dirname "$0")/../nuwa/main_async.py" "$@"
EOF

    chmod +x "$wrapper_dir/nuwa"

    ui_success "女娲已安装"
    return 0
}

install_nuwa_local() {
    ui_info "使用本地安装方式..."

    # 检查当前目录是否为女娲项目
    if [[ -f "requirements.txt" ]]; then
        ui_info "  在当前目录安装依赖..."
        python3 -m pip install -r requirements.txt
        ui_success "女娲依赖已安装"
        return 0
    else
        ui_error "错误: 当前目录不是女娲项目目录，缺少requirements.txt文件"
        return 1
    fi
}

TAGLINE="$DEFAULT_TAGLINE"

NO_ONBOARD=${NUWA_NO_ONBOARD:-0}
NO_PROMPT=${NUWA_NO_PROMPT:-0}
DRY_RUN=${NUWA_DRY_RUN:-0}
INSTALL_METHOD=${NUWA_INSTALL_METHOD:-git}
GIT_DIR_DEFAULT="${HOME}/nuwa"
GIT_DIR=${NUWA_GIT_DIR:-$GIT_DIR_DEFAULT}
GIT_UPDATE=${NUWA_GIT_UPDATE:-1}
VERBOSE=${NUWA_VERBOSE:-0}
HELP=0

print_usage() {
    cat <<EOF
女娲安装程序 (macOS + Linux)

使用方法:
  curl -fsSL --proto '=https' --tlsv1.2 https://nuwa.ai/install.sh | bash -s -- [选项]

选项:
  --install-method, --method git|local   通过git (默认) 或本地目录安装
  --git, --github                       --install-method git 的快捷方式
  --local                               --install-method local 的快捷方式
  --git-dir, --dir <路径>              检出目录 (默认: ~/nuwa)
  --no-git-update                      跳过现有检出的git pull
  --no-onboard                          跳过引导 (非交互式)
  --no-prompt                           禁用提示 (CI/自动化中必需)
  --dry-run                             打印将要发生的事情 (无更改)
  --verbose                             打印调试输出
  --help, -h                            显示此帮助

环境变量:
  NUWA_INSTALL_METHOD=git|local
  NUWA_GIT_DIR=...
  NUWA_GIT_UPDATE=0|1
  NUWA_NO_PROMPT=1
  NUWA_DRY_RUN=1
  NUWA_NO_ONBOARD=1
  NUWA_VERBOSE=1

示例:
  curl -fsSL --proto '=https' --tlsv1.2 https://nuwa.ai/install.sh | bash
  curl -fsSL --proto '=https' --tlsv1.2 https://nuwa.ai/install.sh | bash -s -- --no-onboard
  curl -fsSL --proto '=https' --tlsv1.2 https://nuwa.ai/install.sh | bash -s -- --install-method local --no-onboard
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-onboard)
                NO_ONBOARD=1
                shift
                ;;
            --onboard)
                NO_ONBOARD=0
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --verbose)
                VERBOSE=1
                shift
                ;;
            --no-prompt)
                NO_PROMPT=1
                shift
                ;;
            --help|-h)
                HELP=1
                shift
                ;;
            --install-method|--method)
                INSTALL_METHOD="$2"
                shift 2
                ;;
            --git|--github)
                INSTALL_METHOD="git"
                shift
                ;;
            --local)
                INSTALL_METHOD="local"
                shift
                ;;
            --git-dir|--dir)
                GIT_DIR="$2"
                shift 2
                ;;
            --no-git-update)
                GIT_UPDATE=0
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
}

configure_verbose() {
    if [[ "$VERBOSE" != "1" ]]; then
        return 0
    fi
    set -x
}

is_promptable() {
    if [[ "$NO_PROMPT" == "1" ]]; then
        return 1
    fi
    if [[ -r /dev/tty && -w /dev/tty ]]; then
        return 0
    fi
    return 1
}

print_installer_banner() {
    echo -e "${ACCENT}${BOLD}"
    echo "  🧱 女娲安装程序"
    echo -e "${NC}${INFO}  ${TAGLINE}${NC}"
    echo ""
}

# 检查Homebrew on macOS
is_macos_admin_user() {
    if [[ "$OS" != "macos" ]]; then
        return 0
    fi
    if is_root; then
        return 0
    fi
    id -Gn "$(id -un)" 2>/dev/null | grep -qw "admin"
}

print_homebrew_admin_fix() {
    local current_user
    current_user="$(id -un 2>/dev/null || echo "${USER:-current user}")"
    ui_error "Homebrew安装需要macOS管理员账户"
    echo "当前用户 (${current_user}) 不在admin组中。"
    echo "修复选项:"
    echo "  1) 使用管理员账户并重新运行安装程序。"
    echo "  2) 请管理员授予admin权限，然后登出/登入:"
    echo "     sudo dseditgroup -o edit -a ${current_user} -t user admin"
    echo "然后重试:"
    echo "  curl -fsSL https://nuwa.ai/install.sh | bash"
}

install_homebrew() {
    if [[ "$OS" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            if ! is_macos_admin_user; then
                print_homebrew_admin_fix
                exit 1
            fi
            ui_info "未找到Homebrew，正在安装"
            run_quiet_step "安装Homebrew" run_remote_bash "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

            # 将Homebrew添加到当前会话的PATH
            if [[ -f "/opt/homebrew/bin/brew" ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [[ -f "/usr/local/bin/brew" ]]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
            ui_success "Homebrew已安装"
        else
            ui_success "Homebrew已安装"
        fi
    fi
}

# 主函数
main() {
    parse_args "$@"

    if [[ "$HELP" == "1" ]]; then
        print_usage
        exit 0
    fi

    configure_verbose
    detect_os_or_die

    if [[ "$OS" == "macos" ]]; then
        install_homebrew
    fi

    print_installer_banner

    # 检查Python
    if ! check_python; then
        install_python
    fi

    # 修复pip权限
    fix_pip_permissions

    # 检查Git（如果需要）
    if [[ "$INSTALL_METHOD" == "git" ]]; then
        if ! check_git; then
            install_git
        fi
    fi

    # 显示安装计划
    show_install_plan ""

    if [[ "$DRY_RUN" == "1" ]]; then
        ui_info "模拟运行完成，无实际更改"
        exit 0
    fi

    # 执行安装
    if [[ "$INSTALL_METHOD" == "git" ]]; then
        install_nuwa_git "$GIT_DIR" "$GIT_UPDATE"
    else
        install_nuwa_local
    fi

    # 显示完成信息
    if [[ "$NO_ONBOARD" != "1" ]]; then
        echo ""
        ui_info "运行 'python main_async.py' 启动女娲服务"
        ui_info "访问 http://localhost:8000 查看服务状态"
    fi

    echo ""
    ui_celebrate "🧱 女娲安装成功!"
    show_footer_links
}

main "$@"