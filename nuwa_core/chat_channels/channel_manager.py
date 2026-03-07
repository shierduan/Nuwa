"""
聊天渠道管理器

功能：管理所有聊天渠道的注册、初始化和消息分发
"""

import logging
from typing import Dict, Type, Optional, List, Any

class ChannelManager:
    def __init__(self, kernel=None):
        self.channels = {}
        self.channel_classes = {}
        self.logger = logging.getLogger(__name__)
        self.kernel = kernel
    
    def register_channel(self, channel_name: str, channel_class: Type):
        """注册聊天渠道类"""
        self.channel_classes[channel_name] = channel_class
        self.logger.info(f"Registered channel: {channel_name}")
    
    def initialize_channel(self, channel_name: str, config: Dict[str, Any]) -> bool:
        """初始化聊天渠道"""
        if channel_name not in self.channel_classes:
            self.logger.error(f"Channel {channel_name} not registered")
            return False
        
        try:
            channel = self.channel_classes[channel_name](config, kernel=self.kernel)
            self.channels[channel_name] = channel
            self.logger.info(f"Initialized channel: {channel_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize channel {channel_name}: {str(e)}")
            return False
    
    def send_message(self, channel_name: str, message: str, recipient: str) -> bool:
        """发送消息到指定渠道"""
        if channel_name not in self.channels:
            self.logger.error(f"Channel {channel_name} not initialized")
            return False
        
        try:
            return self.channels[channel_name].send_message(message, recipient)
        except Exception as e:
            self.logger.error(f"Failed to send message via {channel_name}: {str(e)}")
            return False
    
    def receive_message(self, channel_name: str, message: Dict[str, Any]):
        """接收来自渠道的消息"""
        if channel_name not in self.channels:
            self.logger.error(f"Channel {channel_name} not initialized")
            return
        
        try:
            self.channels[channel_name].handle_message(message)
        except Exception as e:
            self.logger.error(f"Failed to handle message from {channel_name}: {str(e)}")
    
    def get_channel(self, channel_name: str) -> Optional[Any]:
        """获取指定渠道实例"""
        return self.channels.get(channel_name)
    
    def list_channels(self) -> List[str]:
        """列出所有已初始化的渠道"""
        return list(self.channels.keys())
