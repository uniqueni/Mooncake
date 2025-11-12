# 📊 多场景测试报告生成指南

## 快速开始

### 1️⃣ 运行测试（生成数据）

为每个测试场景运行测试脚本：

```bash
# 场景 1: 腾讯云单机 Qwen2.5-72B
python3 test_simple.py --config test_config_tencent_qwen.yaml

# 场景 2: 腾讯云跨节点 Qwen2.5-72B
python3 test_simple.py --config test_config_tencent_qwen_cross.yaml

# 场景 3: 火山云单机 Deepseek-R1
python3 test_simple.py --config test_config_volcano_deepseek.yaml

# ... 更多场景
```

测试完成后，会生成统计文件：
- `test_results/with-cache_<model>_stats_<timestamp>.json`

### 2️⃣ 生成多场景汇总报告

#### 方式 A: 使用命令行

```bash
python3 generate_multi_scenario_report.py \
    --scenario "腾讯云-单机-Qwen2.5-72B" \
    --stats test_results/with-cache_Qwen_stats_20250111_100000.json \
    \
    --scenario "腾讯云-跨节点-Qwen2.5-72B" \
    --stats test_results/with-cache_Qwen_stats_20250111_110000.json \
    \
    --scenario "火山云-单机-Deepseek-R1" \
    --stats test_results/with-cache_Deepseek_stats_20250111_120000.json \
    \
    --output final_report.md \
    --chart-dir final_charts
```

#### 方式 B: 使用脚本模板

1. 编辑 `example_generate_report.sh`
2. 修改场景名称和文件路径
3. 运行：`bash example_generate_report.sh`

## 📋 生成的报告内容

### 汇总表格

报告会生成 4 个汇总表格：

1. **TTFT 汇总** - 所有场景的首 Token 延迟对比
2. **吞吐量汇总** - 所有场景的吞吐量对比
3. **TPOT 汇总** - 所有场景的每 Token 延迟对比
4. **Token 吞吐量汇总** - 每秒生成的 Token 数对比

### 可视化图表

生成 5 个图表（需要 matplotlib）：

1. **`ttft_comparison.png`** - TTFT 柱状对比图
   - 展示 Baseline vs Cache Hit
   - 直观看出哪个场景缓存效果最好

2. **`throughput_comparison.png`** - 吞吐量柱状对比图
   - 展示 Baseline vs Cache Hit
   - 对比不同场景的吞吐量提升

3. **`ttft_reduction_comparison.png`** - TTFT 降低百分比横向对比
   - 颜色标识：绿色(≥60%)、橙色(40-60%)、红色(<40%)
   - 一目了然看出哪些场景达标

4. **`throughput_increase_comparison.png`** - 吞吐量提升百分比横向对比
   - 颜色标识：绿色(≥150%)、橙色(100-150%)、红色(<100%)
   - 快速识别性能提升最显著的场景

5. **`performance_radar.png`** - 综合性能雷达图（≤6个场景时生成）
   - 三个维度：TTFT降低、吞吐量提升、TPOT稳定性
   - 综合评估各场景的整体表现

### 详细数据表格

为每个场景生成详细表格，包含：
- TTFT (平均 + P90)
- TPOT
- 吞吐量
- Token 吞吐量
- 端到端延迟
- 指标达成状态

## 💡 场景命名建议

使用清晰的命名规范，便于识别：

```
格式: <平台>-<部署方式>-<模型>
```

示例：
- `腾讯云-单机多卡-Qwen2.5-72B`
- `腾讯云-跨节点-Qwen2.5-72B`
- `火山云-单机多卡-Deepseek-R1`
- `火山云-跨节点-Deepseek-R1`

**说明**：
- **平台**: 腾讯云、火山云、阿里云等
- **部署方式**: 单机多卡、跨节点、单机单卡等
- **模型**: Qwen2.5-72B、Deepseek-R1 等

## 🎯 使用场景

### 场景 1: 对比不同云平台性能

```bash
python3 generate_multi_scenario_report.py \
    --scenario "腾讯云-Qwen2.5-72B" \
    --stats tencent_qwen_stats.json \
    --scenario "火山云-Qwen2.5-72B" \
    --stats volcano_qwen_stats.json \
    --output platform_comparison.md
```

**用途**: 决定使用哪个云平台

### 场景 2: 对比单机 vs 跨节点

```bash
python3 generate_multi_scenario_report.py \
    --scenario "单机多卡-Qwen2.5" \
    --stats single_node_stats.json \
    --scenario "跨节点-Qwen2.5" \
    --stats cross_node_stats.json \
    --output deployment_comparison.md
```

**用途**: 验证跨节点 KV Cache 传输效果

### 场景 3: 对比不同模型表现

```bash
python3 generate_multi_scenario_report.py \
    --scenario "Qwen2.5-72B" \
    --stats qwen_stats.json \
    --scenario "Deepseek-R1" \
    --stats deepseek_stats.json \
    --scenario "Llama3-70B" \
    --stats llama_stats.json \
    --output model_comparison.md
```

**用途**: 了解不同模型的缓存效果差异

### 场景 4: 全面性能测试矩阵

```bash
python3 generate_multi_scenario_report.py \
    --scenario "腾讯云-单机-Qwen2.5" --stats tencent_single_qwen.json \
    --scenario "腾讯云-跨节点-Qwen2.5" --stats tencent_cross_qwen.json \
    --scenario "腾讯云-单机-Deepseek" --stats tencent_single_deepseek.json \
    --scenario "腾讯云-跨节点-Deepseek" --stats tencent_cross_deepseek.json \
    --scenario "火山云-单机-Qwen2.5" --stats volcano_single_qwen.json \
    --scenario "火山云-跨节点-Qwen2.5" --stats volcano_cross_qwen.json \
    --output full_matrix_report.md
```

