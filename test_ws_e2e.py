"""
端到端 WebSocket 测试：验证 Nuwa 服务器的完整对话链路
- 连接 ws://127.0.0.1:8766
- 发送文本消息，收集 stream_chunk / stream_end
- 验证 LLM 是否真正返回内容

用法: python test_ws_e2e.py [消息内容]
"""
import asyncio
import json
import sys

import websockets

WS_URL = "ws://127.0.0.1:8766"
DEFAULT_MSG = "你好，请用一句话介绍一下你自己"


async def main(msg: str):
    print("=" * 60)
    print(f"端到端 WebSocket 测试 -> {WS_URL}")
    print(f"发送消息: {msg}")
    print("=" * 60)

    chunks = []
    full = ""
    got_stream_end = False
    error = None

    try:
        async with websockets.connect(WS_URL, open_timeout=30) as ws:
            print("[OK] WebSocket 已连接")

            # 接收初始状态广播
            try:
                init = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(init)
                print(f"[INFO] 初始消息 type={data.get('type')}")
            except asyncio.TimeoutError:
                print("[WARN] 未收到初始状态广播（可忽略）")

            # 发送文本消息
            await ws.send(json.dumps({"type": "text", "content": msg}))
            print("[OK] 已发送文本消息")

            # 收集响应：直到 stream_end 或超时
            deadline = asyncio.get_event_loop().time() + 90
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    print("[WARN] 等待 stream_end 超时 (90s)")
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except asyncio.TimeoutError:
                    print("[WARN] 接收超时")
                    break

                data = json.loads(raw)
                mtype = data.get("type")

                if mtype == "stream_chunk":
                    c = data.get("content", "")
                    chunks.append(c)
                    full += c
                elif mtype == "stream_end":
                    got_stream_end = True
                    print("[OK] 收到 stream_end")
                    break
                elif mtype == "error":
                    error = data.get("content")
                    print(f"[ERROR] 服务器返回错误: {error}")
                    break
                elif mtype == "status_update":
                    pass  # 状态广播，忽略
                else:
                    print(f"[INFO] 其他消息 type={mtype}")

    except Exception as e:
        print(f"[FAIL] 连接/通信异常: {type(e).__name__}: {e}")
        return 1

    # ---------- 结果判定 ----------
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"  收到 stream_chunk 数 : {len(chunks)}")
    print(f"  收到 stream_end      : {got_stream_end}")
    print(f"  拼接全文长度         : {len(full)}")
    print(f"  回复内容             : {full[:400]!r}")

    if error:
        print(f"\n[FAIL] 服务器错误: {error}")
        return 1
    if not got_stream_end:
        print("\n[FAIL] 未收到 stream_end")
        return 1
    if not full.strip():
        print("\n[FAIL] LLM 返回内容为空 —— 链路仍有问题")
        return 2
    print("\n[SUCCESS] 完整对话链路正常，LLM 返回了实际内容！")
    return 0


if __name__ == "__main__":
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_MSG
    sys.exit(asyncio.run(main(message)))
