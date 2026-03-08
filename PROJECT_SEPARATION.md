# 项目分离说明

## 📋 分离概述

**日期**: 2026-03-08  
**原因**: Live2D 和 Web 前端与女娲核心项目（AI Agent 框架）的核心概念背离，需要独立成额外项目

---

## 🗂️ 项目结构

### 1️⃣ 女娲核心项目 (主目录)

**路径**: `c:/Users/Administrator/Documents/新建文件夹/女娲/`

**定位**: AI Agent 框架 - 基于控制论与向量动力学的数字生命原型

**核心组件**:
```
女娲/
├── nuwa_core/              # 核心 Python 代码
│   ├── adaptive_pid.py     # 自适应 PID 控制
│   ├── causality_judge.py  # 因果判断模块
│   ├── momentum_tracker.py # 动量追踪器
│   ├── state_machine.py    # 状态机
│   ├── model_utils.py      # 模型工具
│   ├── engine.py           # 引擎核心
│   └── riemannian_semantic_field.py  # 黎曼几何语义场
├── skills/                 # AI 技能库
├── lib/                    # 库文件
├── libs/                   # 其他库
├── data/                   # 数据文件
├── config/                 # 配置文件
├── main_async.py          # 主入口
├── server_async.py        # 异步服务器
├── nuwactl.py             # 控制工具
└── tests/                 # 测试用例
```

**技术栈**:
- Python 3.11+
- FastAPI
- PyTorch
- LanceDB (向量数据库)
- Docker

**核心功能**:
- 黎曼几何语义场 (Riemannian Semantic Field)
- 自适应 PID 控制 (Adaptive PID Control)
- 强化学习自我进化 (RL-based Self-Evolution)
- 情感状态空间管理
- 多通道集成 (飞书、微信等)

---

### 2️⃣ 前端与 Live2D 项目 (123 子目录)

**路径**: `c:/Users/Administrator/Documents/新建文件夹/女娲/123/`

**定位**: Live2D 模型显示与用户界面管理

**项目结构**:
```
123/
├── pixi-live2d-display/    # Live2D 显示核心库
│   ├── src/               # TypeScript 源代码
│   ├── core/              # 核心 Live2D 绑定
│   ├── playground/        # 示例
│   └── test/              # 测试
├── frontend-manager/      # 前端管理器
│   ├── backend/          # FastAPI 后端
│   └── frontend/         # React 前端
├── models/               # Live2D 模型文件
│   └── 玳瑁猫 v1_vts/
├── web/                  # Web 界面文件
│   ├── index.html
│   ├── manager.html
│   ├── 启动管理器.html
│   ├── main.js
│   └── style.css
├── package.json          # npm 配置
└── README.md            # 项目文档
```

**技术栈**:
- TypeScript + JavaScript
- React + Vite
- PixiJS + pixi-live2d-display
- Electron (桌面应用)
- Node.js

**核心功能**:
- Live2D 模型渲染与显示
- 用户配置管理界面
- WebSocket 实时通信
- 热重载系统
- 调试控制台

---

## 🔄 迁移内容清单

### 已迁移到 123 的文件/目录:

| 项目 | 原位置 | 新位置 |
|------|--------|--------|
| pixi-live2d-display | `/pixi-live2d-display` | `/123/pixi-live2d-display` |
| frontend-manager | `/frontend-manager` | `/123/frontend-manager` |
| models | `/models` | `/123/models` |
| web | `/web` | `/123/web` |
| package.json | `/package.json` | `/123/package.json` |
| package-lock.json | `/package-lock.json` | `/123/package-lock.json` |
| docker-compose.yml | (复制) | `/123/docker-compose.yml` |
| 自检报告.md | (复制) | `/123/自检报告.md` |

### 从原项目删除的内容:

- ❌ `node_modules/` - 已删除（不再需要）
- ❌ `frontend-manager/` - 已迁移
- ❌ `pixi-live2d-display/` - 已迁移
- ❌ `models/` - 已迁移
- ❌ `web/` - 已迁移

### 原项目保留的内容:

- ✅ `nuwa_core/` - 核心 Python 代码
- ✅ `skills/`, `lib/`, `libs/` - AI 技能库
- ✅ `data/` - 数据文件
- ✅ `config/` - 配置文件
- ✅ `main_async.py`, `server_async.py` - Python 后端
- ✅ `tests/` - 测试用例
- ✅ 所有 Python 脚本和工具

---

## 🚀 使用方法

### 启动女娲核心项目:

```bash
cd c:/Users/Administrator/Documents/新建文件夹/女娲

# 安装 Python 依赖
pip install -r requirements.txt

# 启动主程序
python main_async.py

# 或使用控制工具
python nuwactl.py start
```

### 启动前端与 Live2D 项目:

```bash
cd c:/Users/Administrator/Documents/新建文件夹/女娲/123

# 安装 npm 依赖
npm install

# 启动开发环境
npm start

# 或启动管理器
npm run manager

# 构建生产版本
npm run build:win
```

---

## 🔗 项目间通信

两个项目可以通过以下方式集成：

1. **API 调用**: 前端通过 HTTP/WebSocket 调用核心项目的 API
2. **独立运行**: 两个项目可以完全独立运行
3. **Docker 部署**: 使用 docker-compose 同时部署两个服务

---

## 📝 后续工作

### 原项目 (女娲核心):
- [ ] 更新 requirements.txt，移除前端相关依赖
- [ ] 更新 README.md，说明项目分离
- [ ] 清理 .gitignore 中的前端条目
- [ ] 创建独立的 Python 包配置

### 123 项目 (前端与 Live2D):
- [x] 创建独立的 README.md
- [x] 更新 package.json 配置
- [ ] 安装 node_modules (`npm install`)
- [ ] 测试 Live2D 显示功能
- [ ] 更新前端 API 端点配置

---

## 📊 分离优势

### 对女娲核心项目:
- ✅ 更清晰的项目定位（纯 AI 框架）
- ✅ 减少不必要的依赖（npm/node_modules）
- ✅ 简化安装和部署流程
- ✅ 更专注于核心算法开发

### 对前端项目:
- ✅ 独立版本号
- ✅ 独立发布周期
- ✅ 可以更灵活地更新前端技术栈
- ✅ 可以作为独立产品使用

---

## 📞 联系与维护

如有问题，请参考各自项目的 README.md 文档。

**分离完成时间**: 2026-03-08
