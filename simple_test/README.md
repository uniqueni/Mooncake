# 简化版测试套件

**适用场景**：你已经有 Mooncake 部署和 OpenAI 兼容接口

---

## ⭐ 新用户从这里开始

### 🎯 选择你的方式

#### 方式 1: 手动清理缓存（推荐 - 最简单）

如果没有 Mooncake 清理 API，手动重启 vLLM：

```bash
cat START_HERE_MANUAL.md  # 手动清理指南
```

**特点**:
- ✅ 超简单，直接运行 `test_simple.py`
- ✅ 测试间手动重启 vLLM
- ✅ 灵活，适合 1-3 个场景

#### 方式 2: 自动批处理（适合多场景）

如果有 Mooncake 清理 API 或测试场景多：

```bash
cat START_HERE.md  # 自动批处理指南
```

**特点**:
- ✅ 全自动运行多个场景
- ✅ 自动清理缓存（如果有 API）
- ✅ 适合 4+ 个场景

---

## 📁 文件结构（已整理）

```
simple_test/
├── README.md                       # 本文件
├── START_HERE_MANUAL.md            # 👈 手动清理指南（推荐）
├── START_HERE.md                   # 自动批处理指南
├── QUICKSTART.md                   # 快速开始
│
├── configs/                        # 配置文件
│   ├── test_config_simple.yaml     # 单机配置模板
│   ├── test_config_cross_node.yaml # 跨节点配置模板
│   └── multi_scenario_config*.yaml # 批处理配置
│
├── scripts/                        # 测试脚本
│   ├── test_simple.py              # 👈 主测试脚本
│   ├── run_multi_scenario_test.py  # 批处理脚本
│   └── *.sh                        # 辅助脚本
│
├── reports/                        # 报告生成工具
│   ├── generate_multi_scenario_report.py  # 汇总报告
│   ├── compare_results.py          # 单场景分析
│   └── analyze_results.py          # 深度分析
│
├── templates/                      # 模板
│   └── lmcache_config_template.yaml
│
├── docs/                           # 详细文档
│   ├── SIMPLE_TEST_GUIDE.md
│   ├── MULTI_SCENARIO_TEST_GUIDE.md
│   ├── CROSS_NODE_TESTING_GUIDE.md  # 跨节点测试指南
│   └── ...
│
└── test_results/                   # 测试结果（自动生成）
```

## 🚀 快速开始

### 3 步开始测试

```bash
cd simple_test

# 1. 配置 LMCache
cp lmcache_config_template.yaml lmcache_config.yaml
vim lmcache_config.yaml  # 修改 IP 地址

# 2. 配置测试
cp test_config_simple.yaml my_test_config.yaml
vim my_test_config.yaml  # 修改接口地址

# 3. 运行测试
python3 test_simple.py --config my_test_config.yaml
```

**详细步骤请查看**: `QUICKSTART.md`

## 📖 文档

### 基础文档
- **QUICKSTART.md** - 3 分钟快速开始（推荐先看这个）
- **SIMPLE_TEST_GUIDE.md** - 详细测试指南、配置说明和故障排查
- **docs/CROSS_NODE_TESTING_GUIDE.md** - 🌐 跨节点测试指南（测试不同节点间 KV Cache 传输）

### 高级文档
- **START_HERE_MANUAL.md** - 手动清理缓存方式（推荐）
- **START_HERE.md** - 自动批处理方式
- **IMPORTANT_CACHE_ISOLATION.md** - ⚠️ 缓存隔离重要说明

## 🎯 与复杂版的区别

| 对比项 | 简化版（这个目录）| 完整版（tests/ 目录）|
|--------|-----------------|---------------------|
| **部署方式** | 你已有的服务 | Docker Compose 完整部署 |
| **配置复杂度** | ⭐ 简单（2 个配置文件）| ⭐⭐⭐ 复杂（多容器配置）|
| **测试模式** | 单一模式 | PD 分离 + 非 PD 分离 |
| **适用场景** | 快速验证缓存效果 | 完整性能测试和对比 |
| **文档** | 精简清晰 | 详尽全面 |

## ⚙️ 你需要提供

1. **Mooncake Master 地址**
   - IP:Port（例如：192.168.1.100:50052）
   - Metadata 端口（通常是 8080）

