"""
记忆巩固层验证：惊奇门控 / 情绪性衰减 / 分层巩固 / 再巩固
用法: python test_consolidation.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np

from nuwa_core.memory_cortex import MemoryCortex
from nuwa_core.memory_consolidation import (
    MemoryConsolidator,
    ConsolidationConfig,
    EmotionalDecay,
    SurprisalGate,
)


def main():
    print("=" * 60)
    print("记忆巩固层验证")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp(prefix="nuwa_consolid_"))
    failures = []
    try:
        mc = MemoryCortex("cons", data_dir=str(tmp))
        cfg = ConsolidationConfig(
            surprisal_threshold=0.80,
            min_cluster_size=2,
            min_insight_sources=2,
            half_life_days=7.0,
        )
        cons = MemoryConsolidator(mc, config=cfg)

        # ---- 1. 惊奇门控：寒暄被拒 ----
        ok, s, why = cons.gate.evaluate("好的")
        if ok:
            failures.append("寒暄 '好的' 应被门控拒绝")
        else:
            print(f"[1] 门控拒绝寒暄: OK ({why})")

        ok, s, why = cons.gate.evaluate("好的")
        if ok:
            failures.append("寒暄应被拒绝")
        print(f"[1] 门控拒绝寒暄: OK")

        # ---- 2. 惊奇门控：高信息量内容通过 ----
        rich = "用户提到他从小就不喜欢被叫全名，只希望被称呼小安，这是很重要的称呼偏好"
        ok, s, why = cons.gate.evaluate(rich)
        if not ok:
            failures.append(f"高信息量内容应通过门控，但被拒: {why}")
        else:
            print(f"[2] 门控放行高信息量内容: OK ({why})")

        # ---- 3. 门控去重：相同内容第二次应被拒 ----
        mc.store_memory(rich, metadata={"importance": 0.7})
        ok2, s2, why2 = cons.gate.evaluate(rich)
        if ok2:
            failures.append("重复内容应被门控拒绝")
        else:
            print(f"[3] 门控识别重复内容: OK ({why2})")

        # ---- 4. 情绪性衰减公式 ----
        decay = EmotionalDecay(cfg)
        base = {"importance": 0.5, "emotions": "{}", "timestamp": 1000, "access_count": 0}
        now = 1000 + 7 * 86400  # 恰好一个半衰期
        s_fresh = decay.score(base, now=1000)
        s_half = decay.score(base, now=now)
        ratio = s_half / max(s_fresh, 1e-9)
        if not (0.45 < ratio < 0.55):
            failures.append(f"半衰期公式错误，ratio={ratio:.3f}（应≈0.5）")
        else:
            print(f"[4] 半衰期衰减: OK (ratio={ratio:.3f})")

        # 情绪加权：同样的记忆，有情绪的应得分更高
        emotional = dict(base)
        emotional["emotions"] = '{"joy": 0.9, "trust": 0.8}'
        s_emo = decay.score(emotional, now=1000)
        if s_emo <= s_fresh:
            failures.append(f"情绪加权未生效: {s_emo:.4f} <= {s_fresh:.4f}")
        else:
            print(f"[5] 情绪加权: OK ({s_fresh:.4f} -> {s_emo:.4f})")

        # ---- 6. 访问频率加成 ----
        freq_mem = dict(base)
        freq_mem["access_count"] = 20
        s_freq = decay.score(freq_mem, now=1000)
        if s_freq <= s_fresh:
            failures.append("访问频率加成未生效")
        else:
            print(f"[6] 频率加成: OK ({s_fresh:.4f} -> {s_freq:.4f})")

        # ---- 7. 巩固层写入（走门控）----
        # 注意：rich 已在步骤 3 直接写入库中，这里再次写入应被门控拒绝
        dup_id = cons.store(rich, metadata={"type": "dialogue", "importance": 0.7})
        if dup_id is not None:
            failures.append("重复内容应被门控拒绝（返回 None）")
        else:
            print("[7] 门控在巩固层写入路径生效: OK")

        # 全新内容应写入成功
        fresh = "用户说自己准备换工作，想先休息两个月调整状态，这是重要的人生决定"
        fresh_id = cons.store(fresh, metadata={"type": "dialogue", "importance": 0.7})
        if fresh_id is None:
            failures.append("全新内容应写入成功")
        else:
            print("[7] 巩固层写入新内容: OK")

        short_id = cons.store("嗯嗯", metadata={"type": "dialogue"})
        if short_id is not None:
            failures.append("短文本应被门控拒绝")
        else:
            print("[7] 巩固层写入走门控: OK")

        # ---- 8. 再巩固：标记召回 ----
        cons.mark_recalled(["m1", "m2"])
        if len(cons.book.labile) != 2:
            failures.append("再巩固账本未记录召回")
        elif not cons.book.is_labile("m1", 300):
            failures.append("is_labile 判断错误")
        else:
            print("[8] 再巩固账本: OK")

        # 窗口过期
        expired = cons.book.expire(window=-1)  # 负窗口 → 全部过期
        if len(expired) != 2:
            failures.append(f"窗口过期逻辑错误: {len(expired)}")
        else:
            print("[9] 可塑性窗口过期: OK")

        # ---- 10. 巩固周期（含 L1 摘要）----
        # 写入一组语义相近的记忆（无 LLM 时会退化为首条截断，仍应能生成摘要条目）
        for i in range(4):
            mc.store_memory(
                f"我们讨论了银月湖畔的项目进度，第{i + 1}次跟进细节",
                metadata={"type": "raw", "importance": 0.6,
                          "emotions": '{"joy": 0.5, "trust": 0.6}'},
            )
        report = cons.consolidate_cycle()
        print(f"[10] 巩固周期报告: {report}")
        summaries = mc.get_recent_memories(limit=50, memory_type="summary")
        if not summaries:
            failures.append("未生成 L1 摘要")
        else:
            # 回归检查：摘要文本不应出现双重时间戳前缀
            s_text = summaries[0].get("text", "")
            if s_text.count("[") > 1:
                failures.append(f"摘要文本出现双重时间戳前缀: {s_text[:60]}")
            else:
                print(f"[10] L1 摘要无双重时间戳: OK ({s_text[:50]}...)")
            print(f"[10] L1 摘要生成: OK ({len(summaries)} 条)")

        # ---- 11. 统计 ----
        st = cons.get_stats()
        print(f"[11] 统计: writes={st['writes_total']}, rejected={st['writes_rejected']}, "
              f"summaries={st['summaries_created']}, labile={st['labile_count']}")
        if st["writes_rejected"] < 1:
            failures.append("门控拒绝计数未累加")

        print()
        if failures:
            print("[FAIL] 存在问题：")
            for f in failures:
                print("  -", f)
            return 1
        print("[SUCCESS] 记忆巩固层全部验证通过")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
