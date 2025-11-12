# 📊 多场景批处理测试指南

## 为什么需要场景隔离？

### ❌ 问题：不隔离的后果

如果在一次运行中连续测试多个场景：

```python
# ❌ 有问题的方式
for scenario in ["场景A", "场景B", "场景C"]:
    run_test(scenario, rounds=2)
```

**会发生什么**：
1. **缓存污染**
   - 场景 A Round 2 存储了缓存
   - 场景 B Round 1 应该是 Cold Start，但可能误命中场景 A 的缓存
   - 场景 B Round 2 的缓存效果失真

2. **统计混乱**
   - 所有场景数据混在一个文件里
   - 难以区分哪些结果属于哪个场景
   - 无法生成清晰的对比报告

3. **结果不可靠**
   - Round 1 不是真正的 Cold Start
   - 缓存效果数据失真
   - 无法准确评估性能

### ✅ 解决方案：完全隔离

```bash
# ✅ 正确的方式
for scenario in ["场景A", "场景B", "场景C"]:
    run_test(scenario, rounds=2)
    clear_cache()  # 清理缓存
    wait(10s)      # 等待系统稳定
```

**优点**：
- ✅ 每个场景独立运行，互不干扰
- ✅ 每个场景的 Round 1 都是真正的 Cold Start
- ✅ 缓存效果数据准确可靠
- ✅ 可以灵活控制场景间的清理和等待

---

## 🚀 快速开始

### 方式 1: 使用快速启动脚本（推荐）

```bash
cd simple_test

# 1. 创建配置文件
cp multi_scenario_config_simple.yaml multi_scenario_config.yaml

# 2. 编辑配置文件
vim multi_scenario_config.yaml
# 修改：
#   - mooncake.metadata_server_url: 你的 Mooncake URL
#   - test_scenarios: 添加你的测试场景

# 3. 运行测试
bash quick_start_multi_test.sh
```

### 方式 2: 直接使用 Python 脚本

```bash
python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
```

---

## ⚙️ 配置文件说明

### 完整配置示例

```yaml
# 输出目录
output_dir: "test_results_multi"

# 场景间清理缓存（强烈推荐开启）
clear_cache_between_scenarios: true

# 场景间等待时间（秒）
wait_between_scenarios: 10

# Mooncake 配置
mooncake:
  metadata_server_url: "http://10.237.65.81:8080/metadata"

# 测试场景列表
test_scenarios:
  # 场景 1
  - name: "腾讯云-单机多卡-Qwen2.5-72B"
    config_file: "test_config_tencent_qwen_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
    concurrency: 5  # 可选

  # 场景 2
  - name: "腾讯云-跨节点-Qwen2.5-72B"
    config_file: "test_config_tencent_qwen_cross.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  # ... 更多场景
```

### 配置项详解

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| **output_dir** | 输出目录 | `test_results_multi` |
| **clear_cache_between_scenarios** | 场景间清理缓存 | `true`（强烈推荐） |
| **wait_between_scenarios** | 场景间等待时间（秒） | `10`（TCP）/ `5`（RDMA） |
| **mooncake.metadata_server_url** | Mooncake metadata API | `http://IP:8080/metadata` |

### 场景配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| **name** | 场景名称（用于报告） | `腾讯云-单机-Qwen2.5-72B` |
| **config_file** | 测试配置文件 | `test_config_xxx.yaml` |
| **scenario** | 测试场景类型 | `long_context_high_reuse` |
| **rounds** | 测试轮次 | `2` |
| **concurrency** | 并发数（可选） | `5` |

### 场景类型说明

```yaml
scenario: "long_context_high_reuse"  # 长上下文高重用（推荐，最能体现缓存效果）
scenario: "multi_turn_conversation"  # 多轮对话
scenario: "code_generation"          # 代码生成
scenario: "batch_processing"         # 批量处理
scenario: "cold_start"               # 冷启动基线
```

---

## 🔧 缓存清理机制

### 清理方式

脚本会尝试以下方式清理缓存：

#### 方式 1: API 清理（推荐）

```bash
# 自动调用 Mooncake metadata API
POST http://YOUR_MASTER_IP:8080/metadata/clear
```

**配置**：
```yaml
mooncake:
  metadata_server_url: "http://10.237.65.81:8080/metadata"
```

#### 方式 2: 手动重启 vLLM（如果 API 不可用）

在场景间手动执行：
```bash
# 停止 vLLM
pkill -f vllm

# 重启 vLLM
bash run.sh
```

#### 方式 3: 等待自动过期

如果没有清理 API，可以设置较长的等待时间：
```yaml
wait_between_scenarios: 30  # 等待 30 秒
```

### 为什么需要清理？

| 场景 | 不清理 | 清理后 |
|------|--------|--------|
| **场景 A Round 1** | Cold Start ✅ | Cold Start ✅ |
| **场景 A Round 2** | Cache Hit ✅ | Cache Hit ✅ |
| **场景 B Round 1** | ❌ 误命中场景 A 缓存 | ✅ Cold Start |
| **场景 B Round 2** | ❌ 数据失真 | ✅ Cache Hit |

