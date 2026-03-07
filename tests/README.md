# 测试文档

## 📋 测试概览

本项目包含完整的测试体系，目标覆盖率 **90%+**。

## 📁 目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_semantic_field.py      # 语义场论
│   ├── test_adaptive_pid.py        # 自适应PID
│   └── test_kernels.py             # 核心内核
├── integration/             # 集成测试
│   ├── test_full_system.py         # 完整系统
│   └── test_riemannian_integration.py  # 黎曼几何集成
├── performance/             # 性能测试
│   └── test_benchmark.py           # 基准测试
├── fixtures/                # 测试工具
│   ├── test_helpers.py             # 辅助函数
│   └── __init__.py                 # 包初始化
├── test_monitoring_integration.py # 监控集成测试
└── __init__.py              # 包初始化
```

## 🎯 测试类型

### 1. 单元测试 (Unit Tests)
**目标**: 90%+ 覆盖率

**测试内容**:
- 黎曼几何语义场的数学正确性
- 自适应PID控制器的功能完整性
- 核心内核组件的独立功能

**运行**:
```bash
pytest tests/unit/ -v --cov=nuwa_core
```

### 2. 集成测试 (Integration Tests)
**目标**: 验证模块间协作

**测试内容**:
- 记忆 → PID控制流程
- 语义场与记忆系统集成
- 自我进化与系统集成
- 多模态融合

**运行**:
```bash
pytest tests/integration/ -v
```

### 3. 性能测试 (Performance Tests)
**目标**: 基准和压力测试

**测试内容**:
- 响应时间分布 (Histogram)
- LLM调用成功率 (Counter)
- 记忆检索效率 (Gauge)
- 内存使用趋势 (Gauge)
- 情感状态分布 (Gauge)
- 高负载压力测试

**运行**:
```bash
pytest tests/performance/ -v -s
```

### 4. 监控集成测试
**目标**: 验证指标收集

**测试内容**:
- 指标收集器集成
- 装饰器功能
- 并发安全
- Prometheus导出

**运行**:
```bash
pytest tests/test_monitoring_integration.py -v
```

## 🚀 快速开始

### 环境准备
```bash
# 安装测试依赖
pip install pytest pytest-cov pytest-asyncio

# 安装监控依赖（可选）
pip install prometheus-client psutil
```

### 运行所有测试
```bash
# 基本运行
pytest tests/ -v

# 显示覆盖率
pytest tests/ -v --cov=nuwa_core --cov-report=html

# 并行运行（加速）
pytest tests/ -v -n auto
```

### 运行特定测试
```bash
# 单个测试文件
pytest tests/unit/test_semantic_field.py -v

# 单个测试类
pytest tests/unit/test_semantic_field.py::TestRigorousSemanticField -v

# 单个测试方法
pytest tests/unit/test_semantic_field.py::TestRigorousSemanticField::test_evolution -v

# 按标签运行
pytest tests/ -v -k "evolution"  # 运行包含evolution的测试
```

## 📊 测试覆盖目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|-----------|----------|
| 语义场论 | 95% | ✅ |
| 自适应PID | 90% | ✅ |
| 核心内核 | 90% | ✅ |
| 监控系统 | 85% | ✅ |
| 集成测试 | 80% | ✅ |
| 性能测试 | 基准 | ✅ |

## 🧪 测试工具

### MockEmbeddingModel
```python
from tests.fixtures import MockEmbeddingModel

model = MockEmbeddingModel(dim=384)
vector = model.encode("测试文本")
```

### TestDataGenerator
```python
from tests.fixtures import TestDataGenerator

states = TestDataGenerator.generate_state(10)
vectors = TestDataGenerator.generate_vector(384)
memories = TestDataGenerator.generate_memory_data(20)
```

### TestMetricsCollector
```python
from tests.fixtures import TestMetricsCollector

