#!/usr/bin/env python3
"""v4.3.6: 重新设计合理列宽和间距，缩短时间格式"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 任务名称 8→10，间距 0→6
old_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)'''
new_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
content = content.replace(old_name, new_name)
print("1. 任务名称 8→10")

old_name_pack = '''            name_label.pack(side=tk.LEFT, padx=(0, 0), pady=8)'''
new_name_pack = '''            name_label.pack(side=tk.LEFT, padx=(6, 0), pady=8)'''
content = content.replace(old_name_pack, new_name_pack)
print("   任务名称间距 0→6")

# 2. 类型 5→7，间距 0→6
old_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=5, anchor=tk.W)'''
new_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=7, anchor=tk.W)'''
content = content.replace(old_type, new_type)
print("2. 类型 5→7")

old_type_pack = '''            type_label.pack(side=tk.LEFT, padx=(0, 0))'''
new_type_pack = '''            type_label.pack(side=tk.LEFT, padx=(6, 0))'''
content = content.replace(old_type_pack, new_type_pack)
print("   类型间距 0→6")

# 3. 时间 10→12，间距 0→6
old_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)'''
new_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)'''
content = content.replace(old_time, new_time)
print("3. 时间 10→12")

old_time_pack = '''            time_label.pack(side=tk.LEFT, padx=(0, 0))'''
new_time_pack = '''            time_label.pack(side=tk.LEFT, padx=(6, 0))'''
content = content.replace(old_time_pack, new_time_pack)
print("   时间间距 0→6")

# 4. 状态 5→8，间距 0→6
old_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=5, anchor=tk.W)'''
new_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=8, anchor=tk.W)'''
content = content.replace(old_status, new_status)
print("4. 状态 5→8")

old_status_pack = '''            status_label.pack(side=tk.LEFT, padx=(0, 0))'''
new_status_pack = '''            status_label.pack(side=tk.LEFT, padx=(6, 0))'''
content = content.replace(old_status_pack, new_status_pack)
print("   状态间距 0→6")

# 5. 上次执行 14→16，间距 0→6
old_last = '''            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=14, anchor=tk.W)'''
new_last = '''            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=16, anchor=tk.W)'''
content = content.replace(old_last, new_last)
print("5. 上次执行 14→16")

old_last_pack = '''            last_label.pack(side=tk.LEFT, padx=(0, 0))'''
new_last_pack = '''            last_label.pack(side=tk.LEFT, padx=(6, 0))'''
content = content.replace(old_last_pack, new_last_pack)
print("   上次执行间距 0→6")

# 6. 缩短上次执行时间格式：找到last_run的赋值，改为MM-DD HH:MM
# 先找到原来的格式
old_last_run_format = '''            last_run = task.get("last_run", "未执行")
            if last_run and last_run != "未执行":
                try:
                    dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    last_run = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass'''

# 如果上面的格式不存在，尝试找其他格式
if old_last_run_format not in content:
    # 搜索last_run相关代码
    import re
    matches = list(re.finditer(r'last_run.*=.*', content))
    for m in matches[:5]:
        print(f"   找到last_run代码: {m.group()[:80]}")

# 尝试替换为缩短格式
new_last_run_format = '''            last_run = task.get("last_run", "未执行")
            if last_run and last_run != "未执行":
                try:
                    dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    last_run = dt.strftime("%m-%d %H:%M")
                except:
                    pass'''

if old_last_run_format in content:
    content = content.replace(old_last_run_format, new_last_run_format)
    print("6. 上次执行时间格式缩短为 MM-DD HH:MM")
else:
    print("6. 未找到上次执行时间格式代码，跳过")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
