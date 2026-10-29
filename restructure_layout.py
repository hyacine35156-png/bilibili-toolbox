# -*- coding: utf-8 -*-
file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. 在组内任务列表之前（第3150行，索引3149）插入主内容容器和左右容器
main_container_code = [
    '\n',
    '        # ===== 主内容区域：左边任务列表+控制+调度器，右边日志 =====\n',
    '        main_content = tk.Frame(frame, bg=COLORS["bg_dark"])\n',
    '        main_content.pack(fill=tk.BOTH, expand=True)\n',
    '\n',
    '        # 左边容器：组内任务 + 启动按钮 + 调度器\n',
    '        left_container = tk.Frame(main_content, bg=COLORS["bg_dark"])\n',
    '        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8))\n',
    '\n',
    '        # 右边容器：日志区域（占据整个高度）\n',
    '        right_container = tk.Frame(main_content, bg=COLORS["bg_dark"])\n',
    '        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)\n',
    '\n',
]

# 在第3150行（索引3149）之前插入
insert_pos = 3149
for i, line in enumerate(main_container_code):
    lines.insert(insert_pos + i, line)

print(f"已在第{insert_pos+1}行前插入主内容容器和左右容器")

# 重新计算位置（因为插入了14行）
offset = len(main_container_code)

# 2. 修改组内任务列表的父容器：从frame改成left_container
# 组内任务列表定义在原来的3151行左右，现在是3151+offset
list_card_pos = None
for i in range(insert_pos + offset, len(lines)):
    if 'list_card = tk.Frame(frame,' in lines[i]:
        list_card_pos = i
        lines[i] = lines[i].replace('tk.Frame(frame,', 'tk.Frame(left_container,')
        print(f"第{i+1}行: 已修改组内任务列表父容器为left_container")
        break

# 3. 修改启动按钮容器的父容器：从frame改成left_container
ctrl_card_pos = None
for i in range(insert_pos + offset, len(lines)):
    if 'ctrl_card = tk.Frame(frame,' in lines[i]:
        ctrl_card_pos = i
        lines[i] = lines[i].replace('tk.Frame(frame,', 'tk.Frame(left_container,')
        print(f"第{i+1}行: 已修改启动按钮容器父容器为left_container")
        break

# 4. 删除底部容器的创建和注释（因为不再需要了）
# 找到底部容器的注释和创建
bottom_start = None
bottom_end = None
for i in range(insert_pos + offset, len(lines)):
    if '# ===== 底部区域：左边调度器，右边日志 =====' in lines[i]:
        bottom_start = i
    if bottom_start and 'bottom_container.pack(' in lines[i]:
        bottom_end = i + 1  # 包含pack这一行
        print(f"删除底部容器：第{bottom_start+1}行到第{bottom_end}行")
        break

if bottom_start and bottom_end:
    del lines[bottom_start:bottom_end]
    # 删除后，后面的行号会变化，但是我们已经找到了调度器和日志区的位置，需要重新查找

# 5. 修改调度器的父容器：从bottom_container改成left_container
scheduler_pos = None
for i in range(insert_pos + offset, len(lines)):
    if 'scheduler_card = tk.Frame(bottom_container,' in lines[i]:
        scheduler_pos = i
        lines[i] = lines[i].replace('tk.Frame(bottom_container,', 'tk.Frame(left_container,')
        print(f"第{i+1}行: 已修改调度器父容器为left_container")
        break

# 6. 修改日志区的父容器：从bottom_container改成right_container
log_pos = None
for i in range(insert_pos + offset, len(lines)):
    if 'log_card = tk.Frame(bottom_container,' in lines[i]:
        log_pos = i
        lines[i] = lines[i].replace('tk.Frame(bottom_container,', 'tk.Frame(right_container,')
        print(f"第{i+1}行: 已修改日志区父容器为right_container")
        break

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n布局重构完成！")
print("  - 左边容器：组内任务列表 + 启动按钮 + 调度器")
print("  - 右边容器：日志区域（占据整个高度）")
