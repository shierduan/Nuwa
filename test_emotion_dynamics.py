#!/usr/bin/env python3
"""
情绪动力学回归测试 (Emotion Dynamics Regression)

锁定 v2 动力学语义，防止回归到"LLM 覆写情绪值"的旧行为：

1. 惯性：单次增量不会全额落地（可塑性 < 1.0）
2. 不可还原性：同样的增量，生理状态不同则落地不同
   - 高皮质醇 → 负面增量落地更多、正面增量被压制
   - 高催产素 → 信任/亲密增量更易被接受
3. 天性回归：无刺激时情绪向 baseline_mood 回落，而非拉平到 0.5
4. 压力地板：高皮质醇时负面情绪无法跌破生理基底
5. 持久化：神经递质跨序列化保留（重启不"换人"）
6. 累积性：同一增量反复施加，情绪单调变化并封顶

运行: python test_emotion_dynamics.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.nuwa_state import NuwaState
from nuwa_core.drive_system import BioRhythm

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def make_rhythm(**neuro) -> BioRhythm:
    state = NuwaState()
    rhythm = BioRhythm(state)
    for k, v in neuro.items():
        rhythm.neurotransmitters[k] = v
    return rhythm


def test_inertia():
    """单次增量不全量落地：可塑性默认 0.35"""
    print("\n--- 1. 惯性：事件是推力，不是传送 ---")
    r = make_rhythm()
    before = r.state.emotional_spectrum["anger"]
    after = r.apply_stimulus("anger", 1.0)
    moved = after - before
    check("单次增量只落地约 35%", 0.2 < moved < 0.5, f"moved={moved:.3f}")
    check("未被一次事件打满", after < 0.95, f"after={after:.3f}")


def test_irreducibility_negative():
    """高皮质醇 → 负面刺激落地更猛"""
    print("\n--- 2. 不可还原性：皮质醇放大负面刺激 ---")
    calm = make_rhythm(cortisol=0.0)
    stressed = make_rhythm(cortisol=0.9)

    calm_before = calm.state.emotional_spectrum["anger"]
    calm.apply_stimulus("anger", 0.8)
    calm_moved = calm.state.emotional_spectrum["anger"] - calm_before

    stressed_before = stressed.state.emotional_spectrum["anger"]
    stressed.apply_stimulus("anger", 0.8)
    stressed_moved = stressed.state.emotional_spectrum["anger"] - stressed_before

    check("高压下愤怒涨得更多", stressed_moved > calm_moved * 1.5,
          f"calm={calm_moved:.3f} stressed={stressed_moved:.3f}")


def test_irreducibility_positive():
    """高皮质醇 → 正面刺激被压制"""
    print("\n--- 3. 不可还原性：皮质醇压制正面刺激 ---")
    calm = make_rhythm(cortisol=0.0, dopamine=0.5)
    stressed = make_rhythm(cortisol=0.9, dopamine=0.5)

    calm_before = calm.state.emotional_spectrum["joy"]
    calm.apply_stimulus("joy", 0.9)
    calm_moved = calm.state.emotional_spectrum["joy"] - calm_before

    stressed_before = stressed.state.emotional_spectrum["joy"]
    stressed.apply_stimulus("joy", 0.9)
    stressed_moved = stressed.state.emotional_spectrum["joy"] - stressed_before

    check("高压下快乐涨幅被压制", stressed_moved < calm_moved * 0.6,
          f"calm={calm_moved:.3f} stressed={stressed_moved:.3f}")


def test_oxytocin_trust():
    """催产素促进信任/亲密建立"""
    print("\n--- 4. 依恋激素促进信任建立 ---")
    cold = make_rhythm(oxytocin=0.0)
    warm = make_rhythm(oxytocin=1.0)

    cold_before = cold.state.rapport
    cold.apply_stimulus("rapport", 0.8)
    cold_moved = cold.state.rapport - cold_before

    warm_before = warm.state.rapport
    warm.apply_stimulus("rapport", 0.8)
    warm_moved = warm.state.rapport - warm_before

    check("高催产素下亲密涨得更快", warm_moved > cold_moved * 1.5,
          f"cold={cold_moved:.3f} warm={warm_moved:.3f}")


def test_baseline_regression():
    """无刺激时向 baseline_mood 回归，而非拉平到 0.5"""
    print("\n--- 5. 天性回归：回到她自己，而非回到平静 ---")
    r = make_rhythm()
    r.state.emotional_spectrum["sadness"] = 0.9   # 远高于天性 0.1
    r.state.emotional_spectrum["joy"] = 0.0       # 远低于天性 0.6

    for _ in range(30):
        r.update(60.0)  # 累计 30 分钟

    sadness = r.state.emotional_spectrum["sadness"]
    joy = r.state.emotional_spectrum["joy"]
    check("悲伤向天性 0.1 回落（未拉平到 0.5）", sadness < 0.35, f"sadness={sadness:.3f}")
    check("快乐向天性 0.6 回升", joy > 0.3, f"joy={joy:.3f}")


def test_stress_floor():
    """高皮质醇时负面情绪有生理地板"""
    print("\n--- 6. 压力地板：坏心情的残留 ---")
    r = make_rhythm(cortisol=0.8)
    r.state.emotional_spectrum["anger"] = 0.0
    r.regulate(1.0)
    # 地板由本次调节时的皮质醇决定（代谢已先衰减一步），
    # 因此用调节后的激素值计算期望地板。
    floor = r.neurotransmitters["cortisol"] * 0.5
    check("愤怒被托到底板之上", r.state.emotional_spectrum["anger"] >= floor - 1e-9,
          f"anger={r.state.emotional_spectrum['anger']:.4f} floor={floor:.4f}")


def test_neuro_persistence():
    """神经递质跨序列化保留：重启不换人"""
    print("\n--- 7. 持久化：重启后还是同一个她 ---")
    state = NuwaState()
    rhythm = BioRhythm(state)
    rhythm.neurotransmitters["cortisol"] = 0.77
    rhythm.neurotransmitters["oxytocin"] = 0.42

    restored = NuwaState.from_dict(state.to_dict())
    check("皮质醇跨重启保留", abs(restored.neurotransmitters["cortisol"] - 0.77) < 1e-6,
          f"got={restored.neurotransmitters['cortisol']}")
    check("催产素跨重启保留", abs(restored.neurotransmitters["oxytocin"] - 0.42) < 1e-6,
          f"got={restored.neurotransmitters['oxytocin']}")

    # BioRhythm 复用已持久化的激素，而不是重置为出厂值
    rhythm2 = BioRhythm(restored)
    check("新 BioRhythm 继承持久化激素",
          abs(rhythm2.neurotransmitters["cortisol"] - 0.77) < 1e-6,
          f"got={rhythm2.neurotransmitters['cortisol']}")


def test_convergence():
    """同一增量反复施加，情绪单调变化并封顶"""
    print("\n--- 8. 累积性：重复推动逐渐生效并封顶 ---")
    r = make_rhythm()
    values = []
    for _ in range(12):
        r.apply_stimulus("trust", 0.9)
        values.append(r.state.emotional_spectrum["trust"])
    check("单调递增", all(b >= a - 1e-9 for a, b in zip(values, values[1:])),
          f"values={[round(v, 3) for v in values]}")
    check("多次后接近饱和", values[-1] > 0.75, f"final={values[-1]:.3f}")
    check("始终未越过 1.0", values[-1] <= 1.0 + 1e-9, f"final={values[-1]:.3f}")


def test_state_vector_unchanged():
    """13 维向量契约不变（设计哲学不动）"""
    print("\n--- 9. 13 维状态向量契约不变 ---")
    state = NuwaState()
    vec = state.to_vector()
    check("向量维度仍为 13", len(vec) == 13, f"dim={len(vec)}")


def main():
    print("=" * 60)
    print("情绪动力学回归测试 (Emotion Dynamics)")
    print("=" * 60)

    test_inertia()
    test_irreducibility_negative()
    test_irreducibility_positive()
    test_oxytocin_trust()
    test_baseline_regression()
    test_stress_floor()
    test_neuro_persistence()
    test_convergence()
    test_state_vector_unchanged()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"SUCCESS: {PASS}/{total} 项通过")
        print("=" * 60)
        return 0
    print(f"FAILED: {FAIL}/{total} 项失败")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
