"""
女娲聊天渠道集成模块

功能：提供与飞书、钉钉、企业微信等聊天渠道的集成能力
"""

from .feishu_channel import FeishuChannel
from .dingtalk_channel import DingTalkChannel
from .wecom_channel import WeComChannel
from .channel_manager import ChannelManager

__all__ = ['FeishuChannel', 'DingTalkChannel', 'WeComChannel', 'ChannelManager']