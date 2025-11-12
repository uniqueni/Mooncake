# 简化测试指南 - 已有 Mooncake 和 OpenAI 接口

适用于已经部署好 Mooncake 和有 OpenAI 兼容接口的场景。

## 📋 前提条件

你已经有：
- ✅ Mooncake Master 运行中（IP:Port）
- ✅ 一个遵循 OpenAI 协议的模型服务接口
- ✅ 模型：72B 或 671B

## 🎯 测试目标

测试两种场景：
1. **PD 分离模式** - 使用 LMCache + Mooncake 的缓存效果
2. **非 PD 分离模式** - 不使用 Mooncake，测试基线性能

## ⚙️ LMCache 配置

### 你的服务需要做什么

如果你要测试 **PD 分离模式**（使用 LMCache + Mooncake），你的 vLLM 或其他服务需要：

#### 1. 安装 LMCache

```bash
pip install lmcache
```

#### 2. 创建 LMCache 配置文件

创建 `lmcache_config.yaml`:

```yaml
# LMCache 配置 - 连接到你的 Mooncake

# Chunk 配置
chunk_size: 256  # KV Cache 分块大小，建议 128-512

# Mooncake Store 配置
remote_url: "mooncakestore://YOUR_MOONCAKE_IP:50052/"  # 替换为你的 Mooncake IP
remote_serde: "naive"  # 序列化方式

# 本地 CPU 缓存（可选）
local_cpu: false
max_local_cpu_size: 100

# Mooncake 详细配置
extra_config:
  # 本机 IP（运行 vLLM 的机器 IP）
  local_hostname: "YOUR_VLLM_IP"

  # Mooncake Metadata Server
  metadata_server: "http://YOUR_MOONCAKE_IP:8080/metadata"

  # 传输协议
  protocol: "rdma"  # 或 "tcp"（如果没有 RDMA）

  # RDMA 设备（如果使用 RDMA）
  device_name: "mlx5_0"  # 查看: rdma link

  # Mooncake Master 地址
  master_server_address: "YOUR_MOONCAKE_IP:50052"

  # 缓存大小配置
  global_segment_size: 107374182400  # 100GB（72B 模型推荐）
  local_buffer_size: 2147483648      # 2GB

  # 超时配置
  transfer_timeout: 10  # 大模型建议 10 秒

  # 元数据
  save_chunk_meta: false
```

#### 3. 启动服务时加载 LMCache

**如果使用 vLLM：**

```bash
export LMCACHE_CONFIG_FILE=/path/to/lmcache_config.yaml
export LMCACHE_USE_EXPERIMENTAL=True

vllm serve YOUR_MODEL \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 8
```

**如果使用其他框架：**
- 参考 LMCache 文档：https://docs.lmcache.ai/

---

## 🧪 测试配置

### 修改测试配置文件

编辑 `test_config_simple.yaml`:

```yaml
# OpenAI 兼容接口配置
openai_api:
  # 你的 OpenAI 接口地址
  base_url: "http://YOUR_API_IP:8000/v1"  # 替换为你的接口地址
  api_key: "dummy"  # 如果不需要可以是任意值

  # 模型名称（和你的接口返回的模型名一致）
  model_name: "Qwen/Qwen2.5-72B-Instruct"  # 或 "deepseek-ai/DeepSeek-R1-671B"

# Mooncake 配置（用于监控）
mooncake:
  master_ip: "YOUR_MOONCAKE_IP"
  master_port: 50052
  metadata_port: 8080
  metrics_port: 9004

# 测试模型配置
model:
  name: "Qwen/Qwen2.5-72B-Instruct"
  max_tokens: 128
  temperature: 0.0

# 测试场景
scenarios:
  - long_context_high_reuse  # 长上下文高重用
  - multi_turn_conversation  # 多轮对话
  - cold_start              # 冷启动基线

# 测试参数
test:
  rounds: 2  # 测试轮数（Round 1: Cold Start, Round 2: Cache Hit）
  requests_per_scenario: 30  # 每个场景的请求数
  concurrency: null  # 并发限制（null = 不限制）
```

---

## 🚀 执行测试

### 场景 1: 测试带 LMCache 的缓存效果

```bash
# 确保你的服务已启动并配置了 LMCache

# 运行测试
python3 test_simple.py \
  --config test_config_simple.yaml \
  --mode with-cache \
  --scenarios long_context_high_reuse multi_turn_conversation

# 查看结果
ls test_results/
```

