"""
语义场论核心算法 (Semantic Field Theory Core)

核心思想：一切皆向量，剧情演化遵循物理规律。

核心概念：
- Semantic Tensor: 语义张量（状态向量）
- Narrative Hamiltonian: 叙事哈密顿量（势能函数）
- Evolution Dynamics: 动力学演化
- Inverse Collapse: 逆向波函数坍缩
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

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


# ==================== 全局 Embedding 模型缓存 ====================

_embedding_model_cache = None


def get_embedding_model():
    """
    获取 Embedding 模型（带全局缓存）
    
    使用全局变量缓存模型，避免重复加载。
    
    Returns:
        SentenceTransformer 模型或 None
    """
    global _embedding_model_cache
    
    if not EMBEDDING_AVAILABLE or SentenceTransformer is None:
        return None
    
    if _embedding_model_cache is None:
        try:
            # 复用全局嵌入目录管理逻辑，避免重复联网下载
            from .model_utils import ensure_embedding_model_dir
        except ImportError:
            ensure_embedding_model_dir = None
        
        model_path = None
        if ensure_embedding_model_dir is not None:
            model_path = ensure_embedding_model_dir(SentenceTransformer)
        
        if not model_path:
            print("加载 Embedding 模型失败：无法获取本地模型目录")
            return None
        
        try:
            model = SentenceTransformer(model_path, local_files_only=True)
            _embedding_model_cache = model
        except Exception as e:
            print(f"加载 Embedding 模型失败: {e}")
            return None
    
    return _embedding_model_cache


# ==================== 语义张量定义 ====================

@dataclass
class StateVector:
    """
    状态向量（语义张量）
    
    代表角色或剧情在"语义空间"中的确切坐标。
    严禁使用 HP/MP 等游戏数值，一切皆向量。
    """
    vector: Any = field(default=None)  # 384维向量（np.ndarray 或 List[float]）
    description: str = ""  # 原始描述文本（用于人类阅读）
    timestamp: str = ""
    
    def to_list(self) -> List[float]:
        """转换为列表格式（用于 JSON 序列化）"""
        if NUMPY_AVAILABLE and np is not None and isinstance(self.vector, np.ndarray):
            return self.vector.tolist()
        if isinstance(self.vector, list):
            return self.vector
        return list(self.vector) if self.vector is not None else []
    
    @classmethod
    def from_list(cls, vector_list: List[float], description: str = ""):
        """从列表创建 StateVector"""
        if NUMPY_AVAILABLE and np is not None:
            vector = np.array(vector_list)
        else:
            vector = vector_list
        return cls(vector=vector, description=description)


def vectorize_state(text_description: str) -> Optional[StateVector]:
    """
    将文学描述转化为状态向量（语义张量）
    
    输入：一段文学描述（如 "他已是强弩之末，连举剑的手都在颤抖"）
    输出：一个 384维的 StateVector，代表在"语义空间"中的确切坐标
    
    Args:
        text_description: 文学描述文本
    
    Returns:
        StateVector 或 None
    """
    if not text_description or not text_description.strip():
        return None
    
    if not NUMPY_AVAILABLE or np is None:
        return None
    
    embedding_model = get_embedding_model()
    if embedding_model is None:
        return None
    
    try:
        # 生成向量
        vector = embedding_model.encode(text_description, convert_to_numpy=True)
        
        return StateVector(
            vector=vector,
            description=text_description,
        )
    except Exception as e:
        print(f"向量化状态失败: {e}")
        return None


# ==================== 叙事哈密顿量（势能函数）====================

def calculate_potential_energy(
    current_vector: np.ndarray,
    character_core_vector: Optional[np.ndarray] = None,
    prev_vector: Optional[np.ndarray] = None,
    goal_vector: Optional[np.ndarray] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    计算叙事哈密顿量（总势能）
    
    定义三个"势能场"来约束剧情：
    
    1. E_character (人设势能):
       计算 current_vector 与 character_core_vector 的距离。
       物理意义：角色行为越符合人设，能量越低。
    
    2. E_causality (因果势能):
       计算 current_vector 与 prev_vector 的连贯性。
       物理意义：状态不能瞬移，突变会产生高能量。
    
    3. E_plot (剧情引力):
       计算 current_vector 与 goal_vector 的距离。
       物理意义：剧情总是试图向大纲靠拢。
    
    总能量：E_total = E_character + E_causality + E_plot
    
    Args:
        current_vector: 当前状态向量
        character_core_vector: 角色人设核心向量（可选）
        prev_vector: 前一章状态向量（可选）
        goal_vector: 本章目标向量（可选）
        weights: 权重字典，格式 {"character": 1.0, "causality": 1.0, "plot": 1.0}
    
    Returns:
        (总能量, 能量分解字典)
    """
    if not NUMPY_AVAILABLE or np is None:
        return 0.0, {}
    
    # 默认权重
    if weights is None:
        weights = {
            "character": 1.0,
            "causality": 1.0,
            "plot": 0.5,  # 剧情引力权重较低（允许偏离）
        }
    
    energy_breakdown = {}
    total_energy = 0.0
    
    # 确保向量是一维的
    def ensure_1d_vector(vec: np.ndarray) -> np.ndarray:
        """确保向量是一维的"""
        if vec.ndim > 1:
            return vec.flatten()
        return vec
    
    # 归一化当前向量
    current_vector = ensure_1d_vector(current_vector)
    norm_current = np.linalg.norm(current_vector)
    if norm_current == 0:
        return float('inf'), {"error": "零向量"}
    
    current_normalized = current_vector / norm_current
    
    # 1. E_character (人设势能)
    if character_core_vector is not None:
        character_core_vector = ensure_1d_vector(character_core_vector)
        norm_char = np.linalg.norm(character_core_vector)
        if norm_char > 0:
            char_normalized = character_core_vector / norm_char
            # 计算余弦距离（1 - 余弦相似度）
            cosine_sim = np.dot(current_normalized, char_normalized)
            # 确保cosine_sim是标量
            cosine_sim = float(cosine_sim)
            cosine_distance = 1.0 - cosine_sim
            
            # 使用平方函数，使偏离更明显
            e_character = weights["character"] * (cosine_distance ** 2)
            energy_breakdown["character"] = float(e_character)
            total_energy += e_character
        else:
            energy_breakdown["character"] = 0.0
    else:
        energy_breakdown["character"] = 0.0
    
    # 2. E_causality (因果势能)
    if prev_vector is not None:
        prev_vector = ensure_1d_vector(prev_vector)
        norm_prev = np.linalg.norm(prev_vector)
        if norm_prev > 0:
            prev_normalized = prev_vector / norm_prev
            # 计算余弦距离
            cosine_sim = np.dot(current_normalized, prev_normalized)
            # 确保cosine_sim是标量
            cosine_sim = float(cosine_sim)
            cosine_distance = 1.0 - cosine_sim
            
            # 因果势能：突变会产生高能量
            e_causality = weights["causality"] * (cosine_distance ** 2)
            energy_breakdown["causality"] = float(e_causality)
            total_energy += e_causality
        else:
            energy_breakdown["causality"] = 0.0
    else:
        energy_breakdown["causality"] = 0.0
    
    # 3. E_plot (剧情引力)
    if goal_vector is not None:
        goal_vector = ensure_1d_vector(goal_vector)
        norm_goal = np.linalg.norm(goal_vector)
        if norm_goal > 0:
            goal_normalized = goal_vector / norm_goal
            # 计算余弦距离
            cosine_sim = np.dot(current_normalized, goal_normalized)
            # 确保cosine_sim是标量
            cosine_sim = float(cosine_sim)
            cosine_distance = 1.0 - cosine_sim
            
            # 剧情引力：距离目标越远，能量越高
            e_plot = weights["plot"] * (cosine_distance ** 2)
            energy_breakdown["plot"] = float(e_plot)
            total_energy += e_plot
        else:
            energy_breakdown["plot"] = 0.0
    else:
        energy_breakdown["plot"] = 0.0
    
    return float(total_energy), energy_breakdown


