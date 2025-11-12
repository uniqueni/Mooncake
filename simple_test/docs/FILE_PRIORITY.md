# 📁 文件优先级清单

## 🔴 必看文件（只有这 1 个！）

| 文件 | 说明 |
|------|------|
| **START_HERE.md** | 👈 **从这里开始！超简单 3 步指南** |

---

## 🟡 需要修改的文件（2-3 个）

### 测试配置文件

| 文件 | 用途 | 怎么做 |
|------|------|--------|
| `test_config_xxx.yaml` | 每个场景的配置 | 复制 `test_config_simple.yaml`，改 API URL |
| `multi_scenario_config.yaml` | 批处理配置 | 列出你的所有场景 |

**示例**：
```bash
# 1. 创建场景配置
cp test_config_simple.yaml test_config_tencent.yaml
vim test_config_tencent.yaml  # 改 base_url

# 2. 配置批处理
vim multi_scenario_config.yaml  # 列出场景
```

---

## 🟢 会用到的脚本（不需要修改）

| 文件 | 用途 | 使用方法 |
|------|------|----------|
| `run_multi_scenario_test.py` | 批处理测试脚本 | `python3 run_multi_scenario_test.py --config xxx.yaml` |
| `test_simple.py` | 单场景测试脚本 | `python3 test_simple.py --config xxx.yaml` |
| `generate_multi_scenario_report.py` | 报告生成（自动调用） | 不用手动运行 |
| `compare_results.py` | 单场景分析（可选） | `python3 compare_results.py --stats xxx.json --generate-report` |

---

## ⚪ 可以忽略的文件

### 模板和示例文件（不用看）

```
lmcache_config_template.yaml         # LMCache 模板（你已经有了）
test_config_simple.yaml              # 模板（复制它来创建新配置）
test_config_cross_node.yaml          # 跨节点模板
multi_scenario_config_simple.yaml    # 简化模板
```

### 示例和文档（需要时再看）

```
example_generate_report.sh           # 手动生成报告示例（不需要）
quick_start_multi_test.sh            # 快速启动脚本（可选）
QUICKSTART.md                        # 快速开始（START_HERE.md 更简单）
SIMPLE_TEST_GUIDE.md                 # 详细指南（需要时看）
MULTI_SCENARIO_TEST_GUIDE.md         # 多场景详细指南（需要时看）
REPORT_GENERATION_GUIDE.md           # 报告生成指南（需要时看）
FILES_OVERVIEW.md                    # 文件总览（需要时看）
EXECUTIVE_REPORT_TEMPLATE.md         # 报告模板示例
EXAMPLE_EXECUTIVE_REPORT.md          # 报告示例
```

### 其他工具（很少用）

```
analyze_results.py                   # 深度分析（排查问题时用）
compare_results.py                   # 单场景分析（可选）
```

---

## 🎯 使用流程图

```
1. 阅读 START_HERE.md
   ↓
2. 创建场景配置文件
   cp test_config_simple.yaml test_config_xxx.yaml
   vim test_config_xxx.yaml
   ↓
3. 配置批处理
   vim multi_scenario_config.yaml
   ↓
4. 运行测试
   python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
   ↓
5. 查看报告
   cat test_results_multi/multi_scenario_report_*.md
```

---

## 📝 实际例子

### 你要测试 2 个场景：腾讯云和火山云

#### 1. 创建配置文件

```bash
# 腾讯云配置
cp test_config_simple.yaml test_config_tencent.yaml
vim test_config_tencent.yaml
# 改 base_url: "http://腾讯云IP:端口/v1"

# 火山云配置
cp test_config_simple.yaml test_config_volcano.yaml
vim test_config_volcano.yaml
# 改 base_url: "http://火山云IP:端口/v1"
```

#### 2. 配置批处理

```bash
vim multi_scenario_config.yaml
```

内容：
```yaml
output_dir: "test_results_multi"
clear_cache_between_scenarios: true
wait_between_scenarios: 10

mooncake:
  metadata_server_url: "http://你的Master_IP:8080/metadata"

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

#### 3. 运行

```bash
python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
```

#### 4. 查看结果

```bash
ls test_results_multi/
cat test_results_multi/multi_scenario_report_*.md
```

**完成！**

---

## 💡 记住这些

### ✅ 必须做的

1. 阅读 `START_HERE.md`
2. 创建场景配置文件（改 API URL）
3. 配置 `multi_scenario_config.yaml`
4. 运行测试

### ❌ 不需要做的

1. 不用看所有文档（太多了）
2. 不用修改测试脚本
3. 不用手动生成报告（自动的）
4. 不用担心其他文件

---

## 🆘 遇到问题？

### 最快的解决方法

1. **看 START_HERE.md** - 99% 的问题都能解决
2. **检查配置文件** - 确认 API URL 正确
3. **看测试日志** - 错误信息会告诉你问题在哪

### 需要详细信息？

| 问题类型 | 看哪个文档 |
|---------|-----------|
| 配置不会写 | `START_HERE.md` 示例 |
| 测试失败 | 看终端错误信息 |
| 想了解更多 | `MULTI_SCENARIO_TEST_GUIDE.md` |
| 报告看不懂 | 报告里有说明 |

---

## 🎯 总结

### 你只需要关心 3 个文件

1. **START_HERE.md** - 看这个
2. **test_config_xxx.yaml** - 创建这些（每个场景一个）
3. **multi_scenario_config.yaml** - 配置这个

### 其他文件？

**忽略就好！** 需要时再看。

---

**现在去看 START_HERE.md 吧！**
