# 🌐 跨节点测试指南

## 概述

跨节点测试用于验证 Mooncake KV Cache 在不同 vLLM 实例（节点）间传输的能力。

### 测试原理

```
┌──────────────┐                    ┌──────────────┐
│   节点 A     │                    │   节点 B     │
│  (vLLM 副本1)│                    │  (vLLM 副本2)│
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │ Round 1: 存储 KV Cache            │ Round 2: 加载 KV Cache
       │                                   │
       └───────────────┬───────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Mooncake      │
              │  (分布式 Cache)  │
              └─────────────────┘
```

**工作流程**：
1. **Round 1**: 在节点 A 执行请求，vLLM 生成 KV Cache 并存储到 Mooncake
2. **Round 2**: 在节点 B 执行相同请求，vLLM 从 Mooncake 加载 KV Cache（通过 RDMA 跨节点传输）
3. 对比 Round 1 和 Round 2 的 TTFT 和吞吐量，验证缓存传输效果

---

## 配置跨节点测试

### 步骤 1: 准备配置文件

创建配置文件（或使用 `configs/test_config_cross_node_example.yaml`）：

```yaml
openai_api:
  base_url: "http://10.237.65.81:8080/v1"  # 默认地址（可选）
  api_key: "dummy"
  model_name: "Qwen2.5-72B-Instruct"

  # 🌐 关键配置：按轮次指定不同的 endpoint
  endpoints_per_round:
    1: "http://10.237.65.81:8080/v1"    # Round 1: 节点 A
    2: "http://10.237.65.95:8080/v1"    # Round 2: 节点 B

# 其他配置...
test_execution:
  rounds: 2
  default_scenarios:
    - long_context_high_reuse  # 只配置一个场景！
```

### 步骤 2: 运行测试

```bash
cd simple_test

# 运行跨节点测试
python3 scripts/test_simple.py --config configs/test_config_cross_node_example.yaml

# 结果文件：
# - test_results/with-cache_long_context_high_reuse_72B_results_<timestamp>.json
# - test_results/with-cache_long_context_high_reuse_72B_stats_<timestamp>.json
```

### 步骤 3: 生成报告

```bash
# 单场景报告
python3 reports/compare_results.py \
    --stats test_results/with-cache_long_context_high_reuse_72B_stats_<timestamp>.json \
    --output cross_node_report.md

# 或者多场景对比报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-跨节点-Qwen2.5-72B" \
    --stats test_results/with-cache_long_context_high_reuse_72B_stats_<timestamp>.json \
    --output multi_scenario_report.md
```

---

## 报告中的跨节点信息

### 1. 跨节点测试标识

在报告的汇总表格中，跨节点测试场景会带有 🌐 标识：

```markdown
| 测试场景 | Baseline | Cache Hit | 降低 | 状态 |
|---------|----------|-----------|------|------|
| 🌐 腾讯云-跨节点-Qwen2.5-72B | 1500.0 ms | 450.0 ms | 70.0% | ✅ |
| 腾讯云-单机-Qwen2.5-72B | 1400.0 ms | 500.0 ms | 64.3% | ✅ |
```

### 2. 跨节点测试汇总

报告开头会显示所有跨节点测试的节点信息：

```markdown
### 🌐 跨节点测试信息

本次测试包含 **1** 个跨节点场景，验证 Mooncake KV Cache 跨节点传输能力：

1. **腾讯云-跨节点-Qwen2.5-72B**
   - 节点 A (存储缓存): `http://10.237.65.81:8080/v1`
   - 节点 B (加载缓存): `http://10.237.65.95:8080/v1`

> 跨节点测试说明: Round 1 在节点 A 执行并存储 KV Cache，Round 2 在节点 B 执行并从节点 A 加载缓存。
> TTFT 降低和吞吐量提升说明 Mooncake 成功在节点间传输了 KV Cache。
```

### 3. 详细表格中的节点信息

每个场景的详细数据中会显示具体的节点地址：

```markdown
### 🌐 腾讯云-跨节点-Qwen2.5-72B

#### 🌐 跨节点测试信息

- **Round 1 (Baseline)**: 节点 A - `http://10.237.65.81:8080/v1`
- **Round 2 (Cache Hit)**: 节点 B - `http://10.237.65.95:8080/v1`
- **KV Cache 传输**: ✅ 从节点 A 传输到节点 B

