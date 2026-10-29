#!/usr/bin/env python3
"""v4.3.1最终版：保留多选框，启用/禁用复选框改成按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到"启用/禁用复选框"的行号
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "# 启用/禁用复选框" in line:
        start_idx = i
    if start_idx and 'chk.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))' in line:
        end_idx = i
        break

print(f"找到启用/禁用复选框代码: 第{start_idx+1}行 - 第{end_idx+1}行")

# 替换成按钮
new_code = '''            # 启用/取消按钮
            if task["enabled"]:
                btn_text = "取消"
                btn_bg = COLORS["warning"]
                def toggle_task(t=task):
                    t["enabled"] = False
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"⏸ 已取消日程「{t['name']}」")
            else:
                btn_text = "启用"
                btn_bg = COLORS["success"]
                def toggle_task(t=task):
                    t["enabled"] = True
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"✅ 已启用日程「{t['name']}」")
            toggle_btn = DarkButton(row_frame, btn_text, command=toggle_task,
                                     width=45, height=22, bg_color=btn_bg, text_color="#ffffff")
            toggle_btn.pack(side=tk.LEFT, padx=(4, 4), pady=6)
'''

lines[start_idx:end_idx+1] = [new_code]

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("启用/禁用复选框已替换为启用/取消按钮")

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("语法验证通过")
except py_compile.PyCompileError as e:
    print(f"语法错误: {e}")
