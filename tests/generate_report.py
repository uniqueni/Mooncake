#!/usr/bin/env python3
"""
测试报告生成工具

从测试结果 JSON 文件生成详细的 HTML 和 Markdown 格式报告。
包含性能对比图表、统计数据和分析建议。
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys

try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("警告: matplotlib 未安装，无法生成图表")
    print("运行: pip install matplotlib")


class ReportGenerator:
    """报告生成器"""

    def __init__(self, stats_file: str, results_file: str = None):
        """初始化报告生成器"""
        self.stats_file = Path(stats_file)
        self.results_file = Path(results_file) if results_file else None

        # 加载统计数据
        with open(self.stats_file, 'r', encoding='utf-8') as f:
            self.stats = json.load(f)

        # 加载详细结果（可选）
        self.results = None
        if self.results_file and self.results_file.exists():
            with open(self.results_file, 'r', encoding='utf-8') as f:
                self.results = json.load(f)

        # 按场景分组统计
        self.grouped_stats = self._group_stats_by_scenario()

    def _group_stats_by_scenario(self) -> Dict[str, List[Dict]]:
        """按场景分组统计数据"""
        grouped = {}
        for stat in self.stats:
            scenario = stat['scenario']
            if scenario not in grouped:
                grouped[scenario] = []
            grouped[scenario].append(stat)
        return grouped

    def generate_markdown_report(self, output_file: str = None) -> str:
        """生成 Markdown 格式报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"report_{timestamp}.md"

        output_path = Path(output_file)

        md_lines = []

        # 标题
        md_lines.append("# vLLM + LMCache + Mooncake 缓存效果测试报告")
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

        # 各场景详细结果
        md_lines.append("## 📈 场景详细分析")
        md_lines.append("")

        for scenario, stats_list in self.grouped_stats.items():
            md_lines.append(f"### {self._get_scenario_name(scenario)}")
            md_lines.append("")
            self._add_scenario_analysis(md_lines, scenario, stats_list)
            md_lines.append("")

        # 性能对比表
        md_lines.append("## 📉 性能对比总览")
        md_lines.append("")
        self._add_performance_comparison_table(md_lines)
        md_lines.append("")

        # 关键发现
        md_lines.append("## 🔍 关键发现")
        md_lines.append("")
        self._add_key_findings(md_lines)
        md_lines.append("")

        # 建议
        md_lines.append("## 💡 优化建议")
        md_lines.append("")
        self._add_recommendations(md_lines)
        md_lines.append("")

        # 附录
        md_lines.append("## 📎 附录")
        md_lines.append("")
        md_lines.append("### 测试配置")
        md_lines.append("")
        md_lines.append("- **统计文件**: `{}`".format(self.stats_file.name))
        if self.results_file:
            md_lines.append("- **详细结果**: `{}`".format(self.results_file.name))
        md_lines.append("")

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        print(f"✓ Markdown 报告已生成: {output_path}")
        return str(output_path)

    def generate_html_report(self, output_file: str = None) -> str:
        """生成 HTML 格式报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"report_{timestamp}.html"

        output_path = Path(output_file)

        html_lines = []

        # HTML 头部
        html_lines.append("<!DOCTYPE html>")
        html_lines.append("<html lang='zh-CN'>")
        html_lines.append("<head>")
        html_lines.append("    <meta charset='UTF-8'>")
        html_lines.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html_lines.append("    <title>vLLM + LMCache + Mooncake 测试报告</title>")
        html_lines.append(self._get_html_styles())
        html_lines.append("</head>")
        html_lines.append("<body>")

        # 页面内容
        html_lines.append("    <div class='container'>")
        html_lines.append("        <h1>🚀 vLLM + LMCache + Mooncake 缓存效果测试报告</h1>")
        html_lines.append(f"        <p class='timestamp'>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        # 执行摘要
        html_lines.append("        <div class='section'>")
        html_lines.append("            <h2>📊 执行摘要</h2>")
        self._add_executive_summary_html(html_lines)
        html_lines.append("        </div>")

        # 场景分析
        html_lines.append("        <div class='section'>")
        html_lines.append("            <h2>📈 场景详细分析</h2>")

        for scenario, stats_list in self.grouped_stats.items():
            html_lines.append("            <div class='scenario'>")
            html_lines.append(f"                <h3>{self._get_scenario_name(scenario)}</h3>")
            self._add_scenario_analysis_html(html_lines, scenario, stats_list)
            html_lines.append("            </div>")

        html_lines.append("        </div>")

        # 性能对比
        html_lines.append("        <div class='section'>")
        html_lines.append("            <h2>📉 性能对比总览</h2>")
        self._add_performance_comparison_html(html_lines)
        html_lines.append("        </div>")

        # 关键发现
        html_lines.append("        <div class='section'>")
        html_lines.append("            <h2>🔍 关键发现</h2>")
        self._add_key_findings_html(html_lines)
        html_lines.append("        </div>")

        # 优化建议
        html_lines.append("        <div class='section'>")
        html_lines.append("            <h2>💡 优化建议</h2>")
        self._add_recommendations_html(html_lines)
        html_lines.append("        </div>")

        html_lines.append("    </div>")
        html_lines.append("</body>")
        html_lines.append("</html>")

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_lines))

        print(f"✓ HTML 报告已生成: {output_path}")
        return str(output_path)

    def generate_charts(self, output_dir: str = "charts") -> List[str]:
        """生成性能对比图表"""
        if not HAS_MATPLOTLIB:
            print("跳过图表生成（matplotlib 未安装）")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        chart_files = []

        # 为每个场景生成图表
        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue  # 需要至少2轮数据才能对比

            # 1. 延迟对比图
            chart_file = self._generate_latency_chart(scenario, stats_list, output_path)
            if chart_file:
                chart_files.append(chart_file)

            # 2. 吞吐量对比图
            chart_file = self._generate_throughput_chart(scenario, stats_list, output_path)
            if chart_file:
                chart_files.append(chart_file)

        # 3. 所有场景的改善对比
        chart_file = self._generate_improvement_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        return chart_files

    def _generate_latency_chart(self, scenario: str, stats_list: List[Dict], output_path: Path) -> str:
        """生成延迟对比图"""
        rounds = [f"Round {s['round_num']}" for s in stats_list]
        avg_latencies = [s['avg_latency'] * 1000 for s in stats_list]  # 转换为毫秒
        median_latencies = [s['median_latency'] * 1000 for s in stats_list]
        p90_latencies = [s['p90_latency'] * 1000 for s in stats_list]

        fig, ax = plt.subplots(figsize=(10, 6))

        x = range(len(rounds))
        width = 0.25

        ax.bar([i - width for i in x], avg_latencies, width, label='平均延迟', color='#3498db')
        ax.bar(x, median_latencies, width, label='中位数延迟', color='#2ecc71')
        ax.bar([i + width for i in x], p90_latencies, width, label='P90 延迟', color='#e74c3c')

        ax.set_xlabel('测试轮次')
        ax.set_ylabel('延迟 (ms)')
        ax.set_title(f'{self._get_scenario_name(scenario)} - 延迟对比')
        ax.set_xticks(x)
        ax.set_xticklabels(rounds)
        ax.legend()
        ax.grid(True, alpha=0.3)

        chart_file = output_path / f"{scenario}_latency.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_throughput_chart(self, scenario: str, stats_list: List[Dict], output_path: Path) -> str:
        """生成吞吐量对比图"""
        rounds = [f"Round {s['round_num']}" for s in stats_list]
        throughputs = [s['throughput'] for s in stats_list]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ['#e74c3c' if i == 0 else '#2ecc71' for i in range(len(rounds))]
        bars = ax.bar(rounds, throughputs, color=colors)

        ax.set_xlabel('测试轮次')
        ax.set_ylabel('吞吐量 (req/s)')
        ax.set_title(f'{self._get_scenario_name(scenario)} - 吞吐量对比')
        ax.grid(True, alpha=0.3, axis='y')

        # 在柱子上添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom')

        # 添加改善百分比（如果有多轮）
        if len(throughputs) > 1:
            improvement = (throughputs[1] / throughputs[0] - 1) * 100
            ax.text(0.5, 0.95, f'改善: +{improvement:.1f}%',
                    transform=ax.transAxes,
                    fontsize=12, fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                    verticalalignment='top', horizontalalignment='center')

        chart_file = output_path / f"{scenario}_throughput.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_improvement_chart(self, output_path: Path) -> str:
        """生成所有场景的改善对比图"""
        scenarios = []
        latency_improvements = []
        throughput_improvements = []

        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue

            baseline = stats_list[0]
            cached = stats_list[1]

            scenarios.append(self._get_scenario_name(scenario))

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            latency_improvements.append(lat_imp)

            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100
            throughput_improvements.append(thr_imp)

        if not scenarios:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # 延迟降低
        colors1 = ['#2ecc71' if x > 50 else '#f39c12' if x > 20 else '#e74c3c'
                   for x in latency_improvements]
        ax1.barh(scenarios, latency_improvements, color=colors1)
        ax1.set_xlabel('延迟降低 (%)')
        ax1.set_title('缓存命中后的延迟改善')
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.axvline(x=60, color='green', linestyle='--', alpha=0.5, label='目标: 60%')
        ax1.legend()

        # 吞吐量提升
        colors2 = ['#2ecc71' if x > 180 else '#f39c12' if x > 50 else '#e74c3c'
                   for x in throughput_improvements]
        ax2.barh(scenarios, throughput_improvements, color=colors2)
        ax2.set_xlabel('吞吐量提升 (%)')
        ax2.set_title('缓存命中后的吞吐量改善')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.axvline(x=180, color='green', linestyle='--', alpha=0.5, label='目标: 180%')
        ax2.legend()

        chart_file = output_path / "overall_improvement.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _add_executive_summary(self, md_lines: List[str]):
        """添加执行摘要（Markdown）"""
        total_scenarios = len(self.grouped_stats)
        total_rounds = sum(len(stats) for stats in self.grouped_stats.values())

        md_lines.append(f"- **测试场景数**: {total_scenarios}")
        md_lines.append(f"- **总测试轮数**: {total_rounds}")
        md_lines.append("")

        # 计算平均改善
        improvements = []
        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) >= 2:
                baseline = stats_list[0]
                cached = stats_list[1]
                lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
                thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100
                improvements.append((lat_imp, thr_imp))

        if improvements:
            avg_lat_imp = sum(x[0] for x in improvements) / len(improvements)
            avg_thr_imp = sum(x[1] for x in improvements) / len(improvements)

            md_lines.append("### 🎯 平均性能改善")
            md_lines.append("")
            md_lines.append(f"- **延迟降低**: {avg_lat_imp:.1f}%")
            md_lines.append(f"- **吞吐量提升**: {avg_thr_imp:.1f}%")

    def _add_executive_summary_html(self, html_lines: List[str]):
        """添加执行摘要（HTML）"""
        total_scenarios = len(self.grouped_stats)
        total_rounds = sum(len(stats) for stats in self.grouped_stats.values())

        html_lines.append("            <div class='summary-grid'>")
        html_lines.append(f"                <div class='summary-item'>")
        html_lines.append(f"                    <div class='summary-value'>{total_scenarios}</div>")
        html_lines.append(f"                    <div class='summary-label'>测试场景数</div>")
        html_lines.append(f"                </div>")
        html_lines.append(f"                <div class='summary-item'>")
        html_lines.append(f"                    <div class='summary-value'>{total_rounds}</div>")
        html_lines.append(f"                    <div class='summary-label'>总测试轮数</div>")
        html_lines.append(f"                </div>")
        html_lines.append("            </div>")

    def _add_scenario_analysis(self, md_lines: List[str], scenario: str, stats_list: List[Dict]):
        """添加场景分析（Markdown）"""
        md_lines.append("| 指标 | " + " | ".join([f"Round {s['round_num']}" for s in stats_list]) + " |")
        md_lines.append("|------|" + "|".join(["------" for _ in stats_list]) + "|")

        metrics = [
            ("总请求数", "total_requests", ""),
            ("成功请求", "success_requests", ""),
            ("平均延迟", "avg_latency", "ms", 1000),
            ("中位数延迟", "median_latency", "ms", 1000),
            ("P90 延迟", "p90_latency", "ms", 1000),
            ("P99 延迟", "p99_latency", "ms", 1000),
            ("吞吐量", "throughput", "req/s", 1),
        ]

        for label, key, unit, *scale in metrics:
            multiplier = scale[0] if scale else 1
            values = [f"{s[key] * multiplier:.2f}{unit}" if unit else f"{s[key]}" for s in stats_list]
            md_lines.append(f"| {label} | " + " | ".join(values) + " |")

        # 如果有多轮，计算改善
        if len(stats_list) >= 2:
            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100

            md_lines.append("")
            md_lines.append(f"**缓存效果**: 延迟降低 {lat_imp:.1f}%, 吞吐量提升 {thr_imp:.1f}%")

    def _add_scenario_analysis_html(self, html_lines: List[str], scenario: str, stats_list: List[Dict]):
        """添加场景分析（HTML）"""
        html_lines.append("                <table>")
        html_lines.append("                    <thead>")
        html_lines.append("                        <tr>")
        html_lines.append("                            <th>指标</th>")
        for s in stats_list:
            html_lines.append(f"                            <th>Round {s['round_num']}</th>")
        html_lines.append("                        </tr>")
        html_lines.append("                    </thead>")
        html_lines.append("                    <tbody>")

        metrics = [
            ("平均延迟", "avg_latency", "ms", 1000),
            ("中位数延迟", "median_latency", "ms", 1000),
            ("P90 延迟", "p90_latency", "ms", 1000),
            ("吞吐量", "throughput", "req/s", 1),
        ]

        for label, key, unit, multiplier in metrics:
            html_lines.append("                        <tr>")
            html_lines.append(f"                            <td>{label}</td>")
            for s in stats_list:
                value = s[key] * multiplier
                html_lines.append(f"                            <td>{value:.2f} {unit}</td>")
            html_lines.append("                        </tr>")

        html_lines.append("                    </tbody>")
        html_lines.append("                </table>")

        # 改善信息
        if len(stats_list) >= 2:
            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100

            status_class = 'success' if lat_imp > 50 else 'warning' if lat_imp > 20 else 'error'

            html_lines.append(f"                <div class='improvement-badge {status_class}'>")
            html_lines.append(f"                    缓存效果: 延迟降低 {lat_imp:.1f}%, 吞吐量提升 {thr_imp:.1f}%")
            html_lines.append("                </div>")

    def _add_performance_comparison_table(self, md_lines: List[str]):
        """添加性能对比表（Markdown）"""
        md_lines.append("| 场景 | Cold Start 延迟 | Cache Hit 延迟 | 延迟降低 | Cold Start 吞吐量 | Cache Hit 吞吐量 | 吞吐量提升 |")
        md_lines.append("|------|-----------------|----------------|----------|-------------------|------------------|-----------|")

        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue

            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100

            md_lines.append(
                f"| {self._get_scenario_name(scenario)} | "
                f"{baseline['avg_latency']*1000:.2f}ms | "
                f"{cached['avg_latency']*1000:.2f}ms | "
                f"**{lat_imp:.1f}%** | "
                f"{baseline['throughput']:.2f} req/s | "
                f"{cached['throughput']:.2f} req/s | "
                f"**+{thr_imp:.1f}%** |"
            )

    def _add_performance_comparison_html(self, html_lines: List[str]):
        """添加性能对比表（HTML）"""
        html_lines.append("            <table>")
        html_lines.append("                <thead>")
        html_lines.append("                    <tr>")
        html_lines.append("                        <th>场景</th>")
        html_lines.append("                        <th>Cold Start 延迟</th>")
        html_lines.append("                        <th>Cache Hit 延迟</th>")
        html_lines.append("                        <th>延迟降低</th>")
        html_lines.append("                        <th>吞吐量提升</th>")
        html_lines.append("                    </tr>")
        html_lines.append("                </thead>")
        html_lines.append("                <tbody>")

        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue

            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100

            html_lines.append("                    <tr>")
            html_lines.append(f"                        <td>{self._get_scenario_name(scenario)}</td>")
            html_lines.append(f"                        <td>{baseline['avg_latency']*1000:.2f}ms</td>")
            html_lines.append(f"                        <td>{cached['avg_latency']*1000:.2f}ms</td>")
            html_lines.append(f"                        <td class='improvement'>{lat_imp:.1f}%</td>")
            html_lines.append(f"                        <td class='improvement'>+{thr_imp:.1f}%</td>")
            html_lines.append("                    </tr>")

        html_lines.append("                </tbody>")
        html_lines.append("            </table>")

    def _add_key_findings(self, md_lines: List[str]):
        """添加关键发现（Markdown）"""
        findings = []

        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue

            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100
            thr_imp = (cached['throughput'] / baseline['throughput'] - 1) * 100

            if lat_imp > 60:
                findings.append(f"- ✅ **{self._get_scenario_name(scenario)}** 场景下缓存效果**优秀**，延迟降低 {lat_imp:.1f}%")
            elif lat_imp > 30:
                findings.append(f"- ⚠️  **{self._get_scenario_name(scenario)}** 场景下缓存效果**一般**，延迟降低 {lat_imp:.1f}%")
            else:
                findings.append(f"- ❌ **{self._get_scenario_name(scenario)}** 场景下缓存效果**不明显**，延迟仅降低 {lat_imp:.1f}%")

        md_lines.extend(findings)

    def _add_key_findings_html(self, html_lines: List[str]):
        """添加关键发现（HTML）"""
        html_lines.append("            <ul class='findings'>")

        for scenario, stats_list in self.grouped_stats.items():
            if len(stats_list) < 2:
                continue

            baseline = stats_list[0]
            cached = stats_list[1]

            lat_imp = (1 - cached['avg_latency'] / baseline['avg_latency']) * 100

            if lat_imp > 60:
                html_lines.append(f"                <li class='success'>✅ <strong>{self._get_scenario_name(scenario)}</strong> 场景下缓存效果<strong>优秀</strong>，延迟降低 {lat_imp:.1f}%</li>")
            elif lat_imp > 30:
                html_lines.append(f"                <li class='warning'>⚠️  <strong>{self._get_scenario_name(scenario)}</strong> 场景下缓存效果<strong>一般</strong>，延迟降低 {lat_imp:.1f}%</li>")
            else:
                html_lines.append(f"                <li class='error'>❌ <strong>{self._get_scenario_name(scenario)}</strong> 场景下缓存效果<strong>不明显</strong>，延迟仅降低 {lat_imp:.1f}%</li>")

        html_lines.append("            </ul>")

    def _add_recommendations(self, md_lines: List[str]):
        """添加优化建议（Markdown）"""
        recommendations = [
            "1. **增加缓存重用率**：通过优化提示词模板，提高不同请求之间的前缀重用率",
            "2. **调整 chunk_size**：实验不同的 LMCache chunk_size 值，找到最优配置",
            "3. **优化网络配置**：确保 RDMA 网络配置正确，充分利用高速网络",
            "4. **监控缓存命中率**：通过 Grafana 持续监控 Mooncake Store 的缓存命中率",
            "5. **调整副本数量**：根据访问热度调整 KV Cache 的副本数量",
        ]
        md_lines.extend(recommendations)

    def _add_recommendations_html(self, html_lines: List[str]):
        """添加优化建议（HTML）"""
        recommendations = [
            ("<strong>增加缓存重用率</strong>", "通过优化提示词模板，提高不同请求之间的前缀重用率"),
            ("<strong>调整 chunk_size</strong>", "实验不同的 LMCache chunk_size 值，找到最优配置"),
            ("<strong>优化网络配置</strong>", "确保 RDMA 网络配置正确，充分利用高速网络"),
            ("<strong>监控缓存命中率</strong>", "通过 Grafana 持续监控 Mooncake Store 的缓存命中率"),
            ("<strong>调整副本数量</strong>", "根据访问热度调整 KV Cache 的副本数量"),
        ]

        html_lines.append("            <ol class='recommendations'>")
        for title, desc in recommendations:
            html_lines.append(f"                <li>{title}: {desc}</li>")
        html_lines.append("            </ol>")

    def _get_scenario_name(self, scenario: str) -> str:
        """获取场景的友好名称"""
        names = {
            'high_reuse': '高重用率场景',
            'medium_reuse': '中等重用率场景',
            'low_reuse': '低重用率场景',
            'long_context': '长上下文场景',
        }
        return names.get(scenario, scenario)

    def _get_html_styles(self) -> str:
        """获取 HTML 样式"""
        return """    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #7f8c8d;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .timestamp {
            color: #7f8c8d;
            margin-bottom: 30px;
        }
        .section {
            margin-bottom: 40px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .summary-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .summary-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #3498db;
            color: white;
            font-weight: 600;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .improvement {
            color: #27ae60;
            font-weight: bold;
        }
        .improvement-badge {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
        }
        .improvement-badge.success {
            background: #d4edda;
            color: #155724;
        }
        .improvement-badge.warning {
            background: #fff3cd;
            color: #856404;
        }
        .improvement-badge.error {
            background: #f8d7da;
            color: #721c24;
        }
        .findings, .recommendations {
            list-style-position: inside;
            margin: 20px 0;
        }
        .findings li, .recommendations li {
            margin: 10px 0;
            padding: 10px;
            border-left: 3px solid #3498db;
            background: #f8f9fa;
        }
        .findings li.success {
            border-left-color: #27ae60;
        }
        .findings li.warning {
            border-left-color: #f39c12;
        }
        .findings li.error {
            border-left-color: #e74c3c;
        }
        .scenario {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>"""


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成测试报告")
    parser.add_argument(
        '--stats',
        type=str,
        required=True,
        help='统计数据 JSON 文件路径'
    )
    parser.add_argument(
        '--results',
        type=str,
        help='详细结果 JSON 文件路径（可选）'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='reports',
        help='报告输出目录'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['markdown', 'html', 'both'],
        default='both',
        help='报告格式'
    )
    parser.add_argument(
        '--generate-charts',
        action='store_true',
        help='生成性能对比图表'
    )

    args = parser.parse_args()

    # 创建输出目录
    output_path = Path(args.output_dir)
    output_path.mkdir(exist_ok=True)

    print("="*80)
    print("📊 生成测试报告")
    print("="*80)

    try:
        generator = ReportGenerator(args.stats, args.results)

        # 生成报告
        if args.format in ['markdown', 'both']:
            md_file = output_path / "report.md"
            generator.generate_markdown_report(str(md_file))

        if args.format in ['html', 'both']:
            html_file = output_path / "report.html"
            generator.generate_html_report(str(html_file))

        # 生成图表
        if args.generate_charts:
            charts_dir = output_path / "charts"
            chart_files = generator.generate_charts(str(charts_dir))
            if chart_files:
                print(f"\n✓ 生成了 {len(chart_files)} 个图表")
                for chart in chart_files:
                    print(f"  - {chart}")

        print("\n✅ 报告生成完成!")
        print(f"\n📁 输出目录: {output_path.absolute()}")

    except Exception as e:
        print(f"\n❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
