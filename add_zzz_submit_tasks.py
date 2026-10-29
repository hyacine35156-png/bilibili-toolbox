file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加绝区零3.2投稿任务
# 在每日直播任务后面添加投稿任务
old_daily_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日至少1名用户观看≥10分钟", "task_id": "6ERAcwloghvsp000", "award": "丁尼*5000"},
'''

new_daily_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日至少1名用户观看≥10分钟", "task_id": "6ERAcwloghvsp000", "award": "丁尼*5000"},
    # 全版本 - 投稿任务
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "投稿≥4，播放≥400", "task_id": "6ERAcwloghvy3000", "award": "菲林*80"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "投稿≥5，播放≥500", "task_id": "6ERAcwloghva2p00", "award": "原装母带*1"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥15万", "task_id": "6ERAcwloghvstw00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥70万", "task_id": "6ERAcwloghva0600", "award": "菲林*1600"},
'''

if old_daily_end in content:
    content = content.replace(old_daily_end, new_daily_end)
    print("✓ 已添加绝区零3.2投稿任务（4个）")
else:
    print("✗ 未找到每日直播任务结束位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
