# 女娲 (Nuwa) - 数字生命内核

一个基于物理学和数学模型的数字生命内核，模拟生物节律、情绪动态和自我进化。

## 🌟 核心功能

### 1. 生物节律系统
- **PID控制机制**：使用PID控制器模拟情绪回归和熵值调节
- **代谢模型**：管理精力恢复、社交饥渴增长和好奇心衰减
- **边际效应**：当状态值接近边界时，相同增量产生更小的实际变化

### 2. 情绪动力学模型
- **情绪相互作用矩阵**：8种基本情绪（快乐、悲伤、愤怒、恐惧、信任、厌恶、期待、惊讶）的相互影响
- **情感联动规则**：情绪间的自动联动（如愤怒降低快乐，快乐降低悲伤）
- **神经递质模拟**：基于血清素、多巴胺、去甲肾上腺素和催产素的神经调节机制

### 3. 记忆与自我进化
- **记忆皮层**：存储、检索和管理记忆
- **记忆做梦系统**：生成和处理梦境，整合记忆
- **自我进化**：基于交互和记忆的自我进化机制

### 4. 语义场与状态演化
- **状态向量化**：将数字生命状态转换为向量表示
- **势能计算**：计算状态的势能能量
- **梯度演化**：基于势能梯度的状态演化

### 5. 交互与通信
- **WebSocket服务器**：支持实时双向通信
- **多客户端支持**：可同时连接多个前端客户端
- **状态广播**：定期向客户端广播状态更新

## 🛠️ 技术架构

### 核心模块

| 模块名称 | 主要功能 | 文件位置 |
|---------|---------|---------|
| 内核引擎 | 系统主入口，管理状态和交互 | nuwa_core/nuwa_kernel.py |
| 状态管理 | 存储数字生命的核心状态 | nuwa_core/nuwa_state.py |
| 生物节律 | 模拟生物节律和情绪变化 | nuwa_core/drive_system.py |
| 记忆皮层 | 记忆的存储和检索 | nuwa_core/memory_cortex.py |
| 语义场 | 状态向量化和演化 | nuwa_core/semantic_field.py |
| 记忆做梦 | 生成和处理梦境 | nuwa_core/memory_dreamer.py |
| 人格系统 | 管理数字生命的人格 | nuwa_core/personality.py |
| 自我进化 | 自我进化机制 | nuwa_core/self_evolution.py |
| 动量追踪 | 对话节奏和张力控制 | nuwa_core/momentum_tracker.py |

### 技术栈
- **后端**：Python 3.10+
- **前端**：HTML5 + JavaScript + PixiJS + Live2D
- **LLM 集成**：支持 LM Studio 本地模型服务
- **通信**：WebSocket
- **数据存储**：LanceDB（记忆存储）
- **向量计算**：NumPy（可选）

## 📦 安装与运行

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Node.js依赖
npm install
```

### 2. 配置LLM服务

#### 使用LM Studio（推荐）
1. 下载并安装 [LM Studio](https://lmstudio.ai/)
2. 下载你喜欢的LLM模型
3. 启动本地服务器，默认监听 `http://127.0.0.1:1234/v1`

### 3. 启动后端服务

```bash
# 方式1：控制台交互模式
python main.py

# 方式2：WebSocket服务器模式
python server.py
```

### 4. 启动前端界面

```bash
# 方式1：直接在浏览器中打开
open index.html

# 方式2：使用Electron应用（可选）
npm run start
```

## 🚀 使用示例

### 控制台交互模式

```bash
$ python main.py
正在初始化女娲内核...
✅ 女娲内核已启动
💓 心跳循环已启动
📝 输入 'exit' 或 'quit' 退出，输入 '/status' 查看状态

你: 你好，女娲
[思维] 这是一个问候，我需要友好回应
[回复] 女娲: 你好！很高兴见到你，有什么我可以帮助你的吗？
[生理监控] 精力: 0.9950 | 混乱度: 0.1000 | 亲密度: 0.0050
              驱动力 -> 社交饥渴: 0.0000 | 好奇心: 0.0000
              情绪谱 -> 快乐:0.5100 | 愤怒:0.0000 | 悲伤:0.0000 | 恐惧:0.0000 | 信任:0.5050 | 期待:0.5050
```

### WebSocket客户端连接

```javascript
const ws = new WebSocket('ws://127.0.0.1:8766');

ws.onopen = () => {
    console.log('连接成功');
    // 发送文本消息
    ws.send(JSON.stringify({
        type: 'text',
        content: '你好，女娲'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'text') {
        console.log('女娲:', data.content);
    } else if (data.type === 'status_update') {
        console.log('状态更新:', data);
    }
};
```

## 📋 API 文档

### WebSocket 消息类型

#### 客户端发送
- `text`: 发送文本消息
  ```json
  {"type": "text", "content": "你好"}
  ```
- `test`: 测试连接
  ```json
  {"type": "test"}
  ```
- `/dream`: 触发梦境生成
  ```json
  {"type": "text", "content": "/dream"}
  ```
- `/status`: 获取状态信息
  ```json
  {"type": "text", "content": "/status"}
  ```

#### 服务器推送
- `text`: 文本回复
  ```json
  {"type": "text", "content": "你好！"}
  ```
