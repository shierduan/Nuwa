"""
女娲自我进化状态管理模块 (Nuwa Self Evolution State Module)

功能：管理女娲的自我进化状态，包括演化后的人格特征和演化历史。

核心功能：
- SelfEvolutionState: 自我进化状态管理类
- 加载和保存自我进化状态
- 与人格配置分离，独立管理
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class SelfEvolutionState:
    """
    女娲自我进化状态管理类
    
    管理女娲的自我进化状态，包括演化后的人格特征和演化历史。
    与人格配置分离，独立管理，方便调试和扩展。
    """
    
    def __init__(self, data_dir: str = "data", project_name: str = "nuwa"):
        """
        初始化自我进化状态管理类
        
        Args:
            data_dir: 数据目录
            project_name: 项目名称
        """
        self.data_dir = data_dir
        self.project_name = project_name
        self.evolution_file_path = os.path.join(data_dir, project_name, "evolution_state.json")
        
        # 自我进化状态默认值
        self.state = {
            "short_term_vibe": "",          # 短期情绪和即时需求
            "recent_habits": "",            # 近期习惯和话题
            "relationship_phase": "",       # 关系发展阶段
            "core_bond": "",               # 核心纽带和价值观
            "weights": {                     # 各维度权重
                "short_term_vibe": 1.0,
                "recent_habits": 0.7,
                "relationship_phase": 0.4,
                "core_bond": 0.2
            },
            "last_evolution_time": 0.0,      # 最后演化时间戳
            "evolution_count": 0,             # 演化次数
            "evolution_history": []           # 演化历史记录
        }
        
        # 加载已保存的自我进化状态（如果存在）
        self.load_state()
    
    def load_state(self) -> bool:
        """
        加载已保存的自我进化状态
        
        Returns:
            是否加载成功
        """
        if os.path.exists(self.evolution_file_path):
            try:
                with open(self.evolution_file_path, "r", encoding="utf-8") as f:
                    saved_state = json.load(f)
                
                # 更新状态
                self.state.update(saved_state)
                print(f"📥 [SelfEvolutionState] 成功加载自我进化状态，共演化 {self.state.get('evolution_count', 0)} 次")
                return True
            except (json.JSONDecodeError, IOError, TypeError) as e:
                print(f"⚠️ [SelfEvolutionState] 加载自我进化状态失败: {e}")
                # 加载失败时使用默认状态
                self.reset_state()
        return False
    
    def save_state(self) -> bool:
        """
        保存自我进化状态到文件
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.evolution_file_path), exist_ok=True)
            
            # 保存状态
            with open(self.evolution_file_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            
            print(f"💾 [SelfEvolutionState] 自我进化状态已保存到 {self.evolution_file_path}")
            return True
        except IOError as e:
            print(f"⚠️ [SelfEvolutionState] 保存自我进化状态失败: {e}")
            return False
    
    def update_state(self, new_state: Dict[str, Any]) -> bool:
        """
        更新自我进化状态
        
        Args:
            new_state: 新的状态数据
            
        Returns:
            是否更新成功
        """
        if not isinstance(new_state, dict):
            print(f"⚠️ [SelfEvolutionState] 无效的状态数据类型: {type(new_state)}")
            return False
        
        try:
            # 更新状态
            self.state.update(new_state)
            
            # 记录演化历史
            if new_state.get("last_evolution_time"):
                history_entry = {
                    "timestamp": new_state["last_evolution_time"],
                    "short_term_vibe": new_state.get("short_term_vibe", self.state.get("short_term_vibe", "")),
                    "recent_habits": new_state.get("recent_habits", self.state.get("recent_habits", "")),
                    "relationship_phase": new_state.get("relationship_phase", self.state.get("relationship_phase", "")),
                    "core_bond": new_state.get("core_bond", self.state.get("core_bond", "")),
                    "evolution_count": new_state.get("evolution_count", self.state.get("evolution_count", 0))
                }
                self.state["evolution_history"].append(history_entry)
                
                # 限制历史记录长度
                max_history = 50
                if len(self.state["evolution_history"]) > max_history:
                    self.state["evolution_history"] = self.state["evolution_history"][-max_history:]
            
            # 保存更新后的状态
            return self.save_state()
        except Exception as e:
            print(f"⚠️ [SelfEvolutionState] 更新状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def reset_state(self) -> bool:
        """
        重置自我进化状态到默认值
        
        Returns:
            是否重置成功
        """
        self.state = {
            "short_term_vibe": "",
            "recent_habits": "",
            "relationship_phase": "",
            "core_bond": "",
            "weights": {
                "short_term_vibe": 1.0,
                "recent_habits": 0.7,
                "relationship_phase": 0.4,
                "core_bond": 0.2
            },
            "last_evolution_time": 0.0,
            "evolution_count": 0,
            "evolution_history": []
        }
        
        return self.save_state()
    
    def get_state(self) -> Dict[str, Any]:
        """
        获取当前自我进化状态
        
        Returns:
            当前自我进化状态字典
        """
        return self.state.copy()
    
    def get_evolved_personality_block(self) -> str:
        """
        构建演化人格XML块，用于注入到System Prompt
        
        Returns:
            演化人格XML块字符串
        """
        # 检查是否有非空的人格数据
        has_data = any(
            self.state.get(key) and str(self.state.get(key)).strip()
            for key in ["short_term_vibe", "recent_habits", "relationship_phase", "core_bond"]
        )
        
        if not has_data:
            return ""
        
        # 构建XML块
        blocks = []
        
        short_term_vibe = self.state.get("short_term_vibe", "").strip()
        if short_term_vibe:
            weight = self.state.get("weights", {}).get("short_term_vibe", 1.0)
            blocks.append(f"[High Priority - Weight {weight}] Current Vibe: {short_term_vibe}")
        
        recent_habits = self.state.get("recent_habits", "").strip()
        if recent_habits:
            weight = self.state.get("weights", {}).get("recent_habits", 0.7)
            blocks.append(f"[Medium Priority - Weight {weight}] Recent Habits: {recent_habits}")
        
        relationship_phase = self.state.get("relationship_phase", "").strip()
        if relationship_phase:
            weight = self.state.get("weights", {}).get("relationship_phase", 0.4)
            blocks.append(f"[Low Priority - Weight {weight}] Relationship Phase: {relationship_phase}")
        
        core_bond = self.state.get("core_bond", "").strip()
        if core_bond:
            weight = self.state.get("weights", {}).get("core_bond", 0.2)
            blocks.append(f"[Background - Weight {weight}] Core Bond: {core_bond}")
        
        if not blocks:
            return ""
        
        persona_content = "\n".join(blocks)
        
        return f"""<evolved_personality>
{persona_content}

Instruction: When these traits conflict, prioritize higher weight traits.
</evolved_personality>

"""
    
    def get_last_evolution_time(self) -> float:
        """
        获取最后演化时间
        
        Returns:
            最后演化时间戳
        """
        return self.state.get("last_evolution_time", 0.0)
    
    def get_evolution_count(self) -> int:
        """
        获取演化次数
        
        Returns:
            演化次数
        """
        return self.state.get("evolution_count", 0)
    
    def clear_evolution_history(self) -> bool:
        """
        清除演化历史记录
        
        Returns:
            是否清除成功
        """
        self.state["evolution_history"] = []
        return self.save_state()
