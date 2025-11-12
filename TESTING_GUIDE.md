# Mooncake 缓存效果测试指南

两套测试方案，根据你的需求选择。

---

## 🎯 选择测试方案

### ⭐ 方案 1: 简化版（推荐）

**适合你，如果：**
- ✅ 已有 Mooncake 部署
- ✅ 已有 OpenAI 兼容接口（vLLM 或其他）
- ✅ 只想快速验证缓存效果
- ✅ 不想处理复杂的 Docker 配置

**位置**: `simple_test/` 目录

**快速开始**:
```bash
cd simple_test
cat QUICKSTART.md  # 3 步快速开始
```

---

### 📦 方案 2: 完整版

**适合你，如果：**
- 需要完整的容器化部署
- 需要对比 PD 分离 vs 非 PD 分离
- 需要完整的监控和报告
- 需要测试多种部署模式

**位置**: `tests/` 目录

**快速开始**:
```bash
cd tests
cat README.md
```

---

## 📊 方案对比

| 对比项 | 简化版 (simple_test/) | 完整版 (tests/) |
|--------|----------------------|-----------------|
| **部署** | 使用你已有的服务 | Docker Compose 全新部署 |
| **配置文件** | 2 个 | 10+ 个 |
| **测试模式** | 单一模式 | PD 分离 + 非 PD 分离对比 |
| **部署时间** | < 5 分钟 | 30 分钟 |
| **文档** | 精简（3 个文件）| 详尽（多个指南）|
| **监控** | 可选 | Prometheus + Grafana |
| **报告** | 基础统计 | HTML + Markdown + 图表 |
| **适用场景** | ✅ 快速验证缓存效果 | ✅ 完整性能测试和对比 |

---

## 🚀 快速决策

### 👉 选择简化版，如果你：

```bash
# 你的情况：
已有 Mooncake (IP:Port) ✓
已有 OpenAI 接口 (http://xxx:8000) ✓
只想测试缓存效果 ✓
不想折腾 Docker ✓

# 开始：
cd simple_test
cat QUICKSTART.md
```

### 👉 选择完整版，如果你：

```bash
# 你的情况：
需要从头部署 ✓
需要测试多种模式 ✓
需要详细的性能对比 ✓
需要完整的监控和报告 ✓

# 开始：
cd tests
cat README.md
```

---

## 📁 目录结构

```
Mooncake/
├── simple_test/              # ⭐ 简化版（推荐先看这个）
│   ├── QUICKSTART.md         # 3 步快速开始
│   ├── SIMPLE_TEST_GUIDE.md  # 详细指南
│   ├── lmcache_config_template.yaml  # LMCache 配置
│   ├── test_config_simple.yaml       # 测试配置
│   └── test_simple.py        # 测试脚本
│
└── tests/                    # 完整版
    ├── README.md             # 完整版总览
    ├── LARGE_MODELS_TEST_GUIDE.md    # 大模型指南
    ├── docker-compose.yml    # 容器编排
    ├── test_pd_disagg.py     # PD 分离测试
    ├── test_non_disagg.py    # 非 PD 分离测试
    └── ...                   # 更多文件
```

---

## 🎯 测试目标

两个方案都测试相同的核心指标：

### 核心指标

1. **TTFT (Time to First Token)**
   - 首 token 延迟
   - 目标：Cache Hit 降低 60-70%

2. **TPOT (Time per Output Token)**
   - 每 token 平均时间
   - 目标：保持稳定

3. **吞吐量**
   - 请求/秒，Token/秒
   - 目标：Cache Hit 提升 150-200%

### 预期结果

```
🎯 缓存效果:
  TTFT 降低:    +66.5%  ← 首 token 延迟大幅降低
  吞吐量提升:   +195.7%  ← 系统吞吐量显著提升
  ✅ 达到目标！
```

---

## ⚙️ 前置要求

### 简化版需要：
- ✅ Mooncake Master 运行中
- ✅ OpenAI 兼容接口
- ✅ Python 3.10+
- ✅ `pip install openai pyyaml`

### 完整版需要：
- ✅ Docker + Docker Compose
- ✅ NVIDIA GPU + nvidia-docker
- ✅ 16GB+ 内存
- ✅ RDMA 网卡（推荐）

---

## 📚 文档导航

### 简化版文档（simple_test/）

1. **QUICKSTART.md** ⭐ 从这里开始
   - 3 步快速开始
   - 最快 5 分钟开始测试

2. **SIMPLE_TEST_GUIDE.md**
   - LMCache 配置详解
   - 性能调优
   - 故障排查

3. **lmcache_config_template.yaml**
   - 详细配置注释
   - 多种配置示例

### 完整版文档（tests/）

1. **README.md**
   - 完整版总览
   - 文件结构说明

2. **LARGE_MODELS_TEST_GUIDE.md**
   - 72B/671B 大模型测试
   - Docker 部署详解
   - 性能对比分析

3. **VLLM_LMCACHE_TEST_GUIDE.md**
   - vLLM 集成指南
   - 小模型测试

---

## 🆘 获取帮助

1. **快速问题**：查看对应目录的 README.md
2. **配置问题**：查看配置文件中的注释
3. **测试问题**：查看对应的测试指南

---

## 💡 建议流程

```
1. 先用简化版快速验证（5 分钟）
   ↓
2. 如果效果不好，查看故障排查
   ↓
3. 如果需要详细对比，使用完整版
   ↓
4. 生成完整报告和图表
```

---

**马上开始**:

```bash
# 简化版（推荐）
cd simple_test && cat QUICKSTART.md

# 或完整版
cd tests && cat README.md
```
