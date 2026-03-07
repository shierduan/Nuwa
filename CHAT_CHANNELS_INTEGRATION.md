# 聊天渠道集成说明

## 功能介绍

本模块为女娲提供了与飞书、钉钉、企业微信等聊天渠道的集成能力，支持消息的发送和接收。

## 实现的功能

1. **渠道管理**：通过ChannelManager统一管理所有聊天渠道
2. **飞书集成**：支持与飞书的消息发送和接收
3. **钉钉集成**：支持与钉钉的消息发送和接收
4. **企业微信集成**：支持与企业微信的消息发送和接收
5. **连接状态探测**：支持探测各聊天渠道的连接状态

## 目录结构

```
nuwa_core/
└── chat_channels/
    ├── __init__.py              # 模块导出
    ├── channel_manager.py       # 渠道管理器
    ├── feishu_channel.py        # 飞书渠道实现
    ├── dingtalk_channel.py      # 钉钉渠道实现
    └── wecom_channel.py         # 企业微信渠道实现
```

## 配置说明

在使用聊天渠道之前，需要在配置文件中添加相应的配置。以下是配置示例：

```yaml
# 聊天渠道配置
chat_channels:
  # 飞书配置
  feishu:
    appId: "your_feishu_app_id"
    appSecret: "your_feishu_app_secret"
    domain: "feishu"  # 可选值：feishu 或 lark

  # 钉钉配置
  dingtalk:
    appKey: "your_dingtalk_app_key"
    appSecret: "your_dingtalk_app_secret"
    agentId: "your_dingtalk_agent_id"

  # 企业微信配置
  wecom:
    corpId: "your_wecom_corp_id"
    corpSecret: "your_wecom_corp_secret"
    agentId: "your_wecom_agent_id"
```

## 使用方法

### 1. 初始化渠道管理器

```python
from nuwa_core.chat_channels import ChannelManager, FeishuChannel, DingTalkChannel, WeComChannel

# 创建渠道管理器
manager = ChannelManager()

# 注册渠道
manager.register_channel('feishu', FeishuChannel)
manager.register_channel('dingtalk', DingTalkChannel)
manager.register_channel('wecom', WeComChannel)
```

### 2. 初始化聊天渠道

```python
# 加载配置
import yaml
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 初始化渠道
chat_channels_config = config.get('chat_channels', {})
for channel_name, channel_config in chat_channels_config.items():
    manager.initialize_channel(channel_name, channel_config)
```

### 3. 发送消息

```python
# 发送消息到飞书
manager.send_message('feishu', 'Hello from Nuwa!', 'user:open_id')

# 发送消息到钉钉
manager.send_message('dingtalk', 'Hello from Nuwa!', 'user_id')

# 发送消息到企业微信
manager.send_message('wecom', 'Hello from Nuwa!', 'user_id')
```

### 4. 接收消息

```python
# 接收来自飞书的消息
manager.receive_message('feishu', message_data)

# 接收来自钉钉的消息
manager.receive_message('dingtalk', message_data)

# 接收来自企业微信的消息
manager.receive_message('wecom', message_data)
```

### 5. 探测渠道状态

```python
# 探测飞书渠道状态
feishu_channel = manager.get_channel('feishu')
if feishu_channel:
    status = feishu_channel.probe()
    print(f"Feishu status: {status}")

# 探测钉钉渠道状态
dingtalk_channel = manager.get_channel('dingtalk')
if dingtalk_channel:
    status = dingtalk_channel.probe()
    print(f"DingTalk status: {status}")

# 探测企业微信渠道状态
wecom_channel = manager.get_channel('wecom')
if wecom_channel:
    status = wecom_channel.probe()
    print(f"WeCom status: {status}")
```

## 依赖项

本模块依赖以下Python包：

- requests>=2.28.0  # 用于HTTP请求

这些依赖项已经在项目的requirements.txt文件中定义。

## 注意事项

1. 使用前需要在各聊天平台创建相应的应用，并获取对应的App ID、App Secret等配置信息
2. 确保网络环境能够访问各聊天平台的API
3. 不同聊天平台的消息格式和API调用方式可能有所不同，请参考相应平台的开发文档
4. 建议在生产环境中使用加密方式存储敏感配置信息，如App Secret等
