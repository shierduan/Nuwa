# 女娲项目管理脚本

基于参考项目OpenClaw的脚本设计，为女娲项目创建的一套完整管理脚本系统。

## 脚本目录结构

```
management-scripts/
├── scripts/
│   ├── install.sh          # Linux/macOS 安装脚本
│   ├── install.ps1         # Windows 安装脚本
│   ├── start.sh            # Linux/macOS 启动脚本
│   ├── start.bat           # Windows 启动脚本
│   ├── stop.sh             # Linux/macOS 停止脚本
│   ├── stop.bat            # Windows 停止脚本
│   ├── restart.sh          # Linux/macOS 重启脚本
│   ├── restart.bat         # Windows 重启脚本
│   ├── status.sh           # Linux/macOS 状态检查脚本
│   ├── status.bat          # Windows 状态检查脚本
│   ├── health.sh           # Linux/macOS 健康检查脚本
│   ├── health.bat          # Windows 健康检查脚本
│   ├── monitor.sh          # Linux/macOS 监控脚本
│   ├── monitor.bat         # Windows 监控脚本
│   ├── dev.sh              # Linux/macOS 开发模式脚本
│   ├── dev.bat             # Windows 开发模式脚本
│   ├── test.sh             # Linux/macOS 测试脚本
│   ├── test.bat            # Windows 测试脚本
│   └── nuwactl.py          # 主管理工具
├── scripts-design.md       # 脚本设计文档
└── README.md               # 本说明文件
```

## 核心功能

### 1. 安装管理
- **install.sh/install.ps1**: 自动安装女娲项目，支持多种安装方式
- 自动检测系统环境和依赖
- 智能错误处理和重试机制

### 2. 服务管理
- **start.sh/start.bat**: 启动女娲服务
- **stop.sh/stop.bat**: 停止女娲服务
- **restart.sh/restart.bat**: 重启女娲服务
- **status.sh/status.bat**: 查看服务状态
- **health.sh/health.bat**: 健康检查

### 3. 配置管理
- **nuwactl.py config**: 配置管理功能
  - `nuwactl.py config list`: 查看配置
  - `nuwactl.py config set <key> <value>`: 修改配置项
  - `nuwactl.py config backup`: 备份配置
  - `nuwactl.py config restore <backup_file>`: 恢复配置

### 4. 监控管理
- **monitor.sh/monitor.bat**: 监控服务状态
  - `monitor.sh start`: 启动监控
  - `monitor.sh stop`: 停止监控
  - `monitor.sh status`: 查看监控状态
  - `monitor.sh check`: 手动检查服务状态

### 5. 开发辅助
- **dev.sh/dev.bat**: 开发模式启动
- **test.sh/test.bat**: 运行测试套件

### 6. 主管理工具
- **nuwactl.py**: 统一管理接口
  - 支持所有管理功能
  - 提供详细的命令行帮助
  - 跨平台支持

## 使用方法

### 安装
```bash
# Linux/macOS
curl -fsSL https://nuwa.ai/install.sh | bash

# Windows
powershell -ExecutionPolicy Bypass -Command "iwr -useb https://nuwa.ai/install.ps1 | iex"
```

### 服务管理
```bash
# 启动服务
./scripts/start.sh

# 停止服务
./scripts/stop.sh

# 查看状态
./scripts/status.sh

# 健康检查
./scripts/health.sh
```

### 配置管理
```bash
# 查看配置
python scripts/nuwactl.py config list

# 修改配置
python scripts/nuwactl.py config set llm_base_url "https://api.openai.com/v1"

# 备份配置
python scripts/nuwactl.py config backup

# 恢复配置
python scripts/nuwactl.py config restore config_backup_20260305_120000.yaml
```

### 监控管理
```bash
# 启动监控
./scripts/monitor.sh start

# 停止监控
./scripts/monitor.sh stop

# 查看监控状态
./scripts/monitor.sh status

# 手动检查服务状态
./scripts/monitor.sh check
```

### 开发辅助
```bash
# 开发模式启动
./scripts/dev.sh

# 开发模式启动（指定端口和主机）
./scripts/dev.sh -p 8080 -h 0.0.0.0

# 运行所有测试
./scripts/test.sh

# 运行特定测试
./scripts/test.sh tests/unit/test_kernels.py
```

### 主管理工具
```bash
# 查看帮助
python scripts/nuwactl.py --help

# 启动服务（后台运行）
python scripts/nuwactl.py start --daemon

# 查看服务状态
python scripts/nuwactl.py status

# 查看日志
python scripts/nuwactl.py logs

# 健康检查
python scripts/nuwactl.py health

# 部署新版本
python scripts/nuwactl.py deploy --daemon

# 开发模式启动
python scripts/nuwactl.py dev

# 运行测试
python scripts/nuwactl.py test
```

## 脚本特点

1. **跨平台支持**: 同时支持Linux/macOS和Windows系统
2. **智能错误处理**: 提供详细的错误信息和自动重试机制
3. **美观的用户界面**: 彩色输出，友好的交互体验
4. **完整的功能集**: 从安装到监控的全流程管理
5. **可扩展性**: 模块化设计，易于添加新功能
6. **安全性**: 包含权限检查和安全验证

## 注意事项

1. 所有脚本需要在项目根目录下运行
2. Windows系统需要以管理员权限运行PowerShell脚本
3. Linux/macOS系统需要给脚本添加执行权限：`chmod +x scripts/*.sh`
4. 监控脚本会在后台运行，定期检查服务状态
5. 配置修改后需要重启服务才能生效

## 故障排除

1. **安装失败**: 检查Python和Git是否正确安装
2. **服务启动失败**: 检查端口是否被占用，查看日志文件
3. **监控未运行**: 检查监控进程是否存在，查看监控日志
4. **配置不生效**: 确保配置文件格式正确，重启服务
5. **测试失败**: 检查测试依赖是否安装，查看测试报告

## 总结

本管理脚本系统参考了OpenClaw项目的优秀实践，为女娲项目提供了一套完整、高效、易用的管理工具。这些脚本将大大简化女娲项目的安装、部署和维护过程，提高开发效率和系统稳定性。