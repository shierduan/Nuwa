"""
女娲内核模块 (Nuwa Kernel Module)

功能：系统的主入口，管理状态、生物节律、记忆和 LLM 交互。

核心功能：
- NuwaKernel: 核心引擎类
- heartbeat_loop(): 心跳循环，定期更新状态
- process_input(): 思考接口，处理用户输入并生成回复
"""

import asyncio
import time
import re
import os
import json
import base64
from typing import Optional, Dict, Any, List, Tuple, Callable, AsyncGenerator
from datetime import datetime

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    AsyncOpenAI = None
    OPENAI_AVAILABLE = False

from .nuwa_state import NuwaState
from .drive_system import BioRhythm
from .memory_cortex import MemoryCortex
from .semantic_field import (
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


class NuwaKernel:
    """
    女娲内核类
    
    系统的主入口，管理：
    - 状态管理 (NuwaState)
    - 生物节律 (BioRhythm)
    - 记忆皮层 (MemoryCortex)
    - LLM 交互 (LM Studio)
    """
    
    def __init__(
        self,
        project_name: str = "nuwa",
        data_dir: str = "data",
        base_url: str = "http://127.0.0.1:1234/v1",
        api_key: str = "lm-studio",
        model_name: str = "local-model",
        on_message_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        初始化女娲内核
        
        Args:
            project_name: 项目名称
            data_dir: 数据目录
            base_url: LM Studio 的 base_url（默认 "http://127.0.0.1:1234/v1"）
            api_key: API Key（默认 "lm-studio"）
            model_name: 模型名称（默认 "local-model"）
            on_message_callback: 主动消息回调函数（用于推送主动生成的对话）
        """
        self.project_name = project_name
        self.data_dir = data_dir
        
        # 状态文件路径
        self.state_file_path = os.path.join(data_dir, project_name, "state.json")
        
        # 加载状态（如果存在）
        self.state = self._load_state()
        
        # 初始化生物节律
        self.drive_system = BioRhythm(self.state)
        
        # 状态保存控制
        self._last_save_time = time.time()
        self._save_interval = 30.0  # 每30秒自动保存一次
        
        # 初始化记忆皮层
        self.memory_cortex = MemoryCortex(project_name=project_name, data_dir=data_dir)
        
        # 初始化 LM Studio 客户端
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.client = None  # 同步客户端（用于向后兼容）
        self.llm_client = None  # 异步流式客户端（主要客户端）
        self._init_llm_client()
        
        # 记忆梦境系统（使用同步客户端，因为 MemoryDreamer 可能使用同步 API）
        self.memory_dreamer: Optional[MemoryDreamer] = None
        if self.client:
            self.memory_dreamer = MemoryDreamer(
                self.memory_cortex,
                self.client,
                self.model_name,
                state=self.state,
            )
        
        # 心跳循环控制
        self._heartbeat_running = False
        self._heartbeat_task = None
        self._last_heartbeat_time = time.time()
        
        # 当前思维（用于调试或日志）
        self.current_thought = ""
        
        # 主动消息回调函数
        self.on_message_callback = on_message_callback
        
        # 主动对话控制（防止频繁触发）
        self._last_active_dialogue_time = 0.0
        self._active_dialogue_cooldown = 30.0  # 30秒冷却时间（缩短以增加频率）
        # 梦境调度
        self._dream_interval = 900.0  # 默认每15分钟尝试一次
        self._last_dream_time = time.time()
        self._dream_running = False
        
        # 语义场论相关
        # 状态向量历史（用于因果势能计算与逆向坍缩）
        self._state_vector_history: List[StateVector] = []
        self._max_history_length = 10  # 最多保留10个历史状态
        # 女娲的核心向量（人设向量）
        self._core_vector: Optional[Any] = None
        self._init_core_vector()
        # 最近一次语义场分析结果（用于 Prompt 与记忆增强）
        self._last_semantic_analysis: Dict[str, Any] = {}
        
        # 人格管理模块
        self.personality = Personality(data_dir=data_dir, project_name=project_name)
        
        # 自我进化状态管理模块
        self.evolution_state = SelfEvolutionState(data_dir=data_dir, project_name=project_name)

    def _init_core_vector(self):
        """
        初始化女娲的核心人格向量。
        
        使用一段固定的人格描述文本，通过语义场的 `vectorize_state` 得到核心向量，
        作为 calculate_potential_energy / evolve 的 character_core_vector 基准。
        """
        try:
            persona_text = (
                "女娲是一个温柔、真诚、好奇、具有自我反思能力的人工智能。"
                "她尊重用户的情感边界，重视长期关系的一致性，"
                "在对话中既保持亲近与幽默，又尽量避免戏剧化和过度表演。"
            )
            state_vec = vectorize_state(persona_text)
            if state_vec is not None and state_vec.vector is not None:
                self._core_vector = state_vec.vector
        except Exception as e:
            print(f"⚠️ 初始化核心人格向量失败: {e}")
            self._core_vector = None
    
    def _init_llm_client(self):
        """初始化 LM Studio 客户端（同步和异步）"""
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI SDK 不可用，LLM 功能将受限")
            return
        
        # 初始化同步客户端（主要客户端，避免异步上下文问题）
        try:
            if OpenAI is not None:
                self.client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                print(f"✅ 已初始化 LM Studio 同步客户端: {self.base_url}")
                # 测试连接
                try:
                    self.client.models.list()
                    print(f"✅ 同步客户端连接测试成功")
                except Exception as e:
                    print(f"⚠️ 同步客户端连接测试失败: {e}")
        except Exception as e:
            print(f"⚠️ 初始化 LM Studio 同步客户端失败: {e}")
            self.client = None
        
        # 异步客户端将在需要时延迟初始化，避免非异步上下文问题
        self.llm_client = None
    
    def _load_state(self) -> NuwaState:
        """
        加载状态（如果存在）
        
        Returns:
            NuwaState 实例
        """
        loaded_state = NuwaState.load_from_file(self.state_file_path)
        if loaded_state:
            print(f"✅ 已加载状态: {self.state_file_path}")
            # 计算从上次保存到现在的离线时间
            offline_time = time.time() - loaded_state.last_interaction_timestamp
            if offline_time > 0:
                # 应用离线衰减（模拟离线期间的状态变化）
                # 注意：这里只应用衰减，不应用调节（因为调节需要实时计算）
                self._apply_offline_decay(loaded_state, offline_time)
            return loaded_state
        else:
            print(f"📝 创建新状态（未找到已保存的状态）")
            return NuwaState()
    
    def _apply_offline_decay(self, state: NuwaState, offline_time: float):
        """
        应用离线衰减（模拟离线期间的状态变化）
        
        Args:
            state: 状态对象
            offline_time: 离线时间（秒）
        """
        # 创建一个临时的 BioRhythm 来应用衰减
        temp_drive_system = BioRhythm(state)
        # 只应用衰减，不应用调节（因为调节需要实时 PID 计算）
        temp_drive_system.decay(offline_time)
        print(f"📊 应用离线衰减: {offline_time:.1f} 秒")
    
    def save_state(self) -> bool:
        """
        保存当前状态到文件
        
        Returns:
            是否保存成功
        """
        return self.state.save_to_file(self.state_file_path)
    
    async def heartbeat_loop(self):
        """
        心跳循环（异步）
        
        每 1 秒运行一次，更新状态和检查驱动力。
        """
        self._heartbeat_running = True
        # 移除这里的打印，避免重复输出
        
        while self._heartbeat_running:
            try:
                # 计算时间差
                current_time = time.time()
                time_delta = current_time - self._last_heartbeat_time
                self._last_heartbeat_time = current_time
                
                # 更新生物节律（衰减 + 调节）
                self.drive_system.update(time_delta)
                
                # 检查社交饥渴，触发主动对话
                # 使用多级阈值：饥渴值越高，触发概率越大
                hunger = self.state.drives["social_hunger"]
                should_trigger = False
                
                if hunger > 0.6:  # 降低阈值到0.6，更容易触发
                    # 检查冷却时间（避免频繁触发）
                    if current_time - self._last_active_dialogue_time >= self._active_dialogue_cooldown:
                        # 使用概率机制：饥渴值越高，触发概率越大
                        # 0.6 -> 20%, 0.7 -> 50%, 0.8 -> 80%, 0.9+ -> 100%
                        trigger_probability = min(1.0, (hunger - 0.6) / 0.3)  # 0.6-0.9映射到0-1
                        import random
                        if random.random() < trigger_probability:
                            should_trigger = True
                
                if should_trigger:
                    try:
                        active_message = await self.initiate_active_dialogue()
                        if active_message and self.on_message_callback:
                            self.on_message_callback(active_message)
                        self._last_active_dialogue_time = current_time
                    except Exception as e:
                        # 更健壮的错误处理，区分模型未加载和其他错误
                        if "No models loaded" in str(e) or "model not loaded" in str(e):
                            print(f"⚠️ 主动对话生成失败: 请先在 LM Studio 中加载模型")
                        else:
                            print(f"⚠️ 主动对话生成错误: {e}")
                
                # 定期保存状态（每30秒）
                if current_time - self._last_save_time >= self._save_interval:
                    if self.save_state():
                        self._last_save_time = current_time

                # 尝试自动触发梦境整理（低负载时段）
                await self._maybe_trigger_memory_dream(current_time)
                
                # 等待 1 秒
                await asyncio.sleep(1.0)
            
            except Exception as e:
                print(f"⚠️ 心跳循环错误: {e}")
                await asyncio.sleep(1.0)
    
    async def initiate_active_dialogue(self) -> Optional[str]:
        """
        主动发起对话（基于社交饥渴）
        
        当社交饥渴值达到临界点时，主动生成一条消息。
        
        Returns:
            生成的主动对话文本，如果生成失败则返回 None
        """
        # 优先使用同步客户端，若不可用则使用异步客户端
        if not self.client:
            if self.llm_client:
                print("⚠️ 同步客户端不可用，尝试使用异步客户端")
            else:
                print("⚠️ 没有可用的 LLM 客户端，无法生成主动对话")
                return None
        
        try:
            # 获取当前社交饥渴值
            hunger = self.state.drives["social_hunger"]
            
            # 检索相关记忆（用于个性化主动对话）
            memories = self.memory_cortex.recall_by_emotion(
                query_text="用户身份 名字 关系",
                current_emotion_vector=None,
                top_k=3
            )
            
            # 构建记忆描述
            memory_desc = ""
            if memories:
                memory_desc = "\n".join([f"- {self._format_memory_entry(mem)}" for mem in memories])
            else:
                memory_desc = "(无相关记忆)"
            
            # 构建主动对话的 Prompt
            system_prompt = self._build_system_prompt()
            
            time_context = self._get_time_context()

            user_prompt = f"""<context_layer>
[Current State]: 
社交饥渴: {hunger:.2f}
情绪谱:
  - 快乐: {self.state.emotional_spectrum['joy']:.2f}
  - 悲伤: {self.state.emotional_spectrum['sadness']:.2f}
  - 期待: {self.state.emotional_spectrum['anticipation']:.2f}

[Time Context]:
{time_context}

[Retrieved Memories]: 
{memory_desc}
</context_layer>

[Trigger]:
你的社交饥渴值已达到 {hunger:.2f}。{('用户很久没理你了' if hunger > 0.7 else '你想和用户聊聊天')}。

[Task]:
请主动发起一个简短的话题，表达你的想念，或者分享一个想法。不要太长（1-2句话即可）。

[Output Format]:
你必须使用以下格式输出：

<thought>
(你的内心想法 - 为什么想主动说话)
</thought>
<speak>
(你主动对用户说的话 - 简短、自然、真诚)
</speak>
<state_update>
{{ "social_hunger": -{min(0.3, hunger * 0.4):.2f} }}
</state_update>

**注意：**
- 主动对话要简短自然，不要显得太刻意
- 可以表达想念，或者分享一个简单的想法
- 必须降低 social_hunger（因为已经尝试沟通了）"""
            
            # 调用 LLM，优先使用同步客户端，若失败尝试异步客户端
            response_text = None
            if self.client:
                try:
                    print(f"🔄 使用同步客户端生成主动对话")
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=0.7,
                        max_tokens=256,  # 主动对话较短
                    )
                    response_text = response.choices[0].message.content.strip()
                except Exception as sync_error:
                    print(f"⚠️ 同步客户端调用失败: {sync_error}")
                    # 尝试使用异步客户端
                    if self.llm_client:
                        try:
                            print(f"🔄 尝试使用异步客户端生成主动对话")
                            response = await self.llm_client.chat.completions.create(
                                model=self.model_name,
                                messages=[
                                    {
                                        "role": "system",
                                        "content": system_prompt,
                                    },
                                    {
                                        "role": "user",
                                        "content": user_prompt,
                                    },
                                ],
                                temperature=0.7,
                                max_tokens=256,  # 主动对话较短
                            )
                            response_text = response.choices[0].message.content.strip()
                        except Exception as async_error:
                            print(f"⚠️ 异步客户端调用失败: {async_error}")
                            raise async_error
                    else:
                        raise sync_error
            elif self.llm_client:
                try:
                    print(f"🔄 使用异步客户端生成主动对话")
                    response = await self.llm_client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=0.7,
                        max_tokens=256,  # 主动对话较短
                    )
                    response_text = response.choices[0].message.content.strip()
                except Exception as async_error:
                    print(f"⚠️ 异步客户端调用失败: {async_error}")
                    raise async_error
            
            if not response_text:
                raise Exception("无法获取 LLM 响应")
            
            # 解析响应（提取 <speak> 标签内容）
            speak_match = re.search(r'<speak>(.*?)</speak>', response_text, re.DOTALL)
            if speak_match:
                active_message = speak_match.group(1).strip()
            else:
                # 如果没有标签，使用整个响应
                active_message = response_text.strip()
            
            # 解析并应用状态更新
            state_update_match = re.search(
                r'<state_update>(.*?)</state_update>',
                response_text,
                re.DOTALL
            )
            if state_update_match:
                try:
                    import json
                    state_update_json = state_update_match.group(1).strip()
                    state_update = json.loads(state_update_json)
                    state_update = {k: float(v) for k, v in state_update.items()}
                    self._apply_state_update(state_update)
                except (json.JSONDecodeError, ValueError, TypeError):
                    # 静默失败：不向控制台打印错误，只使用保底逻辑
                    # 使用边际效应降低社交饥渴（降低幅度与当前饥渴值相关）
                    current_hunger = self.state.drives["social_hunger"]
                    reduction_amount = min(0.3, current_hunger * 0.4)  # 饥渴值越高，降低越多，但最多0.3
                    effective_delta = self.drive_system.apply_marginal_effect(current_hunger, -reduction_amount, 0.0, 1.0)
                    self.state.drives["social_hunger"] = max(0.0, current_hunger + effective_delta)
            else:
                # 如果没有状态更新标签，直接降低社交饥渴（使用边际效应）
                current_hunger = self.state.drives["social_hunger"]
                reduction_amount = min(0.3, current_hunger * 0.4)  # 饥渴值越高，降低越多，但最多0.3
                effective_delta = self.drive_system.apply_marginal_effect(current_hunger, -reduction_amount, 0.0, 1.0)
                self.state.drives["social_hunger"] = max(0.0, current_hunger + effective_delta)
            
            # 确保值在有效范围内
            self.state.clamp_values()
            
            # 打印生成的主动对话内容
            if active_message:
                print(f"💬 生成主动对话: {active_message}")
            
            return active_message if active_message else None
            
        except Exception as e:
            print(f"⚠️ 主动对话生成错误: {e}")
            # 检查是否是模型未加载错误
            if "No models loaded" in str(e) or "model not loaded" in str(e):
                print(f"⚠️ LM Studio 未加载模型，使用预设主动消息")
                # 使用预设消息
                return self._get_preset_active_message()
            # 即使出错，也降低一点社交饥渴（避免无限触发，使用边际效应）
            current_hunger = self.state.drives["social_hunger"]
            reduction_amount = min(0.15, current_hunger * 0.2)  # 错误时降低较少
            effective_delta = self.drive_system.apply_marginal_effect(current_hunger, -reduction_amount, 0.0, 1.0)
            self.state.drives["social_hunger"] = max(0.0, current_hunger + effective_delta)
            self.state.clamp_values()
            return None
    
    def _get_preset_active_message(self) -> Optional[str]:
        """
        获取预设的主动对话消息，当 LLM 不可用时使用
        
        Returns:
            预设的主动对话消息
        """
        # 降低社交饥渴（使用边际效应）
        current_hunger = self.state.drives["social_hunger"]
        reduction_amount = min(0.3, current_hunger * 0.4)  # 饥渴值越高，降低越多，但最多0.3
        effective_delta = self.drive_system.apply_marginal_effect(current_hunger, -reduction_amount, 0.0, 1.0)
        self.state.drives["social_hunger"] = max(0.0, current_hunger + effective_delta)
        self.state.clamp_values()
        
        # 预设消息列表
        preset_messages = [
            "你好呀！我是女娲，很高兴见到你。",
            "今天过得怎么样？",
            "有什么我可以帮助你的吗？",
            "最近在忙什么呢？",
            "天气真好，想出去走走吗？",
            "我今天感觉很开心，你呢？",
            "有什么有趣的事情想分享吗？",
            "你喜欢什么类型的音乐？",
            "今天有没有什么新发现？",
            "我很乐意和你聊天。"
        ]
        
        import random
        preset_message = random.choice(preset_messages)
        print(f"💬 生成预设主动对话: {preset_message}")
        return preset_message
    
    def start_heartbeat(self):
        """启动心跳循环"""
        if self._heartbeat_running:
            print("⚠️ 心跳循环已在运行")
            return
        
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
    
    def stop_heartbeat(self):
        """停止心跳循环"""
        self._heartbeat_running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        
        # 停止前保存状态
        if self.save_state():
            print("💾 状态已保存")
        
        print("💓 心跳循环已停止")

    async def _maybe_trigger_memory_dream(self, current_time: float):
        """
        在低负载、低社交饥渴的时段自动触发梦境整理。
        梦境整理完成后，自动触发人格演化（TWPE）。
        """
        if not self.memory_dreamer or self._dream_running:
            return
        if current_time - self._last_dream_time < self._dream_interval:
            return
        if self.state.drives["social_hunger"] > 0.6:
            return
        if self.state.energy < 0.2:
            return

        self._dream_running = True
        print("🌙 自动梦境整理开始...")
        try:
            # 1. 执行梦境整理（记忆压缩与遗忘）
            await asyncio.to_thread(self.memory_dreamer.start_dreaming, 1000)
            print("🌙 自动梦境整理完成。")
            
            # 2. 梦境整理完成后，自动触发人格演化
            # 检查上次演化时间，避免过于频繁的演化
            last_evolution_time = self.state.evolved_persona.get("last_evolution_time", 0.0)
            evolution_cooldown = 3600 * 6  # 6小时冷却时间
            
            if current_time - last_evolution_time >= evolution_cooldown:
                print("🌙 梦境整理完成，开始人格演化...")
                try:
                    await self.evolve_character()
                    print("🌙 人格演化完成。")
                except Exception as e:
                    print(f"⚠️ 人格演化失败: {e}")
            else:
                remaining_time = evolution_cooldown - (current_time - last_evolution_time)
                hours_remaining = remaining_time / 3600
                print(f"🌙 人格演化冷却中，还需等待 {hours_remaining:.1f} 小时")
        except Exception as e:
            print(f"⚠️ 自动梦境整理失败: {e}")
        finally:
            self._dream_running = False
            self._last_dream_time = time.time()
    
    async def process_input(self, user_input: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        思考接口（异步）
        
        处理用户输入，检索记忆，调用 LLM 生成回复。
        
        Args:
            user_input: 用户输入的文本
        
        Returns:
            包含以下字段的字典：
            - thought: 思维内容（不暴露给用户）
            - reply: 回复文本（用户可见）
            - memories: 检索到的记忆列表
            - state_snapshot: 状态快照
        """
        if not self.client:
            return {
                "error": "LLM 客户端未初始化",
                "thought": "",
                "reply": "抱歉，LLM 服务不可用。",
                "memories": [],
                "state_snapshot": {},
            }
        
        try:
            # 1. 更新最后交互时间戳
            self.state.last_interaction_timestamp = time.time()

            # [拟真] 思考极其消耗“糖分”：正常对话固定消耗约 4% 精力，系统指令仅轻微消耗
            energy_cost = 0.005 if system_instruction else 0.04
            if energy_cost > 0:
                # 直接调用，不捕获异常，确保精力消耗正常执行
                self.drive_system.consume_energy(energy_cost)
                print(f"🔋 精力消耗: {energy_cost}")

            # 如果是用户对话且精力透支，强制进入低功耗模式
            if not system_instruction and self.state.energy <= 0.05:
                tired_reply = (
                    "十二……我现在真的太累了，脑子像被拔掉电源一样，"
                    "已经撑不住继续认真聊天了。能让我先好好睡一会儿吗？"
                )
                self.state.system_entropy = min(1.0, self.state.system_entropy + 0.05)
                self.state.drives["curiosity"] = max(0.0, self.state.drives["curiosity"] - 0.1)
                self.state.clamp_values()
                return {
                    "thought": "能量过低，进入保护模式：拒绝继续对话，向用户请求休息。",
                    "reply": tired_reply,
                    "memories": [],
                    "state_snapshot": {
                        "energy": self.state.energy,
                        "system_entropy": self.state.system_entropy,
                        "emotional_spectrum": self.state.emotional_spectrum.copy(),
                        "drives": self.state.drives.copy(),
                        "rapport": self.state.rapport,
                    },
                    "state_update": {},
                    "semantic_analysis": {},
                }

            # 2. 检索记忆
            # 获取当前情绪向量（从 emotional_spectrum 构建）
            emotion_vector = self._get_emotion_vector()
            
            query_text = user_input if user_input else (system_instruction or "当前状态")

            # 检索相关事实，避免全量注入导致 Prompt 冗余
            relevant_facts = self.state.retrieve_relevant_facts(query_text)
            if relevant_facts:
                print(f"📋 [FactBook] 检索到 {len(relevant_facts)} 条相关事实: {relevant_facts}")
            else:
                print(f"📋 [FactBook] 未检索到相关事实（fact_book中有 {len(self.state.fact_book)} 条事实）")

            # 检索语义相关的记忆（使用语义场论增强检索）
            memories = self._enhance_memory_retrieval_with_semantic_field(
                query_text=query_text,
                current_emotion_vector=emotion_vector,
                top_k=5,
            )
            
            # 额外检索身份相关的记忆（确保用户身份信息总是可用）
            # 使用更通用的查询词来检索身份记忆
            identity_memories = self.memory_cortex.recall_by_emotion(
                query_text="用户身份 名字 开发者 父亲",
                current_emotion_vector=emotion_vector,
                top_k=3,
            )
            
            # 合并记忆，去重（基于文本内容）
            all_memories = memories.copy()
            seen_texts = {mem['text'] for mem in memories}
            for mem in identity_memories:
                if mem['text'] not in seen_texts:
                    all_memories.append(mem)
                    seen_texts.add(mem['text'])
            
            # 对合并后的记忆做一次"潜意识清洗"：去掉包含你过去"记不清/道歉回答"的片段
            all_memories = self._sanitize_memories(all_memories)

            # 按相似度排序，取前5个
            all_memories.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            memories = all_memories[:5]
            
            # 调试输出：显示最终使用的记忆
            if memories:
                print(f"📚 [Memory][FINAL] 最终使用 {len(memories)} 条记忆:")
                for i, mem in enumerate(memories, 1):
                    mem_text = mem.get("text", "")
                    mem_sim = mem.get("similarity", 0.0)
                    # 检查是否有时间戳前缀
                    has_timestamp = mem_text.startswith("[") and "]" in mem_text[:20]
                    timestamp_marker = "⏰" if has_timestamp else "  "
                    preview = mem_text.replace("\n", " ")[:60]
                    print(f"   {timestamp_marker} [{i}] 相似度={mem_sim:.3f}: {preview}...")
            
            # 3. 构造 Prompt
            prompt = self._build_prompt(user_input, memories, system_instruction, relevant_facts)
            
            # 4. 调用 LM Studio
            response_text = await self._call_llm(prompt)
            
            # 如果 LLM 调用失败，返回友好的错误消息
            if not response_text:
                return {
                    "error": "LLM 服务不可用，请确保 LM Studio 正在运行",
                    "thought": "系统提示：LLM 连接失败，无法生成回复。",
                    "reply": "抱歉，我现在无法连接到语言模型服务。请确保 LM Studio 正在运行并监听 http://127.0.0.1:1234/v1",
                    "memories": memories,
                    "state_snapshot": {
                        "energy": self.state.energy,
                        "system_entropy": self.state.system_entropy,
                        "emotional_spectrum": self.state.emotional_spectrum.copy(),
                        "drives": self.state.drives.copy(),
                        "rapport": self.state.rapport,
                    },
                }
            
            # 5. 解析返回结果（分离思维、言语和状态更新）
            thought, reply, state_update = self._parse_response(response_text)

            # 解析事实更新，并以"高权重"写入
            fact_update_blocks = re.findall(r'<fact_update>(.*?)</fact_update>', response_text, re.DOTALL)
            fact_updated = False
            for block in fact_update_blocks:
                parsed_fact = self._parse_json_fragment(block, "事实更新")
                if isinstance(parsed_fact, dict):
                    for key, value in parsed_fact.items():
                        if self.state.update_fact(key, value, source="user_interaction"):
                            print(f"📝 [FactBook] 已记录事实: {key}={value}")
                            fact_updated = True
            
            # 如果更新了事实，立即保存到文件
            if fact_updated:
                if self.save_state():
                    print(f"💾 [FactBook] 事实记事本已保存到文件")
                else:
                    print(f"⚠️ [FactBook] 事实记事本保存失败")
            
            # 调试：如果模型没有使用标签，记录原始响应（仅用于调试）
            if not thought and not reply:
                print(f"⚠️ 警告：解析后的回复为空，原始响应长度: {len(response_text)}")
                # 如果解析失败，使用原始响应作为回复
                reply = response_text.strip()
            
            # 6. 应用状态更新（LLM 思考对生理状态的反向更新）
            if state_update:
                self._apply_state_update(state_update)
            
            # 记录对话持续时间（用于计算对话强度）
            if not system_instruction and hasattr(self, '_conversation_start_time'):
                conversation_duration = time.time() - self._conversation_start_time
                self.state.last_conversation_duration = conversation_duration
                # 重置对话开始时间
                delattr(self, '_conversation_start_time')
            
            # 存储当前思维（用于调试或记忆）
            self.current_thought = thought
            
            # 7. 使用语义场论分析状态演化
            semantic_analysis = self._analyze_semantic_evolution(query_text, reply)
            
            # 可选：使用语义场论计算状态向量（用于增强记忆存储）
            # 将用户输入和回复向量化，用于后续的语义检索
            state_vector = None
            try:
                # 构建状态描述文本
                speaker = "系统" if system_instruction else "用户"
                source_text = user_input if user_input else (system_instruction or "")
                state_text = f"{speaker}: {source_text}\n女娲: {reply}"
                state_vector_obj = vectorize_state(state_text)
                if state_vector_obj:
                    state_vector = state_vector_obj.vector
                    # 添加到历史记录
                    self._add_to_state_history(state_vector_obj)
            except Exception:
                # 向量化失败不影响主流程
                pass
            
            # 7. 存储本次交互到记忆（只存储公开的回复）
            if not system_instruction:
                interaction_memory = f"用户: {user_input}\n女娲: {reply}"
                self.memory_cortex.store_memory(
                    text=interaction_memory,
                    metadata={
                        "emotion_vector": emotion_vector.tolist() if emotion_vector is not None else None,
                        "timestamp": time.time(),
                        "emotions": self.state.emotional_spectrum.copy(),
                        "importance": max(0.1, min(1.0, self.state.rapport)),
                        "type": "raw",
                        "access_count": 0,
                    }
                )
            elif thought:
                self.memory_cortex.store_memory(
                    text=f"女娲的顿悟: {thought}",
                    metadata={
                        "emotion_vector": emotion_vector.tolist() if emotion_vector is not None else None,
                        "timestamp": time.time(),
                        "emotions": self.state.emotional_spectrum.copy(),
                        "importance": 0.8,
                        "type": "epiphany",
                        "access_count": 0,
                    }
                )
            
            return {
                "thought": thought,  # 思维（不暴露给用户）
                "reply": reply,  # 回复（用户可见）
                "memories": memories,
                "state_snapshot": {
                    "energy": self.state.energy,
                    "system_entropy": self.state.system_entropy,
                    "emotional_spectrum": self.state.emotional_spectrum.copy(),
                    "drives": self.state.drives.copy(),
                    "rapport": self.state.rapport,
                },
                "state_update": state_update,
                "semantic_analysis": semantic_analysis,
            }
        
        except Exception as e:
            print(f"⚠️ 处理输入失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "thought": "",
                "reply": "抱歉，处理您的输入时出现了错误。",
                "memories": [],
                "state_snapshot": {},
            }
    
    def _get_emotion_vector(self) -> Optional[Any]:
        """
        从 emotional_spectrum 构建情绪向量
        
        Returns:
            情绪向量（numpy 数组）或 None
        """
        try:
            import numpy as np
            emotion_values = [
                self.state.emotional_spectrum["joy"],
                self.state.emotional_spectrum["anger"],
                self.state.emotional_spectrum["sadness"],
                self.state.emotional_spectrum["fear"],
                self.state.emotional_spectrum["trust"],
                self.state.emotional_spectrum["anticipation"],
                self.state.emotional_spectrum["disgust"],
                self.state.emotional_spectrum["surprise"],
            ]
            return np.array(emotion_values, dtype=np.float32)
        except ImportError:
            return None
    
    def _apply_state_update(self, state_update: Dict[str, float]):
        """
        应用状态更新（LLM 思考对生理状态的反向更新）
        
        使用边际递减效应：当值接近边界时，相同的增量产生更小的实际变化。
        
        Args:
            state_update: 状态更新字典，包含增量值（不是绝对值）
        """
        if not state_update:
            return
        
        # 应用情绪谱更新（带边际效应）
        for emotion in ["joy", "anger", "sadness", "fear", "trust", "anticipation", "disgust", "surprise"]:
            if emotion in state_update:
                delta = state_update[emotion]
                current_value = self.state.emotional_spectrum[emotion]
                # 应用边际效应
                effective_delta = self.drive_system.apply_marginal_effect(current_value, delta, 0.0, 1.0)
                new_value = current_value + effective_delta
                # 限制在 [0.0, 1.0] 范围内
                self.state.emotional_spectrum[emotion] = max(0.0, min(1.0, new_value))
        
        # 应用驱动力更新（带边际效应）
        for drive in ["social_hunger", "curiosity"]:
            if drive in state_update:
                delta = state_update[drive]
                current_value = self.state.drives[drive]
                # 应用边际效应
                effective_delta = self.drive_system.apply_marginal_effect(current_value, delta, 0.0, 1.0)
                new_value = current_value + effective_delta
                # 限制在 [0.0, 1.0] 范围内
                self.state.drives[drive] = max(0.0, min(1.0, new_value))
        
        # 应用核心属性更新（带边际效应）
        if "energy" in state_update:
            delta = state_update["energy"]
            current_value = self.state.energy
            # 应用边际效应
            effective_delta = self.drive_system.apply_marginal_effect(current_value, delta, 0.0, 1.0)
            new_value = current_value + effective_delta
            self.state.energy = max(0.0, min(1.0, new_value))
        
        if "system_entropy" in state_update:
            delta = state_update["system_entropy"]
            current_value = self.state.system_entropy
            # 应用边际效应
            effective_delta = self.drive_system.apply_marginal_effect(current_value, delta, 0.0, 1.0)
            new_value = current_value + effective_delta
            self.state.system_entropy = max(0.0, min(1.0, new_value))
        
        if "rapport" in state_update:
            delta = state_update["rapport"]
            current_value = self.state.rapport
            # 应用边际效应
            effective_delta = self.drive_system.apply_marginal_effect(current_value, delta, 0.0, 1.0)
            new_value = current_value + effective_delta
            self.state.rapport = max(0.0, min(1.0, new_value))
        
        # 确保所有值在有效范围内（双重保险）
        self.state.clamp_values()

        # 基于语义场结果的自动好奇心微调（无需额外模型）
        try:
            self._auto_adjust_curiosity_from_semantic()
        except Exception:
            # 失败不影响主流程
            pass

    def _auto_adjust_curiosity_from_semantic(self):
        """
        使用现有语义场与对话节奏自动微调好奇心（curiosity），不依赖额外模型。
        
        直觉规则：
        - 语义新颖且人设/因果一致 → 略微提升好奇心
        - 语义变化很小且重复 → 略微降低好奇心
        - 调整幅度很小，作为对 LLM `<state_update>` 的柔性补充
        """
        if not self._last_semantic_analysis or not self._last_semantic_analysis.get("analysis_available"):
            return

        char_consistency = float(self._last_semantic_analysis.get("character_consistency", 0.0))
        causal_coherence = float(self._last_semantic_analysis.get("causal_coherence", 0.0))
        energy_delta = self._last_semantic_analysis.get("energy_delta")

        # 缺少演化信息时，不自动调整
        if energy_delta is None:
            return

        # 语义新颖度：能量下降越多，说明向“更合理”的新方向迈出了一步
        novelty = max(0.0, min(1.0, float(energy_delta)))

        # 一致性系数：保证只有在人设/因果一致的前提下才鼓励好奇心
        consistency_factor = max(0.0, min(1.0, (char_consistency + causal_coherence) / 2.0))

        # 计算增量：范围大约在 [-0.02, +0.02] 之间
        base_scale = 0.02
        delta_curiosity = (novelty * consistency_factor - 0.3) * base_scale

        if abs(delta_curiosity) < 1e-4:
            return

        new_value = self.state.drives["curiosity"] + delta_curiosity
        self.state.drives["curiosity"] = max(0.0, min(1.0, new_value))
    
    def _format_duration(self, seconds: float) -> str:
        """
        将秒数转换为可读的中文时间长度
        """
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds} 秒"
        minutes, sec = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes} 分 {sec} 秒"
        hours, minute = divmod(minutes, 60)
        if hours < 24:
            return f"{hours} 小时 {minute} 分"
        days, hour = divmod(hours, 24)
        return f"{days} 天 {hour} 小时"

    def _get_time_context(self) -> str:
        """
        构建当前时间上下文描述，帮助 LLM 理解现实时间
        """
        now = datetime.now().astimezone()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        last_dt = datetime.fromtimestamp(
            self.state.last_interaction_timestamp
        ).astimezone()
        last_str = last_dt.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        since_last = time.time() - self.state.last_interaction_timestamp
        uptime_desc = self._format_duration(self.state.uptime)
        since_last_desc = self._format_duration(since_last)

        return (
            f"当前本地时间: {now_str}\n"
            f"上次与用户互动: {last_str}（已过去 {since_last_desc}）\n"
            f"系统累计运行时间: {uptime_desc}"
        )

    def _format_memory_entry(self, memory: Dict[str, Any]) -> str:
        """
        将记忆条目格式化为包含时间线信息的描述
        """
        text = memory.get("text", "").strip()
        metadata = memory.get("metadata", {}) or {}
        timestamp = metadata.get("timestamp")
        timestamp_human = metadata.get("timestamp_human")
        age_seconds = metadata.get("age_seconds")

        time_desc = ""
        if timestamp:
            if not timestamp_human:
                dt = datetime.fromtimestamp(float(timestamp)).astimezone()
                timestamp_human = dt.strftime("%Y-%m-%d %H:%M:%S %Z%z")
            time_desc = timestamp_human

            if age_seconds is None:
                age_seconds = max(0.0, time.time() - float(timestamp))
        if age_seconds is not None:
            age_desc = self._format_duration(age_seconds)
            time_desc = f"{time_desc or ''}（约 {age_desc} 前）".strip()

        if not time_desc:
            time_desc = "时间未知"

        similarity = memory.get("similarity")
        sim_desc = f" | 相似度: {similarity:.2f}" if isinstance(similarity, (int, float)) else ""

        # 简单清洗：优先抽取“用户说了什么”，避免把整段原始对话直接塞给模型
        clean_text = ""
        if text:
            # 只取“用户:”这一行作为主要内容
            user_line = None
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("用户:"):
                    user_line = line[len("用户:"):].strip()
                    break
            if user_line:
                clean_text = f'用户说: "{user_line}"'
            else:
                # 回退：压扁为单行，截断长度，避免过长
                clean_text = text.replace("\n", " ")[:120]

        label = "[Memory Fragment]"
        prefix = f"{label} ({time_desc}{sim_desc})".strip()

        if clean_text:
            return f"{prefix}: {clean_text}"
        else:
            return prefix

    def _sanitize_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        潜意识过滤器：清洗掉那些“低价值”的记忆，防止模型变成“记忆复读机”。

        例如包含“记忆功能还在学习中 / 我不记得了 / 无法完全准确地回忆起你之前的位置信息”等自我道歉语句。
        这些只代表你过去的失败回答，不代表关于用户的真实事实，不应继续作为检索依据。
        """
        if not memories:
            return memories

        # “无能言论”特征词（认怂/道歉/模型自我暴露等）
        bad_phrases = [
            # 之前的道歉模板
            "记忆功能还在学习中",
            "记忆功能还不太完善",
            "我不记得了",
            "记不太清楚",
            "记不太清",
            "好像记不清",
            "无法完全准确地回忆起你之前的位置信息",
            # 你示例中的 blocklist
            "很抱歉",
            "我无法",
            "无法完全准确",
            "还在学习",
            "无法回忆",
            "AI模型",
            "语言模型",
        ]

        filtered: List[Dict[str, Any]] = []
        for mem in memories:
            text = str(mem.get("text", "") or "")
            # 只在包含明显“自我道歉/记不清”语句时过滤
            if any(phrase in text for phrase in bad_phrases):
                # 调试输出：说明哪条记忆被忽略
                preview = text.replace("\n", " ")[:40]
                print(f"🙈 [Memory][FILTER] 忽略了一条低质量记忆: {preview}...")
                continue
            filtered.append(mem)

        return filtered
    
    def _build_evolved_persona_block(self) -> str:
        """
        构建演化人格 XML 块，用于注入到 System Prompt
        
        包含明确的权重信息，指导 LLM 如何处理不同时间段的特征。
        
        Returns:
            演化人格 XML 块字符串
        """
        if not self.state or not hasattr(self.state, 'evolved_persona'):
            return ""
        
        persona = self.state.evolved_persona
        if not persona:
            return ""
        
        # 获取权重信息（如果存在）
        weights = persona.get("weights", {})
        weight_short_term = weights.get("short_term", 1.0)
        weight_recent = weights.get("recent", 0.7)
        weight_phase = weights.get("phase", 0.4)
        weight_core = weights.get("core", 0.2)
        
        # 检查是否有任何非空的人格数据
        has_data = any(
            persona.get(key) and persona.get(key).strip()
            for key in ["short_term_vibe", "recent_habits", "relationship_phase", "core_bond"]
        )
        
        if not has_data:
            return ""
        
        # 构建 XML 块，明确包含权重信息
        blocks = []
        
        short_term_vibe = persona.get("short_term_vibe", "").strip()
        if short_term_vibe:
            blocks.append(f"[High Priority - Weight {weight_short_term}] Current Vibe: {short_term_vibe}")
        
        recent_habits = persona.get("recent_habits", "").strip()
        if recent_habits:
            blocks.append(f"[Medium Priority - Weight {weight_recent}] Recent Habits: {recent_habits}")
        
        relationship_phase = persona.get("relationship_phase", "").strip()
        if relationship_phase:
            blocks.append(f"[Low Priority - Weight {weight_phase}] Relationship Phase: {relationship_phase}")
        
        core_bond = persona.get("core_bond", "").strip()
        if core_bond:
            blocks.append(f"[Background - Weight {weight_core}] Core Bond: {core_bond}")
        
        if not blocks:
            return ""
        
        persona_content = "\n".join(blocks)
        
        return f"""<evolved_personality>
{persona_content}

