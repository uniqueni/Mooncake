#!/usr/bin/env python3
"""
vLLM + LMCache + Mooncake 缓存效果测试脚本

这个脚本用于测试 vLLM 与 LMCache + Mooncake 集成后的 KV Cache 缓存效果。
支持多种测试场景，包括：
- Cold Start vs Cache Hit 对比
- 不同前缀重用率测试
- 长上下文测试
- 并发性能测试
"""

import asyncio
import json
import time
import argparse
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import statistics
import sys

try:
    from openai import AsyncOpenAI
except ImportError:
    print("错误: 需要安装 openai 包")
    print("运行: pip install openai")
    sys.exit(1)


@dataclass
class RequestResult:
    """单个请求的结果"""
    request_id: int
    scenario: str
    round_num: int
    prompt_length: int
    success: bool
    elapsed_time: float
    ttft: Optional[float] = None
    tpot: Optional[float] = None
    output_tokens: int = 0
    error: Optional[str] = None
    timestamp: float = 0


@dataclass
class RoundStats:
    """一轮测试的统计结果"""
    scenario: str
    round_num: int
    total_requests: int
    success_requests: int
    failed_requests: int
    total_time: float
    avg_latency: float
    median_latency: float
    p90_latency: float
    p99_latency: float
    throughput: float
    avg_ttft: Optional[float] = None
    median_ttft: Optional[float] = None
    p90_ttft: Optional[float] = None
    avg_tpot: Optional[float] = None
    median_tpot: Optional[float] = None
    p90_tpot: Optional[float] = None


