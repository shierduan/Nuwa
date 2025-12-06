# 测试WebSocket连接的Python脚本
import asyncio
import websockets
import json

async def test_websocket():
    backend_url = "ws://localhost:8000/ws"
    print("===== WebSocket客户端测试开始 =====")
    print(f"尝试连接到后端: {backend_url}")
    
    try:
        # 建立WebSocket连接
        async with websockets.connect(backend_url) as websocket:
            print("✅ WebSocket连接成功！")
            
            # 发送测试消息
            test_message = {"type": "text", "content": "你好"}
            message_json = json.dumps(test_message)
            print(f"发送消息: {test_message}")
            await websocket.send(message_json)
            print("消息已发送")
            
            # 等待接收响应
            print("等待后端响应...")
            response = await websocket.recv()
            print(f"✅ 收到后端响应:")
            print(response)
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    finally:
        print("===== WebSocket客户端测试结束 =====")

# 运行测试
asyncio.run(test_websocket())
