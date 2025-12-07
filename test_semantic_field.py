#!/usr/bin/env python3
"""
测试语义场论分析功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.nuwa_kernel import NuwaKernel


def test_semantic_field_analysis():
    """测试语义场论分析功能"""
    print("=== 测试语义场论分析功能 ===")
    
    # 初始化 NuwaKernel
    kernel = NuwaKernel(
        project_name="nuwa",
        data_dir="data",
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        model_name="local-model",
        on_message_callback=None
    )
    
    print("✅ NuwaKernel 初始化完成")
    
    # 测试语义场论分析
    user_input = "你好，我是十二"
    reply = "你好，十二！很高兴认识你。"
    
    print(f"\n测试数据：")
    print(f"用户输入: {user_input}")
    print(f"女娲回复: {reply}")
    
    try:
        # 直接调用语义场论分析方法
        result = kernel._analyze_semantic_evolution(user_input, reply)
        
        print(f"\n✅ 语义场论分析成功！")
        print(f"结果: {result}")
        
        # 检查关键指标
        if result.get("analysis_available"):
            print(f"\n🎉 分析可用: 是")
            print(f"   总能量: {result.get('total_energy'):.4f}")
            print(f"   人设一致性: {result.get('character_consistency'):.4f}")
            print(f"   因果连贯性: {result.get('causal_coherence'):.4f}")
            print(f"   能量分解: {result.get('energy_breakdown')}")
            return True
        else:
            print(f"\n⚠️  分析不可用")
            return False
            
    except Exception as e:
        print(f"\n❌ 语义场论分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_semantic_field_analysis()
    if success:
        print("\n🎉 所有测试通过！语义场论分析功能正常工作。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！语义场论分析功能仍有问题。")
        sys.exit(1)
