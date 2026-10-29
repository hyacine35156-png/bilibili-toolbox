# -*- coding: utf-8 -*-
file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. 缩小启动按钮
for i, line in enumerate(lines):
    if 'nm_start_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=6)' in line:
        lines[i] = line.replace('ipadx=20, ipady=6', 'ipadx=12, ipady=3')
        print(f"第{i+1}行: 缩小启动按钮")
    if 'nm_stop_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=6)' in line:
        lines[i] = line.replace('ipadx=20, ipady=6', 'ipadx=12, ipady=3')
        print(f"第{i+1}行: 缩小停止按钮")

# 2. 在调度器之前插入底部容器
scheduler_start = None
for i, line in enumerate(lines):
    if '# ===== 任务组调度器' in line:
        scheduler_start = i
        print(f"调度器开始: 第{i+1}行")
        break

# 在调度器之前插入底部容器的开始
bottom_container_start = [
    '\n',
    '        # ===== 底部区域：左边调度器，右边日志 =====\n',
    '        bottom_container = tk.Frame(frame, bg=COLORS["bg_dark"])\n',
    '        bottom_container.pack(fill=tk.BOTH, expand=True, pady=(0, 0))\n',
    '\n',
]

for j, line in enumerate(bottom_container_start):
    lines.insert(scheduler_start + j, line)

print("已插入底部容器开始")

# 重新计算调度器的位置（因为插入了6行）
scheduler_start += len(bottom_container_start)

# 3. 修改调度器的pack方式：从fill=tk.X改成side=tk.LEFT，设置宽度
for i in range(scheduler_start, scheduler_start + 20):
    if i < len(lines) and 'scheduler_card.pack(fill=tk.X, pady=(0, 8))' in lines[i]:
        lines[i] = '        scheduler_card.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8), pady=(0, 0))\n'
        # 设置调度器的宽度
        lines.insert(i+1, '        scheduler_card.config(width=450)\n')
        print(f"第{i+1}行: 修改调度器pack方式为左侧")
        break

# 4. 修改日志区的pack方式：从fill=tk.BOTH, expand=True改成side=tk.RIGHT, expand=True
log_start = None
for i, line in enumerate(lines):
    if 'log_card = tk.Frame(frame, bg=COLORS["bg_card"]' in line and '抢码日志' in lines[i+2] if i+2 < len(lines) else False:
        log_start = i
        print(f"日志区开始: 第{i+1}行")
        break

if log_start:
    for i in range(log_start, log_start + 10):
        if i < len(lines) and 'log_card.pack(fill=tk.BOTH, expand=True)' in lines[i]:
            lines[i] = '        log_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)\n'
            print(f"第{i+1}行: 修改日志区pack方式为右侧")
            break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nUI布局修改完成！")
print("  - 启动按钮已缩小")
print("  - 底部区域改为左右分栏：左边调度器(450px)，右边日志区")