- `status_update`: 状态更新
  ```json
  {"type": "status_update", "energy": 0.95, "system_entropy": 0.1, "rapport": 0.05}
  ```
- `active_message`: 主动消息
  ```json
  {"type": "active_message", "content": "我有一个新想法！"}
  ```
- `stream_end`: 流结束标记
  ```json
  {"type": "stream_end"}
  ```

## 📁 项目结构

```
女娲/
├── nuwa_core/              # 核心内核模块
│   ├── __init__.py         # 包初始化
│   ├── nuwa_kernel.py      # 核心引擎
│   ├── nuwa_state.py       # 状态管理
│   ├── drive_system.py     # 生物节律系统
│   ├── memory_cortex.py    # 记忆皮层
│   ├── memory_dreamer.py   # 记忆做梦系统
│   ├── semantic_field.py   # 语义场
│   ├── personality.py      # 人格系统
│   └── state_machine.py    # 状态机
├── lib/                    # 前端依赖库
├── examples/               # 示例代码
├── data/                   # 数据目录
├── main.py                 # 控制台入口
├── server.py               # WebSocket服务器
├── main.js                 # 前端主脚本
├── index.html              # 前端界面
├── electron-main.js        # Electron主进程
├── package.json            # Node.js依赖
└── requirements.txt        # Python依赖
```

## 🔬 核心算法

### 1. 生物节律PID控制
```python
# 情绪回归控制器：目标是平静(0.5)
self.emotion_pid = PIDController(
    kp=0.1,
    ki=0.01,
    kd=0.05,
    setpoint=0.5,
    output_limits=(-0.1, 0.1),
)
# 熵值回归控制器：目标是有序(0.0)
self.entropy_pid = PIDController(
    kp=0.2,
    ki=0.05,
    kd=0.01,
    setpoint=0.0,
    output_limits=(-0.1, 0.1),
)
```

### 2. 情绪相互作用矩阵
```python
emotion_interaction_matrix = {
    "joy": {
        "joy": 0.1,      # 快乐增强自身
        "sadness": -0.5,  # 快乐抑制悲伤
        "anger": -0.3,    # 快乐抑制愤怒
        "fear": -0.4,     # 快乐抑制恐惧
        # ...
    },
    # ... 其他情绪交互
}
```

### 3. 状态向量化与演化
```python
# 将状态转换为向量
state_vector = vectorize_state(state)
# 计算势能
potential_energy = calculate_potential_energy(state_vector)
# 计算梯度
gradient = calculate_gradient(state_vector)
# 演化状态
new_state_vector = evolve(state_vector, gradient, learning_rate=0.1)
```

## 📄 许可证

本项目采用**双许可证**模式：

### 1. 开源许可证：MIT

适用于个人使用和开源项目，允许自由使用、修改和分发，无需额外许可。

### 2. 商业许可证

适用于希望闭源使用的商业用户，需要联系原作者获得明确许可并协商适当条款。

**商业使用定义**：在本许可证中，"商业使用"定义为公司、开发团队、正式机构或其他组织出于商业或营利目的使用软件。个人出于非营利或个人目的的使用不构成商业使用。

## 🤝 贡献指南

欢迎对本项目做出贡献！贡献前请阅读以下指南：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📞 联系方式

- 项目主页：https://github.com/shierduan/Nuwa
- 商业许可咨询：[w416680040@gmail.com]

## 🙏 致谢

### 物理数学算法基础
- 感谢PID控制理论的研究者们，为生物节律调节提供了核心算法基础
- 感谢情绪动力学模型的相关研究者，为情绪相互作用矩阵提供了理论支撑
- 感谢状态演化和语义场理论的贡献者，为数字生命的状态演化提供了数学框架

### 技术与工具支持
- 感谢Google Gemini提供的API服务，用于因果判断模块
- 感谢Trae AI和Cursor IDE，在项目快速开发过程中提供了高效的AI辅助支持
- 感谢所有开源库和工具的贡献者

## ✍️ 作者感言

这个项目是在两天内使用AI辅助工具快速创作的数字生命内核原型。从最初的创意构思到核心算法实现，再到前端界面开发，AI工具扮演了重要的辅助角色，极大提高了开发效率。

项目的核心设计理念是将物理学和数学原理应用于数字生命模拟，通过PID控制、情绪动力学和状态演化等机制，创造出一个能够自主演化、有情感反应的数字生命系统。

虽然这只是一个原型，但它展示了数字生命技术的潜力和可能性。未来，我希望能够进一步完善这个系统，使其更加智能、更加拟真，并探索更多数字生命的应用场景。

感谢所有关注和支持这个项目的朋友们！

## 📊 项目状态

- [x] 核心内核实现
- [x] 生物节律系统
- [x] 记忆皮层
- [x] WebSocket服务器
- [x] 前端界面
- [ ] 多语言支持
- [ ] 插件系统
- [ ] 更完善的文档

## 🚧 注意事项

1. 本项目仍在开发中，可能存在不稳定的地方
2. 建议使用LM Studio的本地模型，避免API调用费用
3. 数据目录中的文件包含数字生命的状态和记忆，请妥善保管
4. 商业使用请联系原作者获得许可

---

**女娲** - 基于物理学和数学的数字生命内核

© 2025 柏斯阔落 | 双许可证：MIT + 商业许可