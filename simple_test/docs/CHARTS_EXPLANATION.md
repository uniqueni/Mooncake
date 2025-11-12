# 📊 报告图表说明

## 图表概述

生成报告时会自动创建 **4-5 个可视化图表**，帮助快速理解测试结果。

---

## 图表 1: TTFT 对比柱状图
**文件名**: `ttft_comparison.png`

### 作用
对比每个场景在 **Baseline** 和 **Cache Hit** 下的 TTFT（首 Token 延迟）

### 图表内容
- **红色柱子**: Baseline (Round 1) 的 TTFT
- **绿色柱子**: Cache Hit (Round 2) 的 TTFT
- **X 轴**: 测试场景
- **Y 轴**: TTFT 延迟（毫秒）

### 如何解读
- 绿色柱子越短越好（缓存后延迟降低）
- 红色和绿色差距越大，缓存效果越好
- 柱子上方的数字是具体的 TTFT 值（ms）

### 示例
```
场景1: 红色 1500ms → 绿色 500ms (降低 66%)
场景2: 红色 4000ms → 绿色 800ms (降低 80%)
```

**结论**: 671B 模型缓存效果更明显（降低率更高）

---

## 图表 2: 吞吐量对比柱状图
**文件名**: `throughput_comparison.png`

### 作用
对比每个场景在 **Baseline** 和 **Cache Hit** 下的吞吐量

### 图表内容
- **蓝色柱子**: Baseline (Round 1) 的吞吐量
- **橙色柱子**: Cache Hit (Round 2) 的吞吐量
- **X 轴**: 测试场景
- **Y 轴**: 吞吐量（req/s，每秒请求数）

### 如何解读
- 橙色柱子越高越好（缓存后吞吐量提升）
- 柱子上方的数字是具体的吞吐量值（req/s）
- 目标：Cache Hit 吞吐量应该是 Baseline 的 2.5 倍以上（+150%）

### 示例
```
场景1: 蓝色 1.2 req/s → 橙色 3.0 req/s (+150%)
场景2: 蓝色 0.8 req/s → 橙色 2.5 req/s (+212%)
```

**结论**: 所有场景吞吐量都达到 2.5 倍以上，系统处理能力显著提升

---

## 图表 3: TTFT 降低百分比对比
**文件名**: `ttft_reduction_comparison.png`

### 作用
横向对比每个场景的 **TTFT 降低百分比**

### 图表内容
- **横向条形图**: 每个场景一根
- **颜色**:
  - 🟢 **绿色**: 降低 ≥60%（达到目标）
  - 🟠 **橙色**: 降低 40-60%（一般）
  - 🔴 **红色**: 降低 <40%（需要优化）
- **X 轴**: TTFT 降低百分比
- **绿色虚线**: 目标线（60%）

### 如何解读
- 条形越长越好
- 超过绿色虚线（60%）说明达标
- 可以快速识别哪些场景表现最好

### 示例
```
场景1 (671B-长文本): ████████████████ 82% ✅
场景2 (72B-长文本):  ███████████      70% ✅
场景3 (72B-多轮):    ██████████       65% ✅
```

**结论**: 长文本场景比多轮对话缓存效果更好

---

## 图表 4: 吞吐量提升百分比对比
**文件名**: `throughput_increase_comparison.png`

### 作用
横向对比每个场景的 **吞吐量提升百分比**

### 图表内容
- **横向条形图**: 每个场景一根
- **颜色**:
  - 🟢 **绿色**: 提升 ≥150%（达到目标）
  - 🟠 **橙色**: 提升 100-150%（一般）
  - 🔴 **红色**: 提升 <100%（需要优化）
- **X 轴**: 吞吐量提升百分比
- **绿色虚线**: 目标线（150%）

### 如何解读
- 条形越长越好
- 超过绿色虚线（150%）说明达标
- 吞吐量提升直接反映系统处理能力的改善

### 示例
```
场景1: ████████████████████ +280% ✅
场景2: ███████████████      +195% ✅
场景3: ████████████         +150% ✅
```

**结论**: 缓存后吞吐量普遍提升 1.5-2.8 倍

---

## 图表 5: 综合性能雷达图（可选）
**文件名**: `performance_radar.png`

### 作用
多维度综合对比不同场景的性能（仅在场景 ≤6 个时生成）

### 图表内容
- **三个维度**:
  1. TTFT 降低（分数越高越好）
  2. 吞吐量提升（分数越高越好）
  3. TPOT 稳定性（分数越高越好）
- **多边形面积**: 越大说明综合性能越好
- **不同颜色**: 代表不同场景

### 如何解读
- 面积越大，综合性能越好
- 可以一眼看出哪个场景表现最均衡
- 三个顶点都接近 100 分是理想状态

