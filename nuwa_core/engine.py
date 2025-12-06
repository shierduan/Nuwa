"""
引擎控制器与接口 (Engine Controller Module)

功能：统一对外的接口，供 app.py 调用。

核心功能：
- run_chapter_cycle: 执行完整的章节循环处理
- TaiyiEngine: 太一引擎主类
"""

import json
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

# 导入向量计算相关库（NTD 升级）
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from .state_machine import ChapterNode, extract_state, extract_semantic_state
from .momentum_tracker import (
    calculate_momentum, 
    MomentumReport, 
    apply_pid_to_momentum_report,
    calculate_pid_control_params
)
from .causality_judge import scan_conflicts, ConflictReport, calculate_ooc_scores
from .semantic_field import (
    vectorize_state,
    StateVector,
    calculate_potential_energy,
    evolve,
    inverse_collapse,
    build_collapse_prompt,
    get_embedding_model,
)


class TaiyiEngine:
    """
    太一引擎主类
    
    统一管理状态机、势能追踪和因果判官。
    """
    
    def __init__(self, project_name: str, data_dir: str = "data"):
        """
        初始化引擎
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录路径
        """
        self.project_name = project_name
        self.data_dir = data_dir
        self.nodes_dir = os.path.join(data_dir, project_name, "nodes")
        
        # 确保节点目录存在
        os.makedirs(self.nodes_dir, exist_ok=True)
    
    def run_chapter_cycle(
        self,
        chapter_id: int,
        text: str,
        prev_node_path: Optional[str] = None,
        selected_model: str = "lm_studio",
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        gemini_base_url: Optional[str] = None,
        characters: Optional[List[Dict[str, str]]] = None,
        vector_db=None,
    ) -> Dict[str, Any]:
        """
        执行完整的章节循环处理
        
        流程：
        1. 调用 state_machine 提取状态
        2. 调用 momentum_tracker 计算势能
        3. 调用 causality_judge 检查 Bug
        4. 将所有结果打包保存为 data/{project}/nodes/{chapter_id}.json
        
        Args:
            chapter_id: 章节ID
            text: 章节文本内容
            prev_node_path: 前一章节点文件路径（可选）
            selected_model: 模型类型
            base_url: LM Studio base_url
            model_name: 模型名称
            api_key: Gemini API Key
            gemini_base_url: Gemini base_url
            characters: 角色列表
            vector_db: 向量数据库连接
        
        Returns:
            包含所有处理结果的字典
        """
        # 1. 加载前一章的状态节点
        prev_node = None
        if prev_node_path and os.path.exists(prev_node_path):
            try:
                with open(prev_node_path, 'r', encoding='utf-8') as f:
                    prev_data = json.load(f)
                    prev_node = ChapterNode.from_dict(prev_data.get("node", {}))
            except Exception as e:
                print(f"加载前一章节点失败: {e}")
        
        # 2. 提取状态（使用语义化版本）
        current_node = extract_semantic_state(
            text=text,
            prev_state=prev_node,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
            chapter_id=chapter_id,
            characters=characters,
        )
        
        # ==================== 算法调度中心 (The Algorithm Loop) ====================
        
        # Step 1: Vector_Check - 先计算 OOC 分数，如果偏差过大，直接打回
        ooc_scores = {}
        if characters:
            ooc_scores = calculate_ooc_scores(
                current_node=current_node,
                character_table=characters
            )
            
            # 检查是否有严重 OOC（分数 < 0.4）
            critical_ooc_chars = [char for char, score in ooc_scores.items() if score < 0.4]
            if critical_ooc_chars:
                # 严重 OOC，返回错误报告（不消耗 LLM 算力进行后续生成）
                return {
                    "chapter_id": chapter_id,
                    "error": "OOC_DETECTED",
                    "message": f"检测到严重人设崩塌（OOC）：{', '.join(critical_ooc_chars)}",
                    "ooc_scores": ooc_scores,
                    "recommendation": "请修正角色行为，使其符合角色设定，然后重新生成",
                }
        
        # Step 2: 计算叙事势能（需要最近 3-5 个节点）
        recent_nodes = self._load_recent_nodes(chapter_id, limit=5)
        recent_nodes.append(current_node)
        momentum_report = calculate_momentum(recent_nodes)
        
        # Step 3: PID_Update - 根据上一章的势能误差，动态计算本章的生成参数
        # 加载上一章的 PID 控制信号（用于平滑）
        prev_control_signal = 0.0
        if prev_node:
            prev_node_data = self.load_node(prev_node.chapter_id)
            if prev_node_data and "momentum" in prev_node_data:
                prev_control_signal = prev_node_data["momentum"].get("pid_control_signal", 0.0)
        
        # 应用 PID 控制（根据章节类型设置目标张力）
        # 这里可以根据章节类型动态调整目标张力
        # 例如：高潮章节目标 90，铺垫章节目标 30
        target_tension = self._get_target_tension(chapter_id, momentum_report)
        
        momentum_report = apply_pid_to_momentum_report(
            momentum_report=momentum_report,
            target_tension=target_tension,
            prev_control_signal=prev_control_signal,
        )
        
        # Step 4: 检查冲突（传递 AI 配置参数用于语义校验）
        # 注意：scan_conflicts 内部已经计算了 ooc_scores，不需要额外计算
        conflict_report = scan_conflicts(
            current_node=current_node,
            vector_db=vector_db,
            character_table=characters,
            project_name=self.project_name,
            selected_model=selected_model,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            gemini_base_url=gemini_base_url,
        )
        
        # 5. 打包结果（确保可读性强）
        result = {
            "chapter_id": chapter_id,
            "node": current_node.to_dict(),
            "momentum": momentum_report.to_dict(),
            "conflicts": conflict_report.to_dict(),
            "timestamp": current_node.timestamp,
            # 添加人类可读的摘要
            "human_readable_summary": _generate_human_readable_summary(
                current_node=current_node,
                momentum_report=momentum_report,
                conflict_report=conflict_report,
            ),
        }
        
        # 6. 保存到文件（使用更友好的格式）
        node_file_path = os.path.join(self.nodes_dir, f"{chapter_id}.json")
        with open(node_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result
    
    def _load_recent_nodes(self, current_chapter_id: int, limit: int = 5) -> List[ChapterNode]:
        """
        加载最近的节点
        
        Args:
            current_chapter_id: 当前章节ID
            limit: 加载数量限制
        
        Returns:
            最近的章节节点列表
        """
        nodes = []
        
        # 从当前章节往前加载
        for i in range(1, limit + 1):
            chapter_id = current_chapter_id - i
            if chapter_id < 1:
                break
            
            node_path = os.path.join(self.nodes_dir, f"{chapter_id}.json")
            if os.path.exists(node_path):
                try:
                    with open(node_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        node_data = data.get("node", {})
                        if node_data:
                            nodes.insert(0, ChapterNode.from_dict(node_data))
                except Exception as e:
                    print(f"加载节点 {chapter_id} 失败: {e}")
        
        return nodes
    
    def load_node(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """
        加载指定章节的节点数据
        
        Args:
            chapter_id: 章节ID
        
        Returns:
            节点数据字典，如果不存在则返回 None
        """
        node_path = os.path.join(self.nodes_dir, f"{chapter_id}.json")
        if not os.path.exists(node_path):
            return None
        
        try:
            with open(node_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载节点 {chapter_id} 失败: {e}")
            return None
    
    def get_momentum_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取势能历史数据（用于绘制曲线图）
        
        Args:
            limit: 返回的章节数量限制
        
        Returns:
            势能历史数据列表，每个元素包含 chapter_id 和 momentum 数据
        """
        history = []
        
        # 获取所有节点文件
        if not os.path.exists(self.nodes_dir):
            return history
        
        node_files = sorted(
            [f for f in os.listdir(self.nodes_dir) if f.endswith('.json')],
            key=lambda x: int(x.replace('.json', '')) if x.replace('.json', '').isdigit() else 0,
            reverse=True
        )[:limit]
        
        for node_file in reversed(node_files):
            chapter_id = int(node_file.replace('.json', ''))
            node_data = self.load_node(chapter_id)
            if node_data and "momentum" in node_data:
                history.append({
                    "chapter_id": chapter_id,
                    "tension": node_data["momentum"].get("tension", 0),
                    "pacing_score": node_data["momentum"].get("pacing_score", 0),
                    "emotion_intensity": node_data["momentum"].get("emotion_intensity", 0),
                    "information_density": node_data["momentum"].get("information_density", 0),
                })
        
        return history
    
    def predict_next_vector(
        self,
        current_chapter_id: int,
        momentum: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[float]]:
        """
        预测下一章的理想向量（NTD 升级）
        
        根据当前向量和动量（Momentum），简单推算下一章的理想向量：
        V_next = V_current + Momentum
        
        Args:
            current_chapter_id: 当前章节ID
            momentum: 动量数据（可选，如果不提供则从节点数据加载）
        
        Returns:
            预测的下一章向量（384维列表）或 None
        """
        if not NUMPY_AVAILABLE or np is None:
            return None
        
        # 加载当前章节节点
        current_node_data = self.load_node(current_chapter_id)
        if not current_node_data or not current_node_data.get("node"):
            return None
        
        current_node = ChapterNode.from_dict(current_node_data.get("node", {}))
        if current_node.state_vector is None:
            return None
        
        # 获取动量（如果不提供，从节点数据加载）
        if momentum is None:
            momentum = current_node_data.get("momentum", {})
        
        # 计算动量向量（基于张力变化）
        # 简化：使用张力误差作为动量方向
        tension_error = momentum.get("tension_error", 0.0)  # 目标 - 实际
        
        # 转换为 numpy 数组
        current_vector = np.array(current_node.state_vector)
        
        # 计算动量方向（简化：使用随机方向，但受张力误差影响）
        # 实际应用中，可以根据历史向量变化计算真实动量
        if len(current_vector) > 0:
            # 生成一个小的随机扰动作为动量（受张力误差影响）
            momentum_scale = abs(tension_error) / 100.0  # 归一化到 0-1
            momentum_vector = np.random.normal(0, momentum_scale * 0.1, size=current_vector.shape)
            
            # 预测下一章向量：V_next = V_current + Momentum
            predicted_vector = current_vector + momentum_vector
            
            # 归一化（保持向量长度）
            norm = np.linalg.norm(predicted_vector)
            if norm > 0:
                predicted_vector = predicted_vector / norm * np.linalg.norm(current_vector)
            
            return predicted_vector.tolist()
        
        return None
    
    def build_prompt_context(
        self,
        chapter_id: int,
        include_prev_state: bool = True,
        include_momentum: bool = True,
        include_constraints: bool = True,
        use_inverse_decoding: bool = True,  # NTD 升级：是否使用逆向解码
    ) -> str:
        """
        构建 Prompt 上下文
        
        用于"生成下一章"时，将状态、势能建议和因果约束组装到 Prompt 中。
        
        Args:
            chapter_id: 当前章节ID
            include_prev_state: 是否包含前一章状态
            include_momentum: 是否包含势能建议
            include_constraints: 是否包含因果约束
        
        Returns:
            Prompt 上下文字符串
        """
        context_parts = []
        
        # 1. 前一章状态（使用语义化状态）
        if include_prev_state:
            prev_node_data = self.load_node(chapter_id)
            if prev_node_data:
                node = prev_node_data.get("node", {})
                if node:
                    # 尝试加载语义化状态
                    narrative_state = node.get('narrative_state', {})
                    if narrative_state:
                        context_parts.append("【上一章最终状态（语义化）】")
                        characters = narrative_state.get('characters', {})
                        if characters:
                            context_parts.append(f"- 角色状态: {json.dumps(characters, ensure_ascii=False)[:800]}")
                        relations = narrative_state.get('relations', [])
                        if relations:
                            context_parts.append(f"- 关系状态: {json.dumps(relations, ensure_ascii=False)[:500]}")
                        environment = narrative_state.get('environment', '')
                        if environment:
                            context_parts.append(f"- 环境氛围: {environment[:200]}")
                        plot_flags = narrative_state.get('plot_flags', [])
                        if plot_flags:
                            context_parts.append(f"- 剧情标志: {', '.join(plot_flags)}")
                    else:
                        # 兼容旧版本
                        context_parts.append("【上一章最终状态】")
                        context_parts.append(f"- 世界状态: {json.dumps(node.get('world_state', {}), ensure_ascii=False)[:500]}")
                        context_parts.append(f"- 角色状态: {json.dumps(node.get('character_states', {}), ensure_ascii=False)[:500]}")
                        context_parts.append(f"- 剧情标志: {', '.join(node.get('plot_flags', []))}")
        
        # 2. 势能建议
        if include_momentum:
            current_node_data = self.load_node(chapter_id)
            if current_node_data and "momentum" in current_node_data:
                momentum = current_node_data["momentum"]
                suggestions = momentum.get("suggestions", [])
                if suggestions:
                    context_parts.append("\n【叙事势能建议】")
                    for suggestion in suggestions:
                        context_parts.append(f"- {suggestion}")
        
        # 3. 因果约束
        if include_constraints:
            current_node_data = self.load_node(chapter_id)
            if current_node_data and "conflicts" in current_node_data:
                conflicts = current_node_data["conflicts"]
                critical_errors = conflicts.get("critical_errors", [])
                if critical_errors:
                    context_parts.append("\n【因果约束警告】")
                    for error in critical_errors:
                        context_parts.append(f"⚠️ {error.get('message', '')}")
        
        # 4. NTD 升级：逆向解码策略（Inverse Decoding）
        if use_inverse_decoding:
            try:
                # 预测下一章的理想向量
                predicted_vector = self.predict_next_vector(chapter_id)
                
                if predicted_vector:
                    # 使用预测向量去 LanceDB 中检索 Top 3 风格最相似的历史片段
                    style_chunks = self._retrieve_similar_style_chunks(
                        predicted_vector=predicted_vector,
                        top_k=3,
                        exclude_chapter_id=chapter_id,  # 排除当前章节
                    )
                    
                    if style_chunks:
                        context_parts.append("\n【风格参考片段（逆向解码）】")
                        context_parts.append("请参考以下历史片段的行文质感和情绪浓度（它们在数学上最接近下一章的预测状态）：\n")
                        for idx, chunk in enumerate(style_chunks, 1):
                            chunk_text = chunk.get("text", "")[:300]  # 限制长度
                            chunk_chapter = chunk.get("chapter_id", 0)
                            context_parts.append(f"片段 {idx}（来自第 {chunk_chapter} 章）：{chunk_text}...")
                        context_parts.append("\n请基于此风格，描写新的剧情。")
            except Exception as e:
                print(f"逆向解码失败: {e}")
                # 失败时不影响其他功能
        
        return "\n".join(context_parts)
    
    def _retrieve_similar_style_chunks(
        self,
        predicted_vector: List[float],
        top_k: int = 3,
        exclude_chapter_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用预测向量检索风格相似的历史片段（NTD 升级）
        
        Args:
            predicted_vector: 预测的下一章向量
            top_k: 返回的片段数量
            exclude_chapter_id: 排除的章节ID（通常是当前章节）
        
        Returns:
            风格相似的历史片段列表
        """
        if not NUMPY_AVAILABLE:
            return []
        
        try:
            import numpy as np
        except ImportError:
            return []
        
        try:
            # 尝试导入 memory_engine
            from memory_engine import get_memory_engine
            
            # 获取记忆引擎
            memory_engine = get_memory_engine(project_name=self.project_name)
            if not memory_engine:
                return []
            
            # 将预测向量转换为查询文本（简化：使用向量直接搜索）
            # 注意：LanceDB 的 search 需要查询文本，这里我们需要使用向量搜索
            # 由于 memory_engine 的 search_memory 主要基于文本，我们需要另一种方法
            
            # 方案：加载所有历史节点，计算与预测向量的相似度
            chunks = []
            
            # 获取所有节点文件
            if not os.path.exists(self.nodes_dir):
                return []
            
            node_files = sorted(
                [f for f in os.listdir(self.nodes_dir) if f.endswith('.json')],
                key=lambda x: int(x.replace('.json', '')) if x.replace('.json', '').isdigit() else 0,
            )
            
            predicted_vec = np.array(predicted_vector)
            
            # 计算每个历史节点的相似度
            similarities = []
            for node_file in node_files:
                chapter_id = int(node_file.replace('.json', ''))
                
                # 排除指定章节
                if exclude_chapter_id and chapter_id >= exclude_chapter_id:
                    continue
                
                # 加载节点
                node_data = self.load_node(chapter_id)
                if not node_data or not node_data.get("node"):
                    continue
                
                node = ChapterNode.from_dict(node_data.get("node", {}))
                if node.state_vector is None:
                    continue
                
                # 计算余弦相似度
                node_vec = np.array(node.state_vector)
                dot_product = np.dot(predicted_vec, node_vec)
                norm_pred = np.linalg.norm(predicted_vec)
                norm_node = np.linalg.norm(node_vec)
                
                if norm_pred > 0 and norm_node > 0:
                    similarity = dot_product / (norm_pred * norm_node)
                    similarities.append({
                        "chapter_id": chapter_id,
                        "similarity": float(similarity),
                        "text": node.text_content[:500],  # 限制长度
                    })
            
            # 按相似度排序，取 Top K
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:top_k]
        
        except Exception as e:
            print(f"检索风格相似片段失败: {e}")
            return []
    
    def _get_target_tension(self, chapter_id: int, momentum_report: MomentumReport) -> float:
        """
        根据章节类型和当前状态，动态计算目标张力
        
        Args:
            chapter_id: 章节ID
            momentum_report: 当前叙事势能报告
        
        Returns:
            目标张力值（0-100）
        """
        # 简单策略：根据当前张力动态调整
        # 如果连续多章高张力，降低目标（让节奏回落）
        # 如果连续多章低张力，提高目标（增加冲突）
        
        current_tension = momentum_report.tension
        
        # 如果当前张力 > 80，且连续多章，降低目标
        if current_tension > 80:
            # 检查最近几章的张力
            recent_nodes = self._load_recent_nodes(chapter_id, limit=3)
            # 简化判断：如果最近节点都有 narrative_state，认为可能是高张力
            high_tension_count = sum(
                1 for node in recent_nodes 
                if hasattr(node, 'narrative_state') and node.narrative_state is not None
            )
            
            if high_tension_count >= 2:
                # 连续高张力，降低目标（让节奏回落）
                return 40.0
        
        # 如果当前张力 < 30，提高目标（增加冲突）
        if current_tension < 30:
            return 60.0
        
        # 默认目标：50（中等张力）
        return 50.0
    
    def get_recommended_generation_params(
        self,
        chapter_id: int
    ) -> Dict[str, float]:
        """
        获取推荐的生成参数（基于 PID 控制）
        
        Args:
            chapter_id: 章节ID
        
        Returns:
            包含 recommended_temperature 和 recommended_presence_penalty 的字典
        """
        node_data = self.load_node(chapter_id)
        if not node_data or "momentum" not in node_data:
            # 如果没有数据，返回默认值
            return {
                "temperature": 0.7,
                "presence_penalty": 0.0,
            }
        
        momentum = node_data["momentum"]
        return {
            "temperature": momentum.get("recommended_temperature", 0.7),
            "presence_penalty": momentum.get("recommended_presence_penalty", 0.0),
        }
    
    # ==================== 大一统接口：step() 方法 ====================
    
    def step(
        self,
        user_instruction: str,
        current_chapter_id: int,
        current_text: str = "",
        character_descriptions: Optional[List[Dict[str, str]]] = None,
        chapter_goal: Optional[str] = None,
        selected_model: str = "lm_studio",
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        gemini_base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        统一的演化步骤（大一统接口）
        
        所有的"状态提取"、"OOC检查"、"大纲核对"全部内化为向量运算。
        不再有"红灯报警"：如果用户指令导致能量过高，算法会自动寻找能量较低的路径。
        
        流程：
        1. 向量化当前状态
        2. 计算势能和梯度
        3. 动力学演化，寻找能量最低点
        4. 逆向坍缩，检索相似片段
        5. 生成 Prompt 并调用 LLM
        
        Args:
            user_instruction: 用户指令
            current_chapter_id: 当前章节ID
            current_text: 当前章节文本（可选，如果不提供则从文件加载）
            character_descriptions: 角色描述列表，格式 [{"name": "角色名", "description": "描述"}, ...]
            chapter_goal: 本章目标/细纲（可选）
            selected_model: 模型类型
            base_url: LM Studio base_url
            model_name: 模型名称
            api_key: Gemini API Key
            gemini_base_url: Gemini base_url
        
        Returns:
            包含生成结果和演化信息的字典
        """
        if not NUMPY_AVAILABLE or np is None:
            return {
                "success": False,
                "error": "numpy 不可用",
            }
        
        try:
            # 加载当前章节文本（如果不提供）
            if not current_text:
                node_data = self.load_node(current_chapter_id)
                if node_data and node_data.get("node"):
                    current_text = node_data["node"].get("text_content", "")
            
            if not current_text:
                current_text = user_instruction  # 如果没有当前文本，使用用户指令
            
            # 加载前一章状态向量
            prev_vector = None
            prev_state_description = ""
            if current_chapter_id > 1:
                prev_node_data = self.load_node(current_chapter_id - 1)
                if prev_node_data and prev_node_data.get("node"):
                    prev_node = ChapterNode.from_dict(prev_node_data.get("node", {}))
                    if prev_node.state_vector:
                        prev_vector = np.array(prev_node.state_vector)
                    # 构建前一章状态描述
                    if prev_node.narrative_state:
                        narrative = prev_node.narrative_state
                        desc_parts = []
                        for char_name, char_state in narrative.characters.items():
                            physique = char_state.get("physique", "")
                            psyche = char_state.get("psyche", "")
                            if physique or psyche:
                                desc_parts.append(f"{char_name}：{physique} {psyche}")
                        if narrative.environment:
                            desc_parts.append(f"环境：{narrative.environment}")
                        prev_state_description = "。".join(desc_parts)
            
            # 构建角色核心向量（人设势能）
            character_core_vectors = {}
            if character_descriptions:
                embedding_model = get_embedding_model()
                if embedding_model:
                    for char_desc in character_descriptions:
                        char_name = char_desc.get("name", "")
                        char_description = char_desc.get("description", "")
                        if char_name and char_description:
                            try:
                                core_vector = embedding_model.encode(char_description, convert_to_numpy=True)
                                character_core_vectors[char_name] = core_vector
                            except Exception as e:
                                print(f"生成角色 {char_name} 的核心向量失败: {e}")
            
            # 构建目标向量（剧情引力）
            goal_vector = None
            if chapter_goal:
                goal_state = vectorize_state(chapter_goal)
                if goal_state:
                    goal_vector = goal_state.vector
            
            # 合并所有角色的核心向量（简化：使用平均值）
            character_core_vector = None
            if character_core_vectors:
                vectors_list = list(character_core_vectors.values())
                character_core_vector = np.mean(vectors_list, axis=0)
            
            # 动力学演化：计算理想的下一刻向量
            evolved_state, evolution_info = evolve(
                current_text=current_text + " " + user_instruction,
                character_core_vector=character_core_vector,
                prev_vector=prev_vector,
                goal_vector=goal_vector,
                dt=0.1,
                max_iterations=10,
            )
            
            if evolved_state is None:
                return {
                    "success": False,
                    "error": "演化失败",
                    "evolution_info": evolution_info,
                }
            
            # 逆向波函数坍缩：检索相似片段
            # 获取记忆引擎
            from memory_engine import get_memory_engine
            memory_engine = get_memory_engine(project_name=self.project_name)
            
            retrieved_chunks = inverse_collapse(
                target_vector=evolved_state.vector,
                memory_engine=memory_engine,
                project_name=self.project_name,
                top_k=3,
                exclude_chapter_id=current_chapter_id,
            )
            
            # 构建 Prompt
            collapse_prompt = build_collapse_prompt(
                retrieved_chunks=retrieved_chunks,
                prev_state_description=prev_state_description,
                user_instruction=user_instruction,
            )
            
            # 调用 LLM 生成（只使用已加载的模块）
            result_text = None
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
                
                if selected_model == "gemini":
                    if not api_key or not model_name:
                        return {
                            "success": False,
                            "error": "Gemini 配置不完整",
                        }
                    
                    success, result = generate_content_gemini(
                        api_key=api_key,
                        model_name=model_name,
                        system_prompt="你是一个专业的小说写手。请根据提供的上下文和风格参考，生成符合语义坐标的正文。",
                        user_prompt=collapse_prompt,
                        base_url=gemini_base_url,
                        max_output_tokens=2048,
                        temperature=0.7,
                        stream=False,
                    )
                    if success:
                        result_text = result
                else:
                    # LM Studio
                    if not base_url or not model_name:
                        return {
                            "success": False,
                            "error": "LM Studio 配置不完整",
                        }
                    
                    success, result = generate_content_lm_studio(
                        base_url=base_url,
                        model_name=model_name,
                        system_prompt="你是一个专业的小说写手。请根据提供的上下文和风格参考，生成符合语义坐标的正文。",
                        user_prompt=collapse_prompt,
                        max_tokens=2048,
                        temperature=0.7,
                        stream=False,
                    )
                    if success:
                        result_text = result
            except Exception as e:
                print(f"LLM 生成失败: {e}")
                import traceback
                print(traceback.format_exc())
            
            return {
                "success": result_text is not None,
                "generated_text": result_text,
                "evolved_vector": evolved_state.to_list(),
                "evolution_info": evolution_info,
                "retrieved_chunks": retrieved_chunks,
                "energy": evolution_info.get("final_energy", 0.0),
                "energy_breakdown": evolution_info.get("energy_breakdown", {}),
            }
        
        except Exception as e:
            print(f"step() 执行失败: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
            }


def _generate_human_readable_summary(
    current_node: ChapterNode,
    momentum_report: 'MomentumReport',
    conflict_report: 'ConflictReport',
) -> Dict[str, Any]:
    """
    生成人类可读的摘要
    
    Args:
        current_node: 当前章节节点
        momentum_report: 叙事势能报告
        conflict_report: 冲突报告
    
    Returns:
        人类可读的摘要字典
    """
    summary = {
        "状态摘要": {},
        "叙事势能": {},
        "冲突警告": {},
    }
    
    # 状态摘要
    if current_node.narrative_state:
        narrative = current_node.narrative_state
        summary["状态摘要"]["角色状态"] = {}
        for char_name, char_state in narrative.characters.items():
            summary["状态摘要"]["角色状态"][char_name] = {
                "生理状态": char_state.get("physique", "未描述"),
                "心理状态": char_state.get("psyche", "未描述"),
                "当前行动元": char_state.get("focus", "未描述"),
                "关键道具": char_state.get("equipment", []),
            }
        
        if narrative.relations:
            summary["状态摘要"]["关系状态"] = [
                f"{rel.get('target', '')} - {rel.get('status', '')} ({rel.get('tone', '')})"
                for rel in narrative.relations
            ]
        
        if narrative.environment:
            summary["状态摘要"]["环境氛围"] = narrative.environment
        
        if narrative.plot_flags:
            summary["状态摘要"]["剧情标志"] = narrative.plot_flags
    
    # 叙事势能
    summary["叙事势能"]["张力"] = momentum_report.tension_description
    summary["叙事势能"]["信息密度"] = momentum_report.information_density_description
    summary["叙事势能"]["节奏"] = momentum_report.pacing
    if momentum_report.suggestions:
        summary["叙事势能"]["建议"] = momentum_report.suggestions
    
    # 冲突警告
    if conflict_report.critical_errors:
        summary["冲突警告"]["严重错误"] = [
            error.get("message", "") for error in conflict_report.critical_errors
        ]
    if conflict_report.warnings:
        summary["冲突警告"]["警告"] = [
            warning.get("message", "") for warning in conflict_report.warnings
        ]
    
    return summary

