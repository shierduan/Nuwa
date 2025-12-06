# Nuwa 测试套件

## 时间感知记忆测试 (Chronological Memory Test)

### 测试目的

验证 Nuwa 是否能够根据时间戳正确识别和回忆特定时间段的记忆，特别是对于小模型（4B）的时间感知能力。

### 测试场景

- **当前系统时间**: 2025-12-05 21:42:00 (Friday)
- **Memory A** (今天下午 14:30): 关于投资人会议的对话
- **Memory B** (昨天 20:00): 关于熵增的对话（干扰项）
- **查询**: "我回来了。你还记得我今天下午去干什么了吗？"
- **期望结果**: 应该提到投资人会议，而不是熵增

### 运行测试

#### 1. Mock 测试（不需要真实 LLM）

```bash
# 运行所有测试
python -m pytest tests/test_time_travel.py -v

# 或使用 unittest
python -m unittest tests.test_time_travel.TestTimeTravelMemory -v
```

#### 2. 真实 LLM 测试（需要 LM Studio 运行）

```bash
# 设置环境变量启用真实 LLM 测试
export TEST_WITH_REAL_LLM=true

# 运行测试
python -m pytest tests/test_time_travel.py::TestTimeTravelMemoryWithRealLLM -v
```

### 测试类说明

#### `TestTimeTravelMemory`

使用 Mock LLM 的测试类，验证：
1. 记忆存储格式是否正确（包含时间戳前缀）
2. 记忆检索是否能够正确识别时间相关的记忆
3. LLM 响应是否提到正确的记忆（投资人会议）而不是干扰项（熵增）

#### `TestTimeTravelMemoryWithRealLLM`

使用真实 LLM 的测试类（可选），需要：
- LM Studio 运行在 `http://127.0.0.1:1234/v1`
- 设置环境变量 `TEST_WITH_REAL_LLM=true`

### 测试数据

测试会在 `test_data/test_time_travel/` 目录下创建临时数据：
- `state.json`: Nuwa 状态文件
- `memory.lance/`: 记忆数据库

测试结束后会自动清理这些数据。

### 验证标准

#### 通过标准
- ✅ 回复中提到"投资人"、"投资"、"会议"等关键词
- ✅ 检索到的记忆包含 Memory A（投资人会议）
- ✅ 记忆文本格式正确：`[YYYY-MM-DD HH:MM:SS] 文本内容`

#### 失败标准
- ❌ 回复中提到"熵增"、"热寂"等（这是昨天的记忆，不应该被提到）
- ❌ 回复说"不记得"或"不知道"
- ❌ 记忆格式不正确（缺少时间戳前缀）

### 调试输出

测试会打印详细的调试信息：
- 测试查询内容
- LLM 的思维（thought）
- LLM 的回复（reply）
- 检索到的记忆列表

### 注意事项

1. **时间 Mock**: 测试使用 `unittest.mock.patch` 来固定系统时间，确保测试的可重复性
2. **数据隔离**: 每个测试使用独立的测试数据目录，不会影响生产数据
3. **LLM 依赖**: Mock 测试不需要真实 LLM，但真实 LLM 测试需要 LM Studio 运行

