#!/usr/bin/env python3
"""v5.0.3: 删除看播任务页面多余的空日志区域"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 删除底部固定的空日志区域（bottom_container + log_card）
old_log = '''        # ===== 底部容器：日志 + 控制栏（先pack到BOTTOM，确保固定在窗口最底部）=====
        bottom_container = tk.Frame(right, bg=COLORS["bg_dark"])
        bottom_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        # 日志卡片（固定高度160px）
        log_card = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        log_card.pack_propagate(False)
        log_card.configure(height=160)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 设置卡片'''

new_log = '''        # 设置卡片'''

if old_log in content:
    content = content.replace(old_log, new_log)
    print("1. 已删除看播任务页面底部多余的空日志区域")
else:
    print("1. 未找到目标代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.2"', 'APP_VERSION = "v5.0.3"')
print("2. 版本号: v5.0.2 -> v5.0.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
