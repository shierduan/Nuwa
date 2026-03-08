"""
图神经网络记忆系统 (Graph Neural Network Memory System)

功能：基于图结构的记忆存储和检索，增强记忆关联性和长期演化能力。

核心特性：
- 记忆图构建：基于语义相似度自动构建记忆关联图
- 演化轨迹追踪：支持查询记忆的演化路径
- GNN增强：使用图神经网络进行记忆表示学习
- 路径检索：支持基于图结构的复杂记忆检索

优势：
1. 记忆关联性更强：通过图结构显式建模记忆间关系
2. 支持长期演化：追踪记忆随时间的演变轨迹
3. 上下文感知：基于图结构进行更智能的记忆检索
4. 可解释性：记忆关系可视化和路径分析
"""

import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
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

# 导入现有模块
from .riemannian_semantic_field import vectorize_state, StateVector


@dataclass
class MemoryNode:
    """记忆节点"""
    id: str
    text: str
    vector: Optional[np.ndarray] = None
    timestamp: float = 0.0
    importance: float = 0.5
    memory_type: str = "raw"
    emotions: Dict[str, float] = field(default_factory=dict)
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "text": self.text,
            "vector": self.vector.tolist() if NUMPY_AVAILABLE and isinstance(self.vector, np.ndarray) else self.vector,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "memory_type": self.memory_type,
            "emotions": self.emotions,
            "access_count": self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        """从字典创建"""
        vector = data.get("vector")
        if NUMPY_AVAILABLE and vector is not None:
            vector = np.array(vector, dtype=np.float32)
        
        return cls(
            id=data["id"],
            text=data["text"],
            vector=vector,
            timestamp=data.get("timestamp", 0.0),
            importance=data.get("importance", 0.5),
            memory_type=data.get("memory_type", "raw"),
            emotions=data.get("emotions", {}),
            access_count=data.get("access_count", 0),
        )


@dataclass
class MemoryEdge:
    """记忆边（关系）"""
    source_id: str
    target_id: str
    weight: float = 1.0  # 相似度权重
    relation_type: str = "similarity"  # similarity, temporal, causal, emotional
    timestamp: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "weight": self.weight,
            "relation_type": self.relation_type,
            "timestamp": self.timestamp,
        }


