# vLLM + LMCache + Mooncake 测试套件

完整的测试套件，用于评估 vLLM、LMCache 和 Mooncake 集成的 KV Cache 缓存效果。

## 📁 文件结构

```
tests/
├── README.md                              # 本文件
├── VLLM_LMCACHE_TEST_GUIDE.md            # 通用测试指南（7B 小模型）
├── LARGE_MODELS_TEST_GUIDE.md            # 大模型测试指南（72B/671B）
│
├── test_config.yaml                       # 小模型测试配置
├── test_config_large_models.yaml          # 大模型测试配置
│
├── test_vllm_lmcache_mooncake.py         # PD 分离测试（小模型）
├── test_non_disagg.py                     # 非 PD 分离测试（通用）
├── test_pd_disagg.py                      # PD 分离测试（大模型）
│
├── generate_report.py                     # 报告生成工具
├── compare_results.py                     # 性能对比工具
├── run_full_test.sh                       # 自动化测试脚本
│
├── docker-compose.yml                     # Docker Compose 配置
├── prometheus.yml                         # Prometheus 配置
├── grafana-dashboard-cache-test.json     # Grafana Dashboard
│
└── configs/                               # Mooncake 配置文件目录
    ├── mooncake-prefiller-config.yaml
    └── mooncake-decoder-config.yaml
```

## 🚀 快速开始

### 场景 1: 测试小模型（Qwen2.5-7B）

适合快速验证和功能测试：

```bash
# 1. 使用默认配置
python3 test_vllm_lmcache_mooncake.py

# 2. 查看测试指南
cat VLLM_LMCACHE_TEST_GUIDE.md
```

### 场景 2: 测试大模型（72B/671B）- 容器化部署

适合生产环境性能测试：

```bash
# 1. 修改配置，选择模型
vim test_config_large_models.yaml
# 修改: active_model: "qwen_72b"

# 2. PD 分离模式
docker-compose up -d mooncake-master vllm-prefiller vllm-decoder vllm-proxy
python3 test_pd_disagg.py

# 3. 非 PD 分离模式
docker-compose --profile non-disagg up -d vllm-server
python3 test_non_disagg.py

# 4. 对比结果
python3 compare_results.py \
  --pd-stats test_results/pd_disagg_*_stats_*.json \
  --non-pd-stats test_results/non_disagg_*_stats_*.json \
  --generate-charts

# 5. 查看详细指南
cat LARGE_MODELS_TEST_GUIDE.md
```

## 📊 测试模式对比

### PD 分离 (Prefill-Decode Disaggregation)

**特点：**
- ✅ Prefill 和 Decode 分离到不同节点
- ✅ 使用 LMCache + Mooncake 管理 KV Cache
- ✅ 高吞吐量、高资源利用率
- ⚠️ 首次请求延迟较高（Cold Start）
- ⚠️ 需要网络传输 KV Cache

**适用场景：**
- 大规模生产环境
- 高并发场景
- 长上下文应用
- 资源优化需求

**测试脚本：**
- 小模型: `test_vllm_lmcache_mooncake.py`
- 大模型: `test_pd_disagg.py`

### 非 PD 分离 (Traditional Deployment)

**特点：**
- ✅ 单一 vLLM 服务，部署简单
- ✅ 低延迟（无网络开销）
- ✅ 可使用 vLLM prefix caching
- ⚠️ 资源利用率较低
- ⚠️ Prefill 和 Decode 竞争资源

**适用场景：**
- 中小规模部署
- 快速原型验证
- 低延迟要求
- 简单应用

**测试脚本：**
- 通用: `test_non_disagg.py`

## 🎯 测试指标

### 核心指标

1. **TTFT (Time to First Token)**
   - PD 分离: Prefill + KV传输 + 首次Decode
   - 非 PD 分离: Prefill + 首次Decode
   - 目标: Cache Hit 后降低 60-70%

2. **TPOT (Time per Output Token)**
   - Decode 阶段每个 token 的平均时间
   - 目标: 两种模式相差 <20%

3. **吞吐量 (Throughput)**
   - 请求吞吐量 (req/s)
   - Token 吞吐量 (tokens/s)
   - 目标: PD 分离提升 150-200%

4. **端到端延迟 (E2E Latency)**
   - 从发送请求到接收完整响应的时间
   - 包含 TTFT + 所有 Decode 时间

### PD 分离特有指标

