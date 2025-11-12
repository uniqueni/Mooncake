#!/bin/bash
# 快速启动多场景测试脚本

set -e

echo "🚀 多场景批处理测试 - 快速启动"
echo "=================================="
echo ""

# 检查配置文件
CONFIG_FILE="multi_scenario_config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件不存在: $CONFIG_FILE"
    echo ""
    echo "请先创建配置文件："
    echo "  cp multi_scenario_config_simple.yaml $CONFIG_FILE"
    echo "  vim $CONFIG_FILE  # 修改配置"
    echo ""
    exit 1
fi

echo "✓ 配置文件: $CONFIG_FILE"
echo ""

# 显示测试场景
echo "📋 测试场景："
grep -A 1 "name:" $CONFIG_FILE | grep "name:" | sed 's/.*name: /  - /'
echo ""

# 询问是否继续
read -p "是否开始测试？(y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消测试"
    exit 0
fi

echo ""
echo "🏃 开始测试..."
echo "=================================="
echo ""

# 运行测试
python3 run_multi_scenario_test.py --config $CONFIG_FILE

echo ""
echo "✅ 测试完成！"
echo ""
echo "📊 查看结果："
echo "  - 报告: ls test_results_multi/*_report_*.md"
echo "  - 图表: ls test_results_multi/*_charts_*/"
echo ""
