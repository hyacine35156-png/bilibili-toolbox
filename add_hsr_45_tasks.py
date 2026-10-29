file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在崩坏星穹铁道4.5任务的末尾添加新任务
old_end = '''    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积14天开播", "task_id": "18ERA1wloghvbww00", "award": "星琼*200"},

    # ===== 绝区零3.2 ====='''

new_end = '''    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积14天开播", "task_id": "18ERA1wloghvbww00", "award": "星琼*200"},
    # 限时任务1 - 高阶投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "限时任务1", "type": "投稿", "name": "累计7天投稿总播≥2000且三连≥30", "task_id": "6ERAcwloghvsal00", "award": "星琼*500"},
    # 限时任务2 - 高阶投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "限时任务2", "type": "投稿", "name": "累计7天投稿总播≥2000且三连≥30", "task_id": "6ERAcwloghvudj00", "award": "星琼*500"},
    # 直播里程碑任务（9月11日-9月27日）
    {"version": "崩坏星穹铁道4.5", "period": "直播里程碑", "type": "直播", "name": "累计3天完成开播及互动任务", "task_id": "18ERA1wloghvbtg00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.5", "period": "直播里程碑", "type": "直播", "name": "累计5天完成开播及互动任务", "task_id": "18ERA1wloghvv0w00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.5", "period": "直播里程碑", "type": "直播", "name": "累计10天完成开播及互动任务", "task_id": "18ERA1wloghvbye00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.5", "period": "直播里程碑", "type": "直播", "name": "累计15天完成开播及互动任务", "task_id": "18ERA1wloghvbr900", "award": "星琼*1000"},
    # 直播特殊任务
    {"version": "崩坏星穹铁道4.5", "period": "直播特殊", "type": "直播", "name": "直播间新增1名舰长", "task_id": "6ERAcwloghvymq00", "award": "星轨通票*3"},
    # 每日直播任务
    {"version": "崩坏星穹铁道4.5", "period": "每日直播", "type": "直播", "name": "【每日】开播满60分钟且有效观看≥15分钟", "task_id": "6ERAcwloghva5j00", "award": "冒险记录*6+遗失碎金*5"},
    {"version": "崩坏星穹铁道4.5", "period": "每日直播", "type": "直播", "name": "【每日】获得礼物≥10电池且弹幕人数≥4人", "task_id": "6ERAcwloghvy4d00", "award": "漫游指南*2+信用点*11111"},

    # ===== 绝区零3.2 ====='''

if old_end in content:
    content = content.replace(old_end, new_end)
    print("✓ 已添加9个崩坏星穹铁道4.5新任务")
else:
    print("✗ 未找到插入位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
