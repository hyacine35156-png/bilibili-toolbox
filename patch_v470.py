#!/usr/bin/env python3
"""v4.7.0: 调整定时任务列表表格列宽和间距，避免文字截断"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 表头列宽和间距调整
# ============================================================
old_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=28, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''

new_header = '''        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=36, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold"), width=22, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("1. 表头列宽和间距已调整")
else:
    print("1. 未找到表头代码")

# ============================================================
# 2. 数据行列宽和间距调整
# ============================================================
# 任务名称
old_name = '''            name_text = task.get("task_name", "未知任务")[:28]
            tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)'''
new_name = '''            name_text = task.get("task_name", "未知任务")[:36]
            tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), width=38, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0), pady=6)'''
if old_name in content:
    content = content.replace(old_name, new_name)
    print("2. 任务名称列宽: 30->38, 截断: 28->36, 间距: 8->12")
else:
    print("2. 未找到任务名称代码")

# 领取时间
old_time = '''            tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_time = '''            tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''
if old_time in content:
    content = content.replace(old_time, new_time)
    print("3. 领取时间列宽: 12->14, 间距: 8->12")
else:
    print("3. 未找到领取时间代码")

# 时长/间隔
old_dur = '''            tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_dur = '''            tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''
if old_dur in content:
    content = content.replace(old_dur, new_dur)
    print("4. 时长/间隔列宽: 16->18, 间距: 8->12")
else:
    print("4. 未找到时长/间隔代码")

# 账户
old_acc = '''            tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_acc = '''            tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''
if old_acc in content:
    content = content.replace(old_acc, new_acc)
    print("5. 账户列宽: 15->18, 间距: 8->12")
else:
    print("5. 未找到账户代码")

# 状态
old_status = '''            tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_status = '''            tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(12, 0))'''
if old_status in content:
    content = content.replace(old_status, new_status)
    print("6. 状态列间距: 8->12")
else:
    print("6. 未找到状态代码")

# 操作按钮框架间距
old_btn_frame = '''            btn_frame = tk.Frame(row_frame, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=(8, 0))'''
new_btn_frame = '''            btn_frame = tk.Frame(row_frame, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=(12, 0))'''
if old_btn_frame in content:
    content = content.replace(old_btn_frame, new_btn_frame)
    print("7. 操作按钮间距: 8->12")
else:
    print("7. 未找到操作按钮代码")

# ============================================================
# 3. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.9"', 'APP_VERSION = "v4.7.0"')
print("8. 版本号: v4.6.9 -> v4.7.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