### 场景 2: 测试不带 LMCache 的基线性能

```bash
# 重启你的服务，不加载 LMCache 配置
# 或者连接到另一个没有 LMCache 的服务

# 运行测试
python3 test_simple.py \
  --config test_config_simple.yaml \
  --mode baseline \
  --scenarios long_context_high_reuse

# 查看结果
ls test_results/
```

### 场景 3: 对比两种模式

```bash
# 对比有缓存 vs 无缓存
python3 compare_results.py \
  --with-cache-stats test_results/with_cache_*_stats_*.json \
  --baseline-stats test_results/baseline_*_stats_*.json \
  --generate-charts

# 查看对比报告
cat comparison_report.md
```

---

## 📊 关键配置参数说明

### LMCache 配置参数

#### 1. `chunk_size`
```yaml
chunk_size: 256
```
- **作用**: KV Cache 分块大小，越小缓存粒度越细
- **推荐值**:
  - 72B 模型: 256
  - 671B 模型: 512
- **调优**: 如果缓存命中率低，尝试更小的值（128）

#### 2. `protocol`
```yaml
protocol: "rdma"  # 或 "tcp"
```
- **rdma**: 高性能，需要 RDMA 网卡和驱动
- **tcp**: 兼容性好，性能较低
- **查看 RDMA 设备**: `rdma link` 或 `ibstatus`

#### 3. `device_name`
```yaml
device_name: "mlx5_0"
```
- **查看设备名**: `rdma link`
- **多设备**: 用逗号分隔，如 `"mlx5_0,mlx5_1"`

#### 4. `global_segment_size`
```yaml
global_segment_size: 107374182400  # 100GB
```
- **作用**: Mooncake Store 的全局缓存大小
- **推荐值**:
  - 72B 模型: 100GB
  - 671B 模型: 200GB+
- **根据内存调整**: 不要超过可用内存的 70%

#### 5. `local_buffer_size`
```yaml
local_buffer_size: 2147483648  # 2GB
```
- **作用**: 本地传输缓冲区
- **推荐值**: 1-4GB
- **调优**: 增大可提升传输效率

---

## 🔍 验证配置

### 1. 检查 Mooncake 连接

```bash
# 检查 Mooncake Master 是否可访问
curl http://YOUR_MOONCAKE_IP:9004/metrics | grep master_key_count

# 检查 Metadata 服务
curl http://YOUR_MOONCAKE_IP:8080/metadata
```

### 2. 检查 OpenAI 接口

```bash
# 测试接口是否可用
curl http://YOUR_API_IP:8000/v1/models

# 发送测试请求
curl http://YOUR_API_IP:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "YOUR_MODEL_NAME",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

### 3. 验证 LMCache 加载

如果使用 vLLM，启动日志应该包含：
```
INFO:     LMCache config loaded: ...
INFO:     Using Mooncake Store backend
```

---

## 📈 查看测试结果

### 测试输出示例

```
================================================================================
🚀 测试模式: with-cache
================================================================================

🧪 测试场景: long_context_high_reuse
生成了 30 个测试请求
将运行 2 轮测试

📊 Round 1/2 - Cold Start
  已完成 30/30 个请求...

📈 统计结果:
  总请求数:         30
  成功请求:         30
  平均 TTFT:        21,245.67ms
  平均吞吐量:       0.25 req/s

📊 Round 2/2 - Cache Hit
  已完成 30/30 个请求...

📈 统计结果:
  平均 TTFT:        7,123.45ms

🎯 缓存效果:
  TTFT 降低:        +66.5%
  吞吐量提升:       +195.7%
  ✅ 缓存效果优秀！
```

### 关键指标解释

- **TTFT (Time to First Token)**: 首 token 延迟
  - Cold Start: 高（需要 Prefill + KV 缓存写入）
  - Cache Hit: 低（直接加载缓存）
  - **目标**: Cache Hit 降低 60-70%

- **TPOT (Time per Output Token)**: 每个输出 token 的平均时间
  - 反映 Decode 阶段性能
  - **目标**: 两轮应该接近

- **吞吐量**: 系统处理请求的速度
  - **目标**: Cache Hit 提升 150-200%

---

## ⚠️ 常见问题

### Q1: 如何确认 LMCache 正常工作？

**方法 1: 查看 Mooncake 指标**
```bash
# KV Cache 键数量应该在测试时增长
watch -n 1 'curl -s http://YOUR_MOONCAKE_IP:9004/metrics | grep master_key_count'

