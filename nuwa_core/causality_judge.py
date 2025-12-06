"""
向量因果判官模块 (Vector-Based Causality Judge Module)

在太一引擎时代，这个模块用于做“剧情防崩”；在女娲内核接管后，
它更多被视为 Chatbot 的“事实与人设防崩”防线：

- 纵向：当前回复是否违背已经记录的事实（fact_book / 历史记忆）；
- 横向：当前回复是否违背既定人设（Profile / Persona）；
- 向量：通过余弦相似度评估 OOC 程度。

核心功能：
- scan_conflicts: 扫描当前节点与历史事实和角色设定的人设冲突
- calculate_ooc_score: 基于余弦相似度计算 OOC 分数
- ConflictReport: 冲突报告数据结构
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .state_machine import ChapterNode, NarrativeState, get_embedding_model, get_character_core_vector

# 导入向量计算相关库
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class ConflictLevel(Enum):
    """冲突级别"""
    CRITICAL = "critical"  # 严重错误（Bug）
    WARNING = "warning"    # 风险警告


@dataclass
class ConflictReport:
    """
    冲突报告

    在 Chatbot / AI 伴侣场景下，可理解为“逻辑风控报告”：
    - critical_errors: 事实错误或严重 OOC（人设崩坏等，建议直接打回）
    - warnings: 轻量级风险（语气略违和、能量跃迁过大但尚可兜住等）
    - ooc_scores: 各角色/人格的向量一致性分数（越低越偏离人设）
    """
    critical_errors: List[Dict[str, Any]] = field(default_factory=list)  # 严重错误列表
    warnings: List[Dict[str, Any]] = field(default_factory=list)  # 警告列表
    ooc_scores: Dict[str, float] = field(default_factory=dict)  # OOC 分数（新增）
    # 格式: { "亚瑟": 0.35 }  # 余弦相似度分数（< 0.4 表示 OOC）
    
    def has_conflicts(self) -> bool:
        """是否有冲突"""
        return len(self.critical_errors) > 0 or len(self.warnings) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "critical_errors": self.critical_errors,
            "warnings": self.warnings,
            "ooc_scores": self.ooc_scores,
            "total_critical": len(self.critical_errors),
            "total_warnings": len(self.warnings),
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def scan_conflicts(
    current_node: ChapterNode,
    vector_db=None,
    character_table: Optional[List[Dict[str, str]]] = None,
    project_name: Optional[str] = None,
    # 在 Chatbot 场景下，可显式传入 fact_book（事实账本），用于纵向事实防崩
    fact_book: Optional[Dict[str, Any]] = None,
    # 是否启用“物品/装备一致性检查”（主要用于重度 RP/世界观玩法）
    rp_mode: bool = False,
    selected_model: str = "lm_studio",
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    gemini_base_url: Optional[str] = None,
) -> ConflictReport:
    """
    扫描当前节点与历史和角色设定的冲突（基于语义）
    
    实现三种校验：
    1. 纵向校验 (History / Fact Check): 检查与历史事实 / fact_book 的冲突
    2. 横向校验 (Profile Check): 检查与角色设定的冲突
    3. 状态延续性检查 (State Continuity Check): 检查角色状态的语义延续性
    4. 物品一致性检查 (Equipment Consistency Check): 检查物品使用的逻辑一致性
    
    Args:
        current_node: 当前章节节点
        vector_db: 向量数据库（LanceDB）连接，用于检索历史状态
        character_table: 角色表，格式为 [{"name": "角色名", "description": "描述"}, ...]
        project_name: 项目名称，用于检索记忆
        selected_model: 模型类型（用于语义冲突检测）
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        ConflictReport: 包含所有冲突和警告的报告
    """
    report = ConflictReport()
    
    if not current_node:
        return report
    
    # 1. 状态延续性检查：检查角色状态的语义延续性
    if current_node.chapter_id > 1:
        continuity_conflicts = _check_state_continuity(
            current_node=current_node,
            project_name=project_name,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
        )
        report.critical_errors.extend(continuity_conflicts["critical"])
        report.warnings.extend(continuity_conflicts["warnings"])
    
    # 2. 物品一致性检查：在 Chatbot 中默认关闭，只在 rp_mode=True 的沉浸式 RP 场景启用
    if rp_mode:
        equipment_conflicts = _check_equipment_consistency(
            current_node=current_node,
            project_name=project_name,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
        )
        report.critical_errors.extend(equipment_conflicts["critical"])
        report.warnings.extend(equipment_conflicts["warnings"])
    
    # 3. 纵向校验：检查与历史事实 / fact_book 的冲突
    # Chatbot 场景优先使用 fact_book；如果未提供，则退回太一引擎旧逻辑
    if (fact_book and isinstance(fact_book, dict)) or (vector_db and project_name):
        history_conflicts = _check_history_conflicts(
            current_node=current_node,
            vector_db=vector_db,
            project_name=project_name,
            fact_book=fact_book,
        )
        report.critical_errors.extend(history_conflicts["critical"])
        report.warnings.extend(history_conflicts["warnings"])
    
    # 4. 横向校验：检查与角色设定的冲突
    if character_table:
        profile_conflicts = _check_profile_conflicts(
            current_node=current_node,
            character_table=character_table,
        )
        report.critical_errors.extend(profile_conflicts["critical"])
        report.warnings.extend(profile_conflicts["warnings"])
    
    # 5. 向量 OOC 检测：基于余弦相似度计算 OOC 分数（事实防崩中的“人设一致性层”）
    if character_table and NUMPY_AVAILABLE and np is not None:
        ooc_scores = calculate_ooc_scores(
            current_node=current_node,
            character_table=character_table,
        )
        report.ooc_scores = ooc_scores

        # 当向量一致性过低时，直接落入逻辑风控，标记为严重/轻微 OOC
        for char_name, score in ooc_scores.items():
            if score < 0.4:
                report.critical_errors.append({
                    "type": "ooc_vector",
                    "level": ConflictLevel.CRITICAL.value,
                    "character": char_name,
                    "ooc_score": round(score, 3),
                    "message": f"角色「{char_name}」人设崩塌（OOC）：当前行为与角色设定的余弦相似度仅为 {score:.3f}（阈值 0.4），数学上判定为严重偏离人设",
                })
            elif score < 0.6:
                report.warnings.append({
                    "type": "ooc_vector",
                    "level": ConflictLevel.WARNING.value,
                    "character": char_name,
                    "ooc_score": round(score, 3),
                    "message": f"角色「{char_name}」行为可能偏离人设：余弦相似度为 {score:.3f}（建议 > 0.6）",
                })
    else:
        # 调试信息：为什么 OOC 检测没有运行
        if not character_table:
            print("⚠️ OOC 检测未运行：character_table 为空")
        elif not NUMPY_AVAILABLE:
            print("⚠️ OOC 检测未运行：NUMPY_AVAILABLE 为 False")
        elif np is None:
            print("⚠️ OOC 检测未运行：np 为 None")
    
    # 6. NTD 升级：计算叙事能量（能量函数）
    if NUMPY_AVAILABLE and np is not None and current_node.state_vector is not None:
        # 加载前一章节点（用于计算一致性势能）
        prev_node = None
        if current_node.chapter_id > 1 and project_name:
            try:
                import os
                nodes_dir = os.path.join("data", project_name or "", "nodes")
                prev_chapter_id = current_node.chapter_id - 1
                prev_node_path = os.path.join(nodes_dir, f"{prev_chapter_id}.json")
                if os.path.exists(prev_node_path):
                    with open(prev_node_path, 'r', encoding='utf-8') as f:
                        prev_data = json.load(f)
                        prev_node = ChapterNode.from_dict(prev_data.get("node", {}))
            except Exception as e:
                print(f"加载前一章节点失败（用于能量计算）: {e}")
        
        # 计算叙事能量
        energy, energy_breakdown = calculate_narrative_energy(
            current_node=current_node,
            prev_node=prev_node,
            target_vector=None,  # 可以传入大纲向量（如果有）
        )
        
        # 能量阈值（可调）
        ENERGY_THRESHOLD = 0.8  # 如果能量 > 0.8，判定为高风险
        
        if energy > ENERGY_THRESHOLD:
            report.warnings.append({
                "type": "narrative_energy",
                "level": ConflictLevel.WARNING.value,
                "energy": round(energy, 3),
                "energy_breakdown": energy_breakdown,
                "message": f"⚠️ 高能预警（逻辑崩坏风险）：叙事能量为 {energy:.3f}（阈值 {ENERGY_THRESHOLD}）。状态突变过大，可能导致逻辑不一致。",
            })
    
    return report


def _check_state_continuity(
    current_node: ChapterNode,
    project_name: Optional[str],
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    状态延续性检查：检查角色状态的语义延续性
    
    如果上一章 physique 是 "双腿骨折"，而本章正文写 "他飞起一脚"，
    判官应识别出语义冲突。
    
    Args:
        current_node: 当前章节节点
        project_name: 项目名称
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        包含 critical 和 warnings 的字典
    """
    conflicts = {
        "critical": [],
        "warnings": [],
    }
    
    if not current_node.narrative_state or not current_node.narrative_state.characters:
        return conflicts
    
    # 加载前一章的状态
    try:
        import os
        nodes_dir = os.path.join("data", project_name or "", "nodes")
        prev_chapter_id = current_node.chapter_id - 1
        
        if prev_chapter_id < 1:
            return conflicts
        
        prev_node_path = os.path.join(nodes_dir, f"{prev_chapter_id}.json")
        if not os.path.exists(prev_node_path):
            return conflicts
        
        with open(prev_node_path, 'r', encoding='utf-8') as f:
            prev_data = json.load(f)
            prev_node = ChapterNode.from_dict(prev_data.get("node", {}))
        
        if not prev_node.narrative_state:
            return conflicts
        
        prev_narrative = prev_node.narrative_state
        current_narrative = current_node.narrative_state
        
        # 对每个角色进行状态延续性检查
        for char_name, current_char_state in current_narrative.characters.items():
            if char_name not in prev_narrative.characters:
                continue
            
            prev_char_state = prev_narrative.characters[char_name]
            
            # 检查生理状态的延续性
            prev_physique = prev_char_state.get("physique", "").strip()
            current_physique = current_char_state.get("physique", "").strip()
            current_text = current_node.text_content
            
            if prev_physique and current_text:
                # 使用 LLM 检查语义冲突
                conflict_detected = _check_semantic_conflict_with_llm(
                    prev_state=prev_physique,
                    current_text=current_text,
                    char_name=char_name,
                    selected_model=selected_model,
                    base_url=base_url,
                    model_name=model_name,
                    api_key=api_key,
                    gemini_base_url=gemini_base_url,
                )
                
                if conflict_detected:
                    conflicts["critical"].append({
                        "type": "state_continuity",
                        "level": ConflictLevel.CRITICAL.value,
                        "character": char_name,
                        "prev_physique": prev_physique,
                        "current_text_snippet": current_text[:200],
                        "message": f"角色「{char_name}」的生理状态与正文描述冲突：上一章状态为「{prev_physique}」，但正文中出现了与之矛盾的行为",
                    })
        
    except Exception as e:
        print(f"状态延续性检查失败: {e}")
        import traceback
        print(traceback.format_exc())
    
    return conflicts


