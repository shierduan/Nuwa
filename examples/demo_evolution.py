"""
强化学习自我进化演示

展示SelfEvolutionRL的核心功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.self_evolution_rl import Interaction, SelfEvolutionRL
from nuwa_core.nuwa_state import NuwaState


class MockStateManager:
    """模拟状态管理器"""
    def __init__(self):
        self.state = NuwaState()
        # 设置初始状态
        self.state.energy = 0.7
        self.state.system_entropy = 0.3
        self.state.rapport = 0.5
        self.state.emotional_spectrum["joy"] = 0.6
        self.state.emotional_spectrum["sadness"] = 0.4
        self.state.emotional_spectrum["fear"] = 0.3
        self.state.drives["social_hunger"] = 0.5
        self.state.drives["curiosity"] = 0.7
    
    def get_state(self):
        return self.state
    
    def update_state(self, delta):
        for key, value in delta.items():
            if key in self.state.drives:
                self.state.drives[key] = max(0.0, min(1.0, self.state.drives[key] + value))
            elif key in self.state.emotional_spectrum:
                self.state.emotional_spectrum[key] = max(0.0, min(1.0, self.state.emotional_spectrum[key] + value))
            elif hasattr(self.state, key):
                current = getattr(self.state, key)
                setattr(self.state, key, max(0.0, min(1.0, current + value)))
        
        print(f"   📊 状态更新: {delta}")


class MockMemoryCortex:
    """模拟记忆皮层"""
    def get_index_info(self):
        return {"count": 50}


class MockLLMClient:
    """模拟LLM客户端"""
    pass


async def demo_evolution():
    """演示强化学习自我进化"""
    print("="*70)
    print("🚀 强化学习自我进化演示")
    print("="*70)
    
    # 1. 初始化系统
    print("\n1️⃣ 初始化系统...")
    state_manager = MockStateManager()
    memory_cortex = MockMemoryCortex()
    llm_client = MockLLMClient()
    
    # 创建RL进化器（降低阈值用于演示）
    config = {
        "experience_threshold": 5,  # 演示用，降低阈值
        "enable_debug": True,
    }
    
    evolution = SelfEvolutionRL(state_manager, memory_cortex, llm_client, config)
    
    print("   ✅ 强化学习进化器已初始化")
    print(f"   状态维度: {evolution.config['state_dim']}")
    print(f"   动作维度: {evolution.config['action_dim']}")
    print(f"   训练阈值: {evolution.config['experience_threshold']}")
    
    # 2. 模拟交互历史
    print("\n2️⃣ 模拟用户交互...")
    
    # 创建一组交互，模拟用户满意度逐渐提高的过程
    interactions = []
    
    # 负面交互 (奖励低)
    interactions.append(Interaction(
        user_input="你好",
        ai_response="嗨",
        user_satisfaction=0.3,
        quality_score=0.4,
        emotional_stability=0.5
    ))
    
    # 普通交互
    interactions.append(Interaction(
        user_input="今天天气怎么样？",
        ai_response="我不知道，但希望是晴天",
        user_satisfaction=0.5,
        quality_score=0.5,
        emotional_stability=0.6
    ))
    
    # 良好交互
    interactions.append(Interaction(
        user_input="推荐一本科幻小说",
        ai_response="我推荐《三体》，很有深度",
        user_satisfaction=0.7,
        quality_score=0.8,
        emotional_stability=0.7
    ))
    
    # 优秀交互
    interactions.append(Interaction(
        user_input="我喜欢你的回答风格",
        ai_response="谢谢！我会继续保持真诚",
        user_satisfaction=0.9,
        quality_score=0.85,
        emotional_stability=0.9
    ))
    
    # 完美交互
    interactions.append(Interaction(
        user_input="你真是个好朋友",
        ai_response="你也是，我很珍惜我们的对话",
        user_satisfaction=0.95,
        quality_score=0.9,
        emotional_stability=0.95
    ))
    
    print("   创建交互历史:")
    for i, inter in enumerate(interactions):
        reward = evolution.calculate_reward(inter)
        print(f"     {i+1}. 满意度: {inter.user_satisfaction:.1f}, 奖励: {reward:.3f}")
    
    # 3. 执行进化
    print("\n3️⃣ 执行自我进化...")
    result = await evolution.evolve(interactions)
    
    print(f"   ✅ 进化完成")
    print(f"   - 进化次数: {result.get('evolution_count', 0)}")
    print(f"   - 经验缓冲区: {result.get('buffer_size', 0)}")
    print(f"   - 平均奖励: {result.get('avg_reward', 0):.3f}")
    print(f"   - 训练状态: {result.get('trained', False)}")
    
    # 4. 查看训练结果
    print("\n4️⃣ 训练策略...")
    if evolution.replay_buffer.is_ready():
        training_result = await evolution.train_evolution_policy()
        print(f"   ✅ 训练完成")
        print(f"   - 训练步骤: {training_result.get('training_steps', 0)}")
        print(f"   - 最终损失: {training_result.get('final_loss', 0):.6f}")
    else:
        print(f"   ⚠️ 经验不足 (需要 {evolution.config['experience_threshold']} 条)")
    
    # 5. 获取进化状态总结
    print("\n5️⃣ 进化状态总结...")
    summary = evolution.get_evolution_summary()
    for key, value in summary.items():
        print(f"   - {key}: {value}")
    
    # 6. 应用进化效果
    print("\n6️⃣ 应用进化...")
    apply_result = await evolution.apply_evolution()
    
    if apply_result and apply_result.get("applied"):
        action_idx = apply_result.get("action_idx")
        param = apply_result.get("param")
        effect = apply_result.get("effect")
        print(f"   ✅ 应用动作 {action_idx}: {param} = {effect:+.3f}")
        
        # 显示动作详情
        action_space = evolution.get_action_space()
        action_detail = action_space[action_idx]
        print(f"   🎯 动作描述: {action_detail['desc']}")
        print(f"   💡 预期效果: {action_detail['effect']:+.2f}")
    else:
        print(f"   ⚠️ 未应用进化: {apply_result}")
    
    # 7. 显示状态变化
    print("\n7️⃣ 状态变化对比...")
    state_before = evolution.get_state_vector()
    print(f"   进化前状态向量: {state_before[:5]}... (前5维)")
    
    # 模拟应用进化后的状态
    if apply_result and apply_result.get("applied"):
        param = apply_result.get("param")
        effect = apply_result.get("effect")
        
        # 手动更新状态以显示效果
        if param in evolution.state_manager.get_state().emotional_spectrum:
            evolution.state_manager.update_state({param: effect})
        elif param in evolution.state_manager.get_state().drives:
            evolution.state_manager.update_state({param: effect})
        else:
            evolution.state_manager.update_state({param: effect})
    
    state_after = evolution.get_state_vector()
    print(f"   进化后状态向量: {state_after[:5]}... (前5维)")
    
    # 计算变化量
    changes = state_after - state_before
    print(f"   状态变化量: {changes[:5]}... (前5维)")
    print(f"   总变化幅度: {abs(changes).sum():.3f}")
    
    # 8. 演示动作空间
    print("\n8️⃣ 动作空间概览...")
    action_space = evolution.get_action_space()
    print("   可调整参数:")
    for i, action in enumerate(action_space):
        if i % 3 == 0:
            print()
        print(f"     {i:2d}: {action['param']:12s} ({action['effect']:+.2f})", end="  ")
    
    print("\n" + "="*70)
    print("✅ 演示完成！")
    print("="*70)
    
    print("\n💡 关键要点:")
    print("   1. RL系统基于交互奖励自动调整人格参数")
    print("   2. Q网络学习最优进化策略")
    print("   3. 经验回放确保训练稳定性")
    print("   4. 可与现有KernelDI系统无缝集成")
    print("   5. 支持PyTorch和NumPy双模式")


async def demo_reward_calculation():
    """演示奖励计算"""
    print("\n" + "="*70)
    print("💰 奖励计算演示")
    print("="*70)
    
    # 模拟依赖
    state_manager = MockStateManager()
    memory_cortex = MockMemoryCortex()
    llm_client = MockLLMClient()
    
    evolution = SelfEvolutionRL(state_manager, memory_cortex, llm_client)
    
    # 测试不同场景
    scenarios = [
        {
            "name": "完美对话",
            "user": 0.95, "quality": 0.9, "stability": 0.95,
            "desc": "用户非常满意，对话质量高，情绪稳定"
        },
        {
            "name": "良好对话",
            "user": 0.8, "quality": 0.75, "stability": 0.85,
            "desc": "用户满意，对话质量较好"
        },
        {
            "name": "普通对话",
            "user": 0.6, "quality": 0.6, "stability": 0.7,
            "desc": "基本满足需求，没有明显问题"
        },
        {
            "name": "负面对话",
            "user": 0.2, "quality": 0.3, "stability": 0.4,
            "desc": "用户不满意，对话质量差"
        },
        {
            "name": "混合表现",
            "user": 0.7, "quality": 0.4, "stability": 0.8,
            "desc": "用户满意但对话质量一般"
        },
    ]
    
    print("\n不同场景的奖励计算:")
    print(f"{'场景':<12} {'用户满意度':<12} {'对话质量':<10} {'情绪稳定':<10} {'奖励':<8} {'评价'}")
    print("-" * 80)
    
    for scenario in scenarios:
        interaction = Interaction(
            user_input="test",
            ai_response="test",
            user_satisfaction=scenario["user"],
            quality_score=scenario["quality"],
            emotional_stability=scenario["stability"]
        )
        
        reward = evolution.calculate_reward(interaction)
        
        # 评价
        if reward >= 0.9:
            rating = "优秀"
        elif reward >= 0.7:
            rating = "良好"
        elif reward >= 0.5:
            rating = "普通"
        else:
            rating = "负面"
        
        print(f"{scenario['name']:<12} {scenario['user']:<12.2f} {scenario['quality']:<10.2f} "
              f"{scenario['stability']:<10.2f} {reward:<8.3f} {rating}")
    
    print("\n奖励计算公式: (用户满意度 + 对话质量 + 情绪稳定性) / 3")


async def main():
    """运行演示"""
    try:
        await demo_evolution()
        await demo_reward_calculation()
        
        print("\n🎉 所有演示完成！")
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())