- **Prefill 时间**: Prefill 阶段耗时
- **KV 传输时间**: KV Cache 网络传输耗时
- **Decode 时间**: Decode 阶段总耗时
- **缓存命中率**: 估算的 KV Cache 命中率

## 📝 测试场景

### 1. 长上下文高重用 (long_context_high_reuse)

**特征：**
- 16k-32k tokens 的长上下文
- 90% 请求共享相同上下文
- 模拟 RAG、文档分析场景

**预期效果：** 缓存命中率高，性能提升显著

### 2. 代码生成 (code_generation)

**特征：**
- 8k tokens 代码库上下文
- 80% 请求共享代码上下文
- 模拟代码辅助场景

### 3. 多轮对话 (multi_turn_conversation)

**特征：**
- 逐步累积的对话历史
- 85% 请求共享历史
- 模拟聊天机器人场景

### 4. 批量处理 (batch_processing)

**特征：**
- 共享大量指令模板
- 95% 超高重用率
- 模拟翻译、摘要任务

### 5. 冷启动 (cold_start)

**特征：**
- 0% 缓存重用
- 每个请求唯一
- 测试基线性能

## 🔧 配置说明

### test_config.yaml (小模型)

```yaml
# 代理服务器
proxy:
  url: "http://localhost:9000/v1"

# 模型
model:
  name: "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4"
  max_tokens: 64

# 机器配置
machines:
  machine_a:
    ip: "YOUR_IP"  # 修改为实际 IP
```

### test_config_large_models.yaml (大模型)

```yaml
# 选择模型
active_model: "qwen_72b"  # 或 "deepseek_671b"

# 模型配置
models:
  qwen_72b:
    name: "Qwen/Qwen2.5-72B-Instruct"
    tensor_parallel_size: 8  # 8 GPUs

# 部署模式
deployment_modes:
  pd_disaggregated:
    enabled: true
  non_disaggregated:
    enabled: true
```

## 📈 性能监控

### Prometheus 指标

访问 `http://localhost:9090` 查询指标：

```promql
# KV Cache 键总数
master_key_count

# 已分配内存
master_allocated_bytes

# Put 请求 QPS
rate(master_put_start_requests_total[1m])

# Get 请求 QPS
rate(master_get_replica_list_requests_total[1m])
```

### Grafana Dashboard

1. 访问 `http://localhost:3000` (admin/admin)
2. 导入 `grafana-dashboard-cache-test.json`
3. 实时查看性能指标

## 📊 结果分析

### 生成报告

```bash
# 单个测试报告
python3 generate_report.py \
  --stats test_results/stats_*.json \
  --format both \
  --generate-charts

# 对比报告
python3 compare_results.py \
  --pd-stats test_results/pd_disagg_*_stats_*.json \
  --non-pd-stats test_results/non_disagg_*_stats_*.json \
  --generate-charts
```

### 查看报告

- **HTML 报告**: `reports/report.html`
- **Markdown 报告**: `reports/report.md`
- **对比报告**: `comparison_report.md`
- **图表**: `reports/charts/` 或 `comparison_charts/`

## 🐛 故障排查

### 常见问题

**Q: 连接失败？**
```bash
# 检查服务状态
docker-compose ps
nc -zv localhost 50052  # Mooncake Master
nc -zv localhost 9000   # Proxy
```

**Q: 缓存效果不明显？**
```yaml
# 调整配置
mooncake:
  lmcache:
    chunk_size: 128  # 尝试更小的值
```

**Q: GPU OOM？**
```yaml
# 使用量化模型
models:
  qwen_72b:
    name: "Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4"
```

**Q: RDMA 不可用？**
```yaml
# 使用 TCP
mooncake:
  transfer:
    protocol: "tcp"
```

## 📚 文档

- **通用测试指南**: [VLLM_LMCACHE_TEST_GUIDE.md](VLLM_LMCACHE_TEST_GUIDE.md)
- **大模型测试指南**: [LARGE_MODELS_TEST_GUIDE.md](LARGE_MODELS_TEST_GUIDE.md)
- **Mooncake 官方文档**: https://kvcache-ai.github.io/Mooncake/
- **vLLM 文档**: https://docs.vllm.ai/
- **LMCache 文档**: https://docs.lmcache.ai/

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

与 Mooncake 项目保持一致。

---

**祝测试顺利！🎉**

如有问题，请查看详细指南或提交 Issue。
