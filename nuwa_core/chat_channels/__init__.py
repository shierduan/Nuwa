"""
女娲聊天渠道集成模块

功能：提供与飞书、钉钉、企业微信等聊天渠道的集成能力
"""

from .channel_manager import ChannelManager
from .dingtalk_channel import DingTalkChannel
from .feishu_channel import FeishuChannel
from .wecom_channel import WeComChannel

__all__ = ['FeishuChannel', 'DingTalkChannel', 'WeComChannel', 'ChannelManager']
