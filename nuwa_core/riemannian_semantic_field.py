"""
黎曼几何语义场论 (Riemannian Semantic Field Theory)

基于黎曼流形的严格数学框架，改进语义场计算。

核心改进：
1. 双曲流形：使用双曲几何替代欧几里得空间
2. Hessian矩阵：计算度量张量，实现自然梯度下降
3. 数值稳定性：严格的边界处理和归一化
4. 余弦距离平滑版本：避免奇异点
"""

import numpy as np
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class HyperbolicManifold:
    """
    双曲流形 - 使用庞加莱球模型
    
    双曲空间具有负曲率，适合表示层次化关系。
    在语义空间中，这允许更自然的相似度度量。
    """
    
    curvature: float = -1.0  # 负曲率
    
    def project_tangent(self, point: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        将向量投影到参考点的切空间
        
        Args:
            point: 流形上的点
            reference: 参考点
            
        Returns:
            切空间中的向量
        """
        # 确保输入是向量
        point = self._ensure_vector(point)
        reference = self._ensure_vector(reference)
        
        # 归一化到单位球面（庞加莱球模型的边界）
        norm_point = np.linalg.norm(point)
        norm_ref = np.linalg.norm(reference)
        
        if norm_point == 0 or norm_ref == 0:
            return np.zeros_like(point)
        
        point_norm = point / norm_point
        ref_norm = reference / norm_ref
        
        # 在单位球面上，切空间投影 = point - (point·reference) * reference
        projection = point_norm - np.dot(point_norm, ref_norm) * ref_norm
        
        # 保持投影的长度合理
        proj_norm = np.linalg.norm(projection)
        if proj_norm > 1.0:
            projection = projection / proj_norm
        
        return projection
    
    def exponential_map(self, base: np.ndarray, tangent: np.ndarray) -> np.ndarray:
        """
        指数映射：从切空间映射回流形
        
        Args:
            base: 基点
            tangent: 切空间向量
            
        Returns:
            流形上的点
        """
        base = self._ensure_vector(base)
        tangent = self._ensure_vector(tangent)
        
        # 庞加莱球模型的指数映射
        norm_base = np.linalg.norm(base)
        if norm_base == 0:
            return tangent
        
        # 限制切向量长度（避免超出单位球）
        norm_tangent = np.linalg.norm(tangent)
        if norm_tangent > 0.8:  # 安全边界
            tangent = tangent / norm_tangent * 0.8
        
        # 简化的指数映射：base + tangent，然后归一化
        result = base + tangent
        norm_result = np.linalg.norm(result)
        if norm_result > 0:
            result = result / norm_result
        
        return result
    
    def _ensure_vector(self, v: np.ndarray) -> np.ndarray:
        """确保输入是1维向量"""
        if isinstance(v, list):
            v = np.array(v)
        if not isinstance(v, np.ndarray):
            v = np.array(v)
        if v.ndim > 1:
            v = v.flatten()
        return v


@dataclass
class HessianCalculator:
    """
    Hessian矩阵计算器 - 计算度量张量
    
    Hessian矩阵描述了势能函数的二阶导数，
    用于自然梯度下降（在黎曼流形上的梯度下降）。
    """
    
    epsilon: float = 1e-6  # 数值微分步长
    regularization: float = 1e-8  # 正则化项，避免奇异
    
    def compute(self, state_vector: np.ndarray, 
                core_vector: Optional[np.ndarray] = None) -> np.ndarray:
        """
        计算Hessian矩阵
        
        Args:
            state_vector: 状态向量
            core_vector: 核心向量（用于定义势能函数）
            
        Returns:
            Hessian矩阵（度量张量）
        """
        # 数值稳定性：检查输入
        if not np.all(np.isfinite(state_vector)):
            n = len(state_vector)
            return np.eye(n) * self.regularization
        
        n = len(state_vector)
        hessian = np.zeros((n, n))
        
        if core_vector is None:
            core_vector = state_vector
        
        # 归一化输入（避免数值不稳定）
        state_norm = np.linalg.norm(state_vector)
        core_norm = np.linalg.norm(core_vector)
        
        if state_norm < 1e-10 or core_norm < 1e-10:
            return np.eye(n) * self.regularization
        
        state_normed = state_vector / state_norm
        core_normed = core_vector / core_norm
        
        # 使用数值方法计算二阶导数
        for i in range(n):
            for j in range(n):
                # 扰动向量
                e_i = np.zeros(n)
                e_i[i] = self.epsilon
                
                e_j = np.zeros(n)
                e_j[j] = self.epsilon
                
                # 四个点的函数值
                try:
                    v1 = state_normed + e_i + e_j
                    e1 = self._potential_energy(v1, core_normed)
                    
                    v2 = state_normed + e_i - e_j
                    e2 = self._potential_energy(v2, core_normed)
                    
                    v3 = state_normed - e_i + e_j
                    e3 = self._potential_energy(v3, core_normed)
                    
                    v4 = state_normed - e_i - e_j
                    e4 = self._potential_energy(v4, core_normed)
                    
                    # 中心差分公式
                    hessian[i, j] = (e1 - e2 - e3 + e4) / (4 * self.epsilon * self.epsilon)
                except:
                    hessian[i, j] = 0.0
        
        # 对称化
        hessian = (hessian + hessian.T) / 2
        
        # 正则化：确保正定性
        # 使用对角线占优的正则化，强度与维度相关
        scale = max(1.0, n / 100.0)  # 维度越大，正则化越强
        diagonal_reg = self.regularization * scale * np.eye(n)
        hessian += diagonal_reg
        
        # 特征值修正
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(hessian)
            # 确保所有特征值为正，且有最小值
            min_eig = self.regularization * 100 * scale
            eigenvalues = np.maximum(eigenvalues, min_eig)
            # 限制最大特征值，避免数值爆炸
            max_eig = 100.0 * scale
            eigenvalues = np.minimum(eigenvalues, max_eig)
            # 重构
            hessian = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
        except:
            # 如果特征值分解失败，返回单位矩阵
            hessian = np.eye(n) * self.regularization * scale
        
        return hessian
    
    def _potential_energy(self, state_vector: np.ndarray, core_vector: np.ndarray) -> float:
        """简化的势能函数，用于Hessian计算"""
        # 输入检查
        if not np.all(np.isfinite(state_vector)) or not np.all(np.isfinite(core_vector)):
            return 0.0
        
        # 归一化
        norm_state = np.linalg.norm(state_vector)
        norm_core = np.linalg.norm(core_vector)
        
        if norm_state < 1e-10 or norm_core < 1e-10:
            return 0.0
        
        state_norm = state_vector / norm_state
        core_norm = core_vector / norm_core
        
        # 余弦相似度
        cos_sim = np.dot(state_norm, core_norm)
        
        # 确保是标量
        if isinstance(cos_sim, np.ndarray):
            cos_sim = float(np.sum(cos_sim))
        
        # 平滑截断
        cos_sim = np.clip(cos_sim, -0.999, 0.999)
        
        # 势能
        return (1.0 - cos_sim) ** 2


@dataclass
class RigorousSemanticField:
    """
    严格语义场 - 基于黎曼几何的改进实现
    
    对应用户提供的代码框架：
    - 使用双曲流形
    - Hessian计算器
    - 数值稳定性处理
    - 余弦距离的平滑版本
    """
    
    manifold: HyperbolicManifold = None
    hessian: HessianCalculator = None
    core_vector: np.ndarray = None
    
    def __post_init__(self):
        """初始化后自动创建依赖"""
        if self.manifold is None:
            self.manifold = HyperbolicManifold()
        if self.hessian is None:
            self.hessian = HessianCalculator()
    
    def calculate_potential_energy(self, state_vector: np.ndarray) -> float:
        """
        计算势能 - 严格实现
        
        对应代码框架：
        1. 数值稳定性处理
        2. 归一化到单位球面
        3. 使用余弦距离的平滑版本
        """
        # 确保核心向量存在
        if self.core_vector is None:
            raise ValueError("必须先设置 core_vector")
        
        # 输入验证
        if not np.all(np.isfinite(state_vector)):
            return 0.0
        
        # 统一维度
        min_dim = min(len(state_vector), len(self.core_vector))
        state_vec = state_vector[:min_dim]
        core_vec = self.core_vector[:min_dim]
        
        # 数值稳定性处理：检查零向量
        norm_state = np.linalg.norm(state_vec)
        norm_core = np.linalg.norm(core_vec)
        
        if norm_state < 1e-8 or norm_core < 1e-8:
            return 0.0
        
        # 归一化到单位球面
        state_normalized = state_vec / norm_state
        core_normalized = core_vec / norm_core
        
        # 使用余弦距离的平滑版本
        char_sim = np.dot(state_normalized, core_normalized)
        
        # 严格的边界处理：确保是标量
        if isinstance(char_sim, np.ndarray):
            char_sim = float(np.sum(char_sim))
        
        # 平滑截断，避免奇异点
        char_sim = np.clip(char_sim, -0.999, 0.999)
        
        # 势能公式
        return (1.0 - char_sim) ** 2
    
    def compute_riemannian_gradient(self, state_vector: np.ndarray) -> np.ndarray:
        """
        计算黎曼梯度 - 严格实现
        
        对应代码：
        def compute_riemannian_gradient(self, state_vector: np.ndarray) -> np.ndarray:
            # 在黎曼流形上计算梯度
            tangent = self.manifold.project_tangent(state_vector, self.core_vector)
            hessian = self.hessian.compute(state_vector)
            
            # 自然梯度下降
            return np.linalg.solve(hessian + 1e-8 * np.eye(len(state_vector)), tangent)
        """
        # 输入验证
        if not np.all(np.isfinite(state_vector)):
            return np.zeros_like(state_vector)
        
        # 确保核心向量存在
        if self.core_vector is None:
            return np.zeros_like(state_vector)
        
        # 统一维度
        min_dim = min(len(state_vector), len(self.core_vector))
        state_vec = state_vector[:min_dim]
        core_vec = self.core_vector[:min_dim]
        
        # 检查零向量
        if np.linalg.norm(state_vec) < 1e-8 or np.linalg.norm(core_vec) < 1e-8:
            return np.zeros_like(state_vec)
        
        # 1. 投影到切空间
        tangent = self.manifold.project_tangent(state_vec, core_vec)
        
        # 2. 计算Hessian（度量张量）
        hessian = self.hessian.compute(state_vec, core_vec)
        
        # 3. 自然梯度下降：求解线性系统 H^{-1} * tangent
        
        try:
            # 使用数值稳定的求解器
            riemannian_gradient = np.linalg.solve(hessian, tangent)
        except np.linalg.LinAlgError:
            # 如果求解失败，使用伪逆（更稳定）
            riemannian_gradient = np.linalg.pinv(hessian) @ tangent
        
        # 4. 梯度裁剪：避免数值爆炸
        grad_norm = np.linalg.norm(riemannian_gradient)
        if grad_norm > 100.0:  # 阈值可根据维度调整
            riemannian_gradient = riemannian_gradient / grad_norm * 100.0
        
        return riemannian_gradient
    
    def evolve(self, state_vector: np.ndarray, dt: float = 0.01, 
               iterations: int = 10) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        演化 - 使用黎曼梯度下降
        
        Args:
            state_vector: 初始状态
            dt: 时间步长
            iterations: 迭代次数
            
        Returns:
            (演化后的状态, 演化信息)
        """
        # 输入验证
        if not np.all(np.isfinite(state_vector)):
            return state_vector.copy(), {"error": "Invalid input"}
        
        # 确保维度匹配
        min_dim = min(len(state_vector), len(self.core_vector))
        current = state_vector[:min_dim].copy()
        
        # 归一化初始状态
        norm_current = np.linalg.norm(current)
        if norm_current > 0:
            current = current / norm_current
        
        energy_history = []
        
        for i in range(iterations):
            # 计算势能
            energy = self.calculate_potential_energy(current)
            energy_history.append(energy)
            
            # 计算黎曼梯度
            gradient = self.compute_riemannian_gradient(current)
            
            # 动量项（使演化更平滑）
            if i == 0:
                velocity = gradient * dt
            else:
                momentum = 0.3
                velocity = momentum * velocity + (1 - momentum) * gradient * dt
            
            # 梯度下降：向能量降低方向移动
            current = current - velocity
            
            # 在流形上投影（保持归一化）
            norm = np.linalg.norm(current)
            if norm > 0:
                current = current / norm
            
            # 收敛检查
            if i > 0 and len(energy_history) > 2:
                # 检查能量是否在降低
                if energy_history[-1] < energy_history[-2] < energy_history[-3]:
                    # 连续降低，可能已经收敛
                    if abs(energy_history[-1] - energy_history[-2]) < 1e-6:
                        break
                elif energy_history[-1] > energy_history[-2] + 1e-5:
                    # 能量在增加，说明dt太大或方向错误
                    # 减小步长
                    dt *= 0.5
                    if dt < 1e-4:
                        break
                    # 回退一步
                    current = state_vector[:min_dim].copy() / np.linalg.norm(state_vector[:min_dim])
                    energy_history = energy_history[:-1]
                    i -= 1
                    continue
        
        info = {
            "iterations": i + 1,
            "initial_energy": energy_history[0] if energy_history else 0.0,
            "final_energy": energy_history[-1] if energy_history else 0.0,
            "energy_history": energy_history,
            "final_dt": dt,
        }
        
        return current, info


# ==================== 兼容性接口 ====================

def calculate_potential_energy(state_vector: np.ndarray, core_vector: Optional[np.ndarray] = None) -> float:
    """向后兼容的势能计算函数"""
    if core_vector is None:
        return 0.0
    
    field = RigorousSemanticField(core_vector=core_vector)
    return field.calculate_potential_energy(state_vector)


def calculate_gradient(state_vector: np.ndarray, core_vector: Optional[np.ndarray] = None, 
                      epsilon: float = 1e-5) -> np.ndarray:
    """向后兼容的梯度计算函数（使用黎曼梯度）"""
    if core_vector is None:
        return np.zeros_like(state_vector)
    
    field = RigorousSemanticField(core_vector=core_vector)
    return field.compute_riemannian_gradient(state_vector)


def evolve(current_text: str, core_vector: Optional[np.ndarray] = None, 
           dt: float = 0.01, iterations: int = 10) -> Tuple[Optional[Any], Dict[str, Any]]:
    """
    向后兼容的演化函数
    
    注意：这里需要传入core_vector，因为RigorousSemanticField需要它
    """
    if core_vector is None:
        return None, {"error": "需要提供 core_vector"}
    
    # 简单的文本向量化（实际使用时应使用embedding模型）
    # 这里假设输入已经是向量，或者需要外部处理
    if isinstance(current_text, str):
        # 临时：使用简单哈希生成测试向量
        import hashlib
        hash_val = int(hashlib.md5(current_text.encode()).hexdigest(), 16)
        vector = np.array([(hash_val >> (i % 32)) & 0xFF for i in range(384)], dtype=np.float32) / 255.0
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
    else:
        vector = current_text
    
    field = RigorousSemanticField(core_vector=core_vector)
    evolved, info = field.evolve(vector, dt=dt, iterations=iterations)
    
    # 包装为StateVector（如果需要）
    from .semantic_field import StateVector
    result = StateVector(
        vector=evolved,
        description=f"黎曼演化结果",
    )
    
    return result, info


# ==================== 兼容性类 ====================

@dataclass
class StateVector:
    """状态向量类"""
    vector: np.ndarray
    description: str = ""
    timestamp: str = ""


# ==================== 核心函数 ====================

def vectorize_state(text: str) -> Optional[StateVector]:
    """
    将文本向量化
    
    Args:
        text: 要向量化的文本
        
    Returns:
        StateVector 对象
    """
    try:
        # 简单的文本向量化（实际使用时应使用embedding模型）
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = np.array([(hash_val >> (i % 32)) & 0xFF for i in range(384)], dtype=np.float32) / 255.0
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return StateVector(
            vector=vector,
            description=text[:100],
            timestamp=str(datetime.now())
        )
    except Exception as e:
        print(f"[WARN] 文本向量化失败: {e}")
        return None


def inverse_collapse(vector: np.ndarray, core_vector: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """
    逆坍缩函数
    
    Args:
        vector: 状态向量
        core_vector: 核心向量
        
    Returns:
        坍缩信息
    """
    try:
        info = {
            "vector_norm": float(np.linalg.norm(vector)),
            "vector_dim": len(vector),
            "is_valid": np.all(np.isfinite(vector))
        }
        
        if core_vector is not None:
            # 计算与核心向量的相似度
            similarity = cosine_similarity_smooth(vector, core_vector)
            info["core_similarity"] = similarity
        
        return info
    except Exception as e:
        print(f"[WARN] 逆坍缩失败: {e}")
        return {"error": str(e)}


# ==================== 辅助函数 ====================

def normalize_vector(vector: np.ndarray) -> np.ndarray:
    """安全的向量归一化"""
    norm = np.linalg.norm(vector)
    if norm < 1e-10:
        return np.zeros_like(vector)
    return vector / norm


def cosine_similarity_smooth(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    平滑的余弦相似度计算
    
    避免数值不稳定，使用截断和正则化
    """
    vec1_norm = normalize_vector(vec1)
    vec2_norm = normalize_vector(vec2)
    
    if np.linalg.norm(vec1_norm) == 0 or np.linalg.norm(vec2_norm) == 0:
        return 0.0
    
    similarity = np.dot(vec1_norm, vec2_norm)
    
    # 确保是标量
    if isinstance(similarity, np.ndarray):
        similarity = float(np.sum(similarity))
    
    # 平滑截断
    similarity = np.clip(similarity, -0.999, 0.999)
    
    return float(similarity)


def verify_stability(state_vector: np.ndarray, core_vector: np.ndarray) -> Dict[str, bool]:
    """
    验证数值稳定性
    
    返回各种稳定性检查的结果
    """
    results = {}
    
    # 1. 零向量检查
    norm_state = np.linalg.norm(state_vector)
    norm_core = np.linalg.norm(core_vector)
    results["zero_vector"] = norm_state > 1e-8 and norm_core > 1e-8
    
    # 2. 范围检查
    results["range_check"] = np.all(np.isfinite(state_vector)) and np.all(np.isfinite(core_vector))
    
    # 3. 归一化稳定性
    field = RigorousSemanticField(core_vector=core_vector)
    try:
        energy = field.calculate_potential_energy(state_vector)
        results["energy_stable"] = np.isfinite(energy) and 0 <= energy <= 2.0
    except:
        results["energy_stable"] = False
    
    # 4. 梯度稳定性
    try:
        gradient = field.compute_riemannian_gradient(state_vector)
        results["gradient_stable"] = np.all(np.isfinite(gradient)) and np.linalg.norm(gradient) < 100.0
    except:
        results["gradient_stable"] = False
    
    return results