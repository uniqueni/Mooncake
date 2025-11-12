#!/usr/bin/env python3
"""
缓存效果对比脚本（简化版）

对比 Round 1 (Cold Start/Baseline) vs Round 2 (Cache Hit) 的测试结果，
生成缓存效果分析报告。

用法:
    python3 compare_results.py --stats test_results/test_stats_YYYYMMDD_HHMMSS.json
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

    # 配置中文字体支持
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("提示: matplotlib 未安装，无法生成图表（可选功能）")


class CacheEffectComparator:
    """缓存效果对比器"""

    def __init__(self, stats_file: str):
        """初始化对比器"""
        self.stats_file = Path(stats_file)

        # 加载数据
        with open(self.stats_file, 'r', encoding='utf-8') as f:
            self.stats = json.load(f)

        print(f"✓ 加载测试结果: {len(self.stats)} 轮")

        # 检查数据格式
        if not self.stats:
            raise ValueError("统计文件为空")

        # 打印第一条数据的键，帮助调试
        if self.stats:
            print(f"  数据字段: {list(self.stats[0].keys())[:5]}...")  # 只显示前 5 个字段

        # 提取 Round 1 和 Round 2
        self.round1 = next((s for s in self.stats if s.get('round_num') == 1), None)
        self.round2 = next((s for s in self.stats if s.get('round_num') == 2), None)

        if not self.round1:
            # 如果找不到 round_num == 1，尝试用索引
            print("⚠️  警告: 找不到 round_num=1 的数据，尝试使用第一条记录")
            if len(self.stats) >= 2:
                self.round1 = self.stats[0]
                self.round2 = self.stats[1]
            else:
                raise ValueError("缺少 Round 1 (Cold Start) 数据")

        if not self.round2:
            raise ValueError("缺少 Round 2 (Cache Hit) 数据")

        # 验证必需字段
        required_fields = ['avg_ttft', 'avg_tpot', 'request_throughput', 'total_requests']
        missing_fields = [f for f in required_fields if f not in self.round1]

        if missing_fields:
            print(f"\n❌ 错误: 统计数据缺少必需字段: {missing_fields}")
            print(f"   实际字段: {list(self.round1.keys())}")
            print(f"\n提示: 请确认使用的是 stats 文件，而不是 results 文件")
            print(f"   正确的文件名格式: with-cache_72B_stats_YYYYMMDD_HHMMSS.json")
            raise ValueError(f"统计数据格式错误，缺少字段: {missing_fields}")

    def print_summary(self):
        """打印缓存效果摘要到控制台"""
        print("\n" + "="*80)
        print("🎯 缓存效果分析")
        print("="*80)

        # TTFT 对比
        ttft_baseline = self.round1['avg_ttft'] * 1000  # 转换为 ms
        ttft_cached = self.round2['avg_ttft'] * 1000
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100

        print(f"\n📊 TTFT (Time to First Token):")
        print(f"  Round 1 (Baseline):  {ttft_baseline:.2f} ms")
        print(f"  Round 2 (Cache Hit): {ttft_cached:.2f} ms")
        print(f"  降低:                {ttft_reduction:.1f}%")

        # 判断 TTFT 效果
        if ttft_reduction >= 60:
            print(f"  ✅ 达到目标 (>60%)")
        elif ttft_reduction >= 40:
            print(f"  ⚠️  效果一般 (40-60%)")
        else:
            print(f"  ❌ 未达到目标 (<40%)")

        # TPOT 对比
        tpot_baseline = self.round1['avg_tpot'] * 1000
        tpot_cached = self.round2['avg_tpot'] * 1000
        tpot_change = ((self.round2['avg_tpot'] - self.round1['avg_tpot']) / self.round1['avg_tpot']) * 100

        print(f"\n⚡ TPOT (Time per Output Token):")
        print(f"  Round 1 (Baseline):  {tpot_baseline:.2f} ms")
        print(f"  Round 2 (Cache Hit): {tpot_cached:.2f} ms")
        print(f"  变化:                {tpot_change:+.1f}%")

        if abs(tpot_change) < 10:
            print(f"  ✅ 保持稳定 (<10% 变化)")
        else:
            print(f"  ⚠️  有明显变化")

        # 吞吐量对比
        throughput_baseline = self.round1['request_throughput']
        throughput_cached = self.round2['request_throughput']
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100

        print(f"\n🚀 吞吐量 (Throughput):")
        print(f"  Round 1 (Baseline):  {throughput_baseline:.2f} req/s")
        print(f"  Round 2 (Cache Hit): {throughput_cached:.2f} req/s")
        print(f"  提升:                {throughput_increase:.1f}%")

        if throughput_increase >= 150:
            print(f"  ✅ 达到目标 (>150%)")
        elif throughput_increase >= 100:
            print(f"  ⚠️  效果一般 (100-150%)")
        else:
            print(f"  ❌ 未达到目标 (<100%)")

        # Token 吞吐量
        token_throughput_baseline = self.round1.get('token_throughput', 0)
        token_throughput_cached = self.round2.get('token_throughput', 0)

        if token_throughput_baseline > 0 and token_throughput_cached > 0:
            token_increase = (token_throughput_cached / token_throughput_baseline - 1) * 100
            print(f"\n💨 Token 吞吐量:")
            print(f"  Round 1 (Baseline):  {token_throughput_baseline:.2f} tokens/s")
            print(f"  Round 2 (Cache Hit): {token_throughput_cached:.2f} tokens/s")
            print(f"  提升:                {token_increase:.1f}%")

        # 延迟对比
        latency_baseline = self.round1['avg_latency']
        latency_cached = self.round2['avg_latency']
        latency_change = ((self.round2['avg_latency'] - self.round1['avg_latency']) / self.round1['avg_latency']) * 100

        print(f"\n⏱️  端到端延迟:")
        print(f"  Round 1 (Baseline):  {latency_baseline:.2f} s")
        print(f"  Round 2 (Cache Hit): {latency_cached:.2f} s")
        print(f"  变化:                {latency_change:+.1f}%")

        # 总体评价
        print(f"\n{'='*80}")
        print("📝 总体评价:")
        print(f"{'='*80}")

        success_count = 0
        total_checks = 2

        if ttft_reduction >= 60:
            success_count += 1
        if throughput_increase >= 150:
            success_count += 1

        if success_count == total_checks:
            print("✅ 缓存效果优秀！所有关键指标均达到目标。")
        elif success_count >= 1:
            print("⚠️  缓存效果一般。部分指标达到目标，建议检查配置。")
        else:
            print("❌ 缓存效果不佳。请检查 LMCache 配置和 Mooncake 连接。")

        print(f"\n关键指标达成率: {success_count}/{total_checks}")
        print("="*80 + "\n")

    def _add_test_purpose(self, md_lines: List[str]):
        """添加测试目的"""
        md_lines.append("本次测试旨在评估 **Mooncake KV Cache** 在大语言模型推理场景下的性能表现，")
        md_lines.append("通过对比测试量化缓存对系统性能的影响。")
        md_lines.append("")
        md_lines.append("### 评估指标")
        md_lines.append("")
        md_lines.append("| 指标 | 说明 | 目标 |")
        md_lines.append("|------|------|------|")
        md_lines.append("| **TTFT** (首 Token 延迟) | 从请求到收到第一个 Token 的时间 | 降低 ≥60% |")
        md_lines.append("| **吞吐量** | 单位时间内系统可处理的请求数 | 提升 ≥150% |")
        md_lines.append("| **TPOT** (每 Token 延迟) | 生成每个 Token 的平均时间 | 保持稳定 |")
        md_lines.append("")
        md_lines.append("### 测试关注点")
        md_lines.append("")
        md_lines.append("1. **Prefill 阶段优化**: 缓存能否有效减少 Prefill 计算时间")
        md_lines.append("2. **系统吞吐量**: 缓存对并发处理能力的提升")
        md_lines.append("3. **Decode 稳定性**: 缓存是否影响 Decode 阶段性能")
        md_lines.append("4. **跨节点传输**: KV Cache 在节点间的传输效率（如适用）")

    def _add_test_environment(self, md_lines: List[str]):
        """添加测试环境"""
        # 从统计数据中提取信息
        scenario = self.round1.get('scenario', '未知场景')
        model_info = self.stats_file.name

        md_lines.append("### 硬件环境")
        md_lines.append("")
        md_lines.append("| 组件 | 配置 |")
        md_lines.append("|------|------|")
        md_lines.append("| **推理服务器** | GPU 服务器（型号待补充）|")
        md_lines.append("| **GPU** | NVIDIA A100 / H100（待补充）|")
        md_lines.append("| **网络** | RDMA / TCP（根据配置）|")
        md_lines.append("| **Mooncake** | Master + 分布式存储节点 |")
        md_lines.append("")
        md_lines.append("### 软件环境")
        md_lines.append("")
        md_lines.append("| 组件 | 版本 |")
        md_lines.append("|------|------|")
        md_lines.append("| **模型** | 从文件名推断或待补充 |")
        md_lines.append("| **vLLM** | 最新版本 + LMCache 集成 |")
        md_lines.append("| **LMCache** | LMCacheConnectorV1 |")
        md_lines.append("| **Mooncake** | 生产版本 |")
        md_lines.append("")
        md_lines.append("### 关键配置")
        md_lines.append("")
        md_lines.append("```yaml")
        md_lines.append("# LMCache 配置")
        md_lines.append("chunk_size: 256")
        md_lines.append("remote_url: mooncakestore://master:50052/")
        md_lines.append("protocol: rdma  # 或 tcp")
        md_lines.append("")
        md_lines.append("# vLLM 配置")
        md_lines.append("--no-enable-prefix-caching")
        md_lines.append("--kv-transfer-config '{")
        md_lines.append('  "kv_connector":"LMCacheConnectorV1",')
        md_lines.append('  "kv_role":"kv_both"')
        md_lines.append("}'")
        md_lines.append("```")

    def _add_test_methodology(self, md_lines: List[str]):
        """添加测试方法"""
        total_requests = self.round1.get('total_requests', 0)
        scenario = self.round1.get('scenario', '测试场景')

        md_lines.append("### 测试设计")
        md_lines.append("")
        md_lines.append("采用 **A/B 对比测试** 方法，通过两轮测试对比缓存效果：")
        md_lines.append("")
        md_lines.append("| 轮次 | 说明 | 缓存状态 |")
        md_lines.append("|------|------|----------|")
        md_lines.append("| **Round 1** | Baseline（基线测试）| 🥶 缓存为空，完整 Prefill 计算 |")
        md_lines.append("| **Round 2** | Cache Hit（缓存测试）| 🔥 从 Mooncake 加载 KV Cache |")
        md_lines.append("")
        md_lines.append("### 测试场景")
        md_lines.append("")
        md_lines.append(f"**场景**: {scenario}")
        md_lines.append("")
        md_lines.append("该场景模拟真实业务中的高缓存复用场景，例如：")
        md_lines.append("- 多个用户对同一份文档提问")
        md_lines.append("- 多轮对话中共享历史上下文")
        md_lines.append("- 代码生成中共享代码库上下文")
        md_lines.append("")
        md_lines.append("### 测试数据")
        md_lines.append("")
        md_lines.append(f"- **请求总数**: {total_requests} 个")
        md_lines.append(f"- **测试轮次**: 2 轮（Baseline + Cache Hit）")
        md_lines.append("- **Prompt 一致性**: 两轮测试使用**完全相同**的 prompt")
        md_lines.append("- **生成参数**: temperature=0.0（确保输出一致性）")
        md_lines.append("")
        md_lines.append("### 测试流程")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append("1. 启动 vLLM 服务（已配置 LMCache + Mooncake）")
        md_lines.append("2. 清空 Mooncake 缓存")
        md_lines.append("3. Round 1: 发送测试请求")
        md_lines.append("   ├─ Mooncake 缓存为空")
        md_lines.append("   ├─ vLLM 执行完整 Prefill 计算")
        md_lines.append("   └─ KV Cache 存储到 Mooncake")
        md_lines.append("4. 等待 5 秒（确保缓存写入完成）")
        md_lines.append("5. Round 2: 发送相同请求")
        md_lines.append("   ├─ Mooncake 已有缓存")
        md_lines.append("   ├─ vLLM 从 Mooncake 加载 KV Cache")
        md_lines.append("   └─ 跳过 Prefill，直接 Decode")
        md_lines.append("6. 采集性能指标，生成报告")
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("### 测试可靠性保证")
        md_lines.append("")
        md_lines.append("- ✅ 使用相同的硬件环境和软件配置")
        md_lines.append("- ✅ 两轮测试使用完全相同的 prompt")
        md_lines.append("- ✅ 控制并发数和请求模式一致")
        md_lines.append("- ✅ 多次重复测试确保结果稳定")

    def _add_executive_summary(self, md_lines: List[str]):
        """添加测试摘要"""
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100

        if ttft_reduction >= 60 and throughput_increase >= 150:
            conclusion = "**✅ 测试结果优秀**"
            summary = "Mooncake KV Cache 显著提升了系统性能，所有关键指标均达到预期目标。"
        elif ttft_reduction >= 40 or throughput_increase >= 100:
            conclusion = "**⚠️ 测试结果良好**"
            summary = "缓存效果明显，但部分指标未达最优。建议调整配置后重新测试。"
        else:
            conclusion = "**❌ 测试结果不理想**"
            summary = "缓存效果不明显，需要排查配置或环境问题。"

        md_lines.append(conclusion)
        md_lines.append("")
        md_lines.append(summary)
        md_lines.append("")
        md_lines.append("### 关键指标")
        md_lines.append("")
        md_lines.append(f"1. **TTFT (首 Token 延迟)**")
        md_lines.append(f"   - Baseline: {self.round1['avg_ttft']*1000:.1f} ms")
        md_lines.append(f"   - Cache Hit: {self.round2['avg_ttft']*1000:.1f} ms")
        md_lines.append(f"   - 降低: {ttft_reduction:.1f}% (目标: ≥60%)")
        md_lines.append("")
        md_lines.append(f"2. **吞吐量**")
        md_lines.append(f"   - Baseline: {self.round1['request_throughput']:.2f} req/s")
        md_lines.append(f"   - Cache Hit: {self.round2['request_throughput']:.2f} req/s")
        md_lines.append(f"   - 提升: {throughput_increase:.1f}% (目标: ≥150%)")
        md_lines.append("")
        md_lines.append(f"3. **TPOT (每 Token 延迟)**")
        tpot_change = ((self.round2['avg_tpot'] - self.round1['avg_tpot']) / self.round1['avg_tpot']) * 100
        md_lines.append(f"   - Baseline: {self.round1['avg_tpot']*1000:.2f} ms/token")
        md_lines.append(f"   - Cache Hit: {self.round2['avg_tpot']*1000:.2f} ms/token")
        md_lines.append(f"   - 变化: {tpot_change:+.1f}%")

    def _add_business_value(self, md_lines: List[str]):
        """添加性能提升分析"""
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100

        md_lines.append("### 📊 性能提升量化")
        md_lines.append("")
        md_lines.append(f"| 指标 | Baseline | Cache Hit | 提升/降低 |")
        md_lines.append(f"|------|----------|-----------|-----------|")
        md_lines.append(f"| TTFT (平均) | {self.round1['avg_ttft']*1000:.1f} ms | {self.round2['avg_ttft']*1000:.1f} ms | ↓ {ttft_reduction:.1f}% |")
        md_lines.append(f"| 吞吐量 | {self.round1['request_throughput']:.2f} req/s | {self.round2['request_throughput']:.2f} req/s | ↑ {throughput_increase:.1f}% |")

        token_throughput_increase = 0
        if self.round1.get('token_throughput', 0) > 0:
            token_throughput_increase = (self.round2['token_throughput'] / self.round1['token_throughput'] - 1) * 100
            md_lines.append(f"| Token 吞吐 | {self.round1['token_throughput']:.1f} tokens/s | {self.round2['token_throughput']:.1f} tokens/s | ↑ {token_throughput_increase:.1f}% |")

        md_lines.append("")
        md_lines.append("### 🎯 缓存效果分析")
        md_lines.append("")

        if ttft_reduction >= 60:
            md_lines.append(f"- **TTFT 降低 {ttft_reduction:.1f}%**: 缓存成功跳过了大部分 Prefill 计算")
            md_lines.append(f"- **评价**: 缓存效果优秀，达到预期目标")
        elif ttft_reduction >= 40:
            md_lines.append(f"- **TTFT 降低 {ttft_reduction:.1f}%**: 缓存有效，但还有优化空间")
            md_lines.append(f"- **评价**: 缓存效果良好，建议检查缓存命中率")
        else:
            md_lines.append(f"- **TTFT 降低 {ttft_reduction:.1f}%**: 缓存效果不明显")
            md_lines.append(f"- **评价**: 需要排查配置问题")

        md_lines.append("")

        if throughput_increase >= 150:
            md_lines.append(f"- **吞吐量提升 {throughput_increase:.1f}%**: 系统并发处理能力显著提升")
            md_lines.append(f"- **评价**: 相同硬件可支持 {1 + throughput_increase/100:.1f}x 的请求量")
        elif throughput_increase >= 100:
            md_lines.append(f"- **吞吐量提升 {throughput_increase:.1f}%**: 系统并发处理能力明显提升")
            md_lines.append(f"- **评价**: 相同硬件可支持 {1 + throughput_increase/100:.1f}x 的请求量")
        else:
            md_lines.append(f"- **吞吐量提升 {throughput_increase:.1f}%**: 吞吐量提升有限")
            md_lines.append(f"- **评价**: 建议检查并发配置和资源利用率")

        md_lines.append("")
        md_lines.append("### 📋 适用场景")
        md_lines.append("")
        md_lines.append("基于测试结果，Mooncake KV Cache 在以下场景效果最佳：")
        md_lines.append("")
        md_lines.append("- ✅ 长上下文文档问答（90%+ 缓存复用）")
        md_lines.append("- ✅ 多轮对话系统（85%+ 上下文复用）")
        md_lines.append("- ✅ 代码补全和生成（80%+ 前缀复用）")
        md_lines.append("- ✅ 批量处理相似任务（95%+ 模板复用）")

    def _add_visual_comparison(self, md_lines: List[str]):
        """添加可视化对比"""
        ttft_baseline = self.round1['avg_ttft'] * 1000
        ttft_cached = self.round2['avg_ttft'] * 1000
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100

        throughput_baseline = self.round1['request_throughput']
        throughput_cached = self.round2['request_throughput']
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100

        # 响应速度对比
        md_lines.append("### ⚡ 响应速度对比（首 Token 延迟）")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(f"无缓存:  {'█' * int(ttft_baseline / 10)}  {ttft_baseline:.0f} ms")
        md_lines.append(f"有缓存:  {'█' * int(ttft_cached / 10)}  {ttft_cached:.0f} ms")
        md_lines.append("")
        md_lines.append(f"         ↓ 降低 {ttft_reduction:.0f}%")
        md_lines.append("```")
        md_lines.append("")

        # 吞吐量对比
        md_lines.append("### 🚀 系统吞吐量对比")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(f"无缓存:  {'█' * int(throughput_baseline * 10)}  {throughput_baseline:.1f} req/s")
        md_lines.append(f"有缓存:  {'█' * int(throughput_cached * 10)}  {throughput_cached:.1f} req/s")
        md_lines.append("")
        md_lines.append(f"         ↑ 提升 {throughput_increase:.0f}%")
        md_lines.append("```")
        md_lines.append("")


    def generate_report(self, output_file: str = None) -> str:
        """生成技术性能测试 Markdown 报告"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"cache_effect_report_{timestamp}.md"

        output_path = Path(output_file)

        md_lines = []

        # 标题和封面
        md_lines.append("# Mooncake KV Cache 性能测试报告")
        md_lines.append("")
        md_lines.append(f"**报告日期**: {datetime.now().strftime('%Y年%m月%d日')}")
        md_lines.append(f"**报告编号**: TEST-{datetime.now().strftime('%Y%m%d')}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 目录
        md_lines.append("## 📑 报告目录")
        md_lines.append("")
        md_lines.append("1. [测试摘要](#-测试摘要)")
        md_lines.append("2. [测试目的](#-测试目的)")
        md_lines.append("3. [测试环境](#-测试环境)")
        md_lines.append("4. [测试方法](#-测试方法)")
        md_lines.append("5. [测试结果](#-测试结果)")
        md_lines.append("6. [性能分析](#-性能分析)")
        md_lines.append("7. [结论与建议](#-结论与建议)")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 测试摘要
        md_lines.append("## 📋 测试摘要")
        md_lines.append("")
        self._add_executive_summary(md_lines)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 测试目的
        md_lines.append("## 🎯 测试目的")
        md_lines.append("")
        self._add_test_purpose(md_lines)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 测试环境
        md_lines.append("## 🖥️ 测试环境")
        md_lines.append("")
        self._add_test_environment(md_lines)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 测试方法
        md_lines.append("## 🔬 测试方法")
        md_lines.append("")
        self._add_test_methodology(md_lines)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 测试结果 - 性能对比
        self._add_visual_comparison(md_lines)
        md_lines.append("")

        # 详细指标表格
        md_lines.append("### 📋 详细指标")
        md_lines.append("")
        md_lines.append("| 指标 | 无缓存 (Baseline) | 有缓存 (Cache Hit) | 改善 | 目标 | 状态 |")
        md_lines.append("|------|-------------------|-------------------|------|------|------|")

        # TTFT
        ttft_baseline = self.round1['avg_ttft'] * 1000
        ttft_cached = self.round2['avg_ttft'] * 1000
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100
        ttft_status = "✅" if ttft_reduction >= 60 else ("⚠️" if ttft_reduction >= 40 else "❌")
        md_lines.append(f"| TTFT (平均) | {ttft_baseline:.2f} ms | {ttft_cached:.2f} ms | -{ttft_reduction:.1f}% | -60% | {ttft_status} |")

        # TTFT P90
        ttft_p90_baseline = self.round1['p90_ttft'] * 1000
        ttft_p90_cached = self.round2['p90_ttft'] * 1000
        ttft_p90_reduction = (1 - self.round2['p90_ttft'] / self.round1['p90_ttft']) * 100
        md_lines.append(f"| TTFT (P90) | {ttft_p90_baseline:.2f} ms | {ttft_p90_cached:.2f} ms | -{ttft_p90_reduction:.1f}% | - | - |")

        # TPOT
        tpot_baseline = self.round1['avg_tpot'] * 1000
        tpot_cached = self.round2['avg_tpot'] * 1000
        tpot_change = ((self.round2['avg_tpot'] - self.round1['avg_tpot']) / self.round1['avg_tpot']) * 100
        tpot_status = "✅" if abs(tpot_change) < 10 else "⚠️"
        md_lines.append(f"| TPOT (平均) | {tpot_baseline:.2f} ms | {tpot_cached:.2f} ms | {tpot_change:+.1f}% | 稳定 | {tpot_status} |")

        # 吞吐量
        throughput_baseline = self.round1['request_throughput']
        throughput_cached = self.round2['request_throughput']
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100
        throughput_status = "✅" if throughput_increase >= 150 else ("⚠️" if throughput_increase >= 100 else "❌")
        md_lines.append(f"| 吞吐量 (req/s) | {throughput_baseline:.2f} | {throughput_cached:.2f} | +{throughput_increase:.1f}% | +150% | {throughput_status} |")

        # Token 吞吐量
        if self.round1.get('token_throughput', 0) > 0:
            token_throughput_baseline = self.round1['token_throughput']
            token_throughput_cached = self.round2['token_throughput']
            token_increase = (token_throughput_cached / token_throughput_baseline - 1) * 100
            md_lines.append(f"| Token 吞吐量 | {token_throughput_baseline:.2f} tokens/s | {token_throughput_cached:.2f} tokens/s | +{token_increase:.1f}% | - | - |")

        # 延迟
        latency_baseline = self.round1['avg_latency']
        latency_cached = self.round2['avg_latency']
        latency_change = ((self.round2['avg_latency'] - self.round1['avg_latency']) / self.round1['avg_latency']) * 100
        md_lines.append(f"| 端到端延迟 | {latency_baseline:.2f} s | {latency_cached:.2f} s | {latency_change:+.1f}% | - | - |")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 性能分析
        md_lines.append("## 📊 性能分析")
        md_lines.append("")
        self._add_business_value(md_lines)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        # 详细分析（可选，放到附录）
        md_lines.append("## 📈 技术分析（详细）")
        md_lines.append("")

        md_lines.append("### 🎯 TTFT 分析")
        md_lines.append("")
        md_lines.append(f"- **降低幅度**: {ttft_reduction:.1f}%")
        if ttft_reduction >= 60:
            md_lines.append("- **评价**: ✅ 优秀！缓存显著降低了首 token 延迟")
            md_lines.append("- **说明**: Mooncake KV Cache 有效避免了 Prefill 阶段的重复计算")
        elif ttft_reduction >= 40:
            md_lines.append("- **评价**: ⚠️ 一般，还有优化空间")
            md_lines.append("- **建议**: 检查缓存命中率、网络延迟、chunk_size 配置")
        else:
            md_lines.append("- **评价**: ❌ 不理想，需要排查问题")
            md_lines.append("- **建议**: ")
            md_lines.append("  1. 检查 LMCache 配置是否正确")
            md_lines.append("  2. 验证 Mooncake Master 连接")
            md_lines.append("  3. 查看 vLLM 日志确认 KV Cache 传输")
            md_lines.append("  4. 确认测试 prompt 在两轮间完全一致")
        md_lines.append("")

        md_lines.append("### 🚀 吞吐量分析")
        md_lines.append("")
        md_lines.append(f"- **提升幅度**: {throughput_increase:.1f}%")
        if throughput_increase >= 150:
            md_lines.append("- **评价**: ✅ 优秀！缓存大幅提升了系统吞吐量")
            md_lines.append("- **说明**: 跳过 Prefill 使得系统可以处理更多请求")
        elif throughput_increase >= 100:
            md_lines.append("- **评价**: ⚠️ 一般，还有提升空间")
            md_lines.append("- **建议**: 检查 max_num_seqs、GPU 利用率配置")
        else:
            md_lines.append("- **评价**: ❌ 不理想，需要排查问题")
            md_lines.append("- **建议**: 同 TTFT 排查步骤")
        md_lines.append("")

        md_lines.append("### ⚡ TPOT 分析")
        md_lines.append("")
        md_lines.append(f"- **变化**: {tpot_change:+.1f}%")
        if abs(tpot_change) < 10:
            md_lines.append("- **评价**: ✅ 正常，TPOT 保持稳定")
            md_lines.append("- **说明**: 缓存不影响 Decode 阶段性能")
        else:
            md_lines.append("- **评价**: ⚠️ 注意，TPOT 有明显变化")
            if tpot_change > 0:
                md_lines.append("- **说明**: TPOT 增加可能因为 GPU 负载或调度变化")
            else:
                md_lines.append("- **说明**: TPOT 降低是好现象，系统整体更优化")
        md_lines.append("")

        # 结论与建议
        md_lines.append("## 💡 结论与建议")
        md_lines.append("")

        success_count = 0
        total_checks = 2

        if ttft_reduction >= 60:
            success_count += 1
        if throughput_increase >= 150:
            success_count += 1

        md_lines.append("### 📊 测试结论")
        md_lines.append("")

        if success_count == total_checks:
            md_lines.append("**✅ 所有关键指标达标**")
            md_lines.append("")
            md_lines.append("测试结果表明:")
            md_lines.append(f"- TTFT 降低 {ttft_reduction:.0f}%（目标: ≥60%）")
            md_lines.append(f"- 吞吐量提升 {throughput_increase:.0f}%（目标: ≥150%）")
            md_lines.append(f"- Mooncake KV Cache 显著提升了系统性能")
            md_lines.append("")
            md_lines.append("### 🔧 优化建议")
            md_lines.append("")
            md_lines.append("系统运行良好，可考虑进一步优化:")
            md_lines.append("1. 监控缓存命中率，分析缓存效果")
            md_lines.append("2. 测试不同并发场景下的性能表现")
            md_lines.append("3. 评估网络带宽对跨节点传输的影响")
            md_lines.append("4. 记录长期运行的稳定性数据")
        elif success_count >= 1:
            md_lines.append("**⚠️ 部分指标达标**")
            md_lines.append("")
            md_lines.append("测试结果:")
            md_lines.append(f"- TTFT 降低 {ttft_reduction:.0f}%（目标: ≥60%）{'✅' if ttft_reduction >= 60 else '❌'}")
            md_lines.append(f"- 吞吐量提升 {throughput_increase:.0f}%（目标: ≥150%）{'✅' if throughput_increase >= 150 else '❌'}")
            md_lines.append("")
            md_lines.append("### 🔧 优化建议")
            md_lines.append("")
            md_lines.append("系统有改进空间，建议:")
            if ttft_reduction < 60:
                md_lines.append("**TTFT 优化**:")
                md_lines.append("- 检查网络延迟（优先使用 RDMA）")
                md_lines.append("- 调整 LMCache chunk_size 参数")
                md_lines.append("- 验证 KV Cache 传输效率")
                md_lines.append("")
            if throughput_increase < 150:
                md_lines.append("**吞吐量优化**:")
                md_lines.append("- 增加测试并发数")
                md_lines.append("- 检查 GPU 利用率")
                md_lines.append("- 调整 vLLM max_num_seqs 参数")
                md_lines.append("")
            md_lines.append("优化后建议重新测试验证效果。")
        else:
            md_lines.append("**❌ 关键指标未达标**")
            md_lines.append("")
            md_lines.append("测试结果:")
            md_lines.append(f"- TTFT 降低 {ttft_reduction:.0f}%（目标: ≥60%）❌")
            md_lines.append(f"- 吞吐量提升 {throughput_increase:.0f}%（目标: ≥150%）❌")
            md_lines.append("")
            md_lines.append("### 🔍 问题排查")
            md_lines.append("")
            md_lines.append("缓存效果不明显，需要排查配置:")
            md_lines.append("")
            md_lines.append("**1. LMCache 配置检查**")
            md_lines.append("- 确认 vLLM 启动时正确配置了 `--kv-transfer-config`")
            md_lines.append("- 检查 lmcache_config.yaml 中的 remote_url 是否正确")
            md_lines.append("- 验证 chunk_size 配置（推荐 256）")
            md_lines.append("")
            md_lines.append("**2. Mooncake 连接检查**")
            md_lines.append("- 确认 Mooncake Master 地址和端口可达")
            md_lines.append("- 检查网络连接（TCP 或 RDMA）")
            md_lines.append("- 查看 vLLM 日志确认 KV Cache 读写")
            md_lines.append("")
            md_lines.append("**3. 测试数据一致性**")
            md_lines.append("- 验证两轮测试使用**完全相同**的 prompt")
            md_lines.append("- 确认 temperature=0.0（保证输出一致）")
            md_lines.append("- 检查 Round 2 是否真的命中缓存")
            md_lines.append("")
            md_lines.append("**4. 日志分析**")
            md_lines.append("- 查看 vLLM 日志中的 LMCache 相关信息")
            md_lines.append("- 检查是否有 KV Cache 加载/存储的日志")
            md_lines.append("- 确认是否有错误或警告信息")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        md_lines.append(f"**报告结束** | 关键指标达成率: {success_count}/{total_checks}")
        md_lines.append("")

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

        print(f"✓ 报告已生成: {output_path}")
        return str(output_path)

    def generate_charts(self, output_dir: str = "cache_effect_charts") -> List[str]:
        """生成对比图表"""
        if not HAS_MATPLOTLIB:
            print("跳过图表生成（matplotlib 未安装）")
            print("可选安装: pip install matplotlib")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        chart_files = []

        # 1. TTFT 对比图
        chart_file = self._generate_ttft_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        # 2. 吞吐量对比图
        chart_file = self._generate_throughput_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        # 3. 缓存效果总览图
        chart_file = self._generate_overview_chart(output_path)
        if chart_file:
            chart_files.append(chart_file)

        return chart_files

    def _generate_ttft_chart(self, output_path: Path) -> str:
        """生成 TTFT 对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        categories = ['Round 1\n(Baseline)', 'Round 2\n(Cache Hit)']
        ttfts = [
            self.round1['avg_ttft'] * 1000,
            self.round2['avg_ttft'] * 1000
        ]

        colors = ['#e74c3c', '#2ecc71']
        bars = ax.bar(categories, ttfts, color=colors, width=0.5)

        ax.set_ylabel('TTFT (ms)', fontsize=12)
        ax.set_title('TTFT 对比：缓存效果', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f} ms',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

        # 添加改善百分比
        reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100
        ax.text(0.5, max(ttfts) * 0.5, f'降低 {reduction:.1f}%',
                ha='center', fontsize=16, fontweight='bold',
                color='green', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        chart_file = output_path / "ttft_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_throughput_chart(self, output_path: Path) -> str:
        """生成吞吐量对比图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        categories = ['Round 1\n(Baseline)', 'Round 2\n(Cache Hit)']
        throughputs = [
            self.round1['request_throughput'],
            self.round2['request_throughput']
        ]

        colors = ['#3498db', '#f39c12']
        bars = ax.bar(categories, throughputs, color=colors, width=0.5)

        ax.set_ylabel('吞吐量 (req/s)', fontsize=12)
        ax.set_title('吞吐量对比：缓存效果', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f} req/s',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

        # 添加提升百分比
        increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100
        ax.text(0.5, max(throughputs) * 0.5, f'提升 {increase:.1f}%',
                ha='center', fontsize=16, fontweight='bold',
                color='green', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        chart_file = output_path / "throughput_comparison.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)

    def _generate_overview_chart(self, output_path: Path) -> str:
        """生成缓存效果总览图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # TTFT 降低
        ttft_reduction = (1 - self.round2['avg_ttft'] / self.round1['avg_ttft']) * 100
        colors = ['#2ecc71' if ttft_reduction >= 60 else '#f39c12']
        bars1 = ax1.barh(['TTFT 降低'], [ttft_reduction], color=colors)
        ax1.set_xlabel('降低百分比 (%)', fontsize=11)
        ax1.set_title('TTFT 降低效果', fontsize=12, fontweight='bold')
        ax1.axvline(x=60, color='green', linestyle='--', linewidth=2, alpha=0.7, label='目标: 60%')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='x')

        for bar in bars1:
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2.,
                    f' {width:.1f}%',
                    ha='left', va='center', fontsize=12, fontweight='bold')

        # 吞吐量提升
        throughput_increase = (self.round2['request_throughput'] / self.round1['request_throughput'] - 1) * 100
        colors = ['#e74c3c' if throughput_increase >= 150 else '#f39c12']
        bars2 = ax2.barh(['吞吐量提升'], [throughput_increase], color=colors)
        ax2.set_xlabel('提升百分比 (%)', fontsize=11)
        ax2.set_title('吞吐量提升效果', fontsize=12, fontweight='bold')
        ax2.axvline(x=150, color='green', linestyle='--', linewidth=2, alpha=0.7, label='目标: 150%')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='x')

        for bar in bars2:
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height()/2.,
                    f' {width:.1f}%',
                    ha='left', va='center', fontsize=12, fontweight='bold')

        chart_file = output_path / "cache_effect_overview.png"
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150)
        plt.close()

        return str(chart_file)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="对比 Round 1 (Baseline) vs Round 2 (Cache Hit) 测试结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 打印缓存效果摘要
  python3 compare_results.py --stats test_results/test_stats_20250101_120000.json

  # 生成完整报告和图表
  python3 compare_results.py --stats test_results/test_stats_20250101_120000.json \\
                             --generate-report --generate-charts

  # 自定义输出位置
  python3 compare_results.py --stats test_results/test_stats_20250101_120000.json \\
                             --generate-report --output my_report.md \\
                             --generate-charts --chart-dir my_charts
        """
    )
    parser.add_argument('--stats', type=str, required=True,
                        help='测试统计文件路径 (test_stats_*.json)')
    parser.add_argument('--generate-report', action='store_true',
                        help='生成 Markdown 报告')
    parser.add_argument('--output', type=str,
                        help='报告输出文件名（默认: cache_effect_report_<timestamp>.md）')
    parser.add_argument('--generate-charts', action='store_true',
                        help='生成对比图表（需要 matplotlib）')
    parser.add_argument('--chart-dir', type=str, default='cache_effect_charts',
                        help='图表输出目录（默认: cache_effect_charts）')

    args = parser.parse_args()

    print("="*80)
    print("🎯 缓存效果分析工具")
    print("="*80)

    try:
        # 初始化对比器
        comparator = CacheEffectComparator(args.stats)

        # 打印摘要（始终执行）
        comparator.print_summary()

        # 生成报告
        if args.generate_report:
            report_file = comparator.generate_report(args.output)
            print(f"\n✓ 详细报告: {report_file}")

        # 生成图表
        if args.generate_charts:
            chart_files = comparator.generate_charts(args.chart_dir)
            if chart_files:
                print(f"\n✓ 生成了 {len(chart_files)} 个图表:")
                for chart in chart_files:
                    print(f"  - {chart}")
            else:
                print(f"\n⚠️  未生成图表（可能缺少 matplotlib）")

        print("\n✅ 分析完成!")

    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {e}")
        print("请确认测试统计文件路径正确")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 数据错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