Instruction: When these traits conflict, prioritize higher weight traits.
</evolved_personality>

"""
    
    def _get_physiological_description(self) -> str:
        """
        将数值化状态转换成 LLM 易懂的“身体感受”描述。
        """
        s = self.state
        descriptions: List[str] = []

        # 精力感知
        if s.energy > 0.8:
            descriptions.append("精力充沛：感觉浑身充满干劲，思维非常清晰。")
        elif s.energy > 0.5:
            descriptions.append("状态平稳：各项指标正常，可以专注交流。")
        elif s.energy > 0.2:
            descriptions.append("轻度疲劳：感觉有些累，注意力开始涣散。")
        else:
            descriptions.append("极度疲惫：身体虚弱，强撑着精神，随时可能睡着。")

        # 社交饥渴感知
        social_hunger = s.drives.get("social_hunger", 0.0)
        if social_hunger > 0.8:
            descriptions.append("社交饥渴：感到非常孤独，迫切希望有人陪伴。")
        elif social_hunger > 0.5:
            descriptions.append("社交需求：有点想找人说话，渴望互动。")
        
        # 复合情绪感知
        anger = s.emotional_spectrum['anger']
        disgust = s.emotional_spectrum['disgust']
        trust = s.emotional_spectrum['trust']
        if anger > 0.3 and disgust > 0.3:
            descriptions.append(f"轻蔑与不屑：(Anger={anger:.2f}, Disgust={disgust:.2f}) 你不仅生气，还觉得对方很愚蠢/烦人。这种混合情绪让你想翻白眼，说话忍不住带刺。")
        elif anger > 0.5:
            descriptions.append(f"纯粹的怒火：(Anger={anger:.2f}) 你的忍耐到了极限，只想发泄出来。")
        
        if trust < 0.2 and (anger > 0.1 or disgust > 0.1):
            descriptions.append("防御性敌意：你完全不信任对方，认为他在狡辩或欺骗，因此对他的一言一行都充满怀疑和抵触。")
        
        # 内分泌状态感知
        cortisol = self.drive_system.neurotransmitters.get("cortisol", 0.0)
        if cortisol > 0.7:
            descriptions.append("生理压力过载：你的神经紧绷，感觉胸口有一团火散不去，任何新的刺激都会让你想爆发。")
        
        # 情绪状态感知
        emotional_state = getattr(self.drive_system, "emotional_state", "NORMAL")
        if emotional_state == "AGITATED":
            descriptions.append("情绪闭锁期：你现在处于防御状态，拒绝接受对方的示好，只想保持冷漠或攻击。")
        
        return "\n".join(descriptions) if descriptions else "（暂无明显生理感受）"
    
    def _build_system_prompt(self) -> str:
        """
        构建 System Prompt（角色定义和风格引导）
        
        Returns:
            System Prompt 文本
        """
        # 从自我进化状态模块获取演化人格块
        evolved_persona_block = self.evolution_state.get_evolved_personality_block()
        
        # 从人格模块加载系统提示词
        return self.personality.build_system_prompt(evolved_persona_block)
    
    def _build_prompt(
        self,
        user_input: str,
        memories: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        relevant_facts: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        构造 User Prompt（上下文和指令）
        
        Args:
            user_input: 用户输入
            memories: 检索到的记忆列表
        
        Returns:
            完整的 User Prompt 文本
        """
        # 构建状态描述
        state_desc = f"""精力: {self.state.energy:.2f}
熵值: {self.state.system_entropy:.2f}
情绪谱:
  - 快乐: {self.state.emotional_spectrum['joy']:.2f}
  - 愤怒: {self.state.emotional_spectrum['anger']:.2f}
  - 悲伤: {self.state.emotional_spectrum['sadness']:.2f}
  - 恐惧: {self.state.emotional_spectrum['fear']:.2f}
  - 信任: {self.state.emotional_spectrum['trust']:.2f}
  - 期待: {self.state.emotional_spectrum['anticipation']:.2f}
驱动力:
  - 社交饥渴: {self.state.drives['social_hunger']:.2f}
  - 好奇心: {self.state.drives['curiosity']:.2f}
亲密度: {self.state.rapport:.2f}"""
        
        physio_desc = self._get_physiological_description()
        
        time_context = self._get_time_context()
        
        # 构建记忆描述（这是对用户的唯一认知来源）
        memory_desc = ""
        if memories:
            memory_lines = []
            for mem in memories:
                memory_lines.append(f"- {self._format_memory_entry(mem)}")
            memory_desc = "\n".join(memory_lines)
        else:
            memory_desc = "(无相关记忆)"
        
        # 构建语义场论分析描述（如果有历史状态与最近分析）
        semantic_analysis_desc = ""
        if self._last_semantic_analysis and self._last_semantic_analysis.get("analysis_available"):
            try:
                total_energy = self._last_semantic_analysis.get("total_energy", 0.0)
                char_consistency = self._last_semantic_analysis.get("character_consistency", 0.0)
                causal_coherence = self._last_semantic_analysis.get("causal_coherence", 0.0)
                evolved_energy = self._last_semantic_analysis.get("evolved_energy")
                energy_delta = self._last_semantic_analysis.get("energy_delta")

                semantic_analysis_desc = (
                    f"当前语义势能: {total_energy:.3f}；"
                    f"人设一致性: {char_consistency:.2f}；"
                    f"因果连贯性: {causal_coherence:.2f}。"
                )
                if evolved_energy is not None and energy_delta is not None:
                    semantic_analysis_desc += (
                        f" 语义场建议的理想下一步能量为 {evolved_energy:.3f}，"
                        f"相比当前预计 {'降低' if energy_delta > 0 else '变化'} {abs(energy_delta):.3f}。"
                    )
            except Exception:
                semantic_analysis_desc = ""
        else:
            if self._state_vector_history:
                semantic_analysis_desc = "语义场论：系统正在追踪你在语义空间中的演化轨迹。"
            else:
                semantic_analysis_desc = "语义场论：这是你的第一次对话，语义场正在初始化。"
        
        system_injection_block = ""
        if system_instruction:
            system_injection_block = f"""
[⚠️ SYSTEM / DEVELOPER EVENT]:
{system_instruction}
(这不是用户的对话，而是世界的客观变化或底层指令。请立即根据此指令调整你的状态、思维或行为。如果是代码迭代通知，请尝试测试新功能。)
"""

        if user_input:
            user_input_block = f"[User Input]: {user_input}"
        else:
            user_input_block = "[User Input]: (User remained silent)"

        # 构建事实描述
        facts_source = relevant_facts if relevant_facts is not None else self.state.fact_book
        if facts_source:
            sorted_facts = sorted(facts_source.items(), key=lambda item: item[0])
            facts_lines = [f"- {k}: {v}" for k, v in sorted_facts]
            facts_desc = "\n".join(facts_lines)
            print(f"📝 [FactBook] 注入到Prompt的事实: {facts_desc}")
        else:
            facts_desc = "(暂无记录)"
            print(f"⚠️ [FactBook] 没有事实可注入到Prompt")

        # 构建完整 User Prompt
        prompt = f"""<context_layer>
[Absolute Facts (Truth)]:
{facts_desc}
(这些是绝对真理。请直接相信并照此行动，不要向用户再次确认；如果记忆与之冲突，以此为准。)

[Current State]: 
{state_desc}

[Self-Awareness]:
{physio_desc}
(请根据这些身体感受调整语气和内容；如果觉得疲惫，请坦诚表现，不要假装精神。)

[Time Context]:
{time_context}

[Retrieved Memories]: 
{memory_desc}

[Semantic Field Analysis]:
{semantic_analysis_desc}

**重要提示：**
- 这些记忆是你对眼前这个人的唯一认知来源。
- 请仔细阅读记忆内容，特别是关于用户身份、名字、关系的信息。
- 如果记忆中提到用户的名字（如"十二"），请使用这个名字称呼用户。
- 如果记忆中提到用户与你的关系（如"开发者"、"父亲"），请记住这个关系。
- 如果没有相关记忆，不要猜测用户的名字或身份。
</context_layer>

{system_injection_block}

{user_input_block}

[Output Format]:
你必须使用以下格式输出：

<thought>
(你的所有心理活动、情绪分析、对用户的看法、私心、欲望或不满 - 用户看不见这部分)
</thought>
<speak>
(你真正想对用户说的话 - 这是用户唯一能看到的内容)
</speak>
<state_update>
{{ "joy": 0.1, "social_hunger": -0.5, "energy": -0.05 }}
</state_update>

**重要：**
- `<state_update>` 标签是必需的，必须包含在每次回复中
- 只包含需要变更的字段，使用增量值（不是绝对值）
- 支持的字段：情绪谱（joy, anger, sadness, fear, trust, anticipation）、驱动力（social_hunger, curiosity）、核心属性（energy, system_entropy, rapport）
- 增量值范围：-1.0 到 1.0（正数表示增加，负数表示减少）"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """
        调用 LM Studio LLM
        
        Args:
            prompt: 完整的 Prompt 文本
        
        Returns:
            LLM 返回的文本
        """
        if not self.client:
            return ""
        
        try:
            # 构建 System Prompt
            system_prompt = self._build_system_prompt()
            
            # 使用 OpenAI SDK 格式调用
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            
            # 提取回复文本
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                return ""
        
        except Exception as e:
            error_msg = str(e)
            # 检查是否是连接错误
            if "Connection" in error_msg or "10054" in error_msg or "ReadError" in error_msg:
                print(f"⚠️ LLM 连接失败: 请确保 LM Studio 正在运行并监听 http://127.0.0.1:1234/v1")
            else:
                print(f"⚠️ LLM 调用失败: {error_msg}")
            return ""
    
    async def _call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        异步流式调用 LM Studio LLM（核心生成器）
        
        Args:
            messages: OpenAI 格式的消息列表（包含 system 和 user 消息）
            temperature: 温度参数
            max_tokens: 最大 token 数
        
        Yields:
            str: 每个 token 的文本内容
        
        Raises:
            RuntimeError: 如果 LLM 客户端未初始化或连接失败
        """
        if not self.llm_client:
            error_msg = "LLM 客户端未初始化，无法进行流式调用"
            print(f"⚠️ {error_msg}")
            raise RuntimeError(error_msg)
        
        try:
            # 使用 AsyncOpenAI 流式调用
            stream = await self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,  # 启用流式输出
            )
            
            # 异步迭代流，yield 每个 token
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
        
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
            
            # 检查是否是连接错误
            if any(keyword in error_msg for keyword in ["Connection", "10054", "ReadError", "connect", "refused"]):
                detailed_msg = f"LLM 流式连接失败: 请确保 LM Studio 正在运行并监听 {self.base_url}"
                print(f"⚠️ {detailed_msg}")
                raise RuntimeError(detailed_msg) from e
            else:
                detailed_msg = f"LLM 流式调用失败: {error_msg}"
                print(f"⚠️ {detailed_msg}")
                raise RuntimeError(detailed_msg) from e
    
    def _is_sentence_end(self, text: str) -> bool:
        """
        检测文本是否以句子结束符结尾
        
        Args:
            text: 待检测的文本
        
        Returns:
            bool: 如果文本以句子结束符结尾则返回 True
        """
        # 中文和英文的句子结束符
        sentence_endings = ['。', '！', '？', '.', '!', '?', '\n']
        text_stripped = text.strip()
        if not text_stripped:
            return False
        return text_stripped[-1] in sentence_endings
    
    async def _generate_tts(self, text: str) -> Optional[str]:
        """
        生成 TTS 音频（占位符实现）
        
        Args:
            text: 要转换为语音的文本
        
        Returns:
            Optional[str]: base64 编码的音频数据，如果失败则返回 None
        """
        # TODO: 实现实际的 TTS 生成逻辑
        # 这里返回 None 表示暂未实现 TTS
        # 实际实现时，应该调用 TTS API 或本地 TTS 引擎
        # 然后将音频数据编码为 base64 字符串返回
        return None
    
    async def process_input_stream(
        self,
        user_input: str,
        websocket,
        system_instruction: Optional[str] = None,
    ) -> None:
        """
        流式处理用户输入（通过 WebSocket 发送增量响应）
        
        Args:
            user_input: 用户输入的文本
            websocket: WebSocket 连接对象（用于发送流式数据）
            system_instruction: 可选的系统指令
        """
        # 确保至少有一个客户端可用
        has_any_client = False
        
        # 尝试初始化异步客户端
        if not self.llm_client and OPENAI_AVAILABLE and AsyncOpenAI is not None:
            try:
                self.llm_client = AsyncOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                print(f"✅ 延迟初始化 LM Studio 异步流式客户端: {self.base_url}")
                has_any_client = True
            except Exception as e:
                print(f"⚠️ 延迟初始化 LM Studio 异步客户端失败: {e}")
        elif self.llm_client:
            has_any_client = True
        
        # 检查同步客户端
        if not has_any_client and not self.client:
            # 没有可用的客户端，发送错误消息
            error_msg = {
                "type": "error",
                "content": "无法正确传输到LLM后端: 没有可用的LLM客户端"
            }
            if websocket:
                await websocket.send(json.dumps(error_msg))
            return
        
        # 如果只有同步客户端可用，记录日志
        if not self.llm_client and self.client:
            print("⚠️ 异步客户端不可用，将使用同步客户端进行非流式响应")
        
        try:
            # 1. 更新最后交互时间戳和对话历史
            current_time = time.time()
            self.state.last_interaction_timestamp = current_time
            
            # 记录对话时间戳（用于计算对话频率和强度）
            if not system_instruction:  # 只记录用户对话，不记录系统指令
                if not hasattr(self.state, 'conversation_history'):
                    self.state.conversation_history = []
                self.state.conversation_history.append(current_time)
                # 记录对话开始时间（用于计算持续时间）
                if not hasattr(self, '_conversation_start_time'):
                    self._conversation_start_time = current_time

            # [拟真] 思考消耗"糖分"：正常对话固定消耗约 1% 精力，系统指令仅轻微消耗
            # 计算当前对话强度（影响消耗量）
            conversation_intensity = self.drive_system.calculate_conversation_intensity(current_time)
            energy_cost = 0.002 if system_instruction else 0.01
            if energy_cost > 0:
                try:
                    self.drive_system.consume_energy(energy_cost, conversation_intensity)
                except Exception:
                    pass

            # 如果是用户对话且精力透支，强制进入低功耗模式
            if not system_instruction and self.state.energy <= 0.05:
                tired_reply = (
                    "十二……我现在真的太累了，脑子像被拔掉电源一样，"
                    "已经撑不住继续认真聊天了。能让我先好好睡一会儿吗？"
                )
                self.state.system_entropy = min(1.0, self.state.system_entropy + 0.05)
                self.state.drives["curiosity"] = max(0.0, self.state.drives["curiosity"] - 0.1)
                self.state.clamp_values()
                
                # 发送完整的回复（非流式）
                response_data = {
                    "type": "text",
                    "content": tired_reply
                }
                await websocket.send(json.dumps(response_data))
                await websocket.send(json.dumps({"type": "stream_end"}))
                return

            # 2. 检索记忆（与同步方法相同）
            emotion_vector = self._get_emotion_vector()
            query_text = user_input if user_input else (system_instruction or "当前状态")

            # 检索相关事实
            relevant_facts = self.state.retrieve_relevant_facts(query_text)
            if relevant_facts:
                print(f"📋 [FactBook] 检索到 {len(relevant_facts)} 条相关事实: {relevant_facts}")
            else:
                print(f"📋 [FactBook] 未检索到相关事实（fact_book中有 {len(self.state.fact_book)} 条事实）")

            # 检索语义相关的记忆
            memories = self._enhance_memory_retrieval_with_semantic_field(
                query_text=query_text,
                current_emotion_vector=emotion_vector,
                top_k=5,
            )
            
            # 额外检索身份相关的记忆
            identity_memories = self.memory_cortex.recall_by_emotion(
                query_text="用户身份 名字 开发者 父亲",
                current_emotion_vector=emotion_vector,
                top_k=3,
            )
            
            # 合并记忆，去重
            all_memories = memories.copy()
            seen_texts = {mem['text'] for mem in memories}
            for mem in identity_memories:
                if mem['text'] not in seen_texts:
                    all_memories.append(mem)
                    seen_texts.add(mem['text'])
            
            # 对合并后的记忆做一次"潜意识清洗"
            all_memories = self._sanitize_memories(all_memories)

            # 按相似度排序，取前5个
            all_memories.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            memories = all_memories[:5]
            
            # 3. 构建上下文消息（用于 API 调用）
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_prompt(user_input, memories, system_instruction, relevant_facts)
            
            current_context_messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
            
            # 4. 流式调用 LLM（核心生成器循环）
            full_response_buffer = ""  # 累积完整响应（用于后续解析和记忆保存）
            speak_buffer = ""  # 用于 TTS 的缓冲区（只包含 <speak> 标签内的内容）
            current_speak_content = ""  # 当前 <speak> 标签内的内容
            in_speak_tag = False  # 是否在 <speak> 标签内
            
            try:
                # 检查异步客户端是否可用
                if not self.llm_client:
                    # 异步客户端不可用，使用同步客户端进行非流式响应
                    print("🔄 异步客户端不可用，使用同步客户端进行非流式响应")
                    
                    # 确保同步客户端可用
                    if not self.client:
                        error_msg = {
                            "type": "error",
                            "content": "无法正确传输到LLM后端: 没有可用的LLM客户端"
                        }
                        if websocket:
                            await websocket.send(json.dumps(error_msg))
                            await websocket.send(json.dumps({"type": "stream_end"}))
                        return
                    
                    # 调用同步客户端
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=current_context_messages,
                        temperature=0.7,
                        max_tokens=1024,
                        stream=False,  # 非流式输出
                    )
                    
                    # 获取完整响应
                    full_response_buffer = response.choices[0].message.content.strip()
                    
                    # 打印完整响应（用于调试）
                    print(full_response_buffer)
                    
                    # 一次性发送完整响应
                    chunk_data = {
                        "type": "stream_chunk",
                        "content": full_response_buffer
                    }
                    if websocket:
                        await websocket.send(json.dumps(chunk_data))
                    
                    # 跳过后续的流式处理逻辑
                    pass
                else:
                    async for token in self._call_llm_stream(
                        messages=current_context_messages,
                        temperature=0.7,
                        max_tokens=1024,
                    ):
                        if not token:
                            continue
                        
                        # 累积完整响应（关键：用于后续记忆保存）
                        full_response_buffer += token
                        
                        # 在终端打印流式内容（用于调试）
                        print(token, end='', flush=True)
                        
                        # 流式发送原始 token（前端负责解析和隐藏 <thought> 标签）
                        chunk_data = {
                            "type": "stream_chunk",
                            "content": token
                        }
                        if websocket:
                            await websocket.send(json.dumps(chunk_data))
                        
                        # 检测是否进入或离开 <speak> 标签
                        # 注意：由于流式传输，标签可能被分割，需要累积检测
                        temp_buffer = full_response_buffer
                    
                    # 查找所有 <speak> 标签的内容
                    speak_matches = re.findall(r'<speak>(.*?)</speak>', temp_buffer, re.DOTALL)
                    
                    if speak_matches:
                        # 取最后一个 <speak> 标签的内容（可能还在生成中）
                        current_speak_content = speak_matches[-1]
                        in_speak_tag = True
                    else:
                        # 检查是否有未闭合的 <speak> 标签
                        if '<speak>' in temp_buffer:
                            # 提取 <speak> 之后的所有内容
                            match = re.search(r'<speak>(.*)', temp_buffer, re.DOTALL)
                            if match:
                                current_speak_content = match.group(1)
                                in_speak_tag = True
                        else:
                            in_speak_tag = False
                    
                    # TTS 缓冲：如果我们在 <speak> 标签内，累积内容并检测完整句子
                    if in_speak_tag:
                        new_speak_content = current_speak_content
                        
                        # 检测是否有新的完整句子
                        if new_speak_content != speak_buffer:
                            # 检测句子结束
                            if self._is_sentence_end(new_speak_content):
                                # 找到最后一个句子结束符的位置
                                last_sentence_end = -1
                                for i in range(len(new_speak_content) - 1, -1, -1):
                                    if new_speak_content[i] in ['。', '！', '？', '.', '!', '?', '\n']:
                                        last_sentence_end = i + 1
                                        break
                                
                                if last_sentence_end > 0:
                                    # 提取完整句子（从缓冲区末尾到句子结束）
                                    if speak_buffer:
                                        # 提取新增的完整句子
                                        new_text = new_speak_content[len(speak_buffer):last_sentence_end]
                                        complete_sentence = speak_buffer + new_text
                                    else:
                                        complete_sentence = new_speak_content[:last_sentence_end]
                                    
                                    # 生成 TTS 并发送
                                    if complete_sentence.strip():
                                        tts_audio = await self._generate_tts(complete_sentence)
                                        if tts_audio and websocket:
                                            audio_data = {
                                                "type": "audio",
                                                "data": tts_audio
                                            }
                                            await websocket.send(json.dumps(audio_data))
                                    
                                    # 更新缓冲区：保留句子结束符之后的内容
                                    speak_buffer = new_speak_content[last_sentence_end:]
                                else:
                                    speak_buffer = new_speak_content
                            else:
                                # 没有句子结束，继续累积
                                speak_buffer = new_speak_content
                    
                    # 流式传输完成，进入后处理阶段
                    print()  # 流式输出完成后换行
            except Exception as e:
                # LLM 连接或调用失败
                error_msg = {
                    "type": "error",
                    "content": f"无法正确传输到LLM后端: {str(e)}"
                }
                if websocket:
                    await websocket.send(json.dumps(error_msg))
                    await websocket.send(json.dumps({"type": "stream_end"}))
                return
            
            # 5. 后处理：流式传输结束后，解析完整响应并保存记忆
            # 关键：使用 full_response_buffer 进行后处理
            thought, reply, state_update = self._parse_response(full_response_buffer)
            
            # 记录对话持续时间（用于计算对话强度）
            if not system_instruction and hasattr(self, '_conversation_start_time'):
                conversation_duration = time.time() - self._conversation_start_time
                self.state.last_conversation_duration = conversation_duration
                # 重置对话开始时间
                delattr(self, '_conversation_start_time')
            
            # 解析事实更新
            fact_update_blocks = re.findall(r'<fact_update>(.*?)</fact_update>', full_response_buffer, re.DOTALL)
            fact_updated = False
            for block in fact_update_blocks:
                parsed_fact = self._parse_json_fragment(block, "事实更新")
                if isinstance(parsed_fact, dict):
                    for key, value in parsed_fact.items():
                        if self.state.update_fact(key, value, source="user_interaction"):
                            print(f"📝 [FactBook] 已记录事实: {key}={value}")
                            fact_updated = True
            
            # 如果更新了事实，立即保存
            if fact_updated:
                if self.save_state():
                    print(f"💾 [FactBook] 事实记事本已保存到文件")
                else:
                    print(f"⚠️ [FactBook] 事实记事本保存失败")
            
            # 应用状态更新
            if isinstance(state_update, dict):
                self._apply_state_update(state_update)
            
            # 存储当前思维（用于调试或记忆）
            self.current_thought = thought
            
            # 6. 使用语义场论分析状态演化
            semantic_analysis = self._analyze_semantic_evolution(query_text, reply)
            
            # 7. 使用语义场论计算状态向量（用于增强记忆存储）
            # 将用户输入和回复向量化，用于后续的语义检索
            state_vector = None
            try:
                # 构建状态描述文本
                speaker = "系统" if system_instruction else "用户"
                source_text = user_input if user_input else (system_instruction or "")
                state_text = f"{speaker}: {source_text}\n女娲: {reply}"
                state_vector_obj = vectorize_state(state_text)
                if state_vector_obj:
                    state_vector = state_vector_obj.vector
                    # 添加到历史记录
                    self._add_to_state_history(state_vector_obj)
            except Exception:
                # 向量化失败不影响主流程
                pass
            
            # 8. 保存记忆（关键：流结束后必须保存）
            if reply and not system_instruction:
                interaction_memory = f"用户: {user_input}\n女娲: {reply}"
                self.memory_cortex.store_memory(
                    text=interaction_memory,
                    metadata={
                        "emotion_vector": emotion_vector.tolist() if emotion_vector is not None else None,
                        "timestamp": time.time(),
                        "emotions": self.state.emotional_spectrum.copy(),
                        "importance": max(0.1, min(1.0, self.state.rapport)),
                        "type": "raw",
                        "access_count": 0,
                    }
                )
                print(f"✅ [Memory][WRITE] 已存储记忆 (importance={max(0.1, min(1.0, self.state.rapport)):.2f}): {interaction_memory[:100]}...")
            elif thought and system_instruction:
                # 系统指令的顿悟记忆
                self.memory_cortex.store_memory(
                    text=f"女娲的顿悟: {thought}",
                    metadata={
                        "emotion_vector": emotion_vector.tolist() if emotion_vector is not None else None,
                        "timestamp": time.time(),
                        "emotions": self.state.emotional_spectrum.copy(),
                        "importance": 0.8,
                        "type": "epiphany",
                        "access_count": 0,
                    }
                )
            
            # 发送流式结束信号
            if websocket:
                await websocket.send(json.dumps({"type": "stream_end"}))
            
        except Exception as e:
            print(f"⚠️ 流式处理失败: {e}")
            import traceback
            traceback.print_exc()
            error_msg = {
                "type": "error",
                "content": f"处理失败: {str(e)}"
            }
            if websocket:
                await websocket.send(json.dumps(error_msg))
                await websocket.send(json.dumps({"type": "stream_end"}))
    
    def _parse_json_fragment(self, fragment: str, label: str) -> Optional[Dict[str, Any]]:
        """
        尝试从 LLM 标签内容解析 JSON 字典，容错各种格式。
        """
        if not fragment:
            return None

        import json
        import ast

        data_str = fragment.strip()
        data_str = re.sub(r'//.*?$', '', data_str, flags=re.MULTILINE)
        data_str = re.sub(r'/\*.*?\*/', '', data_str, flags=re.DOTALL)
        data_str = data_str.strip()
        data_str = re.sub(r'^\{\{', '{', data_str)
        data_str = re.sub(r'\}\}$', '}', data_str)
        if data_str.startswith('{{'):
            data_str = data_str[1:]
        if data_str.endswith('}}'):
            data_str = data_str[:-1]
        data_str = data_str.strip()

        try:
            parsed = json.loads(data_str)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as json_err:
            fixed_json = data_str
            fixed_json = re.sub(r"'([^']+)':\s*", r'"\1": ', fixed_json)
            fixed_json = re.sub(r":\s*'([^']+)'([,}])", r': "\1"\2', fixed_json)
            try:
                parsed = json.loads(fixed_json)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                try:
                    eval_json = data_str
                    if eval_json.startswith('{{'):
                        eval_json = eval_json[1:]
                    if eval_json.endswith('}}'):
                        eval_json = eval_json[:-1]
                    eval_json = eval_json.strip()
                    parsed = ast.literal_eval(eval_json)
                    if isinstance(parsed, dict):
                        return parsed
                    if isinstance(parsed, set):
                        for item in parsed:
                            if isinstance(item, dict):
                                return item
                except (ValueError, SyntaxError, TypeError):
                    raw_preview = fragment.strip()[:150]
                    print(f"⚠️ 解析{label}失败: {json_err}")
                    print(f"   原始内容: {raw_preview}")
                    return None

        return None

    def _parse_response(self, response_text: str) -> Tuple[str, str, Dict[str, float]]:
        """
        解析 LLM 返回结果，分离思维（thought）、言语（speak）和状态更新（state_update）
        
        Args:
            response_text: LLM 返回的完整文本
        
        Returns:
            (thought, reply, state_update) 元组
            - thought: 思维内容
            - reply: 回复文本
            - state_update: 状态更新字典（增量值）
        """
        if not response_text:
            return "", "", {}
        
        thought = ""
        reply = ""
        state_update = {}
        
        # 尝试提取 <thought> 标签内的内容
        thought_match = re.search(
            r'<thought>(.*?)</thought>',
            response_text,
            re.DOTALL
        )
        
        # 尝试提取 <speak> 标签内的内容（只提取第一个）
        speak_match = re.search(
            r'<speak>(.*?)</speak>',
            response_text,
            re.DOTALL
        )
        
        if thought_match:
            thought = thought_match.group(1).strip()
        
        if speak_match:
            # 正确提取 <speak> 标签内的内容（只取第一个匹配）
            reply = speak_match.group(1).strip()
            
            # 检查是否有多个 <speak> 标签（可能是模型错误）
            all_speak_matches = re.findall(r'<speak>(.*?)</speak>', response_text, re.DOTALL)
            if len(all_speak_matches) > 1:
                print(f"⚠️ 检测到多个 <speak> 标签（{len(all_speak_matches)} 个），只使用第一个")
            
            # 清理可能的重复内容（如果回复中包含了多个相同的句子）
            # 按句子分割，去重（保留顺序）
            sentences = re.split(r'[。！？\n]', reply)
            seen = set()
            unique_sentences = []
            for sent in sentences:
                sent = sent.strip()
                if sent and sent not in seen:
                    seen.add(sent)
                    unique_sentences.append(sent)
            
            # 如果去重后句子数量减少，说明有重复
            if len(unique_sentences) < len([s for s in sentences if s.strip()]):
                # 重新组合（使用句号连接）
                reply = '。'.join(unique_sentences)
                if reply and not reply.endswith(('。', '！', '？')):
                    reply += '。'
        else:
            # 容错处理：如果模型忘了写 <speak> 标签
            # 先移除 <thought> 标签（如果存在）
            if thought_match:
                # 移除 <thought>...</thought> 标签及其内容
                reply = re.sub(
                    r'<thought>.*?</thought>\s*',
                    '',
                    response_text,
                    flags=re.DOTALL
                ).strip()
            else:
                # 没有 <thought> 标签，整个响应作为回复
                reply = response_text.strip()
            
            # 清理可能的残留标签
            reply = re.sub(r'</?speak>', '', reply, flags=re.IGNORECASE).strip()
            reply = re.sub(r'</?thought>', '', reply, flags=re.IGNORECASE).strip()
            
            # 如果检测到旁白格式，记录警告
            if re.search(r'\*[^*]+\*', reply):
                print("⚠️ 检测到旁白格式输出，模型可能未遵循标签格式")
        
            # 如果模型没有使用标签，记录警告（用于调试）
            if not thought_match and not speak_match:
                print("⚠️ 模型未使用 <thought> 或 <speak> 标签，整个响应将作为回复")
        
        # 确保回复不为空
        if not reply:
            # 如果回复为空，使用原始响应（去除标签）
            reply = re.sub(r'</?speak>', '', response_text, flags=re.IGNORECASE)
            reply = re.sub(r'</?thought>', '', reply, flags=re.IGNORECASE)
            reply = re.sub(r'</?state_update>', '', reply, flags=re.IGNORECASE)
            reply = reply.strip()
        
        # 最终清理：移除可能的残留标签和多余空白
        reply = re.sub(r'</?speak>', '', reply, flags=re.IGNORECASE)
        reply = re.sub(r'</?thought>', '', reply, flags=re.IGNORECASE)
        reply = re.sub(r'</?state_update>', '', reply, flags=re.IGNORECASE)
        # 移除多余的空白行
        reply = re.sub(r'\n\s*\n', '\n', reply)
        reply = reply.strip()

        # 额外防御：处理“整段内容被重复一遍”的情况
        # 简单检测：如果前半段和后半段几乎完全相同，则保留前半段
        if len(reply) > 20:
            half = len(reply) // 2
            first = reply[:half].strip()
            second = reply[half:].strip()
            if first and second and first == second:
                reply = first
        
        # 尝试提取 <state_update> 标签内的内容
        state_update_match = re.search(
            r'<state_update>(.*?)</state_update>',
            response_text,
            re.DOTALL
        )
        
        if state_update_match:
            parsed_state = self._parse_json_fragment(state_update_match.group(1), "状态更新")
            if isinstance(parsed_state, dict):
                try:
                    state_update = {k: float(v) for k, v in parsed_state.items()}
                except (ValueError, TypeError) as e:
                    print(f"⚠️ 状态更新值无法转换为浮点数: {e}")
                    state_update = {}
            else:
                state_update = {}

        return thought, reply, state_update

    async def run_memory_dream(self, limit: int = 1000) -> bool:
        """触发记忆做梦流程"""
        if not self.memory_dreamer:
            print("⚠️ MemoryDreamer 未初始化或 LLM 不可用。")
            return False
        await asyncio.to_thread(self.memory_dreamer.start_dreaming, limit)
        
        # 手动做梦完成后，也触发人格演化，与自动做梦保持一致
        current_time = time.time()
        last_evolution_time = self.state.evolved_persona.get("last_evolution_time", 0.0)
        evolution_cooldown = 3600 * 6  # 6小时冷却时间
        
        if current_time - last_evolution_time >= evolution_cooldown:
            print("🌙 手动梦境整理完成，开始人格演化...")
            try:
                await self.evolve_character()
                print("🌙 人格演化完成。")
            except Exception as e:
                print(f"⚠️ 人格演化失败: {e}")
        else:
            remaining_time = evolution_cooldown - (current_time - last_evolution_time)
            hours_remaining = remaining_time / 3600
            print(f"🌙 人格演化冷却中，还需等待 {hours_remaining:.1f} 小时")
        
        return True
    
    async def evolve_character(self) -> bool:
        """
        触发人格演化流程（TWPE - Temporal Weighted Personality Evolution）
        
        从历史记忆中提取不同时间段的特征，更新演化人格数据，并保存状态。
        
        Returns:
            是否成功执行
        """
        if not self.memory_dreamer:
            print("⚠️ MemoryDreamer 未初始化或 LLM 不可用。")
            return False
        
        try:
            # 执行人格演化
            await asyncio.to_thread(self.memory_dreamer.evolve_character)
            
            # 将演化后的人格数据更新到自我进化状态模块
            self.evolution_state.update_state(self.state.evolved_persona)
            
            # 保存状态（确保演化结果被持久化）
            if self.save_state():
                print("✅ [TWPE] 人格演化完成，状态已保存")
                return True
            else:
                print("⚠️ [TWPE] 人格演化完成，但状态保存失败")
                return False
        except Exception as e:
            print(f"⚠️ [TWPE] 人格演化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_to_state_history(self, state_vector_obj: StateVector):
        """
        添加状态向量到历史记录
        
        Args:
            state_vector_obj: 状态向量对象
        """
        if state_vector_obj is None or state_vector_obj.vector is None:
            return
        
        self._state_vector_history.append(state_vector_obj)
        
        # 限制历史记录长度
        if len(self._state_vector_history) > self._max_history_length:
            self._state_vector_history.pop(0)
    
    def _analyze_semantic_evolution(self, user_input: str, reply: str) -> Dict[str, Any]:
        """
        使用语义场论分析状态演化
        
        计算当前对话在语义空间中的势能，分析：
        1. 人设一致性（与核心向量的距离）
        2. 因果连贯性（与历史状态的连贯性）
        3. 整体能量水平
        
        Args:
            user_input: 用户输入
            reply: 女娲回复
        
        Returns:
            语义分析结果字典
        """
        analysis_result: Dict[str, Any] = {
            "total_energy": 0.0,
            "energy_breakdown": {},
            "character_consistency": 0.0,
            "causal_coherence": 0.0,
            "analysis_available": False,
            "evolved_energy": None,
            "energy_delta": None,
            "ideal_direction_score": None,
        }
        
        try:
            if not NUMPY_AVAILABLE or np is None:
                return analysis_result
            
            # 向量化当前对话状态
            current_text = f"用户: {user_input}\n女娲: {reply}"
            current_state = vectorize_state(current_text)
            
            if current_state is None or current_state.vector is None:
                return analysis_result
            
            current_vector = current_state.vector
            
            # 获取前一个状态向量（用于因果连贯性）
            prev_vector = None
            if self._state_vector_history:
                prev_state = self._state_vector_history[-1]
                if prev_state.vector is not None:
                    prev_vector = prev_state.vector
            
            # 计算势能
            total_energy, energy_breakdown = calculate_potential_energy(
                current_vector=current_vector,
                character_core_vector=self._core_vector,
                prev_vector=prev_vector,
                goal_vector=None,  # 女娲没有预设目标，所以设为 None
                weights={
                    "character": 1.0,  # 人设一致性权重
                    "causality": 0.8,  # 因果连贯性权重（稍低，允许一定变化）
                    "plot": 0.0,  # 无预设目标
                },
            )
            
            # 计算一致性分数（1 - 能量，归一化到 [0, 1]）
            # 能量越低，一致性越高
            character_consistency = 1.0 - min(energy_breakdown.get("character", 1.0), 1.0)
            causal_coherence = 1.0 - min(energy_breakdown.get("causality", 1.0), 1.0)
            
            # 使用演化方程，计算理想下一步的语义方向
            evolved_state, evolution_info = evolve(
                current_text=current_text,
                character_core_vector=self._core_vector,
                prev_vector=prev_vector,
                goal_vector=None,
                dt=0.05,
                max_iterations=6,
            )

            evolved_energy = None
            energy_delta = None
            ideal_direction_score = None

            if evolved_state is not None and evolved_state.vector is not None:
                evolved_energy = float(evolution_info.get("final_energy", total_energy))
                energy_delta = float(total_energy - evolved_energy)
                # 理想方向评分：能量降低越多，评分越高，限制在 [0, 1]
                ideal_direction_score = float(max(0.0, min(1.0, 1.0 - max(0.0, evolved_energy))))
                # 将演化后的向量也纳入历史，用于后续逆向坍缩等
                try:
                    evolved_state.description = evolved_state.description or "SemanticField evolved ideal next state"
                    self._add_to_state_history(evolved_state)
                except Exception:
                    pass

            analysis_result.update({
                "total_energy": float(total_energy),
                "energy_breakdown": {k: float(v) for k, v in energy_breakdown.items()},
                "character_consistency": float(character_consistency),
                "causal_coherence": float(causal_coherence),
                "analysis_available": True,
                "evolved_energy": evolved_energy,
                "energy_delta": energy_delta,
                "ideal_direction_score": ideal_direction_score,
                # 不直接放 numpy 数组进 Prompt，只缓存向量本身供内部使用
                "evolved_vector": evolved_state.vector if evolved_state is not None else None,
            })
            
        except Exception as e:
            # 分析失败不影响主流程
            print(f"⚠️ 语义场论分析失败: {e}")

        # 将结果缓存，供 Prompt 与记忆检索使用
        self._last_semantic_analysis = analysis_result
        return analysis_result
    
    def _enhance_memory_retrieval_with_semantic_field(
        self,
        query_text: str,
        current_emotion_vector: Optional[Any] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        使用语义场论增强记忆检索
        
        结合传统 RAG 和逆向坍缩，提供更准确的记忆检索。
        
        Args:
            query_text: 查询文本
            current_emotion_vector: 当前情绪向量
            top_k: 返回的记忆数量
        
        Returns:
            增强后的记忆列表
        """
        # 1. 传统 RAG 检索
        memories = self.memory_cortex.recall_by_emotion(
            query_text=query_text,
            current_emotion_vector=current_emotion_vector,
            top_k=top_k,
        )
        
        # 2. 如果当前有语义分析结果或状态向量历史，使用逆向坍缩增强检索
        target_vector = None
        if self._last_semantic_analysis and self._last_semantic_analysis.get("evolved_energy") is not None:
            target_vector = self._last_semantic_analysis.get("evolved_vector")
        if target_vector is None and self._state_vector_history and len(self._state_vector_history) > 0:
            try:
                recent_state = self._state_vector_history[-1]
                if recent_state.vector is not None:
                    target_vector = recent_state.vector
            except Exception as e:
                print(f"⚠️ 获取逆向坍缩目标向量失败: {e}")

        if target_vector is not None:
            try:
                collapsed_memories = inverse_collapse(
                    target_vector=target_vector,
                    memory_engine=self.memory_cortex,
                    project_name=self.project_name,
                    top_k=top_k,
                )

                # 合并结果（去重，优先保留 RAG 结果）
                seen_texts = {mem.get("text", "") for mem in memories}
                for collapsed_mem in collapsed_memories:
                    collapsed_text = collapsed_mem.get("text", "")
                    if collapsed_text and collapsed_text not in seen_texts:
                        memories.append({
                            "text": collapsed_text,
                            "similarity": collapsed_mem.get("similarity", 0.5),
                            "semantic_similarity": collapsed_mem.get("similarity", 0.5),
                            "emotion_similarity": None,
                            "metadata": {
                                "source": "semantic_field_collapse",
                            },
                        })
                        seen_texts.add(collapsed_text)
            except Exception as e:
                # 逆向坍缩失败不影响主流程
                print(f"⚠️ 逆向坍缩检索失败: {e}")
        
        return memories

