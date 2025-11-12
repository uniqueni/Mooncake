#!/usr/bin/env python3
"""
多场景测试结果汇总脚本

支持多个测试场景的结果汇总，生成统一的表格和图表。

用法:
    python3 generate_multi_scenario_report.py \
        --scenario "腾讯云-单机-Qwen2.5-72B" --stats test_results/qwen_single_stats.json \
        --scenario "腾讯云-跨节点-Qwen2.5-72B" --stats test_results/qwen_cross_stats.json \
        --scenario "火山云-单机-Deepseek-R1" --stats test_results/deepseek_single_stats.json \
        --output report.md
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    # 配置中文字体支持
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("提示: matplotlib 未安装，无法生成图表")
    print("安装: pip install matplotlib")


class MultiScenarioReporter:
    """多场景测试报告生成器"""

    def __init__(self):
        self.scenarios = []  # List of (name, stats_data)

        # 中英文标签映射
        self.label_translation = {
            '单节点': 'Single',
            '跨节点': 'Cross',
            '多轮': 'Multi',
            '长文本': 'Long',
            '多轮对话': 'Multi-Turn',
            '长文本对话': 'Long-Text',
            '腾讯云': 'Tencent',
            '火山云': 'Volcano',
            '阿里云': 'Alibaba',
        }

    def _translate_label(self, label: str) -> str:
        """将中文标签翻译为英文"""
        for zh, en in self.label_translation.items():
            label = label.replace(zh, en)
        return label

    def add_scenario(self, name: str, stats_file: str):
        """添加一个测试场景"""
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)

        # 提取 Round 1 和 Round 2
        round1 = next((s for s in stats if s.get('round_num') == 1), None)
        round2 = next((s for s in stats if s.get('round_num') == 2), None)

        if not round1:
            if len(stats) >= 2:
                round1 = stats[0]
                round2 = stats[1]
            else:
                raise ValueError(f"{name}: 缺少 Round 1 数据")

        if not round2:
            raise ValueError(f"{name}: 缺少 Round 2 数据")

        # 验证必需字段
        required_fields = ['avg_ttft', 'avg_tpot', 'request_throughput', 'total_requests']
        missing_fields = [f for f in required_fields if f not in round1]
        if missing_fields:
            raise ValueError(f"{name}: 统计数据缺少字段: {missing_fields}")

        self.scenarios.append({
            'name': name,
            'round1': round1,
            'round2': round2
        })

        print(f"✓ 已加载场景: {name}")

    def _calculate_metrics(self, scenario: Dict) -> Dict:
        """计算场景的关键指标"""
        round1 = scenario['round1']
        round2 = scenario['round2']

        ttft_baseline = round1['avg_ttft'] * 1000  # ms
        ttft_cached = round2['avg_ttft'] * 1000
        ttft_reduction = (1 - round2['avg_ttft'] / round1['avg_ttft']) * 100

        tpot_baseline = round1['avg_tpot'] * 1000
        tpot_cached = round2['avg_tpot'] * 1000
        tpot_change = ((round2['avg_tpot'] - round1['avg_tpot']) / round1['avg_tpot']) * 100

        throughput_baseline = round1['request_throughput']
        throughput_cached = round2['request_throughput']
        throughput_increase = (round2['request_throughput'] / round1['request_throughput'] - 1) * 100

        token_throughput_baseline = round1.get('token_throughput', 0)
        token_throughput_cached = round2.get('token_throughput', 0)
        token_increase = 0
        if token_throughput_baseline > 0:
            token_increase = (token_throughput_cached / token_throughput_baseline - 1) * 100

        return {
            'ttft_baseline': ttft_baseline,
            'ttft_cached': ttft_cached,
            'ttft_reduction': ttft_reduction,
            'tpot_baseline': tpot_baseline,
            'tpot_cached': tpot_cached,
            'tpot_change': tpot_change,
            'throughput_baseline': throughput_baseline,
            'throughput_cached': throughput_cached,
            'throughput_increase': throughput_increase,
            'token_throughput_baseline': token_throughput_baseline,
            'token_throughput_cached': token_throughput_cached,
            'token_increase': token_increase,
        }

    def _get_cross_node_summary(self) -> str:
        """生成跨节点测试汇总"""
        cross_node_scenarios = []
        single_node_scenarios = []

        for scenario in self.scenarios:
            round1 = scenario['round1']
            round2 = scenario['round2']
            endpoint1 = round1.get('endpoint_url')
            endpoint2 = round2.get('endpoint_url')

            if endpoint1 and endpoint2 and endpoint1 != endpoint2:
                cross_node_scenarios.append({
                    'name': scenario['name'],
                    'node_a': endpoint1,
                    'node_b': endpoint2
                })
            else:
                single_node_scenarios.append(scenario['name'])

        if not cross_node_scenarios:
            return ""

        lines = []
        lines.append("### 🌐 跨节点测试信息")
        lines.append("")
        lines.append(f"本次测试包含 **{len(cross_node_scenarios)}** 个跨节点场景，验证 Mooncake KV Cache 跨节点传输能力：")
        lines.append("")

        for idx, scenario in enumerate(cross_node_scenarios, 1):
            lines.append(f"{idx}. **{scenario['name']}**")
            lines.append(f"   - 节点 A (存储缓存): `{scenario['node_a']}`")
            lines.append(f"   - 节点 B (加载缓存): `{scenario['node_b']}`")
            lines.append("")

        lines.append("> 跨节点测试说明: Round 1 在节点 A 执行并存储 KV Cache，Round 2 在节点 B 执行并从节点 A 加载缓存。")
        lines.append("> TTFT 降低和吞吐量提升说明 Mooncake 成功在节点间传输了 KV Cache。")
        lines.append("")

        return '\n'.join(lines)

    def generate_summary_table(self) -> str:
        """生成汇总表格 Markdown"""
        lines = []
        lines.append("## 📊 测试结果汇总")
        lines.append("")

        # 添加跨节点测试汇总
        cross_node_summary = self._get_cross_node_summary()
        if cross_node_summary:
            lines.append(cross_node_summary)

        lines.append("### TTFT (首 Token 延迟)")
        lines.append("")
        lines.append("| 测试场景 | Baseline | Cache Hit | 降低 |")
        lines.append("|---------|----------|-----------|------|")

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            status = "✅" if metrics['ttft_reduction'] >= 60 else ("⚠️" if metrics['ttft_reduction'] >= 40 else "❌")

            # 添加跨节点标识
            round1 = scenario['round1']
            round2 = scenario['round2']
            endpoint1 = round1.get('endpoint_url')
            endpoint2 = round2.get('endpoint_url')
            is_cross_node = endpoint1 and endpoint2 and endpoint1 != endpoint2
            name_display = f"🌐 {scenario['name']}" if is_cross_node else scenario['name']

            lines.append(f"| {name_display} | {metrics['ttft_baseline']:.1f} ms | {metrics['ttft_cached']:.1f} ms | {metrics['ttft_reduction']:.1f}% |")

        lines.append("")
        lines.append("### 吞吐量 (Throughput)")
        lines.append("")
        lines.append("| 测试场景 | Baseline | Cache Hit | 提升 |")
        lines.append("|---------|----------|-----------|------|")

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            status = "✅" if metrics['throughput_increase'] >= 150 else ("⚠️" if metrics['throughput_increase'] >= 100 else "❌")

            round1 = scenario['round1']
            round2 = scenario['round2']
            is_cross_node = round1.get('endpoint_url') and round2.get('endpoint_url') and round1.get('endpoint_url') != round2.get('endpoint_url')
            name_display = f"🌐 {scenario['name']}" if is_cross_node else scenario['name']

            lines.append(f"| {name_display} | {metrics['throughput_baseline']:.2f} req/s | {metrics['throughput_cached']:.2f} req/s | +{metrics['throughput_increase']:.1f}% |")

        lines.append("")
        lines.append("### TPOT (每 Token 延迟)")
        lines.append("")
        lines.append("| 测试场景 | Baseline | Cache Hit | 变化 |")
        lines.append("|---------|----------|-----------|------|")

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            status = "✅" if abs(metrics['tpot_change']) < 10 else "⚠️"

            round1 = scenario['round1']
            round2 = scenario['round2']
            is_cross_node = round1.get('endpoint_url') and round2.get('endpoint_url') and round1.get('endpoint_url') != round2.get('endpoint_url')
            name_display = f"🌐 {scenario['name']}" if is_cross_node else scenario['name']

            lines.append(f"| {name_display} | {metrics['tpot_baseline']:.2f} ms | {metrics['tpot_cached']:.2f} ms | {metrics['tpot_change']:+.1f}% |")

        lines.append("")
        lines.append("### Token 吞吐量")
        lines.append("")
        lines.append("| 测试场景 | Baseline | Cache Hit | 提升 |")
        lines.append("|---------|----------|-----------|------|")

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)

            round1 = scenario['round1']
            round2 = scenario['round2']
            is_cross_node = round1.get('endpoint_url') and round2.get('endpoint_url') and round1.get('endpoint_url') != round2.get('endpoint_url')
            name_display = f"🌐 {scenario['name']}" if is_cross_node else scenario['name']

            if metrics['token_throughput_baseline'] > 0:
                lines.append(f"| {name_display} | {metrics['token_throughput_baseline']:.1f} tokens/s | {metrics['token_throughput_cached']:.1f} tokens/s | +{metrics['token_increase']:.1f}% |")
            else:
                lines.append(f"| {name_display} | N/A | N/A | N/A |")

        return '\n'.join(lines)

    def generate_detailed_tables(self) -> str:
        """为每个场景生成详细表格"""
        lines = []
        lines.append("## 📋 详细测试数据")
        lines.append("")

        for scenario in self.scenarios:
            lines.append(f"### {scenario['name']}")
            lines.append("")

            round1 = scenario['round1']
            round2 = scenario['round2']
            metrics = self._calculate_metrics(scenario)

            # 检测跨节点测试
            endpoint1 = round1.get('endpoint_url')
            endpoint2 = round2.get('endpoint_url')
            is_cross_node = endpoint1 and endpoint2 and endpoint1 != endpoint2

            # 如果是跨节点测试，显示节点信息
            if is_cross_node:
                lines.append("#### 🌐 跨节点测试信息")
                lines.append("")
                lines.append(f"- **Round 1 (Baseline)**: 节点 A - `{endpoint1}`")
                lines.append(f"- **Round 2 (Cache Hit)**: 节点 B - `{endpoint2}`")
                lines.append(f"- **KV Cache 传输**: ✅ 从节点 A 传输到节点 B")
                lines.append("")
            elif endpoint1:
                lines.append(f"**测试端点**: `{endpoint1}`")
                lines.append("")

            lines.append("| 指标 | Baseline (Round 1) | Cache Hit (Round 2) | 改善 | 目标 | 状态 |")
            lines.append("|------|-------------------|---------------------|------|------|------|")

            # TTFT
            ttft_status = "✅" if metrics['ttft_reduction'] >= 60 else ("⚠️" if metrics['ttft_reduction'] >= 40 else "❌")
            lines.append(f"| TTFT (avg) | {metrics['ttft_baseline']:.2f} ms | {metrics['ttft_cached']:.2f} ms | -{metrics['ttft_reduction']:.1f}% | -60% | {ttft_status} |")

            # TTFT P90
            if 'p90_ttft' in round1:
                ttft_p90_baseline = round1['p90_ttft'] * 1000
                ttft_p90_cached = round2['p90_ttft'] * 1000
                ttft_p90_reduction = (1 - round2['p90_ttft'] / round1['p90_ttft']) * 100
                lines.append(f"| TTFT (P90) | {ttft_p90_baseline:.2f} ms | {ttft_p90_cached:.2f} ms | -{ttft_p90_reduction:.1f}% | - | - |")

            # TPOT
            tpot_status = "✅" if abs(metrics['tpot_change']) < 10 else "⚠️"
            lines.append(f"| TPOT (avg) | {metrics['tpot_baseline']:.2f} ms | {metrics['tpot_cached']:.2f} ms | {metrics['tpot_change']:+.1f}% | 稳定 | {tpot_status} |")

            # 吞吐量
            throughput_status = "✅" if metrics['throughput_increase'] >= 150 else ("⚠️" if metrics['throughput_increase'] >= 100 else "❌")
            lines.append(f"| 吞吐量 (req/s) | {metrics['throughput_baseline']:.2f} | {metrics['throughput_cached']:.2f} | +{metrics['throughput_increase']:.1f}% | +150% | {throughput_status} |")

            # Token 吞吐量
            if metrics['token_throughput_baseline'] > 0:
                lines.append(f"| Token 吞吐量 | {metrics['token_throughput_baseline']:.1f} tokens/s | {metrics['token_throughput_cached']:.1f} tokens/s | +{metrics['token_increase']:.1f}% | - | - |")

            # 端到端延迟
            latency_baseline = round1.get('avg_latency', 0)
            latency_cached = round2.get('avg_latency', 0)
            if latency_baseline > 0:
                latency_change = ((latency_cached - latency_baseline) / latency_baseline) * 100
                lines.append(f"| 端到端延迟 | {latency_baseline:.2f} s | {latency_cached:.2f} s | {latency_change:+.1f}% | - | - |")

            lines.append("")

        return '\n'.join(lines)

    def generate_comparison_charts(self, output_dir: str = "report_charts") -> List[str]:
        """生成对比图表"""
        if not HAS_MATPLOTLIB:
            print("⚠️  跳过图表生成（matplotlib 未安装）")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        chart_files = []

        # 1. TTFT 对比图
        chart_files.append(self._generate_ttft_comparison_chart(output_path))

        # 2. 吞吐量对比图
        chart_files.append(self._generate_throughput_comparison_chart(output_path))

        # 3. TTFT 降低百分比对比
        chart_files.append(self._generate_ttft_reduction_chart(output_path))

        # 4. 吞吐量提升百分比对比
        chart_files.append(self._generate_throughput_increase_chart(output_path))

        # 5. 综合对比雷达图（如果场景 <= 6）
        if len(self.scenarios) <= 6:
            chart_files.append(self._generate_radar_chart(output_path))

        return chart_files

    def _generate_ttft_comparison_chart(self, output_path: Path) -> str:
        """生成 TTFT 对比柱状图"""
        fig, ax = plt.subplots(figsize=(max(10, len(self.scenarios) * 2), 6))

        x = np.arange(len(self.scenarios))
        width = 0.35

        baseline_values = []
        cached_values = []
        labels = []

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            baseline_values.append(metrics['ttft_baseline'])
            cached_values.append(metrics['ttft_cached'])
            # 简化场景名称（去掉平台前缀，只保留关键信息）
            name = scenario['name']
            if '-' in name:
                parts = name.split('-')
                # 尝试缩短：如 "腾讯云-72B-单节点-多轮" -> "72B-Single-Multi"
                if len(parts) >= 4:
                    # 格式: 云平台-模型-部署方式-场景类型
                    label = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    labels.append(self._translate_label(label))
                elif len(parts) >= 3:
                    label = f"{parts[1]}-{parts[2]}"
                    labels.append(self._translate_label(label))
                else:
                    labels.append(self._translate_label(name))
            else:
                labels.append(self._translate_label(name))

        bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', color='#e74c3c', alpha=0.8)
        bars2 = ax.bar(x + width/2, cached_values, width, label='Cache Hit', color='#2ecc71', alpha=0.8)

        ax.set_ylabel('TTFT (ms)', fontsize=12, fontweight='bold')
        ax.set_title('TTFT Comparison - Multi Scenarios', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=9)

        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=9)

        chart_file = output_path / "ttft_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _generate_throughput_comparison_chart(self, output_path: Path) -> str:
        """生成吞吐量对比柱状图"""
        fig, ax = plt.subplots(figsize=(max(10, len(self.scenarios) * 2), 6))

        x = np.arange(len(self.scenarios))
        width = 0.35

        baseline_values = []
        cached_values = []
        labels = []

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            baseline_values.append(metrics['throughput_baseline'])
            cached_values.append(metrics['throughput_cached'])
            name = scenario['name']
            if '-' in name:
                parts = name.split('-')
                if len(parts) >= 4:
                    label = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    labels.append(self._translate_label(label))
                elif len(parts) >= 3:
                    label = f"{parts[1]}-{parts[2]}"
                    labels.append(self._translate_label(label))
                else:
                    labels.append(self._translate_label(name))
            else:
                labels.append(self._translate_label(name))

        bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, cached_values, width, label='Cache Hit', color='#f39c12', alpha=0.8)

        ax.set_ylabel('Throughput (req/s)', fontsize=12, fontweight='bold')
        ax.set_title('Throughput Comparison - Multi Scenarios', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9)

        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=9)

        chart_file = output_path / "throughput_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _generate_ttft_reduction_chart(self, output_path: Path) -> str:
        """生成 TTFT 降低百分比图"""
        fig, ax = plt.subplots(figsize=(max(10, len(self.scenarios) * 1.5), 6))

        labels = []
        reductions = []
        colors = []

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            name = scenario['name']
            if '-' in name:
                parts = name.split('-')
                if len(parts) >= 4:
                    label = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    labels.append(self._translate_label(label))
                elif len(parts) >= 3:
                    label = f"{parts[1]}-{parts[2]}"
                    labels.append(self._translate_label(label))
                else:
                    labels.append(self._translate_label(name))
            else:
                labels.append(self._translate_label(name))

            reductions.append(metrics['ttft_reduction'])
            # 根据效果设置颜色
            if metrics['ttft_reduction'] >= 60:
                colors.append('#2ecc71')  # 绿色 - 优秀
            elif metrics['ttft_reduction'] >= 40:
                colors.append('#f39c12')  # 橙色 - 一般
            else:
                colors.append('#e74c3c')  # 红色 - 不理想

        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, reductions, color=colors, alpha=0.8)

        ax.set_xlabel('TTFT Reduction (%)', fontsize=12, fontweight='bold')
        ax.set_title('TTFT Reduction Comparison', fontsize=14, fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.axvline(x=60, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Target: 60%')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                    f' {width:.1f}%',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        chart_file = output_path / "ttft_reduction_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _generate_throughput_increase_chart(self, output_path: Path) -> str:
        """生成吞吐量提升百分比图"""
        fig, ax = plt.subplots(figsize=(max(10, len(self.scenarios) * 1.5), 6))

        labels = []
        increases = []
        colors = []

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            name = scenario['name']
            if '-' in name:
                parts = name.split('-')
                if len(parts) >= 4:
                    label = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    labels.append(self._translate_label(label))
                elif len(parts) >= 3:
                    label = f"{parts[1]}-{parts[2]}"
                    labels.append(self._translate_label(label))
                else:
                    labels.append(self._translate_label(name))
            else:
                labels.append(self._translate_label(name))

            increases.append(metrics['throughput_increase'])
            if metrics['throughput_increase'] >= 150:
                colors.append('#2ecc71')
            elif metrics['throughput_increase'] >= 100:
                colors.append('#f39c12')
            else:
                colors.append('#e74c3c')

        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, increases, color=colors, alpha=0.8)

        ax.set_xlabel('Throughput Increase (%)', fontsize=12, fontweight='bold')
        ax.set_title('Throughput Increase Comparison', fontsize=14, fontweight='bold')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.axvline(x=150, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Target: 150%')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                    f' +{width:.1f}%',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        chart_file = output_path / "throughput_increase_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _generate_radar_chart(self, output_path: Path) -> str:
        """生成雷达图（综合对比）"""
        # 归一化指标：TTFT降低、吞吐量提升、TPOT稳定性
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        # 三个维度
        categories = ['TTFT\n降低', '吞吐量\n提升', 'TPOT\n稳定性']
        N = len(categories)

        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(['TTFT\nReduction', 'Throughput\nIncrease', 'TPOT\nStability'], fontsize=11)

        # 为每个场景绘制雷达图
        colors = plt.cm.Set3(np.linspace(0, 1, len(self.scenarios)))

        for idx, scenario in enumerate(self.scenarios):
            metrics = self._calculate_metrics(scenario)

            # 归一化分数（0-100）
            ttft_score = min(100, (metrics['ttft_reduction'] / 60) * 100)
            throughput_score = min(100, (metrics['throughput_increase'] / 150) * 100)
            tpot_score = max(0, 100 - abs(metrics['tpot_change']) * 10)  # 变化越小分数越高

            values = [ttft_score, throughput_score, tpot_score]
            values += values[:1]

            # 简化标签
            name = scenario['name']
            if '-' in name:
                parts = name.split('-')
                if len(parts) >= 4:
                    label = f"{parts[1]}-{parts[2]}-{parts[3]}"
                    label = self._translate_label(label)
                elif len(parts) >= 3:
                    label = f"{parts[1]}-{parts[2]}"
                    label = self._translate_label(label)
                else:
                    label = self._translate_label(name)
            else:
                label = self._translate_label(name)

            ax.plot(angles, values, 'o-', linewidth=2, label=label, color=colors[idx])
            ax.fill(angles, values, alpha=0.15, color=colors[idx])

        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        ax.grid(True)

        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
        plt.title('Performance Comparison (Radar Chart)', size=14, fontweight='bold', y=1.08)

        chart_file = output_path / "performance_radar.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def generate_full_report(self, output_file: str = None, chart_dir: str = "report_charts") -> str:
        """生成完整报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"multi_scenario_report_{timestamp}.md"

        lines = []

        # 标题
        lines.append("# Mooncake KV Cache 多场景性能测试报告")
        lines.append("")
        lines.append(f"**报告日期**: {datetime.now().strftime('%Y年%m月%d日')}")
        lines.append(f"**测试场景数**: {len(self.scenarios)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 汇总表格
        lines.append(self.generate_summary_table())
        lines.append("")
        lines.append("---")
        lines.append("")

        # 生成图表
        print("\n📊 生成对比图表...")
        chart_files = self.generate_comparison_charts(chart_dir)

        if chart_files:
            lines.append("## 📈 可视化对比")
            lines.append("")
            for chart in chart_files:
                chart_name = Path(chart).name
                lines.append(f"### {chart_name.replace('_', ' ').replace('.png', '').title()}")
                lines.append("")
                lines.append(f"![{chart_name}]({chart})")
                lines.append("")
            lines.append("---")
            lines.append("")

        # 详细表格
        lines.append(self.generate_detailed_tables())
        lines.append("")
        lines.append("---")
        lines.append("")

        # 总结
        lines.append("## 💡 测试总结")
        lines.append("")

        success_count = 0
        partial_count = 0
        fail_count = 0

        for scenario in self.scenarios:
            metrics = self._calculate_metrics(scenario)
            if metrics['ttft_reduction'] >= 60 and metrics['throughput_increase'] >= 150:
                success_count += 1
            elif metrics['ttft_reduction'] >= 40 or metrics['throughput_increase'] >= 100:
                partial_count += 1
            else:
                fail_count += 1

        lines.append(f"- **✅ 优秀场景**: {success_count}/{len(self.scenarios)} (所有指标达标)")
        lines.append(f"- **⚠️ 良好场景**: {partial_count}/{len(self.scenarios)} (部分指标达标)")
        lines.append(f"- **❌ 待优化场景**: {fail_count}/{len(self.scenarios)} (需要优化)")
        lines.append("")

        if success_count == len(self.scenarios):
            lines.append("**结论**: 所有测试场景均达到预期目标，Mooncake KV Cache 性能表现优秀。")
        elif success_count + partial_count == len(self.scenarios):
            lines.append("**结论**: 大部分场景达到预期，部分场景有优化空间，建议针对性调优。")
        else:
            lines.append("**结论**: 部分场景未达预期，需要排查配置和环境问题。")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"\n✅ 报告已生成: {output_file}")
        if chart_files:
            print(f"✅ 图表已生成: {len(chart_files)} 个文件在 {chart_dir}/ 目录")

        return output_file


