# 🔧 图表中文显示修复指南

## 问题现象

生成的图表（PNG 文件）中，中文显示为 **方框** □□□ 或乱码。

---

## 快速修复（3 步）

### 步骤 1: 检查系统字体

**macOS**:
```bash
# 查看中文字体
fc-list :lang=zh | grep -i "Arial\|Hei"

# 应该看到类似输出：
# /System/Library/Fonts/Supplemental/Arial Unicode.ttf: Arial Unicode MS
```

**Linux**:
```bash
fc-list :lang=zh | grep -i "Noto\|Hei"
```

**Windows**:
```cmd
# 打开字体文件夹查看
explorer C:\Windows\Fonts
# 确认有"SimHei"（黑体）或"Microsoft YaHei"（微软雅黑）
```

### 步骤 2: 安装中文字体（如果没有）

**macOS**:
```bash
# 通常系统自带 Arial Unicode MS，无需安装
# 如果需要额外字体
brew tap homebrew/cask-fonts
brew install font-noto-sans-cjk
```

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install fonts-noto-cjk fonts-wqy-zenhei
```

**CentOS/RHEL**:
```bash
sudo yum install google-noto-sans-cjk-fonts wqy-zenhei-fonts
```

**Windows**:
通常无需操作，系统自带黑体和微软雅黑

### 步骤 3: 清除 matplotlib 缓存并重新生成

```bash
# 清除 matplotlib 字体缓存
rm -rf ~/.matplotlib/*.cache
rm -rf ~/.cache/matplotlib

# 重新生成报告
python3 reports/generate_multi_scenario_report.py \
    --scenario "测试" \
    --stats test_results/stats.json \
    --output report.md

# 查看图表
open report_charts/ttft_comparison.png
```

---

## 方案 A: 自动修复（推荐）

我已经在代码中配置了字体，通常会自动生效：

```python
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
```

**重新运行即可**：
```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-72B" --stats stats.json \
    --output report.md
```

---

## 方案 B: 手动配置字体

如果自动配置不生效，手动指定字体文件：

### 创建字体配置脚本

创建 `fix_font.py`:

```python
#!/usr/bin/env python3
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 查找系统中的中文字体
fonts = fm.findSystemFonts(fontpaths=None, fontext='ttf')
chinese_fonts = [f for f in fonts if 'Hei' in f or 'Noto' in f or 'Arial Unicode' in f]

print("找到的中文字体：")
for font in chinese_fonts[:5]:
    print(f"  {font}")

if chinese_fonts:
    print(f"\n✅ 推荐使用：{chinese_fonts[0]}")
else:
    print("\n❌ 未找到中文字体，请先安装")
```

运行：
```bash
python3 fix_font.py
```

### 在报告脚本中指定字体路径

修改 `generate_multi_scenario_report.py`：

```python
# 在 import matplotlib 后添加
import matplotlib.font_manager as fm

# 指定字体文件（根据 fix_font.py 的输出）
font_path = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'  # macOS
# font_path = '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'  # Linux

plt.rcParams['font.sans-serif'] = [fm.FontProperties(fname=font_path).get_name()]
```

---

## 方案 C: 使用英文标签

如果中文字体实在无法解决，修改为英文：

### 修改图表标题和标签

编辑 `reports/generate_multi_scenario_report.py`：

```python
# 在图表生成函数中替换中文标签

# TTFT 对比图
ax.set_ylabel('TTFT (ms)', fontsize=12, fontweight='bold')
ax.set_title('TTFT Comparison - Multiple Scenarios', fontsize=14, fontweight='bold')

# 吞吐量对比图
ax.set_ylabel('Throughput (req/s)', fontsize=12, fontweight='bold')
ax.set_title('Throughput Comparison - Multiple Scenarios', fontsize=14, fontweight='bold')

# TTFT 降低率图
ax.set_xlabel('TTFT Reduction (%)', fontsize=12, fontweight='bold')
ax.set_title('TTFT Reduction Comparison', fontsize=14, fontweight='bold')

# 吞吐量提升率图
ax.set_xlabel('Throughput Increase (%)', fontsize=12, fontweight='bold')
ax.set_title('Throughput Increase Comparison', fontsize=14, fontweight='bold')
```

---

## 方案 D: 禁用图表生成

如果完全不需要图表，使用 `--no-charts` 参数：

```bash
python3 reports/generate_multi_scenario_report.py \
    --scenario "测试" \
    --stats stats.json \
    --no-charts \
    --output report.md
```

报告将只包含表格，不生成图表文件。

---

## 验证修复是否成功

### 1. 生成测试图表

```bash
python3 -c "
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots()
ax.bar(['场景1', '场景2'], [100, 200])
ax.set_title('测试中文显示')
ax.set_xlabel('测试场景')
ax.set_ylabel('数值')
plt.savefig('test_chinese.png')
print('✅ 生成测试图表: test_chinese.png')
"
```

### 2. 查看测试图表

```bash
# macOS
open test_chinese.png

# Linux
xdg-open test_chinese.png

# Windows
start test_chinese.png
```

### 3. 判断结果

- ✅ **中文正常显示** → 修复成功，可以生成报告
- ❌ **仍然是方框** → 尝试其他方案或使用英文标签

---

## 常见问题

### Q1: 为什么清除缓存后还是方框？

**A**: 可能系统没有安装中文字体，或字体名称不匹配

**解决**:
```bash
# 查看 matplotlib 检测到的字体
python3 -c "
import matplotlib.font_manager as fm
fonts = [f.name for f in fm.fontManager.ttflist if 'Hei' in f.name or 'Arial' in f.name]
print('可用字体:', set(fonts))
"

# 如果输出为空，需要安装字体
```

### Q2: macOS 上 Arial Unicode MS 不生效？

**A**: 尝试使用完整路径指定字体

```python
import matplotlib.font_manager as fm
font_path = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = prop.get_name()
```

### Q3: Linux 上字体模糊或显示不清？

**A**: 安装更清晰的字体

```bash
# 安装思源黑体
sudo apt-get install fonts-noto-sans-cjk

# 清除缓存
rm -rf ~/.cache/matplotlib
fc-cache -fv
```

### Q4: Windows 上中文显示为繁体？

**A**: 指定简体中文字体

```python
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
```

---

## 推荐字体

### macOS
1. **Arial Unicode MS** (系统自带，全面支持中文)
2. **PingFang SC** (苹方简体，现代美观)

### Linux
1. **Noto Sans CJK SC** (Google 开发，显示清晰)
2. **WenQuanYi Zen Hei** (文泉驿正黑，开源)

### Windows
1. **Microsoft YaHei** (微软雅黑，系统自带)
2. **SimHei** (黑体，兼容性好)

---

## 完整测试脚本

创建 `test_chart_font.sh`:

```bash
#!/bin/bash

echo "🔍 检查系统字体..."
fc-list :lang=zh | head -5

echo ""
echo "🧪 生成测试图表..."
python3 -c "
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(8, 6))
ax.bar(['腾讯云-72B', '腾讯云-671B', '火山云-72B'], [65, 78, 63])
ax.set_title('TTFT 降低率对比', fontsize=14, fontweight='bold')
ax.set_xlabel('测试场景', fontsize=12)
ax.set_ylabel('降低百分比 (%)', fontsize=12)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('test_font.png', dpi=150)
print('✅ 测试图表已生成: test_font.png')
"

echo ""
echo "👀 请查看 test_font.png"
echo "   如果中文正常 → 字体配置成功"
echo "   如果显示方框 → 需要安装中文字体"
```

运行：
```bash
chmod +x test_chart_font.sh
./test_chart_font.sh
```

---

## 总结

### 最简单的方法

1. ✅ **安装中文字体**（Linux 用户）
   ```bash
   sudo apt-get install fonts-noto-cjk
   ```

2. ✅ **清除缓存**
   ```bash
   rm -rf ~/.matplotlib/*.cache
   ```

3. ✅ **重新生成报告**
   ```bash
   python3 reports/generate_multi_scenario_report.py \
       --scenario "测试" --stats stats.json \
       --output report.md
   ```

### 如果还是不行

- 使用 **方案 C**（英文标签）
- 或使用 **方案 D**（禁用图表）

---

**需要帮助？**
查看详细图表说明: `docs/CHARTS_EXPLANATION.md`
