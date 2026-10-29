file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修正累计30天的task_id
old_30day = '{"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计30天完成开播及互动任务", "task_id": "18ERA1wloghvc4600", "award": "菲林*1000"}'
new_30day = '{"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计30天完成开播及互动任务", "task_id": "18ERA1wloghvvef00", "award": "菲林*1000"}'

if old_30day in content:
    content = content.replace(old_30day, new_30day)
    print("✓ 已修正累计30天的task_id为 18ERA1wloghvvef00")
else:
    print("✗ 未找到累计30天的任务")

# 2. 添加每日直播任务
# 在绝区零3.2直播里程碑任务后面添加每日直播任务
old_milestone_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "直播收获1名舰长", "task_id": "6ERAcwloghvuzk00", "award": "菲林*480"},
'''

new_milestone_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "直播收获1名舰长", "task_id": "6ERAcwloghvuzk00", "award": "菲林*480"},
    # 全版本 - 每日直播任务
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日开播60分钟", "task_id": "6ERAcwloghvuse00", "award": "丁尼*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日直播间收到电池≥2", "task_id": "6ERAcwloghvyxs00", "award": "音擎能源模块*2"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日直播间弹幕≥10条", "task_id": "6ERAcwloghvabs00", "award": "资深调查员记录*2"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日至少1名用户观看≥10分钟", "task_id": "6ERAcwloghvsp000", "award": "丁尼*5000"},
'''

if old_milestone_end in content:
    content = content.replace(old_milestone_end, new_milestone_end)
    print("✓ 已添加每日直播任务（4个）")
else:
    print("✗ 未找到直播里程碑任务结束位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