| 指标 | Baseline (Round 1) | Cache Hit (Round 2) | 改善 | 目标 | 状态 |
|------|-------------------|---------------------|------|------|------|
| TTFT (avg) | 1500.00 ms | 450.00 ms | -70.0% | -60% | ✅ |
| 吞吐量 (req/s) | 1.20 | 3.50 | +191.7% | +150% | ✅ |
```

---

## 验证要点

### 必需条件

1. **两个节点都配置了 LMCache**

   在两个 vLLM 实例的启动脚本中都要配置：
   ```bash
   --kv-connector lmcache.server.connector.connectors.LMCacheConnectorV1 \
   --kv-role kv_both \
   --kv-cache-config lmcache_config.yaml
   ```

2. **相同的模型**

   两个节点必须加载相同的模型（如 `Qwen2.5-72B-Instruct`）

3. **相同的 Mooncake 配置**

   `lmcache_config.yaml` 中的 Mooncake Master 地址必须一致：
   ```yaml
   storage_backend:
     type: mooncake
     master_ip: "10.237.65.100"
     master_port: 50052
   ```

4. **Mooncake 集群正常运行**

   ```bash
   # 检查 Mooncake Master
   curl http://10.237.65.100:8080/health

   # 检查指标
   curl http://10.237.65.100:9004/metrics | grep master_key_count
   ```

### 可选但推荐

1. **RDMA 支持**

   Mooncake 使用 RDMA 加速跨节点 KV Cache 传输，显著降低延迟

2. **节点间低延迟网络**

   建议两个节点在同一个数据中心或可用区

---

## 预期结果

### 优秀指标

- **TTFT 降低**: ≥60%
- **吞吐量提升**: ≥150%

如果达到这些指标，说明：
- ✅ Mooncake KV Cache 成功在节点间传输
- ✅ 节点 B 成功加载并使用了节点 A 的缓存
- ✅ 跨节点传输性能良好

### 一般指标

- **TTFT 降低**: 40-60%
- **吞吐量提升**: 100-150%

可能的原因：
- ⚠️ 网络延迟较高（无 RDMA）
- ⚠️ Mooncake 存储性能瓶颈
- ⚠️ 部分 KV Cache 命中

### 需要优化

- **TTFT 降低**: <40%
- **吞吐量提升**: <100%

可能的问题：
- ❌ Mooncake 配置错误
- ❌ 两个节点连接了不同的 Mooncake 实例
- ❌ 网络连接问题
- ❌ KV Cache 过期或清理

---

## 故障排查

### 问题 1: TTFT 没有降低

**症状**: Round 2 的 TTFT 和 Round 1 几乎一样

**排查步骤**:
1. 检查节点 B 是否正确配置了 LMCache：
   ```bash
   # 查看 vLLM 启动日志
   grep "lmcache" /path/to/vllm.log
   ```

2. 检查 Mooncake 是否存储了 KV Cache：
   ```bash
   # 查看 key 数量（应该在 Round 1 后增加）
   curl http://10.237.65.100:9004/metrics | grep master_key_count
   ```

3. 检查两个节点的 Mooncake 配置是否一致

### 问题 2: 连接失败

**症状**: `Connection refused` 或 `Timeout`

**排查步骤**:
1. 检查节点 B 的 vLLM 服务是否启动：
   ```bash
   curl http://10.237.65.95:8080/v1/models
   ```

2. 检查网络连通性：
   ```bash
   ping 10.237.65.95
   telnet 10.237.65.95 8080
   ```

3. 检查防火墙规则

### 问题 3: Round 2 报错

**症状**: Round 2 请求失败或报错

**可能原因**:
- 节点 B 的 vLLM 配置不正确
- 节点 B 没有加载正确的模型
- Mooncake 连接断开

**解决方法**:
1. 重启节点 B 的 vLLM 服务
2. 检查节点 B 的 `lmcache_config.yaml`
3. 验证 Mooncake 健康状态

---

## 示例：完整测试流程

### 1. 准备环境

```bash
# 节点 A: 10.237.65.81
# 节点 B: 10.237.65.95
# Mooncake Master: 10.237.65.100

# 两个节点都启动 vLLM + LMCache
```

### 2. 创建配置

```bash
cd simple_test

# 复制模板
cp configs/test_config_cross_node_example.yaml configs/test_cross_node.yaml

# 修改配置
vim configs/test_cross_node.yaml
```

修改内容：
```yaml
endpoints_per_round:
  1: "http://10.237.65.81:8080/v1"  # 节点 A
  2: "http://10.237.65.95:8080/v1"  # 节点 B
