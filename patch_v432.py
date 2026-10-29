#!/usr/bin/env python3
"""v4.3.2: 去掉复选框选字，启用/取消按钮移到行末尾"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1. 去掉复选框的text="选"
for i, line in enumerate(lines):
    if 'check_chk = tk.Checkbutton(row_frame, text="选"' in line:
        lines[i] = line.replace('text="选", ', '')
        print(f"1. 去掉复选框选字（第{i+1}行）")
        break

# 2. 找到启用/取消按钮的开始和结束行
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "# 启用/取消按钮" in line:
        start_idx = i
    if start_idx and 'toggle_btn.pack(side=tk.LEFT, padx=(4, 4), pady=6)' in line:
        end_idx = i
        break

print(f"2. 找到启用/取消按钮: 第{start_idx+1}行 - 第{end_idx+1}行")

# 保存按钮代码
button_code = lines[start_idx:end_idx+1]

# 删除原来位置的按钮代码
del lines[start_idx:end_idx+1]
print("3. 已删除原位置的按钮代码")

# 重新找到上次执行列的结束行（因为行号变了）
last_run_end = None
for i, line in enumerate(lines):
    if 'last_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))' in line:
        last_run_end = i
        break

print(f"4. 上次执行列结束于第{last_run_end+1}行")

# 在下次执行列后面插入按钮代码，修改pack为side=tk.RIGHT
button_code_str = ''.join(button_code)
button_code_str = button_code_str.replace('toggle_btn.pack(side=tk.LEFT, padx=(4, 4), pady=6)',
                                            'toggle_btn.pack(side=tk.RIGHT, padx=(4, 8), pady=6)')

# 插入到上次执行列后面
lines.insert(last_run_end + 1, button_code_str)
print("5. 按钮代码已移到行末尾（RIGHT对齐）")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
