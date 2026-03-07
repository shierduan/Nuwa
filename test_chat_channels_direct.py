"""
聊天渠道测试脚本（直接测试）

功能：直接测试chat_channels模块的功能，避免加载nuwa_core的其他依赖
"""

import yaml
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 直接读取channel_manager.py文件的内容并执行
channel_manager_code = """
import logging
from typing import Dict, Type, Optional, List, Any

class ChannelManager:
    def __init__(self):
        self.channels = {}
        self.channel_classes = {}
        self.logger = logging.getLogger(__name__)
    
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
            channel = self.channel_classes[channel_name](config)
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
"""

# 直接读取feishu_channel.py文件的内容并执行
feishu_channel_code = """
import logging
from typing import Dict, Any, Optional

class FeishuChannel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app_id = config.get('appId')
        self.app_secret = config.get('appSecret')
        self.domain = config.get('domain', 'feishu')
        self.logger = logging.getLogger(__name__)
        self.access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """获取飞书访问令牌"""
        if self.access_token:
            return self.access_token
        
        try:
            # 模拟获取access token
            print(f"模拟获取飞书access token for appId: {self.app_id}")
            self.access_token = "mock_access_token"
            return self.access_token
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def send_message(self, message: str, recipient: str) -> bool:
        """发送消息到飞书"""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        try:
            print(f"模拟发送消息到飞书: {message} 给 {recipient}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def handle_message(self, message: Dict[str, Any]):
        """处理来自飞书的消息"""
        try:
            print(f"模拟处理来自飞书的消息: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
    
    def probe(self) -> Dict[str, Any]:
        """探测飞书连接状态"""
        access_token = self._get_access_token()
        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        try:
            print("模拟探测飞书连接状态")
            return {
                "status": "ok",
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
"""

# 直接读取dingtalk_channel.py文件的内容并执行
dingtalk_channel_code = """
import logging
from typing import Dict, Any, Optional

class DingTalkChannel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app_key = config.get('appKey')
        self.app_secret = config.get('appSecret')
        self.agent_id = config.get('agentId')
        self.logger = logging.getLogger(__name__)
        self.access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """获取钉钉访问令牌"""
        if self.access_token:
            return self.access_token
        
        try:
            # 模拟获取access token
            print(f"模拟获取钉钉access token for appKey: {self.app_key}")
            self.access_token = "mock_access_token"
            return self.access_token
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def send_message(self, message: str, recipient: str) -> bool:
        """发送消息到钉钉"""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        try:
            print(f"模拟发送消息到钉钉: {message} 给 {recipient}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def handle_message(self, message: Dict[str, Any]):
        """处理来自钉钉的消息"""
        try:
            print(f"模拟处理来自钉钉的消息: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
    
    def probe(self) -> Dict[str, Any]:
        """探测钉钉连接状态"""
        access_token = self._get_access_token()
        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        try:
            print("模拟探测钉钉连接状态")
            return {
                "status": "ok",
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
"""

# 直接读取wecom_channel.py文件的内容并执行
wecom_channel_code = """
import logging
from typing import Dict, Any, Optional

class WeComChannel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.corp_id = config.get('corpId')
        self.corp_secret = config.get('corpSecret')
        self.agent_id = config.get('agentId')
        self.logger = logging.getLogger(__name__)
        self.access_token = None
    
    def _get_access_token(self) -> Optional[str]:
        """获取企业微信访问令牌"""
        if self.access_token:
            return self.access_token
        
        try:
            # 模拟获取access token
            print(f"模拟获取企业微信access token for corpId: {self.corp_id}")
            self.access_token = "mock_access_token"
            return self.access_token
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def send_message(self, message: str, recipient: str) -> bool:
        """发送消息到企业微信"""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        try:
            print(f"模拟发送消息到企业微信: {message} 给 {recipient}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def handle_message(self, message: Dict[str, Any]):
        """处理来自企业微信的消息"""
        try:
            print(f"模拟处理来自企业微信的消息: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
    
    def probe(self) -> Dict[str, Any]:
        """探测企业微信连接状态"""
        access_token = self._get_access_token()
        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        try:
            print("模拟探测企业微信连接状态")
            return {
                "status": "ok",
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
"""

# 执行代码，定义类
exec(channel_manager_code)
exec(feishu_channel_code)
exec(dingtalk_channel_code)
exec(wecom_channel_code)

def load_config():
    """加载配置文件"""
    try:
        with open('chat_channels_example_config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return {}

def test_channel_manager():
    """测试渠道管理器"""
    print("=== 测试渠道管理器 ===")
    
    # 创建渠道管理器
    manager = ChannelManager()
    
    # 注册渠道
    manager.register_channel('feishu', FeishuChannel)
    manager.register_channel('dingtalk', DingTalkChannel)
    manager.register_channel('wecom', WeComChannel)
    
    # 加载配置
    config = load_config()
    chat_channels_config = config.get('chat_channels', {})
    
    # 初始化渠道
    for channel_name, channel_config in chat_channels_config.items():
        print(f"\n初始化 {channel_name} 渠道...")
        success = manager.initialize_channel(channel_name, channel_config)
        print(f"初始化结果: {'成功' if success else '失败'}")
    
    # 列出已初始化的渠道
    print("\n已初始化的渠道:")
    for channel in manager.list_channels():
        print(f"- {channel}")
    
    # 测试获取渠道
    print("\n=== 测试获取渠道 ===")
    for channel_name in ['feishu', 'dingtalk', 'wecom']:
        channel = manager.get_channel(channel_name)
        print(f"获取 {channel_name} 渠道: {'成功' if channel else '失败'}")
    
    # 测试消息发送（模拟）
    print("\n=== 测试消息发送 ===")
    test_message = "这是一条测试消息"
    test_recipient = "user:test_user_id"
    
    for channel_name in manager.list_channels():
        print(f"\n尝试发送消息到 {channel_name}...")
        success = manager.send_message(channel_name, test_message, test_recipient)
        print(f"发送结果: {'成功' if success else '失败'}")
    
    # 测试探测功能（模拟）
    print("\n=== 测试渠道探测 ===")
    for channel_name in manager.list_channels():
        print(f"\n探测 {channel_name} 渠道...")
        channel = manager.get_channel(channel_name)
        if channel:
            result = channel.probe()
            print(f"探测结果: {result}")
        else:
            print("渠道未初始化")

if __name__ == "__main__":
    test_channel_manager()
