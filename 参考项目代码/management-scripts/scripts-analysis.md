# OpenClaw 项目初始化和管理脚本分析

## 概述

OpenClaw 项目提供了一系列强大的初始化和管理脚本，用于简化开发、部署和维护过程。这些脚本覆盖了从安装到日常运营的各个方面，支持多种平台（Windows、macOS、Linux）和部署方式（npm、Git、容器）。

## 核心安装脚本

### 1. `install.sh` - Linux/macOS 安装脚本

**位置**: `scripts/install.sh`

**功能**: 自动安装 OpenClaw 的主要脚本，支持 npm 和 Git 两种安装方式。

**主要特性**:
- 自动检测系统环境（Windows/macOS/Linux）
- 支持 npm 全局安装和 Git 仓库克隆
- 自动安装必要的构建工具（如 make、cmake、Xcode 命令行工具）
- 智能错误处理和重试机制
- 支持调试模式（--verbose）
- 集成了美观的交互式 UI（使用 Charm 的 gum 工具）

**使用方法**:
```bash
# 基础安装
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash

# 自定义安装
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --git --no-onboard
```

**核心函数**:
- `detect_os_or_die()`: 检测并验证操作系统
- `bootstrap_gum_temp()`: 临时安装交互式 UI 工具
- `install_openclaw_npm()`: npm 安装逻辑
- `install_openclaw_git()`: Git 安装逻辑
- `auto_install_build_tools_for_npm_failure()`: 自动安装构建工具

### 2. `install.ps1` - Windows 安装脚本

**位置**: `scripts/install.ps1`

**功能**: PowerShell 版本的安装脚本，专门针对 Windows 系统优化。

**主要特性**:
- 支持通过 winget、chocolatey、scoop 等包管理器自动安装依赖
- 智能执行策略检测和处理
- 提供详细的安装进度反馈
- 支持 npm 和 Git 两种安装方式
- 自动配置系统 PATH 环境变量

**使用方法**:
```powershell
# 基础安装
iwr -useb https://openclaw.ai/install.ps1 | iex

# 自定义安装
& ([scriptblock]::Create((iwr -useb https://openclaw.ai/install.ps1))) -InstallMethod git -GitDir $env:USERPROFILE\openclaw -NoOnboard
```

**核心函数**:
- `Ensure-ExecutionPolicy()`: 处理 PowerShell 执行策略
- `Ensure-Node()`: 确保 Node.js 环境
- `Ensure-Git()`: 确保 Git 环境
- `Install-OpenClawNpm()`: npm 安装
- `Install-OpenClawGit()`: Git 安装

## 认证管理脚本

### 3. `setup-auth-system.sh` - 认证系统设置

**位置**: `scripts/setup-auth-system.sh`

**功能**: 配置 OpenClaw 认证管理系统，包括长期令牌、监控和移动端支持。

**主要配置**:
- **Claude 认证**: 管理 Claude API 令牌
- **系统监控**: 使用 systemd 定时检查认证状态
- **通知系统**: 支持 ntfy.sh 和短信通知
- **移动端支持**: Termux 小部件快速认证

**使用方法**:
```bash
# 运行认证系统设置
./scripts/setup-auth-system.sh
```

**设置步骤**:
1. 检查当前认证状态
2. 配置长期令牌
3. 设置系统监控
4. 配置通知渠道
5. 安装 Termux 小部件

**相关文件**:
- `systemd/openclaw-auth-monitor.service`: systemd 服务配置
- `systemd/openclaw-auth-monitor.timer`: 定时器配置
- `termux-quick-auth.sh`: Termux 快速认证脚本
- `termux-auth-widget.sh`: Termux 完整认证脚本

### 4. `claude-auth-status.sh` - 认证状态检查

**位置**: `scripts/claude-auth-status.sh`

**功能**: 检查当前 Claude API 认证状态，包括令牌有效期和使用情况。

**使用方法**:
```bash
# 检查认证状态
./scripts/claude-auth-status.sh

# 详细检查
./scripts/claude-auth-status.sh full
```

### 5. `auth-monitor.sh` - 认证监控

**位置**: `scripts/auth-monitor.sh`

**功能**: 定时监控认证状态，过期前发送通知。