collector = TestMetricsCollector()
collector.record("metric_name", 1.5)
stats = collector.get_statistics("metric_name")
```

### RiemannianTestHelper
```python
from tests.fixtures import RiemannianTestHelper

field = RiemannianTestHelper.create_test_field(384)
results = RiemannianTestHelper.verify_field_properties(field, test_vector)
```

## 🔍 测试示例

### 语义场测试
```python
def test_evolution_convergence():
    core = np.array([0.8, 0.6, 0.4, 0.2])
    field = RigorousSemanticField(core_vector=core)
    
    initial = np.array([0.5, 0.8, 0.2, 0.6])
    evolved, info = field.evolve(initial, dt=0.02, iterations=20)
    
    # 能量应该降低
    assert info['final_energy'] <= info['initial_energy']
```

### PID控制器测试
```python
def test_adaptive_update():
    controller = create_adaptive_controller()
    state = NuwaState(0.5, 0.6, 0.7, 0.8, 0.5)
    
    controller.update_parameters(state, performance=0.8)
    
    # 应该有RL训练记录
    assert len(controller.rl_agent.memory) > 0
```

### 性能测试
```python
def test_response_time_distribution():
    collector = MetricsCollector()
    
    # 记录100次响应时间
    for _ in range(100):
        start = time.time()
        # 执行操作
        duration = time.time() - start
        collector.record_response_time("/api", duration)
    
    stats = collector.get_response_time_stats()
    assert stats['p95'] < 0.1  # P95 < 100ms
```

## 📈 性能基准

### 黎曼几何计算
| 操作 | 维度 | 平均耗时 | P95 |
|------|------|----------|-----|
| 势能计算 | 384 | ~0.3ms | ~0.5ms |
| 梯度计算 | 384 | ~2ms | ~3ms |
| 演化(10次) | 384 | ~10ms | ~15ms |

### 系统性能
| 指标 | 目标 | 实测 |
|------|------|------|
| 请求吞吐量 | > 50 req/s | ~100 req/s |
| 记忆检索 | < 100ms | ~30ms |
| LLM调用 | < 500ms | ~200ms |
| PID更新 | < 1ms | ~0.1ms |

## 🐛 调试技巧

### 详细输出
```bash
pytest tests/ -v -s  # 显示print输出
pytest tests/ -v --tb=short  # 简化错误追踪
pytest tests/ -v --capture=no  # 不捕获输出
```

### 性能分析
```bash
# 使用pytest-benchmark（需要安装）
pytest tests/performance/ --benchmark-only

# 生成性能报告
pytest tests/performance/ -v --cov-report=html
```

### 覆盖率分析
```bash
# 生成HTML报告
pytest tests/ --cov=nuwa_core --cov-report=html

# 查看覆盖详情
open htmlcov/index.html
```

## ✅ 最佳实践

1. **测试命名**: 使用描述性名称，如 `test_should_return_energy_when_state_is_core`
2. **测试隔离**: 每个测试独立，不依赖其他测试
3. **Mock外部依赖**: 使用fixture模拟外部服务
4. **边界测试**: 测试零值、NaN、Inf等边界情况
5. **性能测试**: 在独立文件中，不与单元测试混合

## 📝 添加新测试

### 步骤
1. 选择测试类型（单元/集成/性能）
2. 创建/编辑测试文件
3. 使用AAA模式（Arrange-Act-Assert）
4. 添加必要的fixture
5. 运行测试验证
6. 更新README

### 模板
```python
import pytest
import numpy as np
from nuwa_core.your_module import YourClass

class TestYourClass:
    def test_method_name(self):
        # Arrange
        obj = YourClass()
        
        # Act
        result = obj.method()
        
        # Assert
        assert result == expected
```

## 🔗 相关文档

- [主README](../README.md) - 项目概览
- [部署文档](../README.md#部署) - Docker部署
- [监控文档](../README.md#监控) - 监控指标

---

**维护者**: Nuwa Core Team  
**更新**: 2025-12-20  
**状态**: ✅ 完整