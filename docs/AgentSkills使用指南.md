# AgentSkills 使用指南

## 1. 概述

AgentSkills 是女娲系统中的技能扩展机制，允许开发者创建自定义技能，实现特定功能的自动处理。本指南将详细说明如何开发和使用 AgentSkills。

## 2. AgentSkills 设计理念

AgentSkills 的核心设计理念是：

- **模块化**：每个技能独立实现，便于维护和扩展
- **标准化**：统一的接口和执行流程
- **上下文感知**：技能执行时考虑情绪状态和记忆上下文
- **结果反馈**：技能执行结果影响情绪和记忆
- **自我进化**：根据技能执行成功与否调整系统参数

## 3. 技能调用流程

1. **用户输入**：用户发送请求（如"帮我查一下北京天气"）
2. **状态更新**：更新系统状态和时间戳
3. **情绪分析**：提取当前情绪状态
4. **记忆检索**：获取相关记忆上下文
5. **技能匹配**：根据用户意图匹配合适的技能
6. **技能执行**：执行匹配的技能，传入情绪状态和记忆上下文
7. **结果处理**：
   - 情绪更新：根据技能执行结果调整情绪
   - 记忆写入：保存技能执行结果到记忆系统
   - 自我进化奖励：根据技能执行成功与否给予奖励
8. **生成回复**：根据技能执行结果生成用户回复

## 4. 创建自定义 AgentSkill

### 4.1 继承 AgentSkill 基类

创建一个新的技能文件，继承 `AgentSkill` 基类并实现必要的方法：

```python
from nuwa_core.skills.agent_skills import AgentSkill, SkillResult

class MyCustomSkill(AgentSkill):
    def __init__(self):
        super().__init__("MyCustomSkill", "我的自定义技能")
    
    def can_handle(self, query: str) -> bool:
        # 判断是否能处理该查询
        return "关键词" in query
    
    async def execute(self, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        # 执行技能逻辑
        # 构建结果
        return SkillResult(
            success=True,
            result={"key": "value"},
            emotion_update={"joy": 0.1},
            memory_update="执行了我的自定义技能",
            message="操作成功"
        ).to_dict()
```

### 4.2 实现 can_handle 方法

`can_handle` 方法用于判断技能是否能处理给定的查询。可以使用正则表达式或关键词匹配：

```python
def can_handle(self, query: str) -> bool:
    patterns = [r'.*关键词.*', r'.*相关词.*']
    query = query.lower()
    for pattern in patterns:
        if re.match(pattern, query):
            return True
    return False
```

### 4.3 实现 execute 方法

`execute` 方法是技能的核心，负责执行具体逻辑并返回结果：

- **参数**：
  - `query`：用户查询
  - `emotion_state`：当前情绪状态
  - `memory_context`：记忆上下文

- **返回值**：
  - `success`：执行是否成功
  - `result`：执行结果数据
  - `emotion_update`：情绪更新建议
  - `memory_update`：记忆更新建议
  - `message`：执行消息

## 5. 注册和管理 AgentSkills

### 5.1 在 NuwaKernel 中注册技能

在 `nuwa_core/nuwa_kernel_async.py` 文件的 `_init_agent_skills` 方法中注册技能：

```python
def _init_agent_skills(self):
    """初始化 AgentSkills"""
    # 注册 AgentSkills
    self.agent_skills = [
        WeatherSkill(),
        MyCustomSkill()  # 添加自定义技能
    ]
```

### 5.2 在 workspace.py 中管理技能

在 `nuwa_core/skills/workspace.py` 文件的 `get_agent_skills` 函数中添加技能：

```python
def get_agent_skills() -> List[AgentSkill]:
    """
    获取所有注册的 AgentSkills
    
    Returns:
        AgentSkill 列表
    """
    from .weather_skill import WeatherSkill
    from .my_custom_skill import MyCustomSkill
    
    return [
        WeatherSkill(),
        MyCustomSkill()  # 添加自定义技能
    ]
```

## 6. WeatherSkill 示例

### 6.1 功能说明

WeatherSkill 是一个示例技能，用于查询城市天气信息。它可以：

- 识别天气相关的查询
- 提取城市名称
- 模拟天气数据
- 更新情绪和记忆

### 6.2 使用示例

```python
# 用户输入
result = await kernel.process_input("帮我查一下北京天气")

# 输出
# 回复: 北京今天多云，温度21°C，湿度46%
# 思维: 执行技能 WeatherSkill 成功
# 技能执行结果: {'success': True, 'result': {'temperature': 21, 'condition': '多云', 'humidity': 46}, 'emotion_update': {'joy': 0.1, 'curiosity': 0.05}, 'memory_update': '查询了北京天气，多云，21°C', 'message': '北京今天多云，温度21°C，湿度46%'}
# 情绪状态: {'joy': 0.6, 'anger': 0.0, 'sadness': 0.0, 'fear': 0.0, 'trust': 0.0, 'anticipation': 0.0, 'disgust': 0.0, 'surprise': 0.0}
```

## 7. 开发最佳实践

### 7.1 技能设计原则

- **单一职责**：每个技能只负责一个特定功能
- **错误处理**：妥善处理执行过程中的错误
- **超时机制**：实现技能执行的超时控制
- **结果标准化**：返回标准化的结果格式
- **资源管理**：合理使用系统资源，避免过度消耗

### 7.2 性能优化

- **缓存**：对于频繁调用的技能，实现结果缓存
- **异步执行**：使用异步编程模式，避免阻塞主流程
- **批量处理**：对于批量操作，实现批量处理逻辑

### 7.3 安全性

- **输入验证**：验证用户输入，防止恶意输入
- **权限控制**：实现技能的权限控制
- **资源限制**：限制技能的资源使用

## 8. 故障排除

### 8.1 技能不被调用

- 检查 `can_handle` 方法是否正确实现
- 确认技能已正确注册到 `_init_agent_skills` 方法
- 检查技能的优先级是否正确

### 8.2 技能执行失败

- 检查技能的 `execute` 方法是否正确实现
- 查看系统日志，了解具体错误信息
- 确认技能所需的依赖是否安装

### 8.3 情绪和记忆更新失败

- 检查 `emotion_update` 和 `memory_update` 的格式是否正确
- 确认 `memory_cortex.store_memory` 方法的调用是否正确
- 查看系统日志，了解具体错误信息

## 9. 总结

AgentSkills 是女娲系统的重要扩展机制，通过标准化的接口和执行流程，使系统能够自动处理特定功能的请求。开发者可以通过继承 `AgentSkill` 基类，实现自定义技能，为系统添加新的功能。

通过合理设计和实现 AgentSkills，可以使女娲系统更加智能、灵活和实用，为用户提供更好的交互体验。