```

### 3. 运行测试

```bash
# 测试长上下文高重用场景
python3 scripts/test_simple.py \
    --config configs/test_cross_node.yaml \
    --scenarios long_context_high_reuse \
    --rounds 2

# 查看控制台输出：
# Round 1: 使用 http://10.237.65.81:8080/v1 (节点 A)
# Round 2: 使用 http://10.237.65.95:8080/v1 (节点 B)
```

### 4. 生成报告

```bash
# 获取生成的 stats 文件
STATS_FILE=$(ls -t test_results/with-cache_long_context_high_reuse_*_stats_*.json | head -1)

# 生成报告
python3 reports/compare_results.py \
    --stats "$STATS_FILE" \
    --output cross_node_test_report.md

# 查看报告
cat cross_node_test_report.md
```

### 5. 验证结果

检查报告中的关键指标：

```markdown
#### 🌐 跨节点测试信息

- **Round 1 (Baseline)**: 节点 A - `http://10.237.65.81:8080/v1`
- **Round 2 (Cache Hit)**: 节点 B - `http://10.237.65.95:8080/v1`
- **KV Cache 传输**: ✅ 从节点 A 传输到节点 B

| 指标 | Baseline (Round 1) | Cache Hit (Round 2) | 改善 | 目标 | 状态 |
|------|-------------------|---------------------|------|------|------|
| TTFT (avg) | 1500.00 ms | 450.00 ms | -70.0% | -60% | ✅ |
| 吞吐量 (req/s) | 1.20 | 3.50 | +191.7% | +150% | ✅ |
```

**✅ 成功！** TTFT 降低 70%，吞吐量提升 191.7%，说明跨节点 KV Cache 传输工作正常。

---

## 多场景跨节点测试

如果要测试多个场景：

### 方法 1: 逐个场景手动测试

```bash
# 场景 1: 长上下文
python3 scripts/test_simple.py \
    --config configs/test_cross_node.yaml \
    --scenarios long_context_high_reuse

# 手动清理缓存（重启 vLLM 或等待）
pkill -f vllm && bash scripts/run.sh

# 场景 2: 多轮对话
python3 scripts/test_simple.py \
    --config configs/test_cross_node.yaml \
    --scenarios multi_turn_conversation

# 生成对比报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "跨节点-长上下文" --stats test_results/stats1.json \
    --scenario "跨节点-多轮对话" --stats test_results/stats2.json \
    --output cross_node_comparison.md
```

### 方法 2: 对比单机 vs 跨节点

```bash
# 1. 单机测试（两轮都用节点 A）
vim configs/test_single_node.yaml
# endpoints_per_round:
#   1: "http://10.237.65.81:8080/v1"
#   2: "http://10.237.65.81:8080/v1"  # 相同节点

python3 scripts/test_simple.py --config configs/test_single_node.yaml

# 2. 跨节点测试（节点 A → 节点 B）
python3 scripts/test_simple.py --config configs/test_cross_node.yaml

# 3. 生成对比报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "单机测试-Qwen2.5-72B" --stats test_results/single_stats.json \
    --scenario "跨节点测试-Qwen2.5-72B" --stats test_results/cross_stats.json \
    --output single_vs_cross_node.md
```

报告会显示：
```markdown
| 测试场景 | Baseline | Cache Hit | 降低 | 状态 |
|---------|----------|-----------|------|------|
| 单机测试-Qwen2.5-72B | 1500 ms | 400 ms | 73.3% | ✅ |
| 🌐 跨节点测试-Qwen2.5-72B | 1500 ms | 450 ms | 70.0% | ✅ |
```

**结论**: 跨节点测试的 TTFT 略高（多了网络传输开销），但仍然达到了 70% 的降低率，证明跨节点缓存传输有效。

---

## 总结

### 关键配置

```yaml
endpoints_per_round:
  1: "http://节点A:端口/v1"  # Round 1
  2: "http://节点B:端口/v1"  # Round 2
```

### 报告识别

- 🌐 标识表示跨节点测试
- 报告会显示详细的节点信息
- 自动对比单机和跨节点性能

### 性能目标

- TTFT 降低 ≥60%
- 吞吐量提升 ≥150%
- 达到这些指标说明跨节点传输成功

---

**需要帮助？** 查看：
- `START_HERE_MANUAL.md` - 基础测试指南
- `IMPORTANT_CACHE_ISOLATION.md` - 缓存隔离说明
- `README.md` - 总体说明
