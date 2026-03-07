"""
多模态集成模块 (Multi-Modal Integration)

功能：将多模态处理器集成到女娲内核中

核心功能：
- MultimodalKernel: 支持多模态的内核扩展
- 集成语音、图像处理到对话流程
- 统一的多模态对话接口
"""

import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime

from .config_manager import NuwaConfig, DependencyContainer
from .kernel_di import KernelDI
from .multimodal_processor import MultiModalProcessor, get_multimodal_processor
from .memory_cortex import MemoryCortex


class MultimodalKernel(KernelDI):
    """
    多模态女娲内核
    
    在DI内核基础上扩展多模态能力
    """
    
    def __init__(
        self,
        config: Optional[NuwaConfig] = None,
        container: Optional[DependencyContainer] = None,
        state_manager=None,
        memory_cortex=None,
        drive_system=None,
        llm_client=None,
        on_message_callback=None,
        # 多模态配置
        multimodal_enabled: bool = True,
        whisper_model: str = "openai/whisper-small",
        clip_model: str = "openai/clip-vit-base-patch32",
        vits_model: str = "facebook/mms-tts-chinese",
    ):
        # 多模态配置
        self.multimodal_enabled = multimodal_enabled
        self.whisper_model = whisper_model
        self.clip_model = clip_model
        self.vits_model = vits_model
        
        # 多模态处理器（延迟初始化）
        self._multimodal_processor: Optional[MultiModalProcessor] = None
        
        # 调用父类初始化
        super().__init__(
            config=config,
            container=container,
            state_manager=state_manager,
            memory_cortex=memory_cortex,
            drive_system=drive_system,
            llm_client=llm_client,
            on_message_callback=on_message_callback,
        )
        
        # 注册到容器
        if self.container:
            self.container.register("multimodal_kernel", self)
        
        print("✅ MultimodalKernel 初始化完成")
    
    def _init_multimodal_processor(self):
        """初始化多模态处理器"""
        if not self.multimodal_enabled:
            print("⚠️ 多模态功能已禁用")
            return
        
        print("=" * 60)
        print("🎤 初始化多模态处理器")
        print("=" * 60)
        
        self._multimodal_processor = get_multimodal_processor(
            whisper_model=self.whisper_model,
            clip_model=self.clip_model,
            vits_model=self.vits_model,
        )
        
        # 检查可用性
        status = self._multimodal_processor.get_status()
        available = sum(status.values())
        total = len(status)
        
        print(f"✅ 多模态处理器就绪: {available}/{total}")
        print("=" * 60)
    
    @property
    def multimodal_processor(self) -> Optional[MultiModalProcessor]:
        """获取多模态处理器（懒加载）"""
        if not self.multimodal_enabled:
            return None
        
        if self._multimodal_processor is None:
            self._init_multimodal_processor()
        
        return self._multimodal_processor
    
    def is_multimodal_available(self) -> bool:
        """检查多模态功能是否可用"""
        if not self.multimodal_enabled:
            return False
        
        processor = self.multimodal_processor
        if processor is None:
            return False
        
        return processor.is_available()
    
    async def process_audio_input(
        self,
        audio: bytes,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理音频输入（语音对话）
        
        Args:
            audio: 音频字节流
            system_instruction: 系统指令
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        if not self.is_multimodal_available():
            return {
                "error": "多模态功能不可用",
                "reply": "抱歉，语音处理功能暂时不可用。",
            }
        
        # 1. 语音识别
        print("🎤 正在识别语音...")
        transcribed_text = await self.multimodal_processor.process_audio(audio, **kwargs)
        
        if transcribed_text.startswith("⚠️"):
            return {
                "error": transcribed_text,
                "reply": "抱歉，语音识别失败。",
                "transcribed_text": transcribed_text,
            }
        
        print(f"✅ 识别结果: {transcribed_text}")
        
        # 2. 保存到记忆（带类型标记）
        await self._store_multimodal_memory(
            content=transcribed_text,
            memory_type="audio_input",
            metadata={"original_audio": True}
        )
        
        # 3. 文本处理
        text_result = await self.process_input(
            user_input=transcribed_text,
            system_instruction=system_instruction,
        )
        
        # 4. 语音合成（可选）
        if kwargs.get("enable_tts", True):
            audio_response = await self._synthesize_response(text_result['reply'])
            text_result['audio_response'] = audio_response
        
        # 5. 添加音频输入标记
        text_result['input_type'] = 'audio'
        text_result['transcribed_text'] = transcribed_text
        
        return text_result
    
    async def process_image_input(
        self,
        image: bytes,
        user_query: Optional[str] = None,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理图像输入（视觉对话）
        
        Args:
            image: 图像字节流
            user_query: 用户关于图像的问题（可选）
            system_instruction: 系统指令
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        if not self.is_multimodal_available():
            return {
                "error": "多模态功能不可用",
                "reply": "抱歉，图像处理功能暂时不可用。",
            }
        
        # 1. 图像理解
        print("🖼️ 正在理解图像...")
        image_desc = await self.multimodal_processor.process_image(image, **kwargs)
        
        if image_desc.startswith("⚠️"):
            return {
                "error": image_desc,
                "reply": "抱歉，图像理解失败。",
                "image_desc": image_desc,
            }
        
        print(f"✅ 图像描述: {image_desc}")
        
        # 2. 保存到记忆
        await self._store_multimodal_memory(
            content=f"[图像] {image_desc}",
            memory_type="image_input",
            metadata={"original_image": True}
        )
        
        # 3. 构建处理文本
        if user_query:
            # 用户有问题
            processing_text = f"用户描述了一张图片: {image_desc}\n用户的问题是: {user_query}"
        else:
            # 用户只发了图片
            processing_text = f"用户分享了一张图片: {image_desc}\n请描述这张图片或做出相关回应。"
        
        # 4. 文本处理
        text_result = await self.process_input(
            user_input=processing_text,
            system_instruction=system_instruction,
        )
        
        # 5. 添加图像输入标记
        text_result['input_type'] = 'image'
        text_result['image_description'] = image_desc
        
        return text_result
    
    async def process_multimodal_input(
        self,
        audio: Optional[bytes] = None,
        image: Optional[bytes] = None,
        text: Optional[str] = None,
        system_instruction: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理混合多模态输入
        
        Args:
            audio: 音频字节流
            image: 图像字节流
            text: 文本输入
            system_instruction: 系统指令
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        if not self.is_multimodal_available():
            return {
                "error": "多模态功能不可用",
                "reply": "抱歉，多模态处理功能暂时不可用。",
            }
        
        # 记录输入类型
        input_types = []
        combined_input = []
        
        # 处理音频
        if audio:
            audio_text = await self.multimodal_processor.process_audio(audio)
            if not audio_text.startswith("⚠️"):
                combined_input.append(f"[语音]: {audio_text}")
                input_types.append("audio")
                await self._store_multimodal_memory(
                    content=audio_text,
                    memory_type="audio_input",
                    metadata={"original_audio": True}
                )
        
        # 处理图像
        if image:
            image_desc = await self.multimodal_processor.process_image(image)
            if not image_desc.startswith("⚠️"):
                combined_input.append(f"[图像]: {image_desc}")
                input_types.append("image")
                await self._store_multimodal_memory(
                    content=f"[图像] {image_desc}",
                    memory_type="image_input",
                    metadata={"original_image": True}
                )
        
        # 处理文本
        if text:
            combined_input.append(f"[文本]: {text}")
            input_types.append("text")
        
        if not combined_input:
            return {
                "error": "无有效输入",
                "reply": "请提供语音、图像或文本输入。",
            }
        
        # 组合处理文本
        processing_text = "\n".join(combined_input)
        
        # 文本处理
        result = await self.process_input(
            user_input=processing_text,
            system_instruction=system_instruction,
        )
        
        # 添加多模态标记
        result['input_types'] = input_types
        result['combined_input'] = processing_text
        
        # 语音合成（可选）
        if kwargs.get("enable_tts", True) and "audio" in input_types:
            audio_response = await self._synthesize_response(result['reply'])
            result['audio_response'] = audio_response
        
        return result
    
    async def _store_multimodal_memory(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict] = None
    ):
        """存储多模态记忆"""
        if not hasattr(self, 'memory_cortex') or self.memory_cortex is None:
            return
        
        try:
            # 构建元数据
            full_metadata = {
                "type": memory_type,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # 存储记忆
            self.memory_cortex.store_memory(
                text=content,
                metadata=full_metadata
            )
            
            print(f"✅ 已存储 {memory_type} 记忆: {content[:50]}...")
            
        except Exception as e:
            print(f"⚠️ 存储记忆失败: {e}")
    
    async def _synthesize_response(self, text: str) -> Optional[bytes]:
        """合成语音响应"""
        if not self.is_multimodal_available():
            return None
        
        try:
            print("🎤 正在合成语音...")
            audio_bytes = await self.multimodal_processor.synthesize_speech(text)
            
            if isinstance(audio_bytes, bytes) and len(audio_bytes) > 0:
                print(f"✅ 语音合成完成: {len(audio_bytes)} 字节")
                return audio_bytes
            else:
                print("⚠️ 语音合成返回无效数据")
                return None
                
        except Exception as e:
            print(f"⚠️ 语音合成失败: {e}")
            return None
    
    async def voice_chat(
        self,
        audio: bytes,
        enable_tts: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        语音对话模式
        
        Args:
            audio: 音频输入
            enable_tts: 是否启用语音回复
            **kwargs: 额外参数
            
        Returns:
            包含音频回复的对话结果
        """
        return await self.process_audio_input(
            audio=audio,
            enable_tts=enable_tts,
            **kwargs
        )
    
    async def vision_chat(
        self,
        image: bytes,
        user_query: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        视觉对话模式
        
        Args:
            image: 图像输入
            user_query: 用户问题
            **kwargs: 额外参数
            
        Returns:
            视觉对话结果
        """
        return await self.process_image_input(
            image=image,
            user_query=user_query,
            **kwargs
        )
    
    def get_multimodal_status(self) -> Dict[str, Any]:
        """获取多模态状态"""
        status = {
            "multimodal_enabled": self.multimodal_enabled,
        }
        
        if self._multimodal_processor:
            status.update(self._multimodal_processor.get_status())
        else:
            status["speech_recognizer"] = False
            status["image_understander"] = False
            status["speech_synthesizer"] = False
        
        return status


# 工厂函数
def create_multimodal_kernel(
    config: Optional[NuwaConfig] = None,
    **kwargs
) -> MultimodalKernel:
    """创建多模态内核"""
    return MultimodalKernel(config=config, **kwargs)