---

## 📊 测试流程

### 完整流程图

```
开始
  │
  ├─→ 场景 1
  │     ├─ Round 1 (Cold Start)
  │     ├─ Round 2 (Cache Hit)
  │     └─ 保存 stats_1.json
  │
  ├─→ [清理缓存 + 等待 10s]
  │
  ├─→ 场景 2
  │     ├─ Round 1 (Cold Start)
  │     ├─ Round 2 (Cache Hit)
  │     └─ 保存 stats_2.json
  │
  ├─→ [清理缓存 + 等待 10s]
  │
  ├─→ 场景 3
  │     └─ ...
  │
  └─→ 自动生成汇总报告
        ├─ 汇总表格
        ├─ 对比图表
        └─ 技术分析
```

### 执行日志示例

```
================================================================================
🚀 多场景批处理测试
================================================================================
测试场景数: 3
输出目录: test_results_multi
场景间清理缓存: ✅
================================================================================

################################################################################
# 进度: 1/3
################################################################################

================================================================================
🧪 场景: 腾讯云-单机多卡-Qwen2.5-72B
================================================================================
配置文件: test_config_tencent_qwen_single.yaml
测试场景: long_context_high_reuse
测试轮次: 2
================================================================================

📝 执行命令: python3 test_simple.py --config test_config_tencent_qwen_single.yaml ...

[test_simple.py 的输出...]

✅ 场景完成: 腾讯云-单机多卡-Qwen2.5-72B (耗时 120.5s)
   Stats 文件: test_results_multi/with-cache_72B_stats_20250111_143022.json

────────────────────────────────────────────────────────────────────────────────
🧹 场景间清理
────────────────────────────────────────────────────────────────────────────────
🧹 清理 Mooncake 缓存...
   Metadata Server: http://10.237.65.81:8080/metadata
   ✅ 缓存已清理
⏳ 等待 10s 让系统稳定...

⏳ 下一个场景前等待 10s...

################################################################################
# 进度: 2/3
################################################################################

[场景 2...]

[场景 3...]

================================================================================
📊 测试总结
================================================================================
总场景数: 3
成功: 3
失败: 0
总耗时: 8.5 分钟

================================================================================
📊 生成汇总报告
================================================================================

📝 生成命令: python3 generate_multi_scenario_report.py ...

✅ 报告已生成:
   报告: test_results_multi/multi_scenario_report_20250111_144530.md
   图表: test_results_multi/multi_scenario_charts_20250111_144530/

================================================================================
✅ 所有测试完成！
================================================================================
```

---

## 📋 测试场景规划示例

### 示例 1: 对比云平台性能

```yaml
test_scenarios:
  - name: "腾讯云-Qwen2.5-72B"
    config_file: "test_config_tencent.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "火山云-Qwen2.5-72B"
    config_file: "test_config_volcano.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "阿里云-Qwen2.5-72B"
    config_file: "test_config_aliyun.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

**用途**: 选择最优云平台

### 示例 2: 验证跨节点效果

```yaml
test_scenarios:
  - name: "单机多卡"
    config_file: "test_config_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "跨节点"
    config_file: "test_config_cross_node.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

**用途**: 验证跨节点 KV Cache 传输

### 示例 3: 对比不同模型

```yaml
test_scenarios:
  - name: "Qwen2.5-72B"
    config_file: "test_config_qwen72b.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "Deepseek-R1"
    config_file: "test_config_deepseek.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "Llama3-70B"
    config_file: "test_config_llama70b.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

**用途**: 了解不同模型的缓存效果

### 示例 4: 完整性能矩阵

```yaml
test_scenarios:
  # 腾讯云 × Qwen2.5
  - name: "腾讯云-单机-Qwen2.5"
    config_file: "test_config_tencent_qwen_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "腾讯云-跨节点-Qwen2.5"
    config_file: "test_config_tencent_qwen_cross.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  # 腾讯云 × Deepseek
  - name: "腾讯云-单机-Deepseek"
    config_file: "test_config_tencent_deepseek_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "腾讯云-跨节点-Deepseek"
    config_file: "test_config_tencent_deepseek_cross.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  # 火山云 × Qwen2.5
  - name: "火山云-单机-Qwen2.5"
    config_file: "test_config_volcano_qwen_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "火山云-跨节点-Qwen2.5"
    config_file: "test_config_volcano_qwen_cross.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

**用途**: 完整的性能测试矩阵报告

---

## 📊 生成的输出

### 目录结构

```
test_results_multi/
├── with-cache_72B_stats_20250111_143022.json      # 场景 1 统计
├── with-cache_72B_results_20250111_143022.json    # 场景 1 原始数据
├── with-cache_R1_stats_20250111_144055.json       # 场景 2 统计
├── with-cache_R1_results_20250111_144055.json     # 场景 2 原始数据
├── ...
├── multi_scenario_report_20250111_144530.md       # 汇总报告
└── multi_scenario_charts_20250111_144530/         # 汇总图表
    ├── ttft_comparison.png
    ├── throughput_comparison.png
    ├── ttft_reduction_comparison.png
    ├── throughput_increase_comparison.png
    └── performance_radar.png
```

