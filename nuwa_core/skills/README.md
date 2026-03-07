# 技能系统 (AgentSkills)

## 简介

AgentSkills 是女娲系统的技能扩展机制，允许开发者创建和集成各种功能模块，使女娲能够执行特定的任务和操作。

## 核心概念

- **AgentSkill**：技能基类，所有技能都应该继承自此类
- **技能执行**：技能接收用户查询、情绪状态和记忆上下文，返回执行结果
- **情绪感知**：技能可以感知和影响女娲的情绪状态
- **记忆上下文**：技能可以利用历史记忆来做出更智能的决策

## 快速开始

### 创建新技能

要创建一个新技能，只需继承 `AgentSkill` 基类并实现 `execute` 方法：

```python
from nuwa_core.skills.agent_skills import AgentSkill
from typing import Dict, Any

class MySkill(AgentSkill):
    def __init__(self):
        super().__init__()
        self.name = "MySkill"
        self.description = "我的自定义技能"
        self.keywords = ["关键词1", "关键词2"]
    
    async def execute(self, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        # 实现技能逻辑
        result = {"data": "技能执行结果"}
        emotion_update = {"joy": 0.1}  # 调整情绪
        memory_update = "使用了我的自定义技能"
        message = "技能执行成功！"
        
        return self.format_response(
            success=True,
            result=result,
            emotion_update=emotion_update,
            memory_update=memory_update,
            message=message
        )
```

### 注册技能

在 `nuwa_core/skills/workspace.py` 文件中，将你的技能添加到 `get_agent_skills` 函数中：

```python
def get_agent_skills() -> List[AgentSkill]:
    from .weather_skill import WeatherSkill
    from .my_skill import MySkill
    
    return [
        WeatherSkill(),
        MySkill()
    ]
```

## 内置技能

### WeatherSkill

**功能**：查询天气信息

**关键词**：天气、温度、晴、雨、雪、预报、天气怎么样

**使用示例**：
- "北京天气怎么样"
- "上海的温度是多少"
- "广州今天晴吗"

**返回结果**：
- 城市当前天气状况
- 温度、湿度、风力等信息
- 未来几天的天气预报
- 根据天气状况调整情绪

## 技能执行流程

1. **查询匹配**：系统根据用户输入的关键词匹配适合的技能
2. **情绪分析**：提取当前的情绪状态
3. **记忆检索**：获取相关的历史记忆
4. **技能执行**：调用匹配的技能执行具体任务
5. **结果处理**：
   - 更新情绪状态
   - 保存记忆
   - 给予自我进化奖励
   - 生成回复消息

## 技能开发指南

### 最佳实践

1. **明确的关键词**：设置清晰的关键词，确保技能能够正确匹配用户查询
2. **情绪感知**：考虑技能执行对情绪的影响，合理调整情绪状态
3. **记忆管理**：保存有意义的记忆，帮助系统学习和改进
4. **错误处理**：妥善处理异常情况，确保系统稳定性
5. **响应时间**：控制技能执行时间，避免系统响应延迟

### 技能执行结果格式

技能执行结果应包含以下字段：

- `success`：布尔值，表示执行是否成功
- `result`：字典，包含执行结果数据
- `emotion_update`：字典，包含情绪更新
- `memory_update`：字符串，包含记忆更新内容
- `message`：字符串，向用户展示的消息

## 测试技能

使用 `test_skills.py` 脚本测试技能：

```bash
python test_skills.py
```

## 示例：创建一个简单的计算器技能

```python
from nuwa_core.skills.agent_skills import AgentSkill
from typing import Dict, Any
import re

class CalculatorSkill(AgentSkill):
    def __init__(self):
        super().__init__()
        self.name = "CalculatorSkill"
        self.description = "简单计算器"
        self.keywords = ["计算", "加", "减", "乘", "除", "等于", "+", "-", "*", "/"]
    
    async def execute(self, query: str, emotion_state: Dict[str, float], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        # 提取计算表达式
        expression = self._extract_expression(query)
        if not expression:
            return self.format_response(
                success=False,
                result={},
                emotion_update={"sadness": 0.1},
                memory_update="用户尝试计算但表达式无效",
                message="请输入有效的计算表达式，例如：1+2"
            )
        
        # 执行计算
        try:
            result = eval(expression)
            message = f"计算结果：{expression} = {result}"
            memory_update = f"计算了 {expression}，结果是 {result}"
            
            return self.format_response(
                success=True,
                result={"expression": expression, "result": result},
                emotion_update={"joy": 0.1},
                memory_update=memory_update,
                message=message
            )
        except Exception as e:
            return self.format_response(
                success=False,
                result={},
                emotion_update={"sadness": 0.2},
                memory_update=f"计算 {expression} 失败",
                message=f"计算失败：{str(e)}"
            )
    
    def _extract_expression(self, query: str) -> str:
        # 提取计算表达式
        pattern = r'[0-9+\-*/()\s]+'
        matches = re.findall(pattern, query)
        if matches:
            return matches[0].strip()
        return ""
```

## 总结

AgentSkills 系统为女娲提供了强大的扩展能力，使她能够执行各种复杂的任务。通过遵循本指南，你可以创建和集成各种自定义技能，丰富女娲的功能和交互体验。