class MemoryGraph:
    """内存中的记忆图结构"""
    
    def __init__(self):
        if not NETWORKX_AVAILABLE or nx is None:
            raise ImportError("networkx 不可用，无法使用记忆图功能")
        
        # 有向图，支持因果关系
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, MemoryNode] = {}
        self.edges: Dict[Tuple[str, str], MemoryEdge] = {}
        
        # 配置参数
        self.similarity_threshold = 0.7  # 构建边的相似度阈值
        self.max_degree = 10  # 每个节点的最大连接数
        self.max_age_days = 30  # 老记忆的自动衰减
    
    def add_node(self, node: MemoryNode):
        """添加节点"""
        self.nodes[node.id] = node
        self.graph.add_node(node.id, **node.to_dict())
    
    def add_edge(self, edge: MemoryEdge):
        """添加边"""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            return False
        
        edge_key = (edge.source_id, edge.target_id)
        self.edges[edge_key] = edge
        self.graph.add_edge(edge.source_id, edge.target_id, **edge.to_dict())
        return True
    
    def calculate_similarity(self, node1: MemoryNode, node2: MemoryNode) -> float:
        """计算两个记忆节点的相似度"""
        if node1.vector is None or node2.vector is None:
            return 0.0
        
        if not NUMPY_AVAILABLE:
            return 0.0
        
        # 余弦相似度
        vec1 = node1.vector
        vec2 = node2.vector
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return float((similarity + 1.0) / 2.0)  # 映射到 [0, 1]
    
    def build_graph_from_memories(self, memories: List[Dict[str, Any]]):
        """
        从记忆列表构建图
        
        策略：
        1. 基于语义相似度构建边
        2. 基于时间顺序构建时序边
        3. 基于情绪一致性构建情绪边
        """
        # 创建节点
        for mem_data in memories:
            node = MemoryNode.from_dict(mem_data)
            self.add_node(node)
        
        # 构建语义相似度边
        node_ids = list(self.nodes.keys())
        for i, id1 in enumerate(node_ids):
            node1 = self.nodes[id1]
            
            # 记录最近的连接数
            recent_edges = 0
            
            for j in range(i + 1, len(node_ids)):
                if recent_edges >= self.max_degree:
                    break
                
                id2 = node_ids[j]
                node2 = self.nodes[id2]
                
                # 计算相似度
                similarity = self.calculate_similarity(node1, node2)
                
                if similarity >= self.similarity_threshold:
                    # 添加双向边（对称关系）
                    edge1 = MemoryEdge(
                        source_id=id1,
                        target_id=id2,
                        weight=similarity,
                        relation_type="similarity",
                        timestamp=time.time()
                    )
                    edge2 = MemoryEdge(
                        source_id=id2,
                        target_id=id1,
                        weight=similarity,
                        relation_type="similarity",
                        timestamp=time.time()
                    )
                    self.add_edge(edge1)
                    self.add_edge(edge2)
                    recent_edges += 1
        
        # 构建时序边（基于时间顺序）
        sorted_nodes = sorted(self.nodes.values(), key=lambda x: x.timestamp)
        for i in range(len(sorted_nodes) - 1):
            node1 = sorted_nodes[i]
            node2 = sorted_nodes[i + 1]
            
            # 时序边权重基于时间间隔（间隔越小，权重越高）
            time_gap = node2.timestamp - node1.timestamp
            temporal_weight = min(1.0, 1.0 / (1.0 + time_gap / 3600.0))  # 以小时为单位
            
            edge = MemoryEdge(
                source_id=node1.id,
                target_id=node2.id,
                weight=temporal_weight,
                relation_type="temporal",
                timestamp=time.time()
            )
            self.add_edge(edge)
        
        # 构建情绪边（相似情绪的记忆相互连接）
        emotion_edges = 0
        for i, id1 in enumerate(node_ids):
            node1 = self.nodes[id1]
            if not node1.emotions:
                continue
            
            for j in range(i + 1, len(node_ids)):
                if emotion_edges >= self.max_degree * 2:  # 情绪边可以更多
                    break
                
                id2 = node_ids[j]
                node2 = self.nodes[id2]
                if not node2.emotions:
                    continue
                
                # 计算情绪相似度
                emotion_sim = self._calculate_emotion_similarity(node1.emotions, node2.emotions)
                
                if emotion_sim > 0.6:
                    edge = MemoryEdge(
                        source_id=id1,
                        target_id=id2,
                        weight=emotion_sim,
                        relation_type="emotional",
                        timestamp=time.time()
                    )
                    self.add_edge(edge)
                    emotion_edges += 1
    
    def _calculate_emotion_similarity(self, emotions1: Dict[str, float], emotions2: Dict[str, float]) -> float:
        """计算情绪相似度"""
        if not emotions1 or not emotions2:
            return 0.0
        
        # 获取所有情绪键
        all_keys = set(emotions1.keys()) | set(emotions2.keys())
        
        if not all_keys:
            return 0.0
        
        # 计算余弦相似度
        vec1 = np.array([emotions1.get(k, 0.0) for k in all_keys])
        vec2 = np.array([emotions2.get(k, 0.0) for k in all_keys])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return float((similarity + 1.0) / 2.0)
    
    def get_memory_trajectory(self, memory_id: str) -> List[str]:
        """
        获取记忆的演化轨迹（到根节点的路径）
        
        返回从根节点到该记忆的路径上的所有节点ID
        """
        if memory_id not in self.nodes:
            return []
        
        # 寻找根节点（入度为0的节点，或时间最早的节点）
        root_nodes = [n for n, d in self.graph.in_degree() if d == 0]
        
        if not root_nodes:
            # 如果没有明确的根节点，选择时间最早的节点作为根
            earliest_node = min(self.nodes.values(), key=lambda x: x.timestamp)
            root_nodes = [earliest_node.id]
        
        # 尝试找到到任意根节点的最短路径
        shortest_path = None
        for root in root_nodes:
            try:
                path = nx.shortest_path(self.graph, root, memory_id)
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        
        return shortest_path if shortest_path else []
    
    def find_related_memories(self, query_id: str, max_depth: int = 3, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        查找相关记忆（基于图遍历）
        
        Args:
            query_id: 查询节点ID
            max_depth: 最大遍历深度
            top_k: 返回Top K个相关记忆
        
        Returns:
            [(node_id, relevance_score), ...] 按相关度排序
        """
        if query_id not in self.nodes:
            return []
        
        # BFS遍历
        visited = set()
        queue = deque([(query_id, 0, 1.0)])  # (node_id, depth, relevance)
        related = []
        
        while queue:
            node_id, depth, relevance = queue.popleft()
            
            if node_id in visited or depth > max_depth:
                continue
            
            visited.add(node_id)
            
            # 跳过查询节点本身
            if node_id != query_id:
                related.append((node_id, relevance))
            
            # 扩展邻居
            if depth < max_depth:
                for neighbor in self.graph.neighbors(node_id):
                    if neighbor not in visited:
                        edge_data = self.graph.get_edge_data(node_id, neighbor)
                        edge_weight = edge_data.get("weight", 1.0)
                        new_relevance = relevance * edge_weight
                        queue.append((neighbor, depth + 1, new_relevance))
        
        # 按相关度排序
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:top_k]
    
    def get_community_clusters(self) -> List[List[str]]:
        """
        获取记忆社区（聚类）
        
        使用社区检测算法识别记忆群组
        """
        if not NETWORKX_AVAILABLE:
            return []
        
        try:
            # 使用弱连通分量作为简单社区
            communities = list(nx.weakly_connected_components(self.graph))
            
            # 按社区大小排序
            communities = sorted(communities, key=len, reverse=True)
            
            return [list(community) for community in communities]
        except:
            return []
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图统计信息"""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1),
            "density": nx.density(self.graph),
            "communities": len(self.get_community_clusters()),
        }
    
    def prune_old_edges(self, max_age_days: Optional[int] = None):
        """修剪过时的边"""
        if max_age_days is None:
            max_age_days = self.max_age_days
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 3600)
        
        edges_to_remove = []
        for (u, v), edge in self.edges.items():
            if edge.timestamp < cutoff_time:
                edges_to_remove.append((u, v))
        
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
            del self.edges[(u, v)]


