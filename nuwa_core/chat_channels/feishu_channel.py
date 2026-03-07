"""
飞书聊天渠道

功能：提供与飞书的集成能力，包括消息发送和接收
"""

import logging
import json
import requests
from typing import Dict, Any, Optional

class FeishuChannel:
    def __init__(self, config: Dict[str, Any], kernel=None):
        self.config = config
        self.app_id = config.get('appId')
        self.app_secret = config.get('appSecret')
        self.domain = config.get('domain', 'feishu')
        self.bot_name = config.get('botName', '女娲')  # 机器人名字，用于识别@消息
        self.logger = logging.getLogger(__name__)
        self.access_token = None
        self.ws_client = None
        self.kernel = kernel
        self.event_loop = None  # 保存主事件循环引用
        self.processed_events = set()  # 已处理的事件 ID 集合，用于防止重复处理
        self.max_event_cache = 1000  # 最多缓存的事件 ID 数量
    
    def set_event_loop(self, loop):
        """设置主事件循环引用，用于在线程安全的环境中执行异步任务"""
        self.event_loop = loop
        self.logger.info(f"已设置主事件循环：{loop}")
    
    def start_ws_client(self):
        """启动长连接客户端"""
        try:
            from .feishu_ws import FeishuWSClient
            self.ws_client = FeishuWSClient(self.app_id, self.app_secret, self.handle_message)
            # 在新线程中启动长连接，避免阻塞
            import threading
            thread = threading.Thread(target=self.ws_client.start, daemon=True)
            thread.start()
            
            # 启动连接监控线程
            def monitor_connection():
                import time
                while True:
                    time.sleep(300)  # 每 5 分钟检查一次连接状态
                    if not self.ws_client or not self.ws_client.running:
                        self.logger.warning("飞书长连接客户端未运行，正在重新启动...")
                        self.start_ws_client()
            
            monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
            monitor_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"启动长连接客户端失败：{e}")
            return False
    
    def _get_access_token(self) -> Optional[str]:
        """获取飞书访问令牌"""
        if self.access_token:
            return self.access_token
        
        try:
            # 使用正确的飞书 API 地址
            url = f"https://open.{self.domain}.cn/open-apis/auth/v3/app_access_token/internal/"
            self.logger.info(f"请求飞书访问令牌：{url}")
            self.logger.info(f"App ID: {self.app_id}")
            
            # 确保请求头正确
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            self.logger.info(f"请求载荷：{json.dumps(payload)}")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=30  # 增加超时时间
            )
            
            self.logger.info(f"响应状态码：{response.status_code}")
            self.logger.info(f"响应内容：{response.text[:1000]}...")
            
            # 检查响应状态码
            if response.status_code != 200:
                self.logger.error(f"获取访问令牌失败，状态码：{response.status_code}")
                self.logger.error(f"响应内容：{response.text}")
                return None
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON 解析错误：{str(e)}")
                self.logger.error(f"响应内容：{response.text}")
                return None
            
            if data.get('code') == 0:
                self.access_token = data.get('app_access_token')
                self.logger.info("获取访问令牌成功")
                return self.access_token
            else:
                self.logger.error(f"获取访问令牌失败：{data.get('msg', 'Unknown error')}")
                self.logger.error(f"完整响应：{json.dumps(data)}")
                return None
        except requests.RequestException as e:
            self.logger.error(f"网络请求错误：{str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"获取访问令牌时发生未知错误：{str(e)}")
            import traceback
            self.logger.error(f"详细错误信息：{traceback.format_exc()}")
            return None
    
    def send_message(self, message: str, recipient: str) -> bool:
        """发送消息到飞书"""
        access_token = self._get_access_token()
        if not access_token:
            self.logger.error("无法获取访问令牌，消息发送失败")
            return False
        
        try:
            # 使用正确的飞书 API 地址
            url = f"https://open.{self.domain}.cn/open-apis/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 根据接收者类型确定 receive_id_type
            if recipient.startswith('chat:'):
                receive_id_type = "chat_id"
                receive_id = recipient.replace('chat:', '')
            elif recipient.startswith('user:'):
                receive_id_type = "open_id"
                receive_id = recipient.replace('user:', '')
            else:
                # 默认认为是 open_id
                receive_id_type = "open_id"
                receive_id = recipient
            
            # 构建消息体 - 正确的 JSON 格式
            content = {
                "text": message
            }
            
            # 构建消息体 - 正确的 JSON 格式
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps(content, ensure_ascii=False)
            }
            
            # 将 receive_id_type 作为查询参数
            params = {
                "receive_id_type": receive_id_type
            }
            
            self.logger.info(f"发送消息到飞书：{url}")
            self.logger.info(f"接收者类型：{receive_id_type}")
            self.logger.info(f"接收者 ID: {receive_id}")
            self.logger.info(f"消息内容：{message}")
            self.logger.info(f"请求载荷：{json.dumps(payload, ensure_ascii=False)}")
            self.logger.info(f"查询参数：{json.dumps(params, ensure_ascii=False)}")
            
            # 使用 json 参数，并传递查询参数
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                params=params,
                timeout=30
            )
            
            self.logger.info(f"响应状态码：{response.status_code}")
            self.logger.info(f"响应内容：{response.text[:1000]}...")
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON 解析错误：{str(e)}")
                self.logger.error(f"响应内容：{response.text}")
                return False
            
            if data.get('code') == 0:
                self.logger.info(f"消息发送成功，接收者：{recipient}")
                message_id = data.get('data', {}).get('message_id', 'unknown')
                self.logger.info(f"消息 ID: {message_id}")
                return True
            else:
                error_msg = data.get('msg', 'Unknown error')
                error_code = data.get('code', 'Unknown code')
                self.logger.error(f"消息发送失败：{error_msg} (错误码：{error_code})")
                self.logger.error(f"完整响应：{json.dumps(data, ensure_ascii=False)}")
                return False
        except Exception as e:
            self.logger.error(f"发送消息时发生错误：{str(e)}")
            import traceback
            self.logger.error(f"详细错误信息：{traceback.format_exc()}")
            return False
    
    def handle_message(self, event: Dict[str, Any]):
        """处理来自飞书的消息"""
        try:
            # 解析飞书事件
            self.logger.info(f"Received event from Feishu: {json.dumps(event, ensure_ascii=False)}")
            
            # 检查事件类型
            event_type = event.get('header', {}).get('event_type', '')
            event_id = event.get('header', {}).get('event_id', '')
            self.logger.info(f"Event type: {event_type}, Event ID: {event_id}")
            
            # 去重检查：如果事件已处理过，直接跳过
            if event_id:
                if event_id in self.processed_events:
                    self.logger.info(f"事件已处理过，跳过：{event_id}")
                    return
                # 添加到已处理集合
                self.processed_events.add(event_id)
                # 如果集合太大，移除最早的事件
                if len(self.processed_events) > self.max_event_cache:
                    # 移除最早的 10% 事件
                    to_remove = list(self.processed_events)[:self.max_event_cache // 10]
                    for eid in to_remove:
                        self.processed_events.discard(eid)
            
            # 只处理消息事件
            if event_type != 'im.message.receive_v1':
                self.logger.info(f"Skipping event type: {event_type}")
                return
            
            # 提取消息内容
            event_body = event.get('event', {})
            message = event_body.get('message', {})
            
            # 获取消息相关信息
            message_id = message.get('message_id', '')
            chat_type = message.get('chat_type', '')  # group/group_bot/direct_bot
            chat_id = message.get('chat_id', '')
            content = message.get('content', '{}')
            
            # 获取发送者信息 - 从 event_body 中获取，因为某些 SDK 版本可能将 sender 放在这里
            sender = event_body.get('sender', {})
            if not sender:
                # 尝试从 message 中获取
                sender = message.get('sender', {})
            
            self.logger.info(f"Message details - ID: {message_id}, Chat Type: {chat_type}, Chat ID: {chat_id}")
            self.logger.info(f"Raw content: {content}")
            self.logger.info(f"Sender: {json.dumps(sender, ensure_ascii=False)}")
            
            # 解析消息内容
            try:
                content_data = json.loads(content)
                msg_text = content_data.get('text', '')
            except json.JSONDecodeError:
                msg_text = str(content)
            
            # 尝试从不同位置获取 mentions
            mentions = message.get('mentions', [])
            
            # 检查 message 对象的所有字段
            self.logger.info(f"Message object keys: {list(message.keys())}")
            self.logger.info(f"Parsed message text: {msg_text}")
            self.logger.info(f"Mentions: {json.dumps(mentions, ensure_ascii=False)}")
            
            # 检查 content 中是否有 mentions
            if 'mentions' in content_data:
                self.logger.info(f"Mentions in content: {json.dumps(content_data['mentions'], ensure_ascii=False)}")
                mentions.extend(content_data['mentions'])
            
            # 检查是否@了机器人
            bot_mentioned = False
            bot_key = ""
            bot_name_lower = self.bot_name.lower()
            
            # 方法 1: 检查 mentions 字段 - 这是最可靠的方法
            if mentions:
                for mention in mentions:
                    mention_name = mention.get('name', '')
                    mention_id = mention.get('id', '')
                    # 检查 mention 名字是否匹配配置的机器人名字
                    if mention_name and (
                        bot_name_lower in mention_name.lower() or 
                        '女娲' in mention_name or
                        'nuwa' in mention_name.lower()
                    ):
                        bot_mentioned = True
                        bot_key = mention.get('key', '')
                        self.logger.info(f"Bot mentioned via mentions field: {mention_name}")
                        break
            
            # 方法 2: 检查文本中是否包含@机器人名字
            if not bot_mentioned:
                # 检查多种可能的@格式
                at_patterns = [
                    f'@{self.bot_name}',
                    f'@{bot_name_lower}',
                    '@女娲',
                    '@nuwa',
                ]
                for pattern in at_patterns:
                    if pattern.lower() in msg_text.lower():
                        bot_mentioned = True
                        self.logger.info(f"Bot mentioned via text pattern: {pattern}")
                        break
            
            # 如果是私聊 (direct_bot)，则不需要@也可以处理
            is_direct_message = chat_type == 'direct_bot'
            self.logger.info(f"Is direct message: {is_direct_message}")
            
            # 处理消息：如果被@了或者是在私聊中
            if bot_mentioned or is_direct_message:
                self.logger.info(f"Processing message: {msg_text}")
                
                # 提取实际消息内容（去除@部分）
                clean_text = msg_text
                if bot_mentioned and bot_key:
                    # 移除@标记（飞书格式）
                    clean_text = clean_text.replace(f'<at user_id="{bot_key}">', '').replace('</at>', '').strip()
                
                # 移除各种@格式的文本
                at_patterns = [
                    f'@{self.bot_name}',
                    f'@{bot_name_lower}',
                    '@女娲',
                    '@nuwa',
                    '@Nuwa',
                    '@NUWA',
                ]
                for pattern in at_patterns:
                    clean_text = clean_text.replace(pattern, '')
                
                clean_text = clean_text.strip()
                self.logger.info(f"Cleaned message text: {clean_text}")
                
                if clean_text:
                    self.logger.info(f"Processing cleaned message: {clean_text}")
                    
                    # 调用 nuwa 的内核处理消息
                    if self.kernel:
                        import asyncio
                        import concurrent.futures
                        
                        async def process_message():
                            try:
                                self.logger.info(f"Processing message with kernel: {clean_text}")
                                result = await self.kernel.process_input(clean_text)
                                
                                # 处理回复
                                if result.get("reply"):
                                    reply = result["reply"]
                                    self.logger.info(f"Nuwa reply: {reply}")
                                    
                                    # 确定回复的目标
                                    # 使用预先保存的 sender 信息
                                    sender_id_info = sender.get('sender_id', {})
                                    open_id = sender_id_info.get('open_id', '')
                                    union_id = sender_id_info.get('union_id', '')
                                    user_id = sender_id_info.get('user_id', '')
                                    
                                    self.logger.info(f"Sender info - Open ID: {open_id}, Union ID: {union_id}, User ID: {user_id}")
                                    
                                    # 确定回复目标
                                    reply_target = ""
                                    if chat_type == 'group' or chat_type == 'group_bot':
                                        # 群聊，回复到群聊
                                        if chat_id:
                                            reply_target = f"chat:{chat_id}"
                                            self.logger.info(f"Replying to group chat: {chat_id}")
                                    elif chat_type == 'direct_bot':
                                        # 私聊，回复给用户
                                        if open_id:
                                            reply_target = f"user:{open_id}"
                                            self.logger.info(f"Replying to user: {open_id}")
                                        elif union_id:
                                            reply_target = union_id
                                            self.logger.info(f"Replying to user (union_id): {union_id}")
                                        elif user_id:
                                            reply_target = user_id
                                            self.logger.info(f"Replying to user (user_id): {user_id}")
                                    
                                    if reply_target:
                                        success = self.send_message(reply, reply_target)
                                        if success:
                                            self.logger.info("Reply sent successfully")
                                        else:
                                            self.logger.error("Failed to send reply")
                                    else:
                                        self.logger.error("Unable to determine reply target")
                                        
                                elif result.get("error"):
                                    self.logger.error(f"Kernel error: {result['error']}")
                                else:
                                    self.logger.warning("No reply or error from kernel")
                            except Exception as e:
                                self.logger.error(f"Error processing message with kernel: {e}")
                                import traceback
                                self.logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        # 使用线程安全的方式执行异步任务
                        def execute_async_task():
                            """在独立的事件循环中执行异步任务"""
                            try:
                                # 优先使用保存的事件循环引用
                                if self.event_loop and not self.event_loop.is_closed():
                                    self.logger.info("Using saved event loop reference")
                                    future = asyncio.run_coroutine_threadsafe(process_message(), self.event_loop)
                                    # 等待任务完成（最多等待 60 秒）
                                    try:
                                        future.result(timeout=60)
                                        self.logger.info("Message processing completed successfully")
                                    except concurrent.futures.TimeoutError:
                                        self.logger.error("Message processing timed out after 60 seconds")
                                    except Exception as e:
                                        self.logger.error(f"Message processing failed: {e}")
                                else:
                                    # 没有可用的事件循环，创建一个新的
                                    self.logger.info("No running event loop, creating new one")
                                    loop = asyncio.new_event_loop()
                                    try:
                                        loop.run_until_complete(process_message())
                                    finally:
                                        loop.close()
                            except Exception as e:
                                self.logger.error(f"Failed to execute async task: {e}")
                                import traceback
                                self.logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        # 在线程池中执行异步任务
                        try:
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(execute_async_task)
                                # 不等待完成，让任务在后台执行
                                # 这样不会阻塞消息处理
                        except Exception as e:
                            self.logger.error(f"Failed to submit async task: {e}")
                            # 回退到直接执行
                            execute_async_task()
                    else:
                        self.logger.error("Kernel not initialized, cannot process message")
                else:
                    self.logger.info("Message is empty after cleaning, ignoring")
            else:
                self.logger.info("Bot not mentioned and not a direct message, ignoring")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def probe(self) -> Dict[str, Any]:
        """探测飞书连接状态"""
        access_token = self._get_access_token()
        if not access_token:
            return {
                "status": "error",
                "message": "Failed to get access token"
            }
        
        try:
            # 使用正确的飞书 API 地址
            url = f"https://open.{self.domain}.cn/open-apis/im/v1/chats"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            self.logger.info(f"探测飞书连接：{url}")
            
            response = requests.get(url, headers=headers, params={"page_size": 1}, timeout=10)
            
            self.logger.info(f"响应状态码：{response.status_code}")
            self.logger.info(f"响应内容：{response.text[:500]}...")
            
            data = response.json()
            if data.get('code') == 0:
                return {
                    "status": "ok",
                    "message": "Connection successful"
                }
            else:
                return {
                    "status": "error",
                    "message": data.get('msg')
                }
        except Exception as e:
            self.logger.error(f"探测连接失败：{str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }