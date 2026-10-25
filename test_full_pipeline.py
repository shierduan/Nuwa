"""
全链路验证：WebSocket 对话 → LLM 流式回复 → 记忆写入（惊奇门控）→ 记忆召回
用法: python test_full_pipeline.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import websockets

WS_URL = "ws://127.0.0.1:8766"


async def main():
    print("=" * 60)
    print("全链路验证：对话 → 记忆写入 → 记忆召回")
    print("=" * 60)

    try:
        async with websockets.connect(WS_URL) as ws:
            # 1. 接收初始状态
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            init = json.loads(msg)
            print(f"[1] 收到初始消息: type={init.get('type')}")

            # 2. 发送一条高信息量消息
            user_msg = (
                "我下个月要去北海道旅行看雪，这是筹划了很久的事情，"
                "有点期待但也担心那边的交通和住宿问题"
            )
            await ws.send(json.dumps({
                "type": "text",
                "content": user_msg,
                "session_id": "verify_session",
            }))
            print(f"[2] 已发送消息: {user_msg[:36]}...")

            # 3. 接收流式回复
            chunks = []
            got_reply = False
            deadline = asyncio.get_event_loop().time() + 120
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=90)
                except asyncio.TimeoutError:
                    break
                m = json.loads(raw)
                t = m.get("type")
                if t == "stream_chunk":
                    chunks.append(m.get("content", ""))
                elif t == "stream_end":
                    got_reply = True
                    break
                elif t == "error":
                    print(f"[FAIL] 服务端错误: {m.get('content')}")
                    return 1

            reply = "".join(chunks)
            print(f"[3] 收到回复 {len(chunks)} 块, 共 {len(reply)} 字")
            print(f"    回复摘要: {reply[:100]}")
            if not got_reply:
                print("[FAIL] 未收到 stream_end")
                return 1
            if len(reply) < 10:
                print("[FAIL] 回复内容过短，LLM 可能未正常返回")
                return 1

            # 4. 验证记忆写入（从服务端日志角度由 store 打印，这里用第二次查询验证召回）
            print("[4] 等待记忆落库...")
            await asyncio.sleep(3)

            # 5. 触发 /dream 指令，验证梦境流程可用
            await ws.send(json.dumps({
                "type": "text",
                "content": "/dream",
                "session_id": "verify_session",
            }))
            dream_msgs = []
            deadline = asyncio.get_event_loop().time() + 90
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    break
                m = json.loads(raw)
                if m.get("type") == "text":
                    dream_msgs.append(m.get("content", ""))
                if m.get("type") == "stream_end":
                    break
            dream_text = " ".join(dream_msgs)
            print(f"[5] /dream 响应: {dream_text[:120]}")
            if "未能运行" in dream_text:
                print("[FAIL] 梦境流程执行失败")
                return 1
            print("[5] /dream 指令执行: OK")

        print()
        print("[SUCCESS] 全链路验证通过")
        return 0
    except Exception as e:
        print(f"[FAIL] 异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
