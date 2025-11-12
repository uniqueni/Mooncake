# 🚀 手动清理缓存 - 超简单指南

## 你说得对！

如果**手动清理缓存**，确实不需要多场景批处理脚本，直接多次运行 `test_simple.py` 就可以。

---

## ⚠️ 重要提醒

### 每次只测一个场景！

配置文件中的 `default_scenarios` **只能配置一个场景**：

```yaml
default_scenarios:
  - long_context_high_reuse     # ✅ 只配置一个
  # - multi_turn_conversation   # ❌ 注释掉其他！
  # - code_generation
```

**为什么？**
- 如果配置多个场景，会连续运行
- 场景 B 的 Round 1 会误命中场景 A 的缓存
- 导致缓存效果数据失真

**详细说明**: 查看 `IMPORTANT_CACHE_ISOLATION.md`

---

## ✅ 推荐方案：手动运行（最简单）

### 步骤 1: 准备配置文件

为每个场景创建一个配置：

```bash
cd simple_test

# 场景 1: 腾讯云单机
cp configs/test_config_simple.yaml configs/test_config_tencent.yaml
vim configs/test_config_tencent.yaml
# 只改 base_url: "http://腾讯云IP:端口/v1"

# 场景 2: 火山云单机（如果有）
cp configs/test_config_simple.yaml configs/test_config_volcano.yaml
vim configs/test_config_volcano.yaml
# 只改 base_url: "http://火山云IP:端口/v1"
```

### 步骤 2: 运行测试

```bash
# 场景 1
python3 scripts/test_simple.py --config configs/test_config_tencent.yaml

# 👉 手动清理缓存
# 方法 1: 重启 vLLM 服务
pkill -f vllm && bash scripts/run.sh

# 或方法 2: 等待 30 秒让缓存过期
sleep 30

# 场景 2
python3 scripts/test_simple.py --config configs/test_config_volcano.yaml

# 手动清理...

# 场景 3（如果有）
python3 scripts/test_simple.py --config configs/test_config_xxx.yaml
```

### 步骤 3: 生成汇总报告

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_<timestamp1>.json \
    --scenario "火山云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_<timestamp2>.json \
    --output final_report.md \
    --chart-dir final_charts
```

---

## 📊 方案对比

### 方案 A: 手动运行 + 手动清理（你的方案）

**优点**:
- ✅ 简单直接
- ✅ 不需要批处理脚本
- ✅ 灵活，想测哪个测哪个

**缺点**:
- ❌ 需要手动清理缓存（重启服务或等待）
- ❌ 需要手动记录每个 stats 文件名
- ❌ 需要手动生成汇总报告

**适合**:
- 测试场景少（1-2个）
- 不介意手动操作
- 没有自动化需求

### 方案 B: 批处理自动化

**优点**:
- ✅ 全自动（清理、测试、报告）
- ✅ 不会忘记清理缓存
- ✅ 自动生成汇总报告

**缺点**:
- ❌ 需要配置 `multi_scenario_config.yaml`
- ❌ 如果没有清理 API，需要改脚本

**适合**:
- 测试场景多（3+个）
- 需要重复测试
- 想要完全自动化

---

## 💡 我的推荐

### 如果你只测试 2-3 个场景

**用方案 A（手动）**，更简单：

```bash
# 创建一个简单的测试脚本
vim run_tests.sh
```

内容：
```bash
#!/bin/bash

# 场景 1
echo "测试场景 1: 腾讯云"
python3 scripts/test_simple.py --config configs/test_config_tencent.yaml

echo "手动重启 vLLM 服务清理缓存，然后按回车继续..."
read

# 场景 2
echo "测试场景 2: 火山云"
python3 scripts/test_simple.py --config configs/test_config_volcano.yaml

