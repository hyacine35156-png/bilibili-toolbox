file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加绝区零3.2更多投稿任务
# 在已有的投稿任务后面添加
old_submit_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥70万", "task_id": "6ERAcwloghva0600", "award": "菲林*1600"},
'''

new_submit_end = '''    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥70万", "task_id": "6ERAcwloghva0600", "award": "菲林*1600"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥100", "task_id": "6ERAcwloghvydm00", "award": "菲林*30"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000", "task_id": "6ERAcwloghvuvr00", "award": "菲林*300"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000的有效投稿≥3", "task_id": "6ERAcwloghva5u00", "award": "菲林*800"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿3天，且累计视频播放≥500", "task_id": "6ERAcwloghvany00", "award": "菲林*150"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿10天，且累计视频播放≥1000", "task_id": "6ERAcwloghvse600", "award": "菲林*300"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿20天，且累计视频播放≥3000", "task_id": "6ERAcwloghvyvy00", "award": "菲林*500"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿30天，且累计视频播放≥6000", "task_id": "6ERAcwloghvy3900", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿35天，且累计视频播放≥50000", "task_id": "6ERAcwloghvsp300", "award": "菲林*1000"},
'''

if old_submit_end in content:
    content = content.replace(old_submit_end, new_submit_end)
    print("✓ 已添加绝区零3.2更多投稿任务（8个）")
else:
    print("✗ 未找到投稿任务结束位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
