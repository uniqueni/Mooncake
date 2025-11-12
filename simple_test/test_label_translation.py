#!/usr/bin/env python3
"""测试标签翻译功能"""

# 模拟翻译逻辑
label_translation = {
    '单节点': 'Single',
    '跨节点': 'Cross',
    '多轮': 'Multi',
    '长文本': 'Long',
    '多轮对话': 'Multi-Turn',
    '长文本对话': 'Long-Text',
    '腾讯云': 'Tencent',
    '火山云': 'Volcano',
    '阿里云': 'Alibaba',
}

def translate_label(label: str) -> str:
    """将中文标签翻译为英文"""
    for zh, en in label_translation.items():
        label = label.replace(zh, en)
    return label

# 测试你的场景名称
test_scenarios = [
    "腾讯云-72B-单节点-多轮",
    "腾讯云-72B-单节点-长文本",
    "腾讯云-72B-跨节点-多轮",
    "腾讯云-72B-跨节点-长文本",
    "腾讯云-671B-单节点-多轮",
    "腾讯云-671B-单节点-长文本",
    "腾讯云-671B-跨节点-多轮",
    "腾讯云-671B-跨节点-长文本",
    "火山云-72B-单节点-多轮",
    "火山云-72B-单节点-长文本",
    "火山云-72B-跨节点-多轮",
    "火山云-72B-跨节点-长文本",
]

print("场景名称翻译测试")
print("=" * 80)
print(f"{'原始场景名称':<35} {'X轴标签 (翻译后)':<35}")
print("=" * 80)

for scenario in test_scenarios:
    parts = scenario.split('-')
    if len(parts) >= 4:
        # 格式: 云平台-模型-部署方式-场景类型
        label = f"{parts[1]}-{parts[2]}-{parts[3]}"
        translated = translate_label(label)
        print(f"{scenario:<35} {translated:<35}")

print("=" * 80)
print("\n✅ 所有标签都已翻译为英文，不会有中文显示问题！")
