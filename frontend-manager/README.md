# 女娲前端管理器

异步配置管理 + WebSocket实时通信 + 热重载系统

## 🎯 核心特性

- ✅ **全异步架构** - FastAPI + asyncio，高并发安全
- ✅ **实时通信** - WebSocket双向推送，配置变更即时同步
- ✅ **热重载** - 文件监听自动应用变更，无需重启
- ✅ **事务安全** - 原子化更新 + 回滚机制 + 历史记录
- ✅ **终端调试** - Rich CLI工具，实时监控和操作
- ✅ **前端管理** - React + TypeScript + Zustand，现代化UI

## 📁 项目结构

```
frontend-manager/
├── backend/                    # FastAPI后端
│   ├── config/                 # 配置管理模块
│   │   ├── models.py          # Pydantic模型
│   │   ├── manager.py         # 异步配置管理器
│   │   ├── hot_reload.py      # 热重载系统
│   │   └── websocket.py       # WebSocket管理器
│   ├── api/routes/            # API路由
│   │   └── config.py          # 配置API
│   ├── core/                  # 核心工具
│   │   ├── logger.py          # 结构化日志
│   │   └── cli.py             # CLI工具
│   ├── utils/                 # 工具模块
│   ├── main.py                # 主应用入口
│   ├── requirements.txt       # Python依赖
│   └── Dockerfile             # 容器配置
│
├── frontend/                  # React前端
│   ├── src/
│   │   ├── components/        # React组件
│   │   │   ├── ConfigPanel.tsx
│   │   │   ├── ConfigInput.tsx
│   │   │   ├── DebugConsole.tsx
│   │   │   └── NotificationContainer.tsx
│   │   ├── hooks/             # React Hooks
│   │   │   └── useWebSocket.ts
│   │   ├── store/             # Zustand状态管理
│   │   │   └── config.ts
│   │   ├── types/             # TypeScript类型
│   │   │   └── config.ts
│   │   ├── utils/             # 工具函数
│   │   │   └── api.ts
│   │   ├── App.tsx            # 主组件
│   │   ├── main.tsx           # 入口
│   │   └── index.css          # 样式
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker-compose.yml         # Docker编排
├── nginx.conf                 # Nginx配置
└── README.md                  # 说明文档
```

## 🚀 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端开发服务器

```bash
npm run dev
```

### 5. 使用Docker（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 仅启动后端
docker-compose up backend -d

# 查看日志
docker-compose logs -f
```

## 🛠️ CLI工具使用

### 查看配置

```bash
cd backend
python -m core.cli view
python -m core.cli view llm          # 查看指定分组
```

### 修改配置

```bash
python -m core.cli set llm_temperature 0.8
python -m core.cli set enable_debug_mode true
```

### 实时监控

```bash
python -m core.cli watch
```

### 健康检查

```bash
python -m core.cli health
```

### 查看历史

```bash
python -m core.cli history --limit 10
```

### 回滚配置

```bash
python -m core.cli rollback abc123def
```

## 🌐 API接口

### REST API

- `GET /api/config/` - 获取当前配置
- `POST /api/config/` - 更新配置
- `GET /api/config/history` - 获取历史记录
- `POST /api/config/rollback/{id}` - 回滚配置
- `GET /api/config/stats` - 系统统计
- `POST /api/config/clear-cache` - 清空缓存
- `GET /health` - 健康检查
- `GET /docs` - API文档（Swagger UI）

### WebSocket

- `ws://localhost:8000/api/config/ws/{client_id}` - WebSocket连接

消息类型：
- `config_updated` - 配置更新
- `hot_reload` - 热重载通知
- `config_rollback` - 回滚通知
- `heartbeat` - 心跳

## 🔧 配置文件

配置文件位于：`backend/config/config.yaml`

默认会自动从 `backend/config/default.yaml` 创建。

### 配置项示例

```yaml
# LLM配置
llm_base_url: "http://127.0.0.1:1234/v1"
llm_api_key: "lm-studio"
llm_temperature: 0.7

# 生物节律
energy_recovery_rate: 0.0003
energy_critical_threshold: 0.05

# 缓存
cache_enabled: true
cache_ttl: 300

# 系统
enable_debug_mode: false
log_level: "INFO"
```

## 📊 监控和日志

### 日志文件

- 后端日志：`backend/logs/frontend-manager.log`
- 格式：JSON结构化日志

### 监控指标

- 配置管理器状态
- WebSocket连接数
- 内存使用
- 运行时间
- 事务统计

## 🔐 安全考虑

1. **CORS配置** - 限制前端域名
2. **配置验证** - Pydantic类型验证
3. **事务安全** - 原子化更新
4. **备份机制** - 自动备份配置文件
5. **回滚支持** - 历史记录回滚

## 🐛 故障排除

### WebSocket连接失败

检查：
- 后端服务是否运行
- 端口8000是否开放
- CORS配置是否正确

### 热重载不工作

检查：
- 配置文件是否存在
- 文件权限
- watchdog是否安装

### 配置更新失败

检查：
- 配置项是否存在
- 值类型是否正确
- Pydantic验证错误

## 📈 性能优化

1. **异步IO** - 所有文件操作异步化
2. **并发安全** - 使用asyncio.Lock
3. **缓存机制** - 配置和响应缓存
4. **队列处理** - WebSocket消息队列
5. **防抖处理** - 文件监听防抖

## 🎨 前端功能

### 配置管理面板
- 分组展示配置项
- 智能输入控件（根据类型）
- 实时验证
- 保存/重置按钮

### 调试控制台
- WebSocket消息监控
- 系统状态查看
- 实时统计
- 缓存操作

### 通知系统
- 操作反馈
- 错误提示
- 热重载通知
- 自动消失

### 主题切换
- 亮色/暗色模式
- 本地存储持久化

## 📝 开发计划

- [ ] 配置导入/导出
- [ ] 配置模板
- [ ] 批量操作
- [ ] 权限管理
- [ ] 操作审计
- [ ] 性能监控图表

## 📄 许可证

MIT License

---

**开发时间**: 2025-12-20  
**版本**: 1.0.0
