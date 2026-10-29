#!/usr/bin/env python3
"""v5.0.5: 修复定时任务列表对齐问题，加宽任务名称列，长文字自动换行"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 统一表头列宽度（340 -> 550，其他列适当减少）
old_header_width = '''        col_widths = [340, 110, 260, 150, 80, 200]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]'''

new_header_width = '''        col_widths = [550, 110, 220, 130, 80, 180]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]'''

if old_header_width in content:
    content = content.replace(old_header_width, new_header_width)
    print("1. 表头列宽度已统一（任务名称550）")
else:
    print("1. 未找到表头列宽度代码")

# 2. 统一数据行列宽度（420 -> 550，其他列对应减少）
old_row_width = '''            col_widths = [420, 110, 260, 150, 80, 200]'''
new_row_width = '''            col_widths = [550, 110, 220, 130, 80, 180]'''

if old_row_width in content:
    content = content.replace(old_row_width, new_row_width)
    print("2. 数据行列宽度已统一（任务名称550）")
else:
    print("2. 未找到数据行列宽度代码")

# 3. 任务名称Label增加wraplength自动换行，行高从44增加到60
old_name_label = '''            # 任务名称（加版本信息括号）
            task_name = task.get("task_name", "未知任务")
            version = task.get("version", "")
            period = task.get("period", "")
            if version or period:
                version_info = f"{version}{period}" if version and period else (version or period)
                name_text = f"{task_name}（{version_info}）"[:40]
            else:
                name_text = task_name[:30]
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=44)
            col1.pack(side=tk.LEFT, padx=(25, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)'''

new_name_label = '''            # 任务名称（加版本信息括号，长文字自动换行）
            task_name = task.get("task_name", "未知任务")
            version = task.get("version", "")
            period = task.get("period", "")
            if version or period:
                version_info = f"{version}{period}" if version and period else (version or period)
                name_text = f"{task_name}（{version_info}）"
            else:
                name_text = task_name
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=60)
            col1.pack(side=tk.LEFT, padx=(25, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W, wraplength=col_widths[0]-20, justify=tk.LEFT).pack(side=tk.LEFT, padx=8, pady=8)'''

if old_name_label in content:
    content = content.replace(old_name_label, new_name_label)
    print("3. 任务名称Label已修改（自动换行，行高60）")
else:
    print("3. 未找到任务名称Label代码")

# 4. 其他列的行高也从44增加到60，保持一致
old_other_cols = '''            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=44)
            col2.pack(side=tk.LEFT, padx=(18, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=44)
            col3.pack(side=tk.LEFT, padx=(18, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=44)
            col4.pack(side=tk.LEFT, padx=(35, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=44)
            col5.pack(side=tk.LEFT, padx=(18, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=44)
            col6.pack(side=tk.LEFT, padx=(18, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=6)'''

new_other_cols = '''            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=60)
            col2.pack(side=tk.LEFT, padx=(18, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=60)
            col3.pack(side=tk.LEFT, padx=(18, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=60)
            col4.pack(side=tk.LEFT, padx=(35, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=60)
            col5.pack(side=tk.LEFT, padx=(18, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=60)
            col6.pack(side=tk.LEFT, padx=(18, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=14)'''

if old_other_cols in content:
    content = content.replace(old_other_cols, new_other_cols)
    print("4. 其他列行高已统一（44 -> 60）")
else:
    print("4. 未找到其他列代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.4"', 'APP_VERSION = "v5.0.5"')
print("5. 版本号: v5.0.4 -> v5.0.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