echo "完成！"
echo "Stats 文件在 test_results/ 目录"
ls -lt test_results/*_stats_*.json | head -2
```

运行：
```bash
chmod +x run_tests.sh
./run_tests.sh
```

在提示时手动重启 vLLM 或等待。

### 如果你测试 4+ 个场景

**用方案 B（批处理）**，改一下脚本：

把 `scripts/run_multi_scenario_test.py` 中的缓存清理部分改为：

```python
def clear_mooncake_cache(self) -> bool:
    """清理 Mooncake 缓存"""
    print("⚠️  请手动清理缓存（重启 vLLM 或等待缓存过期）")
    input("清理完成后按回车继续...")
    return True
```

---

## 🎯 实际使用示例

### 示例：测试腾讯云和火山云

```bash
cd simple_test

# 1. 准备配置（只做一次）
cp configs/test_config_simple.yaml configs/test_config_tencent.yaml
vim configs/test_config_tencent.yaml  # 改 API URL

cp configs/test_config_simple.yaml configs/test_config_volcano.yaml
vim configs/test_config_volcano.yaml  # 改 API URL

# 2. 测试场景 1
python3 scripts/test_simple.py --config configs/test_config_tencent.yaml
# Stats 文件: test_results/with-cache_72B_stats_20250112_100000.json

# 3. 手动清理缓存
# 重启 vLLM 或等待 30 秒

# 4. 测试场景 2
python3 scripts/test_simple.py --config configs/test_config_volcano.yaml
# Stats 文件: test_results/with-cache_72B_stats_20250112_110000.json

# 5. 生成汇总报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_20250112_100000.json \
    --scenario "火山云-Qwen2.5-72B" \
    --stats test_results/with-cache_72B_stats_20250112_110000.json \
    --output comparison_report.md
```

---

## 📁 新的文件结构

```
simple_test/
├── START_HERE_MANUAL.md           # 👈 手动清理指南（本文件）
├── START_HERE.md                  # 自动批处理指南
├── README.md                      # 总体说明
│
├── configs/                       # 配置文件目录
│   ├── test_config_simple.yaml    # 模板
│   ├── test_config_cross_node.yaml
│   └── multi_scenario_config.yaml # 批处理配置
│
├── scripts/                       # 脚本目录
│   ├── test_simple.py             # 👈 主测试脚本
│   ├── run_multi_scenario_test.py # 批处理脚本
│   └── *.sh                       # 辅助脚本
│
├── reports/                       # 报告工具目录
│   ├── generate_multi_scenario_report.py  # 汇总报告
│   ├── compare_results.py         # 单场景分析
│   └── analyze_results.py         # 深度分析
│
├── templates/                     # 模板目录
│   └── lmcache_config_template.yaml
│
├── docs/                          # 文档目录
│   ├── SIMPLE_TEST_GUIDE.md
│   ├── MULTI_SCENARIO_TEST_GUIDE.md
│   └── ...
│
└── test_results/                  # 测试结果（自动生成）
```

---

## ⚙️ 如何手动清理缓存？

### 方法 1: 重启 vLLM（推荐，最彻底）

```bash
# 停止 vLLM
pkill -f vllm

# 重启 vLLM
bash scripts/run.sh
```

### 方法 2: 等待缓存过期

```bash
# 等待足够长时间（如 30 秒）
sleep 30
```

### 方法 3: 重启容器（如果用 Docker）

```bash
docker restart <container_name>
```

---

## ❓ 常见问题

### Q: 我一定要手动清理吗？

**A**: 如果测试多个场景，是的。否则：
- 场景 B 的 Round 1 会误命中场景 A 的缓存
- 缓存效果数据不准确

### Q: 不清理会怎样？

**A**:
- Round 1 (Cold Start) 不是真正的冷启动
- TTFT 降低百分比会失真
- 无法准确评估缓存效果

### Q: 我能自动清理吗？

**A**: 如果 Mooncake 没有清理 API，只能：
1. 手动重启 vLLM
2. 或用批处理脚本，在清理步骤暂停等你手动操作

---

## 🎯 总结

### 手动方式（推荐给你）

```bash
# 1. 创建配置文件
cp configs/test_config_simple.yaml configs/test_config_xxx.yaml
vim configs/test_config_xxx.yaml

# 2. 运行测试
python3 scripts/test_simple.py --config configs/test_config_xxx.yaml

# 3. 手动清理缓存
# 重启 vLLM

# 4. 运行下一个场景
python3 scripts/test_simple.py --config configs/test_config_yyy.yaml

# 5. 生成汇总报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "场景1" --stats test_results/stats1.json \
    --scenario "场景2" --stats test_results/stats2.json \
    --output report.md
```

**简单、直接、灵活！**

---

需要帮助？查看 `README.md` 或 `docs/` 目录下的详细文档。
