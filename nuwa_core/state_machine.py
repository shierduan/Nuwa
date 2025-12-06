"""
向量状态机模块 (Vector-Based State Machine Module)

功能：将文学描述转化为可计算的数学向量，使用向量算法进行状态管理。

核心功能：
- NarrativeState: 语义化的状态数据结构（增强版：包含向量）
- extract_semantic_state: 从文本中提取语义状态信息
- update_vector_state: 计算并更新状态向量（使用 EMA 平滑算法）
"""

import json
import re
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

# 导入向量计算相关库
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    EMBEDDING_AVAILABLE = False

from .model_utils import ensure_embedding_model_dir


@dataclass
class NarrativeState:
    """
    叙事状态对象（语义化 + 向量化）
    
    使用语义描述而非数字，更符合小说创作逻辑。
    同时包含向量表示，用于数学计算和算法判断。
    """
    characters: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # 角色状态字典
    relations: List[Dict[str, Any]] = field(default_factory=list)  # 动态羁绊列表
    environment: str = ""  # 环境氛围描述
    plot_flags: List[str] = field(default_factory=list)  # 剧情标志列表
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 向量表示（新增）
    character_vectors: Dict[str, List[float]] = field(default_factory=dict)  # 角色状态向量
    # 格式: { "亚瑟": [0.12, -0.5, ...] }  # 384维向量（all-MiniLM-L6-v2）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 将 numpy 数组转换为列表（如果存在）
        if NUMPY_AVAILABLE and np is not None:
            for char_name, vector in data.get("character_vectors", {}).items():
                if isinstance(vector, np.ndarray):
                    data["character_vectors"][char_name] = vector.tolist()
        return data
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NarrativeState':
        """从字典创建 NarrativeState"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'NarrativeState':
        """从 JSON 字符串创建 NarrativeState"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ChapterNode:
    """
    章节节点对象（兼容旧版本，但使用 NarrativeState）
    
    每一章不再只是文本，而是一个节点对象，包含完整的状态信息。
    """
    chapter_id: int
    text_content: str
    narrative_state: NarrativeState = field(default_factory=NarrativeState)  # 语义化状态
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # NTD 升级：状态向量（新增）
    state_vector: Optional[List[float]] = None  # 章节整体状态向量（384维）
    # 由 physique + psyche + environment 拼接后向量化得到
    
    # 兼容旧版本的字段（保留但不再使用）
    world_state: Dict[str, Any] = field(default_factory=dict)
    character_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 将 NarrativeState 转换为字典
        data['narrative_state'] = self.narrative_state.to_dict()
        # 将 numpy 数组转换为列表（如果存在）
        if NUMPY_AVAILABLE and np is not None and self.state_vector is not None:
            if isinstance(self.state_vector, np.ndarray):
                data['state_vector'] = self.state_vector.tolist()
        return data
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChapterNode':
        """从字典创建 ChapterNode"""
        # 创建数据副本，避免修改原始数据
        node_data = data.copy()
        
        # 处理 narrative_state
        if 'narrative_state' in node_data and isinstance(node_data['narrative_state'], dict):
            node_data['narrative_state'] = NarrativeState.from_dict(node_data['narrative_state'])
        elif 'narrative_state' not in node_data:
            # 如果没有 narrative_state，尝试从旧格式转换
            narrative_state = NarrativeState()
            
            # 从旧格式的 world_state 转换
            if 'world_state' in node_data:
                world_state = node_data.get('world_state', {})
                # 可以在这里添加转换逻辑，将 world_state 转换为 narrative_state 的格式
            
            # 从旧格式的 character_states 转换
            if 'character_states' in node_data:
                character_states = node_data.get('character_states', {})
                for char_name, char_state in character_states.items():
                    # 转换旧格式的角色状态
                    narrative_state.characters[char_name] = {
                        "physique": char_state.get("hp", ""),  # 简化转换
                        "psyche": char_state.get("emotion", ""),
                        "focus": "",
                        "equipment": char_state.get("items", []),
                    }
            
            # 从旧格式的 plot_flags 转换
            if 'plot_flags' in node_data:
                narrative_state.plot_flags = node_data.get('plot_flags', [])
            
            node_data['narrative_state'] = narrative_state
        
        # 移除不在 ChapterNode 中的字段（兼容旧数据）
        valid_fields = {
            'chapter_id', 'text_content', 'narrative_state', 'timestamp', 
            'state_vector', 'world_state', 'character_states'
        }
        node_data = {k: v for k, v in node_data.items() if k in valid_fields}
        
        return cls(**node_data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ChapterNode':
        """从 JSON 字符串创建 ChapterNode"""
        return cls.from_dict(json.loads(json_str))


def extract_semantic_state(
    text: str,
    prev_state: Optional[ChapterNode] = None,
    selected_model: str = "lm_studio",
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    gemini_base_url: Optional[str] = None,
    chapter_id: Optional[int] = None,
    characters: Optional[List[Dict[str, str]]] = None,
) -> ChapterNode:
    """
    调用 LLM 分析正文，提取语义化的状态信息
    
    Args:
        text: 章节正文内容
        prev_state: 前一章的状态节点（用于增量更新）
        selected_model: 模型类型 ("lm_studio" 或 "gemini")
        base_url: LM Studio 的 base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini 的 base_url
        chapter_id: 章节ID
        characters: 角色列表，格式为 [{"name": "角色名", "description": "描述"}, ...]
    
    Returns:
        ChapterNode: 包含提取的语义状态信息的章节节点
    """
    if not text or len(text.strip()) < 10:
        # 如果文本为空，返回空状态节点
        return ChapterNode(
            chapter_id=chapter_id or 0,
            text_content=text or "",
        )
    
    # 构建提取状态的提示词
    character_list_text = ""
    if characters:
        char_names = [char.get("name", "") for char in characters if char.get("name")]
        if char_names:
            character_list_text = f"\n\n【角色列表】\n{', '.join(char_names)}"
    
    prev_state_text = ""
    if prev_state and prev_state.narrative_state:
        prev_narrative = prev_state.narrative_state
        prev_state_text = f"""
【前一章状态快照】
- 角色状态：{json.dumps(prev_narrative.characters, ensure_ascii=False)[:800]}
- 关系状态：{json.dumps(prev_narrative.relations, ensure_ascii=False)[:500]}
- 环境氛围：{prev_narrative.environment[:200]}
- 剧情标志：{', '.join(prev_narrative.plot_flags[:10])}
"""
    
    system_prompt = """你是一个专业的小说状态分析器。你的任务是从章节文本中提取结构化的语义状态信息。

**重要要求：不要输出数字。请用精炼的文学语言描述角色的当前状态。重点提取那些会影响下一章剧情走向的要素（如伤势、情绪、持有的关键物品）。**

提取要求：
1. **角色状态 (characters)**：对每个出现的角色，提取：
   - physique: 生理状态描述（如："左臂贯穿伤，体力透支，濒临昏迷"）- 代替 HP
   - psyche: 心理状态描述（如："因背叛而极度愤恨，理智线紧绷"）- 代替 SAN/Mood
     **心理状态提取约束**：
     * 必须基于正文中该角色的实际表现和内心活动
     * 必须与前一章的心理状态有逻辑连贯性（除非正文明确描述了情绪突变）
     * 必须与角色的性格设定相符（参考角色列表中的描述）
     * 不要提取其他角色的心理状态
     * 不要提取过于笼统的描述（如"正常"、"一般"），要具体（如"因紧张而手心出汗"）
     * 不要提取正文中没有体现的心理状态
   - focus: 当前行动元（Action Driver，如："必须在日落前把信送出"）
   - equipment: 关键道具列表（仅记录剧情相关的，如：["断裂的家徽剑", "沾血的信"]）

2. **关系状态 (relations)**：角色间的动态羁绊
   - target: 目标角色名
   - status: 关系状态（如："决裂"、"结盟"、"暗恋"等）
   - tone: 关系氛围（如："剑拔弩张"、"温情脉脉"等）

3. **环境氛围 (environment)**：当前场景的环境描述（如："暴雨中的泥泞小道，能见度极低"）

4. **剧情标志 (plot_flags)**：重要剧情事件（如："反派已死"、"获得神器"、"发现真相"等）

输出格式必须是严格的 JSON，包含以下结构：
{
  "characters": {
    "角色名1": {
      "physique": "生理状态描述",
      "psyche": "心理状态描述",
      "focus": "当前行动元",
      "equipment": ["道具1", "道具2"]
    },
    "角色名2": {
      ...
    }
  },
  "relations": [
    {
      "target": "目标角色名",
      "status": "关系状态",
      "tone": "关系氛围"
    }
  ],
  "environment": "环境氛围描述",
  "plot_flags": ["剧情标志1", "剧情标志2"]
}

如果某个维度没有信息，使用空对象 {} 或空数组 []。"""

    user_prompt = f"""请分析以下章节文本，提取语义状态信息。{character_list_text}{prev_state_text}

【章节文本】
{text[:3000]}

请严格按照 JSON 格式输出，不要添加任何解释性文字。重点是用文学语言描述状态，不要使用数字。"""

    # 调用 LLM（只使用已加载的模块，避免触发 Streamlit UI 代码执行）
    result_text = None
    
    try:
        import sys
        
        # 只从已加载的模块中获取函数，绝不尝试导入（避免触发 UI 代码）
        generate_content_lm_studio = None
        generate_content_gemini = None
        
        # 在 Streamlit 中，主文件可能以 '__main__' 运行，也可能以 'app' 运行
        # 尝试从多个可能的模块名中获取函数
        possible_module_names = ['app', '__main__']
        
        for module_name in possible_module_names:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                if generate_content_lm_studio is None:
                    generate_content_lm_studio = getattr(module, 'generate_content_lm_studio', None)
                if generate_content_gemini is None:
                    generate_content_gemini = getattr(module, 'generate_content_gemini', None)
                
                # 如果两个函数都找到了，可以提前退出
                if generate_content_lm_studio is not None and generate_content_gemini is not None:
                    break
        
        # 如果还是找不到，尝试从所有已加载的模块中搜索（但跳过内置模块）
        if generate_content_lm_studio is None or generate_content_gemini is None:
            for module_name, module in sys.modules.items():
                if module is None:
                    continue
                # 跳过内置模块和标准库
                if module_name.startswith('_') or '.' in module_name:
                    continue
                
                if generate_content_lm_studio is None:
                    generate_content_lm_studio = getattr(module, 'generate_content_lm_studio', None)
                if generate_content_gemini is None:
                    generate_content_gemini = getattr(module, 'generate_content_gemini', None)
                
                if generate_content_lm_studio is not None and generate_content_gemini is not None:
                    break
        
        if generate_content_lm_studio is None or generate_content_gemini is None:
            # 提供更详细的错误信息
            loaded_modules = [name for name in sys.modules.keys() if not name.startswith('_') and '.' not in name]
            raise ImportError(
                f"无法获取生成函数。已检查的模块: {possible_module_names}。"
                f"已加载的模块（部分）: {loaded_modules[:10]}。"
                "请确保 app 模块已加载。"
                "注意：nuwa_core 不能导入 app 模块，因为会导致 Streamlit UI 代码重复执行。"
            )
        
        if selected_model == "gemini":
            if not api_key or not model_name:
                raise ValueError("Gemini 配置不完整")
            
            success, result = generate_content_gemini(
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=gemini_base_url,
                max_output_tokens=2048,
                temperature=0.3,
                stream=False,
            )
            if success:
                result_text = result
        else:
            # LM Studio
            if not base_url or not model_name:
                raise ValueError("LM Studio 配置不完整")
            
            success, result = generate_content_lm_studio(
                base_url=base_url,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2048,
                temperature=0.3,
                stream=False,
            )
            if success:
                result_text = result
    except Exception as e:
        print(f"状态提取失败: {e}")
        import traceback
        print(traceback.format_exc())
        result_text = None
    
    # 解析结果
    if not result_text:
        # 如果 LLM 调用失败，返回基础节点
        return ChapterNode(
            chapter_id=chapter_id or 0,
            text_content=text,
        )
    
    # 尝试提取 JSON
    state_data = _parse_state_json(result_text)
    
    # 合并前一章的状态（增量更新）
    if prev_state and prev_state.narrative_state:
        state_data = _merge_semantic_states(prev_state.narrative_state, state_data)
    
    # 验证和修正心理状态（添加约束检查）
    if characters:
        state_data = _validate_and_correct_psyche(
            state_data=state_data,
            text=text,
            prev_state=prev_state,
            characters=characters,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
        )
    
    # 创建 NarrativeState
    narrative_state = NarrativeState(
        characters=state_data.get("characters", {}),
        relations=state_data.get("relations", []),
        environment=state_data.get("environment", ""),
        plot_flags=state_data.get("plot_flags", []),
    )
    
    # 计算并更新向量状态（使用 EMA 平滑）
    prev_narrative_state = prev_state.narrative_state if prev_state else None
    narrative_state = update_vector_state(
        narrative_state=narrative_state,
        prev_narrative_state=prev_narrative_state,
        alpha=0.7  # EMA 平滑系数（可调）
    )
    
    # ==================== NTD 升级：计算章节整体状态向量 ====================
    # 将 physique + psyche + environment 拼接成描述文本，然后向量化
    state_vector = _compute_chapter_state_vector(
        narrative_state=narrative_state,
        prev_state=prev_state,
        alpha=0.7  # EMA 平滑系数
    )
    
    # 创建 ChapterNode
    return ChapterNode(
        chapter_id=chapter_id or 0,
        text_content=text,
        narrative_state=narrative_state,
        state_vector=state_vector,  # 新增：章节状态向量
    )


# 兼容旧版本的函数名
def extract_state(
    text: str,
    prev_state: Optional[ChapterNode] = None,
    selected_model: str = "lm_studio",
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    gemini_base_url: Optional[str] = None,
    chapter_id: Optional[int] = None,
    characters: Optional[List[Dict[str, str]]] = None,
) -> ChapterNode:
    """
    兼容旧版本的函数名，实际调用 extract_semantic_state
    """
    return extract_semantic_state(
        text=text,
        prev_state=prev_state,
        selected_model=selected_model,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        gemini_base_url=gemini_base_url,
        chapter_id=chapter_id,
        characters=characters,
    )


def _parse_state_json(text: str) -> Dict[str, Any]:
    """
    从 LLM 输出中解析 JSON 状态数据
    
    Args:
        text: LLM 返回的文本
    
    Returns:
        解析后的状态数据字典
    """
    if not text:
        return {}
    
    # 尝试提取 JSON 代码块
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 尝试直接提取第一个 JSON 对象
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            return {}
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 如果解析失败，尝试修复常见的 JSON 问题
        try:
            # 移除注释
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            return json.loads(json_str)
        except Exception:
            return {}


def _merge_semantic_states(prev_state: NarrativeState, new_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并前一章的语义状态和新提取的状态（增量更新）
    
    Args:
        prev_state: 前一章的语义状态
        new_state: 新提取的状态数据
    
    Returns:
        合并后的状态数据
    """
    merged = {
        "characters": {k: v.copy() for k, v in prev_state.characters.items()},
        "relations": prev_state.relations.copy(),
        "environment": prev_state.environment,
        "plot_flags": prev_state.plot_flags.copy(),
    }
    
    # 更新角色状态（增量更新）
    if "characters" in new_state:
        for char_name, char_state in new_state["characters"].items():
            if char_name in merged["characters"]:
                # 合并现有状态（新状态覆盖旧状态）
                merged["characters"][char_name].update(char_state)
            else:
                # 新增角色状态
                merged["characters"][char_name] = char_state
    
    # 更新关系状态（追加新关系，去重）
    if "relations" in new_state:
        for new_rel in new_state["relations"]:
            # 检查是否已存在相同的关系
            exists = False
            for existing_rel in merged["relations"]:
                if (existing_rel.get("target") == new_rel.get("target") and
                    existing_rel.get("status") == new_rel.get("status")):
                    # 更新现有关系
                    existing_rel.update(new_rel)
                    exists = True
                    break
            if not exists:
                merged["relations"].append(new_rel)
    
    # 更新环境氛围（新环境覆盖旧环境）
    if "environment" in new_state and new_state["environment"]:
        merged["environment"] = new_state["environment"]
    
    # 更新剧情标志（去重）
    if "plot_flags" in new_state:
        for flag in new_state["plot_flags"]:
            if flag not in merged["plot_flags"]:
                merged["plot_flags"].append(flag)
    
    return merged


def _validate_and_correct_psyche(
    state_data: Dict[str, Any],
    text: str,
    prev_state: Optional[ChapterNode],
    characters: List[Dict[str, str]],
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> Dict[str, Any]:
    """
    验证和修正心理状态提取结果
    
    检查心理状态是否：
    1. 与正文内容匹配
    2. 与前一章状态连贯
    3. 与角色设定一致
    
    Args:
        state_data: 提取的状态数据
        text: 章节正文
        prev_state: 前一章状态
        characters: 角色列表
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        修正后的状态数据
    """
    if "characters" not in state_data:
        return state_data
    
    # 构建角色设定字典
    character_profiles = {}
    for char in characters:
        char_name = char.get("name", "")
        if char_name:
            character_profiles[char_name] = char.get("description", "")
    
    # 构建前一章心理状态字典
    prev_psyche = {}
    if prev_state and prev_state.narrative_state:
        for char_name, char_state in prev_state.narrative_state.characters.items():
            prev_psyche[char_name] = char_state.get("psyche", "")
    
    # 对每个角色的心理状态进行验证
    for char_name, char_state in state_data["characters"].items():
        current_psyche = char_state.get("psyche", "").strip()
        
        # 如果心理状态为空，跳过验证
        if not current_psyche:
            continue
        
        # 检查1: 心理状态是否与正文内容匹配
        if not _verify_psyche_matches_text(char_name, current_psyche, text):
            # 如果验证失败，尝试从正文中重新提取
            corrected_psyche = _re_extract_psyche_from_text(
                char_name=char_name,
                text=text,
                prev_psyche=prev_psyche.get(char_name, ""),
                character_profile=character_profiles.get(char_name, ""),
                selected_model=selected_model,
                base_url=base_url,
                model_name=model_name,
                api_key=api_key,
                gemini_base_url=gemini_base_url,
            )
            if corrected_psyche:
                char_state["psyche"] = corrected_psyche
                print(f"⚠️ 修正角色「{char_name}」的心理状态：{current_psyche} → {corrected_psyche}")
        
        # 检查2: 心理状态是否与前一章连贯（除非正文明确描述情绪突变）
        if char_name in prev_psyche and prev_psyche[char_name]:
            if not _verify_psyche_continuity(
                char_name=char_name,
                current_psyche=current_psyche,
                prev_psyche=prev_psyche[char_name],
                text=text,
            ):
                # 如果连贯性检查失败，保留当前状态但记录警告
                print(f"⚠️ 角色「{char_name}」的心理状态可能与前章不连贯：{prev_psyche[char_name]} → {current_psyche}")
    
    return state_data


def _verify_psyche_matches_text(char_name: str, psyche: str, text: str) -> bool:
    """
    验证心理状态是否与正文内容匹配
    
    Args:
        char_name: 角色名
        psyche: 心理状态描述
        text: 正文内容
    
    Returns:
        是否匹配
    """
    if not psyche or not text:
        return True  # 如果为空，认为匹配（避免误判）
    
    # 简单的关键词匹配检查
    # 如果心理状态中的关键词在正文中找不到，可能不匹配
    psyche_keywords = ["愤怒", "恐惧", "紧张", "兴奋", "悲伤", "快乐", "焦虑", "平静", "困惑", "坚定"]
    found_keywords = [kw for kw in psyche_keywords if kw in psyche]
    
    if found_keywords:
        # 检查这些关键词是否在角色相关的文本中出现
        # 简单检查：如果正文中包含角色名，且包含相关情绪词汇，认为匹配
        if char_name in text:
            # 检查正文中是否有情绪相关的描述
            text_lower = text.lower()
            for keyword in found_keywords:
                if keyword in text_lower:
                    return True
            # 如果没有找到关键词，但心理状态描述较长，可能是合理的（LLM 可能用不同词汇表达）
            if len(psyche) > 10:
                return True  # 较长的描述可能是合理的概括
    
    # 如果心理状态很短或没有关键词，认为匹配（避免过度严格）
    return True


def _verify_psyche_continuity(
    char_name: str,
    current_psyche: str,
    prev_psyche: str,
    text: str,
) -> bool:
    """
    验证心理状态是否与前章连贯
    
    Args:
        char_name: 角色名
        current_psyche: 当前心理状态
        prev_psyche: 前一章心理状态
        text: 正文内容
    
    Returns:
        是否连贯
    """
    if not current_psyche or not prev_psyche:
        return True  # 如果为空，认为连贯
    
    # 检查正文中是否有明确的情绪突变描述
    mutation_keywords = ["突然", "瞬间", "突然", "忽然", "一下子", "突然", "突变", "转变", "改变"]
    if any(kw in text for kw in mutation_keywords):
        return True  # 如果有突变描述，认为连贯
    
    # 简单的情绪方向检查（不要求完全一致，但方向应该合理）
    # 例如：从"平静"到"愤怒"是合理的，从"愤怒"到"平静"也是合理的
    # 但如果从"极度愤怒"到"极度快乐"且没有突变描述，可能不连贯
    
    # 这里使用简单的启发式规则
    # 如果心理状态描述差异很大，但正文中没有突变描述，可能不连贯
    # 但由于情绪变化是复杂的，这里采用宽松策略
    return True


def _re_extract_psyche_from_text(
    char_name: str,
    text: str,
    prev_psyche: str,
    character_profile: str,
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> Optional[str]:
    """
    从正文中重新提取心理状态（当验证失败时使用）
    
    Args:
        char_name: 角色名
        text: 正文内容
        prev_psyche: 前一章心理状态
        character_profile: 角色设定
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        重新提取的心理状态，如果失败则返回 None
    """
    if not text or not char_name:
        return None
    
    system_prompt = """你是一个专业的小说状态分析器。你的任务是从文本中准确提取特定角色的心理状态。

**重要约束**：
1. 只提取该角色在文本中的实际心理状态，不要推测或想象
2. 必须基于文本中明确描述或暗示的内心活动
3. 如果文本中没有该角色的心理描述，返回空字符串
4. 心理状态描述要具体，不要过于笼统
5. 必须与角色设定相符

只返回心理状态描述，不要添加其他文字。如果没有信息，返回空字符串。"""

    user_prompt = f"""角色名：{char_name}
角色设定：{character_profile[:200] if character_profile else "无"}
前一章心理状态：{prev_psyche if prev_psyche else "无"}

【文本片段】
{text[:1500]}

请准确提取该角色在当前文本中的心理状态。如果文本中没有该角色的心理描述，返回空字符串。"""

    try:
        import sys
        
        generate_content_lm_studio = None
        generate_content_gemini = None
        
        possible_module_names = ['app', '__main__']
        
        for module_name in possible_module_names:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                if generate_content_lm_studio is None:
                    generate_content_lm_studio = getattr(module, 'generate_content_lm_studio', None)
                if generate_content_gemini is None:
                    generate_content_gemini = getattr(module, 'generate_content_gemini', None)
                
                if generate_content_lm_studio is not None and generate_content_gemini is not None:
                    break
        
        if generate_content_lm_studio is None or generate_content_gemini is None:
            return None
        
        if selected_model == "gemini":
            if not api_key or not model_name:
                return None
            
            success, result = generate_content_gemini(
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=gemini_base_url,
                max_output_tokens=200,
                temperature=0.2,
                stream=False,
            )
            if success and result:
                result = result.strip()
                if result and result != "无" and result != "无信息":
                    return result
        else:
            if not base_url or not model_name:
                return None
            
            success, result = generate_content_lm_studio(
                base_url=base_url,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=200,
                temperature=0.2,
                stream=False,
            )
            if success and result:
                result = result.strip()
                if result and result != "无" and result != "无信息":
                    return result
    except Exception as e:
        print(f"重新提取心理状态失败: {e}")
        return None
    
    return None


# ==================== 向量计算模块 ====================

# 全局 Embedding 模型缓存
_embedding_model_cache = None


def get_embedding_model():
    """
    获取 Embedding 模型（带缓存）
    
    Returns:
        SentenceTransformer 模型或 None
    """
    global _embedding_model_cache
    
    if not EMBEDDING_AVAILABLE or SentenceTransformer is None:
        return None
    
    if _embedding_model_cache is None:
        model_path = ensure_embedding_model_dir(SentenceTransformer)
        if not model_path:
            print("❌ 无法加载 Embedding 模型：缺少可用的本地目录，且自动下载失败。")
            return None
        try:
            _embedding_model_cache = SentenceTransformer(model_path, local_files_only=True)
        except Exception as e:
            print(f"加载 Embedding 模型失败：{e}")
            return None
    
    return _embedding_model_cache


def update_vector_state(
    narrative_state: NarrativeState,
    prev_narrative_state: Optional[NarrativeState] = None,
    alpha: float = 0.7
) -> NarrativeState:
    """
    更新状态向量（使用 EMA 平滑算法）
    
    将角色的"心理状态"和"生理状态"转化为向量，并使用指数移动平均 (EMA) 平滑更新。
    
    公式: V_new = α × V_current + (1-α) × V_history
    
    这模拟了人的性格惯性，防止 AI 突然发癫。
    
    Args:
        narrative_state: 当前叙事状态
        prev_narrative_state: 前一章的叙事状态（用于 EMA 平滑）
        alpha: EMA 平滑系数（默认 0.7，范围 0-1）
            - alpha 越大，新状态权重越高（变化更快）
            - alpha 越小，历史状态权重越高（变化更慢，更稳定）
    
    Returns:
        更新后的 NarrativeState（包含 character_vectors）
    """
    if not NUMPY_AVAILABLE or np is None:
        # 如果没有 numpy，返回原状态（不计算向量）
        print("⚠️ update_vector_state: NUMPY_AVAILABLE 为 False 或 np 为 None")
        return narrative_state
    
    embedding_model = get_embedding_model()
    if embedding_model is None:
        print("⚠️ update_vector_state: get_embedding_model() 返回 None（embedding 模型未加载）")
        print(f"   EMBEDDING_AVAILABLE = {EMBEDDING_AVAILABLE}, SentenceTransformer = {SentenceTransformer is not None}")
        return narrative_state
    
    # 初始化 character_vectors（如果不存在）
    if not hasattr(narrative_state, 'character_vectors') or narrative_state.character_vectors is None:
        narrative_state.character_vectors = {}
    
    print(f"🔍 update_vector_state: 开始处理 {len(narrative_state.characters)} 个角色")
    
    # 对每个角色计算向量
    for char_name, char_state in narrative_state.characters.items():
        # 构建状态描述文本
        physique = char_state.get("physique", "")
        psyche = char_state.get("psyche", "")
        focus = char_state.get("focus", "")
        
        # 组合状态描述（至少需要 physique 或 psyche 之一）
        state_text = f"{physique} {psyche}".strip()
        if focus:
            state_text = f"{state_text} {focus}".strip()
        
        if not state_text:
            # 如果状态为空，跳过（但记录日志）
            print(f"⚠️ 角色 {char_name} 的状态为空（physique='{physique}', psyche='{psyche}'），无法生成向量")
            continue
        
        # 生成当前状态的向量
        try:
            current_vector = embedding_model.encode(state_text, convert_to_numpy=True)
            if current_vector is None or len(current_vector) == 0:
                print(f"⚠️ 角色 {char_name} 的向量生成失败（返回空向量）")
                continue
            print(f"✅ 角色 {char_name} 的向量生成成功（维度：{len(current_vector)}）")
        except Exception as e:
            print(f"⚠️ 生成角色 {char_name} 的向量失败: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # EMA 平滑：如果有历史向量，进行平滑
        if prev_narrative_state and prev_narrative_state.character_vectors:
            prev_vector = prev_narrative_state.character_vectors.get(char_name)
            if prev_vector is not None:
                # 转换为 numpy 数组（如果是列表）
                if isinstance(prev_vector, list):
                    prev_vector = np.array(prev_vector)
                
                # EMA 平滑: V_new = α × V_current + (1-α) × V_history
                smoothed_vector = alpha * current_vector + (1 - alpha) * prev_vector
                narrative_state.character_vectors[char_name] = smoothed_vector.tolist()
                print(f"✅ 角色 {char_name} 的向量已更新（EMA 平滑）")
            else:
                # 没有历史向量，直接使用当前向量
                narrative_state.character_vectors[char_name] = current_vector.tolist()
                print(f"✅ 角色 {char_name} 的向量已保存（首次生成）")
        else:
            # 没有历史状态，直接使用当前向量
            narrative_state.character_vectors[char_name] = current_vector.tolist()
            print(f"✅ 角色 {char_name} 的向量已保存（无历史状态）")
    
    print(f"🔍 update_vector_state: 完成，共生成 {len(narrative_state.character_vectors)} 个角色向量")
    return narrative_state


def get_character_core_vector(
    character_name: str,
    character_description: str,
    embedding_model=None
) -> Optional[np.ndarray]:
    """
    获取角色的核心向量（基于角色设定）
    
    用于 OOC 检测：将角色设定转化为向量，作为"人设基准"。
    
    Args:
        character_name: 角色名称
        character_description: 角色设定描述
        embedding_model: Embedding 模型（可选，如果不提供则使用默认模型）
    
    Returns:
        角色的核心向量（numpy 数组）或 None
    """
    if not NUMPY_AVAILABLE or np is None:
        return None
    
    if not character_description or not character_description.strip():
        return None
    
    if embedding_model is None:
        embedding_model = get_embedding_model()
    
    if embedding_model is None:
        return None
    
    try:
        # 生成角色设定的向量
        core_vector = embedding_model.encode(character_description, convert_to_numpy=True)
        return core_vector
    except Exception as e:
        print(f"生成角色 {character_name} 的核心向量失败: {e}")
        return None


# ==================== NTD 升级：章节状态向量计算 ====================

def _compute_chapter_state_vector(
    narrative_state: NarrativeState,
    prev_state: Optional[ChapterNode] = None,
    alpha: float = 0.7
) -> Optional[List[float]]:
    """
    计算章节整体状态向量（NTD 升级）
    
    将 physique + psyche + environment 拼接成描述文本，然后向量化。
    使用 EMA 平滑：current_vector = 0.7 * new_vector + 0.3 * prev_vector
    
    Args:
        narrative_state: 当前叙事状态
        prev_state: 前一章的节点（用于 EMA 平滑）
        alpha: EMA 平滑系数（默认 0.7）
    
    Returns:
        章节状态向量（384维列表）或 None
    """
    if not NUMPY_AVAILABLE or np is None:
        return None
    
    embedding_model = get_embedding_model()
    if embedding_model is None:
        return None
    
    # 拼接状态描述文本
    state_parts = []
    
    # 收集所有角色的 physique 和 psyche
    for char_name, char_state in narrative_state.characters.items():
        physique = char_state.get("physique", "").strip()
        psyche = char_state.get("psyche", "").strip()
        if physique:
            state_parts.append(f"{char_name}的生理状态：{physique}")
        if psyche:
            state_parts.append(f"{char_name}的心理状态：{psyche}")
    
    # 添加环境氛围
    if narrative_state.environment:
        state_parts.append(f"环境氛围：{narrative_state.environment}")
    
    # 如果没有状态描述，返回 None
    if not state_parts:
        return None
    
    # 拼接成完整描述
    state_text = "。".join(state_parts)
    
    try:
        # 生成当前状态的向量
        new_vector = embedding_model.encode(state_text, convert_to_numpy=True)
        
        # EMA 平滑：如果有前一章的状态向量，进行平滑
        if prev_state and prev_state.state_vector is not None:
            prev_vector = prev_state.state_vector
            # 转换为 numpy 数组（如果是列表）
            if isinstance(prev_vector, list):
                prev_vector = np.array(prev_vector)
            
            # EMA 平滑: current_vector = 0.7 * new_vector + 0.3 * prev_vector
            smoothed_vector = alpha * new_vector + (1 - alpha) * prev_vector
            return smoothed_vector.tolist()
        else:
            # 没有历史向量，直接使用当前向量
            return new_vector.tolist()
    
    except Exception as e:
        print(f"计算章节状态向量失败: {e}")
        return None
