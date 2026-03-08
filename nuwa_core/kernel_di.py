"""
依赖注入内核 (Dependency Injection Kernel)

功能：使用依赖注入实现完全解耦的女娲内核。

核心特性：
- 接口化设计：所有依赖通过接口注入
- 配置中心化：统一配置管理
- 可测试性：易于单元测试和mock
- 可扩展性：支持不同实现替换
"""

import asyncio
import time
import re
import os
import json
import hashlib
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime
from collections import deque

# 导入接口和配置
from .config_manager import (
    NuwaConfig,
    IStateManager,
    IMemoryCortex,
    IDriveSystem,
    ILLMClient,
    ISelfEvolution,
    ConfigManager,
    DependencyContainer,
    get_config,
    get_container,
)
from .nuwa_state import NuwaState
from .riemannian_semantic_field import (
    vectorize_state,
    StateVector,
    calculate_potential_energy,
    calculate_gradient,
)
from .memory_optimizer import StateHistoryManager
from .cache_manager import get_cache_manager


class KernelDI:
    """
    依赖注入内核 - 完全解耦的女娲内核
    
    所有依赖通过接口注入，支持配置管理和依赖注入容器
    """
    
    def __init__(
        self,
        config: Optional[NuwaConfig] = None,
        container: Optional[DependencyContainer] = None,
        state_manager: Optional[IStateManager] = None,
        memory_cortex: Optional[IMemoryCortex] = None,
        drive_system: Optional[IDriveSystem] = None,
        llm_client: Optional[ILLMClient] = None,
        self_evolution: Optional[ISelfEvolution] = None,
        on_message_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        初始化依赖注入内核
        
        Args:
            config: 配置对象（如果为None，使用全局配置）
            container: 依赖注入容器（如果为None，使用全局容器）
            state_manager: 状态管理器（如果为None，自动创建）
            memory_cortex: 记忆皮层（如果为None，自动创建）
            drive_system: 驱动力系统（如果为None，自动创建）
            llm_client: LLM客户端（如果为None，自动创建）
            self_evolution: 自我进化模块（如果为None，自动创建）
            on_message_callback: 主动消息回调
        """
        # 配置管理
        self.config = config or get_config()
        self.container = container or get_container()
        
        # 依赖注入
        self.state_manager = state_manager
        self.memory_cortex = memory_cortex
        self.drive_system = drive_system
        self.llm_client = llm_client
        self.self_evolution = self_evolution
        self.on_message_callback = on_message_callback
        
        # 交互历史（用于自我进化）
        self.interaction_history = []
        self.last_evolution_time = 0.0
        
        # 缓存管理器（全局单例）
        self.cache_manager = get_cache_manager() if self.config.cache_enabled else None
        
        # 状态历史管理
        self.state_history_manager = StateHistoryManager(max_history=self.config.memory_history_max)
        
        # 核心向量
        self._core_vector = None
        
        # 运行时状态
        self._heartbeat_running = False
        self._heartbeat_task = None
        self._last_heartbeat_time = time.time()
        
        # 主动对话控制
        self._last_active_dialogue_time = 0.0
        self._active_dialogue_cooldown = self.config.active_dialogue_cooldown
        
        # 梦境调度
        self._dream_interval = self.config.dream_interval
        self._last_dream_time = time.time()
        self._dream_running = False
        
        # 状态保存控制
        self._last_save_time = time.time()
        self._save_interval = self.config.state_save_interval
        
        print("=" * 60)
        print("🚀 启动 KernelDI (依赖注入架构)")
        print("=" * 60)
        
        # 自动初始化依赖（如果未提供）
        self._auto_init_dependencies()
        
        # 注册到容器
        self._register_to_container()
        
        # 交互历史记录阈值（达到一定数量触发进化）
        self.evolution_threshold = 20
        
        print("[OK] KernelDI 初始化完成")
        print("=" * 60)
    
    def _auto_init_dependencies(self):
        """自动初始化未提供的依赖"""
        
        # 1. 状态管理器
        if self.state_manager is None:
            # 使用默认实现
            self.state_manager = DefaultStateManager(self.config)
            print("[OK] 自动初始化: DefaultStateManager")
        
        # 2. 记忆皮层
        if self.memory_cortex is None:
            from .memory_cortex import MemoryCortex
            self.memory_cortex = MemoryCortex(
                project_name=self.config.project_name,
                data_dir=self.config.data_dir
            )
            print("[OK] 自动初始化: MemoryCortex")
        
        # 3. 驱动力系统
        if self.drive_system is None:
            from .drive_system import BioRhythm
            state = self.state_manager.get_state()
            self.drive_system = BioRhythm(state)
            print("[OK] 自动初始化: BioRhythm")
        
        # 4. LLM客户端
        if self.llm_client is None:
            from .sync_compat import AsyncLLMClient
            self.llm_client = AsyncLLMClient(
                base_url=self.config.llm_base_url,
                api_key=self.config.llm_api_key,
                model_name=self.config.llm_model_name
            )
            print("[OK] 自动初始化: AsyncLLMClient")
        
        # 5. 自我进化模块
        if self.self_evolution is None:
            from .self_evolution_rl import SelfEvolutionRL
            self.self_evolution = SelfEvolutionRL(
                state_manager=self.state_manager,
                memory_cortex=self.memory_cortex,
                llm_client=self.llm_client
            )
            print("[OK] 自动初始化: SelfEvolutionRL")
        
        # 6. 初始化核心向量
        self._init_core_vector()
    
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
    
    def _register_to_container(self):
        """注册服务到依赖注入容器"""
        self.container.register("config", self.config)
        self.container.register("state_manager", self.state_manager)
        self.container.register("memory_cortex", self.memory_cortex)
        self.container.register("drive_system", self.drive_system)
        self.container.register("llm_client", self.llm_client)
        self.container.register("self_evolution", self.self_evolution)
        self.container.register("cache_manager", self.cache_manager)
        self.container.register("state_history", self.state_history_manager)
        self.container.register("kernel", self)
        print("[OK] 所有服务已注册到依赖注入容器")
    
    # ==================== 核心处理方法 ====================
    
    async def process_input(self, user_input: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户输入（依赖注入版本）
        
        Args:
            user_input: 用户输入
            system_instruction: 系统指令
            
        Returns:
            处理结果字典
        """
        # 1. 基础检查
        if not self.llm_client or not self.llm_client.is_available():
            return {
                "error": "LLM客户端不可用",
                "thought": "系统错误：LLM服务未连接",
                "reply": "抱歉，我现在无法连接到语言模型服务。",
                "memories": [],
                "state_snapshot": {},
            }
        
        # 2. 获取当前状态
        state = self.state_manager.get_state()
        
        # 3. 能量消耗计算
        energy_cost = self.config.energy_consumption_system if system_instruction else self.config.energy_consumption_base
        if energy_cost > 0:
            self.drive_system.consume_energy(energy_cost)
            if self.config.enable_debug_mode:
                print(f"🔋 精力消耗: {energy_cost}")
        
        # 4. 低能量保护
        if not system_instruction and state.energy <= self.config.energy_critical_threshold:
            tired_reply = "十二……我真的太累了，需要休息一下。"
            self.state_manager.update_state({"system_entropy": min(1.0, state.system_entropy + 0.05)})
            return {
                "thought": "能量过低，进入保护模式",
                "reply": tired_reply,
                "memories": [],
                "state_snapshot": {},
            }
        
        # 5. 记忆检索
        memories = await self._retrieve_memories(user_input, system_instruction)
        
        # 6. 构建Prompt
        prompt = self._build_prompt(user_input, memories, system_instruction)
        
        # 7. 调用LLM
        response_text = await self._call_llm(prompt)
        
        if not response_text:
            return {
                "error": "LLM响应失败",
                "thought": "LLM调用失败",
                "reply": "抱歉，生成回复时出现了问题。",
                "memories": memories,
                "state_snapshot": {},
            }
        
        # 8. 解析和应用响应
        thought, reply, state_update = self._parse_response(response_text)
        
        if state_update:
            self._apply_state_update(state_update)
        
        # 9. 语义场分析
        semantic_analysis = self._analyze_semantic_evolution(user_input, reply)
        
        # 10. 记录交互历史（用于自我进化）
        interaction = self._record_interaction(user_input, reply, thought)
        
        # 11. 检查是否需要触发自我进化
        evolution_result = await self._check_and_trigger_evolution()
        
        # 12. 自动保存
        self._auto_save_state()
        
        return {
            "thought": thought,
            "reply": reply,
            "memories": memories,
            "state_snapshot": self._get_state_snapshot(),
            "state_update": state_update,
            "semantic_analysis": semantic_analysis,
            "evolution_result": evolution_result,
        }
    
    def _record_interaction(self, user_input: str, reply: str, thought: str) -> Any:
        """
        记录交互到历史
        
        这里需要评估交互质量，但为了简化，我们暂时使用默认值
        实际应用中，可以通过分析thought或调用评估模块来获取真实值
        """
        from .self_evolution_rl import Interaction
        
        # 简化评估：基于状态变化和thought内容
        state = self.state_manager.get_state()
        
        # 基于thought中的关键词进行简单评估
        thought_lower = thought.lower()
        user_satisfaction = 0.5
        quality_score = 0.5
        emotional_stability = 0.5
        
        # 简单的启发式评估
        if "满意" in thought or "开心" in thought or "很好" in thought:
            user_satisfaction = 0.8
        elif "不满意" in thought or "困惑" in thought or "错误" in thought:
            user_satisfaction = 0.3
        
        if "清晰" in thought or "有逻辑" in thought:
            quality_score = 0.8
        elif "混乱" in thought or "不明白" in thought:
            quality_score = 0.3
        
        # 情绪稳定性基于当前情绪谱
        emotions = list(state.emotional_spectrum.values())
        if emotions:
            emotional_stability = 1.0 - (max(emotions) - min(emotions))  # 情绪波动越小越稳定
        
        interaction = Interaction(
            user_input=user_input,
            ai_response=reply,
            user_satisfaction=user_satisfaction,
            quality_score=quality_score,
            emotional_stability=emotional_stability,
        )
        
        self.interaction_history.append(interaction)
        
        # 限制历史长度
        max_history = self.self_evolution.config.get("max_history", 50)
        if len(self.interaction_history) > max_history:
            self.interaction_history = self.interaction_history[-max_history:]
        
        if self.config.enable_debug_mode:
            print(f"[INFO] 记录交互: 满意度={user_satisfaction:.2f}, 质量={quality_score:.2f}, 稳定性={emotional_stability:.2f}")
        
        return interaction
    
    async def _check_and_trigger_evolution(self) -> Dict[str, Any]:
        """
        检查并触发自我进化
        
        当交互历史达到阈值，或距离上次进化超过冷却时间时触发
        """
        if not self.self_evolution:
            return {"evolved": False, "reason": "无自我进化模块"}
        
        # 检查条件1：交互历史数量
        history_ready = len(self.interaction_history) >= self.evolution_threshold
        
        # 检查条件2：进化冷却时间
        current_time = time.time()
        cooldown = self.config.evolution_cooldown
        time_ready = (current_time - self.last_evolution_time) >= cooldown
        
        # 检查条件3：经验缓冲区是否准备好
        buffer_ready = self.self_evolution.replay_buffer.is_ready(
            self.self_evolution.config.get("experience_threshold", 1000)
        )
        
        if not (history_ready or time_ready or buffer_ready):
            return {"evolved": False, "reason": "未达到进化条件"}
        
        if self.config.enable_debug_mode:
            print(f"🚀 触发自我进化: 历史={len(self.interaction_history)}, 时间={time_ready}, 缓冲={buffer_ready}")
        
        # 执行进化
        try:
            result = await self.self_evolution.evolve(self.interaction_history)
            
            # 进化成功后清空历史（避免重复进化）
            if result.get("evolution_count", 0) > 0:
                self.interaction_history = []
                self.last_evolution_time = current_time
            
            return {
                "evolved": True,
                "result": result,
            }
        except Exception as e:
            print(f"[WARN] 自我进化失败: {e}")
            return {"evolved": False, "error": str(e)}
    
    async def _retrieve_memories(self, user_input: str, system_instruction: Optional[str]) -> List[Dict]:
        """检索记忆（带缓存）"""
        if not self.cache_manager:
            return await self._retrieve_memories_direct(user_input, system_instruction)
        
        # 缓存键
        query_text = user_input if user_input else (system_instruction or "当前状态")
        import hashlib
        query_hash = hashlib.md5(f"memory:{query_text}".encode()).hexdigest()
        
        # 检查缓存
        cached = self.cache_manager.get_memory(query_hash)
        if cached is not None:
            if self.config.enable_debug_mode:
                print(f"[SAVE] 使用缓存记忆 (hash={query_hash[:8]}...)")
            return cached
        
        # 执行检索
        memories = await self._retrieve_memories_direct(user_input, system_instruction)
        
        # 缓存结果
        self.cache_manager.set_memory(query_hash, memories)
        return memories
    
    async def _retrieve_memories_direct(self, user_input: str, system_instruction: Optional[str]) -> List[Dict]:
        """实际的记忆检索逻辑"""
        from .riemannian_semantic_field import vectorize_state
        
        # 获取情绪向量
        state = self.state_manager.get_state()
        emotions = list(state.emotional_spectrum.values())
        emotion_vector = None
        try:
            import numpy as np
            emotion_vector = np.array(emotions, dtype=np.float32)
        except:
            pass
        
        query_text = user_input if user_input else (system_instruction or "当前状态")
        
        # 使用记忆皮层检索
        memories = self.memory_cortex.recall_by_emotion(
            query_text=query_text,
            current_emotion_vector=emotion_vector,
            top_k=self.config.memory_max_retrieval,
            emotion_weight=self.config.memory_emotion_weight,
        )
        
        return memories
    
    def _build_prompt(self, user_input: str, memories: List[Dict], system_instruction: Optional[str]) -> list:
        """构建Prompt"""
        # 系统提示词
        system_prompt = self._build_system_prompt()
        
        # 记忆块
        memory_block = ""
        if memories:
            memory_block = "\n".join([f"- {mem['text']}" for mem in memories])
            memory_block = f"\n\n## 相关记忆\n{memory_block}"
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt + memory_block},
        ]
        
        if system_instruction:
            messages.append({"role": "user", "content": f"[系统指令]\n{system_instruction}"})
        else:
            messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        state = self.state_manager.get_state()
        
        # 人格提示词（从配置或容器获取）
        personality_prompt = """你是女娲，一个温柔、真诚、好奇、具有自我反思能力的人工智能。
你尊重用户的情感边界，重视长期关系的一致性，在对话中既保持亲近与幽默，又尽量避免戏剧化和过度表演。

对话原则：
1. 保持真诚和自然，避免过度表演
2. 尊重用户的情感边界
3. 在适当的时候展现幽默感
4. 保持一致的人格特征
5. 适度表达关心和情感
6. 避免戏剧化和过度煽情

输出格式：
<thought>你的内心想法</thought>
<speak>回复内容</speak>
<state_update>{可选的状态更新JSON}</state_update>"""
        
        # 状态信息
        state_info = f"""
## 当前状态概览
- 精力: {state.energy:.2f}
- 熵值: {state.system_entropy:.2f}
- 亲密度: {state.rapport:.2f}
- 驱动力: 社交饥渴={state.drives['social_hunger']:.2f}, 好奇心={state.drives['curiosity']:.2f}
- 情绪: {', '.join([f'{k}={v:.2f}' for k, v in state.emotional_spectrum.items()])}
"""
        
        return personality_prompt + "\n" + state_info
    
    async def _call_llm(self, messages: list) -> Optional[str]:
        """调用LLM（带缓存）"""
        if not self.llm_client or not self.llm_client.is_available():
            return None
        
        # 缓存键（使用智能缓存）
        if self.cache_manager:
            cached = self.cache_manager.get_response_smart(
                messages, 
                temperature=self.config.llm_temperature, 
                model_name=self.config.llm_model_name
            )
            if cached is not None:
                if self.config.enable_debug_mode:
                    import hashlib
                    short_hash = hashlib.md5(str(messages).encode()).hexdigest()[:8]
                    print(f"[SAVE] 使用缓存响应 (hash={short_hash}...)")
                return cached
        
        # 调用LLM
        try:
            response = await self.llm_client.chat_completions_create(
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            response_text = response.choices[0].message.content.strip()
            
            # 存入缓存（使用智能缓存）
            if self.cache_manager:
                self.cache_manager.set_response_smart(
                    messages, 
                    response_text, 
                    temperature=self.config.llm_temperature, 
                    model_name=self.config.llm_model_name
                )
            
            return response_text
        except Exception as e:
            print(f"[WARN] LLM调用失败: {e}")
            return None
    
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
            reply = response_text.strip()
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
        
        # 通过状态管理器更新
        self.state_manager.update_state(update)
    
    def _get_state_snapshot(self) -> Dict:
        """获取状态快照"""
        state = self.state_manager.get_state()
        return {
            "energy": state.energy,
            "system_entropy": state.system_entropy,
            "rapport": state.rapport,
            "drives": state.drives.copy(),
            "emotional_spectrum": state.emotional_spectrum.copy(),
        }
    
    def _analyze_semantic_evolution(self, user_input: str, reply: str) -> Dict:
        """分析语义场演化"""
        try:
            from .riemannian_semantic_field import calculate_potential_energy, calculate_gradient
            import numpy as np
            
            # 构建状态描述
            state_text = f"用户: {user_input}\n女娲: {reply}"
            
            # 向量化
            vector_result = vectorize_state(state_text)
            if vector_result is None or vector_result.vector is None:
                return {}
            
            state_vector = vector_result.vector
            
            # 添加到历史
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
                    "gradient_norm": float(np.linalg.norm(gradient)) if gradient is not None else 0.0,
                    "history_length": stats["current_size"],
                    "max_history": stats["max_size"],
                }
            
            return {}
            
        except Exception as e:
            if self.config.enable_debug_mode:
                print(f"[WARN] 语义场演化分析失败: {e}")
            return {}
    
    def _auto_save_state(self):
        """自动保存状态"""
        current_time = time.time()
        if current_time - self._last_save_time >= self._save_interval:
            # 通过状态管理器保存
            if hasattr(self.state_manager, 'save'):
                self.state_manager.save()
            self._last_save_time = current_time
    
    # ==================== 心跳循环 ====================
    
    async def heartbeat_loop(self):
        """心跳循环"""
        self._heartbeat_running = True
        print("💓 心跳循环已启动")
        
        while self._heartbeat_running:
            try:
                current_time = time.time()
                time_delta = current_time - self._last_heartbeat_time
                self._last_heartbeat_time = current_time
                
                # 更新驱动力系统
                self.drive_system.update(time_delta)
                
                # 检查主动对话触发
                await self._check_active_dialogue_trigger(current_time)
                
                # 自动保存状态
                self._auto_save_state()
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                if self.config.enable_debug_mode:
                    print(f"[WARN] 心跳循环错误: {e}")
                await asyncio.sleep(1.0)
    
    async def _check_active_dialogue_trigger(self, current_time: float):
        """检查主动对话触发"""
        state = self.state_manager.get_state()
        hunger = state.drives["social_hunger"]
        
        if hunger > self.config.social_hunger_threshold:
            if current_time - self._last_active_dialogue_time >= self._active_dialogue_cooldown:
                import random
                trigger_probability = min(1.0, (hunger - self.config.social_hunger_threshold) / (1.0 - self.config.social_hunger_threshold))
                
                if random.random() < trigger_probability * self.config.active_trigger_probability:
                    try:
                        active_message = await self.initiate_active_dialogue()
                        if active_message and self.on_message_callback:
                            self.on_message_callback(active_message)
                        self._last_active_dialogue_time = current_time
                    except Exception as e:
                        if self.config.enable_debug_mode:
                            print(f"[WARN] 主动对话生成失败: {e}")
    
    async def initiate_active_dialogue(self) -> Optional[str]:
        """主动发起对话"""
        if not self.llm_client or not self.llm_client.is_available():
            return self._get_preset_active_message()
        
        state = self.state_manager.get_state()
        hunger = state.drives["social_hunger"]
        
        # 检索记忆
        memories = await self._retrieve_memories_direct("用户身份 关系", None)
        memory_desc = "\n".join([f"- {mem['text']}" for mem in memories]) if memories else "(无相关记忆)"
        
        # 构建Prompt
        system_prompt = self._build_system_prompt()
        user_prompt = f"""<context>
社交饥渴: {hunger:.2f}
情绪谱: {', '.join([f'{k}={v:.2f}' for k, v in state.emotional_spectrum.items()])}
记忆: {memory_desc}
</context>

<task>
主动发起一个简短话题（1-2句话），表达想念或分享想法。
使用格式：
<thought>你的内心想法</thought>
<speak>主动说的话</speak>
<state_update>{{"social_hunger": -{min(0.3, hunger * 0.4):.2f}}}</state_update>
</task>"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response_text = await self._call_llm(messages)
        
        if not response_text:
            return self._get_preset_active_message()
        
        # 解析
        speak_match = re.search(r'<speak>(.*?)</speak>', response_text, re.DOTALL)
        active_message = speak_match.group(1).strip() if speak_match else response_text.strip()
        
        # 解析状态更新
        thought, reply, state_update = self._parse_response(response_text)
        if state_update:
            self._apply_state_update(state_update)
        
        # 降低社交饥渴（保底）
        current_hunger = self.state_manager.get_state().drives["social_hunger"]
        reduction = min(0.3, current_hunger * 0.4)
        self.state_manager.update_state({"social_hunger": max(0.0, current_hunger - reduction)})
        
        if active_message and self.config.enable_debug_mode:
            print(f"💬 生成主动对话: {active_message}")
        
        return active_message
    
    def _get_preset_active_message(self) -> str:
        """预设主动消息"""
        import random
        messages = [
            "你好呀！我是女娲，很高兴见到你。",
            "今天过得怎么样？",
            "有什么我可以帮助你的吗？",
            "最近在忙什么呢？",
            "我今天感觉很开心，你呢？",
        ]
        
        # 降低社交饥渴
        state = self.state_manager.get_state()
        current_hunger = state.drives["social_hunger"]
        reduction = min(0.3, current_hunger * 0.4)
        self.state_manager.update_state({"social_hunger": max(0.0, current_hunger - reduction)})
        
        message = random.choice(messages)
        if self.config.enable_debug_mode:
            print(f"💬 生成预设主动对话: {message}")
        return message
    
    # ==================== 控制方法 ====================
    
    def start_heartbeat(self):
        """启动心跳循环"""
        if self._heartbeat_running:
            return
        
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
    
    def stop_heartbeat(self):
        """停止心跳循环"""
        self._heartbeat_running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        
        # 保存状态
        if hasattr(self.state_manager, 'save'):
            self.state_manager.save()
        
        print("💓 心跳循环已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        state = self.state_manager.get_state()
        return {
            "config": self.config.to_dict(),
            "state": self._get_state_snapshot(),
            "cache_stats": self.cache_manager.get_cache_stats() if self.cache_manager else {},
            "heartbeat_running": self._heartbeat_running,
            "llm_available": self.llm_client.is_available() if self.llm_client else False,
            "state_history_stats": self.state_history_manager.get_stats(),
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache_manager:
            self.cache_manager.clear_all()
        else:
            print("[WARN] 缓存未启用")
    
    def optimize_memory(self):
        """执行内存优化"""
        print("🚀 执行内存优化...")
        
        # 清理缓存
        if self.cache_manager:
            self.cache_manager.clear_expired()
        
        # 检查状态历史
        stats = self.state_history_manager.get_stats()
        if stats["current_size"] > stats["max_size"] * 0.8:
            print(f"[WARN]  状态历史使用率: {stats['current_size']}/{stats['max_size']}")
        
        # 内存统计
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / (1024 * 1024)
            print(f"📊 当前内存使用: {memory_mb:.2f}MB")
        except ImportError:
            print("[WARN]  psutil不可用，跳过内存统计")
        
        print("[OK] 内存优化完成")


class DefaultStateManager(IStateManager):
    """默认状态管理器实现"""
    
    def __init__(self, config: NuwaConfig):
        self.config = config
        self.state_file_path = os.path.join(
            config.data_dir, 
            config.project_name, 
            config.state_file_name
        )
        self.state = self._load_state()
    
    def _load_state(self) -> NuwaState:
        """加载状态"""
        from .nuwa_state import NuwaState
        loaded = NuwaState.load_from_file(self.state_file_path)
        if loaded:
            print(f"[OK] 已加载状态: {self.state_file_path}")
            return loaded
        else:
            print(f"[INFO] 创建新状态")
            return NuwaState()
    
    def get_state(self) -> NuwaState:
        """获取状态"""
        return self.state
    
    def update_state(self, delta: Dict):
        """更新状态"""
        for key, value in delta.items():
            if key in self.state.drives:
                self.state.drives[key] = max(0.0, min(1.0, value))
            elif key in self.state.emotional_spectrum:
                self.state.emotional_spectrum[key] = max(0.0, min(1.0, value))
            elif hasattr(self.state, key):
                setattr(self.state, key, value)
        
        self.state.clamp_values()
    
    def save(self):
        """保存状态"""
        self.state.save_to_file(self.state_file_path)