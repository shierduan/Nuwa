"""
诊断脚本：验证 OpenAI SDK 对 Kilo AI gateway 的流式调用行为
目标：定位「流式响应完成但客户端收不到 stream_chunk」的根因

用法: python diag_stream.py
"""
import asyncio
import sys
import time

BASE_URL = "https://api.kilo.ai/api/gateway"
API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6IjZlNDgwMDUwLTY2NmItNDI1Yi1iOTNmLTlkZjU5Zjg0MDdlNCIsImFwaVRva2VuUGVwcGVyIjpudWxsLCJ2ZXJzaW9uIjozLCJpYXQiOjE3OTI4NTE4NjIsImV4cCI6MTk1MDUzMTg2Mn0."
    "KwnDwaSlRkyNrUipff3RnEXH0BwKj0PUZKPgBbjWASQ"
)
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
TEST_MSG = "用一句话介绍你自己"


async def main():
    print("=" * 60)
    print("诊断：Kilo AI gateway 流式/非流式调用")
    print(f"  base_url = {BASE_URL}")
    print(f"  model    = {MODEL}")
    print("=" * 60)

    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("[FATAL] 未安装 openai SDK，请先 pip install openai")
        return 1

    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

    # ---------- 测试 1：非流式 ----------
    print("\n[测试1] 非流式调用 (stream=False)")
    t0 = time.time()
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": TEST_MSG}],
            temperature=0.7,
            max_tokens=256,
            stream=False,
        )
        content = resp.choices[0].message.content
        print(f"  [OK] 耗时 {time.time()-t0:.2f}s")
        print(f"  响应内容 = {content!r}")
        nonstream_ok = bool(content and content.strip())
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        nonstream_ok = False

    # ---------- 测试 2：OpenAI SDK 流式 ----------
    print("\n[测试2] OpenAI SDK 流式调用 (stream=True, async for)")
    t0 = time.time()
    n_chunks = 0
    full = ""
    stream_ok = False
    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": TEST_MSG}],
            temperature=0.7,
            max_tokens=256,
            stream=True,
        )
        print(f"  stream 对象类型 = {type(stream).__name__}")
        async for chunk in stream:
            n_chunks += 1
            try:
                delta = chunk.choices[0].delta.content
            except (IndexError, AttributeError):
                delta = None
            if delta:
                full += delta
                if n_chunks <= 8:
                    print(f"    chunk#{n_chunks} = {delta!r}")
        print(f"  [OK] 耗时 {time.time()-t0:.2f}s, 共 {n_chunks} 个 chunk")
        print(f"  拼接全文 = {full[:300]!r}")
        stream_ok = bool(full.strip())
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")

    # ---------- 结论 ----------
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print(f"  非流式可用 : {nonstream_ok}")
    print(f"  流式可用   : {stream_ok}")
    if nonstream_ok and not stream_ok:
        print("\n>>> 根因：gateway 的 SSE 流式响应无法被 OpenAI SDK 解析。")
        print(">>> 建议：process_input_stream 增加「流式为空则回退非流式」的兜底逻辑。")
    elif not nonstream_ok:
        print("\n>>> 根因：gateway 本身调用异常（非流式也不通），需检查 API Key/模型名/余额。")
    else:
        print("\n>>> 流式和非流式均正常，问题可能在别处（如 Prompt 构建/记忆检索）。")

    return 0 if stream_ok else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
