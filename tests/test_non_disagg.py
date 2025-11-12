#!/usr/bin/env python3
"""
非 PD 分离模式测试脚本

测试传统 vLLM 部署模式（单服务），重点测量：
- TTFT (Time to First Token)
- TPOT (Time per Output Token)
- 吞吐量
- 端到端延迟
- 缓存效果（如果启用）
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
class RequestMetrics:
    """单个请求的性能指标"""
    request_id: int
    scenario: str
    round_num: int

    # 基本信息
    prompt_length: int  # 输入 tokens
    output_length: int  # 输出 tokens

    # 时间指标
    ttft: Optional[float] = None  # Time to First Token (秒)
    tpot: Optional[float] = None  # Time per Output Token (秒)
    e2e_latency: float = 0.0  # 端到端延迟 (秒)

    # 状态
    success: bool = True
    error: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class ScenarioStats:
    """场景统计数据"""
    scenario: str
    round_num: int
    total_requests: int
    success_requests: int
    failed_requests: int
    total_time: float

    # TTFT 统计
    avg_ttft: float = 0.0
    median_ttft: float = 0.0
    p90_ttft: float = 0.0
    p99_ttft: float = 0.0

    # TPOT 统计
    avg_tpot: float = 0.0
    median_tpot: float = 0.0
    p90_tpot: float = 0.0

    # 延迟统计
    avg_latency: float = 0.0
    median_latency: float = 0.0
    p90_latency: float = 0.0
    p99_latency: float = 0.0

    # 吞吐量
    request_throughput: float = 0.0  # req/s
    token_throughput: float = 0.0  # tokens/s
    output_token_throughput: float = 0.0  # output tokens/s


class NonDisaggTestRunner:
    """非 PD 分离模式测试运行器"""

    def __init__(self, config_path: str = "test_config_large_models.yaml"):
        """初始化测试运行器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 获取活动模型配置
        active_model = self.config['active_model']
        self.model_config = self.config['models'][active_model]
        self.model_name = self.model_config['name']

        # 获取非 PD 分离部署配置
        deploy_config = self.config['deployment_modes']['non_disaggregated']
        if not deploy_config['enabled']:
            raise ValueError("非 PD 分离模式未启用，请检查配置文件")

        server_config = deploy_config['server']
        self.server_url = f"http://{server_config['host']}:{server_config['port']}/v1"

        self.results: List[RequestMetrics] = []
        self.scenario_stats: List[ScenarioStats] = []

        print(f"✓ 非 PD 分离模式测试配置加载成功")
        print(f"  模型: {self.model_name}")
        print(f"  服务器: {self.server_url}")

    def _generate_long_document(self, length: int = 16384) -> str:
        """生成指定长度的长文档（估算 tokens）"""
        # 简化：假设每个单词约 1.3 tokens
        words_needed = int(length / 1.3)

        # 生成技术文档样本
        base_text = """
        # Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving

        ## Introduction
        Large Language Models (LLMs) have revolutionized natural language processing tasks.
        However, serving these models efficiently at scale remains a significant challenge.
        Traditional architectures often suffer from low GPU utilization and high latency.

        ## Architecture Overview
        Mooncake introduces a disaggregated architecture that separates the prefill and decode
        phases into different clusters. This design enables better resource utilization and
        improves overall system throughput. The key innovation is a KVCache-centric scheduler
        that balances throughput maximization with latency SLO requirements.

        ## Technical Details
        The system consists of several core components:
        1. Transfer Engine: High-performance data transfer layer supporting RDMA and TCP
        2. Mooncake Store: Distributed KVCache storage across multiple nodes
        3. Scheduler: Intelligent request routing and cache management
        4. Metadata Service: Centralized coordination using etcd or HTTP endpoints

        ## Performance Results
        Extensive benchmarks show that Mooncake achieves:
        - Up to 525% increase in throughput compared to baseline methods
        - 60-70% reduction in Time to First Token (TTFT) with cache hits
        - Efficient handling of long-context scenarios (128k+ tokens)
        - Scalability to thousands of GPUs in production environments
        """

        # 重复文本直到达到所需长度
        repeated_text = (base_text * (words_needed // len(base_text.split()) + 1))
        words = repeated_text.split()[:words_needed]

        return ' '.join(words)

    def generate_prompts(self, scenario: str) -> List[Dict[str, Any]]:
        """生成测试提示词"""
        scenario_config = self.config['test_scenarios'][scenario]
        num_requests = scenario_config['num_requests']

        prompts = []

        if scenario == 'long_context_high_reuse':
            # 生成长文档
            long_doc = self._generate_long_document(
                scenario_config['context_length']
            )

            questions = scenario_config['questions']

            for i in range(num_requests):
                question = questions[i % len(questions)]
                prompt = f"{long_doc}\n\n基于上述文档，请回答问题 #{i}: {question}"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': scenario_config['context_length']
                })

        elif scenario == 'multi_turn_conversation':
            # 模拟多轮对话，逐步累积上下文
            conversation_history = ""
            turns = scenario_config['conversation_turns']

            for i in range(num_requests):
                turn = turns[i % len(turns)]
                conversation_history += f"\nUser: {turn}\nAssistant: [Previous response]\n"

                prompt = f"{conversation_history}\nUser: {turn}\nAssistant:"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': len(conversation_history.split()) * 1.3
                })

        elif scenario == 'batch_processing':
            # 批量处理，共享大量指令
            instruction = scenario_config['prompt_template'].split('Text to translate')[0]

            for i in range(num_requests):
                text = f"Sample text for translation task {i}. This is a technical document about distributed systems and high-performance computing."
                prompt = instruction + f"\n\nText to translate #{i}:\n{text}"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': len(instruction.split()) * 1.3 + 50
                })

        elif scenario == 'cold_start':
            # 冷启动，每个请求都是唯一的
            for i in range(num_requests):
                unique_content = f"This is a unique question about topic {i * 137 % 1000}. " * 50
                prompt = f"Question #{i}: {unique_content}"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': 700
                })

        else:
            raise ValueError(f"未知的测试场景: {scenario}")

        return prompts

    async def send_request(
        self,
        client: AsyncOpenAI,
        prompt_data: Dict[str, Any],
        request_id: int,
        scenario: str,
        round_num: int
    ) -> RequestMetrics:
        """发送单个请求并测量性能指标"""
        prompt = prompt_data['prompt']
        estimated_tokens = prompt_data['estimated_tokens']

        start_time = time.time()
        timestamp = datetime.now().timestamp()

        try:
            # 使用流式输出以测量 TTFT
            first_token_time = None
            output_tokens = 0
            total_output_time = 0

            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.model_config['max_tokens'],
                temperature=self.model_config['temperature'],
                stream=True,
            )

            async for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.time()

                if chunk.choices and chunk.choices[0].delta.content:
                    output_tokens += 1

            end_time = time.time()

            # 计算指标
            e2e_latency = end_time - start_time
            ttft = (first_token_time - start_time) if first_token_time else None

            total_output_time = end_time - first_token_time if first_token_time else e2e_latency
            tpot = (total_output_time / output_tokens) if output_tokens > 0 else None

            return RequestMetrics(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                prompt_length=int(estimated_tokens),
                output_length=output_tokens,
                ttft=ttft,
                tpot=tpot,
                e2e_latency=e2e_latency,
                success=True,
                timestamp=timestamp
            )

        except Exception as e:
            end_time = time.time()
            return RequestMetrics(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                prompt_length=int(estimated_tokens),
                output_length=0,
                e2e_latency=end_time - start_time,
                success=False,
                error=str(e),
                timestamp=timestamp
            )

    async def run_scenario(
        self,
        scenario: str,
        num_rounds: int = 2,
        concurrency: Optional[int] = None
    ) -> List[ScenarioStats]:
        """运行单个测试场景"""
        print(f"\n{'='*80}")
        print(f"🧪 测试场景: {scenario}")
        print(f"   {self.config['test_scenarios'][scenario]['description']}")
        print(f"{'='*80}")

        client = AsyncOpenAI(base_url=self.server_url, api_key="dummy")
        prompts = self.generate_prompts(scenario)

        print(f"生成了 {len(prompts)} 个测试请求")
        print(f"将运行 {num_rounds} 轮测试（第1轮: Cold Start, 第2轮: Cache Hit）")

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

            # 根据并发限制执行
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

            # 计算统计
            stats = self._calculate_stats(results, scenario, round_num + 1, round_elapsed)
            scenario_stats.append(stats)
            self.scenario_stats.append(stats)

            # 打印结果
            self._print_stats(stats, round_num)

            # 对比性能提升
            if round_num > 0:
                self._print_improvement(scenario_stats[0], stats)

            # 等待下一轮
            if round_num < num_rounds - 1:
                wait_time = self.config['performance_test'].get('rounds', 5)
                print(f"\n等待 {wait_time} 秒后开始下一轮...")
                await asyncio.sleep(wait_time)

        return scenario_stats

    def _calculate_stats(
        self,
        results: List[RequestMetrics],
        scenario: str,
        round_num: int,
        total_time: float
    ) -> ScenarioStats:
        """计算统计数据"""
        success_results = [r for r in results if r.success]

        if not success_results:
            return ScenarioStats(
                scenario=scenario,
                round_num=round_num,
                total_requests=len(results),
                success_requests=0,
                failed_requests=len(results),
                total_time=total_time
            )

        # TTFT 统计
        ttfts = [r.ttft for r in success_results if r.ttft is not None]
        ttfts.sort()

        # TPOT 统计
        tpots = [r.tpot for r in success_results if r.tpot is not None]
        tpots.sort()

        # 延迟统计
        latencies = [r.e2e_latency for r in success_results]
        latencies.sort()

        # Token 吞吐量
        total_input_tokens = sum(r.prompt_length for r in success_results)
        total_output_tokens = sum(r.output_length for r in success_results)
        total_tokens = total_input_tokens + total_output_tokens

        return ScenarioStats(
            scenario=scenario,
            round_num=round_num,
            total_requests=len(results),
            success_requests=len(success_results),
            failed_requests=len(results) - len(success_results),
            total_time=total_time,

            avg_ttft=statistics.mean(ttfts) if ttfts else 0,
            median_ttft=statistics.median(ttfts) if ttfts else 0,
            p90_ttft=ttfts[int(len(ttfts) * 0.9)] if ttfts else 0,
            p99_ttft=ttfts[int(len(ttfts) * 0.99)] if len(ttfts) > 1 else (ttfts[0] if ttfts else 0),

            avg_tpot=statistics.mean(tpots) if tpots else 0,
            median_tpot=statistics.median(tpots) if tpots else 0,
            p90_tpot=tpots[int(len(tpots) * 0.9)] if tpots else 0,

            avg_latency=statistics.mean(latencies) if latencies else 0,
            median_latency=statistics.median(latencies) if latencies else 0,
            p90_latency=latencies[int(len(latencies) * 0.9)] if latencies else 0,
            p99_latency=latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else (latencies[0] if latencies else 0),

            request_throughput=len(success_results) / total_time if total_time > 0 else 0,
            token_throughput=total_tokens / total_time if total_time > 0 else 0,
            output_token_throughput=total_output_tokens / total_time if total_time > 0 else 0
        )

    def _print_stats(self, stats: ScenarioStats, round_num: int):
        """打印统计结果"""
        print(f"\n📈 统计结果:")
        print(f"  总请求数:       {stats.total_requests}")
        print(f"  成功请求:       {stats.success_requests}")
        print(f"  失败请求:       {stats.failed_requests}")
        print(f"  总耗时:         {stats.total_time:.2f}s")

        print(f"\n⏱️  TTFT (Time to First Token):")
        print(f"  平均:           {stats.avg_ttft*1000:.2f}ms")
        print(f"  中位数:         {stats.median_ttft*1000:.2f}ms")
        print(f"  P90:            {stats.p90_ttft*1000:.2f}ms")
        print(f"  P99:            {stats.p99_ttft*1000:.2f}ms")

        print(f"\n⚡ TPOT (Time per Output Token):")
        print(f"  平均:           {stats.avg_tpot*1000:.2f}ms")
        print(f"  中位数:         {stats.median_tpot*1000:.2f}ms")
        print(f"  P90:            {stats.p90_tpot*1000:.2f}ms")

        print(f"\n🕐 端到端延迟:")
        print(f"  平均:           {stats.avg_latency*1000:.2f}ms")
        print(f"  中位数:         {stats.median_latency*1000:.2f}ms")
        print(f"  P90:            {stats.p90_latency*1000:.2f}ms")
        print(f"  P99:            {stats.p99_latency*1000:.2f}ms")

        print(f"\n🚀 吞吐量:")
        print(f"  请求吞吐量:     {stats.request_throughput:.2f} req/s")
        print(f"  Token 吞吐量:   {stats.token_throughput:.2f} tokens/s")
        print(f"  输出 Token:     {stats.output_token_throughput:.2f} tokens/s")

    def _print_improvement(self, baseline: ScenarioStats, current: ScenarioStats):
        """打印性能提升"""
        print(f"\n🎯 缓存效果 (相比 Round 1):")

        if baseline.avg_ttft > 0:
            ttft_improvement = (1 - current.avg_ttft / baseline.avg_ttft) * 100
            print(f"  TTFT 降低:      {ttft_improvement:+.1f}%")

        if baseline.avg_latency > 0:
            latency_improvement = (1 - current.avg_latency / baseline.avg_latency) * 100
            print(f"  延迟降低:       {latency_improvement:+.1f}%")

        if baseline.request_throughput > 0:
            throughput_improvement = (current.request_throughput / baseline.request_throughput - 1) * 100
            print(f"  吞吐量提升:     {throughput_improvement:+.1f}%")

        # 评价
        if baseline.avg_ttft > 0:
            if ttft_improvement > 60:
                print(f"  ✅ 缓存效果优秀！")
            elif ttft_improvement > 30:
                print(f"  ⚠️  缓存效果一般")
            else:
                print(f"  ❌ 缓存效果不明显")

    def save_results(self, output_dir: str = "test_results"):
        """保存测试结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = self.config['active_model']

        # 保存详细结果
        results_file = f"{output_dir}/non_disagg_{model_name}_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(r) for r in self.results],
                f,
                indent=2,
                ensure_ascii=False
            )

        # 保存统计摘要
        stats_file = f"{output_dir}/non_disagg_{model_name}_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(s) for s in self.scenario_stats],
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
    parser = argparse.ArgumentParser(description="非 PD 分离模式缓存测试")
    parser.add_argument('--config', type=str, default='test_config_large_models.yaml')
    parser.add_argument('--scenarios', type=str, nargs='+',
                       default=['long_context_high_reuse', 'multi_turn_conversation'])
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--concurrency', type=int, help='并发限制')
    parser.add_argument('--output-dir', type=str, default='test_results')

    args = parser.parse_args()

    print("="*80)
    print("🚀 vLLM 非 PD 分离模式 - 缓存效果测试")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        runner = NonDisaggTestRunner(args.config)

        for scenario in args.scenarios:
            await runner.run_scenario(scenario, args.rounds, args.concurrency)

        runner.save_results(args.output_dir)

        print(f"\n{'='*80}")
        print("✅ 所有测试完成!")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
