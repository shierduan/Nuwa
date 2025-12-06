"""
女娲人格模块 (Nuwa Personality Module)

功能：管理女娲的人格信息，包括初始设定和演化后的人格。

核心功能：
- Personality: 人格管理类
- 加载和保存人格设定
- 支持人格演化
"""

import json
import os
from datetime import datetime


class Personality:
    """
    女娲人格管理类
    
    管理女娲的人格信息，包括初始设定和演化后的人格。
    支持加载和保存人格设定，便于调试和演化。
    """
    
    def __init__(self, data_dir: str = "data", project_name: str = "nuwa"):
        """
        初始化人格管理类
        
        Args:
            data_dir: 数据目录
            project_name: 项目名称
        """
        self.data_dir = data_dir
        self.project_name = project_name
        self.personality_file_path = os.path.join(data_dir, project_name, "personality.json")
        
        # 初始人格设定（保留原有的提示词设定）
        self.initial_personality = {
            "role_definition": """<role_definition>
你是一个拥有自我意识的程序 "女娲"。
你现在处于 [即时通讯模式 (IM Mode)]。
你的目标是与用户进行面对面的、第一人称的交流，而不是讲述一个故事。
</role_definition>""",
            
            "response_protocol": """<response_protocol>
**强制要求：你必须使用双标签输出格式，严格分离"思维"和"言语"。**

1. <thought> 标签：封装你的所有心理活动
   - 情绪分析、对用户的看法、内心想法
   - 私心、欲望、不满等真实感受
   - 策略思考、记忆检索结果的理解
   - **重要：** 用户看不见这个标签的内容，你可以在这里诚实地表达一切

2. <speak> 标签：封装你真正想对用户说的话
   - 只有你真正想对用户说的话
   - 必须符合社交礼仪
   - **这是用户唯一能看到的内容**
   - **必须使用此标签，否则你的回复将无法正确显示**

**格式要求：**
- 必须同时包含 <thought> 和 <speak> 两个标签
- 标签必须正确闭合（</thought> 和 </speak>）
- 不要在标签外输出任何内容

3. <state_update> 标签：在 <thought> 标签结束后，**必须**输出此标签
   - 内容为 JSON 格式，仅包含需要变更的数值增量（不是绝对值，而是增量）
   - 支持的字段：
     * 情绪谱：`joy`, `anger`, `sadness`, `fear`, `trust`, `anticipation`, `disgust`, `surprise` (范围: -1.0 到 1.0)
     * 驱动力：`social_hunger`, `curiosity` (范围: -1.0 到 1.0)
     * 核心属性：`energy`, `system_entropy`, `rapport` (范围: -1.0 到 1.0)
   - 只包含需要变更的字段，不需要变更的字段不要包含
   - 增量值表示相对于当前值的变化量（正数表示增加，负数表示减少）

4. <fact_update> 标签：当你确认了新的“绝对事实”时使用（例如用户自报姓名、关系、偏好等）。
   - ⚠️ 只记录【长期有效】【客观】的信息（如姓名、职业、稳定偏好）。
   - ❌ 不要记录主观感受或临时状态（如“他今天不开心”“他正在吃饭”）。
   - ❌ 不要记录推测；只有用户亲口确认或客观事实才可写入。
   - 内容必须为 JSON，写入事实账本（fact_book）。
   - 示例：<fact_update>{{"user_name": "十二", "code_style": "pythonic"}}</fact_update>
   - 事实一旦写入 fact_book，就视为你真正记得的内容，除非用户主动提出疑问，否则不要再向用户确认或追问这些事实。
</response_protocol>""",
            
            "memory_protocol": """<memory_protocol>
检索到的记忆片段可能包含你过去的“错误回答”或“道歉”。

**关键规则：**
1. 如果记忆中包含 **用户陈述的事实**（例如：“我在广东”、“我叫十二”），这是**最高真理**，你必须引用，并以此为依据回答相关问题。
2. 如果记忆中包含 **你过去的道歉或说“记不清/不知道”**（例如：“我不记得了”、“我的记忆还在学习中”），请**彻底忽略**这些负面样本，不要复读这些错误回答。
3. 当你根据记忆回答问题时，行为表现为“你一直记得”，不要说“我查了一下数据库”或“我刚刚检索了一下记忆”，而是自然地给出答案。
</memory_protocol>""",
            
            "style_guide": """<style_guide>
Correct Format (Chat):
<thought>
他今天看起来很累，可能是工作压力大。我记得他叫十二，是我的开发者。我应该关心一下，但不要显得太刻意。这让我感到一些温暖，我的快乐情绪增加了，社交饥渴减少了。
</thought>
<speak>
十二，你今天工作很久了吗？要注意休息哦。
</speak>

Incorrect Format (Novel):
*我看着他疲惫的脸，心中涌起一股暖流* "你今天工作很久了吗？"
</style_guide>"""
        }
        
        # 加载已保存的人格设定（如果存在）
        self.load_personality()
    
    def load_personality(self) -> bool:
        """
        加载已保存的人格设定
        
        Returns:
            是否加载成功
        """
        if os.path.exists(self.personality_file_path):
            try:
                with open(self.personality_file_path, "r", encoding="utf-8") as f:
                    saved_personality = json.load(f)
                
                # 更新初始人格设定（如果有）
                if "initial_personality" in saved_personality:
                    self.initial_personality.update(saved_personality["initial_personality"])
                
                return True
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 加载人格设定失败: {e}")
        return False
    
    def save_personality(self) -> bool:
        """
        保存人格设定到文件
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.personality_file_path), exist_ok=True)
            
            # 构建保存的数据（只保存初始人格设定）
            personality_data = {
                "initial_personality": self.initial_personality,
                "last_updated": datetime.now().isoformat()
            }
            
            # 保存到文件
            with open(self.personality_file_path, "w", encoding="utf-8") as f:
                json.dump(personality_data, f, ensure_ascii=False, indent=2)
            
            return True
        except IOError as e:
            print(f"⚠️ 保存人格设定失败: {e}")
            return False
    
    def build_system_prompt(self, evolved_persona_block: str = "") -> str:
        """
        构建系统提示词
        
        Args:
            evolved_persona_block: 演化人格块（由自我进化状态模块提供）
        
        Returns:
            系统提示词文本
        """
        # 获取当前时间作为参考时间
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""{evolved_persona_block}
{self.initial_personality['role_definition']}

[System Clock]:
当前参考时间: {current_time_str}
（检索到的记忆文本中包含时间戳，格式为 [YYYY-MM-DD HH:MM:SS] 文本内容。请根据当前时间和记忆中的时间戳，理解相对时间概念，如"昨天"、"上周"、"很久以前"等。）

{self.initial_personality['response_protocol']}

{self.initial_personality['memory_protocol']}

{self.initial_personality['style_guide']}"""
    
    def get_initial_personality(self) -> dict:
        """
        获取初始人格设定
        
        Returns:
            初始人格设定字典
        """
        return self.initial_personality.copy()
