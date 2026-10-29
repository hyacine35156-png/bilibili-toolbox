#!/usr/bin/env python3
"""v4.3.4: 进一步压缩列宽，时间列加宽"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 任务名称 12→10
old_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)'''
new_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
content = content.replace(old_name, new_name)
print("1. 任务名称 12→10")

# 2. 类型 8→6，间距 4→2
old_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=8, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(4, 0))'''
new_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=6, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(2, 0))'''
content = content.replace(old_type, new_type)
print("2. 类型 8→6，间距 4→2")

# 3. 时间 10→14，间距 4→2，字体加粗
old_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(4, 0))'''
new_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=14, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(2, 0))'''
content = content.replace(old_time, new_time)
print("3. 时间 10→14，间距 4→2")

# 4. 状态 8→6，间距 4→2
old_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=8, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(4, 0))'''
new_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=6, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(2, 0))'''
content = content.replace(old_status, new_status)
print("4. 状态 8→6，间距 4→2")

# 5. 上次执行 16→12，间距 4→2
old_last = '''            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=16, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(4, 0))'''
new_last = '''            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=12, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(2, 0))'''
content = content.replace(old_last, new_last)
print("5. 上次执行 16→12，间距 4→2")

# 6. 任务名称间距 4→2
old_name_pack = '''            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)'''
new_name_pack = '''            name_label.pack(side=tk.LEFT, padx=(2, 0), pady=8)'''
content = content.replace(old_name_pack, new_name_pack)
print("6. 任务名称间距 4→2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