2. **OpenAI 兼容接口**
   - API URL（例如：http://192.168.1.100:8000/v1）
   - 模型名称

3. **网络信息**（如果用 RDMA）
   - RDMA 设备名（例如：mlx5_0）

## 📊 测试内容

测试场景：
- ✅ 长上下文高重用（16k tokens，90% 重用）
- ✅ 多轮对话（85% 重用）
- ✅ 代码生成（80% 重用）
- ✅ 批量处理（95% 重用）
- ✅ 冷启动基线（0% 重用）

测试指标：
- ⏱️ TTFT (Time to First Token)
- ⚡ TPOT (Time per Output Token)
- 🚀 吞吐量 (req/s, tokens/s)
- 📊 缓存效果（Round 2 vs Round 1）

## 🎁 预期结果

测试成功后，你会看到：

```
🎯 缓存效果:
  TTFT 降低:    +66.5%
  吞吐量提升:   +195.7%
  ✅ 达到目标！
```

## 🔄 多场景批处理测试

**新功能！** 如果你需要测试多个场景（如：单机 vs 跨节点、不同云平台、不同模型），使用批处理测试可以确保场景间完全隔离，避免缓存污染：

```bash
# 快速开始
bash quick_start_multi_test.sh

# 或直接运行
python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
```

**优点**：
- ✅ 场景间完全隔离，自动清理缓存
- ✅ 每个场景的 Round 1 都是真正的 Cold Start
- ✅ 自动生成汇总报告和对比图表
- ✅ 失败场景不影响其他场景

**详细文档**: `MULTI_SCENARIO_TEST_GUIDE.md`

---

## 📊 结果分析

测试完成后，有**三种分析工具**：

### 0️⃣ 多场景汇总分析（新！）

使用 `generate_multi_scenario_report.py` 分析**多个场景**：

```bash
# 自动生成（由 run_multi_scenario_test.py 自动调用）
# 或手动生成：
python3 generate_multi_scenario_report.py \
    --scenario "腾讯云-Qwen2.5" --stats test_results/scenario1_stats.json \
    --scenario "火山云-Qwen2.5" --stats test_results/scenario2_stats.json \
    --output comparison_report.md \
    --chart-dir comparison_charts
```

**会生成**：
- 汇总表格（TTFT、吞吐量、TPOT）
- 5 个对比图表（柱状图、横向对比、雷达图）
- 详细数据表格

### 1️⃣ 单场景技术报告

使用 `compare_results.py` 分析 **stats 文件**：

```bash
# 快速查看缓存效果摘要（控制台输出）
python3 compare_results.py --stats test_results/test_stats_YYYYMMDD_HHMMSS.json

# 生成技术报告
python3 compare_results.py --stats test_results/test_stats_YYYYMMDD_HHMMSS.json \
                           --generate-report

# 生成报告 + 图表
python3 compare_results.py --stats test_results/test_stats_YYYYMMDD_HHMMSS.json \
                           --generate-report --generate-charts
```

### 2️⃣ 技术分析报告（深度分析、画趋势图）

使用 `analyze_results.py` 分析 **results 文件**：

```bash
# 生成所有趋势图 + 技术分析报告
python3 analyze_results.py --results test_results/with-cache_72B_results_*.json

# 自定义输出目录
python3 analyze_results.py --results test_results/with-cache_72B_results_*.json \
                           --output-dir my_analysis \
                           --report my_technical_report.md
```

**会生成 6 个趋势图**：
1. 📈 **TTFT 时间序列图** - 看性能随时间变化（是否越来越慢？）
2. 📊 **TTFT 分布直方图** - 看数据分布是否均匀（有没有长尾？）
3. 🔄 **逐请求 TTFT 对比** - 每个请求的缓存效果（哪个请求慢？）
4. ⚡ **TPOT 分析图** - Decode 阶段性能（生成稳定吗？）
5. 🕐 **延迟分解图** - Prefill vs Decode 时间占比（瓶颈在哪？）
6. 🔍 **异常值检测图** - 找出性能异常的请求（为什么异常？）

### 🎯 三种工具对比

