"""
聊天渠道测试脚本（简单版）

功能：测试聊天渠道的基本功能
"""

import yaml

# 定义一个简单的ChannelManager类
class ChannelManager:
    def __init__(self):
        self.channels = {}
        self.channel_classes = {}
    
    def register_channel(self, channel_name, channel_class):
        """注册聊天渠道类"""
        self.channel_classes[channel_name] = channel_class
        print(f"Registered channel: {channel_name}")
    
    def initialize_channel(self, channel_name, config):
        """初始化聊天渠道"""
        if channel_name not in self.channel_classes:
            print(f"Channel {channel_name} not registered")
            return False
        
        try:
            channel = self.channel_classes[channel_name](config)
            self.channels[channel_name] = channel
            print(f"Initialized channel: {channel_name}")
            return True
        except Exception as e:
            print(f"Failed to initialize channel {channel_name}: {str(e)}")
            return False
    
    def get_channel(self, channel_name):
        """获取指定渠道实例"""
        return self.channels.get(channel_name)
    
    def list_channels(self):
        """列出所有已初始化的渠道"""
        return list(self.channels.keys())

# 定义简单的渠道类
class FeishuChannel:
    def __init__(self, config):
        self.config = config
        print(f"FeishuChannel initialized with appId: {config.get('appId')}")

class DingTalkChannel:
    def __init__(self, config):
        self.config = config
        print(f"DingTalkChannel initialized with appKey: {config.get('appKey')}")

class WeComChannel:
    def __init__(self, config):
        self.config = config
        print(f"WeComChannel initialized with corpId: {config.get('corpId')}")

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

if __name__ == "__main__":
    test_channel_manager()
