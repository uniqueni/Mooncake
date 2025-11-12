#!/usr/bin/env python3
"""
性能对比脚本

对比 PD 分离模式和非 PD 分离模式的测试结果，生成详细的对比报告。
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("警告: matplotlib 未安装，无法生成图表")


class ResultsComparator:
    """结果对比器"""

    def __init__(self, pd_stats_file: str, non_pd_stats_file: str):
        """初始化对比器"""
        self.pd_stats_file = Path(pd_stats_file)
        self.non_pd_stats_file = Path(non_pd_stats_file)

        # 加载数据
        with open(self.pd_stats_file, 'r', encoding='utf-8') as f:
            self.pd_stats = json.load(f)

        with open(self.non_pd_stats_file, 'r', encoding='utf-8') as f:
            self.non_pd_stats = json.load(f)

        print(f"✓ 加载 PD 分离结果: {len(self.pd_stats)} 轮")
        print(f"✓ 加载非 PD 分离结果: {len(self.non_pd_stats)} 轮")

    def generate_comparison_report(self, output_file: str = None) -> str:
        """生成对比报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"comparison_report_{timestamp}.md"

        output_path = Path(output_file)

        md_lines = []

        # 标题
        md_lines.append("# PD 分离 vs 非 PD 分离 性能对比报告")
        md_lines.append("")
        md_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 执行摘要
        md_lines.append("## 📊 执行摘要")
        md_lines.append("")
        self._add_executive_summary(md_lines)
        md_lines.append("")

        # 详细对比表
        md_lines.append("## 📈 详细性能对比")
        md_lines.append("")
        self._add_detailed_comparison(md_lines)
        md_lines.append("")

        # 缓存效果分析
        md_lines.append("## 🎯 缓存效果分析")
        md_lines.append("")
        self._add_cache_effectiveness_analysis(md_lines)
        md_lines.append("")

        # 结论和建议
        md_lines.append("## 💡 结论和建议")
        md_lines.append("")
        self._add_conclusions(md_lines)
        md_lines.append("")

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        print(f"✓ 对比报告已生成: {output_path}")
        return str(output_path)

    def generate_comparison_charts(self, output_dir: str = "comparison_charts") -> List[str]:
        """生成对比图表"""
        if not HAS_MATPLOTLIB:
            print("跳过图表生成（matplotlib 未安装）")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        chart_files = []

        # 1. TTFT 对比
        chart_file = self._generate_ttft_comparison_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        # 2. 吞吐量对比
        chart_file = self._generate_throughput_comparison_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        # 3. 缓存效果对比
        chart_file = self._generate_cache_effect_comparison_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        return chart_files

    def _add_executive_summary(self, md_lines: List[str]):
        """添加执行摘要"""
        # 获取 Round 2 (Cache Hit) 的数据进行对比
        pd_cache_hit = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cache_hit = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if not pd_cache_hit or not non_pd_cache_hit:
            md_lines.append("⚠️  缺少 Round 2 数据，无法生成完整对比")
            return

        # TTFT 对比
        ttft_diff = ((pd_cache_hit['avg_ttft'] - non_pd_cache_hit['avg_ttft']) / non_pd_cache_hit['avg_ttft']) * 100

        # 吞吐量对比
        throughput_diff = ((pd_cache_hit['request_throughput'] - non_pd_cache_hit['request_throughput']) / non_pd_cache_hit['request_throughput']) * 100

        md_lines.append(f"### 关键发现")
        md_lines.append("")
        md_lines.append(f"- **TTFT 对比** (Cache Hit):")
        md_lines.append(f"  - PD 分离: {pd_cache_hit['avg_ttft']*1000:.2f}ms")
        md_lines.append(f"  - 非 PD 分离: {non_pd_cache_hit['avg_ttft']*1000:.2f}ms")
        if ttft_diff > 0:
            md_lines.append(f"  - PD 分离 **慢 {abs(ttft_diff):.1f}%**")
        else:
            md_lines.append(f"  - PD 分离 **快 {abs(ttft_diff):.1f}%**")
        md_lines.append("")

        md_lines.append(f"- **吞吐量对比** (Cache Hit):")
        md_lines.append(f"  - PD 分离: {pd_cache_hit['request_throughput']:.2f} req/s")
        md_lines.append(f"  - 非 PD 分离: {non_pd_cache_hit['request_throughput']:.2f} req/s")
        if throughput_diff > 0:
            md_lines.append(f"  - PD 分离 **高 {abs(throughput_diff):.1f}%**")
        else:
            md_lines.append(f"  - PD 分离 **低 {abs(throughput_diff):.1f}%**")

    def _add_detailed_comparison(self, md_lines: List[str]):
        """添加详细对比表"""
        md_lines.append("### Cold Start 性能对比")
        md_lines.append("")
        md_lines.append("| 指标 | PD 分离 | 非 PD 分离 | 差异 |")
        md_lines.append("|------|---------|-----------|------|")

        pd_cold = next((s for s in self.pd_stats if s['round_num'] == 1), None)
        non_pd_cold = next((s for s in self.non_pd_stats if s['round_num'] == 1), None)

        if pd_cold and non_pd_cold:
            self._add_comparison_row(md_lines, "TTFT (平均)", pd_cold['avg_ttft']*1000, non_pd_cold['avg_ttft']*1000, "ms")
            self._add_comparison_row(md_lines, "TTFT (P90)", pd_cold['p90_ttft']*1000, non_pd_cold['p90_ttft']*1000, "ms")
            self._add_comparison_row(md_lines, "TPOT (平均)", pd_cold['avg_tpot']*1000, non_pd_cold['avg_tpot']*1000, "ms")
            self._add_comparison_row(md_lines, "端到端延迟", pd_cold['avg_latency'], non_pd_cold['avg_latency'], "s")
            self._add_comparison_row(md_lines, "吞吐量", pd_cold['request_throughput'], non_pd_cold['request_throughput'], "req/s")

        md_lines.append("")
        md_lines.append("### Cache Hit 性能对比")
        md_lines.append("")
        md_lines.append("| 指标 | PD 分离 | 非 PD 分离 | 差异 |")
        md_lines.append("|------|---------|-----------|------|")

        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if pd_cache and non_pd_cache:
            self._add_comparison_row(md_lines, "TTFT (平均)", pd_cache['avg_ttft']*1000, non_pd_cache['avg_ttft']*1000, "ms")
            self._add_comparison_row(md_lines, "TTFT (P90)", pd_cache['p90_ttft']*1000, non_pd_cache['p90_ttft']*1000, "ms")
            self._add_comparison_row(md_lines, "TPOT (平均)", pd_cache['avg_tpot']*1000, non_pd_cache['avg_tpot']*1000, "ms")
            self._add_comparison_row(md_lines, "端到端延迟", pd_cache['avg_latency'], non_pd_cache['avg_latency'], "s")
            self._add_comparison_row(md_lines, "吞吐量", pd_cache['request_throughput'], non_pd_cache['request_throughput'], "req/s")

    def _add_comparison_row(self, md_lines: List[str], metric: str, pd_val: float, non_pd_val: float, unit: str):
        """添加对比行"""
        diff_pct = ((pd_val - non_pd_val) / non_pd_val) * 100 if non_pd_val > 0 else 0

        if diff_pct > 0:
            diff_str = f"+{diff_pct:.1f}%"
            emoji = "📈" if "吞吐量" in metric else "📉"
        else:
            diff_str = f"{diff_pct:.1f}%"
            emoji = "📉" if "吞吐量" in metric else "📈"

        md_lines.append(f"| {metric} | {pd_val:.2f} {unit} | {non_pd_val:.2f} {unit} | {emoji} {diff_str} |")

    def _add_cache_effectiveness_analysis(self, md_lines: List[str]):
        """添加缓存效果分析"""
        # PD 分离缓存效果
        pd_cold = next((s for s in self.pd_stats if s['round_num'] == 1), None)
        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)

        if pd_cold and pd_cache:
            pd_ttft_improvement = (1 - pd_cache['avg_ttft'] / pd_cold['avg_ttft']) * 100
            pd_throughput_improvement = (pd_cache['request_throughput'] / pd_cold['request_throughput'] - 1) * 100

            md_lines.append("### PD 分离模式缓存效果")
            md_lines.append("")
            md_lines.append(f"- **TTFT 降低**: {pd_ttft_improvement:.1f}%")
            md_lines.append(f"- **吞吐量提升**: {pd_throughput_improvement:.1f}%")
            md_lines.append("")

        # 非 PD 分离缓存效果
        non_pd_cold = next((s for s in self.non_pd_stats if s['round_num'] == 1), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if non_pd_cold and non_pd_cache:
            non_pd_ttft_improvement = (1 - non_pd_cache['avg_ttft'] / non_pd_cold['avg_ttft']) * 100
            non_pd_throughput_improvement = (non_pd_cache['request_throughput'] / non_pd_cold['request_throughput'] - 1) * 100

            md_lines.append("### 非 PD 分离模式缓存效果")
            md_lines.append("")
            md_lines.append(f"- **TTFT 降低**: {non_pd_ttft_improvement:.1f}%")
            md_lines.append(f"- **吞吐量提升**: {non_pd_throughput_improvement:.1f}%")
            md_lines.append("")

        # 对比缓存效果
        if pd_cold and pd_cache and non_pd_cold and non_pd_cache:
            md_lines.append("### 缓存效果对比")
            md_lines.append("")
            if pd_ttft_improvement > non_pd_ttft_improvement:
                md_lines.append(f"✅ **PD 分离的缓存效果更好**，TTFT 降低多 {pd_ttft_improvement - non_pd_ttft_improvement:.1f}%")
            else:
                md_lines.append(f"⚠️  **非 PD 分离的缓存效果更好**，TTFT 降低多 {non_pd_ttft_improvement - pd_ttft_improvement:.1f}%")

    def _add_conclusions(self, md_lines: List[str]):
        """添加结论和建议"""
        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if not pd_cache or not non_pd_cache:
            md_lines.append("无法生成结论（缺少数据）")
            return

        ttft_diff = ((pd_cache['avg_ttft'] - non_pd_cache['avg_ttft']) / non_pd_cache['avg_ttft']) * 100
        throughput_diff = ((pd_cache['request_throughput'] - non_pd_cache['request_throughput']) / non_pd_cache['request_throughput']) * 100

        md_lines.append("### 关键结论")
        md_lines.append("")

        # TTFT 结论
        if abs(ttft_diff) < 10:
            md_lines.append("1. **TTFT 性能相近**: PD 分离和非 PD 分离在缓存命中后的 TTFT 相差不大（<10%）")
        elif ttft_diff > 0:
            md_lines.append(f"1. **非 PD 分离 TTFT 更优**: 在缓存命中场景下，非 PD 分离比 PD 分离快 {abs(ttft_diff):.1f}%")
            md_lines.append("   - 原因: 无网络传输开销")
        else:
            md_lines.append(f"1. **PD 分离 TTFT 更优**: 在缓存命中场景下，PD 分离比非 PD 分离快 {abs(ttft_diff):.1f}%")
            md_lines.append("   - 原因: 可能的优化或更好的缓存策略")

        # 吞吐量结论
        if throughput_diff > 50:
            md_lines.append(f"2. **PD 分离吞吐量显著提升**: 比非 PD 分离高 {throughput_diff:.1f}%")
            md_lines.append("   - 推荐用于高并发场景")
        elif throughput_diff > 0:
            md_lines.append(f"2. **PD 分离吞吐量略高**: 比非 PD 分离高 {throughput_diff:.1f}%")
        else:
            md_lines.append(f"2. **非 PD 分离吞吐量更高**: 比 PD 分离高 {abs(throughput_diff):.1f}%")

        md_lines.append("")
        md_lines.append("### 部署建议")
        md_lines.append("")

        if throughput_diff > 50 and abs(ttft_diff) < 20:
            md_lines.append("**推荐使用 PD 分离模式**")
            md_lines.append("- ✅ 显著提升系统吞吐量")
            md_lines.append("- ✅ TTFT 性能可接受")
            md_lines.append("- ✅ 更好的资源利用率")
            md_lines.append("- 适合场景: 高并发、长上下文、生产环境")
        elif ttft_diff > 30:
            md_lines.append("**推荐使用非 PD 分离模式**")
            md_lines.append("- ✅ 更低的延迟")
            md_lines.append("- ✅ 部署更简单")
            md_lines.append("- ⚠️  吞吐量较低")
            md_lines.append("- 适合场景: 低延迟要求、小规模部署")
        else:
            md_lines.append("**两种模式各有优势**")
            md_lines.append("- PD 分离: 更高吞吐量，适合大规模部署")
            md_lines.append("- 非 PD 分离: 更简单，适合快速原型")
            md_lines.append("- 根据具体需求选择")

    def _generate_ttft_comparison_chart(self, output_path: Path) -> str:
        """生成 TTFT 对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        pd_cold = next((s for s in self.pd_stats if s['round_num'] == 1), None)
        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cold = next((s for s in self.non_pd_stats if s['round_num'] == 1), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if not all([pd_cold, pd_cache, non_pd_cold, non_pd_cache]):
            return None

        categories = ['Cold Start', 'Cache Hit']
        pd_ttfts = [pd_cold['avg_ttft']*1000, pd_cache['avg_ttft']*1000]
        non_pd_ttfts = [non_pd_cold['avg_ttft']*1000, non_pd_cache['avg_ttft']*1000]

        x = np.arange(len(categories))
        width = 0.35

        bars1 = ax.bar(x - width/2, pd_ttfts, width, label='PD 分离', color='#3498db')
        bars2 = ax.bar(x + width/2, non_pd_ttfts, width, label='非 PD 分离', color='#2ecc71')

        ax.set_xlabel('场景')
        ax.set_ylabel('TTFT (ms)')
        ax.set_title('TTFT 性能对比')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.0f}',
                        ha='center', va='bottom', fontsize=9)

        chart_file = output_path / "ttft_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_throughput_comparison_chart(self, output_path: Path) -> str:
        """生成吞吐量对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        pd_cold = next((s for s in self.pd_stats if s['round_num'] == 1), None)
        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cold = next((s for s in self.non_pd_stats if s['round_num'] == 1), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if not all([pd_cold, pd_cache, non_pd_cold, non_pd_cache]):
            return None

        categories = ['Cold Start', 'Cache Hit']
        pd_throughputs = [pd_cold['request_throughput'], pd_cache['request_throughput']]
        non_pd_throughputs = [non_pd_cold['request_throughput'], non_pd_cache['request_throughput']]

        x = np.arange(len(categories))
        width = 0.35

        bars1 = ax.bar(x - width/2, pd_throughputs, width, label='PD 分离', color='#e74c3c')
        bars2 = ax.bar(x + width/2, non_pd_throughputs, width, label='非 PD 分离', color='#f39c12')

        ax.set_xlabel('场景')
        ax.set_ylabel('吞吐量 (req/s)')
        ax.set_title('吞吐量性能对比')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=9)

        chart_file = output_path / "throughput_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_cache_effect_comparison_chart(self, output_path: Path) -> str:
        """生成缓存效果对比图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        pd_cold = next((s for s in self.pd_stats if s['round_num'] == 1), None)
        pd_cache = next((s for s in self.pd_stats if s['round_num'] == 2), None)
        non_pd_cold = next((s for s in self.non_pd_stats if s['round_num'] == 1), None)
        non_pd_cache = next((s for s in self.non_pd_stats if s['round_num'] == 2), None)

        if not all([pd_cold, pd_cache, non_pd_cold, non_pd_cache]):
            return None

        # TTFT 降低
        pd_ttft_reduction = (1 - pd_cache['avg_ttft'] / pd_cold['avg_ttft']) * 100
        non_pd_ttft_reduction = (1 - non_pd_cache['avg_ttft'] / non_pd_cold['avg_ttft']) * 100

        modes = ['PD 分离', '非 PD 分离']
        ttft_reductions = [pd_ttft_reduction, non_pd_ttft_reduction]

        bars1 = ax1.barh(modes, ttft_reductions, color=['#2ecc71', '#3498db'])
        ax1.set_xlabel('TTFT 降低 (%)')
        ax1.set_title('缓存命中后 TTFT 降低')
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.axvline(x=60, color='green', linestyle='--', alpha=0.5, label='目标: 60%')
        ax1.legend()

        for bar in bars1:
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2.,
                    f'{width:.1f}%',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        # 吞吐量提升
        pd_throughput_increase = (pd_cache['request_throughput'] / pd_cold['request_throughput'] - 1) * 100
        non_pd_throughput_increase = (non_pd_cache['request_throughput'] / non_pd_cold['request_throughput'] - 1) * 100

        throughput_increases = [pd_throughput_increase, non_pd_throughput_increase]

        bars2 = ax2.barh(modes, throughput_increases, color=['#e74c3c', '#f39c12'])
        ax2.set_xlabel('吞吐量提升 (%)')
        ax2.set_title('缓存命中后吞吐量提升')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.axvline(x=150, color='green', linestyle='--', alpha=0.5, label='目标: 150%')
        ax2.legend()

        for bar in bars2:
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height()/2.,
                    f'{width:.1f}%',
                    ha='left', va='center', fontsize=10, fontweight='bold')

        chart_file = output_path / "cache_effect_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="对比 PD 分离和非 PD 分离测试结果")
    parser.add_argument('--pd-stats', type=str, required=True, help='PD 分离统计文件')
    parser.add_argument('--non-pd-stats', type=str, required=True, help='非 PD 分离统计文件')
    parser.add_argument('--output', type=str, default='comparison_report.md', help='输出报告文件')
    parser.add_argument('--generate-charts', action='store_true', help='生成对比图表')
    parser.add_argument('--chart-dir', type=str, default='comparison_charts', help='图表输出目录')

    args = parser.parse_args()

    print("="*80)
    print("📊 PD 分离 vs 非 PD 分离 性能对比")
    print("="*80)

    try:
        comparator = ResultsComparator(args.pd_stats, args.non_pd_stats)

        # 生成报告
        report_file = comparator.generate_comparison_report(args.output)
        print(f"\n✓ 对比报告: {report_file}")

        # 生成图表
        if args.generate_charts:
            chart_files = comparator.generate_comparison_charts(args.chart_dir)
            if chart_files:
                print(f"\n✓ 生成了 {len(chart_files)} 个对比图表:")
                for chart in chart_files:
                    print(f"  - {chart}")

        print("\n✅ 对比分析完成!")

    except Exception as e:
        print(f"\n❌ 对比失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
