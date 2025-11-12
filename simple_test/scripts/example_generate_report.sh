#!/bin/bash
# 多场景测试报告生成示例脚本
#
# 使用方法：
# 1. 根据你的实际测试结果文件修改下面的路径和场景名称
# 2. 运行脚本: bash example_generate_report.sh

set -e

echo "📊 生成多场景测试报告"
echo "======================="

# 定义你的测试场景和对应的统计文件
# 格式: --scenario "场景名称" --stats "统计文件路径"

python3 generate_multi_scenario_report.py \
    --scenario "腾讯云-单机多卡-Qwen2.5-72B" \
    --stats test_results/tencent_single_qwen_stats.json \
    \
    --scenario "腾讯云-跨节点-Qwen2.5-72B" \
    --stats test_results/tencent_cross_qwen_stats.json \
    \
    --scenario "火山云-单机多卡-Qwen2.5-72B" \
    --stats test_results/volcano_single_qwen_stats.json \
    \
    --scenario "腾讯云-单机多卡-Deepseek-R1" \
    --stats test_results/tencent_single_deepseek_stats.json \
    \
    --scenario "腾讯云-跨节点-Deepseek-R1" \
    --stats test_results/tencent_cross_deepseek_stats.json \
    \
    --output final_report.md \
    --chart-dir final_charts

echo ""
echo "✅ 报告生成完成！"
echo "   - 报告文件: final_report.md"
echo "   - 图表目录: final_charts/"
echo ""
echo "📖 查看报告: cat final_report.md"
echo "🖼️  查看图表: ls final_charts/"
