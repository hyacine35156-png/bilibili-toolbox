file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加绝区零3.2的act_id
old_config = '''VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.6": "1ERAzwloghvn7l00",
    "原神7.0": "1ERAzwloghvcpc00",
    "崩坏星穹铁道4.5": "1ERAzwloghvb5600",
}'''

new_config = '''VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.6": "1ERAzwloghvn7l00",
    "原神7.0": "1ERAzwloghvcpc00",
    "崩坏星穹铁道4.5": "1ERAzwloghvb5600",
    "绝区零3.2": "1ERAzwloghvbmi00",
}'''

if old_config in content:
    content = content.replace(old_config, new_config)
    print("✓ 已添加绝区零3.2的act_id: 1ERAzwloghvbmi00")
else:
    print("✗ 未找到VERSION_DEFAULT_ACT_ID配置，可能已被修改")
    # 尝试查找
    import re
    match = re.search(r'VERSION_DEFAULT_ACT_ID\s*=\s*\{[^}]+\}', content)
    if match:
        print("找到的配置:", match.group()[:200])

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
