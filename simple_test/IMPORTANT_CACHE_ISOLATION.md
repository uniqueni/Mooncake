# ⚠️ 重要：缓存隔离问题

## 问题发现

用户提出了一个非常好的问题：

> 如果在 `default_scenarios` 配置多个场景，会不会一次跑完所有场景？
> 跑 2 轮的话，不就是有缓存了吗（场景间会互相影响）？

**答案：是的！这正是缓存污染问题。**

---

## ❌ 错误做法

### 配置文件这样写：

```yaml
default_scenarios:
  - long_context_high_reuse      # 场景 A
  - multi_turn_conversation      # 场景 B
  - code_generation              # 场景 C
```

### 运行：

```bash
python3 scripts/test_simple.py --config configs/test_config.yaml
```

### 会发生什么：

```
1. 场景 A Round 1 (Cold Start) ✅ 正确
2. 场景 A Round 2 (Cache Hit)  ✅ 正确，使用场景 A 缓存

3. 场景 B Round 1 (Cold Start) ❌ 错误！
   → Mooncake 中还有场景 A 的缓存
   → 如果 prompt 相似，会误命中
   → 不是真正的 Cold Start

4. 场景 B Round 2 (Cache Hit)  ❌ 错误！
   → 缓存数据混乱（A + B 混合）
   → TTFT 降低百分比失真

5. 场景 C Round 1...          ❌ 继续错误
   → 缓存更混乱（A + B + C）
```

### 结果：

- **只有第一个场景测试准确** ✅
- **其他场景都不准确** ❌

---

## ✅ 正确做法

### 方法 1: 每次只配置一个场景（推荐）

#### 配置文件：

```yaml
# test_config_scenario_a.yaml
default_scenarios:
  - long_context_high_reuse  # 只配置一个！

# test_config_scenario_b.yaml
default_scenarios:
  - multi_turn_conversation  # 只配置一个！

# test_config_scenario_c.yaml
default_scenarios:
  - code_generation  # 只配置一个！
```

#### 运行：

```bash
# 场景 A
python3 scripts/test_simple.py --config configs/test_config_scenario_a.yaml

# 👉 手动清理缓存
pkill -f vllm && bash scripts/run.sh

# 场景 B
python3 scripts/test_simple.py --config configs/test_config_scenario_b.yaml

# 👉 手动清理缓存
pkill -f vllm && bash scripts/run.sh

# 场景 C
python3 scripts/test_simple.py --config configs/test_config_scenario_c.yaml
```

### 方法 2: 命令行覆盖

#### 使用同一个配置文件，命令行指定场景：

```bash
# 场景 A
python3 scripts/test_simple.py \
    --config configs/test_config_simple.yaml \
    --scenarios long_context_high_reuse

# 清理缓存...

# 场景 B
python3 scripts/test_simple.py \
    --config configs/test_config_simple.yaml \
    --scenarios multi_turn_conversation

# 清理缓存...

# 场景 C
python3 scripts/test_simple.py \
    --config configs/test_config_simple.yaml \
    --scenarios code_generation
```

---

## 🔍 为什么会缓存污染？

### Mooncake KV Cache 工作原理

1. **Round 1**: vLLM 生成 KV Cache → 存储到 Mooncake
2. **Round 2**: 相同 prompt → vLLM 从 Mooncake 加载缓存

### 缓存匹配机制

Mooncake 根据 **prompt** 匹配缓存（通常是 hash）：

- 如果 prompt 完全相同 → 命中缓存 ✅
- 如果 prompt 部分相同 → 部分命中 ⚠️
- 如果 prompt 完全不同 → 不命中 ✅

### 场景间污染示例

```
场景 A: "这是一个 16k 长文档..."
场景 B: "这是一个 16k 长文档..."  # 可能有相似内容

→ 场景 B Round 1 误命中场景 A 的缓存
→ TTFT 异常低
→ 缓存效果数据失真
```

---

## 📊 影响范围

### 受影响的指标

| 指标 | 场景 1 | 场景 2+ |
|------|--------|---------|
| **Round 1 TTFT** | ✅ 准确 | ❌ 可能偏低（误命中） |
| **Round 2 TTFT** | ✅ 准确 | ❌ 失真 |
| **TTFT 降低百分比** | ✅ 准确 | ❌ 失真 |
| **吞吐量提升** | ✅ 准确 | ❌ 失真 |

### 报告结果

- **场景 1 的报告** ✅ 可信
- **场景 2+ 的报告** ❌ 不可信

---

## 🛠️ 解决方案对比

### 方案 A: 手动隔离（推荐）

**做法**：每次测一个场景，手动清理

```bash
# 场景 A
python3 scripts/test_simple.py --config config_a.yaml
# 清理：重启 vLLM

# 场景 B
python3 scripts/test_simple.py --config config_b.yaml
# 清理：重启 vLLM

# 场景 C
python3 scripts/test_simple.py --config config_c.yaml
```

**优点**：
- ✅ 简单直接
- ✅ 完全隔离
- ✅ 结果准确

**缺点**：
- ❌ 手动操作

### 方案 B: 批处理自动化

**做法**：用 `run_multi_scenario_test.py`，自动清理

**优点**：
- ✅ 全自动

**缺点**：
- ❌ 需要 Mooncake 清理 API（你没有）
- ❌ 或需要改脚本手动提示

---

## 💡 推荐配置

### test_config_simple.yaml

```yaml
default_scenarios:
  - long_context_high_reuse  # 只配置一个！
  # - multi_turn_conversation  # 注释掉！
  # - code_generation          # 注释掉！
  # - batch_processing         # 注释掉！
  # - cold_start               # 注释掉！
```

### 如果需要测试多个场景

**创建多个配置文件**：

```bash
# 场景 A
cp configs/test_config_simple.yaml configs/test_scenario_a.yaml
# 只保留 long_context_high_reuse

# 场景 B
cp configs/test_config_simple.yaml configs/test_scenario_b.yaml
# 只保留 multi_turn_conversation
```

---

## 🎯 总结

### ✅ 正确理解

1. 一个配置文件可以配置多个场景
2. 但一次运行会连续执行所有场景
3. **场景间会缓存污染**
4. 导致除第一个场景外，其他都不准确

### ✅ 正确做法

**每次只测一个场景**：

```yaml
default_scenarios:
  - long_context_high_reuse  # 只写一个
```

或命令行指定：

```bash
python3 scripts/test_simple.py --scenarios long_context_high_reuse
```

### ✅ 清理缓存

测试间必须清理：

```bash
# 方法 1: 重启 vLLM（推荐）
pkill -f vllm && bash scripts/run.sh

# 方法 2: 重启容器
docker restart <container>

# 方法 3: 等待过期
sleep 30
```

---

**感谢你发现这个问题！** 这对确保测试结果准确非常重要。👍
