# 大模型缓存效果测试指南（72B / 671B）

专用于测试 **Qwen2.5-72B-Instruct** 和 **DeepSeek-R1-671B** 模型在 vLLM + LMCache + Mooncake 环境下的缓存效果。

## 📋 目录

- [快速开始](#快速开始)
- [测试模式](#测试模式)
- [容器化部署](#容器化部署)
- [测试执行](#测试执行)
- [性能对比](#性能对比)
- [结果分析](#结果分析)
- [常见问题](#常见问题)

---

## 快速开始

### 最快 3 步开始

```bash
# 1. 修改配置（选择要测试的模型）
cd tests
vim test_config_large_models.yaml
# 修改 active_model: "qwen_72b" 或 "deepseek_671b"

# 2. 启动容器（选择测试模式）
# PD 分离模式：
docker-compose up -d mooncake-master vllm-prefiller vllm-decoder vllm-proxy prometheus grafana

# 非 PD 分离模式：
docker-compose --profile non-disagg up -d mooncake-master vllm-server prometheus grafana

# 3. 运行测试
python3 test_pd_disagg.py     # PD 分离模式
# 或
python3 test_non_disagg.py    # 非 PD 分离模式
```

---

## 测试模式

本测试套件支持两种部署和测试模式：

### 模式 1: PD 分离（Prefill-Decode Disaggregation）

**架构图：**
```
Client → Proxy → Prefiller (Prefill) → Mooncake Store (KV Cache) → Decoder (Decode)
                     ↓
                  8 GPUs                                              8 GPUs
```

**特点：**
- ✅ Prefill 和 Decode 分离在不同节点/容器
- ✅ 使用 LMCache + Mooncake 管理 KV Cache
- ✅ 支持跨节点 KV Cache 传输
- ✅ 资源利用率更高
- ⚠️ 网络开销（KV Cache 传输）

**测试脚本：** `test_pd_disagg.py`

**测试指标：**
- TTFT (Time to First Token) = Prefill 时间 + KV 传输时间 + 首次 Decode
- TPOT (Time per Output Token) = Decode 阶段每 token 时间
- 缓存命中后的性能提升
- KV Cache 传输效率

**适用场景：**
- 大规模生产环境
- 需要高资源利用率
- 长上下文场景
- 多轮对话

### 模式 2: 非 PD 分离（Traditional Deployment）

**架构图：**
```
Client → vLLM Server (Prefill + Decode)
              ↓
           8 GPUs
```

**特点：**
- ✅ 部署简单，单一服务
- ✅ 无网络传输开销
- ✅ 可以使用 vLLM prefix caching
- ⚠️ 资源利用率较低
- ⚠️ Prefill 和 Decode 竞争资源

**测试脚本：** `test_non_disagg.py`

**测试指标：**
- TTFT (Time to First Token) = Prefill + 首次 Decode
- TPOT (Time per Output Token) = Decode 阶段每 token 时间
- 缓存命中后的性能提升
- 基线性能

**适用场景：**
- 中小规模部署
- 快速原型验证
- 低延迟要求
- 简单应用

---

## 容器化部署

### 前置要求

```bash
# 安装 Docker 和 Docker Compose
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin

# 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 验证 GPU 在容器中可用
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### 部署步骤

#### 步骤 1: 配置模型和测试参数

编辑 `test_config_large_models.yaml`:

```yaml
# 选择要测试的模型
active_model: "qwen_72b"  # 或 "deepseek_671b"

# 根据实际硬件调整 GPU 配置
models:
  qwen_72b:
    tensor_parallel_size: 8  # 72B 需要 8 卡
  deepseek_671b:
    tensor_parallel_size: 64  # 671B 需要 64 卡（8 nodes × 8 GPUs）
    pipeline_parallel_size: 8
```

#### 步骤 2: 准备 Mooncake 配置文件

创建 `configs/mooncake-prefiller-config.yaml`:

```yaml
chunk_size: 256
remote_url: "mooncakestore://mooncake-master:50052/"
remote_serde: "naive"
local_cpu: false
max_local_cpu_size: 100

extra_config:
  local_hostname: "vllm-prefiller"
  metadata_server: "http://mooncake-master:8080/metadata"
  protocol: "tcp"  # 或 "rdma"（如果容器支持）
  device_name: "mlx5_0"
  master_server_address: "mooncake-master:50052"
  global_segment_size: 107374182400  # 100GB for 72B
  local_buffer_size: 2147483648  # 2GB
  transfer_timeout: 10
  save_chunk_meta: false
```

创建 `configs/mooncake-decoder-config.yaml`:

```yaml
chunk_size: 256
remote_url: "mooncakestore://mooncake-master:50052/"
remote_serde: "naive"
local_cpu: false
max_local_cpu_size: 100

extra_config:
  local_hostname: "vllm-decoder"
  metadata_server: "http://mooncake-master:8080/metadata"
  protocol: "tcp"
  device_name: "mlx5_0"
  master_server_address: "mooncake-master:50052"
  global_segment_size: 107374182400  # 100GB
  local_buffer_size: 2147483648  # 2GB
  transfer_timeout: 10
  save_chunk_meta: false
```

#### 步骤 3: 启动服务

**PD 分离模式：**

```bash
# 启动所有 PD 分离服务
docker-compose up -d mooncake-master vllm-prefiller vllm-decoder vllm-proxy prometheus grafana

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f mooncake-master
docker-compose logs -f vllm-prefiller
docker-compose logs -f vllm-decoder
docker-compose logs -f vllm-proxy
```

**非 PD 分离模式：**

```bash
# 启动单服务模式
docker-compose --profile non-disagg up -d mooncake-master vllm-server prometheus grafana

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f vllm-server
```

#### 步骤 4: 验证服务

```bash
# 验证 Mooncake Master
curl http://localhost:9004/metrics | grep master_key_count

# 验证 vLLM 服务
# PD 分离模式：
curl http://localhost:9000/v1/models

# 非 PD 分离模式：
curl http://localhost:8000/v1/models

# 验证 Prometheus
curl http://localhost:9090/-/healthy

# 访问 Grafana
open http://localhost:3000  # 用户名: admin, 密码: admin
```

---

## 测试执行

### 测试 PD 分离模式

```bash
# 基础测试（推荐的场景）
python3 test_pd_disagg.py \
  --config test_config_large_models.yaml \
  --scenarios long_context_high_reuse multi_turn_conversation \
  --rounds 2

# 测试所有场景
python3 test_pd_disagg.py \
  --scenarios long_context_high_reuse code_generation multi_turn_conversation batch_processing cold_start \
  --rounds 2

# 限制并发测试
python3 test_pd_disagg.py \
  --scenarios long_context_high_reuse \
  --rounds 3 \
  --concurrency 5

# 指定输出目录
python3 test_pd_disagg.py \
  --output-dir results/pd_disagg_qwen72b
```

**预期输出：**

```
================================================================================
🚀 vLLM PD 分离模式 + LMCache + Mooncake 缓存测试
================================================================================
✓ PD 分离模式测试配置加载成功
  模型: Qwen/Qwen2.5-72B-Instruct
  Proxy: http://vllm-proxy:9000/v1
  Prefiller: vllm-prefiller:8100
  Decoder: vllm-decoder:8200

================================================================================
🧪 PD 分离测试场景: long_context_high_reuse
   长文档分析，多个问题共享相同的长上下文
================================================================================
生成了 30 个测试请求
将运行 2 轮测试

────────────────────────────────────────────────────────────────────────────────
📊 Round 1/2
   🥶 Cold Start - KV Cache 冷启动
────────────────────────────────────────────────────────────────────────────────
  已完成 30/30 个请求...

📈 统计结果:
  总请求数:         30
  成功请求:         30
  失败请求:         0
  总耗时:           120.45s

⏱️  TTFT (Prefill + KV Transfer + First Token):
  平均:             21,245.67ms
  中位数:           22,102.34ms
  P90:              28,456.12ms
  P99:              32,789.45ms

🔄 PD 分离阶段时间（估算）:
  平均 Prefill:     14,871.97ms
  平均 Decode:      3,245.78ms

⚡ TPOT (Decode 阶段):
  平均:             145.23ms/token
  中位数:           142.56ms/token
  P90:              178.90ms/token

🕐 端到端延迟:
  平均:             25.34s
  中位数:           26.12s
  P90:              31.45s
  P99:              35.67s

🚀 吞吐量:
  请求吞吐量:       0.25 req/s
  Token 吞吐量:     620.34 tokens/s
  输出 Token:       16.78 tokens/s

────────────────────────────────────────────────────────────────────────────────
📊 Round 2/2
   🔥 Cache Hit - 测试缓存效果
────────────────────────────────────────────────────────────────────────────────
  已完成 30/30 个请求...

📈 统计结果:
  ...
  TTFT 平均:        7,123.45ms  (降低 66.5%)

🎯 PD 分离 + 缓存效果 (相比 Round 1):
  ⚡ TTFT 降低:         +66.5%
  🔄 Prefill 时间降低:  +68.2%
  📉 延迟降低:         +64.8%
  📈 吞吐量提升:       +195.7%

  ✅ 达到性能目标！TTFT 降低 66.5% (目标: 60%)
  ✅ 达到性能目标！吞吐量提升 195.7% (目标: 150%)

💾 结果已保存:
  详细结果: test_results/pd_disagg_qwen_72b_results_20250111_143256.json
  统计摘要: test_results/pd_disagg_qwen_72b_stats_20250111_143256.json

================================================================================
✅ PD 分离测试完成!
================================================================================
```

### 测试非 PD 分离模式

```bash
# 基础测试
python3 test_non_disagg.py \
  --config test_config_large_models.yaml \
  --scenarios long_context_high_reuse multi_turn_conversation \
  --rounds 2

# 完整测试
python3 test_non_disagg.py \
  --scenarios long_context_high_reuse batch_processing cold_start \
  --rounds 3 \
  --output-dir results/non_disagg_qwen72b
```

### 同时运行两种模式对比

```bash
# 脚本 1: PD 分离模式
python3 test_pd_disagg.py \
  --scenarios long_context_high_reuse \
  --rounds 2 \
  --output-dir results/pd_disagg &

PD_PID=$!

# 等待 PD 分离测试完成
wait $PD_PID

# 切换到非 PD 分离模式
docker-compose stop vllm-prefiller vllm-decoder vllm-proxy
docker-compose --profile non-disagg up -d vllm-server

sleep 30  # 等待服务启动

# 脚本 2: 非 PD 分离模式
python3 test_non_disagg.py \
  --scenarios long_context_high_reuse \
  --rounds 2 \
  --output-dir results/non_disagg

# 对比结果
python3 compare_results.py \
  --pd-stats results/pd_disagg/pd_disagg_qwen_72b_stats_*.json \
  --non-pd-stats results/non_disagg/non_disagg_qwen_72b_stats_*.json
```

---

## 性能对比

### 预期性能（72B 模型）

| 指标 | 非 PD 分离 (Baseline) | PD 分离 (Cold Start) | PD 分离 (Cache Hit) | 改善 |
|------|---------------------|---------------------|-------------------|------|
| **TTFT** | 3,000-5,000ms | 20,000-25,000ms | 7,000-9,000ms | **↓ 65%** |
| **TPOT** | 120-150ms | 140-160ms | 120-140ms | **↓ 10%** |
| **端到端延迟** | 10-15s | 25-30s | 10-12s | **↓ 60%** |
| **吞吐量** | 1-2 req/s | 0.2-0.3 req/s | 0.6-0.8 req/s | **↑ 200%** |

**解释：**

1. **Cold Start**: PD 分离模式下，首次请求需要 Prefill + KV 传输，延迟较高
2. **Cache Hit**: 缓存命中后，可以跳过大部分 Prefill，大幅降低延迟
3. **TPOT**: Decode 阶段性能相近，PD 分离略有开销
4. **吞吐量**: PD 分离模式在缓存命中时可以显著提升系统吞吐量

### 预期性能（671B 模型）

| 指标 | 非 PD 分离 | PD 分离 (Cold) | PD 分离 (Cache Hit) | 改善 |
|------|-----------|---------------|-------------------|------|
| **TTFT** | 15,000-20,000ms | 60,000-80,000ms | 20,000-25,000ms | **↓ 70%** |
| **吞吐量** | 0.1-0.2 req/s | 0.02-0.05 req/s | 0.15-0.20 req/s | **↑ 300%** |

---

## 结果分析

### 理解关键指标

#### 1. TTFT (Time to First Token)

**PD 分离模式：**
- **Cold Start**: 包含 Prefill + KV Cache 生成 + 网络传输 + 首次 Decode
- **Cache Hit**: 主要是 KV Cache 加载 + 首次 Decode（跳过 Prefill）

**非 PD 分离模式：**
- 包含 Prefill + 首次 Decode（本地操作，无网络开销）

**目标：**
- PD 分离 Cache Hit 应该比 Cold Start 降低 **60-70%**
- PD 分离 Cache Hit 应该接近非 PD 分离的 TTFT

#### 2. TPOT (Time per Output Token)

衡量 Decode 阶段的效率：
- 两种模式应该相近
- PD 分离可能有轻微的网络/调度开销

**目标：**
- PD 分离 TPOT 不应超过非 PD 分离 **20%**

#### 3. 吞吐量

**系统级指标：**
- PD 分离可以通过资源隔离提升整体吞吐量
- 缓存命中后，Prefiller 可以处理新请求，Decoder 处理生成

**目标：**
- PD 分离 Cache Hit 吞吐量提升 **150-200%**

### 生成对比报告

```bash
# 生成 PD 分离报告
python3 generate_report.py \
  --stats results/pd_disagg/pd_disagg_qwen_72b_stats_*.json \
  --output-dir reports/pd_disagg \
  --format both \
  --generate-charts

# 生成非 PD 分离报告
python3 generate_report.py \
  --stats results/non_disagg/non_disagg_qwen_72b_stats_*.json \
  --output-dir reports/non_disagg \
  --format both \
  --generate-charts

# 查看报告
open reports/pd_disagg/report.html
open reports/non_disagg/report.html
```

---

## 常见问题

### Q1: 671B 模型需要多少 GPU？

**答案：** 671B 模型需要至少 **64 个 GPU**

**配置示例：**
```yaml
models:
  deepseek_671b:
    tensor_parallel_size: 64  # 64 GPUs
    pipeline_parallel_size: 8  # 8 个 pipeline 阶段
```

**部署方案：**
- **方案 1**: 8 个节点 × 8 GPUs = 64 GPUs
- **方案 2**: 16 个节点 × 4 GPUs = 64 GPUs

**Docker Compose**: 需要使用 Docker Swarm 或 Kubernetes 进行多节点编排

### Q2: 为什么 PD 分离 Cold Start 比非 PD 分离慢很多？

**原因：**
1. **网络传输**: KV Cache 需要从 Prefiller 传输到 Decoder
2. **序列化开销**: KV Cache 序列化/反序列化
3. **Mooncake Store**: 写入和读取 KV Cache 的开销

**正常情况：**
- Cold Start TTFT 可能是非 PD 分离的 **3-5 倍**
- 这是预期行为，因为增加了分布式开销

**关键：**
- Cache Hit 后应该显著降低，接近或优于非 PD 分离模式

### Q3: 如何优化 PD 分离的性能？

**优化建议：**

1. **调整 chunk_size**
```yaml
mooncake:
  lmcache:
    chunk_size: 128  # 尝试更小的值提高缓存粒度
```

2. **增加网络带宽**
- 使用 RDMA 代替 TCP
- 使用多个 RDMA 网卡聚合带宽

3. **调整缓存大小**
```yaml
mooncake:
  transfer:
    global_segment_size: 214748364800  # 200GB
    local_buffer_size: 4294967296  # 4GB
```

4. **优化并发**
```bash
# 测试不同并发级别
python3 test_pd_disagg.py --concurrency 1   # 串行
python3 test_pd_disagg.py --concurrency 5   # 中等并发
python3 test_pd_disagg.py --concurrency 10  # 高并发
```

### Q4: 容器内存不足怎么办？

**解决方案：**

1. **增加 shm_size**
```yaml
services:
  vllm-server:
    shm_size: '128gb'  # 增加共享内存
```

2. **减小 global_segment_size**
```yaml
mooncake:
  transfer:
    global_segment_size: 53687091200  # 50GB
```

3. **使用 swap（不推荐）**
```bash
sudo swapon --show
sudo fallocate -l 100G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q5: 如何监控测试过程？

**实时监控：**

```bash
# 终端 1: 监控 GPU
watch -n 1 nvidia-smi

# 终端 2: 监控 Mooncake 指标
watch -n 1 'curl -s http://localhost:9004/metrics | grep -E "master_key_count|master_allocated_bytes"'

# 终端 3: 监控容器资源
docker stats

# 终端 4: 查看日志
docker-compose logs -f vllm-prefiller vllm-decoder
```

**Grafana Dashboard:**
- 访问: http://localhost:3000
- 导入: `grafana-dashboard-cache-test.json`
- 实时查看指标曲线

---

## 性能调优 Checklist

- [ ] **GPU 配置正确**
  - 72B: 8 GPUs
  - 671B: 64 GPUs

- [ ] **网络优化**
  - 使用 RDMA（如果可能）
  - 多网卡聚合带宽
  - 调整 MTU 大小

- [ ] **内存优化**
  - 足够的 RAM（推荐 512GB+ for 72B）
  - 大的 shm_size（64GB+）
  - global_segment_size 根据内存调整

- [ ] **模型加载**
  - 预先下载模型到本地
  - 使用 SSD 存储模型

- [ ] **并发调优**
  - 测试不同并发级别
  - 找到最优并发数

- [ ] **监控就绪**
  - Prometheus 正常抓取指标
  - Grafana Dashboard 配置完成
  - 日志输出正常

---

## 下一步

完成测试后：

1. **生成对比报告**
```bash
python3 compare_results.py \
  --pd-stats results/pd_disagg/*.json \
  --non-pd-stats results/non_disagg/*.json \
  --output comparison_report.html
```

2. **分析 Grafana 数据**
- 导出指标到 CSV
- 生成时间序列图表

3. **优化配置**
- 根据测试结果调整参数
- 重新测试验证改进

4. **撰写测试报告**
- 包含性能对比表
- 分析缓存效果
- 给出部署建议

---

**祝测试顺利！🚀**

如有问题，请查看：
- Mooncake 文档: https://kvcache-ai.github.io/Mooncake/
- vLLM 文档: https://docs.vllm.ai/
- LMCache 文档: https://docs.lmcache.ai/