class VLLMCacheTestRunner:
    """测试运行器"""

    def __init__(self, config_path: str = "test_config.yaml"):
        """初始化测试运行器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.proxy_url = self.config['proxy']['url']
        self.model_name = self.config['model']['name']
        self.results: List[RequestResult] = []
        self.round_stats: List[RoundStats] = []

        print(f"✓ 测试配置加载成功")
        print(f"  Proxy URL: {self.proxy_url}")
        print(f"  Model: {self.model_name}")

    def generate_prompts(self, scenario: str) -> List[str]:
        """生成测试提示词"""
        scenario_config = self.config['test_scenarios'][scenario]
        num_requests = scenario_config['num_requests']
        prompt_template = scenario_config['prompt_template']
        reuse_ratio = scenario_config.get('reuse_ratio', 0)

        prompts = []

        if scenario == 'high_reuse':
            # 高重用率：所有请求使用相同的长前缀
            base_prefix = prompt_template.format(i=0)
            for i in range(num_requests):
                prompts.append(base_prefix + f"\n请求ID: {i}")

        elif scenario == 'medium_reuse':
            # 中等重用率：部分请求共享前缀
            num_groups = max(1, int(num_requests * (1 - reuse_ratio)))
            for i in range(num_requests):
                group_id = i % num_groups
                prompts.append(prompt_template.format(i=group_id, req=i))

        elif scenario == 'low_reuse':
            # 低重用率：每个请求都是唯一的
            for i in range(num_requests):
                prompts.append(prompt_template.format(i=i))

        elif scenario == 'long_context':
            # 长上下文测试
            context_length = scenario_config.get('context_length', 8192)
            base_text = "这是一段用于测试长上下文的文本。" * (context_length // 50)
            for i in range(num_requests):
                prompts.append(f"{base_text}\n\n问题{i}: {prompt_template.format(i=i)}")

        else:
            raise ValueError(f"未知的测试场景: {scenario}")

        return prompts

    async def send_request(
        self,
        client: AsyncOpenAI,
        prompt: str,
        request_id: int,
        scenario: str,
        round_num: int
    ) -> RequestResult:
        """发送单个请求并记录结果"""
        start_time = time.time()
        timestamp = datetime.now().timestamp()

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config['model']['max_tokens'],
                temperature=self.config['model']['temperature'],
            )

            elapsed = time.time() - start_time

            # 提取输出 tokens 数量
            output_tokens = 0
            if hasattr(response, 'usage') and response.usage:
                output_tokens = response.usage.completion_tokens

            result = RequestResult(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                prompt_length=len(prompt),
                success=True,
                elapsed_time=elapsed,
                output_tokens=output_tokens,
                timestamp=timestamp
            )

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            return RequestResult(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                prompt_length=len(prompt),
                success=False,
                elapsed_time=elapsed,
                error=str(e),
                timestamp=timestamp
            )

    async def run_scenario(
        self,
        scenario: str,
        num_rounds: int = 2,
        concurrency: Optional[int] = None
    ) -> List[RoundStats]:
        """运行单个测试场景"""
        print(f"\n{'='*80}")
        print(f"🧪 测试场景: {scenario}")
        print(f"{'='*80}")

        client = AsyncOpenAI(base_url=self.proxy_url, api_key="dummy")
        prompts = self.generate_prompts(scenario)

        print(f"生成了 {len(prompts)} 个测试请求")
        print(f"将运行 {num_rounds} 轮测试")

        if concurrency:
            print(f"并发限制: {concurrency}")

        scenario_stats = []

        for round_num in range(num_rounds):
            print(f"\n{'─'*80}")
            print(f"📊 Round {round_num + 1}/{num_rounds}")
            print(f"{'─'*80}")

            round_start = time.time()

            # 创建任务
            tasks = [
                self.send_request(client, prompt, i, scenario, round_num + 1)
                for i, prompt in enumerate(prompts)
            ]

            # 根据并发限制执行任务
            if concurrency:
                results = []
                for i in range(0, len(tasks), concurrency):
                    batch = tasks[i:i+concurrency]
                    batch_results = await asyncio.gather(*batch)
                    results.extend(batch_results)
                    print(f"  已完成 {min(i+concurrency, len(tasks))}/{len(tasks)} 个请求...")
            else:
                results = await asyncio.gather(*tasks)

            round_elapsed = time.time() - round_start

            # 保存结果
            self.results.extend(results)

            # 计算统计数据
            stats = self._calculate_stats(results, scenario, round_num + 1, round_elapsed)
            scenario_stats.append(stats)
            self.round_stats.append(stats)

            # 打印结果
            self._print_round_stats(stats, round_num)

            # 如果有多轮，比较性能提升
            if round_num > 0:
                self._print_improvement(scenario_stats[0], stats)

            # 等待一段时间再进行下一轮
            if round_num < num_rounds - 1:
                wait_time = self.config.get('round_wait_seconds', 5)
                print(f"\n等待 {wait_time} 秒后开始下一轮...")
                await asyncio.sleep(wait_time)

        return scenario_stats

    def _calculate_stats(
        self,
        results: List[RequestResult],
        scenario: str,
        round_num: int,
        total_time: float
    ) -> RoundStats:
        """计算统计数据"""
        success_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        latencies = [r.elapsed_time for r in success_results]

        if not latencies:
            # 所有请求都失败了
            return RoundStats(
                scenario=scenario,
                round_num=round_num,
                total_requests=len(results),
                success_requests=0,
                failed_requests=len(failed_results),
                total_time=total_time,
                avg_latency=0,
                median_latency=0,
                p90_latency=0,
                p99_latency=0,
                throughput=0
            )

        latencies.sort()

        return RoundStats(
            scenario=scenario,
            round_num=round_num,
            total_requests=len(results),
            success_requests=len(success_results),
            failed_requests=len(failed_results),
            total_time=total_time,
            avg_latency=statistics.mean(latencies),
            median_latency=statistics.median(latencies),
            p90_latency=latencies[int(len(latencies) * 0.9)] if latencies else 0,
            p99_latency=latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0],
            throughput=len(success_results) / total_time if total_time > 0 else 0
        )

    def _print_round_stats(self, stats: RoundStats, round_num: int):
        """打印单轮统计结果"""
        print(f"\n📈 统计结果:")
        print(f"  总请求数:     {stats.total_requests}")
        print(f"  成功请求:     {stats.success_requests}")
        print(f"  失败请求:     {stats.failed_requests}")
        print(f"  总耗时:       {stats.total_time:.2f}s")
        print(f"\n  平均延迟:     {stats.avg_latency*1000:.2f}ms")
        print(f"  中位数延迟:   {stats.median_latency*1000:.2f}ms")
        print(f"  P90 延迟:     {stats.p90_latency*1000:.2f}ms")
        print(f"  P99 延迟:     {stats.p99_latency*1000:.2f}ms")
        print(f"\n  吞吐量:       {stats.throughput:.2f} req/s")

    def _print_improvement(self, baseline: RoundStats, current: RoundStats):
        """打印性能提升"""
        if baseline.avg_latency == 0:
            return

        latency_improvement = (1 - current.avg_latency / baseline.avg_latency) * 100
        throughput_improvement = (current.throughput / baseline.throughput - 1) * 100

        print(f"\n🎯 缓存效果 (相比 Round 1):")
        print(f"  延迟降低:     {latency_improvement:+.1f}%")
        print(f"  吞吐量提升:   {throughput_improvement:+.1f}%")

        if latency_improvement > 50:
            print(f"  ✅ 缓存效果显著！")
        elif latency_improvement > 20:
            print(f"  ⚠️  缓存效果一般")
        else:
            print(f"  ❌ 缓存效果不明显")

    def save_results(self, output_dir: str = "test_results"):
        """保存测试结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        results_file = f"{output_dir}/results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(r) for r in self.results],
                f,
                indent=2,
                ensure_ascii=False
            )

        # 保存统计摘要
        stats_file = f"{output_dir}/stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(s) for s in self.round_stats],
                f,
                indent=2,
                ensure_ascii=False
            )

        print(f"\n💾 结果已保存:")
        print(f"  详细结果: {results_file}")
        print(f"  统计摘要: {stats_file}")

        return results_file, stats_file


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="vLLM + LMCache + Mooncake 缓存效果测试"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='test_config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--scenarios',
        type=str,
        nargs='+',
        default=['high_reuse', 'medium_reuse', 'low_reuse'],
        help='要运行的测试场景'
    )
    parser.add_argument(
        '--rounds',
        type=int,
        default=2,
        help='每个场景运行的轮数'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        help='并发请求数限制'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='test_results',
        help='结果输出目录'
    )

    args = parser.parse_args()

    print("="*80)
    print("🚀 vLLM + LMCache + Mooncake 缓存效果测试")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        runner = VLLMCacheTestRunner(args.config)

        # 运行所有测试场景
        for scenario in args.scenarios:
            await runner.run_scenario(
                scenario,
                num_rounds=args.rounds,
                concurrency=args.concurrency
            )

        # 保存结果
        results_file, stats_file = runner.save_results(args.output_dir)

        print(f"\n{'='*80}")
        print("✅ 所有测试完成!")
        print(f"{'='*80}")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 生成报告提示
        print(f"\n📊 生成测试报告:")
        print(f"  python3 generate_report.py --stats {stats_file}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
