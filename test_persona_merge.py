#!/usr/bin/env python3
"""
人格演化双轨合并测试 (Persona Track Merge)

锁定 _get_evolved_persona_block 的合并行为：

轨 A（梦境）：MemoryDreamer.evolve_character 写入 state.evolved_persona
轨 B（自演化）：SelfEvolutionState.state

规则：
1. 梦境轨有数据的层，优先进入 prompt
2. 梦境轨为空的层，回退到自演化轨
3. 两层都空 → 返回空串（新用户无侵入）
4. 权重短键（short_term）与全名（short_term_vibe）都兼容

运行: python test_persona_merge.py
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.nuwa_state import NuwaState
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync as NuwaKernel

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


def make_kernel(dream_layers: dict, evo_layers: dict) -> NuwaKernel:
    """绕过 __init__ 与单例文件锁的轻量内核：只挂 state 与 evolution_state"""
    kernel = object.__new__(NuwaKernel)
    kernel.state = NuwaState()
    for k, v in dream_layers.items():
        kernel.state.evolved_persona[k] = v
    kernel.evolution_state = types.SimpleNamespace(state=dict(evo_layers))
    # _build_prompt 需要的最小属性集（其余路径在空数据下不触达）
    kernel.skills_enabled = False
    return kernel


def test_dream_track_wins():
    print("\n--- 1. 梦境轨优先 ---")
    k = make_kernel(
        dream_layers={"short_term_vibe": "用户今天很兴奋，在聊新项目"},
        evo_layers={"short_term_vibe": "自演化轨的旧描述"},
    )
    block = k._get_evolved_persona_block()
    check("梦境轨内容进入 prompt", "用户今天很兴奋，在聊新项目" in block, block[:120])
    check("自演化轨同层内容被覆盖", "自演化轨的旧描述" not in block)


def test_fallback_to_evo():
    print("\n--- 2. 梦境空层回退自演化轨 ---")
    k = make_kernel(
        dream_layers={},
        evo_layers={"recent_habits": "用户习惯深夜写代码"},
    )
    block = k._get_evolved_persona_block()
    check("回退内容进入 prompt", "用户习惯深夜写代码" in block, block[:120])


def test_layer_merge():
    print("\n--- 3. 逐层合并（两轨互补）---")
    k = make_kernel(
        dream_layers={"short_term_vibe": "今天心情不错"},
        evo_layers={"core_bond": "三年一起 Debug 的战友情"},
    )
    block = k._get_evolved_persona_block()
    check("梦境层在场", "今天心情不错" in block)
    check("自演化层在场", "三年一起 Debug 的战友情" in block)
    check("XML 结构完整", block.startswith("<evolved_personality>") and "</evolved_personality>" in block)


def test_both_empty():
    print("\n--- 4. 两层都空 → 无侵入 ---")
    k = make_kernel(dream_layers={}, evo_layers={})
    block = k._get_evolved_persona_block()
    check("返回空串", block == "", repr(block[:80]))


def test_weight_keys():
    print("\n--- 5. 权重双键兼容 ---")
    # 梦境轨用短键
    k1 = make_kernel(
        dream_layers={
            "short_term_vibe": "测试A",
            "weights": {"short_term": 1.0},
        },
        evo_layers={},
    )
    b1 = k1._get_evolved_persona_block()
    check("短键权重生效", "Weight 1.0" in b1, b1[:120])

    # 自演化轨用全名（回退路径）
    k2 = make_kernel(
        dream_layers={},
        evo_layers={
            "short_term_vibe": "测试B",
            "weights": {"short_term_vibe": 0.9},
        },
    )
    b2 = k2._get_evolved_persona_block()
    check("全名权重生效", "Weight 0.9" in b2, b2[:120])

    # 无权重时用默认
    k3 = make_kernel(
        dream_layers={"core_bond": "测试C"},
        evo_layers={},
    )
    b3 = k3._get_evolved_persona_block()
    check("默认权重 0.2", "Weight 0.2" in b3, b3[:120])


def test_prompt_injection():
    print("\n--- 6. _build_prompt 实际注入 ---")
    k = make_kernel(
        dream_layers={"recent_habits": "用户最近总在深夜出现"},
        evo_layers={},
    )
    # _build_prompt 只用到 _get_evolved_persona_block 与若干属性，
    # 其余路径（技能/记忆）在空数据下安全降级
    messages = k._build_prompt("你好", [], None)
    system_content = messages[0]["content"]
    check("system prompt 含演化人格", "用户最近总在深夜出现" in system_content)
    check("用户输入原样传递", messages[-1]["content"] == "你好")


def main():
    print("=" * 60)
    print("人格演化双轨合并测试 (Persona Track Merge)")
    print("=" * 60)

    test_dream_track_wins()
    test_fallback_to_evo()
    test_layer_merge()
    test_both_empty()
    test_weight_keys()
    test_prompt_injection()

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