**使用方法**:
```bash
# 运行认证监控（通常由 systemd 定时调用）
./scripts/auth-monitor.sh
```

**环境变量**:
- `NOTIFY_NTFY`: ntfy.sh 主题
- `NOTIFY_PHONE`: 通知电话
- `CLAUDE_API_KEY`: Claude API 密钥

## 应用管理脚本

### 6. `restart-mac.sh` - macOS 应用重启

**位置**: `scripts/restart-mac.sh`

**功能**: 完全重置 OpenClaw macOS 应用，包括清理、重新构建和重新启动。

**主要功能**:
- 杀死所有运行的 OpenClaw 实例
- 清理构建缓存
- 重新编译应用
- 重新打包应用
- 重新启动应用并验证运行状态

**使用方法**:
```bash
# 基础重启
./scripts/restart-mac.sh

# 选项
./scripts/restart-mac.sh --wait         # 等待其他重启完成
./scripts/restart-mac.sh --no-sign      # 跳过代码签名（快速开发）
./scripts/restart-mac.sh --sign         # 强制代码签名
./scripts/restart-mac.sh --attach-only  # 仅启动应用（跳过 launchd 安装）
```

### 7. `package-mac-app.sh` - macOS 应用打包

**位置**: `scripts/package-mac-app.sh`

**功能**: 将 OpenClaw 打包成 macOS 应用程序包。

**使用方法**:
```bash
./scripts/package-mac-app.sh
```

## 容器化管理脚本

### 8. `run-openclaw-podman.sh` - Podman 容器管理

**位置**: `scripts/run-openclaw-podman.sh`

**功能**: 管理 OpenClaw 的 Podman 容器化部署。

**主要特性**:
- 自动设置容器环境
- 生成安全的网关令牌
- 管理配置和工作区卷
- 支持容器启动、停止和重启
- 提供 onboarding 流程

**使用方法**:
```bash
# 启动容器（首次运行）
./scripts/run-openclaw-podman.sh launch setup

# 正常启动
./scripts/run-openclaw-podman.sh launch
```

**配置文件**:
- `~/.openclaw/.env`: 容器环境变量
- `~/.openclaw/openclaw.json`: 应用配置

### 9. `setup-podman.sh` - Podman 环境设置

**位置**: `setup-podman.sh` (项目根目录)

**功能**: 初始化 Podman 运行环境，包括用户创建和权限配置。

**使用方法**:
```bash
sudo ./setup-podman.sh
```

### 10. `test-cleanup-docker.sh` - Docker 清理测试

**位置**: `scripts/test-cleanup-docker.sh`

**功能**: 构建并测试 Docker 容器的资源清理功能。

**使用方法**:
```bash
./scripts/test-cleanup-docker.sh
```

### 11. `sandbox-setup.sh` - 沙箱环境设置

**位置**: `scripts/sandbox-setup.sh`

**功能**: 构建 OpenClaw 沙箱环境，用于隔离测试。

**使用方法**:
```bash
./scripts/sandbox-setup.sh
```

## 开发和测试脚本

### 12. `build-and-run-mac.sh` - macOS 开发构建

**位置**: `scripts/build-and-run-mac.sh`

**功能**: 快速构建并运行 OpenClaw macOS 应用的开发版本。

**使用方法**:
```bash
./scripts/build-and-run-mac.sh
```

### 13. `test-*.sh` - 测试脚本集合

**位置**: `scripts/` 目录下多个 test-*.sh 文件

**功能**: 自动化测试脚本，用于验证各种功能的正确性。

**主要脚本**:
- `test-live-models-docker.sh`: 测试 live 模型
- `test-live-gateway-models-docker.sh`: 测试网关 live 模型
- `test-install-sh-docker.sh`: 测试安装脚本
- `test-install-sh-e2e-docker.sh`: 端到端安装测试

## 文档和国际化脚本

### 14. `docs-i18n` - 文档国际化工具

**位置**: `scripts/docs-i18n/`

**功能**: 管理多语言文档翻译和同步。

**主要工具**:
- `translator.go`: 翻译主程序
- `main.go`: 命令行接口
- `*.tm.jsonl`: 翻译记忆库
- `glossary.zh-CN.json`: 术语表

**使用方法**:
```bash
# 翻译整个文档
cd scripts/docs-i18n
go run main.go -mode doc -parallel 6 ../../docs/**/*.md

# 翻译单个文件
go run main.go -mode doc ../../docs/channels/matrix.md
```

### 15. `build-docs-list.mjs` - 文档构建工具

**位置**: `scripts/build-docs-list.mjs`

**功能**: 生成文档索引和导航结构。

## 系统管理脚本

### 16. `package-mac-app.sh` - macOS 应用打包脚本

**位置**: `scripts/package-mac-app.sh`

**功能**: 将 OpenClaw 打包成 macOS 应用程序包（.app）。

**主要特性**:
- 自动构建并打包 OpenClaw 应用
- 支持多架构（arm64、x86_64 或 universal binary）
- 嵌入必要的资源文件（图标、设备模型、Sparkle 框架）
- 配置应用信息（版本号、构建号、Bundle ID）
- 处理代码签名和公证流程
- 自动停止并清理旧的应用实例

**使用方法**:
```bash
# 基础使用
./scripts/package-mac-app.sh

# 自定义配置
BUNDLE_ID=ai.openclaw.mac.production APP_VERSION=2026.3.5 ./scripts/package-mac-app.sh
```

**核心配置**:
- `BUNDLE_ID`: 应用程序标识符（默认：ai.openclaw.mac.debug）
- `APP_VERSION`: 应用版本号（默认：package.json 中的版本）
- `APP_BUILD`: 构建号（默认：Git 提交计数）
- `BUILD_CONFIG`: 构建配置（debug 或 release）
- `BUILD_ARCHS`: 构建架构（arm64、x86_64 或 all）

**输出位置**: `dist/OpenClaw.app`

### 17. `claude-auth-status.sh` - Claude 认证状态检查器

**位置**: `scripts/claude-auth-status.sh`

**功能**: 检查 Claude Code 和 OpenClaw 的认证状态。

**主要特性**:
- 同时检查两个位置的认证：Claude Code 和 OpenClaw
- 计算并显示认证剩余时间
- 支持多种输出格式：full、json、simple
- 使用颜色编码显示状态（绿色=OK，黄色=即将过期，红色=过期/缺失）
- 提供详细的操作建议

**使用方法**:
```bash
# 完整输出（默认）
./scripts/claude-auth-status.sh

# JSON 格式输出（用于脚本处理）
./scripts/claude-auth-status.sh json

# 简单输出（用于脚本判断）
./scripts/claude-auth-status.sh simple
```

**输出示例**:
```
=== Claude Code Auth Status ===

Claude Code (~/.claude/.credentials.json):
  Subscription: pro
  Rate tier: tier-3
  Status: OK
  Expires: Tue Mar  5 10:30:00 PM PST 2026 (23h 45m)

OpenClaw Auth (~/.openclaw/agents/main/agent/auth-profiles.json):
  Profile: anthropic:default
  Status: OK
  Expires: Tue Mar  5 10:45:00 PM PST 2026 (23h 55m)
```

**状态含义**:
- `OK`: 认证有效
- `EXPIRING SOON`: 认证将在 1 小时内过期
- `EXPIRED`: 认证已过期
- `NOT FOUND`: 未找到认证信息

### 18. `mobile-reauth.sh` - 移动端重认证脚本

**位置**: `scripts/mobile-reauth.sh`

**功能**: 为移动端设计的 Claude Code 重认证脚本，优化了手机端体验。

**主要特性**:
- 简化的认证流程，适合手机操作
- 检查当前认证状态
- 引导用户完成 claude setup-token 流程
- 显示易于在手机上打开的 URL
- 提供清晰的步骤说明
- 自动重启 OpenClaw 服务（如果需要）

**使用方法**:
```bash
# 在手机上通过 Termux 运行
./scripts/mobile-reauth.sh
```

**重认证流程**:
1. 检查当前认证状态
2. 显示需要打开的网页链接（https://console.anthropic.com/settings/api-keys）
3. 引导用户创建或获取 API 密钥
4. 运行 `claude setup-token` 进行配置
5. 验证认证成功并重启服务

