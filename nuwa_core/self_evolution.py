"""
女娲自我进化模块 (Nuwa Self Evolution Module)

功能：管理女娲的自我进化过程，包括性格、行为模式和关系模式的演化。

核心功能：
- SelfEvolution: 自我进化管理类
- 支持从历史记忆中提取演化特征
- 支持多种演化维度（性格、习惯、关系等）
- 完善的错误处理和日志记录
- 独立于记忆梦境系统，可单独调用
"""

import json
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

import numpy as np


class SelfEvolution:
    """
    女娲自我进化管理类
    
    负责管理女娲的自我进化过程，包括性格、行为模式和关系模式的演化。
    支持从历史记忆中提取演化特征，更新演化人格数据，并保存到文件。
    """
    
    def __init__(self, memory_cortex, llm_client, model_name: str = "local-model"):
        """
        初始化自我进化管理类
        
        Args:
            memory_cortex: 记忆皮层实例
            llm_client: LLM 客户端实例
            model_name: 模型名称
        """
        self.memory_cortex = memory_cortex
        self.llm_client = llm_client
        self.model_name = model_name
        
        # 演化配置
        self.evolution_config = {
            "max_memory_samples": 20,  # 每个时间桶的最大记忆样本数
            "time_buckets": {
                "short_term": 86400,  # 短期：1天
                "recent": 2592000,  # 近期：30天
                "medium": 7776000,  # 中期：90天
                "long_term": 31536000  # 长期：1年
            },
            "default_weights": {
                "short_term_vibe": 1.0,
                "recent_habits": 0.7,
                "relationship_phase": 0.4,
                "core_bond": 0.2
            }
        }
        
        # 演化状态
        self.evolution_state = {
            "last_evolution_time": 0.0,
            "evolution_count": 0,
            "last_evolution_result": None
        }
    
    def _get_time_buckets(self, current_time: float) -> Dict[str, List[str]]:
        """
        将记忆按时间分桶
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            按时间分桶的记忆文本列表
        """
        buckets = {
            "short_term": [],  # < 1天
            "recent": [],      # 1天 - 30天
            "medium": [],      # 30天 - 90天
            "long_term": []    # > 90天
        }
        
        # 获取最近的记忆
        recent_memories = self.memory_cortex.get_recent_memories(limit=2000, memory_type="raw")
        if not recent_memories:
            return buckets
        
        # 按时间分桶
        for mem in recent_memories:
            try:
                timestamp = float(mem.get("timestamp", current_time))
                text = mem.get("text", "").strip()
                if not text:
                    continue
                
                age_seconds = current_time - timestamp
                
                if age_seconds < self.evolution_config["time_buckets"]["short_term"]:
                    buckets["short_term"].append(text)
                elif age_seconds < self.evolution_config["time_buckets"]["recent"]:
                    buckets["recent"].append(text)
                elif age_seconds < self.evolution_config["time_buckets"]["medium"]:
                    buckets["medium"].append(text)
                else:
                    buckets["long_term"].append(text)
            except Exception as e:
                # 跳过无效记忆
                continue
        
        return buckets
    
    def _analyze_short_term_vibe(self, short_term_memories: List[str]) -> str:
        """
        分析短期（1天）记忆，提取当前情绪
        
        Args:
            short_term_memories: 短期记忆文本列表
            
        Returns:
            当前情绪描述字符串
        """
        if not short_term_memories:
            return ""
        
        sampled_texts = short_term_memories[:self.evolution_config["max_memory_samples"]]  # 采样最多指定数量的记忆
        joined_text = "\n".join(sampled_texts)
        
        prompt = (
            "你是女娲的自我进化分析器。请分析以下最近1天的对话记忆，"
            "提取用户的当前情绪状态和即时需求。"
            "输出1-2句话的简洁总结，描述用户的当前心情和即时关注点。\n\n"
            f"{joined_text}\n\n"
            "总结："
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个负责分析用户当前状态的人格分析器。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=128,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[SelfEvolution] 分析短期情绪失败: {e}")
            return ""
    
    def _analyze_recent_habits(self, recent_memories: List[str]) -> str:
        """
        分析近期（1月）记忆，提取行为习惯
        
        Args:
            recent_memories: 近期记忆文本列表
            
        Returns:
            行为习惯描述字符串
        """
        if not recent_memories:
            return ""
        
        sampled_texts = recent_memories[:self.evolution_config["max_memory_samples"]]
        joined_text = "\n".join(sampled_texts)
        
        prompt = (
            "你是女娲的自我进化分析器。请分析以下最近1个月的对话记忆，"
            "提取用户的行为习惯、常见话题和互动模式。"
            "输出1-2句话的简洁总结，描述用户的近期习惯和常聊话题。\n\n"
            f"{joined_text}\n\n"
            "总结："
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个负责分析用户习惯的人格分析器。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=128,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[SelfEvolution] 分析近期习惯失败: {e}")
            return ""
    
    def _analyze_relationship_phase(self, medium_memories: List[str]) -> str:
        """
        分析中期（3月）记忆，提取关系阶段
        
        Args:
            medium_memories: 中期记忆文本列表
            
        Returns:
            关系阶段描述字符串
        """
        if not medium_memories:
            return ""
        
        sampled_texts = medium_memories[:self.evolution_config["max_memory_samples"]]
        joined_text = "\n".join(sampled_texts)
        
        prompt = (
            "你是女娲的自我进化分析器。请分析以下最近3个月的对话记忆，"
            "提取用户与女娲的关系定义、关系发展阶段和互动深度。"
            "输出1-2句话的简洁总结，描述当前的关系定义和关系特征。\n\n"
            f"{joined_text}\n\n"
            "总结："
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个负责分析关系定义的人格分析器。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=128,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[SelfEvolution] 分析关系阶段失败: {e}")
            return ""
    
    def _analyze_core_values(self, long_term_memories: List[str]) -> str:
        """
        分析长期（1年）记忆，提取核心价值观
        
        Args:
            long_term_memories: 长期记忆文本列表
            
        Returns:
            核心价值观描述字符串
        """
        if not long_term_memories:
            return ""
        
        sampled_texts = long_term_memories[:self.evolution_config["max_memory_samples"]]
        joined_text = "\n".join(sampled_texts)
        
        prompt = (
            "你是女娲的自我进化分析器。请分析以下超过3个月的长期对话记忆，"
            "提取用户与女娲的共享价值观、核心纽带和深层关系基础。"
            "输出1-2句话的简洁总结，描述核心共享价值观和长期关系基础。\n\n"
            f"{joined_text}\n\n"
            "总结："
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个负责分析长期关系的人格分析器。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=128,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[SelfEvolution] 分析核心价值观失败: {e}")
            return ""
    
    def evolve(self) -> Dict[str, Any]:
        """
        执行自我进化
        
        从不同时间段的记忆中提取特征，更新演化人格数据
        
        Returns:
            包含 evolved_persona 数据的字典
        """
        current_time = time.time()
        
        # 获取时间分桶的记忆
        buckets = self._get_time_buckets(current_time)
        
        # 初始化演化人格数据
        evolved_persona = {
            "short_term_vibe": "",
            "recent_habits": "",
            "relationship_phase": "",
            "core_values": "",
            "weights": self.evolution_config["default_weights"],
            "last_evolution_time": current_time,
        }
        
        # 分析不同时间段的记忆
        evolved_persona["short_term_vibe"] = self._analyze_short_term_vibe(buckets["short_term"])
        evolved_persona["recent_habits"] = self._analyze_recent_habits(buckets["recent"])
        evolved_persona["relationship_phase"] = self._analyze_relationship_phase(buckets["medium"])
        evolved_persona["core_values"] = self._analyze_core_values(buckets["long_term"])
        
        # 更新演化状态
        self.evolution_state["last_evolution_time"] = current_time
        self.evolution_state["evolution_count"] += 1
        self.evolution_state["last_evolution_result"] = evolved_persona
        
        return evolved_persona