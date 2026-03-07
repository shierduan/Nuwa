# OpenClaw Skills 机制完整实现提取

## 项目概述

本文件夹包含 OpenClaw 项目中 Skills 机制的完整实现代码。Skills 是 OpenClaw 系统的核心组件之一，提供了可扩展的功能模块，允许用户和系统通过自然语言或命令接口与各种外部服务和工具进行交互。

## 核心架构

### 1. Skills 类型定义 (types.ts)

Skills 机制的基础是类型定义，位于 `skills/types.ts` 文件中。主要定义包括：

- **SkillInstallSpec**: 技能安装规范，支持多种安装方式（brew、node、go、uv、download）
- **OpenClawSkillMetadata**: 技能元数据，包含技能的特性、依赖、安装信息等
- **SkillInvocationPolicy**: 技能调用策略，控制技能的可访问性
- **SkillEntry**: 技能条目，包含技能实例、前导内容和元数据
- **SkillSnapshot**: 技能快照，用于在运行时保存和恢复技能状态

### 2. Skills 工作区管理 (workspace.ts)

`skills/workspace.ts` 是 Skills 机制的核心管理文件，提供以下功能：

- **技能加载**: `loadSkillEntries` 函数从多个位置加载技能（捆绑技能、管理技能、个人技能、项目技能、工作区技能）
- **技能过滤**: `filterSkillEntries` 根据配置和环境过滤符合条件的技能
- **技能快照**: `buildWorkspaceSkillSnapshot` 创建技能状态快照
- **技能同步**: `syncSkillsToWorkspace` 实现技能在不同工作区之间的同步
- **命令规范**: `buildWorkspaceSkillCommandSpecs` 为用户可调用的技能生成命令规范

### 3. Skills 配置管理 (config.ts)

`skills/config.ts` 负责处理技能配置和可用性判断：

- **配置解析**: 解析技能的配置文件
- **平台检测**: 判断技能在当前平台的可用性
- **依赖检查**: 验证技能所需的二进制文件和环境变量是否存在
- **权限控制**: 管理技能的允许列表和禁止列表

### 4. Skills 环境管理 (env-overrides.ts)

`skills/env-overrides.ts` 处理技能的环境变量覆盖：

- **环境变量设置**: `applySkillEnvOverrides` 为技能运行设置特定的环境变量
- **快照恢复**: `applySkillEnvOverridesFromSnapshot` 从技能快照中恢复环境变量

### 5. Skills 过滤机制 (filter.ts)

`skills/filter.ts` 实现技能过滤逻辑：

- **名称匹配**: 根据技能名称进行模糊匹配
- **标签过滤**: 根据技能标签筛选
- **复杂查询**: 支持AND、OR等逻辑运算符的复杂查询

### 6. Skills 安装管理 (skills-install.ts)

`skills-install.ts` 及其相关文件处理技能的安装过程：

- **多平台支持**: 支持多种安装方式（npm、brew、go等）
- **依赖管理**: 自动解析和安装技能依赖
- **安装缓存**: 管理技能安装过程中的缓存
- **错误处理**: 处理安装过程中的错误和回退机制

### 7. Skills 安全扫描 (skill-scanner.ts)

`security/skill-scanner.ts` 提供技能的安全扫描功能：

- **代码审计**: 扫描技能代码中的安全隐患
- **权限检查**: 检查技能请求的权限是否合理
- **依赖分析**: 分析技能依赖包的安全状态

### 8. Skills 运行时 (pi-embedded-runner/skills-runtime.ts)

`pi-embedded-runner/skills-runtime.ts` 负责在嵌入式环境中管理技能的执行：

- **技能解析**: 从技能快照中解析技能条目
- **执行环境**: 为技能执行创建安全的环境
- **资源管理**: 管理技能执行所需的资源

## 文件结构