def _check_equipment_consistency(
    current_node: ChapterNode,
    project_name: Optional[str],
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    物品一致性检查：检查物品使用的逻辑一致性
    
    如果 equipment 里没有 "枪"，正文却写 "他拔枪射击"，触发警告。
    
    Args:
        current_node: 当前章节节点
        project_name: 项目名称
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        包含 critical 和 warnings 的字典
    """
    conflicts = {
        "critical": [],
        "warnings": [],
    }
    
    if not current_node.narrative_state or not current_node.narrative_state.characters:
        return conflicts
    
    narrative_state = current_node.narrative_state
    current_text = current_node.text_content
    
    if not current_text:
        return conflicts
    
    # 只检查在正文中实际出现的角色，避免无用的LLM调用
    # 快速检查：如果角色名不在正文中出现，直接跳过
    for char_name, char_state in narrative_state.characters.items():
        # 快速过滤：如果角色名不在正文中出现，跳过（避免无用的LLM调用）
        if char_name not in current_text:
            continue
        
        equipment = char_state.get("equipment", [])
        equipment_text = ", ".join(equipment) if equipment else "无"
        
        # 使用 LLM 检查物品使用是否一致
        inconsistency_detected = _check_equipment_inconsistency_with_llm(
            equipment_list=equipment_text,
            current_text=current_text,
            char_name=char_name,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
        )
        
        if inconsistency_detected:
            # 尝试提取具体使用的物品（通过 LLM）
            used_item = _extract_used_item_from_text(
                equipment_list=equipment_text,
                current_text=current_text[:1000],
                char_name=char_name,
                selected_model=selected_model,
                base_url=base_url,
                model_name=model_name,
                api_key=api_key,
                gemini_base_url=gemini_base_url,
            )
            
            if used_item:
                message = f"角色「{char_name}」使用了未在装备列表中的物品：{used_item}（装备列表：{equipment_text}）"
            else:
                message = f"角色「{char_name}」使用了未在装备列表中的物品（装备列表：{equipment_text}）"
            
            conflicts["critical"].append({
                "type": "equipment_consistency",
                "level": ConflictLevel.CRITICAL.value,
                "character": char_name,
                "equipment_list": equipment_text,
                "current_text_snippet": current_text[:200],
                "message": message,
            })
    
    return conflicts


def _check_semantic_conflict_with_llm(
    prev_state: str,
    current_text: str,
    char_name: str,
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> bool:
    """
    使用 LLM 检查语义冲突
    
    Args:
        prev_state: 前一章的状态描述
        current_text: 当前章节正文
        char_name: 角色名
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        是否检测到冲突
    """
    if not prev_state or not current_text:
        return False
    
    system_prompt = """你是一个专业的小说逻辑检查器。你的任务是检查角色状态的语义延续性。

对比【历史状态描述】和【新生成正文】，寻找逻辑矛盾点。

如果发现明显的语义冲突（例如：历史状态是"双腿骨折"，但正文中写"他飞起一脚"），请回答"冲突"。
如果没有明显冲突，请回答"无冲突"。

只回答"冲突"或"无冲突"，不要添加其他文字。"""

    user_prompt = f"""角色名：{char_name}

【历史状态描述】
{prev_state}

【新生成正文】
{current_text[:1000]}

请判断是否存在语义冲突。"""

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
            return False
        
        if selected_model == "gemini":
            if not api_key or not model_name:
                return False
            
            success, result = generate_content_gemini(
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=gemini_base_url,
                max_output_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                return "冲突" in result.strip()
        else:
            if not base_url or not model_name:
                return False
            
            success, result = generate_content_lm_studio(
                base_url=base_url,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                return "冲突" in result.strip()
    except Exception as e:
        print(f"语义冲突检查失败: {e}")
        return False
    
    return False


def _check_equipment_inconsistency_with_llm(
    equipment_list: str,
    current_text: str,
    char_name: str,
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> bool:
    """
    使用 LLM 检查物品使用是否一致
    
    Args:
        equipment_list: 装备列表（字符串）
        current_text: 当前章节正文
        char_name: 角色名
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        是否检测到不一致
    """
    if not current_text:
        return False
    
    system_prompt = """你是一个专业的小说逻辑检查器。你的任务是检查角色物品使用的逻辑一致性。

重要规则：
1. **语义匹配**：装备列表中的物品和正文中使用的物品应该进行语义匹配，而不是严格的字符串匹配。
   - 例如：装备列表有"护照（日本签证）"，正文中使用"护照"或"他的护照" → 应该判断为"一致"（是同一个物品）
   - 例如：装备列表有"手机"，正文中使用"智能手机"或"他的手机" → 应该判断为"一致"
   - 例如：装备列表有"断裂的家徽剑"，正文中使用"剑"或"家徽剑" → 应该判断为"一致"（是同一个物品）

2. **只检查明确使用**：只检查角色**明确持有或使用**的物品，而不是正文中**仅仅提到**的物品。
   - 如果正文中只是描述环境中的物品、其他角色的物品、或者只是提到物品名称但没有明确表示该角色持有或使用，应该判断为"一致"。

3. **获取物品的处理**：
   - **关键**：如果正文中描述角色"获取"、"获得"、"捡到"、"找到"、"购买"、"收到"某个物品，这表示物品是**新获得的**，不应该判断为"不一致"。
   - 装备列表记录的是**当前持有的物品**，如果正文中描述角色获取了新物品，这是正常的剧情发展，应该判断为"一致"。
   - 例如：装备列表："护照"，正文："他捡到了一把钥匙" → "一致"（获取新物品，不是使用未列出的物品）
   - 例如：装备列表："护照"，正文："他收到了一个包裹" → "一致"（获取新物品）

4. **原本就有的物品**：
   - 如果正文中描述角色使用某个物品，但该物品在装备列表中没有，需要判断：
     * 如果正文中明确表示这是角色"原本就有"、"一直带着"、"随身携带"的物品，且装备列表为空或很少，这可能表示装备列表不完整，应该判断为"一致"（避免误报）。
     * 如果正文中描述角色使用某个物品，且该物品在语义上与装备列表中的物品不匹配，但正文中没有明确表示这是新获取的，才判断为"不一致"。

5. **不一致的判断标准**：只有当正文中明确表示该角色持有、使用、操作某个物品，且该物品在语义上与装备列表中的任何物品都不匹配，且不是"获取新物品"的情况时，才判断为"不一致"。

6. **空列表处理**：
   - 如果装备列表为空（"无"），但正文中明确表示角色持有或使用了某个物品，需要区分：
     * 如果是"获取"新物品 → "一致"（正常剧情）
     * 如果是"使用"物品但没有获取描述 → "不一致"（可能遗漏了装备列表更新）

7. **物品描述变体**：装备列表中可能包含物品的描述性信息（如"护照（日本签证）"、"断裂的家徽剑"），正文中可能只使用核心物品名称（如"护照"、"剑"），这应该被认为是匹配的。

示例：
- 装备列表："护照（日本签证）"，正文："他拿出护照" → "一致"（语义匹配）
- 装备列表："护照（日本签证）"，正文："他检查了护照上的签证" → "一致"（语义匹配）
- 装备列表："无"，正文："他看到了桌上的枪" → "一致"（只是看到，没有持有）
- 装备列表："无"，正文："他拔枪射击" → "不一致"（明确使用，且没有获取描述）
- 装备列表："护照"，正文："他拔枪射击" → "不一致"（明确使用但不在列表中，且语义不匹配）
- 装备列表："枪"，正文："他拔枪射击" → "一致"（装备列表中有）
- 装备列表："断裂的家徽剑"，正文："他挥舞着剑" → "一致"（语义匹配，是同一个物品）
- 装备列表："护照（日本签证）"，正文："他拿出手机" → "不一致"（明确使用但不在列表中，且语义不匹配）
- **装备列表："护照"，正文："他捡到了一把钥匙" → "一致"（获取新物品，不是使用未列出的物品）**
- **装备列表："护照"，正文："他找到了一个钱包" → "一致"（获取新物品）**
- **装备列表："护照"，正文："他收到了一个包裹" → "一致"（获取新物品）**
- **装备列表："无"，正文："他捡起地上的枪" → "一致"（获取新物品，正常剧情）**
- **装备列表："护照"，正文："他一直带着的手机响了" → "一致"（原本就有，装备列表可能不完整，避免误报）**

请仔细分析装备列表和正文，进行语义匹配判断。

只回答"不一致"或"一致"，不要添加其他文字。"""

    user_prompt = f"""角色名：{char_name}

【装备列表】
{equipment_list}

【新生成正文】
{current_text[:1000]}

请仔细判断：正文中是否明确表示该角色持有或使用了未在装备列表中的物品？
注意：请进行语义匹配，而不是严格的字符串匹配。例如"护照（日本签证）"和"护照"应该被认为是同一个物品。"""

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
            return False
        
        if selected_model == "gemini":
            if not api_key or not model_name:
                return False
            
            success, result = generate_content_gemini(
                api_key=api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                base_url=gemini_base_url,
                max_output_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                return "不一致" in result.strip()
        else:
            if not base_url or not model_name:
                return False
            
            success, result = generate_content_lm_studio(
                base_url=base_url,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                return "不一致" in result.strip()
    except Exception as e:
        print(f"物品一致性检查失败: {e}")
        return False
    
    return False


def _extract_used_item_from_text(
    equipment_list: str,
    current_text: str,
    char_name: str,
    selected_model: str,
    base_url: Optional[str],
    model_name: Optional[str],
    api_key: Optional[str],
    gemini_base_url: Optional[str],
) -> Optional[str]:
    """
    从正文中提取角色使用的物品名称（用于更详细的错误消息）
    
    Args:
        equipment_list: 装备列表（字符串）
        current_text: 当前章节正文
        char_name: 角色名
        selected_model: 模型类型
        base_url: LM Studio base_url
        model_name: 模型名称
        api_key: Gemini API Key
        gemini_base_url: Gemini base_url
    
    Returns:
        使用的物品名称，如果无法提取则返回 None
    """
    if not current_text:
        return None
    
    system_prompt = """你是一个专业的小说分析助手。你的任务是从正文中提取角色明确使用的物品名称。

请仔细分析正文，找出角色明确持有、使用、操作的物品名称。
如果找到了，只返回物品名称（不要添加其他文字）。
如果没有找到或无法确定，返回"无法确定"。

只返回物品名称或"无法确定"，不要添加其他文字。"""

    user_prompt = f"""角色名：{char_name}

【装备列表】
{equipment_list}

【正文片段】
{current_text[:800]}

请提取该角色在正文中明确使用的物品名称（该物品不在装备列表中）。"""

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
                max_output_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                result = result.strip()
                if result and result != "无法确定":
                    return result
        else:
            if not base_url or not model_name:
                return None
            
            success, result = generate_content_lm_studio(
                base_url=base_url,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=50,
                temperature=0.1,
                stream=False,
            )
            if success and result:
                result = result.strip()
                if result and result != "无法确定":
                    return result
    except Exception as e:
        print(f"提取物品名称失败: {e}")
        return None
    
    return None


def _check_history_conflicts(
    current_node: ChapterNode,
    vector_db: Any,
    project_name: str,
    fact_book: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    纵向校验：检查与历史事实 / fact_book 的冲突

    Chatbot 场景下优先视为“事实账本防崩”层：
    - 将当前回复视为一个新的“事实声明”
    - 与 fact_book 中的已知真值做简单字符串/模式匹配，发现明显自相矛盾的说法

    在未提供 fact_book 时，会退回太一引擎时代的剧情标志冲突检查逻辑，
    以保持对旧小说项目的兼容性。

    Args:
        current_node: 当前章节节点（在 Chatbot 中可视为“当前轮对话节点”）
        vector_db: 向量数据库连接（兼容参数，当前实现不依赖）
        project_name: 项目名称
        fact_book: 事实账本（如 {"user_name": "十二", "user_location": "广东"}）

    Returns:
        包含 critical 和 warnings 的字典
    """
    conflicts: Dict[str, List[Dict[str, Any]]] = {
        "critical": [],
        "warnings": [],
    }

    reply_text = (current_node.text_content or "").strip() if current_node else ""

    # ========== 优先分支：基于 fact_book 的事实防崩 ==========
    if fact_book and isinstance(fact_book, dict) and reply_text:
        for key, value in fact_book.items():
            if value is None:
                continue
            # 统一转为字符串，去掉多余空白
            str_value = str(value).strip()
            if not str_value:
                continue

            conflict_info = _detect_fact_conflict(
                fact_key=str(key),
                fact_value=str_value,
                reply_text=reply_text,
            )
            if not conflict_info:
                continue

            conflicts["critical"].append({
                "type": "fact_conflict",
                "level": ConflictLevel.CRITICAL.value,
                "fact_key": key,
                "fact_value": str_value,
                "evidence": conflict_info.get("evidence", ""),
                "message": conflict_info["message"],
            })

        return conflicts

    # ========== 兼容分支：保留原有“剧情标志 vs 历史记忆”逻辑 ==========
    if not current_node.narrative_state or not current_node.narrative_state.plot_flags:
        return conflicts

    try:
        # 尝试导入 memory_engine
        from memory_engine import MemoryEngine, get_memory_engine

        # 获取记忆引擎
        memory_engine = get_memory_engine(project_name=project_name)
        if not memory_engine:
            return conflicts

        # 对每个剧情标志进行检索
        for flag in current_node.narrative_state.plot_flags:
            if not flag or len(flag.strip()) < 2:
                continue

            # 构建查询：查找与当前标志冲突的历史记录
            query_text = f"{flag} 冲突 矛盾 不一致"

            try:
                success, results = memory_engine.search_memory(
                    query_text=query_text,
                    top_k=5,
                    novel_name=project_name,
                    use_summary=True,
                    enhance_query=False,
                    current_chapter_id=current_node.chapter_id,
                )

                if success and results:
                    # 检查结果中是否有冲突
                    for result in results:
                        result_text = result.get("text", "") or result.get("summary", "")
                        result_chapter_id = result.get("chapter_id", 0)

                        # 简单的冲突检测：检查是否包含相反或矛盾的描述
                        if _is_conflicting(flag, result_text):
                            conflicts["critical"].append({
                                "type": "history_conflict",
                                "level": ConflictLevel.CRITICAL.value,
                                "current_flag": flag,
                                "conflicting_text": result_text[:200],
                                "conflicting_chapter_id": result_chapter_id,
                                "message": f"剧情标志「{flag}」与第 {result_chapter_id} 章的历史记录冲突",
                            })
            except Exception as e:
                print(f"历史冲突检查失败: {e}")
                continue

    except ImportError:
        # memory_engine 不可用
        pass
    except Exception as e:
        print(f"历史冲突检查异常: {e}")

    return conflicts


def _check_profile_conflicts(
    current_node: ChapterNode,
    character_table: List[Dict[str, str]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    横向校验：检查与角色设定的冲突
    
    拿当前的 character_states 去比对 character_table。
    如果行为违背人设核心（如"懦弱者突然杀人"且无铺垫），生成警告。
    
    Args:
        current_node: 当前章节节点
        character_table: 角色表
    
    Returns:
        包含 critical 和 warnings 的字典
    """
    conflicts = {
        "critical": [],
        "warnings": [],
    }
    
    if not current_node.narrative_state or not current_node.narrative_state.characters or not character_table:
        return conflicts
    
    # 构建角色设定字典
    character_profiles = {}
    for char in character_table:
        char_name = char.get("name", "").strip()
        char_desc = char.get("description", "").strip()
        if char_name:
            character_profiles[char_name] = char_desc
    
    # 检查每个角色的状态是否与设定冲突
    narrative_state = current_node.narrative_state
    for char_name, char_state in narrative_state.characters.items():
        if char_name not in character_profiles:
            continue
        
        profile = character_profiles[char_name].lower()
        psyche = char_state.get("psyche", "").lower()
        focus = char_state.get("focus", "").lower()
        
        # 检查心理状态/行动元是否与角色设定冲突
        if psyche or focus:
            # 简单的关键词匹配检查
            conflict_keywords = _detect_profile_conflict(profile, psyche, focus)
            
            if conflict_keywords:
                # 检查是否有铺垫（通过检查前一章的状态）
                has_setup = False  # 这里可以扩展，检查是否有合理的铺垫
                
                if has_setup:
                    # 有铺垫，只是警告
                    conflicts["warnings"].append({
                        "type": "profile_conflict",
                        "level": ConflictLevel.WARNING.value,
                        "character": char_name,
                        "profile": profile[:100],
                        "current_state": f"心理: {psyche}, 行动元: {focus}",
                        "conflict_keywords": conflict_keywords,
                        "message": f"角色「{char_name}」的行为可能与角色设定存在偏差，但可能有合理铺垫",
                    })
                else:
                    # 无铺垫，严重错误
                    conflicts["critical"].append({
                        "type": "profile_conflict",
                        "level": ConflictLevel.CRITICAL.value,
                        "character": char_name,
                        "profile": profile[:100],
                        "current_state": f"心理: {psyche}, 行动元: {focus}",
                        "conflict_keywords": conflict_keywords,
                        "message": f"角色「{char_name}」的行为违背角色设定核心，且无合理铺垫（OOC）",
                    })
    
    return conflicts


def _is_conflicting(flag: str, history_text: str) -> bool:
    """
    检查剧情标志是否与历史文本冲突
    
    Args:
        flag: 当前剧情标志
        history_text: 历史文本
    
    Returns:
        是否冲突
    """
    if not flag or not history_text:
        return False
    
    flag_lower = flag.lower()
    text_lower = history_text.lower()
    
    # 定义一些冲突模式
    conflict_patterns = {
        "已死": ["不死", "复活", "活着", "未死"],
        "死亡": ["不死", "复活", "活着", "未死"],
        "失去": ["拥有", "获得", "得到"],
        "破坏": ["完好", "修复", "重建"],
        "失败": ["成功", "胜利", "完成"],
        "离开": ["到达", "在", "位于"],
    }
    
    # 检查是否有冲突模式
    for key, opposites in conflict_patterns.items():
        if key in flag_lower:
            for opposite in opposites:
                if opposite in text_lower:
                    return True
    
    return False


def _detect_fact_conflict(
    fact_key: str,
    fact_value: str,
    reply_text: str,
) -> Optional[Dict[str, str]]:
    """
    检测当前回复是否与 fact_book 中的某条事实明显矛盾（轻量级启发式规则）。

    设计目标：
    - 高置信度拦截“自我否定”或“明显改口”的情况；
    - 使用简单字符串/正则，不引入额外 NLP 依赖；
    - 尽量避免过度敏感（宁可少报也不要乱报）。

    返回:
        包含 message 和 evidence 的字典，如果未发现冲突则返回 None
    """
    if not fact_key or not fact_value or not reply_text:
        return None

    text = reply_text
    value = fact_value

    # 1. 直接否定模式（“不是X / 不在X / 没在X”）——适用于任意事实类型
    neg_patterns = [
        f"不是{re.escape(value)}",
        f"不在{re.escape(value)}",
        f"没在{re.escape(value)}",
        f"并非{re.escape(value)}",
    ]
    for p in neg_patterns:
        if p in text:
            return {
                "message": f"模型在回复中显式否定已记录事实「{fact_key}={value}」，存在自相矛盾的风险。",
                "evidence": p,
            }

    key_lower = fact_key.lower()

    # 2. 用户姓名类事实：如 user_name / 用户名 / 名字 等
    if (
        "name" in key_lower
        or "昵称" in fact_key
        or "名字" in fact_key
        or "称呼" in fact_key
    ):
        # 匹配诸如“你叫XX”“你名字是XX”“我记得你叫XX”之类的说法
        name_patterns = [
            r"你叫([^\s，。,！!？?]+)",
            r"你的名字是([^\s，。,！!？?]+)",
            r"我记得你叫([^\s，。,！!？?]+)",
        ]
        for pat in name_patterns:
            m = re.search(pat, text)
            if m:
                mentioned = m.group(1).strip()
                if mentioned and mentioned != value:
                    return {
                        "message": f"用户姓名在 fact_book 中记录为「{value}」，但当前回复中称呼为「{mentioned}」，疑似自相矛盾。",
                        "evidence": m.group(0),
                    }
        return None

    # 3. 位置/城市类事实：如 location / city / 省 / 城市 / 地区 等
    if (
        "location" in key_lower
        or "city" in key_lower
        or "城市" in fact_key
        or "地区" in fact_key
        or "省" in fact_key
    ):
        # 简单匹配“在XXX”这种句式，排除与已知 value 完全一致的情况
        # 例如：fact_book 中为“广东”，但回复说“你现在在上海”
        loc_pattern = r"在([^\s，。,！!？?]+)"
        m = re.search(loc_pattern, text)
        if m:
            loc = m.group(1).strip()
            if loc and loc != value and value not in text:
                return {
                    "message": f"用户常驻地点在 fact_book 中记录为「{value}」，但当前回复中提到「{loc}」，可能与既有事实不一致。",
                    "evidence": m.group(0),
                }
        return None

    # 4. 其他键：当前仅做保守处理，不主动报冲突（避免误伤）
    return None


def _detect_profile_conflict(profile: str, psyche: str, focus: str) -> List[str]:
    """
    检测角色状态是否与设定冲突
    
    Args:
        profile: 角色设定描述
        psyche: 当前心理状态
        focus: 当前行动元
    
    Returns:
        冲突关键词列表
    """
    conflicts = []
    
    # 定义一些冲突模式
    conflict_rules = [
        {
            "profile_keywords": ["懦弱", "胆小", "怯懦"],
            "state_keywords": ["愤怒", "杀人", "攻击", "暴力"],
            "conflict": "懦弱者突然暴力",
        },
        {
            "profile_keywords": ["善良", "仁慈", "温和"],
            "state_keywords": ["残忍", "杀戮", "无情"],
            "conflict": "善良者突然残忍",
        },
        {
            "profile_keywords": ["冷静", "理智", "沉着"],
            "state_keywords": ["崩溃", "失控", "疯狂"],
            "conflict": "冷静者突然失控",
        },
    ]
    
    state_text = f"{psyche} {focus}".lower()
    
    for rule in conflict_rules:
        profile_match = any(kw in profile for kw in rule["profile_keywords"])
        state_match = any(kw in state_text for kw in rule["state_keywords"])
        
        if profile_match and state_match:
            conflicts.append(rule["conflict"])
    
    return conflicts


# ==================== 向量 OOC 检测 ====================

def calculate_ooc_scores(
    current_node: ChapterNode,
    character_table: List[Dict[str, str]],
) -> Dict[str, float]:
    """
    批量计算所有角色的 OOC 分数（基于余弦相似度）
    
    Args:
        current_node: 当前章节节点
        character_table: 角色表，格式为 [{"name": "角色名", "description": "描述"}, ...]
    
    Returns:
        OOC 分数字典，格式为 {角色名: 余弦相似度分数}
        - 分数 < 0.4: 严重 OOC
        - 分数 < 0.6: 警告
        - 分数 >= 0.6: 正常
    """
    ooc_scores = {}
    
    if not NUMPY_AVAILABLE or np is None:
        return ooc_scores
    
    if not current_node.narrative_state or not current_node.narrative_state.characters:
        return ooc_scores
    
    # 获取 Embedding 模型
    embedding_model = get_embedding_model()
    if embedding_model is None:
        print("⚠️ OOC 检测：get_embedding_model() 返回 None（embedding 模型未加载）")
        return ooc_scores
    
    # 构建角色设定字典（只检测 character_table 中定义的角色）
    character_profiles = {}
    for char in character_table:
        char_name = char.get("name", "").strip()
        char_desc = char.get("description", "").strip()
        if char_name:
            if not char_desc:
                print(f"⚠️ OOC 检测：角色 {char_name} 的描述为空，跳过该角色的 OOC 检测")
            else:
                character_profiles[char_name] = char_desc
    
    if not character_profiles:
        print(f"⚠️ OOC 检测：character_profiles 为空（character_table 长度：{len(character_table)}，有效角色数：{len(character_profiles)}）")
        return ooc_scores
    
    narrative_state = current_node.narrative_state
    if not narrative_state:
        print("⚠️ OOC 检测：narrative_state 为空")
        return ooc_scores
    
    if not narrative_state.characters:
        print("⚠️ OOC 检测：narrative_state.characters 为空")
        return ooc_scores
    
    print(f"🔍 OOC 检测：开始检测 {len(narrative_state.characters)} 个角色，character_table 中有 {len(character_profiles)} 个角色定义")
    
    # 优先使用 character_vectors（如果存在）
    character_vectors = narrative_state.character_vectors if narrative_state.character_vectors else {}
    
    # 昵称 / 简称解析：尝试将「凛」映射到「三桥凛」等
    def _resolve_character_name(short_name: str) -> Optional[str]:
        """
        将章节中的称呼映射为角色表中的全名。
        
        策略（保守）：
        - 完全匹配优先
        - 否则查找包含关系（如 '凛' 是 '三桥凛' 的子串），且候选唯一时才接受
        """
        if short_name in character_profiles:
            return short_name
        
        candidates = []
        for full_name in character_profiles.keys():
            if not full_name:
                continue
            if short_name in full_name or full_name in short_name:
                candidates.append(full_name)
        
        if len(candidates) == 1:
            resolved = candidates[0]
            print(f"🔁 OOC 检测：将称呼「{short_name}」视为角色「{resolved}」的昵称/简称")
            return resolved
        
        return None
    
    # 只检测在当前章节状态中出现的角色，且这些角色也在 character_table 中（或能通过昵称映射到其中）
    # 这样可以避免遍历所有角色，只检测实际出现的角色
    checked_count = 0
    for char_name, char_state in narrative_state.characters.items():
        resolved_name = _resolve_character_name(char_name)
        if not resolved_name:
            # 如果无法在角色表中找到对应条目，则跳过
            print(f"⚠️ OOC 检测：角色 {char_name} 不在 character_table 中，且无法通过昵称映射，跳过")
            continue
        
        checked_count += 1
        char_desc = character_profiles[resolved_name]
        print(f"🔍 OOC 检测：正在检测角色 {resolved_name}（称呼：{char_name}）...")
        # 获取角色核心向量（人设）
        character_core_vector = get_character_core_vector(
            character_name=resolved_name,
            character_description=char_desc,
            embedding_model=embedding_model,
        )
        
        if character_core_vector is None:
            print(f"⚠️ 无法生成角色 {resolved_name} 的核心向量，跳过 OOC 检测")
            continue
        
        # 获取角色当前状态向量（优先使用 character_vectors）
        current_vector = None
        
        if resolved_name in character_vectors and character_vectors[resolved_name]:
            # 优先使用已计算的 character_vectors
            vector_data = character_vectors[resolved_name]
            if isinstance(vector_data, list) and len(vector_data) > 0:
                current_vector = np.array(vector_data)
            elif isinstance(vector_data, np.ndarray) and len(vector_data) > 0:
                current_vector = vector_data
        
        # 如果 character_vectors 中没有，尝试从当前状态生成
        if current_vector is None:
            physique = char_state.get("physique", "")
            psyche = char_state.get("psyche", "")
            if physique or psyche:
                state_text = f"{physique} {psyche}".strip()
                try:
                    current_vector = embedding_model.encode(state_text, convert_to_numpy=True)
                except Exception as e:
                    print(f"生成角色 {resolved_name} 的状态向量失败: {e}")
                    continue
            else:
                # 如果状态为空，跳过该角色
                print(f"⚠️ 角色 {resolved_name} 的状态为空（physique 和 psyche 都为空），跳过 OOC 检测")
                continue
        
        # 计算余弦相似度
        try:
            dot_product = np.dot(character_core_vector, current_vector)
            norm_core = np.linalg.norm(character_core_vector)
            norm_current = np.linalg.norm(current_vector)
            
            if norm_core > 0 and norm_current > 0:
                cosine_similarity = dot_product / (norm_core * norm_current)
                ooc_scores[resolved_name] = float(cosine_similarity)
                print(f"✅ OOC 检测：角色 {resolved_name} 的 OOC 分数 = {cosine_similarity:.3f}")
            else:
                ooc_scores[resolved_name] = 0.0
                print(f"⚠️ OOC 检测：角色 {resolved_name} 的向量范数为 0，设置 OOC 分数为 0.0")
        except Exception as e:
            print(f"❌ 计算角色 {resolved_name} 的 OOC 分数失败: {e}")
            import traceback
            traceback.print_exc()
            ooc_scores[resolved_name] = 0.0
    
    print(f"🔍 OOC 检测完成：检测了 {checked_count} 个角色，返回 {len(ooc_scores)} 个分数")
    return ooc_scores


# ==================== NTD 升级：叙事能量函数 ====================

def calculate_narrative_energy(
    current_node: ChapterNode,
    prev_node: Optional[ChapterNode] = None,
    target_vector: Optional[List[float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    计算叙事能量（NTD 升级）
    
    能量函数：E = E_consistency + E_target
    
    - E_consistency（一致性势能）：计算 current_node.state_vector 与 prev_node 的余弦距离。
      如果距离过大（突变），能量飙升。
    - E_target（目标势能）：（如果有大纲向量）计算与大纲的距离。
    
    Args:
        current_node: 当前章节节点
        prev_node: 前一章节点（可选）
        target_vector: 目标向量（大纲向量，可选）
    
    Returns:
        (总能量, 能量分解字典)
    """
    if not NUMPY_AVAILABLE or np is None:
        return 0.0, {}
    
    if current_node.state_vector is None:
        return 0.0, {}
    
    energy_breakdown = {}
    total_energy = 0.0
    
    # 转换为 numpy 数组
    current_vector = np.array(current_node.state_vector)
    
    # 1. 一致性势能 E_consistency
    if prev_node and prev_node.state_vector is not None:
        prev_vector = np.array(prev_node.state_vector)
        
        # 计算余弦距离（1 - 余弦相似度）
        dot_product = np.dot(current_vector, prev_vector)
        norm_current = np.linalg.norm(current_vector)
        norm_prev = np.linalg.norm(prev_vector)
        
        if norm_current > 0 and norm_prev > 0:
            cosine_similarity = dot_product / (norm_current * norm_prev)
            cosine_distance = 1.0 - cosine_similarity
            
            # 一致性势能：距离越大，能量越高
            # 使用平方函数，使突变更明显
            e_consistency = cosine_distance ** 2
            energy_breakdown["consistency"] = float(e_consistency)
            total_energy += e_consistency
    else:
        energy_breakdown["consistency"] = 0.0
    
    # 2. 目标势能 E_target
    if target_vector is not None:
        target_vec = np.array(target_vector)
        
        # 计算与目标的余弦距离
        dot_product = np.dot(current_vector, target_vec)
        norm_current = np.linalg.norm(current_vector)
        norm_target = np.linalg.norm(target_vec)
        
        if norm_current > 0 and norm_target > 0:
            cosine_similarity = dot_product / (norm_current * norm_target)
            cosine_distance = 1.0 - cosine_similarity
            
            # 目标势能：距离越大，能量越高
            e_target = cosine_distance ** 2
            energy_breakdown["target"] = float(e_target)
            total_energy += e_target
    else:
        energy_breakdown["target"] = 0.0
    
    return float(total_energy), energy_breakdown
