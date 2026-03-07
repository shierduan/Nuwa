"""
多模态处理器模块 (Multi-Modal Processor)

功能：统一处理语音、图像等多模态输入输出

核心功能：
- MultiModalProcessor: 多模态统一处理器
- SpeechRecognizer: 语音识别（Whisper）
- ImageUnderstander: 图像理解（CLIP）
- TTSSynthesizer: 语音合成（VITS）
"""

import asyncio
import base64
import io
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from transformers import (
        WhisperProcessor, 
        WhisperForConditionalGeneration,
        CLIPProcessor, 
        CLIPModel,
        VitsTokenizer, 
        VitsModel,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    WhisperProcessor = None
    CLIPProcessor = None
    VitsTokenizer = None

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class BaseProcessor(ABC):
    """基类：模态处理器"""
    
    @abstractmethod
    async def process(self, input_data: Any, **kwargs) -> Any:
        """处理输入数据"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查处理器是否可用"""
        pass


class SpeechRecognizer(BaseProcessor):
    """
    语音识别处理器（Whisper）
    
    支持：
    - 音频文件/字节流识别
    - 多语言支持
    - 实时流式处理
    """
    
    def __init__(self, model_name: str = "openai/whisper-small"):
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._available = False
        self._load_model()
    
    def _load_model(self):
        """加载Whisper模型"""
        if not TRANSFORMERS_AVAILABLE:
            print("[WARN] transformers库不可用，语音识别功能受限")
            return
        
        try:
            print(f"🔄 正在加载Whisper模型: {self.model_name}")
            self.processor = WhisperProcessor.from_pretrained(self.model_name)
            self.model = WhisperForConditionalGeneration.from_pretrained(self.model_name)
            self._available = True
            print(f"[OK] Whisper模型加载完成: {self.model_name}")
        except Exception as e:
            print(f"[WARN] Whisper模型加载失败: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    async def process(self, audio_data: Union[bytes, str], **kwargs) -> str:
        """
        处理音频数据
        
        Args:
            audio_data: 音频字节流或文件路径
            **kwargs: 额外参数（sampling_rate, language等）
            
        Returns:
            识别文本
        """
        if not self.is_available():
            return "[WARN] 语音识别服务不可用"
        
        try:
            # 读取音频
            if isinstance(audio_data, str):
                # 文件路径
                if LIBROSA_AVAILABLE:
                    import librosa
                    audio, sr = librosa.load(audio_data, sr=16000)
                else:
                    # 简单读取（需要soundfile或类似库）
                    return "[WARN] 需要librosa支持文件路径读取"
            else:
                # 字节流
                import io
                import soundfile as sf
                audio_stream = io.BytesIO(audio_data)
                audio, sr = sf.read(audio_stream)
            
            # 确保采样率正确
            if sr != 16000:
                if LIBROSA_AVAILABLE:
                    import librosa
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                    sr = 16000
            
            # 处理音频
            input_features = self.processor(
                audio, 
                sampling_rate=sr, 
                return_tensors="pt"
            ).input_features
            
            # 生成识别结果
            with torch.no_grad():
                predicted_ids = self.model.generate(input_features)
            
            # 解码
            transcription = self.processor.batch_decode(
                predicted_ids, 
                skip_special_tokens=True
            )[0]
            
            return transcription
            
        except Exception as e:
            return f"[WARN] 语音识别失败: {e}"
    
    async def transcribe(self, audio_data: Union[bytes, str], **kwargs) -> str:
        """转录音频（别名）"""
        return await self.process(audio_data, **kwargs)


class ImageUnderstander(BaseProcessor):
    """
    图像理解处理器（CLIP）
    
    支持：
    - 图像描述生成
    - 图像-文本匹配
    - 图像分类
    """
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._available = False
        self._load_model()
    
    def _load_model(self):
        """加载CLIP模型"""
        if not TRANSFORMERS_AVAILABLE:
            print("[WARN] transformers库不可用，图像理解功能受限")
            return
        
        try:
            print(f"🔄 正在加载CLIP模型: {self.model_name}")
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
            self._available = True
            print(f"[OK] CLIP模型加载完成: {self.model_name}")
        except Exception as e:
            print(f"[WARN] CLIP模型加载失败: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    async def process(self, image_data: Union[bytes, str], **kwargs) -> str:
        """
        处理图像数据
        
        Args:
            image_data: 图像字节流或文件路径
            **kwargs: 额外参数（description_text等）
            
        Returns:
            图像描述或分析结果
        """
        if not self.is_available():
            return "[WARN] 图像理解服务不可用"
        
        try:
            # 加载图像
            if isinstance(image_data, str):
                # 文件路径
                if PIL_AVAILABLE:
                    image = Image.open(image_data).convert('RGB')
                else:
                    return "[WARN] 需要PIL支持文件路径读取"
            else:
                # 字节流
                if PIL_AVAILABLE:
                    image = Image.open(io.BytesIO(image_data)).convert('RGB')
                else:
                    return "[WARN] 需要PIL处理字节流"
            
            # 准备描述文本（用于零样本分类）
            description_text = kwargs.get(
                "description_text", 
                "a photo of a person, object, scene, or situation"
            )
            
            # 处理图像和文本
            inputs = self.processor(
                text=[description_text],
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # 计算相似度
            with torch.no_grad():
                image_features = self.model.get_image_features(inputs["pixel_values"])
                text_features = self.model.get_text_features(inputs["input_ids"])
                
                # 归一化
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # 计算相似度
                similarity = (image_features @ text_features.T).item()
            
            # 生成描述
            description = f"图像与描述'{description_text}'的相似度: {similarity:.3f}"
            
            # 如果相似度高，可以扩展描述
            if similarity > 0.25:
                description += " [OK] 匹配度较高"
            else:
                description += " [WARN] 匹配度较低"
            
            return description
            
        except Exception as e:
            return f"[WARN] 图像理解失败: {e}"
    
    async def describe(self, image_data: Union[bytes, str], **kwargs) -> str:
        """生成图像描述（别名）"""
        return await self.process(image_data, **kwargs)


class TTSSynthesizer(BaseProcessor):
    """
    语音合成处理器（VITS）
    
    支持：
    - 文本转语音
    - 多音色支持
    - 实时合成
    """
    
    def __init__(self, model_name: str = "facebook/mms-tts-chinese"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._available = False
        self._load_model()
    
    def _load_model(self):
        """加载VITS模型"""
        if not TRANSFORMERS_AVAILABLE:
            print("[WARN] transformers库不可用，语音合成功能受限")
            return
        
        try:
            print(f"🔄 正在加载VITS模型: {self.model_name}")
            self.tokenizer = VitsTokenizer.from_pretrained(self.model_name)
            self.model = VitsModel.from_pretrained(self.model_name)
            self._available = True
            print(f"[OK] VITS模型加载完成: {self.model_name}")
        except Exception as e:
            print(f"[WARN] VITS模型加载失败: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    async def process(self, text: str, **kwargs) -> bytes:
        """
        处理文本转语音
        
        Args:
            text: 输入文本
            **kwargs: 额外参数（speaker_id等）
            
        Returns:
            音频字节流（WAV格式）
        """
        if not self.is_available():
            return b"[WARN] 语音合成服务不可用"
        
        try:
            # 编码文本
            inputs = self.tokenizer(text, return_tensors="pt")
            
            # 生成语音
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # 获取音频波形
            waveform = outputs.waveform[0]
            
            # 转换为字节流
            import io
            import soundfile as sf
            
            buffer = io.BytesIO()
            sf.write(buffer, waveform.numpy(), self.model.config.sampling_rate, format='WAV')
            audio_bytes = buffer.getvalue()
            
            return audio_bytes
            
        except Exception as e:
            return f"[WARN] 语音合成失败: {e}".encode()
    
    async def synthesize(self, text: str, **kwargs) -> bytes:
        """合成语音（别名）"""
        return await self.process(text, **kwargs)


class MultiModalProcessor:
    """
    多模态统一处理器
    
    整合所有模态处理器，提供统一接口
    """
    
    def __init__(
        self,
        whisper_model: str = "openai/whisper-small",
        clip_model: str = "openai/clip-vit-base-patch32",
        vits_model: str = "facebook/mms-tts-chinese"
    ):
        # 初始化各模态处理器
        self.speech_recognizer = SpeechRecognizer(whisper_model)
        self.image_understander = ImageUnderstander(clip_model)
        self.speech_synthesizer = TTSSynthesizer(vits_model)
        
        print("=" * 60)
        print("🎤 图像/语音 多模态处理器初始化")
        print("=" * 60)
        
        # 检查可用性
        available_count = sum([
            self.speech_recognizer.is_available(),
            self.image_understander.is_available(),
            self.speech_synthesizer.is_available()
        ])
        
        print(f"[OK] 可用处理器: {available_count}/3")
        print("=" * 60)
    
    def is_available(self, modality: str = "all") -> bool:
        """
        检查模态处理器可用性
        
        Args:
            modality: "audio", "image", "tts", 或 "all"
        """
        checks = {
            "audio": self.speech_recognizer.is_available(),
            "image": self.image_understander.is_available(),
            "tts": self.speech_synthesizer.is_available(),
        }
        
        if modality == "all":
            return all(checks.values())
        return checks.get(modality, False)
    
    async def process_audio(self, audio: bytes, **kwargs) -> str:
        """处理音频输入"""
        return await self.speech_recognizer.transcribe(audio, **kwargs)
    
    async def process_image(self, image: bytes, **kwargs) -> str:
        """处理图像输入"""
        return await self.image_understander.describe(image, **kwargs)
    
    async def synthesize_speech(self, text: str, **kwargs) -> bytes:
        """合成语音输出"""
        return await self.speech_synthesizer.synthesize(text, **kwargs)
    
    async def process_multimodal_input(
        self,
        audio: Optional[bytes] = None,
        image: Optional[bytes] = None,
        text: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理多模态输入
        
        Args:
            audio: 音频字节流
            image: 图像字节流
            text: 文本输入
            **kwargs: 额外参数
            
        Returns:
            处理结果字典
        """
        results = {}
        
        # 处理音频
        if audio:
            results["audio_text"] = await self.process_audio(audio, **kwargs)
        
        # 处理图像
        if image:
            results["image_desc"] = await self.process_image(image, **kwargs)
        
        # 文本直接返回
        if text:
            results["text_input"] = text
        
        return results
    
    async def generate_multimodal_response(
        self,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成多模态响应
        
        Args:
            text: 输入文本
            **kwargs: 额外参数
            
        Returns:
            响应字典（文本 + 语音）
        """
        results = {"text": text}
        
        # 生成语音
        if self.is_available("tts"):
            audio_bytes = await self.synthesize_speech(text, **kwargs)
            results["audio"] = audio_bytes
        
        return results
    
    def get_status(self) -> Dict[str, bool]:
        """获取处理器状态"""
        return {
            "speech_recognizer": self.speech_recognizer.is_available(),
            "image_understander": self.image_understander.is_available(),
            "speech_synthesizer": self.speech_synthesizer.is_available(),
        }


# 全局实例
_global_multimodal_processor = None


def get_multimodal_processor(
    whisper_model: str = "openai/whisper-small",
    clip_model: str = "openai/clip-vit-base-patch32",
    vits_model: str = "facebook/mms-tts-chinese"
) -> MultiModalProcessor:
    """获取全局多模态处理器实例"""
    global _global_multimodal_processor
    if _global_multimodal_processor is None:
        _global_multimodal_processor = MultiModalProcessor(
            whisper_model=whisper_model,
            clip_model=clip_model,
            vits_model=vits_model
        )
    return _global_multimodal_processor