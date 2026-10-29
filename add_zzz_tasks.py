file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 绝区零3.2任务列表（从活动页面API获取）
zzz_tasks = [
    '    # ===== 绝区零3.2 =====\n',
    '    # 全版本 - 抽奖任务\n',
    '    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "每日投递活动话题稿件", "task_id": "6ERAcwloghvse500", "award": "抽奖次数+3"},\n',
    '    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "每日开播>30分钟", "task_id": "6ERAcwloghvycf00", "award": "抽奖次数+3"},\n',
    '    {"version": "绝区零3.2", "period": "全版本", "type": "看播里程碑", "name": "每日累计观看直播", "task_id": "6ERAcwloghvyc600", "award": "抽奖次数+1~3"},\n',
    '    {"version": "绝区零3.2", "period": "全版本", "type": "看播里程碑", "name": "每日累计观看活动视频", "task_id": "6ERAcwloghvyin00", "award": "抽奖次数+1~3"},\n',
    '    {"version": "绝区零3.2", "period": "全版本", "type": "其他", "name": "首次关注绝区零官号", "task_id": "6ERAcwloghva0300", "award": "抽奖次数+3"},\n',
]

# 在ALL_TASKS结束行（第415行，索引414）之前插入
insert_pos = 414  # 第415行的索引
new_lines = lines[:insert_pos] + zzz_tasks + lines[insert_pos:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✓ 已在第{insert_pos+1}行前插入绝区零3.2的任务")
print(f"✓ 共添加{len(zzz_tasks)}行（含注释）")
print(f"✓ 文件已保存")
