# 快速开始 - 3 步测试缓存效果

**适用场景**：你已经有 Mooncake 和 OpenAI 兼容接口

## 📦 你需要的文件

- ✅ `lmcache_config_template.yaml` - LMCache 配置模板
- ✅ `test_config_simple.yaml` - 测试配置
- ✅ `test_simple.py` - 测试脚本
- ✅ `compare_results.py` - 对比工具

## 🚀 3 步开始

### 步骤 1: 配置 LMCache（如果要测试缓存效果）

```bash
# 1. 复制配置模板
cp lmcache_config_template.yaml lmcache_config.yaml

# 2. 修改 IP 地址
vim lmcache_config.yaml

# 修改以下内容:
# - YOUR_MOONCAKE_IP: 你的 Mooncake Master IP
# - YOUR_LOCAL_IP: 运行 vLLM 的机器 IP
# - protocol: "tcp" 或 "rdma"（看你有没有 RDMA）

# 3. 启动你的服务时加载配置
export LMCACHE_CONFIG_FILE=/path/to/lmcache_config.yaml
export LMCACHE_USE_EXPERIMENTAL=True

# 然后启动你的 vLLM 或其他服务
vllm serve YOUR_MODEL ...
```

### 步骤 2: 配置测试脚本

```bash
# 1. 复制测试配置
cp test_config_simple.yaml my_test_config.yaml

# 2. 修改配置
vim my_test_config.yaml

# 修改以下内容:
# openai_api:
#   base_url: "http://YOUR_API_IP:8000/v1"  # 你的 OpenAI 接口
#   model_name: "YOUR_MODEL_NAME"            # 你的模型名
#
# mooncake:
#   master_ip: "YOUR_MOONCAKE_IP"
```

### 步骤 3: 运行测试

```bash
# 测试带缓存的性能
python3 test_simple.py \
  --config my_test_config.yaml \
  --mode with-cache \
  --scenarios long_context_high_reuse

# 结果会保存在 test_results/
ls test_results/
```

---

## 📊 对比测试（可选）

如果你想对比有缓存 vs 无缓存：

```bash
# 1. 测试带缓存（确保服务加载了 LMCache 配置）
python3 test_simple.py \
  --config my_test_config.yaml \
  --mode with-cache \
  --scenarios long_context_high_reuse \
  --rounds 2

# 2. 重启服务，不加载 LMCache
# (或者连接到另一个没有 LMCache 的服务)

# 3. 测试不带缓存
python3 test_simple.py \
  --config my_test_config.yaml \
  --mode baseline \
  --scenarios long_context_high_reuse \
  --rounds 2

# 4. 对比结果
python3 compare_results.py \
  --with-cache-stats test_results/with-cache_*_stats_*.json \
  --baseline-stats test_results/baseline_*_stats_*.json \
  --generate-charts

# 5. 查看对比报告
cat comparison_report.md
```

---

## 🎯 关键指标

测试会输出这些关键指标：

| 指标 | 说明 | 目标 |
|------|------|------|
| **TTFT** | Time to First Token（首 token 延迟） | Cache Hit 降低 60-70% |
| **TPOT** | Time per Output Token（每 token 时间） | 保持稳定 |
| **吞吐量** | 请求/秒，Token/秒 | Cache Hit 提升 150-200% |

### 示例输出

```
🧪 场景: long_context_high_reuse

📊 Round 1/2
   🥶 Cold Start

📈 统计:
  请求数: 30/30
  耗时:   120.45s

⏱️  TTFT:
  平均:   21,245.67ms  ← Cold Start 时较高
  P90:    28,456.12ms

🚀 吞吐:
  请求:   0.25 req/s

────────────────────────────────

📊 Round 2/2
   🔥 Cache Hit

📈 统计:
  请求数: 30/30
  耗时:   45.23s

⏱️  TTFT:
  平均:   7,123.45ms  ← Cache Hit 显著降低！
  P90:    9,234.56ms

🚀 吞吐:
  请求:   0.66 req/s

🎯 缓存效果:
  TTFT 降低:    +66.5%  ← 达到目标！
  吞吐量提升:   +164.0%
  ✅ 达到目标！（60%）
```

---

## ✅ 验证清单

测试前确认：

- [ ] **Mooncake Master 运行中**
  ```bash
  curl http://YOUR_MOONCAKE_IP:9004/metrics | grep master_key_count
  ```

- [ ] **OpenAI 接口可访问**
  ```bash
  curl http://YOUR_API_IP:8000/v1/models
  ```

- [ ] **LMCache 配置正确**（如果测试缓存）
  - IP 地址都修改了
  - protocol 选对了（tcp/rdma）

- [ ] **服务已加载 LMCache**（如果测试缓存）
  - 启动日志有 "LMCache config loaded"

- [ ] **测试配置修改了**
  - `base_url` 指向你的接口
  - `model_name` 匹配你的模型

---

## ⚠️ 常见问题

### Q: 怎么知道 LMCache 有没有生效？

**A: 三种方法**

1. **查看 Mooncake 指标**
   ```bash
   # KV Cache 键数量应该增长
   watch -n 1 'curl -s http://YOUR_MOONCAKE_IP:9004/metrics | grep master_key_count'
   ```

2. **看测试结果**
   - Round 2 的 TTFT 应该明显低于 Round 1
   - 如果没有降低，说明缓存没生效

3. **检查服务日志**
   - 应该有 KV Cache 写入/读取的日志

### Q: 缓存效果不明显？

**A: 检查这些**

1. **调整 chunk_size**
   ```yaml
   chunk_size: 128  # 试试更小的值
   ```

2. **确认请求真的共享前缀**
   - 查看测试场景的 `reuse_ratio`

3. **检查缓存空间够不够**
   ```bash
   curl -s http://YOUR_MOONCAKE_IP:9004/metrics | grep master_allocated_bytes
   ```

### Q: 连接失败？

**A: 检查网络**

```bash
# 1. ping 通不通
ping YOUR_MOONCAKE_IP

# 2. 端口开没开
nc -zv YOUR_MOONCAKE_IP 50052  # Master
nc -zv YOUR_MOONCAKE_IP 8080   # Metadata
nc -zv YOUR_API_IP 8000        # API

# 3. 防火墙
sudo iptables -L | grep ACCEPT
```

---

## 📚 更多信息

- **详细指南**: `SIMPLE_TEST_GUIDE.md`
- **LMCache 配置**: `lmcache_config_template.yaml`（有详细注释）
- **测试配置**: `test_config_simple.yaml`（有详细注释）

---

## 🎁 测试场景

可用的测试场景：

- `long_context_high_reuse` - 长上下文高重用（推荐）
- `multi_turn_conversation` - 多轮对话
- `code_generation` - 代码生成
- `batch_processing` - 批量处理
- `cold_start` - 冷启动基线

**运行多个场景：**
```bash
python3 test_simple.py \
  --scenarios long_context_high_reuse multi_turn_conversation code_generation
```

---

**就这么简单！🎉**

有问题查看 `SIMPLE_TEST_GUIDE.md` 获取详细说明。