### 报告内容

汇总报告包含：
1. **汇总表格** - 所有场景的 TTFT、吞吐量、TPOT 对比
2. **可视化图表** - 5 个对比图表
3. **详细数据** - 每个场景的完整指标表格
4. **测试总结** - 达标场景统计、结论

---

## 🔧 故障排查

### 问题 1: 缓存清理失败

```
⚠️  清理失败: Connection refused
```

**原因**: Mooncake metadata server 不可达或没有提供 `/clear` API

**解决**:
1. 检查 `metadata_server_url` 配置是否正确
2. 确认 Mooncake 是否运行
3. 如果没有清理 API，手动在场景间重启 vLLM

### 问题 2: 某个场景失败

```
❌ 场景失败: 腾讯云-单机-Qwen2.5-72B
```

**解决**:
- 其他场景会继续运行（不受影响）
- 检查该场景的配置文件是否正确
- 查看详细错误日志
- 修复后可以单独重新运行该场景

### 问题 3: 场景间仍有干扰

**症状**: 场景 B 的 Round 1 TTFT 异常低

**原因**: 缓存未清理干净

**解决**:
```yaml
# 增加等待时间
wait_between_scenarios: 30  # 从 10 增加到 30

# 或手动在场景间重启 vLLM
```

### 问题 4: 报告生成失败

```
❌ 报告生成失败: matplotlib not found
```

**解决**:
```bash
pip install matplotlib
```

---

## 💡 最佳实践

### 1. 场景命名规范

使用清晰的命名：
```
格式: <平台>-<部署方式>-<模型>

示例:
  ✅ "腾讯云-单机多卡-Qwen2.5-72B"
  ✅ "火山云-跨节点-Deepseek-R1"
  ❌ "test1"
  ❌ "scenario_a"
```

### 2. 测试顺序安排

先跑简单场景，后跑复杂场景：
```yaml
test_scenarios:
  - name: "单机-Qwen-10个请求"    # 快速验证
  - name: "单机-Qwen-100个请求"   # 完整测试
  - name: "跨节点-Qwen-100个请求" # 复杂场景
```

### 3. 并发控制

根据资源调整并发：
```yaml
# GPU 足够
concurrency: 10

# GPU 紧张
concurrency: 5

# 保守测试
# 不设置 concurrency（串行）
```

### 4. 缓存清理策略

根据网络选择等待时间：
```yaml
# RDMA（高带宽低延迟）
wait_between_scenarios: 5

# TCP
wait_between_scenarios: 10

# 跨机房
wait_between_scenarios: 20
```

### 5. 测试时间估算

```
单场景时间 ≈ 请求数 × (TTFT + 生成时间) / 并发数 × 2轮

总时间 ≈ 场景数 × (单场景时间 + 清理等待时间)

示例:
  10 请求 × 5s × 2 轮 = 100s ≈ 2分钟
  3 场景 × (2分钟 + 10s) = 6.5分钟
```

---

## 📖 完整示例

### 步骤 1: 准备配置文件

```bash
# 创建每个场景的测试配置
cp test_config_simple.yaml test_config_tencent_qwen.yaml
vim test_config_tencent_qwen.yaml  # 修改 API URL

cp test_config_simple.yaml test_config_volcano_qwen.yaml
vim test_config_volcano_qwen.yaml  # 修改 API URL
```

### 步骤 2: 创建多场景配置

```bash
cp multi_scenario_config_simple.yaml my_test.yaml
vim my_test.yaml
```

```yaml
output_dir: "my_test_results"
clear_cache_between_scenarios: true
wait_between_scenarios: 10

mooncake:
  metadata_server_url: "http://10.237.65.81:8080/metadata"

test_scenarios:
  - name: "腾讯云-Qwen2.5-72B"
    config_file: "test_config_tencent_qwen.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "火山云-Qwen2.5-72B"
    config_file: "test_config_volcano_qwen.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

### 步骤 3: 运行测试

```bash
python3 run_multi_scenario_test.py --config my_test.yaml
```

### 步骤 4: 查看结果

```bash
# 查看报告
cat my_test_results/multi_scenario_report_*.md

# 查看图表
ls my_test_results/multi_scenario_charts_*/
```

---

## 🎯 总结

| 特性 | 单次运行多场景 | 批处理隔离测试 |
|------|----------------|----------------|
| **缓存隔离** | ❌ 互相污染 | ✅ 完全隔离 |
| **Round 1 准确性** | ❌ 可能误命中 | ✅ 真正 Cold Start |
| **数据可靠性** | ❌ 失真 | ✅ 准确 |
| **失败处理** | ❌ 全部失败 | ✅ 独立失败 |
| **灵活性** | ❌ 固定流程 | ✅ 可控清理 |

**推荐使用批处理隔离测试！**

---

**快速开始**: `bash quick_start_multi_test.sh`