| 特性 | generate_multi_scenario_report | compare_results | analyze_results |
|------|-------------------------------|-----------------|-----------------|
| **数据源** | 多个 stats 文件 | 单个 stats 文件（汇总）| 单个 results 文件（原始）|
| **用途** | 多场景对比汇总 | 单场景技术分析 | 单场景深度分析 |
| **内容** | 汇总表格、场景对比 | 性能分析、优化建议 | 趋势图、异常值检测 |
| **图表** | 5 个对比图 | 3 个对比图 | 6 个详细趋势图 |
| **适用场景** | 平台选型、性能对比 | 性能评估、配置优化 | 问题排查、深度优化 |
| **回答问题** | "哪个平台最快？" | "缓存效果如何？" | "为什么第 15 个请求慢？" |

### 💡 使用建议

1. **测试多个场景时**
   - 使用 `run_multi_scenario_test.py` 批处理运行
   - 自动生成多场景汇总报告

2. **单场景性能评估**
   - 使用 `compare_results.py` 生成技术报告
   - 获取性能指标和优化建议

3. **深度问题排查**
   - 使用 `analyze_results.py` 分析趋势
   - 找出性能瓶颈和异常请求

### 📝 报告内容说明

生成的技术报告包含：

1. **📋 测试摘要**
   - 关键指标达成情况
   - 核心性能数据

2. **🎯 测试目的**
   - 评估指标说明（TTFT、吞吐量、TPOT）
   - 测试关注点（Prefill 优化、系统吞吐量等）

3. **🖥️ 测试环境**
   - 硬件环境（GPU、网络、Mooncake）
   - 软件环境（模型、vLLM、LMCache）
   - 关键配置参数

4. **🔬 测试方法**
   - 测试设计（A/B 对比测试）
   - 测试场景（模拟真实业务）
   - 测试数据（请求数、prompt 长度）
   - 测试流程（分步骤说明）

5. **📊 测试结果**
   - 可视化性能对比
   - 详细指标表格
   - 指标达成状态

6. **📊 性能分析**
   - TTFT 分析和优化建议
   - 吞吐量分析
   - TPOT 稳定性分析

7. **💡 结论与建议**
   - 测试结论（指标达标情况）
   - 技术优化建议
   - 问题排查步骤（如有）

**完整示例报告**: 查看 `EXECUTIVE_REPORT_TEMPLATE.md`

## 🌐 跨节点测试

如果你有多个 vLLM 副本（在不同节点），可以测试跨节点的 KV Cache 传输：

### 场景说明

```
副本 A (192.168.1.100:8000)          Mooncake Master
        │                                  │
Round 1 │ 生成 KV Cache                    │
        ├─────────────────────────────────>│ 存储
        │                                  │
                                          │
副本 B (192.168.1.101:8000)              │
        │                                  │
Round 2 │ 请求相同 prompt                  │
        │<─────────────────────────────────┤ 加载
        │ 直接使用，跳过 Prefill             │
```

### 配置和运行

```bash
# 1. 使用跨节点配置模板
cp test_config_cross_node.yaml my_cross_node_config.yaml

# 2. 修改配置文件中的副本地址
vim my_cross_node_config.yaml
# 修改 endpoints_per_round:
#   1: "http://副本A的IP:端口/v1"
#   2: "http://副本B的IP:端口/v1"

# 3. 运行测试
python3 test_simple.py --config my_cross_node_config.yaml

# 4. 分析结果
python3 compare_results.py --stats test_results_cross_node/test_stats_*.json
```

### 验证要点

跨节点测试成功的标志：
- ✅ Round 1 在副本 A 完成，TTFT 正常（Baseline）
- ✅ Round 2 在副本 B 完成，TTFT 显著降低 60%+
- ✅ 说明副本 B 成功从 Mooncake 加载了副本 A 存储的 KV Cache

如果 Round 2 的 TTFT 没有降低：
- ❌ 检查两个副本是否连接到**同一个** Mooncake Master
- ❌ 检查 LMCache 配置中的 `remote_url` 是否一致
- ❌ 确认两个副本使用**完全相同**的模型

## 🆘 需要帮助？

1. **快速开始**: 查看 `QUICKSTART.md`
2. **详细指南**: 查看 `SIMPLE_TEST_GUIDE.md`
3. **配置模板**: `lmcache_config_template.yaml` 有详细注释

## ⚠️ 注意

- 这个目录是**简化版**，适合快速测试
- 如果需要**完整的性能对比测试**，请使用 `tests/` 目录

---

**马上开始**: `cat QUICKSTART.md`
