#!/bin/bash
# 生成完整的 12 场景对比报告

set -e

echo "📊 生成 Mooncake KV Cache 综合测试报告"
echo "=========================================="
echo ""

# 检查结果文件是否存在
RESULTS_DIR="results"
if [ ! -d "$RESULTS_DIR" ]; then
    echo "❌ 错误: 找不到 $RESULTS_DIR 目录"
    exit 1
fi

echo "✓ 找到结果目录: $RESULTS_DIR"
echo ""

# 运行报告生成
python3 reports/generate_multi_scenario_report.py \
    --scenario "腾讯云-72B-单节点-多轮" --stats results/tencent_72b_1_conversation.json \
    --scenario "腾讯云-72B-单节点-长文本" --stats results/tencent_72b_1_long_text.json \
    --scenario "腾讯云-72B-跨节点-多轮" --stats results/tencent_72b_2_conversation.json \
    --scenario "腾讯云-72B-跨节点-长文本" --stats results/tencent_72b_2_long_text.json \
    --scenario "腾讯云-671B-单节点-多轮" --stats results/tencent_671b_1_conversation.json \
    --scenario "腾讯云-671B-单节点-长文本" --stats results/tencent_671b_1_long_text.json \
    --scenario "腾讯云-671B-跨节点-多轮" --stats results/tencent_671b_2_conversation.json \
    --scenario "腾讯云-671B-跨节点-长文本" --stats results/tencent_671b_2_long_text.json \
    --scenario "火山云-72B-单节点-多轮" --stats results/vke_72b_1_conversation.json \
    --scenario "火山云-72B-单节点-长文本" --stats results/vke_72b_1_long_text.json \
    --scenario "火山云-72B-跨节点-多轮" --stats results/vke_72b_2_conversation.json \
    --scenario "火山云-72B-跨节点-长文本" --stats results/vke_72b_2_long_text.json \
    --output all_report.md

echo ""
echo "=========================================="
echo "✅ 完成！"
echo ""
echo "📄 报告文件: all_report.md"
echo "📊 图表目录: report_charts/"
echo ""
echo "查看报告:"
echo "  cat all_report.md"
echo "  open all_report.md  # macOS"
echo ""
echo "查看图表:"
echo "  ls -l report_charts/"
echo "  open report_charts/  # macOS"
