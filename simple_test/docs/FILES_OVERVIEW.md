# 📁 文件总览

## 核心测试脚本

| 文件 | 用途 | 使用场景 |
|------|------|----------|
| **test_simple.py** | 单场景测试脚本 | 测试单个配置场景 |
| **run_multi_scenario_test.py** | 多场景批处理脚本 | 测试多个场景（完全隔离） |

## 配置文件

| 文件 | 用途 |
|------|------|
| **test_config_simple.yaml** | 单机测试配置模板 |
| **test_config_cross_node.yaml** | 跨节点测试配置模板 |
| **lmcache_config_template.yaml** | LMCache 配置模板 |
| **multi_scenario_config.yaml** | 多场景测试配置（完整版） |
| **multi_scenario_config_simple.yaml** | 多场景测试配置（简化版） |

## 报告生成工具

| 文件 | 输入 | 输出 | 用途 |
|------|------|------|------|
| **generate_multi_scenario_report.py** | 多个 stats 文件 | 汇总报告 + 5个对比图 | 多场景对比 |
| **compare_results.py** | 单个 stats 文件 | 技术报告 + 3个图 | 单场景分析 |
| **analyze_results.py** | 单个 results 文件 | 技术报告 + 6个趋势图 | 深度分析 |

## 快速启动脚本

| 文件 | 用途 |
|------|------|
| **quick_start_multi_test.sh** | 快速启动多场景测试 |
| **example_generate_report.sh** | 手动生成汇总报告示例 |

## 文档

| 文件 | 内容 |
|------|------|
| **README.md** | 总体说明和快速开始 |
| **QUICKSTART.md** | 3 步快速开始指南 |
| **SIMPLE_TEST_GUIDE.md** | 详细测试指南 |
| **MULTI_SCENARIO_TEST_GUIDE.md** | 多场景测试指南（⭐ 重要） |
| **REPORT_GENERATION_GUIDE.md** | 报告生成指南 |
| **EXECUTIVE_REPORT_TEMPLATE.md** | 报告模板示例 |
| **EXAMPLE_EXECUTIVE_REPORT.md** | 报告完整示例 |
| **FILES_OVERVIEW.md** | 本文件 - 文件总览 |

---

## 🚀 典型使用流程

### 流程 1: 测试单个场景

```bash
# 1. 准备配置
vim test_config_simple.yaml

# 2. 运行测试
python3 test_simple.py --config test_config_simple.yaml

# 3. 生成报告
python3 compare_results.py --stats test_results/test_stats_*.json --generate-report
```

### 流程 2: 测试多个场景（推荐）

```bash
# 1. 准备每个场景的配置文件
vim test_config_scenario1.yaml
vim test_config_scenario2.yaml
vim test_config_scenario3.yaml

# 2. 配置多场景测试
cp multi_scenario_config_simple.yaml my_test.yaml
vim my_test.yaml  # 添加所有场景

# 3. 运行批处理测试
python3 run_multi_scenario_test.py --config my_test.yaml

# 4. 自动生成汇总报告！
# (报告会自动生成在 output_dir 中)
```

---

## 📊 三层分析体系

### 第 1 层：多场景汇总对比

**工具**: `generate_multi_scenario_report.py`

**问题**:
- 哪个云平台性能最好？
- 单机 vs 跨节点效果如何？
- 不同模型的缓存效果差异？

**输出**:
- 汇总表格（所有场景对比）
- 5 个对比图表
- 测试总结

### 第 2 层：单场景技术分析

**工具**: `compare_results.py`

**问题**:
- 这个场景的缓存效果如何？
- 关键指标达标了吗？
- 有什么优化建议？

**输出**:
- 性能指标表格
- 技术分析（TTFT、吞吐量、TPOT）
- 优化建议或问题排查步骤

### 第 3 层：深度问题排查

**工具**: `analyze_results.py`

**问题**:
- 为什么第 15 个请求特别慢？
- 性能是否随时间下降？
- 哪些请求是异常值？

**输出**:
- 6 个趋势图（时间序列、分布、异常检测等）
- 逐请求分析
- 异常值标记

---

## 🎯 选择指南

### 我该用哪个脚本？

```
你要测试几个场景？
│
├─ 只有 1 个场景
│   └─> 使用 test_simple.py
│       └─> 生成报告：compare_results.py
│
└─ 2+ 个场景
    └─> 使用 run_multi_scenario_test.py（推荐）
        └─> 自动生成汇总报告
```

### 我该用哪个报告工具？

```
你有几个场景的数据？
│
├─ 多个场景
│   └─> generate_multi_scenario_report.py
│       └─> 对比哪个场景最好
│
├─ 单个场景
│   └─> compare_results.py
│       └─> 评估性能和优化建议
│
└─ 需要深度分析
    └─> analyze_results.py
        └─> 找出性能问题和异常
```

---

## ⚠️ 重要提醒

### 为什么需要场景隔离？

❌ **错误做法**:
```python
for scenario in ["场景A", "场景B", "场景C"]:
    test(scenario)  # 直接连续测试
```

**问题**:
- 场景 B 的 Round 1 会误命中场景 A 的缓存
- 缓存效果数据失真
- 结果不可靠

✅ **正确做法**:
```bash
# 使用批处理脚本
python3 run_multi_scenario_test.py --config my_test.yaml
```

**优点**:
- 场景间自动清理缓存
- 每个 Round 1 都是真正的 Cold Start
- 数据准确可靠

---

## 📖 推荐阅读顺序

1. **新手**: `README.md` → `QUICKSTART.md` → 开始测试
2. **多场景测试**: `MULTI_SCENARIO_TEST_GUIDE.md` ⭐ 必读
3. **详细配置**: `SIMPLE_TEST_GUIDE.md`
4. **报告生成**: `REPORT_GENERATION_GUIDE.md`

---

**快速开始多场景测试**: `bash quick_start_multi_test.sh`