**用途**: 完整性能测试报告

## 📊 报告示例输出

```markdown
# Mooncake KV Cache 多场景性能测试报告

**报告日期**: 2025年01月11日
**测试场景数**: 4

---

## 📊 测试结果汇总

### TTFT (首 Token 延迟)

| 测试场景 | Baseline | Cache Hit | 降低 | 状态 |
|---------|----------|-----------|------|------|
| 腾讯云-单机-Qwen2.5-72B | 1200.0 ms | 400.0 ms | 66.7% | ✅ |
| 腾讯云-跨节点-Qwen2.5-72B | 1250.0 ms | 420.0 ms | 66.4% | ✅ |
| 火山云-单机-Deepseek-R1 | 1100.0 ms | 380.0 ms | 65.5% | ✅ |

### 吞吐量 (Throughput)

| 测试场景 | Baseline | Cache Hit | 提升 | 状态 |
|---------|----------|-----------|------|------|
| 腾讯云-单机-Qwen2.5-72B | 2.50 req/s | 7.40 req/s | +196.0% | ✅ |
| 腾讯云-跨节点-Qwen2.5-72B | 2.40 req/s | 7.20 req/s | +200.0% | ✅ |
| 火山云-单机-Deepseek-R1 | 2.60 req/s | 7.50 req/s | +188.5% | ✅ |

...
```

## ⚙️ 高级选项

### 仅生成表格（不生成图表）

如果不需要图表或没有 matplotlib：

```bash
python3 generate_multi_scenario_report.py \
    --scenario "场景1" --stats stats1.json \
    --scenario "场景2" --stats stats2.json \
    --no-charts \
    --output report_tables_only.md
```

### 自定义图表输出目录

```bash
python3 generate_multi_scenario_report.py \
    --scenario "场景1" --stats stats1.json \
    --chart-dir /path/to/custom/charts/
```

## 🔧 故障排查

### 问题 1: 找不到统计文件

```
❌ 文件未找到: test_results/xxx_stats.json
```

**解决**:
- 确认测试已运行完成
- 检查文件路径是否正确
- 使用 `ls test_results/*_stats.json` 查看实际文件名

### 问题 2: 场景名和文件数量不匹配

```
❌ 错误: --scenario 和 --stats 参数数量必须一致
```

**解决**:
- 确保每个 `--scenario` 都有对应的 `--stats`
- 检查是否遗漏了某个参数

### 问题 3: 无法生成图表

```
提示: matplotlib 未安装，无法生成图表
```

**解决**:
```bash
pip install matplotlib
```

或使用 `--no-charts` 仅生成表格。

### 问题 4: 数据格式错误

```
❌ 数据错误: 统计数据缺少字段: ['avg_ttft']
```

**解决**:
- 确认使用的是 **stats 文件**，不是 results 文件
- 正确文件名格式: `with-cache_<model>_stats_<timestamp>.json`
- 重新运行测试生成正确的统计文件

## 📝 完整工作流示例

```bash
# 1. 准备测试配置
vim test_config_scenario1.yaml
vim test_config_scenario2.yaml

# 2. 运行所有测试
python3 test_simple.py --config test_config_scenario1.yaml
python3 test_simple.py --config test_config_scenario2.yaml

# 3. 等待测试完成，查看生成的统计文件
ls test_results/*_stats.json

# 4. 生成汇总报告
python3 generate_multi_scenario_report.py \
    --scenario "场景1" --stats test_results/with-cache_Model1_stats_20250111_100000.json \
    --scenario "场景2" --stats test_results/with-cache_Model2_stats_20250111_110000.json \
    --output final_report.md \
    --chart-dir final_charts

# 5. 查看报告
cat final_report.md

# 6. 查看图表
ls final_charts/
# 或在文件管理器中打开图片
```

## 🎁 额外工具

### 使用 compare_results.py 生成单场景详细报告

如果需要某个场景的详细分析：

```bash
# 生成单个场景的详细报告（含技术分析、优化建议）
python3 compare_results.py \
    --stats test_results/with-cache_Qwen_stats_20250111_100000.json \
    --generate-report \
    --output scenario1_detailed_report.md
```

### 使用 analyze_results.py 生成趋势图

如果需要查看单个场景的详细趋势：

```bash
# 生成 6 个趋势图（TTFT时间序列、分布直方图等）
python3 analyze_results.py \
    --results test_results/with-cache_Qwen_results_20250111_100000.json \
    --output-dir scenario1_analysis
```

## 📊 三种报告工具对比

| 工具 | 输入 | 用途 | 输出 |
|------|------|------|------|
| **generate_multi_scenario_report.py** | 多个 stats 文件 | 多场景对比汇总 | 汇总表格 + 对比图表 |
| **compare_results.py** | 单个 stats 文件 | 单场景详细分析 | 详细报告 + 技术建议 |
| **analyze_results.py** | 单个 results 文件 | 单场景趋势分析 | 6个趋势图 + 异常检测 |

**推荐工作流**:
1. 先用 `generate_multi_scenario_report.py` 生成多场景汇总
2. 对感兴趣的场景，用 `compare_results.py` 生成详细报告
3. 如果发现问题，用 `analyze_results.py` 深入分析

---

**快速入门**: 复制 `example_generate_report.sh`，修改场景名称和文件路径，直接运行！