# 查看 Put/Get 请求
curl -s http://YOUR_MOONCAKE_IP:9004/metrics | grep -E "put|get"
```

**方法 2: 查看服务日志**
- vLLM 日志应该显示 KV Cache 写入/读取

**方法 3: 对比测试**
- Round 2 的 TTFT 应该明显低于 Round 1

### Q2: 缓存效果不明显怎么办？

**1. 调整 chunk_size**
```yaml
chunk_size: 128  # 尝试更小的值
```

**2. 检查请求是否真的共享前缀**
- 查看测试场景配置
- 确保 `reuse_ratio` 足够高

**3. 检查 Mooncake 缓存空间**
```bash
# 查看已分配内存
curl -s http://YOUR_MOONCAKE_IP:9004/metrics | grep master_allocated_bytes
```

### Q3: TCP vs RDMA 如何选择？

**使用 TCP 如果：**
- 没有 RDMA 网卡
- 测试/开发环境
- 小规模部署

**使用 RDMA 如果：**
- 有 RDMA 网卡（InfiniBand/RoCE）
- 生产环境
- 需要最佳性能

**验证 RDMA：**
```bash
# 查看 RDMA 设备
rdma link

# 或
ibstatus
```

### Q4: 671B 模型配置有什么不同？

```yaml
# 671B 需要更大的缓存和更长的超时
extra_config:
  global_segment_size: 214748364800  # 200GB
  local_buffer_size: 4294967296      # 4GB
  transfer_timeout: 20               # 20 秒
```

---

## 📝 配置检查清单

测试前确认：

- [ ] **Mooncake Master 运行中**
  ```bash
  curl http://YOUR_MOONCAKE_IP:9004/metrics
  ```

- [ ] **OpenAI 接口可访问**
  ```bash
  curl http://YOUR_API_IP:8000/v1/models
  ```

- [ ] **LMCache 配置文件已创建**
  - `lmcache_config.yaml` 中的 IP 地址正确

- [ ] **服务已加载 LMCache**
  - 启动命令包含 `LMCACHE_CONFIG_FILE`

- [ ] **测试配置文件已修改**
  - `test_config_simple.yaml` 中的 URL 正确

- [ ] **网络连通性**
  ```bash
  ping YOUR_MOONCAKE_IP
  nc -zv YOUR_MOONCAKE_IP 50052
  ```

---

## 🎯 快速测试流程

### 1 分钟快速验证

```bash
# 1. 创建配置（复制模板并修改 IP）
cp test_config_simple.yaml my_config.yaml
vim my_config.yaml  # 修改 IP 地址

# 2. 运行简单测试（只测 1 个场景，10 个请求）
python3 test_simple.py \
  --config my_config.yaml \
  --mode with-cache \
  --scenarios cold_start \
  --requests 10 \
  --rounds 2

# 3. 查看结果
# 如果 Round 2 的 TTFT 明显低于 Round 1，说明缓存工作正常
```

### 完整测试流程

```bash
# 1. 带缓存测试
python3 test_simple.py \
  --config my_config.yaml \
  --mode with-cache \
  --scenarios long_context_high_reuse multi_turn_conversation \
  --rounds 2

# 2. 基线测试（不带缓存）
python3 test_simple.py \
  --config my_config.yaml \
  --mode baseline \
  --scenarios long_context_high_reuse \
  --rounds 2

# 3. 生成对比报告
python3 compare_results.py \
  --with-cache-stats test_results/with_cache_*_stats_*.json \
  --baseline-stats test_results/baseline_*_stats_*.json \
  --output comparison.md

# 4. 查看报告
cat comparison.md
```

---

## 📞 需要帮助？

1. **LMCache 文档**: https://docs.lmcache.ai/
2. **Mooncake 文档**: https://kvcache-ai.github.io/Mooncake/
3. **检查日志**: 查看 vLLM 或 Mooncake 的日志输出

---

**就是这么简单！🎉**

只需要：
1. 配置 LMCache（lmcache_config.yaml）
2. 修改测试配置（test_config_simple.yaml）
3. 运行测试（test_simple.py）
