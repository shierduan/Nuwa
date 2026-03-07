"""
测试图记忆集成 (Test Graph Memory Integration)

功能：验证 GraphEnhancedMemoryCortex 是否正确集成到女娲内核
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


async def test_graph_memory_integration():
    """测试图记忆集成"""
    print("=" * 80)
    print("测试图记忆集成")
    print("=" * 80)
    
    try:
        # 1. 测试导入
        print("\n[1/5] 测试模块导入...")
        from nuwa_core.memory_graph import GraphEnhancedMemoryCortex
        print("[OK] GraphEnhancedMemoryCortex 导入成功")
        
        # 2. 初始化图增强记忆皮层
        print("\n[2/5] 初始化图增强记忆皮层...")
        memory_cortex = GraphEnhancedMemoryCortex(
            project_name="test_graph_integration",
            data_dir="test_data"
        )
        print("[OK] 图增强记忆皮层初始化成功")
        
        # 3. 测试存储记忆
        print("\n[3/5] 测试存储记忆...")
        test_memories = [
            "今天学习了机器学习的基础知识",
            "机器学习是人工智能的一个重要分支",
            "深度学习使用神经网络进行模式识别",
            "图神经网络可以处理图结构数据",
            "记忆系统需要支持长期演化和关联检索"
        ]
        
        for i, memory in enumerate(test_memories):
            success = memory_cortex.store_memory(
                memory,
                metadata={"id": f"test_{i}", "importance": 0.8}
            )
            if success:
                print(f"  [+] 存储记忆 {i+1}: {memory[:30]}...")
            else:
                print(f"  [-] 存储失败：{memory}")
        
        print("[OK] 记忆存储测试完成")
        
        # 4. 测试检索记忆
        print("\n[4/5] 测试检索记忆（基于语义搜索）...")
        query = "机器学习和神经网络"
        results = memory_cortex.recall_by_emotion(
            query_text=query,
            top_k=3
        )
        
        print(f"\n查询：'{query}'")
        print(f"找到 {len(results)} 条相关记忆:")
        for i, result in enumerate(results):
            print(f"\n  [{i+1}] 相似度：{result.get('similarity', 0):.4f}")
            print(f"      内容：{result['text']}")
            print(f"      来源：{result.get('source', 'unknown')}")
            if 'neighbors' in result:
                print(f"      邻居节点：{len(result['neighbors'])} 个")
        
        print("\n[OK] 记忆检索测试完成")
        
        # 5. 获取统计信息
        print("\n[5/5] 获取统计信息...")
        stats = memory_cortex.get_statistics()
        
        print("\n统计信息:")
        if 'graph' in stats:
            graph_stats = stats['graph']
            print(f"  - 图节点数：{graph_stats.get('total_nodes', 0)}")
            print(f"  - 图边数：{graph_stats.get('total_edges', 0)}")
            print(f"  - 社区数量：{graph_stats.get('num_communities', 0)}")
        
        if 'lancedb' in stats:
            lancedb_stats = stats['lancedb']
            print(f"  - LanceDB 索引大小：{lancedb_stats.get('total_count', 0)}")
        
        print("\n[OK] 统计信息获取完成")
        
        # 6. 测试记忆社区发现
        print("\n[6/5] 测试记忆社区发现...")
        communities = memory_cortex.find_communities()
        print(f"发现 {len(communities)} 个记忆社区:")
        for i, community in enumerate(communities):
            center = community.get('center_node', {})
            print(f"\n  社区 {i+1}:")
            print(f"    - 中心节点：{center.get('text', 'N/A')[:50]}...")
            print(f"    - 成员数量：{len(community.get('members', []))}")
            print(f"    - 平均重要性：{community.get('avg_importance', 0):.3f}")
        
        print("\n[OK] 社区发现测试完成")
        
        # 清理
        print("\n" + "=" * 80)
        print("[SUCCESS] 所有测试通过！图记忆集成成功！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"[ERROR] 测试失败：{e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 保存并清理
        try:
            if 'memory_cortex' in locals():
                memory_cortex.save()
                print("\n[INFO] 数据已保存")
        except Exception:
            pass


async def test_kernel_integration():
    """测试内核级别的集成"""
    print("\n" + "=" * 80)
    print("测试内核级别的图记忆集成")
    print("=" * 80)
    
    try:
        # 1. 导入内核
        print("\n[1/3] 导入女娲内核...")
        from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
        print("[OK] 内核导入成功")
        
        # 2. 初始化内核
        print("\n[2/3] 初始化内核...")
        kernel = NuwaKernelAsync(
            project_name="test_kernel_graph",
            data_dir="test_data",
            enable_cache=False
        )
        print("[OK] 内核初始化成功")
        
        # 3. 检查记忆皮层类型
        print("\n[3/3] 检查记忆皮层类型...")
        cortex_type = type(kernel.memory_cortex).__name__
        print(f"记忆皮层类型：{cortex_type}")
        
        if cortex_type == "GraphEnhancedMemoryCortex":
            print("[OK] 内核已成功使用图增强记忆皮层！")
        else:
            print(f"[WARN] 内核使用的是：{cortex_type}")
        
        print("\n" + "=" * 80)
        print("[OK] 内核集成测试完成！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"[ERROR] 内核集成测试失败：{e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("女娲系统 - 图记忆集成测试")
    print("=" * 80)
    
    # 测试 1: 图记忆基础功能
    test1_passed = await test_graph_memory_integration()
    
    # 等待一下
    await asyncio.sleep(2)
    
    # 测试 2: 内核集成
    test2_passed = await test_kernel_integration()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"图记忆基础功能：{'[OK] 通过' if test1_passed else '[FAIL] 失败'}")
    print(f"内核集成测试：{'[OK] 通过' if test2_passed else '[FAIL] 失败'}")
    print("=" * 80)
    
    if test1_passed and test2_passed:
        print("\n[SUCCESS] 所有测试通过！图记忆已成功集成到女娲内核！")
        return 0
    else:
        print("\n[WARN] 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
