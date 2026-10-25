"""
端到端记忆测试：验证 Nuwa 的记忆存储与检索链路
- 第一轮：告知一个特定事实（暗号）
- 等待记忆写入
- 第二轮：询问该事实，检查是否能回忆起来

用法: python test_memory_e2e.py
"""
import asyncio
import json
import sys

import websockets

WS_URL = "ws://127.0.0.1:8766"
SECRET = "银月之约"
MSG_1 = f"请记住这个暗号：{SECRET}。这是只有我们两个人知道的秘密。"
MSG_2 = "我之前告诉你的那个暗号是什么？请直接回答。"


async def send_and_wait(ws, content: str, timeout: float = 120.0):
    """发送文本消息并等待完整的流式响应，返回拼接的完整回复"""
    await ws.send(json.dumps({"type": "text", "content": content}))
    full = ""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            print("  [WARN] 等待响应超时")
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        data = json.loads(raw)
        mtype = data.get("type")
        if mtype == "stream_chunk":
            full += data.get("content", "")
        elif mtype == "stream_end":
            break
        elif mtype == "error":
            print(f"  [ERROR] {data.get('content')}")
            break
    return full


async def main():
    print("=" * 60)
    print("端到端记忆测试")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL, open_timeout=30) as ws:
            print("[OK] WebSocket 已连接\n")

            print(f"[第1轮] 告知暗号: {SECRET}")
            r1 = await send_and_wait(ws, MSG_1)
            print(f"  回复: {r1[:200]!r}\n")

            # 等待记忆异步写入完成
            print("[等待] 6 秒，让记忆写入 LanceDB ...")
            await asyncio.sleep(6)

            print(f"[第2轮] 询问暗号")
            r2 = await send_and_wait(ws, MSG_2)
            print(f"  回复: {r2[:300]!r}\n")

            # 判定
            print("=" * 60)
            print("测试结果")
            print("=" * 60)
            hit = SECRET in r2
            print(f"  暗号 '{SECRET}' 是否出现在第2轮回复: {hit}")
            if hit:
                print("\n[SUCCESS] 记忆链路正常：成功检索到先前对话内容！")
                return 0
            print("\n[WARN] 未直接命中暗号 —— 可能是检索阈值/截断，或模型转述。")
            return 2

    except Exception as e:
        print(f"[FAIL] 异常: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