class GraphBasedMemory:
    """
    图神经网络记忆系统
    
    集成到现有 MemoryCortex，提供增强的记忆关联和演化能力
    """
    
    def __init__(self, project_name: str, data_dir: str = "data"):
        self.project_name = project_name
        self.data_dir = data_dir
        self.graph_file = os.path.join(data_dir, project_name, "memory_graph.json")
        
        # 内存中的图结构
        self.memory_graph: Optional[MemoryGraph] = None
        
        # 是否启用GNN增强（可选）
        self.gnn_enabled = False
        self.gnn_model = None
        
        # 缓存最近的查询结果
        self.query_cache = {}
        
        print("[OK] GraphBasedMemory 初始化完成")
    
    def initialize_graph(self, memories: List[Dict[str, Any]]):
        """
        初始化记忆图
        
        Args:
            memories: 从 MemoryCortex 获取的记忆列表
        """
        if not NETWORKX_AVAILABLE:
            print("[WARN] networkx 不可用，无法使用图记忆功能")
            return
        
        self.memory_graph = MemoryGraph()
        self.memory_graph.build_graph_from_memories(memories)
        
        # 保存到磁盘
        self.save_graph()
        
        stats = self.memory_graph.get_graph_stats()
        print(f"[OK] 记忆图已构建: {stats['node_count']} 节点, {stats['edge_count']} 边, {stats['communities']} 社区")
    
    def update_graph(self, new_memory: Dict[str, Any]):
        """
        更新图：添加新记忆并连接相关记忆
        
        Args:
            new_memory: 新的记忆数据
        """
        if self.memory_graph is None:
            return
        
        # 添加新节点
        new_node = MemoryNode.from_dict(new_memory)
        self.memory_graph.add_node(new_node)
        
        # 与现有记忆建立连接
        for existing_id, existing_node in self.memory_graph.nodes.items():
            if existing_id == new_node.id:
                continue
            
            # 计算相似度
            similarity = self.memory_graph.calculate_similarity(new_node, existing_node)
            
            if similarity >= self.memory_graph.similarity_threshold:
                # 添加双向边
                edge1 = MemoryEdge(
                    source_id=new_node.id,
                    target_id=existing_id,
                    weight=similarity,
                    relation_type="similarity",
                    timestamp=time.time()
                )
                edge2 = MemoryEdge(
                    source_id=existing_id,
                    target_id=new_node.id,
                    weight=similarity,
                    relation_type="similarity",
                    timestamp=time.time()
                )
                self.memory_graph.add_edge(edge1)
                self.memory_graph.add_edge(edge2)
        
        # 保存
        self.save_graph()
    
    def get_memory_trajectory(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        获取记忆演化轨迹
        
        Returns:
            轨迹上的记忆节点列表（按时间顺序）
        """
        if self.memory_graph is None:
            return []
        
        trajectory_ids = self.memory_graph.get_memory_trajectory(memory_id)
        
        if not trajectory_ids:
            return []
        
        # 获取节点详情
        trajectory = []
        for node_id in trajectory_ids:
            if node_id in self.memory_graph.nodes:
                trajectory.append(self.memory_graph.nodes[node_id].to_dict())
        
        # 按时间排序
        trajectory.sort(key=lambda x: x["timestamp"])
        
        return trajectory
    
    def enhanced_retrieval(
        self,
        query_text: str,
        query_vector: Optional[np.ndarray] = None,
        top_k: int = 5,
        use_graph_traversal: bool = True,
        min_similarity: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        增强的记忆检索（结合向量搜索和图遍历）
        
        Args:
            query_text: 查询文本
            query_vector: 查询向量（可选）
            top_k: 返回Top K个结果
            use_graph_traversal: 是否使用图遍历增强
            min_similarity: 最小相似度阈值
        
        Returns:
            检索结果列表
        """
        if self.memory_graph is None:
            return []
        
        if not NUMPY_AVAILABLE:
            return []
        
        # 生成查询向量
        if query_vector is None:
            state_vec = vectorize_state(query_text)
            if state_vec is None or state_vec.vector is None:
                return []
            query_vector = state_vec.vector
        
        results = []
        
        # 1. 基于向量相似度的初步检索
        for node_id, node in self.memory_graph.nodes.items():
            if node.vector is None:
                continue
            
            # 计算余弦相似度
            norm_query = np.linalg.norm(query_vector)
            norm_node = np.linalg.norm(node.vector)
            
            if norm_query == 0 or norm_node == 0:
                continue
            
            similarity = np.dot(query_vector, node.vector) / (norm_query * norm_node)
            similarity = float((similarity + 1.0) / 2.0)
            
            if similarity >= min_similarity:
                results.append({
                    "node": node,
                    "vector_similarity": similarity,
                    "graph_relevance": 0.0,  # 初始值
                    "combined_score": similarity,
                })
        
        if not results:
            return []
        
        # 2. 使用图遍历增强（如果启用）
        if use_graph_traversal and len(results) > 0:
            # 找到最相关的节点
            best_node = max(results, key=lambda x: x["vector_similarity"])
            best_node_id = best_node["node"].id
            
            # 图遍历查找相关记忆
            related = self.memory_graph.find_related_memories(
                best_node_id,
                max_depth=3,
                top_k=top_k * 2
            )
            
            # 将图相关性合并到结果中
            related_dict = {node_id: relevance for node_id, relevance in related}
            
            for result in results:
                node_id = result["node"].id
                if node_id in related_dict:
                    result["graph_relevance"] = related_dict[node_id]
                    # 综合分数 = 0.7 * 向量相似度 + 0.3 * 图相关性
                    result["combined_score"] = 0.7 * result["vector_similarity"] + 0.3 * related_dict[node_id]
        
        # 3. 排序并返回
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # 格式化输出
        formatted_results = []
        for result in results[:top_k]:
            node_dict = result["node"].to_dict()
            node_dict["vector_similarity"] = result["vector_similarity"]
            node_dict["graph_relevance"] = result["graph_relevance"]
            node_dict["combined_score"] = result["combined_score"]
            formatted_results.append(node_dict)
        
        return formatted_results
    
    def get_memory_communities(self) -> List[Dict[str, Any]]:
        """获取记忆社区（聚类）"""
        if self.memory_graph is None:
            return []
        
        communities = self.memory_graph.get_community_clusters()
        
        # 获取每个社区的代表性信息
        community_info = []
        for i, community in enumerate(communities):
            if not community:
                continue
            
            # 计算社区统计
            nodes = [self.memory_graph.nodes[node_id] for node_id in community if node_id in self.memory_graph.nodes]
            
            if not nodes:
                continue
            
            # 找出最中心的节点（连接最多的）
            degrees = dict(self.memory_graph.graph.degree(community))
            center_node_id = max(degrees, key=degrees.get) if degrees else community[0]
            center_node = self.memory_graph.nodes[center_node_id]
            
            community_info.append({
                "community_id": i,
                "size": len(community),
                "center_node_id": center_node_id,
                "center_text": center_node.text[:100],
                "node_ids": community,
            })
        
        return community_info
    
    def get_graph_insights(self) -> Dict[str, Any]:
        """获取图洞察信息"""
        if self.memory_graph is None:
            return {}
        
        stats = self.memory_graph.get_graph_stats()
        
        # 找出关键节点（中心性）
        try:
            # 度中心性
            degree_centrality = nx.degree_centrality(self.memory_graph.graph)
            top_central = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:3]
            
            central_nodes = []
            for node_id, score in top_central:
                if node_id in self.memory_graph.nodes:
                    node = self.memory_graph.nodes[node_id]
                    central_nodes.append({
                        "id": node_id,
                        "centrality": score,
                        "text": node.text[:80],
                    })
            
            stats["central_nodes"] = central_nodes
        except:
            stats["central_nodes"] = []
        
        # 社区信息
        stats["communities_detail"] = self.get_memory_communities()[:5]  # 只返回前5个
        
        return stats
    
    def save_graph(self):
        """保存图到磁盘"""
        if self.memory_graph is None:
            return
        
        try:
            os.makedirs(os.path.dirname(self.graph_file), exist_ok=True)
            
            # 序列化图数据
            data = {
                "nodes": {node_id: node.to_dict() for node_id, node in self.memory_graph.nodes.items()},
                "edges": {f"{u}|{v}": edge.to_dict() for (u, v), edge in self.memory_graph.edges.items()},
                "metadata": {
                    "created_at": time.time(),
                    "stats": self.memory_graph.get_graph_stats(),
                }
            }
            
            with open(self.graph_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[OK] 记忆图已保存: {self.graph_file}")
        except Exception as e:
            print(f"[WARN] 保存记忆图失败: {e}")
    
    def load_graph(self):
        """从磁盘加载图"""
        if not NETWORKX_AVAILABLE:
            return
        
        if not os.path.exists(self.graph_file):
            print(f"[WARN] 记忆图文件不存在: {self.graph_file}")
            return
        
        try:
            with open(self.graph_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.memory_graph = MemoryGraph()
            
            # 加载节点
            for node_id, node_data in data["nodes"].items():
                node = MemoryNode.from_dict(node_data)
                self.memory_graph.add_node(node)
            
            # 加载边
            for edge_key, edge_data in data["edges"].items():
                u, v = edge_key.split("|")
                edge = MemoryEdge(
                    source_id=edge_data["source"],
                    target_id=edge_data["target"],
                    weight=edge_data["weight"],
                    relation_type=edge_data["relation_type"],
                    timestamp=edge_data["timestamp"],
                )
                self.memory_graph.add_edge(edge)
            
            stats = data.get("metadata", {}).get("stats", {})
            print(f"[OK] 记忆图已加载: {stats.get('node_count', 0)} 节点, {stats.get('edge_count', 0)} 边")
        except Exception as e:
            print(f"[WARN] 加载记忆图失败: {e}")
            self.memory_graph = None
    
    def enable_gnn(self, gnn_model_path: Optional[str] = None):
        """
        启用GNN增强（预留接口）
        
        未来可以集成PyG或DGL等图神经网络库
        """
        self.gnn_enabled = True
        print("[WARN] GNN增强功能预留接口，需要额外依赖库")


class GraphMemoryIntegration:
    """
    图记忆系统与现有 MemoryCortex 的集成层
    
    提供统一接口，将图记忆功能无缝集成到现有系统
    """
    
    def __init__(self, memory_cortex, graph_memory: GraphBasedMemory):
        self.memory_cortex = memory_cortex
        self.graph_memory = graph_memory
    
    async def store_with_graph(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """
        存储记忆并更新图
        
        Args:
            text: 记忆文本
            metadata: 元数据
        """
        # 1. 存储到 MemoryCortex
        if hasattr(self.memory_cortex, 'store_memory'):
            self.memory_cortex.store_memory(text, metadata)
        
        # 2. 从 MemoryCortex 重新获取所有记忆（包含新存储的）
        # 注意：这里需要 MemoryCortex 提供获取所有记忆的方法
        # 如果没有，可以暂时跳过图更新，或者实现增量更新
        
        # 3. 更新图（简化版：只添加新节点，不重新构建整个图）
        if self.graph_memory.memory_graph:
            # 构建新记忆数据
            new_memory = {
                "id": f"{int(time.time() * 1000)}_{hash(text) % 10000}",
                "text": text,
                "vector": None,  # 需要从 MemoryCortex 获取
                "timestamp": time.time(),
                "importance": metadata.get("importance", 0.5) if metadata else 0.5,
                "memory_type": metadata.get("type", "raw") if metadata else "raw",
                "emotions": metadata.get("emotions", {}) if metadata else {},
                "access_count": 0,
            }
            
            # 尝试获取向量
            if hasattr(self.memory_cortex, 'embedding_model') and self.memory_cortex.embedding_model:
                try:
                    vector = self.memory_cortex.embedding_model.encode(text, convert_to_numpy=True)
                    new_memory["vector"] = vector.tolist()
                except:
                    pass
            
            self.graph_memory.update_graph(new_memory)
    
    def enhanced_recall(
        self,
        query_text: str,
        top_k: int = 5,
        use_graph: bool = True,
        emotion_vector=None,
        emotion_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        增强的记忆回忆（结合向量检索和图遍历）
        
        Args:
            query_text: 查询文本
            top_k: 返回数量
            use_graph: 是否使用图增强
            emotion_vector: 情绪向量
            emotion_weight: 情绪权重
        
        Returns:
            记忆列表
        """
        # 1. 使用 MemoryCortex 进行基础检索
        if hasattr(self.memory_cortex, 'recall_by_emotion'):
            base_results = self.memory_cortex.recall_by_emotion(
                query_text=query_text,
                current_emotion_vector=emotion_vector,
                top_k=top_k * 2,  # 多取一些用于重排序
                emotion_weight=emotion_weight,
            )
        else:
            base_results = []
        
        if not use_graph or self.graph_memory.memory_graph is None:
            return base_results[:top_k]
        
        # 2. 使用图增强重排序
        if not base_results:
            # 如果基础检索无结果，使用图检索
            return self.graph_memory.enhanced_retrieval(
                query_text=query_text,
                top_k=top_k,
                use_graph_traversal=True,
            )
        
        # 3. 对基础结果进行图增强评分
        enhanced_results = []
        for result in base_results:
            node_id = result.get("metadata", {}).get("id", "")
            
            if node_id and self.graph_memory.memory_graph and node_id in self.graph_memory.memory_graph.nodes:
                # 查找相关记忆（图遍历）
                related = self.graph_memory.memory_graph.find_related_memories(
                    node_id,
                    max_depth=2,
                    top_k=3
                )
                
                # 计算图相关性分数
                graph_score = sum(relevance for _, relevance in related) / max(len(related), 1)
                
                # 综合分数（保留原始相似度，增加图相关性）
                combined_score = result["similarity"] + graph_score * 0.2
                
                enhanced_result = result.copy()
                enhanced_result["graph_relevance"] = graph_score
                enhanced_result["combined_similarity"] = combined_score
                enhanced_result["related_nodes"] = related
                
                enhanced_results.append(enhanced_result)
            else:
                result["graph_relevance"] = 0.0
                result["combined_similarity"] = result["similarity"]
                result["related_nodes"] = []
                enhanced_results.append(result)
        
        # 按综合分数排序
        enhanced_results.sort(key=lambda x: x["combined_similarity"], reverse=True)
        
        return enhanced_results[:top_k]
    
    def get_trajectory(self, memory_id: str) -> List[Dict[str, Any]]:
        """获取记忆轨迹"""
        return self.graph_memory.get_memory_trajectory(memory_id)
    
    def get_communities(self) -> List[Dict[str, Any]]:
        """获取记忆社区"""
        return self.graph_memory.get_memory_communities()
    
    def get_insights(self) -> Dict[str, Any]:
        """获取图洞察"""
        return self.graph_memory.get_graph_insights()


# 使用示例
async def demo_graph_memory():
    """演示图记忆系统"""
    print("=" * 60)
    print("图神经网络记忆系统演示")
    print("=" * 60)
    
    # 模拟记忆数据
    memories = [
        {
            "id": "m1",
            "text": "[2025-12-20 10:00:00] 用户: 你好，我是张三",
            "vector": np.random.rand(384).tolist(),
            "timestamp": 1734672000.0,
            "importance": 0.8,
            "memory_type": "raw",
            "emotions": {"happy": 0.6, "curious": 0.4},
            "access_count": 1,
        },
        {
            "id": "m2",
            "text": "[2025-12-20 10:05:00] 用户: 今天天气真好",
            "vector": np.random.rand(384).tolist(),
            "timestamp": 1734672300.0,
            "importance": 0.5,
            "memory_type": "raw",
            "emotions": {"happy": 0.7},
            "access_count": 1,
        },
        {
            "id": "m3",
            "text": "[2025-12-20 10:10:00] 用户: 我喜欢编程",
            "vector": np.random.rand(384).tolist(),
            "timestamp": 1734672600.0,
            "importance": 0.7,
            "memory_type": "raw",
            "emotions": {"happy": 0.5, "excited": 0.5},
            "access_count": 1,
        },
        {
            "id": "m4",
            "text": "[2025-12-20 10:15:00] 用户: 你是谁？",
            "vector": np.random.rand(384).tolist(),
            "timestamp": 1734672900.0,
            "importance": 0.6,
            "memory_type": "raw",
            "emotions": {"curious": 0.8},
            "access_count": 1,
        },
    ]
    
    # 创建图记忆系统
    graph_memory = GraphBasedMemory("demo", "data")
    graph_memory.initialize_graph(memories)
    
    # 演示1: 获取记忆轨迹
    print("\n1. 记忆轨迹查询:")
    trajectory = graph_memory.get_memory_trajectory("m3")
    print(f"   m3 的轨迹: {[node['id'] for node in trajectory]}")
    
    # 演示2: 增强检索
    print("\n2. 增强检索:")
    results = graph_memory.enhanced_retrieval("编程", top_k=3)
    for r in results:
        print(f"   - {r['id']}: 相似度={r['vector_similarity']:.3f}, 图相关={r['graph_relevance']:.3f}, 综合={r['combined_score']:.3f}")
    
    # 演示3: 社区发现
    print("\n3. 记忆社区:")
    communities = graph_memory.get_memory_communities()
    for c in communities:
        print(f"   社区 {c['community_id']}: {c['size']} 个记忆，中心: {c['center_text']}")
    
    # 演示4: 图洞察
    print("\n4. 图洞察:")
    insights = graph_memory.get_graph_insights()
    print(f"   节点数: {insights['node_count']}")
    print(f"   边数: {insights['edge_count']}")
    print(f"   社区数: {insights['communities']}")
    print(f"   中心节点: {len(insights.get('central_nodes', []))} 个")
    
    print("\n[OK] 演示完成")


if __name__ == "__main__":
    asyncio.run(demo_graph_memory())