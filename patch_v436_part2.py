#!/usr/bin/env python3
"""v4.3.6 part2: 缩短last_run格式，压缩宽度和间距"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改last_run格式和宽度
old = '''            # 上次执行
            last_run = task.get("last_run", "-")
            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=16, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(6, 0))'''

new = '''            # 上次执行
            last_run = task.get("last_run", "-")
            if last_run and last_run != "-":
                try:
                    from datetime import datetime as _dt
                    _parsed = _dt.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    last_run = _parsed.strftime("%m-%d %H:%M")
                except:
                    pass
            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=12, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(4, 0))'''

if old in content:
    content = content.replace(old, new)
    print("1. last_run格式缩短，宽度16→12，间距6→4")
else:
    print("1. 未找到last_run代码块")

# 2. 任务名称宽度10→8，间距6→4
old_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
new_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)'''
content = content.replace(old_name, new_name)
content = content.replace('name_label.pack(side=tk.LEFT, padx=(6, 0), pady=8)',
                          'name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)')
print("2. 任务名称 10→8，间距 6→4")

# 3. 类型宽度7→6，间距6→4
old_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=7, anchor=tk.W)'''
new_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=6, anchor=tk.W)'''
content = content.replace(old_type, new_type)
content = content.replace('type_label.pack(side=tk.LEFT, padx=(6, 0))',
                          'type_label.pack(side=tk.LEFT, padx=(4, 0))')
print("3. 类型 7→6，间距 6→4")

# 4. 时间宽度12→10，间距6→4
old_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)'''
new_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
content = content.replace(old_time, new_time)
content = content.replace('time_label.pack(side=tk.LEFT, padx=(6, 0))',
                          'time_label.pack(side=tk.LEFT, padx=(4, 0))')
print("4. 时间 12→10，间距 6→4")

# 5. 状态宽度8→7，间距6→4
old_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=8, anchor=tk.W)'''
new_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=7, anchor=tk.W)'''
content = content.replace(old_status, new_status)
content = content.replace('status_label.pack(side=tk.LEFT, padx=(6, 0))',
                          'status_label.pack(side=tk.LEFT, padx=(4, 0))')
print("5. 状态 8→7，间距 6→4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
