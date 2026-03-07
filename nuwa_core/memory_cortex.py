"""
记忆皮层模块 (Memory Cortex Module)

功能：封装 LanceDB 连接，提供基于情绪一致性的记忆检索接口。

核心功能：
- MemoryCortex: 记忆皮层类，封装 LanceDB 操作
- recall_by_emotion(): RAG 检索接口，优先检索语义相关的记忆，并根据情绪向量进行加权
"""

import os
import json
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from difflib import SequenceMatcher

# 延迟导入可选依赖，避免类型注解导致的导入错误
NUMPY_AVAILABLE = False
PYARROW_AVAILABLE = False
LANCEDB_AVAILABLE = False
EMBEDDING_AVAILABLE = False

np = None
pa = None
lancedb = None
SentenceTransformer = None

# 尝试导入可选依赖
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass

try:
    import pyarrow as pa
    PYARROW_AVAILABLE = True
except ImportError:
    pass

try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    pass

from .model_utils import ensure_embedding_model_dir


class MemoryCortex:
    """
    记忆皮层类
    
    封装 LanceDB 连接，提供记忆存储和检索功能。
    支持基于语义相似度和情绪一致性的记忆检索。
    """
    
    # 向量维度（all-MiniLM-L6-v2 的维度是 384）
    VECTOR_DIM = 384
    
    def __init__(self, project_name: str, data_dir: str = "data"):
        """
        初始化记忆皮层
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录（默认 "data"）
        """
        self.project_name = project_name
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, project_name, "memory.lance")
        
        # 定义显式 Schema（避免 PyArrow 自动推断错误）
        self.schema = self._define_schema()
        
        # 初始化 LanceDB 连接
        self.db = None
        self.table = None
        self._init_db()
        
        # 初始化 Embedding 模型
        self.embedding_model = None
        self._init_embedding_model()
    
    def _define_schema(self):
        """
        定义显式 Schema

        Returns:
            PyArrow Schema 对象或 None
        """
        if not PYARROW_AVAILABLE or pa is None:
            return None

        return pa.schema([
            pa.field("id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),  # 384维向量
            pa.field("emotion_vector", pa.string()),  # JSON 字符串（嵌入使用）
            pa.field("timestamp", pa.float64()),
            pa.field("importance", pa.float32()),
            pa.field("type", pa.string()),  # raw / summary / other
            pa.field("emotions", pa.string()),  # JSON 字典（情绪标签）
            pa.field("access_count", pa.int64()),
        ])
    
    def _init_db(self):
        """初始化 LanceDB 数据库"""
        if not LANCEDB_AVAILABLE:
            print("[WARN] LanceDB 不可用，记忆检索功能将受限")
            return
        
        if not PYARROW_AVAILABLE:
            print("[WARN] PyArrow 不可用，无法定义 Schema")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # 连接数据库
            self.db = lancedb.connect(self.db_path)
            
            # 检查表是否存在
            table_names = self.db.table_names()
            if "memory" not in table_names:
                # 表不存在，使用显式 Schema 创建空表
                if self.schema:
                    # 创建一个空的数据列表来初始化表
                    empty_data = [{
                        "id": "",
                        "text": "",
                        "vector": [0.0] * self.VECTOR_DIM,
                        "emotion_vector": "",
                        "timestamp": 0.0,
                        "importance": 0.0,
                        "type": "raw",
                        "emotions": "",
                        "access_count": 0,
                    }]
                    self.table = self.db.create_table(
                        "memory",
                        empty_data,
                        schema=self.schema,
                        mode="overwrite"
                    )
                    # 创建后立即删除这个空记录
                    # 注意：LanceDB 可能不支持直接删除，所以我们先创建空表，后续插入时覆盖
                    print(f"[INFO] 创建新的记忆表: {self.db_path}")
                else:
                    print("[WARN] Schema 未定义，无法创建表")
            else:
                # 表已存在，尝试打开表
                try:
                    self.table = self.db.open_table("memory")
                    if self.table:
                        if not self._schema_is_compatible(self.table.schema.names):
                            print("[WARN] 检测到旧的记忆表结构，正在重建以支持 Memory Dreamer...")
                            self.db.drop_table("memory")
                            self._create_empty_table()
                            self.table = self.db.open_table("memory")
                        else:
                            print(f"[OK] 已加载记忆表: {self.db_path}")
                    else:
                        print(f"[WARN] 表打开失败，尝试重新创建...")
                        self._create_empty_table()
                        self.table = self.db.open_table("memory")
                        print(f"[OK] 已重新创建记忆表: {self.db_path}")
                except Exception as e:
                    print(f"[WARN] 打开表失败: {e}，尝试重新创建...")
                    try:
                        self.db.drop_table("memory")
                        self._create_empty_table()
                        self.table = self.db.open_table("memory")
                        print(f"[OK] 已重新创建记忆表: {self.db_path}")
                    except Exception as e2:
                        print(f"[WARN] 重新创建表也失败: {e2}")
                        self.table = None
        except Exception as e:
            print(f"[WARN] 初始化 LanceDB 失败: {e}")
            import traceback
            traceback.print_exc()
            self.db = None
            self.table = None

    def _create_empty_table(self):
        """创建一个空的 LanceDB 表以匹配最新 Schema"""
        empty_data = [{
            "id": "",
            "text": "",
            "vector": [0.0] * self.VECTOR_DIM,
            "emotion_vector": "",
            "timestamp": 0.0,
            "importance": 0.0,
            "type": "raw",
            "emotions": "",
            "access_count": 0,
        }]
        self.table = self.db.create_table(
            "memory",
            empty_data,
            schema=self.schema,
            mode="overwrite"
        )

    def _schema_is_compatible(self, names: List[str]) -> bool:
        required = {"id", "text", "vector", "emotion_vector", "timestamp", "importance", "type", "emotions", "access_count"}
        return required.issubset(set(names))

    def _init_embedding_model(self):
        """初始化 Embedding 模型"""
        if not EMBEDDING_AVAILABLE or SentenceTransformer is None:
            print("[WARN] SentenceTransformer 不可用，无法生成向量")
            return
        
        try:
            # 获取模型路径
            model_path = ensure_embedding_model_dir(SentenceTransformer)
            if not model_path:
                print("[WARN] 无法加载 Embedding 模型：缺少可用的本地目录，且自动下载失败。")
                return
            
            # 加载模型
            self.embedding_model = SentenceTransformer(model_path, local_files_only=True)
            print(f"[OK] 已加载 Embedding 模型: {model_path}")
        except Exception as e:
            print(f"[WARN] 初始化 Embedding 模型失败: {e}")
            self.embedding_model = None
    
    def store_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None, timestamp: Optional[datetime] = None):
        """
        存储记忆（内在时间感知版本）
        
        关键特性：将时间戳直接融合到文本内容中，格式为 [YYYY-MM-DD HH:MM:SS] 文本内容
        这样小模型（4B）可以直接从检索到的文本中读取时间信息，实现时间感知推理。
        
        Args:
            text: 记忆文本（原始文本，时间戳会自动添加）
            metadata: 可选的元数据（如时间戳、情绪向量等）
            timestamp: 可选的 datetime 对象，如果为 None 则使用当前时间
        """
        if not LANCEDB_AVAILABLE or self.db is None:
            return
        
        if not self.embedding_model:
            print("[WARN] Embedding 模型未加载，无法存储记忆")
            return
        
        if not self.table:
            print("[WARN] 记忆表未初始化，无法存储记忆")
            return
        
        try:
            # 处理时间戳：优先使用传入的 timestamp，其次使用 metadata 中的 timestamp，最后使用当前时间
            if timestamp is not None:
                memory_datetime = timestamp
            elif metadata and "timestamp" in metadata and metadata["timestamp"] is not None:
                # 如果 metadata 中是 float（Unix 时间戳），转换为 datetime
                ts_value = metadata["timestamp"]
                if isinstance(ts_value, (int, float)):
                    memory_datetime = datetime.fromtimestamp(float(ts_value))
                elif isinstance(ts_value, datetime):
                    memory_datetime = ts_value
                else:
                    memory_datetime = datetime.now()
            else:
                memory_datetime = datetime.now()
            
            # 格式化时间戳字符串：YYYY-MM-DD HH:MM:SS
            timestamp_str = memory_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            # 关键改进：时间戳不用于生成向量，避免污染语义空间
            # 原因：时间戳中的数字和符号（如 [2026-03-06 02:21:00]）会在向量空间中产生噪声
            #       导致相近时间的消息向量变得相似，而非基于语义相似
            # 方案：仅使用纯文本内容生成 embedding，时间戳单独存储在 text 字段用于展示
            
            # 使用纯文本生成向量（不包含时间戳）
            vector = self.embedding_model.encode(text, convert_to_numpy=True)
            
            # 存储时将时间戳融合到文本中（用于检索结果展示）
            # 格式：[YYYY-MM-DD HH:MM:SS] 文本内容
            fused_text = f"[{timestamp_str}] {text}"
            
            # 确保向量维度正确
            if len(vector) != self.VECTOR_DIM:
                print(f"[WARN] 向量维度不匹配: 期望 {self.VECTOR_DIM}，实际 {len(vector)}")
                return
            
            # 准备数据（确保符合 Schema）
            memory_id = f"{int(time.time() * 1000)}_{hash(text) % 10000}"
            
            # 处理 emotion_vector（转换为 JSON 字符串）
            emotion_vector_str = ""
            if metadata and "emotion_vector" in metadata and metadata["emotion_vector"] is not None:
                emotion_vec = metadata["emotion_vector"]
                if isinstance(emotion_vec, np.ndarray):
                    emotion_vec = emotion_vec.tolist()
                elif not isinstance(emotion_vec, list):
                    emotion_vec = list(emotion_vec)
                emotion_vector_str = json.dumps(emotion_vec, ensure_ascii=False)
            
            # 情绪字典（用于 Memory Dreamer）
            emotions_dict = {}
            if metadata and "emotions" in metadata and metadata["emotions"] is not None:
                emotions_dict = metadata["emotions"]
            elif hasattr(self, "state") and self.state is not None:
                emotions_dict = getattr(self.state, "emotional_spectrum", {})
            emotions_str = json.dumps(emotions_dict, ensure_ascii=False)
            
            # 将 datetime 转换为 Unix 时间戳（用于数据库存储）
            memory_timestamp = float(memory_datetime.timestamp())
            
            # 构建符合 Schema 的数据
            # 注意：text 字段存储融合后的文本（包含时间戳），这样检索时可以直接看到时间
            data = {
                "id": memory_id,
                "text": fused_text,  # 存储融合后的文本（包含时间戳）
                "vector": vector.tolist(),  # 使用融合文本生成的向量
                "emotion_vector": emotion_vector_str,  # JSON 字符串
                "timestamp": memory_timestamp,  # Unix 时间戳（用于排序和查询）
                "importance": float(metadata.get("importance", 0.5)) if metadata else 0.5,
                "type": str(metadata.get("type", "raw")) if metadata else "raw",
                "emotions": emotions_str,
                "access_count": int(metadata.get("access_count", 0)) if metadata else 0,
            }
            
            # 插入数据
            self.table.add([data])

            # 终端调试输出：向量写入（显示融合后的文本）
            preview = fused_text.replace("\n", " ")[:100]
            print(f"[OK] [Memory][WRITE] 已存储记忆 (id={memory_id}, time={timestamp_str}, importance={data['importance']:.2f}): {preview}...")
        except Exception as e:
            print(f"[WARN] 存储记忆失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _calculate_string_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个字符串的相似度（0.0-1.0）
        
        使用 SequenceMatcher 计算相似度，适用于检测重复查询。
        
        Args:
            text1: 第一个字符串
            text2: 第二个字符串
        
        Returns:
            float: 相似度分数（0.0-1.0），1.0 表示完全相同
        """
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
    
    def _extract_user_input_from_memory(self, memory_text: str) -> Optional[str]:
        """
        从记忆文本中提取用户输入部分
        
        记忆格式可能是：
        - "[timestamp] 用户: ... 女娲: ..."
        - "用户: ... 女娲: ..."
        
        Args:
            memory_text: 记忆文本
        
        Returns:
            用户输入部分，如果无法提取则返回 None
        """
        if not memory_text:
            return None
        
        # 移除时间戳前缀（如果存在）
        text = memory_text
        if text.startswith("[") and "]" in text[:25]:
            # 找到第一个 ] 的位置
            end_idx = text.find("]", 1)
            if end_idx > 0:
                text = text[end_idx + 1:].strip()
        
        # 查找 "用户:" 或 "用户：" 标记
        user_markers = ["用户:", "用户："]
        for marker in user_markers:
            if marker in text:
                # 提取用户输入部分（到 "女娲:" 或 "女娲：" 之前）
                start_idx = text.find(marker)
                user_part = text[start_idx + len(marker):].strip()
                
                # 查找女娲回复的开始位置
                nuwa_markers = ["女娲:", "女娲："]
                for nuwa_marker in nuwa_markers:
                    if nuwa_marker in user_part:
                        end_idx = user_part.find(nuwa_marker)
                        user_part = user_part[:end_idx].strip()
                        break
                
                return user_part
        
        return None
    
    def _migration_fix_timestamps(self, default_timestamp: Optional[datetime] = None) -> int:
        """
        数据迁移辅助方法：为旧记忆（没有时间戳前缀的）添加默认时间戳
        
        这个方法会遍历所有记忆，检查文本是否以 [YYYY-MM-DD HH:MM:SS] 格式开头。
        如果没有，则使用 timestamp 字段（如果存在）或默认时间戳来添加前缀。
        
        Args:
            default_timestamp: 默认时间戳（如果记忆没有 timestamp 字段）。如果为 None，使用当前时间。
        
        Returns:
            int: 修复的记忆数量
        
        Note:
            这是一个可选的数据迁移方法，用于处理升级前的旧数据。
            建议在首次部署新版本时运行一次。
        """
        if not LANCEDB_AVAILABLE or self.table is None:
            print("[WARN] LanceDB 不可用，无法执行迁移")
            return 0
        
        if default_timestamp is None:
            default_timestamp = datetime.now()
        
        try:
            # 获取所有记忆
            df = self.table.to_pandas()
            if df.empty:
                print("[INFO] 没有记忆需要迁移")
                return 0
            
            fixed_count = 0
            updates = []
            
            # 检查时间戳前缀的正则表达式
            import re
            timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')
            
            for idx, row in df.iterrows():
                text = str(row.get("text", ""))
                memory_id = str(row.get("id", ""))
                timestamp_value = row.get("timestamp", 0.0)
                
                # 检查是否已经有时间戳前缀
                if timestamp_pattern.match(text):
                    continue  # 已经有时间戳前缀，跳过
                
                # 确定要使用的时间戳
                if timestamp_value and float(timestamp_value) > 0:
                    memory_datetime = datetime.fromtimestamp(float(timestamp_value))
                else:
                    memory_datetime = default_timestamp
                
                # 格式化时间戳字符串
                timestamp_str = memory_datetime.strftime('%Y-%m-%d %H:%M:%S')
                
                # 构建融合后的文本（用于存储和展示）
                fused_text = f"[{timestamp_str}] {text}"
                
                # 关键改进：使用纯文本生成向量，避免时间戳污染语义空间
                if self.embedding_model:
                    try:
                        vector = self.embedding_model.encode(text, convert_to_numpy=True)
                        if len(vector) != self.VECTOR_DIM:
                            print(f"[WARN] 记忆 {memory_id} 向量维度不匹配，跳过")
                            continue
                    except Exception as e:
                        print(f"[WARN] 记忆 {memory_id} 向量生成失败：{e}，跳过")
                        continue
                else:
                    print(f"[WARN] Embedding 模型未加载，无法更新向量，跳过记忆 {memory_id}")
                    continue
                
                # 准备更新数据
                try:
                    # LanceDB 的删除操作
                    for memory_id in ids_to_update:
                        self.table.delete(f"id = '{memory_id}'")
                except Exception as e:
                    print(f"[WARN] 删除旧记录时出错: {e}")
                    # 如果删除失败，尝试直接插入（可能会产生重复，但至少数据会更新）
                
                # 插入更新后的记录
                try:
                    # 需要获取完整的记录数据（不仅仅是更新的字段）
                    full_updates = []
                    for update_data in updates:
                        memory_id = update_data["id"]
                        # 从原始数据中获取其他字段
                        original_row = df[df["id"] == memory_id].iloc[0]
                        full_data = {
                            "id": update_data["id"],
                            "text": update_data["text"],
                            "vector": update_data["vector"],
                            "emotion_vector": str(original_row.get("emotion_vector", "")),
                            "timestamp": float(original_row.get("timestamp", 0.0)),
                            "importance": float(original_row.get("importance", 0.5)),
                            "type": str(original_row.get("type", "raw")),
                            "emotions": str(original_row.get("emotions", "{}")),
                            "access_count": int(original_row.get("access_count", 0)),
                        }
                        full_updates.append(full_data)
                    
                    self.table.add(full_updates)
                    print(f"[OK] 已迁移 {fixed_count} 条记忆，添加了时间戳前缀")
                except Exception as e:
                    print(f"[WARN] 插入更新后的记录时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    return 0
            
            return fixed_count
            
        except Exception as e:
            print(f"[WARN] 迁移过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def recall_by_emotion(
        self,
        query_text: str,
        current_emotion_vector = None,
        top_k: int = 5,
        emotion_weight: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        RAG 检索接口：优先检索语义相关的记忆，并根据情绪向量进行加权
        
        逻辑：
        1. 使用 query_text 生成查询向量
        2. 在 LanceDB 中检索语义相似的记忆
        3. 如果提供了 current_emotion_vector，计算情绪一致性分数
        4. 综合语义相似度和情绪一致性，返回加权后的结果
        
        Args:
            query_text: 查询文本
            current_emotion_vector: 当前情绪向量（可选，用于情绪一致性加权）
            top_k: 返回的记忆数量
            emotion_weight: 情绪一致性权重（0.0-1.0，默认 0.3）
        
        Returns:
            记忆列表，每个记忆包含：
            - text: 记忆文本
            - similarity: 综合相似度分数 (0.0-1.0)
            - semantic_similarity: 语义相似度分数
            - emotion_similarity: 情绪一致性分数（如果有）
            - metadata: 元数据
        """
        if not LANCEDB_AVAILABLE or self.db is None or self.table is None:
            return []
        
        if not self.embedding_model:
            print("[WARN] Embedding 模型未加载，无法检索记忆")
            return []
        
        try:
            # 1. 生成查询向量
            query_vector = self.embedding_model.encode(query_text, convert_to_numpy=True)
            
            # 确保向量维度正确
            if len(query_vector) != self.VECTOR_DIM:
                print(f"[WARN] 查询向量维度不匹配: 期望 {self.VECTOR_DIM}，实际 {len(query_vector)}")
                return []
            
            # 2. 在 LanceDB 中检索语义相似的记忆
            # 使用向量搜索，明确指定使用 "vector" 列
            # 返回 top_k * 2 个结果（后续会加权筛选）
            results = self.table.search(
                query_vector.tolist(),
                vector_column_name="vector"
            ).limit(top_k * 2).to_pandas()
            
            if results.empty:
                return []
            
            # 3. 计算综合相似度
            memories = []
            access_updates: List[Dict[str, Any]] = []
            current_ts = time.time()
            for _, row in results.iterrows():
                memory_text = row.get("text", "")
                memory_vector = row.get("vector", [])
                
                # 检查 memory_text 和 memory_vector 是否有效
                if not memory_text:
                    continue
                if memory_vector is None or (isinstance(memory_vector, (list, np.ndarray)) and len(memory_vector) == 0):
                    continue
                
                # 计算语义相似度（余弦相似度）
                if isinstance(memory_vector, list):
                    memory_vec = np.array(memory_vector, dtype=np.float32)
                else:
                    memory_vec = np.array(memory_vector, dtype=np.float32)
                
                # 归一化向量
                query_norm = np.linalg.norm(query_vector)
                memory_norm = np.linalg.norm(memory_vec)
                
                if query_norm > 0 and memory_norm > 0:
                    semantic_similarity = float(np.dot(query_vector, memory_vec) / (query_norm * memory_norm))
                    # 将相似度从 [-1, 1] 映射到 [0, 1]
                    semantic_similarity = (semantic_similarity + 1.0) / 2.0
                else:
                    semantic_similarity = 0.0
                
                # 计算情绪一致性分数（如果有情绪向量）
                emotion_similarity = 1.0  # 默认值（无情绪向量时不影响结果）
                if current_emotion_vector is not None and NUMPY_AVAILABLE:
                    # 检查记忆是否有情绪向量元数据
                    memory_emotion_str = row.get("emotion_vector", "")
                    if memory_emotion_str:
                        try:
                            # emotion_vector 存储为 JSON 字符串，需要解析
                            memory_emotion_vec = np.array(json.loads(memory_emotion_str), dtype=np.float32)
                            
                            # 计算情绪向量相似度
                            emotion_norm = np.linalg.norm(current_emotion_vector)
                            memory_emotion_norm = np.linalg.norm(memory_emotion_vec)
                            
                            if emotion_norm > 0 and memory_emotion_norm > 0:
                                emotion_similarity = float(
                                    np.dot(current_emotion_vector, memory_emotion_vec) / 
                                    (emotion_norm * memory_emotion_norm)
                                )
                                # 将相似度从 [-1, 1] 映射到 [0, 1]
                                emotion_similarity = (emotion_similarity + 1.0) / 2.0
                            else:
                                emotion_similarity = 0.5  # 中性值
                        except (json.JSONDecodeError, ValueError, TypeError) as e:
                            # JSON 解析失败，使用默认值
                            emotion_similarity = 1.0
                
                # 综合相似度 = (1 - emotion_weight) * 语义相似度 + emotion_weight * 情绪相似度
                combined_similarity = (1.0 - emotion_weight) * semantic_similarity + emotion_weight * emotion_similarity
                
                # 过滤重复查询：如果记忆中的用户输入与当前查询高度相似，降低其分数
                # 这样可以避免检索到用户之前问过的相同问题，而是检索到实际的答案
                user_input_from_memory = self._extract_user_input_from_memory(memory_text)
                if user_input_from_memory:
                    query_similarity = self._calculate_string_similarity(query_text, user_input_from_memory)
                    
                    # 如果相似度超过阈值（0.75），说明这是重复查询
                    # 降低其相似度分数，使其排在后面
                    if query_similarity > 0.75:
                        # 降低相似度：相似度越高，降低越多
                        # 例如：0.9 相似度 -> 降低到原来的 10%，0.8 相似度 -> 降低到原来的 20%
                        # 使用 max(0.05, ...) 确保至少保留 5% 的分数，避免完全排除
                        penalty_factor = max(0.05, 1.0 - query_similarity)  # 0.05 到 0.25
                        original_similarity = combined_similarity
                        combined_similarity = combined_similarity * penalty_factor
                        print(f"🚫 [Memory][FILTER] 检测到重复查询（相似度={query_similarity:.2f}），降低记忆分数: {original_similarity:.3f} -> {combined_similarity:.3f}")
                        print(f"   查询: {query_text[:60]}...")
                        print(f"   记忆中的用户输入: {user_input_from_memory[:60]}...")
                
                # 提取其他元数据
                timestamp_value = float(row.get("timestamp", 0.0) or 0.0)
                current_access = int(row.get("access_count", 0) or 0)
                metadata = {
                    "id": row.get("id", ""),
                    "timestamp": timestamp_value,
                    "timestamp_human": self._format_timestamp(timestamp_value),
                    "age_seconds": max(0.0, current_ts - timestamp_value),
                    "importance": row.get("importance", 0.5),
                    "type": row.get("type", "raw"),
                    "emotions": row.get("emotions", ""),
                    "access_count": current_access,
                }
                
                memories.append({
                    "text": memory_text,
                    "similarity": combined_similarity,
                    "semantic_similarity": semantic_similarity,
                    "emotion_similarity": emotion_similarity if current_emotion_vector is not None else None,
                    "metadata": metadata,
                })
                access_updates.append({"id": metadata["id"], "new_value": current_access + 1})
            
            # 更新访问计数
            if access_updates:
                self._increment_access_counts(access_updates)
            
            # 4. 按综合相似度排序，返回 top_k
            memories.sort(key=lambda x: x["similarity"], reverse=True)
            top = memories[:top_k]

            # 终端调试输出：向量读取 / 检索结果摘要
            if top:
                best = top[0]
                preview = best["text"].replace("\n", " ")[:80]
                print(
                    f"[SEARCH] [Memory][READ] query='{query_text[:40]}' "
                    f"-> {len(top)} 条，最高相似度={best['similarity']:.3f}，示例: {preview}..."
                )
                # 详细输出前3条记忆（用于调试）
                for i, mem in enumerate(top[:3], 1):
                    mem_text = mem.get("text", "")
                    mem_sim = mem.get("similarity", 0.0)
                    # 检查是否有时间戳前缀
                    has_timestamp = mem_text.startswith("[") and "]" in mem_text[:20]
                    timestamp_marker = "⏰" if has_timestamp else "  "
                    print(f"   {timestamp_marker} [{i}] 相似度={mem_sim:.3f}: {mem_text[:60]}...")
            else:
                print(f"[SEARCH] [Memory][READ] query='{query_text[:40]}' -> 未找到相关记忆")

            return top
        except Exception as e:
            print(f"[WARN] 记忆检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _format_timestamp(self, ts: float) -> str:
        """将时间戳转换为人类可读的本地时间描述"""
        if not ts:
            return "(未知时间)"
        try:
            dt = datetime.fromtimestamp(float(ts)).astimezone()
            return dt.strftime("%Y-%m-%d %H:%M:%S %Z%z")
        except Exception:
            return "(时间解析失败)"

    def _increment_access_counts(self, updates: List[Dict[str, Any]]):
        """将指定记忆的访问次数 +1"""
        if not updates or not self.table:
            return
        for item in updates:
            mem_id = item.get("id")
            new_value = item.get("new_value")
            if not mem_id:
                continue
            try:
                self.table.update(
                    where=f"id == '{mem_id}'",
                    values={"access_count": int(new_value)},
                )
            except Exception:
                try:
                    row_df = self.table.to_pandas()
                    row = row_df[row_df["id"] == mem_id]
                    if not row.empty:
                        fallback_value = int(row.iloc[0].get("access_count", 0)) + 1
                        self.table.update(
                            where=f"id == '{mem_id}'",
                            values={"access_count": fallback_value},
                        )
                except Exception:
                    continue

    def get_recent_memories(self, limit: int = 1000, memory_type: str = "raw") -> List[Dict[str, Any]]:
        """获取最近的记忆列表"""
        if not self.table:
            return []
        try:
            df = self.table.to_pandas()
            if memory_type:
                df = df[df["type"] == memory_type]
            df = df.sort_values("timestamp", ascending=False).head(limit)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"[WARN] 获取记忆失败: {e}")
            return []

    def delete_memories(self, memory_ids: List[str]):
        """删除指定 ID 的记忆"""
        if not memory_ids or not self.table:
            return
        for mem_id in memory_ids:
            try:
                self.table.delete(where=f"id == '{mem_id}'")
            except Exception as e:
                print(f"[WARN] 删除记忆 {mem_id} 失败: {e}")
