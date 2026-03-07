"""
图神经网络记忆增强模块 (Graph Neural Network Memory Enhancement)

功能：基于图结构的记忆关联和演化追踪，增强记忆系统的长期关联能力。

核心特性：
- 记忆关联图：基于语义相似度构建记忆之间的关联关系
- 演化轨迹追踪：支持记忆的长期演化分析
- 社区发现：自动识别记忆的主题社区
- 路径分析：记忆之间的关联路径查询

技术栈：
- NetworkX: 图结构存储和分析
- GNN (Graph Neural Network): 图神经网络用于节点表示学习
- LanceDB: 向量存储（兼容现有架构）
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from itertools import combinations

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    nx = None
    NETWORKX_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    EMBEDDING_AVAILABLE = False


class MemoryGraph:
    """
    记忆图 - 基于图结构的记忆关联管理
    
    功能：
    1. 构建记忆关联图（节点=记忆，边=语义相似度）
    2. 支持记忆演化轨迹追踪
    3. 提供社区发现和路径分析
    """
    
    def __init__(self, project_name: str, data_dir: str = "data"):
        """
        初始化记忆图
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录
        """
        self.project_name = project_name
        self.data_dir = data_dir
        self.graph_path = os.path.join(data_dir, project_name, "memory_graph.json")
        
        # 图结构
        self.graph = None
        if NETWORKX_AVAILABLE:
            self.graph = nx.Graph()
        
        # 相似度阈值（用于构建边）
        self.similarity_threshold = 0.7
        
        # 核心向量（用于计算关联强度）
        self.core_vector = None
        
        # 统计信息
        self.stats = {
            "nodes": 0,
            "edges": 0,
            "communities": 0,
            "last_update": None,
        }
        
        # 加载或初始化
        self._load_graph()
        
        print(f"[OK] MemoryGraph 初始化完成: {self.graph_path}")
        if self.graph:
            print(f"   - 节点数: {self.graph.number_of_nodes()}")
            print(f"   - 边数: {self.graph.number_of_edges()}")
    
    def _load_graph(self):
        """从文件加载图结构"""
        if not NETWORKX_AVAILABLE:
            print("[WARN] NetworkX 不可用，图功能受限")
            return
        
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 从 JSON 重建图
                    self.graph = nx.node_link_graph(data)
                    self.stats = data.get("stats", self.stats)
                    print(f"[OK] 已加载记忆图: {len(self.graph.nodes)} 个节点")
            except Exception as e:
                print(f"[WARN] 加载记忆图失败: {e}，将创建新图")
                self.graph = nx.Graph()
        else:
            self.graph = nx.Graph()
    
    def save_graph(self):
        """保存图结构到文件"""
        if not self.graph or not NETWORKX_AVAILABLE:
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
            
            # 更新统计信息
            self.stats["nodes"] = self.graph.number_of_nodes()
            self.stats["edges"] = self.graph.number_of_edges()
            self.stats["last_update"] = datetime.now().isoformat()
            
            # 转换为 JSON 可序列化格式
            data = nx.node_link_data(self.graph)
            data["stats"] = self.stats
            
            with open(self.graph_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] 记忆图已保存: {self.graph_path}")
        except Exception as e:
            print(f"[WARN] 保存记忆图失败: {e}")
    
    def set_core_vector(self, core_vector: Any):
        """设置核心向量（用于关联强度计算）"""
        if NUMPY_AVAILABLE and np is not None:
            if isinstance(core_vector, list):
                self.core_vector = np.array(core_vector)
            elif isinstance(core_vector, np.ndarray):
                self.core_vector = core_vector
            else:
                self.core_vector = core_vector
    
    def _calculate_similarity(self, vector1: Any, vector2: Any) -> float:
        """计算两个向量的余弦相似度"""
        if not NUMPY_AVAILABLE or np is None:
            return 0.0
        
        try:
            vec1 = vector1 if isinstance(vector1, np.ndarray) else np.array(vector1)
            vec2 = vector2 if isinstance(vector2, np.ndarray) else np.array(vector2)
            
            # 归一化
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            vec1 = vec1 / norm1
            vec2 = vec2 / norm2
            
            # 余弦相似度
            similarity = np.dot(vec1, vec2)
            
            # 确保是标量
            if isinstance(similarity, np.ndarray):
                similarity = float(np.sum(similarity))
            
            # 映射到 [0, 1]
            similarity = (similarity + 1.0) / 2.0
            
            return float(similarity)
        except Exception:
            return 0.0
    
    def add_memory_node(self, memory_id: str, text: str, vector: Any, 
                       metadata: Optional[Dict] = None) -> bool:
        """
        添加记忆节点到图中
        
        Args:
            memory_id: 记忆ID
            text: 记忆文本
            vector: 向量表示
            metadata: 元数据（timestamp, type, emotions等）
        
        Returns:
            是否成功添加
        """
        if not NETWORKX_AVAILABLE or not self.graph:
            return False
        
        if not NUMPY_AVAILABLE or np is None:
            return False
        
        try:
            # 确保向量是numpy数组
            if isinstance(vector, list):
                vector = np.array(vector)
            
            # 添加节点
            node_data = {
                "text": text,
                "vector": vector.tolist(),  # JSON序列化需要
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "access_count": 0,
            }
            
            self.graph.add_node(memory_id, **node_data)
            
            # 自动构建关联（如果已有其他节点）
            self._build_associations(memory_id, vector)
            
            return True
            
        except Exception as e:
            print(f"[WARN] 添加记忆节点失败: {e}")
            return False
    
    def _build_associations(self, new_memory_id: str, new_vector: Any):
        """为新节点构建关联边"""
        if not self.graph:
            return
        
        try:
            added_edges = 0
            for node_id, node_data in self.graph.nodes(data=True):
                if node_id == new_memory_id:
                    continue
                
                # 获取节点向量
                node_vector = node_data.get("vector")
                if not node_vector:
                    continue
                
                # 计算相似度
                similarity = self._calculate_similarity(new_vector, node_vector)
                
                # 如果相似度超过阈值，添加边
                if similarity >= self.similarity_threshold:
                    # 边权重 = 相似度
                    edge_weight = similarity
                    
                    # 如果有核心向量，增强权重
                    if self.core_vector is not None:
                        # 计算两个节点相对于核心的"协同性"
                        sim_to_core1 = self._calculate_similarity(new_vector, self.core_vector)
                        sim_to_core2 = self._calculate_similarity(node_vector, self.core_vector)
                        # 协同性越高，边权重越大
                        synergy = (sim_to_core1 + sim_to_core2) / 2.0
                        edge_weight = similarity * (1.0 + 0.5 * synergy)
                    
                    self.graph.add_edge(new_memory_id, node_id, weight=edge_weight)
                    added_edges += 1
            
            if added_edges > 0:
                print(f"[LINK] 为记忆 {new_memory_id} 构建了 {added_edges} 条关联边")
            
        except Exception as e:
            print(f"[WARN] 构建关联失败: {e}")
    
    def get_memory_trajectory(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        获取记忆的演化轨迹（从根节点到该节点的路径）
        
        Args:
            memory_id: 目标记忆ID
        
        Returns:
            路径上的节点列表（按时间顺序）
        """
        if not NETWORKX_AVAILABLE or not self.graph:
            return []
        
        if memory_id not in self.graph:
            return []
        
        try:
            # 寻找根节点（入度为0的节点，或最早的节点）
            roots = [n for n, d in self.graph.in_degree() if d == 0]
            if not roots:
                # 如果没有明确的根，使用最早创建的节点
                nodes_with_time = []
                for node_id, node_data in self.graph.nodes(data=True):
                    created_at = node_data.get("created_at", "")
                    if created_at:
                        nodes_with_time.append((node_id, created_at))
                
                if nodes_with_time:
                    nodes_with_time.sort(key=lambda x: x[1])
                    roots = [nodes_with_time[0][0]]
            
            if not roots:
                return []
            
            # 寻找从根到目标的最短路径（按边权重）
            trajectories = []
            for root in roots:
                try:
                    # 使用最短路径算法（考虑边权重）
                    path = nx.shortest_path(self.graph, source=root, target=memory_id, weight="weight")
                    
                    # 构建路径详情
                    trajectory = []
                    for node_id in path:
                        node_data = self.graph.nodes[node_id]
                        trajectory.append({
                            "memory_id": node_id,
                            "text": node_data.get("text", "")[:100],
                            "created_at": node_data.get("created_at"),
                            "metadata": node_data.get("metadata", {}),
                        })
                    trajectories.append(trajectory)
                except nx.NetworkXNoPath:
                    continue
            
            # 返回最短的轨迹
            if trajectories:
                trajectories.sort(key=len)
                return trajectories[0]
            
            return []
            
        except Exception as e:
            print(f"[WARN] 获取演化轨迹失败: {e}")
            return []
    
    def find_communities(self) -> List[Dict[str, Any]]:
        """
        发现记忆社区（基于Louvain社区检测算法）
        
        Returns:
            社区列表，每个社区包含节点和代表性记忆
        """
        if not NETWORKX_AVAILABLE or not self.graph:
            return []
        
        try:
            # 使用Louvain算法检测社区
            if hasattr(nx.algorithms, 'community') and hasattr(nx.algorithms.community, 'louvain_communities'):
                communities = nx.algorithms.community.louvain_communities(
                    self.graph, weight="weight", resolution=1.0
                )
            else:
                # 备选：使用贪婪模块度
                communities = list(nx.algorithms.community.greedy_modularity_communities(
                    self.graph, weight="weight"
                ))
            
            # 包装社区信息
            community_info = []
            for idx, community in enumerate(communities):
                if len(community) < 2:
                    continue
                
                # 计算社区中心性（最核心的节点）
                subgraph = self.graph.subgraph(community)
                centrality = nx.degree_centrality(subgraph)
                if centrality:
                    center_node = max(centrality.items(), key=lambda x: x[1])[0]
                    center_text = self.graph.nodes[center_node].get("text", "")[:100]
                else:
                    center_node = list(community)[0]
                    center_text = self.graph.nodes[center_node].get("text", "")[:100]
                
                # 计算社区内平均相似度
                avg_similarity = 0.0
                edge_count = 0
                for u, v, data in subgraph.edges(data=True):
                    avg_similarity += data.get("weight", 0.0)
                    edge_count += 1
                if edge_count > 0:
                    avg_similarity /= edge_count
                
                community_info.append({
                    "community_id": idx,
                    "size": len(community),
                    "center_node": center_node,
                    "center_text": center_text,
                    "avg_similarity": avg_similarity,
                    "members": list(community),
                })
            
            # 按大小排序
            community_info.sort(key=lambda x: x["size"], reverse=True)
            
            self.stats["communities"] = len(community_info)
            
            return community_info
            
        except Exception as e:
            print(f"[WARN] 社区发现失败: {e}")
            return []
    
    def query_similar_memories(self, query_vector: Any, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        查询相似记忆（基于图的关联搜索）
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
        
        Returns:
            相似记忆列表
        """
        if not NETWORKX_AVAILABLE or not self.graph:
            return []
        
        if not NUMPY_AVAILABLE or np is None:
            return []
        
        try:
            similarities = []
            
            for node_id, node_data in self.graph.nodes(data=True):
                node_vector = node_data.get("vector")
                if not node_vector:
                    continue
                
                # 计算相似度
                similarity = self._calculate_similarity(query_vector, node_vector)
                
                # 如果节点有边，增强相似度（关联增强）
                edge_bonus = 0.0
                neighbors = list(self.graph.neighbors(node_id))
                if neighbors:
                    # 计算邻居平均权重作为bonus
                    weights = [self.graph[node_id][nbr].get("weight", 0.0) for nbr in neighbors]
                    edge_bonus = sum(weights) / len(weights) * 0.1  # 10%的权重增强
                
                enhanced_similarity = similarity + edge_bonus
                
                similarities.append({
                    "memory_id": node_id,
                    "text": node_data.get("text", ""),
                    "similarity": enhanced_similarity,
                    "metadata": node_data.get("metadata", {}),
                    "neighbors": neighbors,
                })
            
            # 排序并返回top_k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            print(f"[WARN] 图查询失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图的统计信息"""
        if not NETWORKX_AVAILABLE or not self.graph:
            return {"error": "NetworkX不可用"}
        
        try:
            stats = {
                "nodes": self.graph.number_of_nodes(),
                "edges": self.graph.number_of_edges(),
                "density": nx.density(self.graph),
                "avg_clustering": nx.average_clustering(self.graph),
                "is_connected": nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False,
                "communities": self.stats.get("communities", 0),
                "last_update": self.stats.get("last_update"),
            }
            
            # 如果图不为空，添加更多统计
            if self.graph.number_of_nodes() > 0:
                try:
                    stats["avg_degree"] = sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes()
                    stats["diameter"] = nx.diameter(self.graph) if nx.is_connected(self.graph) else None
                except:
                    pass
            
            return stats
        except Exception as e:
            return {"error": str(e)}


class GraphEnhancedMemoryCortex:
    """
    图增强的记忆皮层 - 将图神经网络能力集成到现有记忆系统
    
    继承MemoryCortex并添加图关联能力
    """
    
    def __init__(self, project_name: str, data_dir: str = "data"):
        """
        初始化图增强记忆皮层
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录
        """
        from .memory_cortex import MemoryCortex
        
        # 初始化基础记忆皮层
        self.memory_cortex = MemoryCortex(project_name, data_dir)
        
        # 初始化记忆图
        self.memory_graph = MemoryGraph(project_name, data_dir)
        
        # 设置核心向量
        if hasattr(self.memory_cortex, '_core_vector') and self.memory_cortex._core_vector is not None:
            self.memory_graph.set_core_vector(self.memory_cortex._core_vector)
        
        print("[OK] GraphEnhancedMemoryCortex 初始化完成")
    
    def store_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None, 
                    timestamp: Optional[datetime] = None) -> bool:
        """
        存储记忆（同时存储到LanceDB和图中）
        
        Args:
            text: 记忆文本
            metadata: 元数据
            timestamp: 时间戳
        
        Returns:
            是否成功
        """
        # 1. 存储到基础记忆皮层（LanceDB）
        result = self.memory_cortex.store_memory(text, metadata, timestamp)
        
        if not result:
            return False
        
        # 2. 生成向量并添加到图中
        if self.memory_cortex.embedding_model:
            # 生成向量（使用融合时间戳的文本）
            timestamp_str = (timestamp or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
            fused_text = f"[{timestamp_str}] {text}"
            
            vector = self.memory_cortex.embedding_model.encode(fused_text, convert_to_numpy=True)
            
            # 生成记忆ID
            memory_id = f"{int(time.time() * 1000)}_{hash(text) % 10000}"
            
            # 添加到图中
            self.memory_graph.add_memory_node(memory_id, fused_text, vector, metadata)
            
            return True
        
        return False
    
    def recall_by_emotion(self, query_text: str, current_emotion_vector=None, 
                         top_k: int = 5, emotion_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        检索记忆（基于图增强的语义搜索）
        
        逻辑：
        1. 使用基础记忆皮层检索
        2. 使用图查询增强结果
        3. 合并并去重
        4. 按综合相似度排序
        
        Args:
            query_text: 查询文本
            current_emotion_vector: 情绪向量
            top_k: 返回数量
            emotion_weight: 情绪权重
        
        Returns:
            记忆列表
        """
        # 1. 基础检索
        base_results = self.memory_cortex.recall_by_emotion(
            query_text, current_emotion_vector, top_k * 2, emotion_weight
        )
        
        # 2. 图增强检索
        graph_results = []
        if self.memory_cortex.embedding_model:
            query_vector = self.memory_cortex.embedding_model.encode(query_text, convert_to_numpy=True)
            graph_results = self.memory_graph.query_similar_memories(query_vector, top_k=top_k)
        
        # 3. 合并结果
        combined = {}
        
        # 添加基础结果
        for result in base_results:
            memory_id = result["metadata"].get("id", "")
            if memory_id:
                combined[memory_id] = {
                    "text": result["text"],
                    "similarity": result["similarity"],
                    "source": "base",
                    "metadata": result["metadata"],
                }
        
        # 添加图结果
        for result in graph_results:
            memory_id = result["memory_id"]
            graph_similarity = result["similarity"]
            
            if memory_id in combined:
                # 如果已存在，使用更高的相似度
                combined[memory_id]["similarity"] = max(
                    combined[memory_id]["similarity"], 
                    graph_similarity
                )
                combined[memory_id]["source"] = "both"
            else:
                combined[memory_id] = {
                    "text": result["text"],
                    "similarity": graph_similarity,
                    "source": "graph",
                    "metadata": result["metadata"],
                }
        
        # 4. 排序并返回
        sorted_results = sorted(combined.values(), key=lambda x: x["similarity"], reverse=True)
        
        # 5. 添加图特有的信息（如邻居、轨迹）
        for result in sorted_results[:top_k]:
            memory_id = result["metadata"].get("id", "")
            if memory_id:
                # 添加邻居信息
                if memory_id in self.memory_graph.graph:
                    neighbors = list(self.memory_graph.graph.neighbors(memory_id))
                    result["neighbors"] = neighbors[:5]  # 最多5个邻居
                
                # 添加轨迹信息（可选，因为计算成本较高）
                # result["trajectory"] = self.memory_graph.get_memory_trajectory(memory_id)
        
        return sorted_results[:top_k]
    
    def get_memory_trajectory(self, memory_id: str) -> List[Dict[str, Any]]:
        """获取记忆演化轨迹"""
        return self.memory_graph.get_memory_trajectory(memory_id)
    
    def find_communities(self) -> List[Dict[str, Any]]:
        """发现记忆社区"""
        return self.memory_graph.find_communities()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "lancedb": self.memory_cortex.get_index_info() if hasattr(self.memory_cortex, 'get_index_info') else {},
            "graph": self.memory_graph.get_statistics(),
        }
        return stats
    
    def get_recent_memories(self, limit: int = 100, memory_type: str = "raw") -> List[Dict[str, Any]]:
        """
        获取最近的记忆（委托给底层 MemoryCortex）
        
        Args:
            limit: 数量限制
            memory_type: 记忆类型
        
        Returns:
            记忆列表
        """
        if hasattr(self.memory_cortex, 'get_recent_memories'):
            return self.memory_cortex.get_recent_memories(limit, memory_type)
        return []
    
    def delete_memories(self, ids: List[str]) -> bool:
        """
        删除记忆（委托给底层 MemoryCortex）
        
        Args:
            ids: 要删除的记忆 ID 列表
        
        Returns:
            是否成功
        """
        if hasattr(self.memory_cortex, 'delete_memories'):
            return self.memory_cortex.delete_memories(ids)
        return False
    
    def save(self):
        """保存所有数据"""
        self.memory_graph.save_graph()


class SimpleGNN:
    """
    简化的图神经网络（用于节点表示学习）
    
    注意：这是一个轻量级实现，用于演示GNN在记忆系统中的应用。
    生产环境可以考虑使用更强大的GNN库（如PyTorch Geometric, DGL）。
    """
    
    def __init__(self, embedding_dim: int = 384, hidden_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.is_initialized = False
        
        # 检查依赖
        try:
            import torch
            self.torch = torch
            self.is_initialized = True
            print("[OK] SimpleGNN: PyTorch 可用")
        except ImportError:
            print("[WARN] SimpleGNN: PyTorch 不可用，使用纯NumPy实现")
            self.torch = None
    
    def aggregate_neighbors(self, node_vector: np.ndarray, neighbor_vectors: List[np.ndarray], 
                           edge_weights: List[float]) -> np.ndarray:
        """
        聚合邻居信息（消息传递的第一步）
        
        Args:
            node_vector: 当前节点向量
            neighbor_vectors: 邻居节点向量列表
            edge_weights: 边权重列表
        
        Returns:
            聚合后的邻居表示
        """
        if not NUMPY_AVAILABLE or np is None:
            return node_vector
        
        if not neighbor_vectors:
            return node_vector
        
        # 加权平均聚合
        weighted_sum = np.zeros_like(node_vector, dtype=np.float32)
        total_weight = 0.0
        
        for neighbor_vec, weight in zip(neighbor_vectors, edge_weights):
            if len(neighbor_vec) != len(node_vector):
                continue
            weighted_sum += neighbor_vec * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return node_vector
    
    def update_node(self, node_vector: np.ndarray, aggregated_neighbor: np.ndarray) -> np.ndarray:
        """
        更新节点表示（消息传递的第二步）
        
        Args:
            node_vector: 原始节点向量
            aggregated_neighbor: 聚合的邻居信息
        
        Returns:
            更新后的节点向量
        """
        if not NUMPY_AVAILABLE or np is None:
            return node_vector
        
        # 简单的更新：加权融合
        # alpha 控制邻居信息的影响程度
        alpha = 0.3
        
        updated = (1 - alpha) * node_vector + alpha * aggregated_neighbor
        
        # 归一化
        norm = np.linalg.norm(updated)
        if norm > 0:
            updated = updated / norm * np.linalg.norm(node_vector)
        
        return updated
    
    def learn_node_representation(self, graph: nx.Graph, node_id: str, 
                                 num_iterations: int = 3) -> np.ndarray:
        """
        学习节点的GNN表示
        
        Args:
            graph: NetworkX图
            node_id: 节点ID
            num_iterations: 消息传递迭代次数
        
        Returns:
            学习后的节点表示
        """
        if not NETWORKX_AVAILABLE or not graph:
            return None
        
        if node_id not in graph:
            return None
        
        # 获取初始节点向量
        node_data = graph.nodes[node_id]
        node_vector = np.array(node_data.get("vector", []), dtype=np.float32)
        
        if len(node_vector) == 0:
            return None
        
        # 消息传递迭代
        for iteration in range(num_iterations):
            # 获取邻居
            neighbors = list(graph.neighbors(node_id))
            
            if not neighbors:
                break
            
            # 收集邻居向量和边权重
            neighbor_vectors = []
            edge_weights = []
            
            for neighbor_id in neighbors:
                neighbor_data = graph.nodes[neighbor_id]
                neighbor_vector = np.array(neighbor_data.get("vector", []), dtype=np.float32)
                
                if len(neighbor_vector) == 0:
                    continue
                
                # 获取边权重
                edge_weight = graph[node_id][neighbor_id].get("weight", 0.5)
                
                neighbor_vectors.append(neighbor_vector)
                edge_weights.append(edge_weight)
            
            # 聚合邻居信息
            aggregated = self.aggregate_neighbors(node_vector, neighbor_vectors, edge_weights)
            
            # 更新节点表示
            node_vector = self.update_node(node_vector, aggregated)
        
        return node_vector
    
    def enhance_memory_retrieval(self, graph: nx.Graph, query_vector: np.ndarray, 
                                top_k: int = 5) -> List[Dict[str, Any]]:
        """
        使用GNN增强记忆检索
        
        Args:
            graph: NetworkX图
            query_vector: 查询向量
            top_k: 返回数量
        
        Returns:
            增强后的检索结果
        """
        if not NETWORKX_AVAILABLE or not graph:
            return []
        
        results = []
        
        for node_id, node_data in graph.nodes(data=True):
            # 获取原始向量
            original_vector = np.array(node_data.get("vector", []), dtype=np.float32)
            
            if len(original_vector) == 0:
                continue
            
            # 计算原始相似度
            original_similarity = self._cosine_similarity(query_vector, original_vector)
            
            # 获取GNN增强的表示
            gnn_vector = self.learn_node_representation(graph, node_id, num_iterations=2)
            
            if gnn_vector is None:
                gnn_similarity = original_similarity
            else:
                # 计算GNN增强后的相似度
                gnn_similarity = self._cosine_similarity(query_vector, gnn_vector)
            
            # 综合相似度（GNN增强权重 0.6）
            enhanced_similarity = 0.4 * original_similarity + 0.6 * gnn_similarity
            
            results.append({
                "memory_id": node_id,
                "text": node_data.get("text", ""),
                "similarity": enhanced_similarity,
                "original_similarity": original_similarity,
                "gnn_similarity": gnn_similarity,
                "metadata": node_data.get("metadata", {}),
            })
        
        # 排序并返回
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        vec1_norm = vec1 / norm1
        vec2_norm = vec2 / norm2
        
        similarity = np.dot(vec1_norm, vec2_norm)
        return float((similarity + 1.0) / 2.0)


# 导出接口
__all__ = ["MemoryGraph", "GraphEnhancedMemoryCortex", "SimpleGNN"]