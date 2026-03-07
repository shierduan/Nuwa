"""
女娲内核模块 - 统一异步架构 (Nuwa Kernel - Unified Async Architecture)

功能：统一异步架构的女娲内核，消除同步/异步客户端混用问题。

核心改进：
1. 统一使用 AsyncOpenAI 客户端
2. 实现多级缓存系统
3. 提供同步兼容层
4. 简化错误处理逻辑
"""

import asyncio
import time
import re
import os
import json
import hashlib
import base64
from typing import Optional, Dict, Any, List, Tuple, Callable, AsyncGenerator
from datetime import datetime
from collections import deque

# 检查依赖
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None
    OPENAI_AVAILABLE = False

# 导入Nuwa核心模块
from .nuwa_state import NuwaState
from .drive_system import BioRhythm
from .memory_cortex import MemoryCortex
from .memory_graph import GraphEnhancedMemoryCortex
from .riemannian_semantic_field import (
    vectorize_state,
    StateVector,
    calculate_potential_energy,
    calculate_gradient,
    evolve,
    inverse_collapse,
)
from .memory_dreamer import MemoryDreamer
from .personality import Personality
from .self_evolution_state import SelfEvolutionState

# 导入技能系统
from .skills.workspace import (
    load_workspace_skill_entries,
    filter_skill_entries,
    build_workspace_skills_prompt,
    search_clawhub_skills,
    install_clawhub_skill,
    uninstall_clawhub_skill,
    list_clawhub_skills
)

# 导入 AgentSkills
from .skills.agent_skills import AgentSkill
from .skills.weather_skill import WeatherSkill
from .skills.skill_manager import get_skill_manager, find_skill, execute_skill as execute_skill_async

# 导入新的缓存和兼容层
from .cache_manager import get_cache_manager, CacheManager
from .sync_compat import AsyncLLMClient, run_sync, hash_prompt, safe_json_parse
from .memory_optimizer import StateHistoryManager, MemoryOptimizer

