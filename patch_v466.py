#!/usr/bin/env python3
"""v4.6.6: 加大抢码工具定时任务列表表格字体"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 表头字体：9号 -> 11号
# ============================================================
old_header_font = 'font=("微软雅黑", 9, "bold")'
new_header_font = 'font=("微软雅黑", 11, "bold")'
header_count = content.count(old_header_font)
content = content.replace(old_header_font, new_header_font)
print(f"1. 表头字体: 9号 -> 11号 (共{header_count}处)")

# ============================================================
# 2. 数据行任务名称字体：8号 -> 10号
# ============================================================
old_name_font = '''tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 8), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=3)'''
new_name_font = '''tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)'''
if old_name_font in content:
    content = content.replace(old_name_font, new_name_font)
    print("2. 数据行任务名称字体: 8号 -> 10号")
else:
    print("2. 未找到数据行任务名称字体代码")

# ============================================================
# 3. 数据行领取时间字体：8号bold -> 10号bold
# ============================================================
old_time_font = '''tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 8, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_time_font = '''tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
if old_time_font in content:
    content = content.replace(old_time_font, new_time_font)
    print("3. 数据行领取时间字体: 8号bold -> 10号bold")
else:
    print("3. 未找到数据行领取时间字体代码")

# ============================================================
# 4. 数据行时长/间隔字体：8号 -> 10号
# ============================================================
old_dur_font = '''tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 8), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_dur_font = '''tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
if old_dur_font in content:
    content = content.replace(old_dur_font, new_dur_font)
    print("4. 数据行时长/间隔字体: 8号 -> 10号")
else:
    print("4. 未找到数据行时长/间隔字体代码")

# ============================================================
# 5. 数据行账户字体：8号 -> 10号
# ============================================================
old_acc_font = '''tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 8), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_acc_font = '''tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
if old_acc_font in content:
    content = content.replace(old_acc_font, new_acc_font)
    print("5. 数据行账户字体: 8号 -> 10号")
else:
    print("5. 未找到数据行账户字体代码")

# ============================================================
# 6. 数据行状态字体：8号bold -> 10号bold
# ============================================================
old_status_font = '''tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 8, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
new_status_font = '''tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))'''
if old_status_font in content:
    content = content.replace(old_status_font, new_status_font)
    print("6. 数据行状态字体: 8号bold -> 10号bold")
else:
    print("6. 未找到数据行状态字体代码")

# ============================================================
# 7. 操作按钮高度：28 -> 34
# ============================================================
old_btn_height = 'width=80, height=28'
new_btn_height = 'width=90, height=34'
btn_count = content.count(old_btn_height)
content = content.replace(old_btn_height, new_btn_height)
print(f"7. 操作按钮: 80x28 -> 90x34 (共{btn_count}处)")

# ============================================================
# 8. 空提示字体：9号 -> 10号
# ============================================================
old_empty_font = '''tk.Label(self.schedule_list_frame, text="暂无定时任务，设置好参数后点击「+ 添加当前设置」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(pady=10)'''
new_empty_font = '''tk.Label(self.schedule_list_frame, text="暂无定时任务，设置好参数后点击「+ 添加当前设置」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=10)'''
if old_empty_font in content:
    content = content.replace(old_empty_font, new_empty_font)
    print("8. 空提示字体: 9号 -> 10号")
else:
    print("8. 未找到空提示字体代码")

# ============================================================
# 9. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.5"', 'APP_VERSION = "v4.6.6"')
print("9. 版本号: v4.6.5 -> v4.6.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
