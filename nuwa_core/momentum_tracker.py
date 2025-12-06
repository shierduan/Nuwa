"""
PID 势能控制器模块 (PID Momentum Controller Module)

原版用于“叙事节奏控制”；在 AI 伴侣 / Chatbot 场景下，
可以近似理解为“对话投入度控制器”：

- emotion_intensity: 基于情绪词密度 + 回复长度的“情感浓度”；
- information_density: 重新诠释为 topic_depth（话题深度 / 新信息点数量）；
- pacing: 重新诠释为 interaction_flow（交互流畅度）。

核心功能：
- calculate_momentum: 分析最近若干轮对话的情绪浓度与话题深度
- PIDController: PID 控制器类，用于调节 temperature 等生成参数
- MomentumReport: 对话势能报告数据结构（包含 PID 控制结果）
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .state_machine import ChapterNode, NarrativeState

# 导入 numpy（用于 PID 计算）
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class PacingLevel(Enum):
    """
    交互流等级（语义化）

    兼容保留旧枚举名，但语义映射到 Chatbot 场景下的对话流：
    - DRAGGING  → DISENGAGED：冷场 / 复读 / 单字回复
    - SMOOTH    → ENGAGED：互相跟进、节奏自然
    - RUSHING   → OVERWHELMING：信息过载 / 一次说太多
    """

    DRAGGING = "DISENGAGED"       # 冷场 / 复读
    SMOOTH = "ENGAGED"            # 流畅 / 自然
    RUSHING = "OVERWHELMING"      # 信息过载 / 刷屏感


@dataclass
class MomentumReport:
    """
    对话势能报告（语义化 + PID 控制）

    在 Chatbot 模式下，可理解为最近几轮对话的“投入度与流畅度体检”：
    - emotion_intensity: 结合情绪词密度与回复长度的情感浓度指标
    - information_density: 近似话题深度 / 新信息点密度（命名兼容旧字段）
    - pacing: 交互流等级（DISENGAGED / ENGAGED / OVERWHELMING）
    """
    tension_description: str = "平缓"  # 对话张力 / 情绪紧绷程度的语义描述
    information_density_description: str = "适中"  # 话题深度 / 信息量的语义描述
    pacing: str = PacingLevel.SMOOTH.value  # 交互流等级（见 PacingLevel 注释）
    suggestions: List[str] = field(default_factory=list)  # 建议列表（语义化）
    
    # 保留数字字段用于兼容（但不再作为主要输出）
    tension: float = 0.0  # 张力值 (0-100) - 仅用于内部计算
    pacing_score: float = 0.0  # 节奏分数
    emotion_intensity: float = 0.0  # 情绪强度
    information_density: float = 0.0  # 信息密度（在 Chatbot 中近似“topic_depth”）
    
    # PID 控制参数（新增）
    target_tension: float = 50.0  # 目标张力（默认 50）
    tension_error: float = 0.0  # 张力误差（目标 - 实际）
    pid_control_signal: float = 0.0  # PID 控制信号
    recommended_temperature: float = 0.7  # 推荐的 Temperature（基于 PID）
    recommended_presence_penalty: float = 0.0  # 推荐的 Presence Penalty（基于 PID）
    
    # 叙事连续性指标（新增）
    continuity_score: float = 1.0  # 前后章节状态向量的余弦相似度（0-1）
    continuity_level: str = "连续"  # 语义化描述（如："连续"、"轻微跳跃"、"严重跳跃"）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tension_description": self.tension_description,
            "information_density_description": self.information_density_description,
            "pacing": self.pacing,
            "suggestions": self.suggestions,
            # 兼容字段
            "tension": self.tension,
            "pacing_score": self.pacing_score,
            "emotion_intensity": self.emotion_intensity,
            "information_density": self.information_density,
            # PID 控制参数
            "target_tension": self.target_tension,
            "tension_error": self.tension_error,
            "pid_control_signal": self.pid_control_signal,
            "recommended_temperature": self.recommended_temperature,
            "recommended_presence_penalty": self.recommended_presence_penalty,
            # 叙事连续性
            "continuity_score": self.continuity_score,
            "continuity_level": self.continuity_level,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def calculate_momentum(recent_nodes: List[ChapterNode]) -> MomentumReport:
    """
    分析最近 3-5 个节点的“情绪强度 / 情感浓度”和“话题深度 / 信息密度”，生成对话势能报告。
    
    Args:
        recent_nodes: 最近的章节节点列表（建议 3-5 个）
    
    Returns:
        MomentumReport: 包含语义化张力和节奏的分析报告
    """
    if not recent_nodes or len(recent_nodes) == 0:
        return MomentumReport()
    
    # 限制分析范围（最多 5 个节点）
    nodes = recent_nodes[-5:] if len(recent_nodes) > 5 else recent_nodes
    
    # 1. 计算情绪强度（用于内部计算）——在 Chatbot 中视为“情感浓度”
    emotion_intensity = _calculate_emotion_intensity(nodes)
    
    # 2. 计算信息密度（用于内部计算）——在 Chatbot 中视为“话题深度”
    information_density = _calculate_information_density(nodes)
    
    # 3. 计算张力（综合情绪强度和信息密度）
    tension = (emotion_intensity * 0.6 + information_density * 0.4)
    
    # 4. 计算节奏
    pacing_score, pacing = _calculate_pacing(nodes)
    
    # 5. 计算叙事连续性（显式前后章余弦相似度）
    continuity_score = 1.0
    continuity_level = "连续"
    if NUMPY_AVAILABLE and np is not None and len(nodes) >= 2:
        prev_node = nodes[-2]
        curr_node = nodes[-1]
        if prev_node.state_vector is not None and curr_node.state_vector is not None:
            try:
                v_prev = np.array(prev_node.state_vector)
                v_curr = np.array(curr_node.state_vector)
                norm_prev = np.linalg.norm(v_prev)
                norm_curr = np.linalg.norm(v_curr)
                if norm_prev > 0 and norm_curr > 0:
                    cosine = float(np.dot(v_prev, v_curr) / (norm_prev * norm_curr))
                    # 数值安全：夹在 [0,1] 内
                    continuity_score = max(0.0, min(1.0, cosine))
                    if continuity_score >= 0.8:
                        continuity_level = "高度连续"
                    elif continuity_score >= 0.6:
                        continuity_level = "基本连续"
                    elif continuity_score >= 0.4:
                        continuity_level = "存在跳跃"
                    else:
                        continuity_level = "严重跳跃"
            except Exception:
                pass
    
    # 6. 生成语义化描述
    tension_description = _describe_tension(tension, nodes)
    information_density_description = _describe_information_density(information_density, nodes)
    
    # 7. 生成建议（语义化）
    suggestions = _generate_semantic_suggestions(
        tension_description=tension_description,
        information_density_description=information_density_description,
        pacing=pacing,
        node_count=len(nodes),
    )
    
    return MomentumReport(
        tension_description=tension_description,
        information_density_description=information_density_description,
        pacing=pacing,
        suggestions=suggestions,
        # 兼容字段
        tension=round(tension, 2),
        pacing_score=round(pacing_score, 2),
        emotion_intensity=round(emotion_intensity, 2),
        information_density=round(information_density, 2),
        continuity_score=round(continuity_score, 3),
        continuity_level=continuity_level,
    )


def _describe_tension(tension: float, nodes: List[ChapterNode]) -> str:
    """
    将张力值转换为语义描述
    
    Args:
        tension: 张力值 (0-100)
        nodes: 章节节点列表（用于上下文分析）
    
    Returns:
        张力描述（如："生死一线"、"闲庭信步"）
    """
    # 分析节点中的语义线索
    semantic_clues = []
    for node in nodes:
        if node.narrative_state:
            for char_name, char_state in node.narrative_state.characters.items():
                physique = char_state.get("physique", "").lower()
                psyche = char_state.get("psyche", "").lower()
                
                # 提取高张力关键词
                if any(kw in physique or kw in psyche for kw in ["濒死", "重伤", "崩溃", "绝望", "生死"]):
                    semantic_clues.append("高张力")
                elif any(kw in physique or kw in psyche for kw in ["轻松", "放松", "平静", "满足"]):
                    semantic_clues.append("低张力")
    
    # 基于数值和语义线索生成描述
    if tension >= 85:
        if "高张力" in semantic_clues:
            return "生死一线"
        else:
            return "极度紧张"
    elif tension >= 70:
        return "高度紧张"
    elif tension >= 50:
        return "适度紧张"
    elif tension >= 30:
        if "低张力" in semantic_clues:
            return "闲庭信步"
        else:
            return "平缓"
    else:
        return "轻松舒缓"


def _describe_information_density(density: float, nodes: List[ChapterNode]) -> str:
    """
    将信息密度值转换为语义描述
    
    Args:
        density: 信息密度值 (0-100)
        nodes: 章节节点列表（用于上下文分析）
    
    Returns:
        信息 / 话题深度描述（如："在灌水"、"信息量极大"）
    """
    # 在 Chatbot 中，我们更关心“是否在认真展开一个具体话题”，
    # 因此用文本长度 + 近似实体计数来粗略判断深度。
    total_length = 0
    total_entities = 0

    for node in nodes:
        text = (node.text_content or "").strip()
        if not text:
            continue
        total_length += len(text)

        # 简单分词：中英文统一按「连续字母/数字/汉字」切分
        tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text)
        if not tokens:
            continue

        # 非内容词粗略停用词表（中英混合，仅覆盖高频虚词）
        stopwords = {
            "的", "了", "呢", "嘛", "啊", "呀", "吧", "在", "和", "跟", "就", "也", "很",
            "是", "有", "没", "不", "吗", "我", "你", "他", "她", "它", "我们", "你们", "他们",
            "and", "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "with",
        }
        content_tokens = {
            t for t in tokens
            if len(t) > 1 and t.lower() not in stopwords
        }
        total_entities += len(content_tokens)

    # 如果没有文本信号，回退到原有描述
    if total_length == 0:
        if density >= 70:
            return "信息量极大"
        elif density >= 50:
            return "信息量适中"
        elif density >= 30:
            return "信息量较少"
        else:
            return "在灌水"

    # 实际实体密度：每 50 个字符包含多少“新名词/信息点”
    entity_density = total_entities / max(1.0, total_length / 50.0)

    if entity_density >= 4:
        return "信息量极大（话题非常密集）"
    elif entity_density >= 2:
        return "信息量适中（有明确话题在展开）"
    elif entity_density >= 1:
        return "信息量略少（以闲聊为主）"
    else:
        return "在灌水（几乎没有新的信息点）"


def _calculate_emotion_intensity(nodes: List[ChapterNode]) -> float:
    """
    计算情绪强度 / 情感浓度

    新逻辑（Chatbot 优先）：
    - 检查回复文本中的情绪词密度（正负向形容词、副词等）；
    - 结合回复长度：短且无情绪词 → 极低浓度；长且情绪词密集 → 高浓度；
    - 回退：如果没有可用文本，再使用旧的“小说叙事状态”逻辑。
    
    Args:
        nodes: 章节节点列表
    
    Returns:
        情绪强度值 (0-100)
    """
    if not nodes:
        return 0.0

    # 情绪关键词表（中英文混合，粗粒度即可）
    emotion_keywords = {
        # 强烈负向
        "崩溃", "绝望", "愤怒", "暴怒", "痛苦", "恐惧", "害怕", "惊恐", "难受",
        # 强烈正向
        "狂喜", "兴奋", "激动", "超开心", "开心死了",
        # 中等情绪
        "紧张", "焦虑", "不安", "担忧", "期待", "难过", "伤心", "委屈",
        "放松", "轻松", "舒坦", "满足", "安心", "平静", "冷静",
        # 英文常见情绪词
        "happy", "excited", "angry", "sad", "upset", "anxious",
        "nervous", "relaxed", "tired", "exhausted",
    }

    total_score = 0.0
    counted_nodes = 0

    for node in nodes:
        text = (node.text_content or "").strip()
        if not text:
            continue

        counted_nodes += 1
        length = len(text)
        lower_text = text.lower()

        # 统计情绪词出现次数（简单 contains 即可）
        emo_count = 0
        for kw in emotion_keywords:
            if kw.lower() in lower_text:
                emo_count += 1

        # 基于“长度 + 情绪词数”构造一个 0-100 的主观刻度
        if emo_count == 0:
            # 完全没有情绪词：根据长度给一个保底的低浓度
            if length < 20:
                score = 5.0   # 极短 & 无情绪：典型“冷冰冰单句”
            elif length < 80:
                score = 20.0  # 正常长度但中性：轻度情感投入
            else:
                score = 30.0  # 很长但中性：有展开，但语气不激烈
        else:
            # 有情绪词：随长度和密度爬升
            # emo_factor: 情绪词越多越接近 1
            emo_factor = min(1.0, emo_count / 8.0)
            # len_factor: 回复越长越接近 1
            len_factor = min(1.0, length / 120.0)
            # 基础 40，再根据两个因子各加最多 30 分
            score = 40.0 + emo_factor * 30.0 + len_factor * 30.0

        total_score += score

    if counted_nodes == 0:
        # 没有文本（纯旧小说状态），退回原有基于 plot_flags 的估算逻辑
        legacy_total = 0.0
        legacy_count = 0
        for node in nodes:
            if not node.narrative_state:
                continue
            if node.narrative_state.plot_flags:
                legacy_total += 40
                legacy_count += 1
        if legacy_count == 0:
            return 0.0
        return min(legacy_total / legacy_count, 100.0)

    avg_score = total_score / counted_nodes
    return float(min(max(avg_score, 0.0), 100.0))


def _calculate_information_density(nodes: List[ChapterNode]) -> float:
    """
    计算信息密度 / 话题深度（轻量近似）

    新逻辑：
    - 统计文本中的“内容词”（近似实体名词 / 概念词）数量；
    - 使用去重后的内容词计数近似“新信息点数量”；
    - 按单节点上限 100 归一化，取多个节点的平均值。
    
    Args:
        nodes: 章节节点列表
    
    Returns:
        信息密度值 (0-100)
    """
    if not nodes:
        return 0.0

    total_density = 0.0
    counted = 0

    for node in nodes:
        text = (node.text_content or "").strip()
        if not text:
            continue

        counted += 1
        # 简单分词：中英文统一按「连续字母/数字/汉字」切分
        tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text)
        if not tokens:
            continue

        stopwords = {
            "的", "了", "呢", "嘛", "啊", "呀", "吧", "在", "和", "跟", "就", "也", "很",
            "是", "有", "没", "不", "吗", "我", "你", "他", "她", "它", "我们", "你们", "他们",
            "而且", "然后", "但是", "不过",
            "and", "the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "with",
        }
        content_tokens = {
            t for t in tokens
            if len(t) > 1 and t.lower() not in stopwords
        }

        # 每个不同内容词近似一个“信息点”，粗略上限 100
        density = min(len(content_tokens) * 5.0, 100.0)
        total_density += density

    if counted == 0:
        return 0.0

    avg_density = total_density / counted
    return float(min(max(avg_density, 0.0), 100.0))


def _calculate_pacing(nodes: List[ChapterNode]) -> tuple[float, str]:
    """
    计算交互流 / 节奏（轻量启发式）

    在 Chatbot 场景下，我们主要用几个粗指标来判断：
    - 是否连续多轮非常短的回复（“嗯”“好”“哈哈”）→ DISENGAGED；
    - 是否持续给出特别长且信息点极多的回复 → OVERWHELMING；
    - 其他情况视为 ENGAGED。
    
    Args:
        nodes: 章节节点列表
    
    Returns:
        (节奏分数, 节奏等级)
        节奏分数: -100 到 100，负数为拖沓，正数为急促
        节奏等级: "拖沓" / "平缓" / "急促"
    """
    if not nodes:
        return 0.0, PacingLevel.SMOOTH.value

    texts = [(node.text_content or "").strip() for node in nodes if (node.text_content or "").strip()]
    if not texts:
        return 0.0, PacingLevel.SMOOTH.value

    lengths = [len(t) for t in texts]

    # 短回复比例（近似冷场/敷衍）
    short_threshold = 20
    short_ratio = sum(1 for l in lengths if l <= short_threshold) / len(lengths)

    # 超长回复比例（近似信息过载）
    long_threshold = 180
    long_ratio = sum(1 for l in lengths if l >= long_threshold) / len(lengths)

    # 复读率：完全相同或高度相似的回复比例
    normalized = [re.sub(r"\s+", "", t) for t in texts]
    unique_count = len(set(normalized))
    repeat_ratio = 1.0 - (unique_count / len(normalized))

    # 构造一个 -100 ~ 100 的交互流评分：
    # - 短 & 复读 → 向负方向拉；长 & 信息密集 → 向正方向拉。
    # 这里的信息密集使用上方的信息密度函数近似。
    info_density = _calculate_information_density(nodes)

    pacing_score = 0.0
    pacing_score -= (short_ratio * 80.0 + repeat_ratio * 60.0)
    pacing_score += (long_ratio * 70.0 + info_density / 2.0)  # 0-50 分左右的正向拉升

    # 限幅
    pacing_score = max(-100.0, min(100.0, pacing_score))

    # 映射到离散等级
    if pacing_score <= -25.0:
        pacing = PacingLevel.DRAGGING.value  # DISENGAGED
    elif pacing_score >= 25.0:
        pacing = PacingLevel.RUSHING.value  # OVERWHELMING
    else:
        pacing = PacingLevel.SMOOTH.value   # ENGAGED

    return float(pacing_score), pacing


def _generate_semantic_suggestions(
    tension_description: str,
    information_density_description: str,
    pacing: str,
    node_count: int,
) -> List[str]:
    """
    生成语义化建议
    
    基于张力和节奏分析，生成写作建议（使用自然语言）。
    
    Args:
        tension_description: 张力描述
        information_density_description: 信息密度描述
        pacing: 节奏等级
        node_count: 分析的节点数量
    
    Returns:
        建议列表（语义化）
    """
    suggestions = []
    
    # 1. 高张力疲劳检测（基于语义描述）
    if "生死一线" in tension_description and node_count >= 3:
        suggestions.append("⚠️ 读者已疲劳：连续多章张力为「生死一线」，建议下一章进入「贤者时间」（张力回落）。请安排一段过场戏（Sequel），让角色整理物资、对话复盘，放松节奏。")
    
    # 2. 节奏建议（基于语义描述）
    if pacing == PacingLevel.DRAGGING.value:
        suggestions.append("📉 节奏过慢：建议增加剧情推进速度，或加入冲突事件")
    elif pacing == PacingLevel.RUSHING.value:
        suggestions.append("📈 节奏过快：建议适当放缓，增加细节描写或角色内心活动")
    
    # 3. 张力建议（基于语义描述）
    if "轻松舒缓" in tension_description or "闲庭信步" in tension_description:
        suggestions.append("💤 张力过低：建议增加冲突或悬念，提升读者兴趣")
    elif "生死一线" in tension_description or "极度紧张" in tension_description:
        suggestions.append("🔥 张力过高：建议适当降低，避免读者疲劳")
    
    # 4. 信息密度建议（基于语义描述）
    if "在灌水" in information_density_description:
        suggestions.append("💧 信息密度过低：建议增加剧情推进或重要信息揭示")
    elif "密集抛设定" in information_density_description:
        suggestions.append("📚 信息密度过高：建议适当分散设定，避免信息过载")
    
    return suggestions


# ==================== PID 控制器模块 ====================

class PIDController:
    """
    PID 控制器（比例-积分-微分控制器）
    
    用于调节叙事节奏，动态调整生成参数（Temperature, Presence Penalty）。
    
    PID 算法：
    - P (Proportional): 比例项，响应当前误差
    - I (Integral): 积分项，响应累积误差（消除稳态误差）
    - D (Derivative): 微分项，响应误差变化率（预测未来趋势）
    
    控制信号 = Kp × Error + Ki × Integral + Kd × Derivative
    """
    
    def __init__(
        self,
        kp: float = 0.5,  # 比例系数
        ki: float = 0.1,  # 积分系数
        kd: float = 0.2,  # 微分系数
        target: float = 50.0,  # 目标张力值（默认 50）
        min_output: float = -50.0,  # 最小输出
        max_output: float = 50.0,  # 最大输出
    ):
        """
        初始化 PID 控制器
        
        Args:
            kp: 比例系数（越大，响应越快，但可能震荡）
            ki: 积分系数（消除稳态误差，但可能过调）
            kd: 微分系数（抑制震荡，但可能对噪声敏感）
            target: 目标张力值（0-100）
            min_output: 最小输出值
            max_output: 最大输出值
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.target = target
        self.min_output = min_output
        self.max_output = max_output
        
        # PID 状态变量
        self.integral = 0.0  # 累积误差
        self.last_error = 0.0  # 上一次误差
        self.last_time = None  # 上一次更新时间
    
    def update(self, current_value: float, dt: float = 1.0) -> float:
        """
        更新 PID 控制器，计算控制信号
        
        Args:
            current_value: 当前张力值（0-100）
            dt: 时间步长（默认 1.0，表示每章）
        
        Returns:
            控制信号（范围：min_output 到 max_output）
        """
        # 计算误差
        error = self.target - current_value
        
        # 比例项
        p_term = self.kp * error
        
        # 积分项（累积误差）
        self.integral += error * dt
        # 积分限幅（防止积分饱和）
        if self.integral > 100:
            self.integral = 100
        elif self.integral < -100:
            self.integral = -100
        i_term = self.ki * self.integral
        
        # 微分项（误差变化率）
        if self.last_time is not None:
            derivative = (error - self.last_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative
        
        # 计算控制信号
        control_signal = p_term + i_term + d_term
        
        # 限幅
        if control_signal > self.max_output:
            control_signal = self.max_output
        elif control_signal < self.min_output:
            control_signal = self.min_output
        
        # 更新状态
        self.last_error = error
        self.last_time = dt
        
        return control_signal
    
    def reset(self):
        """重置 PID 控制器状态"""
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = None
    
    def set_target(self, target: float):
        """设置目标值"""
        self.target = target


def calculate_pid_control_params(
    current_tension: float,
    target_tension: float = 50.0,
    prev_control_signal: float = 0.0,
    kp: float = 0.5,
    ki: float = 0.1,
    kd: float = 0.2,
) -> Tuple[float, float, float]:
    """
    计算 PID 控制参数（Temperature 和 Presence Penalty）
    
    根据张力误差，动态调整生成参数：
    - 如果张力太低（Error > 0）：提高 Temperature，降低 Presence Penalty（增加创造性）
    - 如果张力太高（Error < 0）：降低 Temperature，提高 Presence Penalty（减少重复，更稳定）
    
    Args:
        current_tension: 当前张力值（0-100）
        target_tension: 目标张力值（0-100）
        prev_control_signal: 上一次控制信号（用于平滑）
        kp: 比例系数
        ki: 积分系数
        kd: 微分系数
    
    Returns:
        (control_signal, recommended_temperature, recommended_presence_penalty)
    """
    if not NUMPY_AVAILABLE or np is None:
        # 如果没有 numpy，返回默认值
        return 0.0, 0.7, 0.0
    
    # 创建 PID 控制器
    pid = PIDController(kp=kp, ki=ki, kd=kd, target=target_tension)
    
    # 计算控制信号
    control_signal = pid.update(current_tension, dt=1.0)
    
    # 将控制信号映射到 Temperature 和 Presence Penalty
    # Temperature 范围：0.3 - 1.0（默认 0.7）
    # Presence Penalty 范围：-0.5 - 0.5（默认 0.0）
    
    # 控制信号范围：-50 到 50
    # 如果 control_signal > 0（张力太低），提高 Temperature
    # 如果 control_signal < 0（张力太高），降低 Temperature
    
    # Temperature 映射：control_signal 从 -50 到 50，映射到 0.3 到 1.0
    temperature = 0.7 + (control_signal / 50.0) * 0.3
    temperature = max(0.3, min(1.0, temperature))  # 限幅
    
    # Presence Penalty 映射：control_signal 从 -50 到 50，映射到 0.5 到 -0.5
    # 张力高时（control_signal < 0），提高 Presence Penalty（减少重复）
    presence_penalty = -(control_signal / 50.0) * 0.5
    presence_penalty = max(-0.5, min(0.5, presence_penalty))  # 限幅
    
    return control_signal, temperature, presence_penalty


def apply_pid_to_momentum_report(
    momentum_report: MomentumReport,
    target_tension: float = 50.0,
    prev_control_signal: float = 0.0,
) -> MomentumReport:
    """
    将 PID 控制参数应用到 MomentumReport
    
    Args:
        momentum_report: 叙事势能报告
        target_tension: 目标张力值
        prev_control_signal: 上一次控制信号
    
    Returns:
        更新后的 MomentumReport（包含 PID 控制参数）
    """
    # 计算 PID 控制参数
    control_signal, temperature, presence_penalty = calculate_pid_control_params(
        current_tension=momentum_report.tension,
        target_tension=target_tension,
        prev_control_signal=prev_control_signal,
    )
    
    # 更新报告
    momentum_report.target_tension = target_tension
    momentum_report.tension_error = target_tension - momentum_report.tension
    momentum_report.pid_control_signal = control_signal
    momentum_report.recommended_temperature = temperature
    momentum_report.recommended_presence_penalty = presence_penalty
    
    return momentum_report