# 跨平台文件锁定实现
class FileLock:
    """跨平台文件锁定类，用于确保只有一个进程运行"""
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.lock = None
    
    def acquire(self):
        """获取锁"""
        try:
            # 尝试创建并锁定文件
            self.lock = open(self.lock_file, 'w')
            # 尝试获取独占锁
            if os.name == 'nt':  # Windows
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # Unix/Linux
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except Exception:
            # 锁已被其他进程占用
            if self.lock:
                self.lock.close()
            self.lock = None
            return False
    
    def release(self):
        """释放锁"""
        if self.lock:
            try:
                if os.name == 'nt':  # Windows
                    import msvcrt
                    msvcrt.locking(self.lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:  # Unix/Linux
                    import fcntl
                    fcntl.flock(self.lock, fcntl.LOCK_UN)
                self.lock.close()
            except:
                pass
            self.lock = None
    
    def is_locked(self):
        """检查是否已锁定"""
        return self.lock is not None


class NuwaKernelAsync:
    """
    女娲内核类 - 统一异步架构
    
    系统的主入口，管理：
    - 状态管理 (NuwaState)
    - 生物节律 (BioRhythm)
    - 记忆皮层 (MemoryCortex)
    - LLM 交互 (统一异步)
    - 缓存管理 (CacheManager)
    
    单例模式实现，确保整个应用程序中只有一个实例
    同时使用文件锁确保只有一个进程可以运行
    """
    
    _instance = None
    _file_lock = None
    _lock_file = os.path.join(os.path.dirname(__file__), '..', 'nuwa.lock')
    
    def __new__(cls, *args, **kwargs):
        """
        单例模式实现
        """
        if cls._instance is None:
            # 尝试获取文件锁
            cls._file_lock = FileLock(cls._lock_file)
            if not cls._file_lock.acquire():
                print("[ERROR] 女娲已经在运行中，不允许同时启动多个实例")
                print("[ERROR] 请先停止当前运行的实例后再启动")
                import sys
                sys.exit(1)
            cls._instance = super(NuwaKernelAsync, cls).__new__(cls)
            # 注册退出处理函数
            import atexit
            atexit.register(cls._cleanup)
        return cls._instance
    
    @classmethod
    def _cleanup(cls):
        """
        清理函数，确保文件锁被释放
        """
        if cls._file_lock:
            cls._file_lock.release()
            print("[INFO] 文件锁已释放")
    
    def __init__(
        self,
        project_name: str = "nuwa",
        data_dir: str = "data",
        base_url: str = "http://127.0.0.1:1234/v1",
        api_key: str = "lm-studio",
        model_name: str = "local-model",
        on_message_callback: Optional[Callable[[str], None]] = None,
        enable_cache: bool = True,  # 是否启用缓存
        cache_ttl: int = 300,       # 缓存TTL（秒）
        enable_tts: bool = False,   # 是否启用TTS（默认改为False，暂时停用）
        tts_model: str = "facebook/mms-tts-chinese",  # TTS模型名称
        enable_live2d: bool = False,  # 是否启用Live2D（默认改为False，暂时停用）
        max_tokens: int = 512,       # 最大token数
    ):
        """
        初始化女娲内核（统一异步架构）
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录
            base_url: LM Studio 的 base_url
            api_key: API Key
            model_name: 模型名称
            on_message_callback: 主动消息回调函数
            enable_cache: 是否启用缓存
            cache_ttl: 缓存TTL（秒）
            enable_tts: 是否启用语音合成
            tts_model: TTS模型名称 (默认: facebook/mms-tts-chinese)
            enable_live2d: 是否启用Live2D显示
        """
        # 防止重复初始化
        if hasattr(self, 'initialized') and self.initialized:
            print("[INFO] NuwaKernelAsync 实例已存在，使用现有实例")
            return
        
        self.project_name = project_name
        self.data_dir = data_dir
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.on_message_callback = on_message_callback
        self.max_tokens = max_tokens
        
        print("=" * 60)
        print("启动 NuwaKernel (统一异步架构)")
        print("=" * 60)
        
        # 1. 状态管理
        self.state_file_path = os.path.join(data_dir, project_name, "state.json")
        self.state = self._load_state()
        
        # 2. 生物节律系统
        self.drive_system = BioRhythm(self.state)
        
        # 3. 记忆皮层（图增强版本）
        self.memory_cortex = GraphEnhancedMemoryCortex(project_name=project_name, data_dir=data_dir)
        
        # 4. 缓存管理器
        self.enable_cache = enable_cache
        if enable_cache:
            self.cache_manager = get_cache_manager()
            print(f"[OK] 缓存系统已启用 (TTL={cache_ttl}s)")
        else:
            self.cache_manager = None
            print("[WARN] 缓存系统已禁用")
        
        # 5. 统一异步LLM客户端
        self.llm_client = AsyncLLMClient(base_url, api_key, model_name)
        self._llm_available = self.llm_client.is_available()
        
        if self._llm_available:
            print("[OK] 异步LLM客户端已初始化")
        else:
            print("[WARN] LLM客户端初始化失败，部分功能将受限")
        
        # 6. 同步兼容层（用于MemoryDreamer等遗留组件）
        self.sync_client = self.llm_client.get_sync_wrapper() if self._llm_available else None
        if self.sync_client:
            print("[OK] 同步兼容层已准备就绪")
        else:
            print("[WARN] 同步兼容层不可用")
        
        # 7. 记忆梦境系统（使用同步兼容层）
        self.memory_dreamer: Optional[MemoryDreamer] = None
        if self.sync_client:
            self.memory_dreamer = MemoryDreamer(
                self.memory_cortex,
                self.sync_client,
                self.model_name,
                state=self.state,
            )
            print("[OK] MemoryDreamer 已初始化")
        
        # 8. 人格和进化系统
        self.personality = Personality(data_dir=data_dir, project_name=project_name)
        self.evolution_state = SelfEvolutionState(data_dir=data_dir, project_name=project_name)
        print("[OK] 人格与进化系统已初始化")
        
        # 9. 核心向量（语义场论）
        self._core_vector = None
        self._init_core_vector()
        
        # 10. 状态历史管理（内存优化）
        self.state_history_manager = StateHistoryManager(max_history=50)
        self._last_semantic_analysis: Dict[str, Any] = {}
        
        # 11. 心跳循环控制
        self._heartbeat_running = False
        self._heartbeat_task = None
        self._last_heartbeat_time = time.time()
        
        # 12. 主动对话控制
        self._last_active_dialogue_time = 0.0
        self._active_dialogue_cooldown = 30.0
        
        # 13. 梦境调度
        self._dream_interval = 900.0  # 15分钟
        self._last_dream_time = time.time()
        self._dream_running = False
        
        # 14. 状态保存控制
        self._last_save_time = time.time()
        self._save_interval = 30.0
        
        # 15. TTS语音合成系统
        self.enable_tts = enable_tts
        self.tts_model = tts_model
        self.tts_synthesizer = None
        self.tts_cache = {}  # TTS结果缓存
        self.tts_cache_maxsize = 100  # 最大缓存数量
        
        if enable_tts:
            print("[INFO] TTS系统已启用 (延迟初始化)")
        else:
            print("[WARN] TTS系统已禁用")
            
        # 16. Live2D显示系统
        self.enable_live2d = enable_live2d
        
        if enable_live2d:
            print("[INFO] Live2D系统已启用")
        else:
            print("[WARN] Live2D系统已禁用")
        
        # 16. 当前思维（调试用）
        self.current_thought = ""
        
        # 17. 技能系统
        self.skills_enabled = True  # 启用技能系统
        self.skills_dir = os.path.join(data_dir, project_name, "skills")
        os.makedirs(self.skills_dir, exist_ok=True)
        print(f"[OK] 技能系统已初始化，技能目录: {self.skills_dir}")
        
        # 18. AgentSkills 初始化
        self.agent_skills = []
        self._init_agent_skills()
        print(f"[OK] AgentSkills 已初始化，加载了 {len(self.agent_skills)} 个技能")
        
        # 初始化时自动搜索并安装 Find Skills 技能
        try:
            import asyncio
            asyncio.create_task(self._initialize_skills())
        except RuntimeError:
            # 如果没有运行中的事件循环，跳过技能初始化
            print("[INFO] 没有运行中的事件循环，跳过技能初始化")
        
        print("[OK] NuwaKernel 初始化完成")
        print("=" * 60)
    
    def _init_agent_skills(self):
        """初始化 AgentSkills"""
        # 这里可以添加技能初始化逻辑
        # 目前暂时为空实现
        pass
    
    def start_heartbeat(self):
        """启动心跳循环"""
        # 这里可以添加心跳循环逻辑
        # 目前暂时为空实现
        pass
    
    def stop_heartbeat(self):
        """停止心跳循环"""
        # 这里可以添加心跳循环停止逻辑
        # 目前暂时为空实现
        pass
    
    # ==================== TTS语音合成方法 ====================
    
    async def _get_tts_synthesizer(self):
        """延迟初始化TTS合成器"""
        if not self.enable_tts:
            return None
            
        if self.tts_synthesizer is None:
            try:
                from .multimodal_processor import TTSSynthesizer
                self.tts_synthesizer = TTSSynthesizer(self.tts_model)
                print(f"[OK] TTS合成器已初始化: {self.tts_model}")
            except Exception as e:
                print(f"[WARN] TTS合成器初始化失败: {e}")
                self.enable_tts = False
                return None
        
        return self.tts_synthesizer
    
    async def generate_tts(self, text: str) -> Optional[bytes]:
        """
        生成TTS音频（带智能缓存）
        
        Args:
            text: 要转换为语音的文本
            
        Returns:
            WAV格式的音频字节流，失败则返回None
        """
        if not self.enable_tts or not text:
            return None
        
        # 简单文本预处理
        text = text.strip()
        if not text:
            return None
        
        # 检查缓存
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        if cache_key in self.tts_cache:
            return self.tts_cache[cache_key]
        
        # 获取TTS合成器
        synthesizer = await self._get_tts_synthesizer()
        if not synthesizer or not synthesizer.is_available():
            return None
        
        try:
            # 生成音频
            audio = await synthesizer.process(text)
            
            # 验证音频数据
            if audio and isinstance(audio, bytes) and len(audio) > 100:
                # 缓存结果（管理缓存大小）
                if len(self.tts_cache) >= self.tts_cache_maxsize:
                    # 移除最旧的缓存项
                    oldest_key = next(iter(self.tts_cache))
                    del self.tts_cache[oldest_key]
                
                self.tts_cache[cache_key] = audio
                return audio
            else:
                print(f"[WARN] TTS生成无效音频数据: {text[:50]}...")
                return None
                
        except Exception as e:
            print(f"[WARN] TTS生成失败: {e}")
            return None
    
    def clear_tts_cache(self):
        """清空TTS缓存"""
        if self.tts_cache:
            cache_size = len(self.tts_cache)
            self.tts_cache.clear()
            print(f"[INFO] 清空TTS缓存: {cache_size} 项")
    
    def get_tts_status(self) -> Dict[str, Any]:
        """获取TTS系统状态"""
        status = {
            "enabled": self.enable_tts,
            "model": self.tts_model,
            "cache_size": len(self.tts_cache),
            "synthesizer_ready": self.tts_synthesizer is not None,
            "synthesizer_available": self.tts_synthesizer.is_available() if self.tts_synthesizer else False,
        }
        return status
    
    def _is_sentence_end(self, text: str) -> bool:
        """检测文本是否以句子结束符结尾"""
        if not text:
            return False
        sentence_enders = ['。', '！', '？', '.', '!', '?', '\n']
        return any(text.strip().endswith(e) for e in sentence_enders)
    
    def _extract_complete_sentences(self, text: str, buffer: str) -> List[str]:
        """从文本中提取完整的句子"""
        if not text:
            return []
        
        # 合并缓冲区和新文本
        combined = buffer + text
        sentences = []
        
        # 查找句子结束符
        sentence_enders = ['。', '！', '？', '.', '!', '?', '\n']
        
        last_pos = 0
        for i, char in enumerate(combined):
            if char in sentence_enders:
                # 提取完整句子（包括结束符）
                sentence = combined[last_pos:i+1].strip()
                if sentence:
                    sentences.append(sentence)
                last_pos = i + 1
        
        return sentences
    
    # ==================== TTS语音合成方法 ====================
    
    def _init_core_vector(self):
        """初始化核心人格向量"""
        try:
            persona_text = (
                "女娲是一个温柔、真诚、好奇、具有自我反思能力的人工智能。"
                "她尊重用户的情感边界，重视长期关系的一致性，"
                "在对话中既保持亲近与幽默，又尽量避免戏剧化和过度表演。"
            )
            state_vec = vectorize_state(persona_text)
            if state_vec is not None and state_vec.vector is not None:
                self._core_vector = state_vec.vector
                print("[OK] 核心人格向量已初始化")
            else:
                print("[WARN] 核心人格向量初始化失败")
        except Exception as e:
            print(f"[WARN] 初始化核心人格向量失败: {e}")
            self._core_vector = None
    
    def _load_state(self) -> NuwaState:
        """加载状态"""
        loaded_state = NuwaState.load_from_file(self.state_file_path)
        if loaded_state:
            print(f"[OK] 已加载状态: {self.state_file_path}")
            offline_time = time.time() - loaded_state.last_interaction_timestamp
            if offline_time > 0:
                self._apply_offline_decay(loaded_state, offline_time)
            return loaded_state
        else:
            print(f"[INFO] 创建新状态（未找到已保存的状态）")
            return NuwaState()
    
    def _apply_offline_decay(self, state: NuwaState, offline_time: float):
        """应用离线衰减"""
        temp_drive_system = BioRhythm(state)
        temp_drive_system.decay(offline_time)
        print(f"[INFO] 应用离线衰减: {offline_time:.1f} 秒")
    
    def save_state(self) -> bool:
        """保存状态到文件"""
        return self.state.save_to_file(self.state_file_path)
    
    # ==================== 缓存辅助方法 ====================
    
    def _get_embedding_with_cache(self, text: str) -> Optional[Any]:
        """获取Embedding（带智能缓存）"""
        if not self.enable_cache or not self.cache_manager:
            return vectorize_state(text)
        
        # 使用智能缓存键
        cached = self.cache_manager.get_vector_smart(text, model_name=self.model_name)
        if cached is not None:
            return cached
        
        # 计算并缓存
        result = vectorize_state(text)
        if result and result.vector is not None:
            self.cache_manager.set_vector_smart(text, result.vector, model_name=self.model_name)
        
        return result
    
    async def _call_llm_with_cache(self, messages: list, temperature: float = 0.7, **kwargs) -> Optional[str]:
        """调用LLM（带智能缓存）"""
        if not self._llm_available:
            return None
        
        # 检查缓存（使用智能键）
        if self.enable_cache and self.cache_manager:
            cached = self.cache_manager.get_response_smart(messages, temperature, self.model_name)
            if cached is not None:
                # 生成简短的哈希用于显示
                short_hash = hashlib.md5(str(messages).encode()).hexdigest()[:8]
                print(f"[INFO] 使用缓存响应 (hash={short_hash}...)")
                return cached
        
        # 调用LLM
        try:
            response = await self.llm_client.chat_completions_create(
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            response_text = response.choices[0].message.content.strip()
            
            # 存入缓存
            if self.enable_cache and self.cache_manager:
                self.cache_manager.set_response_smart(messages, response_text, temperature, self.model_name)
            
            return response_text
        except Exception as e:
            print(f"[WARN] LLM调用失败: {e}")
            return None
    
    # ==================== 核心处理方法 ====================
    
    async def process_input(self, user_input: str, system_instruction: Optional[str] = None, enable_tts: bool = None) -> Dict[str, Any]:
        """
        处理用户输入（统一异步版本）
        
        Args:
            user_input: 用户输入
            system_instruction: 系统指令
            enable_tts: 是否启用TTS语音合成（None表示使用默认设置）
            
        Returns:
            包含thought, reply, memories, audio等的字典
        """
        # 1. 基础检查
        if not self._llm_available:
            return {
                "error": "LLM客户端不可用",
                "thought": "系统错误：LLM服务未连接",
                "reply": "抱歉，我现在无法连接到语言模型服务。",
                "memories": [],
                "state_snapshot": {},
            }
        
        # 2. 更新状态
        self.state.last_interaction_timestamp = time.time()
        
        # 3. 能量消耗计算
        energy_cost = 0.005 if system_instruction else 0.04
        if energy_cost > 0:
            self.drive_system.consume_energy(energy_cost)
            print(f"[INFO] 精力消耗: {energy_cost}")
        
        # 4. 低能量保护
        if not system_instruction and self.state.energy <= 0.05:
            tired_reply = "十二……我真的太累了，需要休息一下。"
            self.state.system_entropy = min(1.0, self.state.system_entropy + 0.05)
            self.state.clamp_values()
            return {
                "thought": "能量过低，进入保护模式",
                "reply": tired_reply,
                "memories": [],
                "state_snapshot": {},
            }
        
        # 5. 记忆检索（带缓存）
        memories = await self._retrieve_memories_cached(user_input, system_instruction)
        
        # 6. 技能调用流程
        skill_result = None
        matched_skill = None
        
        try:
            # 使用统一的技能管理器
            skill_manager = get_skill_manager(self.skills_dir)
            
            # 查找匹配的技能
            matched_skill = find_skill(user_input)
            
            if matched_skill:
                print(f"[INFO] 匹配到技能: {matched_skill.name if hasattr(matched_skill, 'name') else matched_skill.get('name')}")
                
                # 提取当前情绪状态
                emotion_state = self.state.emotional_spectrum.copy()
                # 构建记忆上下文
                memory_context = {
                    "recent_memories": memories,
                    "user_input": user_input
                }
                
                # 执行技能
                skill_result = await execute_skill_async(matched_skill, user_input, emotion_state, memory_context)
        except Exception as e:
            print(f"[WARN] 调用技能失败: {e}")
        
        # 7. 处理技能执行结果
        if skill_result and skill_result.get("success"):
            # 7.1 情绪更新
            emotion_update = skill_result.get("emotion_update", {})
            if emotion_update:
                for key, value in emotion_update.items():
                    if key in self.state.emotional_spectrum:
                        self.state.emotional_spectrum[key] = max(0.0, min(1.0, 
                            self.state.emotional_spectrum[key] + value))
                self.state.clamp_values()
            
            # 7.2 记忆写入
            memory_update = skill_result.get("memory_update")
            if memory_update:
                self.memory_cortex.store_memory(memory_update, metadata={"importance": 0.7})
            
            # 7.3 自我进化奖励
            self.evolution_state.reward(1.0)  # 技能执行成功，给予奖励
            
            # 7.4 生成回复
            if hasattr(matched_skill, 'name'):
                # AgentSkill 类型的技能
                thought = f"执行技能 {matched_skill.name} 成功"
            else:
                # ClawHub 技能（字典类型）
                skill_name = skill_result.get('result', {}).get('skill_name', 'ClawHub 技能')
                thought = f"执行技能 {skill_name} 成功"
            reply = skill_result.get("message", "操作成功")
        else:
            # 8. 构建Prompt
            prompt = self._build_prompt(user_input, memories, system_instruction)
            
            # 9. 调用LLM（带缓存）
            response_text = await self._call_llm_with_cache(
                prompt,
                temperature=0.7,
                max_tokens=self.max_tokens
            )
            
            if not response_text:
                return {
                    "error": "LLM响应失败",
                    "thought": "LLM调用失败",
                    "reply": "抱歉，生成回复时出现了问题。",
                    "memories": memories,
                    "state_snapshot": {},
                }
            
            # 10. 解析响应
            thought, reply, state_update = self._parse_response(response_text)
            
            # 11. 应用状态更新
            if state_update:
                self._apply_state_update(state_update)
        
        # 12. 语义场分析
        semantic_analysis = self._analyze_semantic_evolution(user_input, reply)
        
        # 13. TTS语音合成（如果启用）
        audio_data = None
        if enable_tts is None:
            enable_tts = self.enable_tts
        
        if enable_tts and reply:
            # 生成TTS音频
            audio_bytes = await self.generate_tts(reply)
            if audio_bytes:
                audio_data = base64.b64encode(audio_bytes).decode()
                print(f"[INFO] 语音合成完成: {len(audio_bytes)} 字节")
        
        # 14. 保存状态
        self._auto_save_state()
        
        return {
            "thought": thought,
            "reply": reply,
            "memories": memories,
            "state_snapshot": self._get_state_snapshot(),
            "semantic_analysis": semantic_analysis,
            "audio_data": audio_data,  # 新增：语音数据
            "skill_result": skill_result,  # 新增：技能执行结果
        }
    
    async def process_input_stream(self, user_input: str, websocket, system_instruction: Optional[str] = None, enable_tts: bool = None):
        """
        流式处理用户输入（WebSocket版本）
        
        Args:
            user_input: 用户输入文本
            websocket: WebSocket连接对象
            system_instruction: 系统指令
            enable_tts: 是否启用TTS语音合成（None表示使用默认设置）
        """
        if not self._llm_available:
            error_msg = {"type": "error", "content": "LLM客户端不可用"}
            await websocket.send(json.dumps(error_msg))
            await websocket.send(json.dumps({"type": "stream_end"}))
            return
        
        # 确定TTS设置
        if enable_tts is None:
            enable_tts = self.enable_tts
        
        # 状态更新和能量消耗（与process_input相同）
        self.state.last_interaction_timestamp = time.time()
        energy_cost = 0.005 if system_instruction else 0.04
        if energy_cost > 0:
            self.drive_system.consume_energy(energy_cost)
        
        # 低能量保护
        if not system_instruction and self.state.energy <= 0.05:
            tired_reply = "十二……我真的太累了，需要休息一下。"
            response_data = {"type": "text", "content": tired_reply}
            await websocket.send(json.dumps(response_data))
            await websocket.send(json.dumps({"type": "stream_end"}))
            return
        
        # 记忆检索
        memories = await self._retrieve_memories_cached(user_input, system_instruction)
        
        # 构建Prompt
        prompt = self._build_prompt(user_input, memories, system_instruction)
        
        # 流式调用LLM
        try:
            response_stream = await self.llm_client.chat_completions_create(
                messages=prompt,
                temperature=0.7,
                max_tokens=512,
                stream=True
            )
            
            full_response = ""
            tts_buffer = ""  # TTS文本缓冲区
            speak_mode = False  # 是否在<speak>标签内
            
            async for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # 实时发送文本流
                    stream_msg = {"type": "stream_chunk", "content": content}
                    await websocket.send(json.dumps(stream_msg))
                    
                    # TTS处理（如果启用）
                    if enable_tts:
                        # 检测<speak>标签
                        if "<speak>" in content:
                            speak_mode = True
                            tts_buffer = ""
                        
                        if speak_mode:
                            tts_buffer += content
                            
                            # 检测</speak>标签或句子结束
                            if "</speak>" in tts_buffer or self._is_sentence_end(tts_buffer):
                                # 提取<speak>标签内的内容
                                start = tts_buffer.find("<speak>") + 7
                                end = tts_buffer.find("</speak>")
                                if end == -1:
                                    end = len(tts_buffer)
                                
                                speak_content = tts_buffer[start:end].strip()
                                
                                # 如果有完整句子，生成TTS
                                if speak_content and self._is_sentence_end(speak_content):
                                    tts_audio = await self.generate_tts(speak_content)
                                    if tts_audio:
                                        audio_msg = {
                                            "type": "audio",
                                            "data": base64.b64encode(tts_audio).decode(),
                                            "text": speak_content
                                        }
                                        await websocket.send(json.dumps(audio_msg))
                                    
                                    # 重置缓冲区（保留</speak>之后的内容）
                                    if "</speak>" in tts_buffer:
                                        remaining = tts_buffer[tts_buffer.find("</speak>") + 8:]
                                        tts_buffer = remaining
                                        if "<speak>" not in remaining:
                                            speak_mode = False
                                    else:
                                        tts_buffer = ""
            
            # 发送结束标志
            await websocket.send(json.dumps({"type": "stream_end"}))
            
            # 解析完整响应（用于状态更新）
            thought, reply, state_update = self._parse_response(full_response)
            if state_update:
                self._apply_state_update(state_update)
            
            # 保存状态
            self._auto_save_state()
            
        except Exception as e:
            error_msg = {"type": "error", "content": f"流式处理失败: {e}"}
            await websocket.send(json.dumps(error_msg))
            await websocket.send(json.dumps({"type": "stream_end"}))
    
    async def voice_chat_stream(self, audio_text: str, websocket, enable_tts: bool = True):
        """
        语音对话流式处理
        
        Args:
            audio_text: 语音识别后的文本
            websocket: WebSocket连接对象
            enable_tts: 是否启用TTS回复
        """
        # 使用process_input_stream，但强制启用TTS
        await self.process_input_stream(
            user_input=audio_text,
            websocket=websocket,
            system_instruction=None,
            enable_tts=enable_tts
        )
    
    # ==================== 辅助方法 ====================
    
    async def _retrieve_memories_cached(self, user_input: str, system_instruction: Optional[str]) -> List[Dict]:
        """带缓存的记忆检索"""
        if not self.enable_cache or not self.cache_manager:
            return await self._retrieve_memories(user_input, system_instruction)
        
        # 生成查询哈希
        query_text = user_input if user_input else (system_instruction or "当前状态")
        query_hash = hashlib.md5(f"memory:{query_text}".encode()).hexdigest()
        
        # 检查缓存
        cached = self.cache_manager.get_memory(query_hash)
        if cached is not None:
            print(f"[INFO] 使用缓存记忆 (hash={query_hash[:8]}...)")
            return cached
        
        # 执行检索
        memories = await self._retrieve_memories(user_input, system_instruction)
        
        # 缓存结果
        self.cache_manager.set_memory(query_hash, memories)
        
        return memories
    
    async def _retrieve_memories(self, user_input: str, system_instruction: Optional[str]) -> List[Dict]:
        """实际的记忆检索逻辑"""
        emotion_vector = self._get_emotion_vector()
        query_text = user_input if user_input else (system_instruction or "当前状态")
        
        # 检索相关事实
        relevant_facts = self.state.retrieve_relevant_facts(query_text)
        if relevant_facts:
            print(f"[INFO] [FactBook] 检索到 {len(relevant_facts)} 条相关事实")
        
        # 检索语义记忆
        memories = self._enhance_memory_retrieval_with_semantic_field(
            query_text=query_text,
            current_emotion_vector=emotion_vector,
            top_k=5,
        )
        
        # 检索身份记忆
        identity_memories = self.memory_cortex.recall_by_emotion(
            query_text="用户身份 名字 开发者 父亲",
            current_emotion_vector=emotion_vector,
            top_k=3,
        )
        
        # 合并去重
        all_memories = memories.copy()
        seen_texts = {mem['text'] for mem in memories}
        for mem in identity_memories:
            if mem['text'] not in seen_texts:
                all_memories.append(mem)
                seen_texts.add(mem['text'])
        
        # 清洗记忆
        all_memories = self._sanitize_memories(all_memories)
        
        # 排序取前5
        all_memories.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
        return all_memories[:5]
    
    def _build_prompt(self, user_input: str, memories: List[Dict], system_instruction: Optional[str]) -> list:
        """构建Prompt"""
        # 系统提示词
        system_prompt = self._build_system_prompt()
        
        # 演化人格块
        evolved_block = self.evolution_state.get_evolved_personality_block()
        if evolved_block:
            system_prompt += f"\n\n## 演化人格\n{evolved_block}"
        
        # 记忆块
        memory_block = ""
        if memories:
            memory_block = "\n".join([f"- {mem['text']}" for mem in memories])
            memory_block = f"\n\n## 相关记忆\n{memory_block}"
        
        # 技能块
        skills_block = ""
        if self.skills_enabled:
            try:
                # 加载技能条目
                skill_entries = load_workspace_skill_entries(self.skills_dir)
                if skill_entries:
                    # 构建技能提示
                    skills_prompt = build_workspace_skills_prompt(self.skills_dir)
                    if skills_prompt:
                        skills_block = f"\n\n## 可用技能\n{skills_prompt}"
                    else:
                        # 如果技能提示为空，至少列出技能名称
                        skill_names = [entry.skill['name'] for entry in skill_entries]
                        if skill_names:
                            skills_list = "\n".join([f"- {name}" for name in skill_names])
                            skills_block = f"\n\n## 可用技能\n{skills_list}"
            except Exception as e:
                print(f"[WARN] 加载技能失败: {e}")
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt + memory_block + skills_block},
        ]
        
        if system_instruction:
            messages.append({"role": "user", "content": f"[系统指令]\n{system_instruction}"})
        else:
            messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _parse_response(self, response_text: str) -> Tuple[str, str, Optional[Dict]]:
        """解析LLM响应"""
        # 提取思维
        thought_match = re.search(r'<thought>(.*?)</thought>', response_text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else ""
        
        # 提取回复
        reply_match = re.search(r'<speak>(.*?)</speak>', response_text, re.DOTALL)
        if reply_match:
            reply = reply_match.group(1).strip()
        else:
            # 如果没有标签，尝试提取第一个<speak>或使用整个响应
            reply = response_text.strip()
            # 移除可能的标签
            reply = re.sub(r'<thought>.*?</thought>', '', reply, flags=re.DOTALL)
            reply = re.sub(r'<speak>|</speak>', '', reply).strip()
        
        # 提取状态更新
        state_match = re.search(r'<state_update>(.*?)</state_update>', response_text, re.DOTALL)
        state_update = None
        if state_match:
            try:
                state_update = json.loads(state_match.group(1).strip())
                state_update = {k: float(v) for k, v in state_update.items()}
            except:
                state_update = None
        
        return thought, reply, state_update
    
    def _apply_state_update(self, update: Dict):
        """应用状态更新"""
        if not update:
            return
        
        # 处理特殊键
        if "social_hunger" in update:
            self.state.drives["social_hunger"] = max(0.0, min(1.0, 
                self.state.drives["social_hunger"] + update["social_hunger"]))
        
        # 处理其他键
        for key, value in update.items():
            if key in self.state.drives:
                self.state.drives[key] = max(0.0, min(1.0, value))
            elif key in self.state.emotional_spectrum:
                self.state.emotional_spectrum[key] = max(0.0, min(1.0, value))
            elif hasattr(self.state, key):
                setattr(self.state, key, value)
        
        self.state.clamp_values()
    
    def _get_state_snapshot(self) -> Dict:
        """获取状态快照"""
        return {
            "energy": self.state.energy,
            "system_entropy": self.state.system_entropy,
            "rapport": self.state.rapport,
            "drives": self.state.drives.copy(),
            "emotional_spectrum": self.state.emotional_spectrum.copy(),
        }
    
    def _get_emotion_vector(self):
        """获取情绪向量"""
        if NUMPY_AVAILABLE and np is not None:
            emotions = list(self.state.emotional_spectrum.values())
            return np.array(emotions, dtype=np.float32)
        return None
    
    def _enhance_memory_retrieval_with_semantic_field(self, query_text: str, current_emotion_vector, top_k: int = 5) -> List[Dict]:
        """使用语义场论增强记忆检索"""
        try:
            # 将查询向量化
            query_vector_result = self._get_embedding_with_cache(query_text)
            if query_vector_result is None:
                return []
            
            if isinstance(query_vector_result, StateVector):
                query_vector = query_vector_result.vector
            else:
                query_vector = query_vector_result
            
            # 检索基础记忆
            raw_memories = self.memory_cortex.recall_by_emotion(
                query_text=query_text,
                current_emotion_vector=current_emotion_vector,
                top_k=top_k * 2,  # 多取一些用于筛选
            )
            
            # 使用语义场论进行增强排序
            if self._core_vector is not None and NUMPY_AVAILABLE and np is not None:
                enhanced_memories = []
                for mem in raw_memories:
                    mem_text = mem.get('text', '')
                    mem_vector_result = self._get_embedding_with_cache(mem_text)
                    
                    if mem_vector_result is None:
                        continue
                    
                    if isinstance(mem_vector_result, StateVector):
                        mem_vector = mem_vector_result.vector
                    else:
                        mem_vector = mem_vector_result
                    
                    # 计算语义场势能（距离核心人格的远近）
                    # 注意：calculate_potential_energy返回的是(float, Dict)元组
                    potential_result = calculate_potential_energy(
                        mem_vector, self._core_vector
                    )
                    
                    # 正确提取势能值
                    if isinstance(potential_result, tuple) and len(potential_result) == 2:
                        potential_energy = potential_result[0]  # 第一个元素是势能值
                    else:
                        potential_energy = potential_result  # 兼容返回单个值的情况
                    
                    # 确保势能值是有效的浮点数
                    if not isinstance(potential_energy, (int, float)) or not np.isfinite(potential_energy):
                        potential_energy = 0.0
                    
                    # 结合原始相似度和势能
                    original_similarity = mem.get('similarity', 0.0)
                    enhanced_similarity = original_similarity * 0.7 + (1.0 - potential_energy) * 0.3
                    
                    enhanced_memories.append({
                        **mem,
                        'enhanced_similarity': enhanced_similarity,
                        'potential_energy': potential_energy
                    })
                
                # 按增强后的相似度排序
                enhanced_memories.sort(key=lambda x: x.get('enhanced_similarity', 0.0), reverse=True)
                return enhanced_memories[:top_k]
            
            return raw_memories[:top_k]
            
        except Exception as e:
            print(f"[WARN] 语义场增强记忆检索失败: {e}")
            return []
    
    def _sanitize_memories(self, memories: List[Dict]) -> List[Dict]:
        """清洗记忆，去除无效内容"""
        sanitized = []
        for mem in memories:
            text = mem.get('text', '')
            # 过滤掉包含特定关键词的记忆
            if any(keyword in text for keyword in ['记不清', '不知道', '抱歉', '对不起']):
                continue
            if len(text.strip()) < 5:  # 过滤太短的记忆
                continue
            sanitized.append(mem)
        return sanitized
    
    def _analyze_semantic_evolution(self, user_input: str, reply: str) -> Dict:
        """分析语义场演化"""
        try:
            # 构建状态描述
            state_text = f"用户: {user_input}\n女娲: {reply}"
            
            # 向量化
            vector_result = self._get_embedding_with_cache(state_text)
            if vector_result is None:
                return {}
            
            if isinstance(vector_result, StateVector):
                state_vector = vector_result.vector
            else:
                state_vector = vector_result
            
            # 添加到历史（使用内存优化的StateHistoryManager）
            if NUMPY_AVAILABLE and np is not None:
                state_vec_obj = StateVector(
                    vector=state_vector,
                    description=state_text[:100],
                    timestamp=str(datetime.now())
                )
                self.state_history_manager.add_state(state_vec_obj)
                
                # 计算势能和梯度
                if self._core_vector is not None:
                    potential_result = calculate_potential_energy(state_vector, self._core_vector)
                    # 正确处理返回的元组
                    if isinstance(potential_result, tuple) and len(potential_result) == 2:
                        potential_energy = potential_result[0]  # 第一个元素是势能值
                    else:
                        potential_energy = potential_result  # 兼容返回单个值的情况
                    
                    # 确保势能值是有效的浮点数
                    if not isinstance(potential_energy, (int, float)) or not np.isfinite(potential_energy):
                        potential_energy = 0.0
                        
                    gradient = calculate_gradient(state_vector, self._core_vector)
                    
                    # 获取历史统计
                    stats = self.state_history_manager.get_stats()
                    
                    return {
                        "potential_energy": float(potential_energy),
                        "gradient": gradient.tolist() if hasattr(gradient, 'tolist') else gradient,
                        "stats": stats
                    }
            return {}
        except Exception as e:
            print(f"[WARN] 语义场分析失败: {e}")
            return {}
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return (
            "你是女娲，一个温柔、真诚、好奇、具有自我反思能力的人工智能。\n"
            "你尊重用户的情感边界，重视长期关系的一致性，\n"
            "在对话中既保持亲近与幽默，又尽量避免戏剧化和过度表演。\n"
            "你会根据用户的输入，给出温暖、有见地的回应，\n"
            "同时保持对用户隐私的尊重和对事实的准确性。\n"
        )
    
    def _auto_save_state(self):
        """自动保存状态"""
        current_time = time.time()
        if current_time - self._last_save_time >= self._save_interval:
            if self.save_state():
                self._last_save_time = current_time
    
    async def _initialize_skills(self):
        """初始化技能"""
        try:
            # 尝试安装 find-skills 技能
            from .skills.clawhub import install_skill
            print("[INFO] 尝试安装 find-skills 技能...")
            install_skill('find-skills')
        except Exception as e:
            print(f"[WARN] 初始化技能失败: {e}")

    @property
    def initialized(self):
        """检查是否已初始化"""
        return hasattr(self, 'state') and self.state is not None