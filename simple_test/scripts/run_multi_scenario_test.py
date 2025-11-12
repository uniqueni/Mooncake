#!/usr/bin/env python3
"""
多场景批处理测试脚本

完全隔离地运行多个测试场景，场景之间自动清理缓存，最后生成汇总报告。

用法:
    python3 run_multi_scenario_test.py --config multi_scenario_config.yaml
"""

import asyncio
import subprocess
import sys
import time
import json
import yaml
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests


class MultiScenarioTestRunner:
    """多场景测试运行器"""

    def __init__(self, config_path: str):
        """初始化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.test_scenarios = self.config.get('test_scenarios', [])
        self.output_dir = Path(self.config.get('output_dir', 'test_results_multi'))
        self.output_dir.mkdir(exist_ok=True)

        self.clear_cache_between_scenarios = self.config.get('clear_cache_between_scenarios', True)
        self.wait_between_scenarios = self.config.get('wait_between_scenarios', 10)
        self.mooncake_metadata_url = self.config.get('mooncake', {}).get('metadata_server_url')

        self.stats_files = []  # 收集所有场景的 stats 文件
        self.failed_scenarios = []

        print("="*80)
        print("🚀 多场景批处理测试")
        print("="*80)
        print(f"测试场景数: {len(self.test_scenarios)}")
        print(f"输出目录: {self.output_dir}")
        print(f"场景间清理缓存: {'✅' if self.clear_cache_between_scenarios else '❌'}")
        print("="*80)

    def clear_mooncake_cache(self) -> bool:
        """清理 Mooncake 缓存"""
        if not self.mooncake_metadata_url:
            print("⚠️  未配置 Mooncake metadata server URL，跳过缓存清理")
            return False

        try:
            print(f"🧹 清理 Mooncake 缓存...")
            print(f"   Metadata Server: {self.mooncake_metadata_url}")

            # 调用 Mooncake metadata API 清理缓存
            # 注意：这个 API 端点可能需要根据实际 Mooncake 版本调整
            response = requests.post(
                f"{self.mooncake_metadata_url}/clear",
                timeout=30
            )

            if response.status_code == 200:
                print("   ✅ 缓存已清理")
                return True
            else:
                print(f"   ⚠️  清理失败: HTTP {response.status_code}")
                print(f"   响应: {response.text}")
                return False

        except Exception as e:
            print(f"   ⚠️  清理失败: {e}")
            print(f"   提示: 如果 Mooncake 没有提供清理 API，可以手动重启 vLLM 服务")
            return False

    def run_single_scenario(self, scenario: Dict[str, Any]) -> bool:
        """运行单个测试场景"""
        name = scenario['name']
        config_file = scenario['config_file']
        scenario_name = scenario.get('scenario', 'long_context_high_reuse')
        rounds = scenario.get('rounds', 2)

        print(f"\n{'='*80}")
        print(f"🧪 场景: {name}")
        print(f"{'='*80}")
        print(f"配置文件: {config_file}")
        print(f"测试场景: {scenario_name}")
        print(f"测试轮次: {rounds}")
        print(f"{'='*80}\n")

        # 构建命令
        cmd = [
            'python3',
            'test_simple.py',
            '--config', config_file,
            '--scenarios', scenario_name,
            '--rounds', str(rounds),
            '--output-dir', str(self.output_dir)
        ]

        # 添加并发参数（如果配置了）
        if 'concurrency' in scenario:
            cmd.extend(['--concurrency', str(scenario['concurrency'])])

        print(f"📝 执行命令: {' '.join(cmd)}\n")

        # 执行测试
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=False,  # 直接显示输出
                text=True,
                check=True
            )
            elapsed = time.time() - start_time

            print(f"\n✅ 场景完成: {name} (耗时 {elapsed:.1f}s)")

            # 查找生成的 stats 文件
            stats_file = self._find_latest_stats_file()
            if stats_file:
                self.stats_files.append({
                    'name': name,
                    'file': str(stats_file)
                })
                print(f"   Stats 文件: {stats_file}")
            else:
                print(f"   ⚠️  未找到 stats 文件")

            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ 场景失败: {name}")
            print(f"   错误码: {e.returncode}")
            self.failed_scenarios.append(name)
            return False

        except Exception as e:
            print(f"\n❌ 场景异常: {name}")
            print(f"   错误: {e}")
            self.failed_scenarios.append(name)
            return False

    def _find_latest_stats_file(self) -> Optional[Path]:
        """查找最新生成的 stats 文件"""
        stats_files = sorted(
            self.output_dir.glob("*_stats_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return stats_files[0] if stats_files else None

    def generate_summary_report(self) -> bool:
        """生成汇总报告"""
        if not self.stats_files:
            print("\n⚠️  没有可用的测试结果，跳过报告生成")
            return False

        print(f"\n{'='*80}")
        print("📊 生成汇总报告")
        print(f"{'='*80}")

        # 构建 generate_multi_scenario_report.py 命令
        cmd = ['python3', 'generate_multi_scenario_report.py']

        for item in self.stats_files:
            cmd.extend(['--scenario', item['name']])
            cmd.extend(['--stats', item['file']])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"multi_scenario_report_{timestamp}.md"
        chart_dir = self.output_dir / f"multi_scenario_charts_{timestamp}"

        cmd.extend([
            '--output', str(report_file),
            '--chart-dir', str(chart_dir)
        ])

        print(f"\n📝 生成命令: {' '.join(cmd)}\n")

        try:
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                check=True
            )

            print(f"\n✅ 报告已生成:")
            print(f"   报告: {report_file}")
            print(f"   图表: {chart_dir}/")

            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ 报告生成失败: {e}")
            return False

        except Exception as e:
            print(f"\n❌ 报告生成异常: {e}")
            return False

    def run(self):
        """运行所有测试场景"""
        total_scenarios = len(self.test_scenarios)
        success_count = 0

        start_time = time.time()

        for idx, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n{'#'*80}")
            print(f"# 进度: {idx}/{total_scenarios}")
            print(f"{'#'*80}")

            # 场景开始前清理缓存
            if self.clear_cache_between_scenarios and idx > 1:
                print(f"\n{'─'*80}")
                print("🧹 场景间清理")
                print(f"{'─'*80}")
                self.clear_mooncake_cache()
                print(f"⏳ 等待 {self.wait_between_scenarios}s 让系统稳定...")
                time.sleep(self.wait_between_scenarios)

            # 运行场景
            success = self.run_single_scenario(scenario)
            if success:
                success_count += 1

            # 场景间等待
            if idx < total_scenarios:
                wait_time = self.wait_between_scenarios
                print(f"\n⏳ 下一个场景前等待 {wait_time}s...")
                time.sleep(wait_time)

        elapsed = time.time() - start_time

        # 打印总结
        print(f"\n{'='*80}")
        print("📊 测试总结")
        print(f"{'='*80}")
        print(f"总场景数: {total_scenarios}")
        print(f"成功: {success_count}")
        print(f"失败: {len(self.failed_scenarios)}")
        print(f"总耗时: {elapsed/60:.1f} 分钟")

        if self.failed_scenarios:
            print(f"\n❌ 失败场景:")
            for name in self.failed_scenarios:
                print(f"  - {name}")

        # 生成汇总报告
        if success_count > 0:
            self.generate_summary_report()

        print(f"\n{'='*80}")
        if len(self.failed_scenarios) == 0:
            print("✅ 所有测试完成！")
        else:
            print(f"⚠️  部分测试失败 ({len(self.failed_scenarios)}/{total_scenarios})")
        print(f"{'='*80}\n")

        return len(self.failed_scenarios) == 0


def main():
    parser = argparse.ArgumentParser(
        description="多场景批处理测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

1. 使用配置文件运行:
   python3 run_multi_scenario_test.py --config multi_scenario_config.yaml

2. 查看配置文件模板:
   cat multi_scenario_config.yaml

配置文件格式:
  test_scenarios:
    - name: "腾讯云-单机-Qwen2.5-72B"
      config_file: "test_config_tencent_qwen.yaml"
      scenario: "long_context_high_reuse"
      rounds: 2
    - name: "火山云-单机-Deepseek-R1"
      config_file: "test_config_volcano_deepseek.yaml"
      scenario: "long_context_high_reuse"
      rounds: 2
        """
    )
    parser.add_argument('--config', required=True,
                        help='多场景测试配置文件')

    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"❌ 配置文件不存在: {args.config}")
        sys.exit(1)

    try:
        runner = MultiScenarioTestRunner(args.config)
        success = runner.run()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
