"""
梦境全流程验证（使用 Mock LLM，不依赖外部 API）：
巩固周期 → L1 摘要 → L2 洞察 → 事实账本写入 → 情绪性衰减遗忘
用法: python test_dream_e2e.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

from nuwa_core.memory_cortex import MemoryCortex
from nuwa_core.memory_consolidation import MemoryConsolidator, ConsolidationConfig
from nuwa_core.nuwa_state import NuwaState


class MockLLM:
    """Mock LLM：按提示词内容返回对应的 JSON"""

    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model=None, messages=None, temperature=None, max_tokens=None, **kw):
        self.calls.append(messages)
        user_msg = messages[-1]["content"] if messages else ""

        if '"insight"' in user_msg:
            payload = {
                "insight": "用户处于职业转换期，情绪上偏向谨慎与期待，沟通中反复确认细节。",
                "facts": {"user_career_stage": "考虑换工作", "interaction_style": "注重细节确认"},
            }
        else:
            payload = {
                "summary": "用户提到自己在准备换工作，想先休息两个月调整状态。",
                "facts": {"user_name": "小安", "user_preference": "被称呼小安"},
            }
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False)))]
        )


def main():
    print("=" * 60)
    print("梦境全流程验证（Mock LLM）")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp(prefix="nuwa_dream_"))
    failures = []
    try:
        state = NuwaState()
        mc = MemoryCortex("dream", data_dir=str(tmp))
        llm = MockLLM()
        cfg = ConsolidationConfig(
            surprisal_threshold=0.85,
            min_cluster_size=2,
            min_insight_sources=2,
            forget_threshold=0.15,
        )
        cons = MemoryConsolidator(mc, llm_client=llm, state_ref=state, config=cfg)

        # ---- 1. 写入一组同主题记忆 ----
        topic_texts = [
            "用户说他在考虑换工作，公司最近不太顺利，想先休息一下",
            "用户提到换工作的事情还在犹豫，担心休息两个月会影响 career",
            "用户说如果真的换工作，希望能看到自己的成长而不是一直重复",
        ]
        for t in topic_texts:
            mc.store_memory(t, metadata={
                "type": "raw", "importance": 0.7,
                "emotions": '{"sadness": 0.4, "anticipation": 0.6, "trust": 0.5}',
            })
        print(f"[1] 写入 {len(topic_texts)} 条同主题记忆")

        # ---- 2. 第一轮巩固：生成 L1 摘要 ----
        report1 = cons.consolidate_cycle()
        print(f"[2] 第一轮巩固: {report1}")
        if report1["summaries"] < 1:
            failures.append("第一轮未生成 L1 摘要")
        else:
            print("[2] L1 摘要生成: OK")

        summaries = mc.get_recent_memories(limit=50, memory_type="summary")
        if summaries:
            s_text = summaries[0]["text"]
            if s_text.count("[") > 1:
                failures.append(f"摘要双重时间戳: {s_text[:60]}")
            print(f"[2] 摘要内容: {s_text[:70]}...")

        # ---- 3. 第二轮巩固：生成 L2 洞察 ----
        # 需先有 >=2 条摘要
        mc.store_memory("用户还在纠结要不要休息，认为停下来就会失去节奏",
                        metadata={"type": "summary", "importance": 0.8,
                                  "emotions": '{"sadness": 0.3, "trust": 0.4}'})
        report2 = cons.consolidate_cycle()
        print(f"[3] 第二轮巩固: {report2}")
        if report2["insights"] < 1:
            failures.append("第二轮未生成 L2 洞察")
        else:
            print("[3] L2 洞察生成: OK")

        insights = mc.get_recent_memories(limit=50, memory_type="insight")
        if insights:
            print(f"[3] 洞察内容: {insights[0]['text'][:80]}")

        # ---- 4. 事实账本写入 ----
        facts = state.fact_book
        print(f"[4] 事实账本: {facts}")
        if not facts:
            failures.append("事实账本未写入任何事实")
        else:
            print("[4] 事实账本写入: OK")

        # ---- 5. 情绪性衰减：低分记忆被遗忘 ----
        # 写入一条无情绪、无重要性、很旧的记忆
        old_ts = 1000.0
        mc.store_memory("一条很久以前的无关紧要的内容，用来测试遗忘机制是否生效",
                        metadata={"type": "raw", "importance": 0.0, "emotions": "{}"},
                        timestamp=__import__("datetime").datetime.fromtimestamp(old_ts))
        before = mc.get_stats().get("count", 0)
        report3 = cons.consolidate_cycle()
        after = mc.get_stats().get("count", 0)
        print(f"[5] 遗忘周期: before={before}, after={after}, report={report3}")
        if report3["forgotten"] < 1:
            failures.append("低价值记忆未被遗忘")
        else:
            print("[5] 情绪性衰减遗忘: OK")

        # ---- 6. 统计 ----
        st = cons.get_stats()
        print(f"[6] 统计: {st}")
        if st["summaries_created"] < 1 or st["insights_created"] < 1:
            failures.append("统计计数不正确")

        # ---- 7. 去重回归：再跑一轮不应新增摘要/洞察 ----
        summaries_before = len(mc.get_recent_memories(limit=100, memory_type="summary"))
        insights_before = len(mc.get_recent_memories(limit=100, memory_type="insight"))
        cons.consolidate_cycle()
        summaries_after = len(mc.get_recent_memories(limit=100, memory_type="summary"))
        insights_after = len(mc.get_recent_memories(limit=100, memory_type="insight"))
        if summaries_after != summaries_before:
            failures.append(
                f"去重失效：摘要数 {summaries_before} -> {summaries_after}"
            )
        else:
            print(f"[7] 摘要去重: OK (仍为 {summaries_after} 条)")
        if insights_after != insights_before:
            failures.append(
                f"去重失效：洞察数 {insights_before} -> {insights_after}"
            )
        else:
            print(f"[7] 洞察去重: OK (仍为 {insights_after} 条)")

        print()
        if failures:
            print("[FAIL] 存在问题：")
            for f in failures:
                print("  -", f)
            return 1
        print("[SUCCESS] 梦境全流程验证通过")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
