#!/usr/bin/env python3
"""
简化测试脚本 - 直接连接到 OpenAI 兼容接口

适用于已有 Mooncake 和 OpenAI 接口的场景。
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
    """请求指标"""
    request_id: int
    scenario: str
    round_num: int
    mode: str  # "with-cache" 或 "baseline"

    prompt_length: int
    output_length: int

    ttft: Optional[float] = None
    tpot: Optional[float] = None
    e2e_latency: float = 0.0

    success: bool = True
    error: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class RoundStats:
    """轮次统计"""
    scenario: str
    round_num: int
    mode: str
    total_requests: int
    success_requests: int
    total_time: float

    avg_ttft: float = 0.0
    median_ttft: float = 0.0
    p90_ttft: float = 0.0
    p99_ttft: float = 0.0

    avg_tpot: float = 0.0
    median_tpot: float = 0.0

    avg_latency: float = 0.0
    p90_latency: float = 0.0

    request_throughput: float = 0.0
    token_throughput: float = 0.0

    # 跨节点测试信息
    endpoint_url: Optional[str] = None  # 使用的 endpoint URL


class SimpleTestRunner:
    """简化测试运行器"""

    def __init__(self, config_path: str, mode: str = "with-cache"):
        """初始化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.mode = mode  # "with-cache" 或 "baseline"
        self.api_url = self.config['openai_api']['base_url']
        self.model_name = self.config['openai_api']['model_name']
        self.api_key = self.config['openai_api']['api_key']

        # 支持跨节点测试：每轮使用不同的 endpoint
        self.endpoints_per_round = self.config['openai_api'].get('endpoints_per_round', {})

        self.results: List[RequestMetrics] = []
        self.round_stats: List[RoundStats] = []

        print(f"✓ 测试配置加载成功")
        print(f"  模式: {self.mode}")
        print(f"  API URL: {self.api_url}")
        print(f"  模型: {self.model_name}")

        if self.endpoints_per_round:
            print(f"  跨节点测试: 启用")
            for round_num, endpoint in self.endpoints_per_round.items():
                print(f"    Round {round_num}: {endpoint}")

    def _generate_long_doc(self, length: int = 16384) -> str:
        """生成长文档"""
        base = """
        # 分布式机器学习系统综述

        ## 1. 引言
        随着深度学习模型规模的指数级增长，单机训练已无法满足需求。分布式训练成为训练
        大规模模型的必要手段。本文介绍分布式机器学习的核心概念、架构设计和最佳实践。

        ## 2. 数据并行
        数据并行是最常见的分布式训练方式。不同GPU处理不同批次的数据，每个GPU维护完整
        的模型副本，独立计算梯度。梯度通过AllReduce等集合通信操作进行聚合。

        ### 2.1 同步数据并行
        同步数据并行中，所有worker等待梯度聚合后才更新参数。这确保了一致性，但可能
        受到stragglers的影响。

        ### 2.2 异步数据并行
        异步方式允许worker独立更新，提高吞吐量但可能因梯度过时影响收敛。

        ## 3. 模型并行
        当模型太大无法放入单个GPU时，模型并行将模型的不同部分分布到多个设备上。

        ### 3.1 张量并行
        将单个层分割到多个设备，需要设备间密集通信。

        ### 3.2 流水线并行
        将模型分为多个阶段，每个阶段分配到不同GPU。使用micro-batching提高效率。

        ## 4. 通信优化
        高效通信是分布式训练性能的关键：
        - 梯度压缩和量化
        - 计算与通信重叠
        - 分层AllReduce算法
        - RDMA和NVLink高带宽互连

        ## 5. 容错与检查点
        分布式系统必须优雅处理故障：
        - 定期保存模型状态
        - 弹性训练与动态worker池
        - 自动故障检测和恢复

        ## 6. 性能优化
        关键优化技术：
        - 混合精度训练（FP16/BF16）
        - 梯度累积
        - Zero Redundancy Optimizer（ZeRO）
        - FlashAttention和内存高效注意力

        ## 7. 案例研究
        GPT-3（175B参数）的训练需要创新的数据、张量和流水线并行组合，横跨数千GPU。
        """

        words_needed = int(length / 1.3)
        repeated = (base * (words_needed // len(base.split()) + 1))
        return ' '.join(repeated.split()[:words_needed])

    def generate_prompts(self, scenario: str) -> List[Dict[str, Any]]:
        """生成测试提示词"""
        config = self.config['test_scenarios'][scenario]
        num_requests = config['num_requests']

        prompts = []

        if scenario == 'long_context_high_reuse':
            doc = self._generate_long_doc(config['context_length'])
            questions = config['questions']

            for i in range(num_requests):
                q = questions[i % len(questions)]
                prompt = f"{doc}\n\n问题 #{i}: {q}"
                prompts.append({
                    'prompt': prompt,
                    'tokens': config['context_length']
                })

        elif scenario == 'multi_turn_conversation':
            history = ""
            turns = config['conversation_turns']

            for i in range(num_requests):
                turn = turns[i % len(turns)]
                history += f"\n\nUser: {turn}\nAssistant: [详细回答]\n"
                prompt = f"对话历史：{history}\n\nUser: {turn}\nAssistant:"
                prompts.append({
                    'prompt': prompt,
                    'tokens': len(history.split()) * 1.3
                })

        elif scenario == 'code_generation':
            code_ctx = self._generate_long_doc(config['context_length'])
            tasks = config['tasks']

            for i in range(num_requests):
                task = tasks[i % len(tasks)]
                prompt = f"代码库：\n{code_ctx}\n\n任务 #{i}: {task}"
                prompts.append({
                    'prompt': prompt,
                    'tokens': config['context_length']
                })

        elif scenario == 'batch_processing':
            instruction = "你是专业翻译。" * int(config['instruction_length'] / 10)

            for i in range(num_requests):
                text = f"Technical text {i}: Distributed systems..."
                prompt = f"{instruction}\n\n文本 #{i}:\n{text}"
                prompts.append({
                    'prompt': prompt,
                    'tokens': config['instruction_length']
                })

        elif scenario == 'cold_start':
            for i in range(num_requests):
                content = self._generate_long_doc(config['content_length'])
                prompt = f"问题 #{i * 137}:\n{content}\n\n请分析。"
                prompts.append({
                    'prompt': prompt,
                    'tokens': config['content_length']
                })

        return prompts

    async def send_request(
        self,
        client: AsyncOpenAI,
        prompt_data: Dict,
        request_id: int,
        scenario: str,
        round_num: int
    ) -> RequestMetrics:
        """发送请求"""
        prompt = prompt_data['prompt']
        est_tokens = prompt_data['tokens']

        start = time.time()
        first_token_time = None
        output_tokens = 0

        try:
            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config['model']['max_tokens'],
                temperature=self.config['model']['temperature'],
                stream=True,
            )

            async for chunk in stream:
                if first_token_time is None:
                    first_token_time = time.time()
                if chunk.choices and chunk.choices[0].delta.content:
                    output_tokens += 1

            end = time.time()

            ttft = (first_token_time - start) if first_token_time else None
            e2e = end - start
            tpot = ((end - first_token_time) / output_tokens) if first_token_time and output_tokens > 0 else None

            return RequestMetrics(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                mode=self.mode,
                prompt_length=int(est_tokens),
                output_length=output_tokens,
                ttft=ttft,
                tpot=tpot,
                e2e_latency=e2e,
                success=True,
                timestamp=datetime.now().timestamp()
            )

        except Exception as e:
            return RequestMetrics(
                request_id=request_id,
                scenario=scenario,
                round_num=round_num,
                mode=self.mode,
                prompt_length=int(est_tokens),
                output_length=0,
                e2e_latency=time.time() - start,
                success=False,
                error=str(e),
                timestamp=datetime.now().timestamp()
            )

    async def run_scenario(
        self,
        scenario: str,
        num_rounds: int = 2,
        concurrency: Optional[int] = None
    ):
        """运行测试场景"""
        print(f"\n{'='*80}")
        print(f"🧪 场景: {scenario}")
        print(f"   {self.config['test_scenarios'][scenario]['description']}")
        print(f"{'='*80}")

        prompts = self.generate_prompts(scenario)
        print(f"生成 {len(prompts)} 个请求，运行 {num_rounds} 轮")

        for round_num in range(num_rounds):
            print(f"\n{'─'*80}")
            print(f"📊 Round {round_num + 1}/{num_rounds}")
            if round_num == 0:
                print("   🥶 Cold Start")
            else:
                print("   🔥 Cache Hit")

            # 根据轮次选择 endpoint（支持跨节点测试）
            round_api_url = self.endpoints_per_round.get(round_num + 1, self.api_url)
            if round_api_url != self.api_url:
                print(f"   🌐 跨节点测试 - 使用 endpoint: {round_api_url}")
            else:
                print(f"   🖥️  使用 endpoint: {round_api_url}")

            print(f"{'─'*80}")

            # 为每轮创建新的 client（支持不同的 endpoint）
            client = AsyncOpenAI(base_url=round_api_url, api_key=self.api_key)
            round_start = time.time()

            tasks = [
                self.send_request(client, p, i, scenario, round_num + 1)
                for i, p in enumerate(prompts)
            ]

            if concurrency:
                results = []
                for i in range(0, len(tasks), concurrency):
                    batch = await asyncio.gather(*tasks[i:i+concurrency])
                    results.extend(batch)
                    print(f"  完成 {min(i+concurrency, len(tasks))}/{len(tasks)}")
            else:
                results = await asyncio.gather(*tasks)

            elapsed = time.time() - round_start

            self.results.extend(results)
            stats = self._calc_stats(results, scenario, round_num + 1, elapsed, round_api_url)
            self.round_stats.append(stats)

            self._print_stats(stats, round_num)

            if round_num > 0:
                self._print_improvement(self.round_stats[-2], stats)

            if round_num < num_rounds - 1:
                wait = self.config['test_execution'].get('wait_between_rounds', 15)
                print(f"\n等待 {wait}s...")
                await asyncio.sleep(wait)

    def _calc_stats(self, results, scenario, round_num, total_time, endpoint_url=None) -> RoundStats:
        """计算统计"""
        success = [r for r in results if r.success]

        if not success:
            return RoundStats(
                scenario=scenario,
                round_num=round_num,
                mode=self.mode,
                total_requests=len(results),
                success_requests=0,
                total_time=total_time,
                request_throughput=0,
                endpoint_url=endpoint_url
            )

        ttfts = sorted([r.ttft for r in success if r.ttft])
        tpots = sorted([r.tpot for r in success if r.tpot])
        latencies = sorted([r.e2e_latency for r in success])

        total_tokens = sum(r.prompt_length + r.output_length for r in success)

        return RoundStats(
            scenario=scenario,
            round_num=round_num,
            mode=self.mode,
            total_requests=len(results),
            success_requests=len(success),
            total_time=total_time,

            avg_ttft=statistics.mean(ttfts) if ttfts else 0,
            median_ttft=statistics.median(ttfts) if ttfts else 0,
            p90_ttft=ttfts[int(len(ttfts)*0.9)] if ttfts else 0,
            p99_ttft=ttfts[int(len(ttfts)*0.99)] if len(ttfts) > 1 else (ttfts[0] if ttfts else 0),

            avg_tpot=statistics.mean(tpots) if tpots else 0,
            median_tpot=statistics.median(tpots) if tpots else 0,

            avg_latency=statistics.mean(latencies),
            p90_latency=latencies[int(len(latencies)*0.9)],

            request_throughput=len(success) / total_time if total_time > 0 else 0,
            token_throughput=total_tokens / total_time if total_time > 0 else 0
        )

    def _print_stats(self, stats: RoundStats, round_num: int):
        """打印统计"""
        print(f"\n📈 统计:")
        print(f"  请求数: {stats.success_requests}/{stats.total_requests}")
        print(f"  耗时:   {stats.total_time:.2f}s")
        print(f"\n⏱️  TTFT:")
        print(f"  平均:   {stats.avg_ttft*1000:.2f}ms")
        print(f"  中位:   {stats.median_ttft*1000:.2f}ms")
        print(f"  P90:    {stats.p90_ttft*1000:.2f}ms")
        print(f"\n⚡ TPOT:")
        print(f"  平均:   {stats.avg_tpot*1000:.2f}ms/token")
        print(f"\n🚀 吞吐:")
        print(f"  请求:   {stats.request_throughput:.2f} req/s")
        print(f"  Token:  {stats.token_throughput:.2f} tokens/s")

    def _print_improvement(self, baseline: RoundStats, current: RoundStats):
        """打印改善"""
        print(f"\n🎯 缓存效果:")

        if baseline.avg_ttft > 0:
            ttft_imp = (1 - current.avg_ttft / baseline.avg_ttft) * 100
            print(f"  TTFT 降低:    {ttft_imp:+.1f}%")

        if baseline.request_throughput > 0:
            thr_imp = (current.request_throughput / baseline.request_throughput - 1) * 100
            print(f"  吞吐量提升:   {thr_imp:+.1f}%")

        targets = self.config['performance_targets']['cache_hit']

        if baseline.avg_ttft > 0:
            if ttft_imp >= targets['ttft_reduction_percent']:
                print(f"  ✅ 达到目标！（{targets['ttft_reduction_percent']}%）")
            else:
                print(f"  ⚠️  未达目标（{targets['ttft_reduction_percent']}%）")

    def save_results(self, output_dir: str = "test_results"):
        """保存结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_size = self.config['model']['size']

        # 获取场景列表，生成简短的场景标识
        scenarios = list(set([r.scenario for r in self.results]))
        if len(scenarios) == 1:
            scenario_prefix = scenarios[0]
        else:
            scenario_prefix = f"{scenarios[0]}_etc"  # 多场景时只显示第一个

        # 文件名格式: {mode}_{scenario}_{model_size}_results_{timestamp}.json
        results_file = f"{output_dir}/{self.mode}_{scenario_prefix}_{model_size}_results_{ts}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)

        stats_file = f"{output_dir}/{self.mode}_{scenario_prefix}_{model_size}_stats_{ts}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(s) for s in self.round_stats], f, indent=2)

        print(f"\n💾 结果已保存:")
        print(f"  {results_file}")
        print(f"  {stats_file}")

        return results_file, stats_file


async def main():
    parser = argparse.ArgumentParser(description="简化测试脚本")
    parser.add_argument('--config', default='test_config_simple.yaml')
    parser.add_argument('--mode', choices=['with-cache', 'baseline'], default='with-cache')
    parser.add_argument('--scenarios', nargs='+', default=['long_context_high_reuse'])
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--concurrency', type=int)
    parser.add_argument('--output-dir', default='test_results')

    args = parser.parse_args()

    print("="*80)
    print(f"🚀 测试模式: {args.mode}")
    print("="*80)

    try:
        runner = SimpleTestRunner(args.config, args.mode)

        for scenario in args.scenarios:
            await runner.run_scenario(scenario, args.rounds, args.concurrency)

        runner.save_results(args.output_dir)

        print(f"\n{'='*80}")
        print("✅ 测试完成!")
        print(f"{'='*80}")

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