def calculate_gradient(
    current_vector: np.ndarray,
    character_core_vector: Optional[np.ndarray] = None,
    prev_vector: Optional[np.ndarray] = None,
    goal_vector: Optional[np.ndarray] = None,
    weights: Optional[Dict[str, float]] = None,
    epsilon: float = 1e-5,
) -> np.ndarray:
    """
    计算势能场的梯度（受力情况）
    
    梯度 = -∇E = -∇(E_character + E_causality + E_plot)
    
    物理意义：梯度指向能量降低最快的方向。
    
    Args:
        current_vector: 当前状态向量
        character_core_vector: 角色人设核心向量
        prev_vector: 前一章状态向量
        goal_vector: 本章目标向量
        weights: 权重字典
        epsilon: 数值微分的步长
    
    Returns:
        梯度向量（受力方向）
    """
    if not NUMPY_AVAILABLE or np is None:
        if isinstance(current_vector, np.ndarray):
            return np.zeros_like(current_vector)
        elif isinstance(current_vector, list):
            return [0.0] * len(current_vector)
        return None
    
    # L2 归一化所有向量（投影到单位超球面上）
    def normalize_vector(vec: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if vec is None:
            return None
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec.copy()
        return vec / norm
    
    # 归一化输入向量
    normalized_current = normalize_vector(current_vector)
    normalized_character = normalize_vector(character_core_vector)
    normalized_prev = normalize_vector(prev_vector)
    normalized_goal = normalize_vector(goal_vector)
    
    # 使用数值微分计算梯度
    gradient = np.zeros_like(normalized_current)
    
    for i in range(len(normalized_current)):
        # 前向差分
        vector_plus = normalized_current.copy()
        vector_plus[i] += epsilon
        # 保持归一化
        vector_plus = normalize_vector(vector_plus) or vector_plus
        
        # 计算能量差
        energy_plus, _ = calculate_potential_energy(
            current_vector=vector_plus,
            character_core_vector=normalized_character,
            prev_vector=normalized_prev,
            goal_vector=normalized_goal,
            weights=weights,
        )
        
        energy_current, _ = calculate_potential_energy(
            current_vector=normalized_current,
            character_core_vector=normalized_character,
            prev_vector=normalized_prev,
            goal_vector=normalized_goal,
            weights=weights,
        )
        
        # 梯度 = -∂E/∂x（负号表示能量降低方向）
        gradient[i] = -(energy_plus - energy_current) / epsilon
    
    return gradient


# ==================== 动力学演化 ====================

def evolve(
    current_text: str,
    character_core_vector: Optional[np.ndarray] = None,
    prev_vector: Optional[np.ndarray] = None,
    goal_vector: Optional[np.ndarray] = None,
    dt: float = 0.1,
    max_iterations: int = 10,
    momentum: float = 0.3,
) -> Tuple[Optional[StateVector], Dict[str, Any]]:
    """
    动力学演化：计算理想的下一刻向量
    
    流程：
    Step 1: 将当前的剧情文本转化为向量 V_now
    Step 2: 计算该向量在三个场中的受力情况 (Gradient)
    Step 3: 计算理想的下一刻向量：V_next = V_now + F_total × Δt + 动量项
    
    Args:
        current_text: 当前剧情文本
        character_core_vector: 角色人设核心向量
        prev_vector: 前一章状态向量
        goal_vector: 本章目标向量
        dt: 时间步长（默认 0.1）
        max_iterations: 最大迭代次数（用于能量最小化）
        momentum: 动量因子（默认 0.3），使演化方向更平滑
    
    Returns:
        (演化后的状态向量, 演化信息字典)
    """
    if not NUMPY_AVAILABLE or np is None:
        return None, {"error": "numpy 不可用"}
    
    # Step 1: 将当前文本转化为向量
    current_state = vectorize_state(current_text)
    if current_state is None:
        return None, {"error": "无法向量化当前文本"}
    
    V_now = current_state.vector
    
    # Step 2 & 3: 迭代演化，寻找能量最低点
    V_current = V_now.copy()
    evolution_info = {
        "initial_energy": 0.0,
        "final_energy": 0.0,
        "iterations": 0,
        "energy_history": [],
    }
    
    # 初始化动量项
    velocity = np.zeros_like(V_current)
    
    for iteration in range(max_iterations):
        # 计算当前能量
        energy, energy_breakdown = calculate_potential_energy(
            current_vector=V_current,
            character_core_vector=character_core_vector,
            prev_vector=prev_vector,
            goal_vector=goal_vector,
        )
        
        if iteration == 0:
            evolution_info["initial_energy"] = energy
        evolution_info["energy_history"].append(energy)
        
        # 计算梯度（受力）
        gradient = calculate_gradient(
            current_vector=V_current,
            character_core_vector=character_core_vector,
            prev_vector=prev_vector,
            goal_vector=goal_vector,
        )
        
        # 更新动量项和向量
        # 动量公式：velocity = momentum * velocity + gradient * dt
        # 向量更新：V_next = V_current + velocity
        velocity = momentum * velocity + gradient * dt
        V_next = V_current + velocity
        
        # 归一化（保持向量长度）
        norm = np.linalg.norm(V_next)
        if norm > 0:
            V_next = V_next / norm * np.linalg.norm(V_current)
        
        # 检查收敛（能量变化很小）
        if iteration > 0:
            energy_change = abs(energy - evolution_info["energy_history"][-2])
            if energy_change < 1e-6:
                break
        
        V_current = V_next
    
    evolution_info["final_energy"] = energy
    evolution_info["iterations"] = iteration + 1
    evolution_info["energy_breakdown"] = energy_breakdown
    
    # 返回演化后的状态向量
    evolved_state = StateVector(
        vector=V_current,
        description=f"演化后的状态（初始：{current_text[:50]}...）",
    )
    
    return evolved_state, evolution_info


# ==================== 逆向波函数坍缩 ====================

def inverse_collapse(
    target_vector: np.ndarray,
    memory_engine=None,
    project_name: Optional[str] = None,
    top_k: int = 3,
    exclude_chapter_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    逆向波函数坍缩：将计算出的向量变回文字
    
    全息检索：使用 target_vector 在 LanceDB 中搜索最相似的历史片段。
    
    Args:
        target_vector: 目标向量（演化后的理想状态）
        memory_engine: 记忆引擎实例（可选）
        project_name: 项目名称（用于获取记忆引擎）
        top_k: 返回的片段数量
        exclude_chapter_id: 排除的章节ID
    
    Returns:
        检索到的历史片段列表
    """
    if not NUMPY_AVAILABLE or np is None:
        return []
    
    chunks = []
    
    # 方案1：使用 memory_engine 检索（如果可用）
    if memory_engine is not None:
        try:
            # 将向量转换为查询文本（简化：使用向量直接搜索）
            # 注意：memory_engine 的 search_memory 主要基于文本
            # 这里我们需要直接使用向量相似度搜索
            
            # 尝试从 memory_engine 获取表
            if hasattr(memory_engine, 'db_path'):
                try:
                    import lancedb
                    db = lancedb.connect(memory_engine.db_path)
                    if "memory" in db.table_names():
                        table = db.open_table("memory")
                        
                        # 使用向量搜索
                        results = table.search(target_vector.tolist()).limit(top_k * 2).to_pandas()
                        
                        for _, row in results.iterrows():
                            chunk_id = row.get("id", "")
                            chapter_id = int(chunk_id.split("_")[0]) if "_" in chunk_id else 0
                            
                            if exclude_chapter_id and chapter_id >= exclude_chapter_id:
                                continue
                            
                            chunks.append({
                                "chapter_id": chapter_id,
                                "text": row.get("text", "") or row.get("summary", ""),
                                "similarity": 1.0 - row.get("_distance", 1.0),  # 距离转相似度
                            })
                            
                            if len(chunks) >= top_k:
                                break
                except Exception as e:
                    print(f"使用 memory_engine 检索失败: {e}")
        except Exception as e:
            print(f"memory_engine 检索异常: {e}")
    
    # 方案2：从节点文件直接检索（备用方案）
    if not chunks and project_name:
        try:
            import os
            nodes_dir = os.path.join("data", project_name, "nodes")
            
            if os.path.exists(nodes_dir):
                node_files = sorted(
                    [f for f in os.listdir(nodes_dir) if f.endswith('.json')],
                    key=lambda x: int(x.replace('.json', '')) if x.replace('.json', '').isdigit() else 0,
                )
                
                similarities = []
                for node_file in node_files:
                    chapter_id = int(node_file.replace('.json', ''))
                    
                    if exclude_chapter_id and chapter_id >= exclude_chapter_id:
                        continue
                    
                    try:
                        with open(os.path.join(nodes_dir, node_file), 'r', encoding='utf-8') as f:
                            node_data = json.load(f)
                            node = node_data.get("node", {})
                            
                            # 检查是否有 state_vector
                            if node.get("state_vector"):
                                node_vector = np.array(node["state_vector"])
                                
                                # 计算余弦相似度
                                dot_product = np.dot(target_vector, node_vector)
                                norm_target = np.linalg.norm(target_vector)
                                norm_node = np.linalg.norm(node_vector)
                                
                                if norm_target > 0 and norm_node > 0:
                                    similarity = dot_product / (norm_target * norm_node)
                                    similarities.append({
                                        "chapter_id": chapter_id,
                                        "text": node.get("text_content", "")[:500],
                                        "similarity": float(similarity),
                                    })
                    except Exception as e:
                        continue
                
                # 按相似度排序，取 Top K
                similarities.sort(key=lambda x: x["similarity"], reverse=True)
                chunks = similarities[:top_k]
        except Exception as e:
            print(f"从节点文件检索失败: {e}")
    
    return chunks


def build_collapse_prompt(
    retrieved_chunks: List[Dict[str, Any]],
    prev_state_description: str = "",
    user_instruction: str = "",
) -> str:
    """
    构建逆向坍缩的 Prompt
    
    Args:
        retrieved_chunks: 检索到的历史片段
        prev_state_description: 前一章状态描述
        user_instruction: 用户指令
    
    Returns:
        组装好的 Prompt
    """
    prompt_parts = []
    
    prompt_parts.append("当前故事正在向一个特定的语义坐标演化。")
    prompt_parts.append("这个坐标的感觉接近于以下片段：\n")
    
    for idx, chunk in enumerate(retrieved_chunks, 1):
        chunk_text = chunk.get("text", "")[:300]
        chunk_chapter = chunk.get("chapter_id", 0)
        prompt_parts.append(f"片段 {idx}（来自第 {chunk_chapter} 章）：{chunk_text}...")
    
    prompt_parts.append("\n")
    
    if prev_state_description:
        prompt_parts.append(f"状态约束：请确保生成的文字，在语义上体现出【{prev_state_description}】的自然延续。")
    
    if user_instruction:
        prompt_parts.append(f"\n用户指令：{user_instruction}")
    
    prompt_parts.append("\n请生成下一段正文。")
    
    return "\n".join(prompt_parts)

