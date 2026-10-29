#!/usr/bin/env python3
"""v4.3.3: 优化任务列表列宽和间距，解决时间被遮挡"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 复选框间距减小
old_check_pack = '''            check_chk.pack(side=tk.LEFT, padx=(4, 2), pady=8)'''
new_check_pack = '''            check_chk.pack(side=tk.LEFT, padx=(4, 0), pady=8)'''
content = content.replace(old_check_pack, new_check_pack)
print("1. 复选框间距减小")

# 2. 任务名称宽度从18减到12，间距减小
old_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=18, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)'''
new_name = '''            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)'''
content = content.replace(old_name, new_name)
print("2. 任务名称宽度18→12")

# 3. 类型宽度从10减到8，间距从10减到4
old_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=10, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(10, 0))'''
new_type = '''            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=8, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(4, 0))'''
content = content.replace(old_type, new_type)
print("3. 类型宽度10→8，间距10→4")

# 4. 时间宽度从8增加到10，间距从10减到4
old_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(10, 0))'''
new_time = '''            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(4, 0))'''
content = content.replace(old_time, new_time)
print("4. 时间宽度8→10，间距10→4")

# 5. 状态宽度从10减到8，间距从10减到4
old_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=10, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(10, 0))'''
new_status = '''            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=8, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(4, 0))'''
content = content.replace(old_status, new_status)
print("5. 状态宽度10→8，间距10→4")

# 6. 上次执行宽度从18减到16，间距从10减到4
old_last = '''            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=18, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(10, 0))'''
new_last = '''            last_label = tk.Label(row_frame, text=f"上次: {last_run}", bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=16, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(4, 0))'''
content = content.replace(old_last, new_last)
print("6. 上次执行宽度18→16，间距10→4")

# 7. 启用/取消按钮间距调整
old_btn_pack = '''            toggle_btn.pack(side=tk.RIGHT, padx=(4, 8), pady=6)'''
new_btn_pack = '''            toggle_btn.pack(side=tk.RIGHT, padx=(4, 4), pady=6)'''
content = content.replace(old_btn_pack, new_btn_pack)
print("7. 按钮间距调整")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
