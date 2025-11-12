#!/usr/bin/env python3
"""
详细技术分析工具 - 分析 results 文件

用于深度分析每个请求的性能数据，生成趋势图和技术报告。

用法:
    python3 analyze_results.py --results test_results/with-cache_72B_results_*.json
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import sys
import statistics

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
    print("❌ 错误: 需要安装 matplotlib")
    print("运行: pip install matplotlib")
    sys.exit(1)


class DetailedAnalyzer:
    """详细性能分析器"""

    def __init__(self, results_file: str):
        """初始化"""
        self.results_file = Path(results_file)

        # 加载数据
        with open(self.results_file, 'r', encoding='utf-8') as f:
            self.results = json.load(f)

        print(f"✓ 加载原始数据: {len(self.results)} 条请求记录")

        if not self.results:
            raise ValueError("结果文件为空")

        # 分离 Round 1 和 Round 2
        self.round1 = [r for r in self.results if r['round_num'] == 1]
        self.round2 = [r for r in self.results if r['round_num'] == 2]

        print(f"  Round 1: {len(self.round1)} 条")
        print(f"  Round 2: {len(self.round2)} 条")

    def generate_all_charts(self, output_dir: str = "analysis_charts"):
        """生成所有分析图表"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n{'='*80}")
        print("📊 生成分析图表")
        print(f"{'='*80}")

        charts = []

        # 1. TTFT 时间序列图
        chart = self._plot_ttft_timeline(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        # 2. TTFT 分布对比图
        chart = self._plot_ttft_distribution(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        # 3. 每个请求的 TTFT 对比
        chart = self._plot_request_comparison(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        # 4. TPOT 分析
        chart = self._plot_tpot_analysis(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        # 5. 延迟分解图
        chart = self._plot_latency_breakdown(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        # 6. 异常值检测
        chart = self._plot_outliers(output_path)
        if chart:
            charts.append(chart)
            print(f"✓ {chart}")

        print(f"\n✅ 共生成 {len(charts)} 个图表")
        return charts

    def _plot_ttft_timeline(self, output_path: Path) -> str:
        """TTFT 时间序列图 - 看性能随时间的变化"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Round 1
        round1_ids = [r['request_id'] for r in self.round1]
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]

        ax1.plot(round1_ids, round1_ttfts, marker='o', linewidth=2, markersize=6,
                 color='#e74c3c', label='Round 1 (Cold Start)')
        ax1.axhline(y=statistics.mean(round1_ttfts), color='red', linestyle='--',
                    alpha=0.5, label=f'平均值: {statistics.mean(round1_ttfts):.1f}ms')
        ax1.set_xlabel('请求序号', fontsize=12)
        ax1.set_ylabel('TTFT (ms)', fontsize=12)
        ax1.set_title('Round 1: TTFT 随时间变化（冷启动）', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Round 2
        round2_ids = [r['request_id'] for r in self.round2]
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]

        ax2.plot(round2_ids, round2_ttfts, marker='o', linewidth=2, markersize=6,
                 color='#2ecc71', label='Round 2 (Cache Hit)')
        ax2.axhline(y=statistics.mean(round2_ttfts), color='green', linestyle='--',
                    alpha=0.5, label=f'平均值: {statistics.mean(round2_ttfts):.1f}ms')
        ax2.set_xlabel('请求序号', fontsize=12)
        ax2.set_ylabel('TTFT (ms)', fontsize=12)
        ax2.set_title('Round 2: TTFT 随时间变化（缓存命中）', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        chart_file = output_path / "1_ttft_timeline.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _plot_ttft_distribution(self, output_path: Path) -> str:
        """TTFT 分布直方图 - 看数据分布是否均匀"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Round 1 分布
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        axes[0].hist(round1_ttfts, bins=20, color='#e74c3c', alpha=0.7, edgecolor='black')
        axes[0].axvline(statistics.mean(round1_ttfts), color='red', linestyle='--',
                        linewidth=2, label=f'平均: {statistics.mean(round1_ttfts):.1f}ms')
        axes[0].axvline(statistics.median(round1_ttfts), color='orange', linestyle='--',
                        linewidth=2, label=f'中位数: {statistics.median(round1_ttfts):.1f}ms')
        axes[0].set_xlabel('TTFT (ms)', fontsize=12)
        axes[0].set_ylabel('请求数', fontsize=12)
        axes[0].set_title('Round 1: TTFT 分布', fontsize=13, fontweight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3, axis='y')

        # Round 2 分布
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]
        axes[1].hist(round2_ttfts, bins=20, color='#2ecc71', alpha=0.7, edgecolor='black')
        axes[1].axvline(statistics.mean(round2_ttfts), color='green', linestyle='--',
                        linewidth=2, label=f'平均: {statistics.mean(round2_ttfts):.1f}ms')
        axes[1].axvline(statistics.median(round2_ttfts), color='darkgreen', linestyle='--',
                        linewidth=2, label=f'中位数: {statistics.median(round2_ttfts):.1f}ms')
        axes[1].set_xlabel('TTFT (ms)', fontsize=12)
        axes[1].set_ylabel('请求数', fontsize=12)
        axes[1].set_title('Round 2: TTFT 分布', fontsize=13, fontweight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        chart_file = output_path / "2_ttft_distribution.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _plot_request_comparison(self, output_path: Path) -> str:
        """每个请求的 TTFT 对比 - 逐一对比缓存效果"""
        fig, ax = plt.subplots(figsize=(14, 8))

        request_ids = list(range(len(self.round1)))
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]

        x = np.arange(len(request_ids))
        width = 0.35

        bars1 = ax.bar(x - width/2, round1_ttfts, width, label='Round 1 (无缓存)',
                       color='#e74c3c', alpha=0.8)
        bars2 = ax.bar(x + width/2, round2_ttfts, width, label='Round 2 (有缓存)',
                       color='#2ecc71', alpha=0.8)

        ax.set_xlabel('请求序号', fontsize=12)
        ax.set_ylabel('TTFT (ms)', fontsize=12)
        ax.set_title('逐请求 TTFT 对比：缓存效果', fontsize=14, fontweight='bold')
        ax.set_xticks(x[::2])  # 每隔一个显示
        ax.set_xticklabels(request_ids[::2])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 添加平均值线
        ax.axhline(y=statistics.mean(round1_ttfts), color='red', linestyle='--',
                   alpha=0.5, label='R1 平均')
        ax.axhline(y=statistics.mean(round2_ttfts), color='green', linestyle='--',
                   alpha=0.5, label='R2 平均')

        plt.tight_layout()
        chart_file = output_path / "3_request_comparison.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _plot_tpot_analysis(self, output_path: Path) -> str:
        """TPOT 分析 - 看 Decode 阶段性能"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # TPOT 对比
        round1_tpots = [r['tpot'] * 1000 for r in self.round1 if r.get('tpot')]
        round2_tpots = [r['tpot'] * 1000 for r in self.round2 if r.get('tpot')]

        bp1 = axes[0].boxplot([round1_tpots, round2_tpots],
                               labels=['Round 1\n(无缓存)', 'Round 2\n(有缓存)'],
                               patch_artist=True)
        bp1['boxes'][0].set_facecolor('#e74c3c')
        bp1['boxes'][1].set_facecolor('#2ecc71')

        axes[0].set_ylabel('TPOT (ms/token)', fontsize=12)
        axes[0].set_title('TPOT 箱线图对比', fontsize=13, fontweight='bold')
        axes[0].grid(True, alpha=0.3, axis='y')

        # TPOT 时间序列
        axes[1].plot([r['request_id'] for r in self.round1],
                     [r['tpot'] * 1000 for r in self.round1 if r.get('tpot')],
                     marker='o', label='Round 1', color='#e74c3c', alpha=0.7)
        axes[1].plot([r['request_id'] for r in self.round2],
                     [r['tpot'] * 1000 for r in self.round2 if r.get('tpot')],
                     marker='s', label='Round 2', color='#2ecc71', alpha=0.7)

        axes[1].set_xlabel('请求序号', fontsize=12)
        axes[1].set_ylabel('TPOT (ms/token)', fontsize=12)
        axes[1].set_title('TPOT 随时间变化', fontsize=13, fontweight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        chart_file = output_path / "4_tpot_analysis.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _plot_latency_breakdown(self, output_path: Path) -> str:
        """延迟分解图 - 看 TTFT vs 总延迟"""
        fig, ax = plt.subplots(figsize=(12, 7))

        # 计算每个请求的 Decode 时间
        for round_num, (round_data, color, label) in enumerate([
            (self.round1, '#e74c3c', 'Round 1'),
            (self.round2, '#2ecc71', 'Round 2')
        ], 1):
            request_ids = [r['request_id'] for r in round_data]
            ttfts = [r['ttft'] for r in round_data]
            total_latencies = [r['e2e_latency'] for r in round_data]
            decode_times = [total - ttft for total, ttft in zip(total_latencies, ttfts)]

            x = np.array(request_ids) + (round_num - 1.5) * 0.35

            # 堆叠柱状图
            ax.bar(x, ttfts, width=0.35, label=f'{label} - Prefill (TTFT)',
                   color=color, alpha=0.7)
            ax.bar(x, decode_times, width=0.35, bottom=ttfts,
                   label=f'{label} - Decode', color=color, alpha=0.4)

        ax.set_xlabel('请求序号', fontsize=12)
        ax.set_ylabel('延迟 (秒)', fontsize=12)
        ax.set_title('延迟分解：Prefill (TTFT) vs Decode', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        chart_file = output_path / "5_latency_breakdown.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def _plot_outliers(self, output_path: Path) -> str:
        """异常值检测 - 找出性能异常的请求"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Round 1 TTFT 异常值
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        mean1 = statistics.mean(round1_ttfts)
        std1 = statistics.stdev(round1_ttfts)

        axes[0, 0].scatter(range(len(round1_ttfts)), round1_ttfts,
                          color='#e74c3c', alpha=0.6, s=50)
        axes[0, 0].axhline(y=mean1, color='blue', linestyle='-', linewidth=2, label='平均值')
        axes[0, 0].axhline(y=mean1 + 2*std1, color='red', linestyle='--',
                          linewidth=2, label='异常阈值 (+2σ)')
        axes[0, 0].axhline(y=mean1 - 2*std1, color='red', linestyle='--', linewidth=2)

        # 标记异常值
        outliers1 = [(i, v) for i, v in enumerate(round1_ttfts) if abs(v - mean1) > 2 * std1]
        if outliers1:
            outlier_ids, outlier_vals = zip(*outliers1)
            axes[0, 0].scatter(outlier_ids, outlier_vals, color='red', s=200,
                              marker='x', linewidths=3, label='异常值')

        axes[0, 0].set_xlabel('请求序号')
        axes[0, 0].set_ylabel('TTFT (ms)')
        axes[0, 0].set_title('Round 1: TTFT 异常值检测', fontweight='bold')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Round 2 TTFT 异常值
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]
        mean2 = statistics.mean(round2_ttfts)
        std2 = statistics.stdev(round2_ttfts)

        axes[0, 1].scatter(range(len(round2_ttfts)), round2_ttfts,
                          color='#2ecc71', alpha=0.6, s=50)
        axes[0, 1].axhline(y=mean2, color='blue', linestyle='-', linewidth=2, label='平均值')
        axes[0, 1].axhline(y=mean2 + 2*std2, color='red', linestyle='--',
                          linewidth=2, label='异常阈值 (+2σ)')
        axes[0, 1].axhline(y=mean2 - 2*std2, color='red', linestyle='--', linewidth=2)

        outliers2 = [(i, v) for i, v in enumerate(round2_ttfts) if abs(v - mean2) > 2 * std2]
        if outliers2:
            outlier_ids, outlier_vals = zip(*outliers2)
            axes[0, 1].scatter(outlier_ids, outlier_vals, color='red', s=200,
                              marker='x', linewidths=3, label='异常值')

        axes[0, 1].set_xlabel('请求序号')
        axes[0, 1].set_ylabel('TTFT (ms)')
        axes[0, 1].set_title('Round 2: TTFT 异常值检测', fontweight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 改善率分析
        improvements = [(r1['ttft'] - r2['ttft']) / r1['ttft'] * 100
                       for r1, r2 in zip(self.round1, self.round2)]

        axes[1, 0].bar(range(len(improvements)), improvements,
                      color=['#2ecc71' if i > 0 else '#e74c3c' for i in improvements],
                      alpha=0.7)
        axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=1)
        axes[1, 0].axhline(y=statistics.mean(improvements), color='blue',
                          linestyle='--', linewidth=2,
                          label=f'平均改善: {statistics.mean(improvements):.1f}%')
        axes[1, 0].set_xlabel('请求序号')
        axes[1, 0].set_ylabel('TTFT 改善 (%)')
        axes[1, 0].set_title('每个请求的缓存效果', fontweight='bold')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3, axis='y')

        # 失败请求统计
        failures1 = [r for r in self.round1 if not r.get('success', True)]
        failures2 = [r for r in self.round2 if not r.get('success', True)]

        axes[1, 1].bar(['Round 1\n(无缓存)', 'Round 2\n(有缓存)'],
                      [len(failures1), len(failures2)],
                      color=['#e74c3c', '#2ecc71'], alpha=0.7, width=0.5)
        axes[1, 1].set_ylabel('失败请求数')
        axes[1, 1].set_title('请求成功率', fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, axis='y')

        # 添加成功率文字
        success_rate1 = (len(self.round1) - len(failures1)) / len(self.round1) * 100
        success_rate2 = (len(self.round2) - len(failures2)) / len(self.round2) * 100
        axes[1, 1].text(0, len(failures1) + 0.5, f'{success_rate1:.1f}%\n成功',
                       ha='center', fontsize=11, fontweight='bold')
        axes[1, 1].text(1, len(failures2) + 0.5, f'{success_rate2:.1f}%\n成功',
                       ha='center', fontsize=11, fontweight='bold')

        plt.tight_layout()
        chart_file = output_path / "6_outliers_analysis.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(chart_file)

    def generate_technical_report(self, output_file: str = None) -> str:
        """生成技术分析报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"technical_analysis_{timestamp}.md"

        output_path = Path(output_file)

        md_lines = []

        # 标题
        md_lines.append("# 技术详细分析报告")
        md_lines.append("")
        md_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"**数据来源**: {self.results_file.name}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 数据概览
        md_lines.append("## 📊 数据概览")
        md_lines.append("")
        md_lines.append(f"- **总请求数**: {len(self.results)}")
        md_lines.append(f"- **Round 1 请求数**: {len(self.round1)}")
        md_lines.append(f"- **Round 2 请求数**: {len(self.round2)}")
        md_lines.append("")

        # TTFT 详细分析
        self._add_ttft_detailed_analysis(md_lines)
        md_lines.append("")

        # TPOT 分析
        self._add_tpot_detailed_analysis(md_lines)
        md_lines.append("")

        # 异常值分析
        self._add_outlier_analysis(md_lines)
        md_lines.append("")

        # 性能稳定性分析
        self._add_stability_analysis(md_lines)
        md_lines.append("")

        # 优化建议
        self._add_optimization_suggestions(md_lines)

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        print(f"✓ 技术报告已生成: {output_path}")
        return str(output_path)

    def _add_ttft_detailed_analysis(self, md_lines: List[str]):
        """添加 TTFT 详细分析"""
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]

        md_lines.append("## ⚡ TTFT 详细分析")
        md_lines.append("")
        md_lines.append("### Round 1 (Cold Start)")
        md_lines.append("")
        md_lines.append(f"- **平均值**: {statistics.mean(round1_ttfts):.2f} ms")
        md_lines.append(f"- **中位数**: {statistics.median(round1_ttfts):.2f} ms")
        md_lines.append(f"- **标准差**: {statistics.stdev(round1_ttfts):.2f} ms")
        md_lines.append(f"- **最小值**: {min(round1_ttfts):.2f} ms")
        md_lines.append(f"- **最大值**: {max(round1_ttfts):.2f} ms")
        md_lines.append(f"- **P90**: {sorted(round1_ttfts)[int(len(round1_ttfts)*0.9)]:.2f} ms")
        md_lines.append(f"- **P99**: {sorted(round1_ttfts)[int(len(round1_ttfts)*0.99)]:.2f} ms")
        md_lines.append("")

        md_lines.append("### Round 2 (Cache Hit)")
        md_lines.append("")
        md_lines.append(f"- **平均值**: {statistics.mean(round2_ttfts):.2f} ms")
        md_lines.append(f"- **中位数**: {statistics.median(round2_ttfts):.2f} ms")
        md_lines.append(f"- **标准差**: {statistics.stdev(round2_ttfts):.2f} ms")
        md_lines.append(f"- **最小值**: {min(round2_ttfts):.2f} ms")
        md_lines.append(f"- **最大值**: {max(round2_ttfts):.2f} ms")
        md_lines.append(f"- **P90**: {sorted(round2_ttfts)[int(len(round2_ttfts)*0.9)]:.2f} ms")
        md_lines.append(f"- **P99**: {sorted(round2_ttfts)[int(len(round2_ttfts)*0.99)]:.2f} ms")
        md_lines.append("")

        # 改善分析
        improvement = (1 - statistics.mean(round2_ttfts) / statistics.mean(round1_ttfts)) * 100
        md_lines.append(f"### 缓存效果")
        md_lines.append("")
        md_lines.append(f"- **平均 TTFT 降低**: {improvement:.1f}%")
        md_lines.append(f"- **中位数 TTFT 降低**: {(1 - statistics.median(round2_ttfts) / statistics.median(round1_ttfts)) * 100:.1f}%")

    def _add_tpot_detailed_analysis(self, md_lines: List[str]):
        """添加 TPOT 详细分析"""
        round1_tpots = [r['tpot'] * 1000 for r in self.round1 if r.get('tpot')]
        round2_tpots = [r['tpot'] * 1000 for r in self.round2 if r.get('tpot')]

        md_lines.append("## 🔄 TPOT 详细分析")
        md_lines.append("")
        md_lines.append(f"- **Round 1 平均**: {statistics.mean(round1_tpots):.2f} ms/token")
        md_lines.append(f"- **Round 2 平均**: {statistics.mean(round2_tpots):.2f} ms/token")
        md_lines.append(f"- **变化**: {((statistics.mean(round2_tpots) - statistics.mean(round1_tpots)) / statistics.mean(round1_tpots) * 100):+.1f}%")

    def _add_outlier_analysis(self, md_lines: List[str]):
        """添加异常值分析"""
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        mean1 = statistics.mean(round1_ttfts)
        std1 = statistics.stdev(round1_ttfts)

        outliers1 = [(i, r) for i, r in enumerate(self.round1)
                    if abs(r['ttft'] * 1000 - mean1) > 2 * std1]

        md_lines.append("## 🔍 异常值分析")
        md_lines.append("")
        md_lines.append(f"### Round 1 异常请求（超过 2σ）")
        md_lines.append("")

        if outliers1:
            md_lines.append(f"发现 {len(outliers1)} 个异常请求：")
            md_lines.append("")
            for i, r in outliers1[:5]:  # 只显示前 5 个
                md_lines.append(f"- **请求 {i}**: TTFT = {r['ttft']*1000:.2f} ms (偏离平均值 {abs(r['ttft']*1000 - mean1):.2f} ms)")
        else:
            md_lines.append("✅ 无明显异常值，性能稳定")

    def _add_stability_analysis(self, md_lines: List[str]):
        """添加稳定性分析"""
        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]

        cv1 = (statistics.stdev(round1_ttfts) / statistics.mean(round1_ttfts)) * 100
        cv2 = (statistics.stdev(round2_ttfts) / statistics.mean(round2_ttfts)) * 100

        md_lines.append("## 📈 性能稳定性分析")
        md_lines.append("")
        md_lines.append(f"- **Round 1 变异系数 (CV)**: {cv1:.2f}%")
        md_lines.append(f"- **Round 2 变异系数 (CV)**: {cv2:.2f}%")
        md_lines.append("")

        if cv1 < 10 and cv2 < 10:
            md_lines.append("✅ **评价**: 性能非常稳定 (CV < 10%)")
        elif cv1 < 20 and cv2 < 20:
            md_lines.append("⚠️  **评价**: 性能稳定性一般 (CV < 20%)")
        else:
            md_lines.append("❌ **评价**: 性能波动较大 (CV > 20%)")

    def _add_optimization_suggestions(self, md_lines: List[str]):
        """添加优化建议"""
        md_lines.append("## 💡 优化建议")
        md_lines.append("")

        round1_ttfts = [r['ttft'] * 1000 for r in self.round1]
        round2_ttfts = [r['ttft'] * 1000 for r in self.round2]

        # 基于分析给出建议
        if max(round1_ttfts) - min(round1_ttfts) > statistics.mean(round1_ttfts) * 0.5:
            md_lines.append("1. **TTFT 波动较大**")
            md_lines.append("   - 建议检查网络稳定性")
            md_lines.append("   - 检查 GPU 负载是否均匀")
            md_lines.append("")

        if statistics.mean(round2_ttfts) > statistics.mean(round1_ttfts) * 0.5:
            md_lines.append("2. **缓存效果不够理想**")
            md_lines.append("   - 建议检查 LMCache 配置")
            md_lines.append("   - 增加 chunk_size")
            md_lines.append("   - 检查 RDMA 是否正常工作")
            md_lines.append("")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="详细技术分析工具 - 分析 results 文件",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--results', type=str, required=True,
                        help='测试结果文件路径 (results_*.json)')
    parser.add_argument('--output-dir', type=str, default='analysis_charts',
                        help='图表输出目录（默认: analysis_charts）')
    parser.add_argument('--report', type=str,
                        help='技术报告输出文件（默认: technical_analysis_<timestamp>.md）')

    args = parser.parse_args()

    print("="*80)
    print("🔬 详细技术分析工具")
    print("="*80)

    try:
        analyzer = DetailedAnalyzer(args.results)

        # 生成所有图表
        charts = analyzer.generate_all_charts(args.output_dir)

        # 生成技术报告
        report = analyzer.generate_technical_report(args.report)

        print(f"\n{'='*80}")
        print("✅ 分析完成！")
        print(f"{'='*80}")
        print(f"\n📊 图表: {args.output_dir}/ ({len(charts)} 个)")
        print(f"📝 报告: {report}")

    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
