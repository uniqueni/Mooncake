# 🚀 从这里开始 - 超简单指南

## 你只需要关注 3 个文件

```
simple_test/
├── test_simple.py                    # 测试脚本（已有，不用改）
├── run_multi_scenario_test.py        # 批处理脚本（已有，不用改）
└── multi_scenario_config.yaml        # 👈 你要改的配置文件
```

**其他文件可以忽略！**

---

## 📝 快速开始（3 步）

### 第 1 步：准备配置文件

为每个测试场景创建一个配置文件：

```bash
cd simple_test

# 场景 1：腾讯云单机
cp test_config_simple.yaml test_config_tencent_single.yaml
vim test_config_tencent_single.yaml
```

修改内容（只改这几行）：
```yaml
openai_api:
  base_url: "http://腾讯云IP:端口/v1"     # 改成你的 vLLM API 地址
  model_name: "Qwen2.5-72B-Instruct"    # 改成你的模型名

model:
  size: "72B"                            # 改成模型大小
```

如果有多个场景，重复上面的步骤：
```bash
# 场景 2：腾讯云跨节点
cp test_config_simple.yaml test_config_tencent_cross.yaml
vim test_config_tencent_cross.yaml
# 修改 base_url 和 endpoints_per_round

# 场景 3：火山云单机
cp test_config_simple.yaml test_config_volcano_single.yaml
vim test_config_volcano_single.yaml
```

### 第 2 步：配置多场景测试

```bash
# 创建批处理配置
vim multi_scenario_config.yaml
```

内容（复制粘贴，改成你的场景）：
```yaml
output_dir: "test_results_multi"
clear_cache_between_scenarios: true
wait_between_scenarios: 10

mooncake:
  metadata_server_url: "http://你的Master_IP:8080/metadata"  # 改这里

test_scenarios:
  # 场景 1
  - name: "腾讯云-单机-Qwen2.5-72B"
    config_file: "test_config_tencent_single.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  # 场景 2（如果有）
  - name: "腾讯云-跨节点-Qwen2.5-72B"
    config_file: "test_config_tencent_cross.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  # 场景 3（如果有）
  # - name: "火山云-单机-Qwen2.5-72B"
  #   config_file: "test_config_volcano_single.yaml"
  #   scenario: "long_context_high_reuse"
  #   rounds: 2
```

### 第 3 步：运行测试

```bash
python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
```

**就这么简单！**

等待测试完成后，报告会自动生成在 `test_results_multi/` 目录。

---

## 📊 查看结果

```bash
# 查看汇总报告
ls test_results_multi/
cat test_results_multi/multi_scenario_report_*.md

# 查看图表
open test_results_multi/multi_scenario_charts_*/
```

---

## 🎯 常见场景

### 场景 A: 我只有 1 个测试环境

```yaml
test_scenarios:
  - name: "单机测试-Qwen2.5-72B"
    config_file: "test_config_simple.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

运行：
```bash
python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
```

### 场景 B: 对比单机 vs 跨节点

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

### 场景 C: 对比不同云平台

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
```

### 场景 D: 对比不同模型

```yaml
test_scenarios:
  - name: "Qwen2.5-72B"
    config_file: "test_config_qwen.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2

  - name: "Deepseek-R1"
    config_file: "test_config_deepseek.yaml"
    scenario: "long_context_high_reuse"
    rounds: 2
```

---

## 💡 配置说明（就这 4 个参数）

### multi_scenario_config.yaml

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `output_dir` | 结果保存目录 | `test_results_multi` |
| `clear_cache_between_scenarios` | 场景间清理缓存 | `true`（必须） |
| `wait_between_scenarios` | 场景间等待秒数 | `10` |
| `mooncake.metadata_server_url` | Mooncake Master URL | `http://IP:8080/metadata` |

### 场景配置（每个场景 4 个参数）

| 参数 | 说明 | 示例 |
|------|------|------|
| `name` | 场景名称 | `腾讯云-单机-Qwen2.5-72B` |
| `config_file` | 配置文件 | `test_config_xxx.yaml` |
| `scenario` | 测试类型 | `long_context_high_reuse` |
| `rounds` | 测试轮数 | `2` |

---

## ⚠️ 常见问题

### Q1: 需要清理缓存吗？

**A**: 是的！必须设置：
```yaml
clear_cache_between_scenarios: true
```

否则场景 B 会用到场景 A 的缓存，结果不准确。

### Q2: 测试要多久？

**A**: 估算公式：
```
单场景时间 ≈ 2分钟（10个请求 × 2轮）
总时间 ≈ 场景数 × 2分钟 + 场景间等待

示例：
  3个场景 = 3 × 2分钟 + 2 × 10秒 ≈ 7分钟
```

### Q3: 测试失败了怎么办？

**A**: 其他场景会继续运行（不受影响）。检查失败场景的配置文件，修复后可以单独重新测试。

### Q4: 我不想用批处理，可以单独测试吗？

**A**: 可以！
```bash
python3 test_simple.py --config test_config_xxx.yaml
```

但这样你需要手动清理缓存、手动生成汇总报告。

---

## 📖 需要更多信息？

- **详细配置说明**: `cat SIMPLE_TEST_GUIDE.md`
- **多场景详细指南**: `cat MULTI_SCENARIO_TEST_GUIDE.md`
- **报告生成说明**: `cat REPORT_GENERATION_GUIDE.md`

---

## 🎯 总结

**你只需要做 3 件事**：

1. ✅ 准备每个场景的配置文件（改 API URL）
2. ✅ 配置 `multi_scenario_config.yaml`（列出所有场景）
3. ✅ 运行 `python3 run_multi_scenario_test.py --config multi_scenario_config.yaml`

**完成！** 报告会自动生成。
