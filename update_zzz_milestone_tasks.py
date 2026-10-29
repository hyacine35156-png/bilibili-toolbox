file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 删除之前添加的绝区零3.2抽奖任务
old_zzz_tasks = '''    # ===== 绝区零3.2 =====
    # 全版本 - 抽奖任务
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "每日投递活动话题稿件", "task_id": "6ERAcwloghvse500", "award": "抽奖次数+3"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "每日开播>30分钟", "task_id": "6ERAcwloghvycf00", "award": "抽奖次数+3"},
    {"version": "绝区零3.2", "period": "全版本", "type": "看播里程碑", "name": "每日累计观看直播", "task_id": "6ERAcwloghvyc600", "award": "抽奖次数+1~3"},
    {"version": "绝区零3.2", "period": "全版本", "type": "看播里程碑", "name": "每日累计观看活动视频", "task_id": "6ERAcwloghvyin00", "award": "抽奖次数+1~3"},
    {"version": "绝区零3.2", "period": "全版本", "type": "其他", "name": "首次关注绝区零官号", "task_id": "6ERAcwloghva0300", "award": "抽奖次数+3"},
'''

if old_zzz_tasks in content:
    content = content.replace(old_zzz_tasks, '')
    print("✓ 已删除之前添加的绝区零3.2抽奖任务")
else:
    print("✗ 未找到之前添加的绝区零3.2抽奖任务，可能格式不同")

# 添加绝区零3.2直播里程碑任务
new_zzz_tasks = '''    # ===== 绝区零3.2 =====
    # 全版本 - 直播里程碑任务
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计3天完成开播及互动任务", "task_id": "18ERA1wloghvv9m00", "award": "菲林*360"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计5天完成开播及互动任务", "task_id": "18ERA1wloghvbtf00", "award": "菲林*660"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计10天完成开播及互动任务", "task_id": "18ERA1wloghvv1m00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计20天完成开播及互动任务", "task_id": "18ERA1wloghvbfq00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计30天完成开播及互动任务", "task_id": "18ERA1wloghvc4600", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计35天完成开播及互动任务", "task_id": "18ERA1wloghvc4600", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "直播收获1名舰长", "task_id": "6ERAcwloghvuzk00", "award": "菲林*480"},
'''

# 在ALL_TASKS结束前插入
old_end = '''    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积14天开播", "task_id": "18ERA1wloghvbww00", "award": "星琼*200"},
]'''

new_end = '''    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积14天开播", "task_id": "18ERA1wloghvbww00", "award": "星琼*200"},

''' + new_zzz_tasks + ''']'''

if old_end in content:
    content = content.replace(old_end, new_end)
    print("✓ 已添加绝区零3.2直播里程碑任务")
else:
    print("✗ 未找到ALL_TASKS结束位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
