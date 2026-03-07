"""
企业微信聊天渠道

功能：提供与企业微信的集成能力，包括消息发送和接收
"""

import logging
import requests
import time
from typing import Dict, Any, Optional

class WeComChannel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.corp_id = config.get('corpId')
        self.corp_secret = config.get('corpSecret')
        self.agent_id = config.get('agentId')
        self.logger = logging.getLogger(__name__)
        self.access_token = None
        self.token_expire_time = 0
    
    def _get_access_token(self) -> Optional[str]:
        """获取企业微信访问令牌"""
        current_time = time.time()
        if self.access_token and current_time < self.token_expire_time:
            return self.access_token
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            response = requests.get(url)
            data = response.json()
            if data.get('errcode') == 0:
                self.access_token = data.get('access_token')
                self.token_expire_time = current_time + 7200  # 2小时过期
                return self.access_token
            else:
                self.logger.error(f"Failed to get access token: {data.get('errmsg')}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def send_message(self, message: str, recipient: str) -> bool:
        """发送消息到企业微信"""
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            # 构建消息体
            payload = {
                "touser": recipient if recipient.startswith('user:') else recipient,
                "agentid": self.agent_id,
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            if data.get('errcode') == 0:
                self.logger.info(f"Message sent to {recipient}")
                return True
            else:
                self.logger.error(f"Failed to send message: {data.get('errmsg')}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def handle_message(self, message: Dict[str, Any]):
        """处理来自企业微信的消息"""
        try:
            # 这里可以根据实际需求处理消息
            self.logger.info(f"Received message from WeCom: {message}")
            # 可以在这里添加消息处理逻辑，如解析消息内容、调用nuwa的其他模块等
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
            url = f"https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token={access_token}"
            response = requests.get(url)
            data = response.json()
            if data.get('errcode') == 0:
                return {
                    "status": "ok",
                    "message": "Connection successful"
                }
            else:
                return {
                    "status": "error",
                    "message": data.get('errmsg')
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