### 19. `systemd` - 系统服务配置

**位置**: `scripts/systemd/`

**功能**: 提供 systemd 服务配置，用于在 Linux 系统上运行 OpenClaw。

**主要文件**:
- `openclaw-auth-monitor.service`: 认证监控服务
- `openclaw-auth-monitor.timer`: 认证监控定时器
- `openclaw-gateway.service`: 网关服务

### 17. `shell-helpers` - 通用工具函数

**位置**: `scripts/shell-helpers/`

**功能**: 提供项目范围使用的通用 shell 工具函数。

**主要文件**:
- `colored-echo.sh`: 彩色输出函数
- `common.sh`: 通用工具函数
- `file-helpers.sh`: 文件操作辅助函数

## 移动端管理脚本

### 18. `mobile-reauth.sh` - 移动设备重认证

**位置**: `scripts/mobile-reauth.sh`

**功能**: 帮助移动设备用户重新认证 OpenClaw。

**使用方法**:
```bash
./scripts/mobile-reauth.sh
```

### 19. `termux-*.sh` - Termux 小部件脚本

**位置**: `scripts/` 目录下多个 termux-*.sh 文件

**功能**: 为 Termux:Widget 提供快速认证功能。

**主要脚本**:
- `termux-quick-auth.sh`: 快速认证和状态检查
- `termux-auth-widget.sh`: 完整认证流程
- `termux-sync-widget.sh`: 同步状态检查

**使用方法**:
```bash
# 在 Termux 中设置
mkdir -p ~/.shortcuts
cp scripts/termux-quick-auth.sh ~/.shortcuts/ClawdAuth
chmod +x ~/.shortcuts/ClawdAuth
```

## 代码质量和验证脚本

### 20. `check-*.mjs/.ts` - 代码检查脚本

**位置**: `scripts/` 目录下多个 check-*.mjs/.ts 文件

**功能**: 自动化代码质量和架构检查工具。

**主要脚本**:
- `check-channel-agnostic-boundaries.mjs`: 检查通道无关边界
- `check-no-random-messaging-tmp.mjs`: 检查临时消息目录使用
- `check-no-raw-channel-fetch.mjs`: 检查原始通道获取
- `check-plugin-sdk-exports.mjs`: 检查插件 SDK 导出

### 21. `pre-commit` - 提交前检查

**位置**: `scripts/pre-commit/`

**功能**: Git 提交前的自动检查脚本。

## 性能和基准测试脚本

### 22. `bench-cli-startup.ts` - CLI 启动时间基准测试

**位置**: `scripts/bench-cli-startup.ts`

**功能**: 测量 OpenClaw CLI 的启动性能。

**使用方法**:
```bash
./scripts/bench-cli-startup.ts
```

### 23. `bench-model.ts` - 模型性能基准测试

**位置**: `scripts/bench-model.ts`

**功能**: 测试各种 LLM 模型的响应时间和性能。

## 使用建议和最佳实践

### 1. 选择合适的安装方式

- **生产环境**: 使用 npm 安装（`install.sh` 或 `install.ps1`）
- **开发环境**: 使用 Git 克隆安装（`--git` 选项）
- **容器化部署**: 使用 `setup-podman.sh` 和 `run-openclaw-podman.sh`

### 2. 自动化维护

- 配置 `setup-auth-system.sh` 以确保认证状态
- 使用 `restart-mac.sh` 进行定期更新和维护
- 监控系统日志以快速定位问题

### 3. 开发工作流程

- 使用 `build-and-run-mac.sh` 进行快速开发测试
- 运行 `pnpm test` 进行全面测试
- 使用 `pnpm build` 构建生产版本

### 4. 故障排除

- 使用 `--verbose` 选项获取详细错误信息
- 检查系统日志（macOS 上使用 `clawlog.sh`）
- 重新运行安装脚本通常可以解决大部分问题

## 总结

OpenClaw 提供了一个全面且强大的脚本生态系统，简化了从安装到日常管理的整个过程。这些脚本不仅功能强大，而且经过精心设计，具有良好的错误处理、用户友好的界面和跨平台兼容性。无论您是开发者、运维人员还是普通用户，都能找到适合您需求的工具和方法。