### 示例
```
场景1 (671B): 三角形面积大，三个维度都接近满分
场景2 (72B): 三角形面积中等，TTFT略低
```

**结论**: 可以快速识别综合性能最优的配置

---

## 中文显示问题

### 问题现象
- 图表上的中文显示为 **方框** (□□□)
- 图表标题、轴标签、图例文字乱码

### 原因
matplotlib 默认不支持中文字体

### 解决方案

#### 方案 1: 自动字体配置（已内置）
我已经在代码中配置了常用中文字体：
```python
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
```

系统会自动尝试以下字体：
1. **Arial Unicode MS** (macOS 自带)
2. **SimHei** (黑体，Windows/Linux)
3. **DejaVu Sans** (备选)

#### 方案 2: 手动安装中文字体

**macOS**:
```bash
# 查看系统已安装字体
fc-list :lang=zh

# 如果没有中文字体，安装
brew install font-noto-sans-cjk
```

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# CentOS/RHEL
sudo yum install google-noto-sans-cjk-fonts
```

**Windows**:
系统自带宋体、黑体，通常无需额外安装

#### 方案 3: 修改配置文件

如果自动配置不生效，手动修改 matplotlib 配置：

```bash
# 查找配置文件位置
python3 -c "import matplotlib; print(matplotlib.matplotlib_fname())"

# 编辑配置文件
vim ~/.matplotlib/matplotlibrc

# 添加以下行
font.sans-serif: Arial Unicode MS, SimHei, WenQuanYi Zen Hei
axes.unicode_minus: False
```

#### 方案 4: 使用英文标签（备选）

如果中文字体问题无法解决，可以修改代码使用英文标签：

在报告脚本中搜索并替换：
- "TTFT 对比" → "TTFT Comparison"
- "吞吐量对比" → "Throughput Comparison"
- "降低" → "Reduction"
- "提升" → "Increase"

### 验证字体是否生效

运行报告生成后，检查图表：

```bash
# 生成报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "测试" --stats test_stats.json \
    --output report.md

# 查看生成的图表
ls -l report_charts/
open report_charts/ttft_comparison.png  # macOS
xdg-open report_charts/ttft_comparison.png  # Linux
```

如果中文正常显示 → ✅ 字体配置成功
如果仍然是方框 → 尝试方案 2 或 3

---

## 图表文件位置

默认生成在 `report_charts/` 目录：

```
report_charts/
├── ttft_comparison.png              # 图表1: TTFT对比
├── throughput_comparison.png        # 图表2: 吞吐量对比
├── ttft_reduction_comparison.png    # 图表3: TTFT降低百分比
├── throughput_increase_comparison.png  # 图表4: 吞吐量提升百分比
└── performance_radar.png            # 图表5: 综合雷达图（可选）
```

可以通过 `--chart-dir` 参数自定义：

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "测试" --stats stats.json \
    --chart-dir my_charts \
    --output report.md
```

---

## 图表用途

### 1. 技术报告
- 放在报告正文中，增强可读性
- 用于技术评审、性能分析

### 2. 汇报演示
- 提取单个图表用于 PPT
- 快速展示关键指标

### 3. 性能对比
- 不同配置、不同场景的直观对比
- 识别性能瓶颈和优化方向

### 4. 趋势分析
- 多次测试的结果对比
- 追踪性能改进效果

---

## 禁用图表生成

如果不需要图表（例如字体问题无法解决），可以使用 `--no-charts` 参数：

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "测试" --stats stats.json \
    --no-charts \
    --output report.md
```

报告将只包含表格数据，不生成图表文件。

---

## 总结

### 4 个核心图表的作用

| 图表 | 主要用途 | 关键信息 |
|------|---------|---------|
| **TTFT 对比** | 看延迟降低效果 | 绿色柱子越短越好 |
| **吞吐量对比** | 看处理能力提升 | 橙色柱子越高越好 |
| **TTFT 降低率** | 快速识别达标场景 | 超过 60% 虚线为达标 |
| **吞吐量提升率** | 快速识别性能提升 | 超过 150% 虚线为达标 |

### 图表阅读顺序（推荐）

1. **先看图表 3 和 4**（降低率和提升率）
   - 快速判断哪些场景达标
   - 识别表现最好和最差的场景

2. **再看图表 1 和 2**（绝对值对比）
   - 了解具体的延迟和吞吐量数值
   - 对比不同场景的性能差异

3. **最后看雷达图**（如果有）
   - 综合评估各场景的均衡性
   - 选择最优配置

---

**需要帮助？**
- 字体问题无法解决 → 使用 `--no-charts` 参数
- 看不懂图表 → 查看报告中的表格数据（更详细）
- 需要自定义图表 → 修改 `generate_multi_scenario_report.py` 的 `_generate_*_chart()` 方法
