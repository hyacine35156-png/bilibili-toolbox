# -*- coding: utf-8 -*-
file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到调度器代码的开始和结束位置
scheduler_start = None
scheduler_end = None
for i, line in enumerate(lines):
    if '# ===== 任务组调度器' in line:
        scheduler_start = i
        print(f"调度器开始: 第{i+1}行")
    if scheduler_start and i > scheduler_start and '# ===== 第二步：添加任务到当前组' in line:
        scheduler_end = i
        print(f"调度器结束: 第{i}行（下一部分开始前）")
        break

# 找到组内任务列表的结束位置（日志区域开始前）
list_end = None
for i, line in enumerate(lines):
    if i > scheduler_end and 'log_card = tk.Frame(frame' in line and '抢码日志' in lines[i+2] if i+2 < len(lines) else False:
        list_end = i
        print(f"日志区域开始: 第{i+1}行")
        break

# 如果上面的方法没找到，用另一种方式
if list_end is None:
    for i, line in enumerate(lines):
        if i > scheduler_end and '抢码日志（详细模式）' in line:
            list_end = i - 2  # log_card = tk.Frame 在这之前2行
            print(f"日志区域开始（通过标题找到）: 第{list_end+1}行")
            break

print(f"\n调度器代码行数: {scheduler_end - scheduler_start}")
print(f"组内任务列表结束位置: 第{list_end+1}行")

# 提取调度器代码
scheduler_code = lines[scheduler_start:scheduler_end]

# 删除原来的调度器代码
del lines[scheduler_start:scheduler_end]

# 重新计算日志区域的位置（因为删除了代码，位置会变化）
# 调度器代码有 scheduler_end - scheduler_start 行
# 所以日志区域的新位置是 list_end - (scheduler_end - scheduler_start)
new_log_position = list_end - (scheduler_end - scheduler_start)
print(f"删除后日志区域新位置: 第{new_log_position+1}行")

# 在日志区域之前插入调度器代码
for i, line in enumerate(scheduler_code):
    lines.insert(new_log_position + i, line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n调度器代码已移动到组内任务列表之后，日志区域之前！")

# 验证新的顺序
print("\n验证新的UI顺序:")
for i, line in enumerate(lines):
    if any(keyword in line for keyword in ['任务组调度器', '第二步：添加任务', '组内任务列表', '抢码日志（详细模式）']):
        if '#' in line or 'tk.Label' in line:
            print(f"  第{i+1}行: {line.strip()[:60]}")
