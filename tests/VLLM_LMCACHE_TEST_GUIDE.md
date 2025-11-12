# vLLM + LMCache + Mooncake 缓存效果测试指南

这是一份完整的测试指南，帮助你测试 vLLM、LMCache 和 Mooncake 集成后的 KV Cache 缓存效果。

## 📋 目录

- [系统要求](#系统要求)
- [推荐模型](#推荐模型)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [测试场景说明](#测试场景说明)
- [配置说明](#配置说明)
- [结果分析](#结果分析)
- [常见问题](#常见问题)
- [进阶使用](#进阶使用)

---

## 系统要求

### 硬件要求

- **最小配置**：
  - 2 台机器，每台至少 1 个 GPU（用于 Decoder 和 Prefiller）
  - RDMA 网络（推荐 RoCE 或 InfiniBand）
  - 推荐配置：每台 2-4 个 GPU

- **推荐配置**：
  - 2 台机器，每台 4-8 个 H800/A800/H100 GPU
  - 200 Gbps 或更高的 RDMA 网络
  - 足够的内存用于缓存（推荐 256GB+）

### 软件要求

- **操作系统**：Linux（推荐 Ubuntu 20.04+）
- **Python**: 3.10+
- **CUDA**: 12.1+
- **依赖包**：
  ```bash
  pip install openai pyyaml matplotlib
  ```

### 已安装组件

- [x] **vLLM**: 请参考 [vLLM 官方文档](https://docs.vllm.ai/)
- [x] **LMCache**: 请参考 [LMCache 官方文档](https://docs.lmcache.ai/)
- [x] **Mooncake**: 请参考 [Mooncake 官方文档](https://kvcache-ai.github.io/Mooncake/)

---

## 推荐模型

根据不同的测试目标和资源情况，推荐以下模型：

### 1. 快速验证和开发（推荐新手）

**Qwen2.5-7B-Instruct-GPTQ-Int4**
- ✅ 量化版本，显存占用小
- ✅ 官方示例使用此模型
- ✅ 适合资源有限的环境
- 📊 预期缓存命中后延迟降低：50-70%

**适用场景**：
- 功能验证
- 快速开发和调试
- 学习和实验

### 2. 性能基准测试（推荐测试）

**Qwen2.5-72B-Instruct**
- ✅ LMCache 官方性能测试使用此模型
- ✅ 可以体现长上下文缓存的优势
- ⚠️ 需要 8×H800 或类似配置
- 📊 预期缓存命中后延迟降低：60-70%
- 📊 预期吞吐量提升：180-200%

**适用场景**：
- 正式性能测试
- 论文/报告数据
- 生产环境评估

### 3. 长上下文测试

**LLaMA3-70B**
- ✅ 支持长上下文（128k tokens）
- ✅ Mooncake 官方文档提到的模型
- 📊 40GB KV Cache（约 128k tokens）
- 📊 适合测试大规模 KV Cache 传输性能

**适用场景**：
- 长上下文场景测试
- 大规模 KV Cache 传输测试
- RAG 应用评估

### 4. 大规模 MoE 测试（进阶）

**DeepSeek-R1-671B**
- ✅ 大规模 MoE 模型
- ⚠️ 需要大规模 GPU 集群（96-128 GPUs）
- 📊 SGLang 文档中的案例

**适用场景**：
- 大规模集群测试
- MoE 模型专项测试
- 超大规模应用

### 选择建议

| 资源情况 | 推荐模型 | GPU 需求 | 测试目标 |
|---------|---------|---------|---------|
| 有限 | Qwen2.5-7B-GPTQ-Int4 | 2×单卡 | 功能验证 |
| 充足 | Qwen2.5-72B-Instruct | 2×4卡 | 性能基准 |
| 丰富 | LLaMA3-70B | 2×8卡 | 长上下文 |
| 集群 | DeepSeek-R1-671B | 96+卡 | 大规模测试 |

---

## 快速开始

### 最快 3 步开始测试

```bash
# 1. 修改配置文件，设置你的 IP 地址和模型
cd tests
vim test_config.yaml

# 2. 启动 vLLM 服务（Decoder + Prefiller + Proxy）
# 请参考下面的"详细步骤"部分

# 3. 运行测试
python3 test_vllm_lmcache_mooncake.py
```

### 使用自动化脚本（推荐）

```bash
# 运行完整测试（假设服务已启动）
./run_full_test.sh

# 查看帮助
./run_full_test.sh --help

# 自定义测试场景和轮数
./run_full_test.sh --scenarios "high_reuse medium_reuse" --rounds 3
```

---

## 详细步骤

### 步骤 1: 准备配置文件

编辑 `test_config.yaml`，修改以下关键配置：

```yaml
# 1. 修改机器 IP 地址
machines:
  machine_a:  # Decoder 节点
    ip: "YOUR_MACHINE_A_IP"  # 替换为实际 IP

  machine_b:  # Prefiller 节点
    ip: "YOUR_MACHINE_B_IP"  # 替换为实际 IP

# 2. 修改模型名称
model:
  name: "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4"  # 或其他模型

# 3. 修改 RDMA 设备名称（如果需要）
mooncake:
  device_name: "mlx5_0"  # 查看你的 RDMA 设备名
```

**检查 RDMA 设备名称**：
```bash
# 查看 RDMA 设备
rdma link
# 或
ibstatus
```

### 步骤 2: 启动 Mooncake Master

在 Machine A 上启动 Mooncake Master：

```bash
# 方式 1: 使用默认参数
mooncake_master -port 50052 -max_threads 64 -metrics_port 9004 \
  --enable_http_metadata_server=true \
  --http_metadata_server_host=0.0.0.0 \
  --http_metadata_server_port=8080

# 方式 2: 后台运行
nohup mooncake_master -port 50052 -max_threads 64 -metrics_port 9004 \
  --enable_http_metadata_server=true \
  --http_metadata_server_host=0.0.0.0 \
  --http_metadata_server_port=8080 \
  > mooncake_master.log 2>&1 &
```

**验证启动成功**：
```bash
# 检查端口是否监听
nc -zv localhost 50052  # Master 端口
nc -zv localhost 8080   # Metadata 端口
nc -zv localhost 9004   # Metrics 端口

# 查看 Metrics
curl http://localhost:9004/metrics | grep master_
```

### 步骤 3: 配置 vLLM Decoder 和 Prefiller

#### 3.1 创建 Mooncake 配置文件

**在 Machine A (Decoder) 创建** `mooncake-decoder-config.yaml`:

```yaml
chunk_size: 256
remote_url: "mooncakestore://MACHINE_A_IP:50052/"
remote_serde: "naive"
local_cpu: False
max_local_cpu_size: 100

extra_config:
  local_hostname: "MACHINE_A_IP"
  metadata_server: "http://MACHINE_A_IP:8080/metadata"
  protocol: "rdma"
  device_name: "mlx5_0"  # 你的 RDMA 设备
  master_server_address: "MACHINE_A_IP:50052"
  global_segment_size: 32212254720  # 30GB
  local_buffer_size: 1073741824  # 1GB
  transfer_timeout: 1
  save_chunk_meta: False
```

**在 Machine B (Prefiller) 创建** `mooncake-prefiller-config.yaml`:

```yaml
chunk_size: 256
remote_url: "mooncakestore://MACHINE_A_IP:50052/"
remote_serde: "naive"
local_cpu: False
max_local_cpu_size: 100

extra_config:
  local_hostname: "MACHINE_B_IP"
  metadata_server: "http://MACHINE_A_IP:8080/metadata"
  protocol: "rdma"
  device_name: "mlx5_0"  # 你的 RDMA 设备
  master_server_address: "MACHINE_A_IP:50052"
  global_segment_size: 32212254720  # 30GB
  local_buffer_size: 1073741824  # 1GB
  transfer_timeout: 1
  save_chunk_meta: False
```

#### 3.2 启动 Decoder（在 Machine A）

```bash
cd vllm/examples/others/lmcache/disagg_prefill_lmcache_v1

# 修改启动脚本使用 Mooncake 配置
# 编辑 disagg_vllm_launcher.sh，将 decoder 部分的 config 改为：
# decode_config_file=$SCRIPT_DIR/configs/mooncake-decoder-config.yaml

# 启动 Decoder
bash disagg_vllm_launcher.sh decoder Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4
```

**验证 Decoder 启动**：
```bash
# 检查端口
nc -zv localhost 8200

# 检查日志
tail -f /path/to/decoder.log
```

#### 3.3 启动 Prefiller（在 Machine B）

```bash
cd vllm/examples/others/lmcache/disagg_prefill_lmcache_v1

# 修改启动脚本使用 Mooncake 配置
# 编辑 disagg_vllm_launcher.sh，将 prefiller 部分的 config 改为：
# prefill_config_file=$SCRIPT_DIR/configs/mooncake-prefiller-config.yaml

# 启动 Prefiller
bash disagg_vllm_launcher.sh prefiller Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4
```

**验证 Prefiller 启动**：
```bash
# 检查端口
nc -zv MACHINE_B_IP 8100

# 检查日志
tail -f /path/to/prefiller.log
```

#### 3.4 启动 Proxy Server

在任意机器（通常是 Machine A 或客户端机器）：

```bash
cd LMCache/examples/disagg_prefill

# 根据 LMCache issue #1342，需要注释掉 wait_decode_kv_ready
# 编辑 disagg_proxy_server.py，注释掉相关行

# 启动 Proxy
python3 disagg_proxy_server.py \
  --host localhost \
  --port 9000 \
  --prefiller-host MACHINE_B_IP \
  --prefiller-port 8100 \
  --decoder-host MACHINE_A_IP \
  --decoder-port 8200
```

**验证 Proxy 启动**：
```bash
# 检查端口
nc -zv localhost 9000

# 测试 API
curl http://localhost:9000/v1/models
```

### 步骤 4: 运行测试

```bash
cd tests

# 运行基础测试（所有场景，2 轮）
python3 test_vllm_lmcache_mooncake.py

# 运行特定场景
python3 test_vllm_lmcache_mooncake.py \
  --scenarios high_reuse medium_reuse \
  --rounds 3

# 限制并发
python3 test_vllm_lmcache_mooncake.py \
  --concurrency 10
```

**测试过程中监控**：

```bash
# 终端 1: 监控 Mooncake Metrics
watch -n 1 'curl -s http://MACHINE_A_IP:9004/metrics | grep -E "master_key_count|master_allocated_bytes"'

# 终端 2: 监控 GPU 使用
watch -n 1 nvidia-smi

# 终端 3: 监控网络
watch -n 1 rdma statistics show
```

### 步骤 5: 生成报告

测试完成后，自动生成报告：

```bash
# 使用最新的测试结果
python3 generate_report.py \
  --stats test_results/stats_XXXXXX.json \
  --results test_results/results_XXXXXX.json \
  --output-dir reports \
  --format both \
  --generate-charts

# 查看报告
open reports/report.html  # macOS
xdg-open reports/report.html  # Linux
```

### 步骤 6: 导入 Grafana Dashboard

```bash
# 1. 登录 Grafana
# 访问 http://localhost:3000

# 2. 导入 Dashboard
# - 点击 "+" -> "Import"
# - 上传 grafana-dashboard-cache-test.json
# - 选择 Prometheus 数据源
# - 点击 "Import"

# 3. 查看实时指标
# 在 Dashboard 中可以看到：
# - KV Cache 键总数
# - 已分配内存
# - Put/Get QPS
# - 请求计数
```

---

## 测试场景说明

测试套件包含 4 个预定义场景：

### 场景 1: 高重用率场景 (high_reuse)

**特点**：
- 所有请求共享相同的长前缀
- 模拟多轮对话或批处理场景
- 预期缓存命中率：90%+

**预期结果**：
- ✅ 延迟降低 60-70%
- ✅ 吞吐量提升 180-200%

**适用于**：
- 聊天机器人多轮对话
- 批量处理相似任务
- RAG 系统（相同文档）

### 场景 2: 中等重用率场景 (medium_reuse)

**特点**：
- 约 50% 的请求共享前缀
- 模拟混合工作负载
- 预期缓存命中率：40-60%

**预期结果**：
- ⚠️ 延迟降低 30-50%
- ⚠️ 吞吐量提升 50-100%

**适用于**：
- 混合场景测试
- 多用户并发
- 部分前缀重用的应用

### 场景 3: 低重用率场景 (low_reuse)

**特点**：
- 每个请求都是唯一的
- 模拟冷启动或随机请求
- 预期缓存命中率：<10%

**预期结果**：
- ❌ 延迟降低 <20%
- ❌ 吞吐量提升 <30%
- 主要测试基线性能

**适用于**：
- 冷启动性能测试
- 基线对比
- 最坏情况评估

### 场景 4: 长上下文场景 (long_context)

**特点**：
- 8k-128k tokens 的长上下文
- 测试大 KV Cache 传输
- 预期缓存命中率：70-90%

**预期结果**：
- ✅ 延迟降低 65-75%
- ✅ 吞吐量提升 200-300%
- 网络带宽利用率高

**适用于**：
- 长文档处理
- 代码生成
- 学术论文分析

---

## 配置说明

### test_config.yaml 核心配置

```yaml
# 1. Proxy 服务器地址
proxy:
  url: "http://localhost:9000/v1"

# 2. 模型配置
model:
  name: "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4"
  max_tokens: 64  # 每个请求生成的 token 数
  temperature: 0.0  # 确定性输出

# 3. 机器 IP 配置
machines:
  machine_a:
    ip: "192.168.80.135"  # 修改为实际 IP
  machine_b:
    ip: "192.168.80.136"  # 修改为实际 IP

# 4. Mooncake 网络配置
mooncake:
  protocol: "rdma"  # 或 "tcp"
  device_name: "mlx5_0"  # RDMA 设备
  global_segment_size: 32212254720  # 30GB
  local_buffer_size: 1073741824  # 1GB

# 5. 测试场景
test_scenarios:
  high_reuse:
    num_requests: 50
    reuse_ratio: 1.0
    prompt_template: "..."  # 提示词模板
```

### 性能调优参数

```yaml
# LMCache chunk_size 调优
# 较小的值：更细粒度的缓存，命中率可能更高
# 较大的值：传输效率更高，开销更小
# 推荐：256 (默认)
mooncake:
  chunk_size: 256

# 全局缓存大小
# 根据可用内存调整
# 推荐：30GB（用于 70B 模型）
mooncake:
  global_segment_size: 32212254720  # 30GB

# 本地缓冲区大小
# 影响传输批处理效率
# 推荐：1GB
mooncake:
  local_buffer_size: 1073741824  # 1GB
```

---

## 结果分析

### 理解输出指标

测试脚本会输出以下关键指标：

#### 1. 延迟指标

```
平均延迟:     1234.56ms
中位数延迟:   1100.23ms
P90 延迟:     1800.45ms
P99 延迟:     2500.78ms
```

**说明**：
- **平均延迟**：所有请求的平均响应时间
- **中位数延迟**：50% 的请求延迟低于此值
- **P90 延迟**：90% 的请求延迟低于此值
- **P99 延迟**：99% 的请求延迟低于此值（尾延迟）

**目标**：
- Cache Hit 后平均延迟应降低 60-70%
- P99 延迟改善更明显（70%+）

#### 2. 吞吐量指标

```
吞吐量:       12.34 req/s
```

**说明**：
- 每秒处理的请求数
- 反映系统整体性能

**目标**：
- Cache Hit 后吞吐量应提升 180-200%

#### 3. 缓存效果

```
🎯 缓存效果 (相比 Round 1):
  延迟降低:     +65.3%
  吞吐量提升:   +195.7%
  ✅ 缓存效果显著！
```

**评价标准**：
- ✅ 优秀：延迟降低 > 60%
- ⚠️ 一般：延迟降低 20-60%
- ❌ 不佳：延迟降低 < 20%

### 报告文件说明

测试完成后生成以下文件：

```
test_results/
├── results_20250111_123456.json  # 详细的每个请求结果
└── stats_20250111_123456.json    # 统计摘要

reports/
├── report.html                    # HTML 报告（推荐查看）
├── report.md                      # Markdown 报告
└── charts/                        # 性能对比图表
    ├── high_reuse_latency.png
    ├── high_reuse_throughput.png
    ├── medium_reuse_latency.png
    └── overall_improvement.png
```

### Grafana Dashboard

在 Grafana 中监控以下指标：

1. **KV Cache 键总数**：应该在测试期间增长
2. **已分配内存**：观察内存使用趋势
3. **Put/Get QPS**：观察请求模式
4. **请求计数**：验证测试是否正确执行

---

## 常见问题

### Q1: 测试失败，报错 "Connection refused"

**原因**：服务未启动或端口配置错误

**解决方案**：
```bash
# 1. 检查各服务是否运行
nc -zv MACHINE_A_IP 50052  # Mooncake Master
nc -zv MACHINE_A_IP 8200   # Decoder
nc -zv MACHINE_B_IP 8100   # Prefiller
nc -zv localhost 9000      # Proxy

# 2. 检查防火墙
sudo iptables -L | grep ACCEPT
sudo firewall-cmd --list-all

# 3. 查看服务日志
tail -f mooncake_master.log
tail -f decoder.log
tail -f prefiller.log
```

### Q2: 缓存效果不明显（<20% 改善）

**可能原因**：
1. 提示词重用率低
2. Chunk size 配置不当
3. 网络带宽不足

**解决方案**：
```yaml
# 1. 修改测试场景，增加重用率
test_scenarios:
  high_reuse:
    reuse_ratio: 1.0  # 确保高重用

# 2. 调整 chunk_size
mooncake:
  chunk_size: 128  # 尝试更小的值

# 3. 检查网络性能
iperf3 -c MACHINE_B_IP -p 5201
```

### Q3: RDMA 设备未找到

**解决方案**：
```bash
# 1. 检查 RDMA 驱动
lsmod | grep rdma
lsmod | grep mlx5

# 2. 查看设备
rdma link
ibv_devinfo

# 3. 如果没有 RDMA，使用 TCP
# 修改配置文件
mooncake:
  protocol: "tcp"
```

### Q4: 内存不足

**解决方案**：
```yaml
# 减小全局缓存大小
mooncake:
  global_segment_size: 10737418240  # 10GB

# 减少请求数量
test_scenarios:
  high_reuse:
    num_requests: 20  # 从 50 减少到 20
```

### Q5: GPU OOM（显存不足）

**解决方案**：
```bash
# 1. 使用量化模型
# Qwen2.5-7B-GPTQ-Int4 而不是 Qwen2.5-72B

# 2. 减少并发
python3 test_vllm_lmcache_mooncake.py --concurrency 5

# 3. 减少 max_tokens
# 在 test_config.yaml 中
model:
  max_tokens: 32  # 从 64 减到 32
```

### Q6: Prometheus 没有数据

**解决方案**：
```bash
# 1. 检查 Mooncake Master 的 metrics 端点
curl http://MACHINE_A_IP:9004/metrics

# 2. 检查 Prometheus 配置
cat prometheus.yml

# 3. 确保 scrape_configs 包含 Mooncake
scrape_configs:
  - job_name: 'mooncake'
    static_configs:
      - targets: ['MACHINE_A_IP:9004']

# 4. 重启 Prometheus
sudo systemctl restart prometheus
```

---

## 进阶使用

### 自定义测试场景

编辑 `test_config.yaml` 添加自定义场景：

```yaml
test_scenarios:
  # 自定义场景
  my_custom_scenario:
    num_requests: 30
    reuse_ratio: 0.7  # 70% 重用
    prompt_template: |
      你的自定义提示词模板...
      变量: {i}
```

### 集成 CI/CD

```bash
# Jenkins/GitLab CI 示例
#!/bin/bash

# 运行测试
./run_full_test.sh --scenarios "high_reuse" --rounds 2

# 检查结果
python3 <<EOF
import json
import sys

with open('test_results/stats_*.json', 'r') as f:
    stats = json.load(f)

# 检查是否达到性能目标
baseline = stats[0]
cached = stats[1]

improvement = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100

if improvement < 50:
    print(f"FAILED: 缓存改善不足 {improvement:.1f}%")
    sys.exit(1)

print(f"PASSED: 缓存改善 {improvement:.1f}%")
EOF
```

### 长时间压力测试

```bash
# 运行 10 轮测试
./run_full_test.sh --rounds 10

# 或者持续运行
while true; do
    python3 test_vllm_lmcache_mooncake.py --rounds 1
    sleep 60
done
```

### 导出 Prometheus 指标

```bash
# 导出测试期间的指标
python3 <<EOF
import requests
import json
from datetime import datetime, timedelta

prometheus_url = "http://MACHINE_A_IP:9090"

# 查询最近 1 小时的数据
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)

query = "master_key_count"
params = {
    'query': query,
    'start': start_time.timestamp(),
    'end': end_time.timestamp(),
    'step': '15s'
}

response = requests.get(f"{prometheus_url}/api/v1/query_range", params=params)
data = response.json()

with open('metrics_export.json', 'w') as f:
    json.dump(data, f, indent=2)

print("✓ 指标已导出到 metrics_export.json")
EOF
```

---

## 性能优化建议

### 1. 网络优化

```bash
# 调整 RDMA 参数
sudo sysctl -w net.core.rmem_max=268435456
sudo sysctl -w net.core.wmem_max=268435456

# 启用 RDMA QoS
sudo mlnx_qos -i mlx5_0 --trust=dscp
```

### 2. GPU 优化

```bash
# 设置 GPU 性能模式
sudo nvidia-smi -pm 1
sudo nvidia-smi -ac 1215,1410  # 根据你的 GPU 调整
```

### 3. 内存优化

```yaml
# 调整缓存策略
mooncake:
  # 增加本地缓冲区
  local_buffer_size: 2147483648  # 2GB

  # 调整全局缓存
  global_segment_size: 53687091200  # 50GB（如果内存充足）
```

---

## 参考资源

- **Mooncake 官方文档**: https://kvcache-ai.github.io/Mooncake/
- **LMCache 官方文档**: https://docs.lmcache.ai/
- **vLLM 官方文档**: https://docs.vllm.ai/
- **Mooncake x LMCache 集成**: https://blog.lmcache.ai/2025-04-22-tencent/
- **SGLang HiCache**: https://lmsys.org/blog/2025-09-10-sglang-hicache/

---

## 支持和反馈

如果遇到问题：

1. **查看日志文件**：`logs/` 目录下的各服务日志
2. **检查配置**：确保 `test_config.yaml` 配置正确
3. **验证环境**：运行 `./run_full_test.sh --help` 检查依赖
4. **提交 Issue**：
   - Mooncake: https://github.com/kvcache-ai/Mooncake/issues
   - LMCache: https://github.com/LMCache/LMCache/issues
   - vLLM: https://github.com/vllm-project/vllm/issues

---

**祝测试顺利！🎉**
