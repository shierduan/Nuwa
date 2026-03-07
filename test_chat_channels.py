"""
聊天渠道测试脚本

功能：测试飞书、钉钉、企业微信等聊天渠道的集成功能
"""

import yaml
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

# 直接导入chat_channels模块中的文件
from nuwa_core.chat_channels.channel_manager import ChannelManager
from nuwa_core.chat_channels.feishu_channel import FeishuChannel
from nuwa_core.chat_channels.dingtalk_channel import DingTalkChannel
from nuwa_core.chat_channels.wecom_channel import WeComChannel

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