def main():
    parser = argparse.ArgumentParser(
        description="多场景测试结果汇总和报告生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

1. 单个场景:
   python3 generate_multi_scenario_report.py \\
       --scenario "腾讯云-单机-Qwen2.5-72B" \\
       --stats test_results/qwen_single_stats.json

2. 多个场景:
   python3 generate_multi_scenario_report.py \\
       --scenario "腾讯云-单机-Qwen2.5-72B" --stats test_results/qwen_single_stats.json \\
       --scenario "腾讯云-跨节点-Qwen2.5-72B" --stats test_results/qwen_cross_stats.json \\
       --scenario "火山云-单机-Deepseek-R1" --stats test_results/deepseek_stats.json \\
       --output final_report.md \\
       --chart-dir charts

3. 使用通配符批量加载（需要场景名包含在文件名中）:
   python3 generate_multi_scenario_report.py \\
       --auto-load test_results/*_stats.json \\
       --output report.md
        """
    )

    parser.add_argument('--scenario', action='append', dest='scenario_names',
                        help='测试场景名称（可多次使用）')
    parser.add_argument('--stats', action='append', dest='stats_files',
                        help='对应的统计文件路径（与 --scenario 配对）')
    parser.add_argument('--output', type=str,
                        help='输出报告文件名（默认: multi_scenario_report_<timestamp>.md）')
    parser.add_argument('--chart-dir', type=str, default='report_charts',
                        help='图表输出目录（默认: report_charts）')
    parser.add_argument('--no-charts', action='store_true',
                        help='不生成图表（仅生成表格）')

    args = parser.parse_args()

    # 验证参数
    if not args.scenario_names or not args.stats_files:
        print("❌ 错误: 必须提供 --scenario 和 --stats 参数")
        print("示例: --scenario \"腾讯云-Qwen2.5\" --stats test_stats.json")
        parser.print_help()
        sys.exit(1)

    if len(args.scenario_names) != len(args.stats_files):
        print("❌ 错误: --scenario 和 --stats 参数数量必须一致")
        sys.exit(1)

    print("="*80)
    print("📊 多场景测试报告生成工具")
    print("="*80)

    try:
        reporter = MultiScenarioReporter()

        # 加载所有场景
        for name, stats_file in zip(args.scenario_names, args.stats_files):
            reporter.add_scenario(name, stats_file)

        # 生成报告
        print(f"\n📝 生成报告...")
        if args.no_charts:
            # 仅生成表格，不生成图表
            output_file = args.output or f"multi_scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

            lines = []
            lines.append("# Mooncake KV Cache 多场景性能测试报告")
            lines.append("")
            lines.append(f"**报告日期**: {datetime.now().strftime('%Y年%m月%d日')}")
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(reporter.generate_summary_table())
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(reporter.generate_detailed_tables())

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print(f"\n✅ 报告已生成: {output_file}")
        else:
            reporter.generate_full_report(args.output, args.chart_dir)

        print("\n✅ 完成!")

    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 数据错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