```
skills-extract/
├── security/
│   ├── skill-scanner.test.ts
│   └── skill-scanner.ts
├── skills/
│   ├── bundled-context.ts
│   ├── bundled-dir.test.ts
│   ├── bundled-dir.ts
│   ├── config.ts
│   ├── env-overrides.ts
│   ├── filter.test.ts
│   ├── filter.ts
│   ├── frontmatter.test.ts
│   ├── frontmatter.ts
│   ├── plugin-skills.test.ts
│   ├── plugin-skills.ts
│   ├── refresh.test.ts
│   ├── refresh.ts
│   ├── serialize.ts
│   ├── tools-dir.ts
│   ├── types.ts
│   └── workspace.ts
├── pi-embedded-runner/
│   ├── skills-runtime.integration.test.ts
│   ├── skills-runtime.test.ts
│   └── skills-runtime.ts
├── sandbox-skills.test.ts
├── skills-install-download.ts
├── skills-install-extract.ts
├── skills-install-fallback.test.ts
├── skills-install-output.ts
├── skills-install-tar-verbose.ts
├── skills-install.download-test-utils.ts
├── skills-install.download.test.ts
├── skills-install.test-mocks.ts
├── skills-install.test.ts
├── skills-install.ts
├── skills-status.test.ts
├── skills-status.ts
├── skills.agents-skills-directory.test.ts
├── skills.build-workspace-skills-prompt.applies-bundled-allowlist-without-affecting-workspace-skills.test.ts
├── skills.build-workspace-skills-prompt.prefers-workspace-skills-managed-skills.test.ts
├── skills.build-workspace-skills-prompt.syncs-merged-skills-into-target-workspace.test.ts
├── skills.buildworkspaceskillsnapshot.test.ts
├── skills.buildworkspaceskillstatus.test.ts
├── skills.compact-skill-paths.test.ts
├── skills.e2e-test-helpers.test.ts
├── skills.e2e-test-helpers.ts
├── skills.loadworkspaceskillentries.test.ts
├── skills.resolveskillspromptforrun.test.ts
├── skills.sherpa-onnx-tts-bin.test.ts
├── skills.summarize-skill-description.test.ts
├── skills.test-helpers.ts
├── skills.test.ts
└── skills.ts
```

## 功能特性

### 1. 多源技能加载

OpenClaw 支持从多个位置加载技能：

1. **捆绑技能**: 与 OpenClaw 一起分发的核心技能
2. **管理技能**: 系统级管理的技能库
3. **个人技能**: 用户个人配置的技能
4. **项目技能**: 当前项目特定的技能
5. **插件技能**: 通过插件系统提供的技能
6. **工作区技能**: 直接在工作区目录下的技能

### 2. 智能过滤和匹配

- 支持按技能名称、标签、描述进行搜索
- 提供模糊匹配和精确匹配
- 支持复杂查询条件（AND、OR逻辑）
- 根据当前平台和环境自动过滤不可用的技能

### 3. 安全沙箱执行

- 技能执行在安全沙箱中运行
- 严格控制技能的资源访问权限
- 提供技能的安全扫描和审计功能
- 支持技能执行的实时监控

### 4. 自动依赖管理

- 自动解析技能的依赖关系
- 支持多种包管理系统（npm、brew、go等）
- 处理依赖冲突和版本管理
- 提供依赖安装的错误恢复机制

## 使用方法

### 技能开发

创建技能需要：

1. 创建技能目录
2. 在目录中添加 `SKILL.md` 文件，包含技能描述和元数据
3. 实现技能的具体功能
4. （可选）提供技能的安装和配置说明

### 技能使用

- 通过自然语言与技能交互
- 使用 `/skill-name` 命令直接调用技能
- 技能可通过 OpenClaw 系统进行配置和管理

## 技术栈

- **TypeScript**: 主要开发语言
- **Node.js**: 运行时环境
- **Vitest**: 测试框架
- **ESLint/OxLint**: 代码检查工具
- **OxFmt**: 代码格式化工具

## 测试覆盖

代码库包含全面的测试覆盖：

- 单元测试：覆盖核心功能的各个方面
- 集成测试：测试技能与其他系统组件的交互
- 端到端测试：测试完整的技能生命周期

## 总结

OpenClaw Skills 机制提供了一个强大而灵活的扩展系统，允许用户和开发人员通过编写简单的技能模块来扩展 OpenClaw 的功能。技能可以用多种语言编写，支持多种安装方式，并在安全的沙箱环境中执行，确保系统的稳定性和安全性。
