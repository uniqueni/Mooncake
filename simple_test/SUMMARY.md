# 📊 文件整理完成总结

## ✅ 已完成

### 1. 文件夹结构整理

```
simple_test/
├── configs/          # ✅ 所有配置文件
├── scripts/          # ✅ 所有脚本
├── reports/          # ✅ 报告生成工具
├── templates/        # ✅ 模板文件
├── docs/             # ✅ 详细文档
└── test_results/     # 测试结果（自动生成）
```

### 2. 创建手动清理指南

**START_HERE_MANUAL.md** - 针对没有缓存清理 API 的情况

---

## 🎯 你的问题：需要多场景批处理吗？

### 答案：看情况

#### 如果测试 1-3 个场景 → 不需要

**直接用 test_simple.py + 手动清理**

```bash
# 场景 1
python3 scripts/test_simple.py --config configs/test_config_1.yaml

# 手动重启 vLLM
pkill -f vllm && bash scripts/run.sh

# 场景 2
python3 scripts/test_simple.py --config configs/test_config_2.yaml

# 手动重启...

# 最后生成汇总报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "场景1" --stats test_results/stats1.json \
    --scenario "场景2" --stats test_results/stats2.json \
    --output report.md
```

**优点**：
- ✅ 简单直接
- ✅ 不需要配置批处理
- ✅ 灵活

#### 如果测试 4+ 个场景 → 推荐批处理

**用 run_multi_scenario_test.py**

修改清理函数为手动提示：
```python
def clear_mooncake_cache(self):
    print("请手动重启 vLLM 清理缓存")
    input("完成后按回车继续...")
    return True
```

**优点**：
- ✅ 自动化流程
- ✅ 不会忘记清理
- ✅ 自动生成报告

---

## 🚀 推荐使用方式（手动清理）

### 超简单 3 步

#### 第 1 步：创建配置

```bash
# 腾讯云配置
cp configs/test_config_simple.yaml configs/test_config_tencent.yaml
vim configs/test_config_tencent.yaml
# 改 base_url: "http://腾讯云IP:端口/v1"

# 火山云配置
cp configs/test_config_simple.yaml configs/test_config_volcano.yaml
vim configs/test_config_volcano.yaml
# 改 base_url: "http://火山云IP:端口/v1"
```

#### 第 2 步：依次测试

```bash
# 场景 1
python3 scripts/test_simple.py --config configs/test_config_tencent.yaml
# 记录 stats 文件名：test_results/with-cache_72B_stats_20250112_100000.json

# 👉 手动清理缓存
pkill -f vllm && bash scripts/run.sh

# 场景 2
python3 scripts/test_simple.py --config configs/test_config_volcano.yaml
# 记录 stats 文件名：test_results/with-cache_72B_stats_20250112_110000.json
```

#### 第 3 步：生成报告

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_20250112_100000.json \
    --scenario "火山云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_20250112_110000.json \
    --output final_report.md \
    --chart-dir final_charts
```

**完成！** 报告在 `final_report.md`，图表在 `final_charts/`

---

## 📁 关键文件位置

### 你需要的文件

| 文件 | 位置 | 用途 |
|------|------|------|
| **配置模板** | `configs/test_config_simple.yaml` | 复制它创建新配置 |
| **测试脚本** | `scripts/test_simple.py` | 运行测试 |
| **汇总报告** | `reports/generate_multi_scenario_report.py` | 生成多场景对比 |
| **手动指南** | `START_HERE_MANUAL.md` | 查看详细步骤 |

### 可选文件

| 文件 | 位置 | 用途 |
|------|------|------|
| 单场景分析 | `reports/compare_results.py` | 详细分析单个场景 |
| 深度分析 | `reports/analyze_results.py` | 趋势图和异常检测 |
| 批处理脚本 | `scripts/run_multi_scenario_test.py` | 自动化（需要改清理函数）|

---

## 💡 快速参考

### 运行单个场景测试

```bash
python3 scripts/test_simple.py --config configs/你的配置.yaml
```

### 手动清理缓存

```bash
# 方法 1: 重启 vLLM（推荐）
pkill -f vllm && bash scripts/run.sh

# 方法 2: 重启容器
docker restart <container_name>

# 方法 3: 等待过期
sleep 30
```

### 生成多场景汇总报告

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "场景1" --stats stats文件1.json \
    --scenario "场景2" --stats stats文件2.json \
    --output report.md
```

### 查看结果

```bash
# 查看报告
cat final_report.md

# 查看图表
ls final_charts/
```

---

## 🎯 总结

### 你的情况

- ✅ 没有 Mooncake 清理 API
- ✅ 可以手动重启 vLLM
- ✅ 测试场景可能 2-3 个

### 最佳方案

**手动运行 test_simple.py + 手动清理**

1. 为每个场景创建配置文件
2. 依次运行测试，测试间手动重启 vLLM
3. 最后用 `generate_multi_scenario_report.py` 生成汇总

### 不需要

- ❌ 不需要配置 `multi_scenario_config.yaml`
- ❌ 不需要运行 `run_multi_scenario_test.py`
- ❌ 不需要改批处理脚本

### 工作流

```
创建配置 → 测试场景1 → 重启vLLM → 测试场景2 → 重启vLLM → ... → 生成报告
```

---

## 📖 需要详细说明？

查看：
```bash
cat START_HERE_MANUAL.md  # 手动清理详细指南
```

---

**简单、直接、有效！** 🎉
