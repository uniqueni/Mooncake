#!/usr/bin/env python3
"""
PD 分离模式测试脚本

测试 Prefill-Decode 分离架构 + LMCache + Mooncake，重点测量：
- TTFT (Time to First Token) - 包括 Prefill 时间
- TPOT (Time per Output Token) - Decode 阶段
- KV Cache 传输时间
- 吞吐量和延迟
- 缓存命中效果
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
    prompt_length: int
    output_length: int

    # 时间指标
    ttft: Optional[float] = None  # Prefill + KV传输 + 首token生成
    tpot: Optional[float] = None  # Decode 阶段每token时间
    e2e_latency: float = 0.0

    # PD 分离特有指标
    prefill_time: Optional[float] = None  # Prefill 阶段时间（估算）
    kv_transfer_time: Optional[float] = None  # KV Cache 传输时间（估算）
    decode_time: Optional[float] = None  # Decode 阶段时间

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

    # TTFT 统计（包含 Prefill + KV 传输）
    avg_ttft: float = 0.0
    median_ttft: float = 0.0
    p90_ttft: float = 0.0
    p99_ttft: float = 0.0

    # TPOT 统计（Decode 阶段）
    avg_tpot: float = 0.0
    median_tpot: float = 0.0
    p90_tpot: float = 0.0

    # 延迟统计
    avg_latency: float = 0.0
    median_latency: float = 0.0
    p90_latency: float = 0.0
    p99_latency: float = 0.0

    # 吞吐量
    request_throughput: float = 0.0
    token_throughput: float = 0.0
    output_token_throughput: float = 0.0

    # PD 分离特有统计
    avg_prefill_time: float = 0.0
    avg_decode_time: float = 0.0
    cache_hit_rate: float = 0.0  # 估算的缓存命中率


class PDDisaggTestRunner:
    """PD 分离模式测试运行器"""

    def __init__(self, config_path: str = "test_config_large_models.yaml"):
        """初始化测试运行器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 获取活动模型配置
        active_model = self.config['active_model']
        self.model_config = self.config['models'][active_model]
        self.model_name = self.model_config['name']

        # 获取 PD 分离部署配置
        deploy_config = self.config['deployment_modes']['pd_disaggregated']
        if not deploy_config['enabled']:
            raise ValueError("PD 分离模式未启用，请检查配置文件")

        proxy_config = deploy_config['proxy']
        self.proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}/v1"

        self.results: List[RequestMetrics] = []
        self.scenario_stats: List[ScenarioStats] = []

        print(f"✓ PD 分离模式测试配置加载成功")
        print(f"  模型: {self.model_name}")
        print(f"  Proxy: {self.proxy_url}")
        print(f"  Prefiller: {deploy_config['prefiller']['host']}:{deploy_config['prefiller']['port']}")
        print(f"  Decoder: {deploy_config['decoder']['host']}:{deploy_config['decoder']['port']}")

    def _generate_long_document(self, length: int = 16384) -> str:
        """生成指定长度的长文档"""
        base_text = """
        # Distributed Machine Learning Systems: A Comprehensive Guide

        ## 1. Introduction to Distributed Training
        Deep learning models have grown exponentially in size and complexity. Training these massive
        models requires distributed computing across multiple GPUs and nodes. This guide explores
        the fundamental concepts, architectures, and best practices for distributed machine learning.

        ## 2. Data Parallelism
        Data parallelism is the most common approach where different GPUs process different batches
        of data with the same model. Each GPU maintains a complete copy of the model and computes
        gradients independently. These gradients are then aggregated using collective communication
        operations like AllReduce.

        ### 2.1 Synchronous Data Parallelism
        In synchronous data parallelism, all workers wait for gradient aggregation before updating
        model parameters. This ensures consistency but may suffer from stragglers.

        ### 2.2 Asynchronous Data Parallelism
        Asynchronous approaches allow workers to update independently, improving throughput but
        potentially affecting convergence due to stale gradients.

        ## 3. Model Parallelism
        When models are too large to fit in a single GPU, model parallelism distributes different
        parts of the model across multiple devices. This includes:

        ### 3.1 Tensor Parallelism
        Splits individual layers across devices, requiring intensive communication between GPUs.

        ### 3.2 Pipeline Parallelism
        Divides the model into stages, with each stage assigned to different GPUs. Micro-batching
        is used to improve efficiency.

        ## 4. Communication Optimization
        Efficient communication is critical for distributed training performance:
        - Gradient compression and quantization
        - Overlapping communication with computation
        - Hierarchical AllReduce algorithms
        - RDMA and NVLink for high-bandwidth interconnects

        ## 5. Fault Tolerance and Checkpointing
        Distributed systems must handle failures gracefully through:
        - Regular checkpointing of model states
        - Elastic training with dynamic worker pools
        - Automatic failure detection and recovery

        ## 6. Performance Optimization
        Key optimization techniques include:
        - Mixed precision training (FP16/BF16)
        - Gradient accumulation
        - Zero Redundancy Optimizer (ZeRO)
        - FlashAttention and memory-efficient attention

        ## 7. Case Studies

        ### 7.1 Training GPT-3
        GPT-3 with 175B parameters required innovative approaches combining data, tensor, and
        pipeline parallelism across thousands of GPUs.

        ### 7.2 Training Stable Diffusion
        Diffusion models present unique challenges with their iterative denoising process and
        attention mechanisms operating on high-resolution feature maps.

        ## 8. Future Directions
        Emerging trends in distributed ML:
        - Disaggregated architectures separating compute and memory
        - Mixture-of-Experts (MoE) scaling
        - Cross-datacenter training
        - Energy-efficient training methods
        """

        words_needed = int(length / 1.3)
        repeated_text = (base_text * (words_needed // len(base_text.split()) + 1))
        words = repeated_text.split()[:words_needed]

        return ' '.join(words)

    def generate_prompts(self, scenario: str) -> List[Dict[str, Any]]:
        """生成测试提示词"""
        scenario_config = self.config['test_scenarios'][scenario]
        num_requests = scenario_config['num_requests']

        prompts = []

        if scenario == 'long_context_high_reuse':
            long_doc = self._generate_long_document(scenario_config['context_length'])
            questions = scenario_config['questions']

            for i in range(num_requests):
                question = questions[i % len(questions)]
                prompt = f"{long_doc}\n\n基于上述技术文档，请详细回答问题 #{i}: {question}"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': scenario_config['context_length']
                })

        elif scenario == 'code_generation':
            code_context = self._generate_long_document(8192)
            tasks = scenario_config['tasks']

            for i in range(num_requests):
                task = tasks[i % len(tasks)]
                prompt = f"代码库上下文：\n{code_context}\n\n任务 #{i}: {task}\n\n请提供详细的实现方案和代码。"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': 8192
                })

        elif scenario == 'multi_turn_conversation':
            conversation_history = ""
            turns = scenario_config['conversation_turns']

            for i in range(num_requests):
                turn = turns[i % len(turns)]
                conversation_history += f"\n\nUser: {turn}\nAssistant: 这是一个详细的回答，解释了相关概念、原理和应用场景。\n"

                prompt = f"以下是对话历史：{conversation_history}\n\nUser: {turn}\nAssistant:"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': len(conversation_history.split()) * 1.3
                })

        elif scenario == 'batch_processing':
            instruction = "你是一个专业翻译助手。请将以下英文准确翻译成中文：\n" * 100  # 长指令模板

            for i in range(num_requests):
                text = f"Technical document {i}: Distributed systems enable scalable computing..."
                prompt = f"{instruction}\n\nText #{i}:\n{text}"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': 1500
                })

        elif scenario == 'cold_start':
            for i in range(num_requests):
                unique_content = self._generate_long_document(2000)
                prompt = f"独特问题 #{i * 137}:\n{unique_content}\n\n请分析这个问题。"
                prompts.append({
                    'prompt': prompt,
                    'estimated_tokens': 2000
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
            first_token_time = None
            output_tokens = 0

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

            # 估算 PD 分离阶段时间
            # TTFT = Prefill + KV Transfer + First Decode
            # 假设 Prefill ≈ 70% of TTFT, KV Transfer ≈ 20%, First Decode ≈ 10%
            prefill_time = ttft * 0.7 if ttft else None
            kv_transfer_time = ttft * 0.2 if ttft else None

            total_output_time = end_time - first_token_time if first_token_time else e2e_latency
            decode_time = total_output_time
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
                prefill_time=prefill_time,
                kv_transfer_time=kv_transfer_time,
                decode_time=decode_time,
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
        print(f"🧪 PD 分离测试场景: {scenario}")
        print(f"   {self.config['test_scenarios'][scenario]['description']}")
        print(f"{'='*80}")

        client = AsyncOpenAI(base_url=self.proxy_url, api_key="dummy")
        prompts = self.generate_prompts(scenario)

        print(f"生成了 {len(prompts)} 个测试请求")
        print(f"将运行 {num_rounds} 轮测试")

        scenario_stats = []

        for round_num in range(num_rounds):
            print(f"\n{'─'*80}")
            print(f"📊 Round {round_num + 1}/{num_rounds}")
            if round_num == 0:
                print("   🥶 Cold Start - KV Cache 冷启动")
            else:
                print("   🔥 Cache Hit - 测试缓存效果")
            print(f"{'─'*80}")

            round_start = time.time()

            tasks = [
                self.send_request(client, prompt, i, scenario, round_num + 1)
                for i, prompt in enumerate(prompts)
            ]

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

            self.results.extend(results)

            stats = self._calculate_stats(results, scenario, round_num + 1, round_elapsed)
            scenario_stats.append(stats)
            self.scenario_stats.append(stats)

            self._print_stats(stats, round_num)

            if round_num > 0:
                self._print_improvement(scenario_stats[0], stats)

            if round_num < num_rounds - 1:
                wait_time = 5
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

        ttfts = [r.ttft for r in success_results if r.ttft is not None]
        ttfts.sort()

        tpots = [r.tpot for r in success_results if r.tpot is not None]
        tpots.sort()

        latencies = [r.e2e_latency for r in success_results]
        latencies.sort()

        prefill_times = [r.prefill_time for r in success_results if r.prefill_time is not None]
        decode_times = [r.decode_time for r in success_results if r.decode_time is not None]

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

            avg_latency=statistics.mean(latencies),
            median_latency=statistics.median(latencies),
            p90_latency=latencies[int(len(latencies) * 0.9)],
            p99_latency=latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0],

            request_throughput=len(success_results) / total_time if total_time > 0 else 0,
            token_throughput=total_tokens / total_time if total_time > 0 else 0,
            output_token_throughput=total_output_tokens / total_time if total_time > 0 else 0,

            avg_prefill_time=statistics.mean(prefill_times) if prefill_times else 0,
            avg_decode_time=statistics.mean(decode_times) if decode_times else 0,
        )

    def _print_stats(self, stats: ScenarioStats, round_num: int):
        """打印统计结果"""
        print(f"\n📈 统计结果:")
        print(f"  总请求数:         {stats.total_requests}")
        print(f"  成功请求:         {stats.success_requests}")
        print(f"  失败请求:         {stats.failed_requests}")
        print(f"  总耗时:           {stats.total_time:.2f}s")

        print(f"\n⏱️  TTFT (Prefill + KV Transfer + First Token):")
        print(f"  平均:             {stats.avg_ttft*1000:.2f}ms")
        print(f"  中位数:           {stats.median_ttft*1000:.2f}ms")
        print(f"  P90:              {stats.p90_ttft*1000:.2f}ms")
        print(f"  P99:              {stats.p99_ttft*1000:.2f}ms")

        print(f"\n🔄 PD 分离阶段时间（估算）:")
        print(f"  平均 Prefill:     {stats.avg_prefill_time*1000:.2f}ms")
        print(f"  平均 Decode:      {stats.avg_decode_time*1000:.2f}ms")

        print(f"\n⚡ TPOT (Decode 阶段):")
        print(f"  平均:             {stats.avg_tpot*1000:.2f}ms/token")
        print(f"  中位数:           {stats.median_tpot*1000:.2f}ms/token")
        print(f"  P90:              {stats.p90_tpot*1000:.2f}ms/token")

        print(f"\n🕐 端到端延迟:")
        print(f"  平均:             {stats.avg_latency:.2f}s")
        print(f"  中位数:           {stats.median_latency:.2f}s")
        print(f"  P90:              {stats.p90_latency:.2f}s")
        print(f"  P99:              {stats.p99_latency:.2f}s")

        print(f"\n🚀 吞吐量:")
        print(f"  请求吞吐量:       {stats.request_throughput:.2f} req/s")
        print(f"  Token 吞吐量:     {stats.token_throughput:.2f} tokens/s")
        print(f"  输出 Token:       {stats.output_token_throughput:.2f} tokens/s")

    def _print_improvement(self, baseline: ScenarioStats, current: ScenarioStats):
        """打印缓存效果"""
        print(f"\n🎯 PD 分离 + 缓存效果 (相比 Round 1):")

        if baseline.avg_ttft > 0:
            ttft_reduction = (1 - current.avg_ttft / baseline.avg_ttft) * 100
            print(f"  ⚡ TTFT 降低:         {ttft_reduction:+.1f}%")

        if baseline.avg_prefill_time > 0:
            prefill_reduction = (1 - current.avg_prefill_time / baseline.avg_prefill_time) * 100
            print(f"  🔄 Prefill 时间降低:  {prefill_reduction:+.1f}%")

        if baseline.avg_latency > 0:
            latency_reduction = (1 - current.avg_latency / baseline.avg_latency) * 100
            print(f"  📉 延迟降低:         {latency_reduction:+.1f}%")

        if baseline.request_throughput > 0:
            throughput_increase = (current.request_throughput / baseline.request_throughput - 1) * 100
            print(f"  📈 吞吐量提升:       {throughput_increase:+.1f}%")

        # 评价缓存效果
        targets = self.config['performance_test']['targets']['pd_disaggregated']

        if baseline.avg_ttft > 0:
            if ttft_reduction >= targets['cache_hit_ttft_reduction']:
                print(f"\n  ✅ 达到性能目标！TTFT 降低 {ttft_reduction:.1f}% (目标: {targets['cache_hit_ttft_reduction']}%)")
            else:
                print(f"\n  ⚠️  未达到目标。TTFT 降低 {ttft_reduction:.1f}% (目标: {targets['cache_hit_ttft_reduction']}%)")

        if baseline.request_throughput > 0:
            if throughput_increase >= targets['cache_hit_throughput_increase']:
                print(f"  ✅ 达到性能目标！吞吐量提升 {throughput_increase:.1f}% (目标: {targets['cache_hit_throughput_increase']}%)")
            else:
                print(f"  ⚠️  未达到目标。吞吐量提升 {throughput_increase:.1f}% (目标: {targets['cache_hit_throughput_increase']}%)")

    def save_results(self, output_dir: str = "test_results"):
        """保存测试结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = self.config['active_model']

        results_file = f"{output_dir}/pd_disagg_{model_name}_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2, ensure_ascii=False)

        stats_file = f"{output_dir}/pd_disagg_{model_name}_stats_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(s) for s in self.scenario_stats], f, indent=2, ensure_ascii=False)

        print(f"\n💾 结果已保存:")
        print(f"  详细结果: {results_file}")
        print(f"  统计摘要: {stats_file}")

        return results_file, stats_file


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PD 分离模式缓存测试")
    parser.add_argument('--config', type=str, default='test_config_large_models.yaml')
    parser.add_argument('--scenarios', type=str, nargs='+',
                       default=['long_context_high_reuse', 'multi_turn_conversation'])
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--concurrency', type=int, help='并发限制')
    parser.add_argument('--output-dir', type=str, default='test_results')

    args = parser.parse_args()

    print("="*80)
    print("🚀 vLLM PD 分离模式 + LMCache + Mooncake 缓存测试")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        runner = PDDisaggTestRunner(args.config)

        for scenario in args.scenarios:
            await runner.run_scenario(scenario, args.rounds, args.concurrency)

        runner.save_results(args.output_dir)

        print(f"\n{'='*80}")
        print("✅ PD 分离测试完成!")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
