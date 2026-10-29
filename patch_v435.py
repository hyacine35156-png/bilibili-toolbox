#!/usr/bin/env python3
"""v4.3.5: 进一步压缩列宽，去掉上次:前缀"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 任务名称 10→8
old_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
new_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)'''
content = content.replace(old_name, new_name)
print("1. 任务名称 10→8")

# 2. 类型 6→5
old_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=6, anchor=tk.W)'''
new_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=5, anchor=tk.W)'''
content = content.replace(old_type, new_type)
print("2. 类型 6→5")

# 3. 时间 14→10
old_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=14, anchor=tk.W)'''
new_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
content = content.replace(old_time, new_time)
print("3. 时间 14→10")

# 4. 状态 6→5
old_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=6, anchor=tk.W)'''
new_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=5, anchor=tk.W)'''
content = content.replace(old_status, new_status)
print("4. 状态 6→5")

# 5. 上次执行 12→10，去掉"上次:"前缀
old_last = '''            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=12, anchor=tk.W)'''
new_last = '''            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=14, anchor=tk.W)'''
content = content.replace(old_last, new_last)
print("5. 上次执行去掉前缀，宽度12→14")

# 6. 所有列间距 2→0
content = content.replace('padx=(2, 0)', 'padx=(0, 0)')
print("6. 所有列间距 2→0")

# 7. 任务名称间距 2→0
content = content.replace('padx=(2, 0), pady=8', 'padx=(0, 0), pady=8')
print("7. 任务名称间距 2→0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
