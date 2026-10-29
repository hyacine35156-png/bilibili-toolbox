#!/usr/bin/env python3
"""v4.5.6: 删除所有页面日志区域的滚动条（Text仍支持鼠标滚轮）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 抢码页面：删除日志滚动条
# ============================================================
old_rush_log = '''        self.rush_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                      insertbackground=COLORS["accent"], font=("Consolas", 9),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.rush_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rush_log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.rush_log_text.yview,
                                         style="Dark.Horizontal.TScrollbar")
        rush_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.rush_log_text.config(yscrollcommand=rush_log_scroll.set)'''

new_rush_log = '''        self.rush_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                      insertbackground=COLORS["accent"], font=("Consolas", 9),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.rush_log_text.pack(fill=tk.BOTH, expand=True)'''

if old_rush_log in content:
    content = content.replace(old_rush_log, new_rush_log)
    print("1. 抢码页面：删除日志滚动条")
else:
    print("1. 未找到抢码页面日志滚动条代码")

# ============================================================
# 2. 弹幕工具页面：删除日志滚动条
# ============================================================
old_danmaku_log = '''        log_scroll = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)'''

new_danmaku_log = '''        self.log_text.pack(fill=tk.BOTH, expand=True)'''

if old_danmaku_log in content:
    content = content.replace(old_danmaku_log, new_danmaku_log)
    print("2. 弹幕工具页面：删除日志滚动条")
else:
    print("2. 未找到弹幕工具页面日志滚动条代码")

# ============================================================
# 3. 日程任务页面：删除日志滚动条
# ============================================================
old_schedule_log = '''        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.schedule_log_text.yview,
                                    style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.schedule_log_text.config(yscrollcommand=log_scroll.set)'''

new_schedule_log = '''        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(fill=tk.BOTH, expand=True)'''

if old_schedule_log in content:
    content = content.replace(old_schedule_log, new_schedule_log)
    print("3. 日程任务页面：删除日志滚动条")
else:
    print("3. 未找到日程任务页面日志滚动条代码")

# ============================================================
# 4. 主程序（看播/其他页面）：删除日志滚动条
# ============================================================
old_main_log = '''        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview, style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)'''

new_main_log = '''        # 日志滚动条已删除，仍支持鼠标滚轮滚动'''

if old_main_log in content:
    content = content.replace(old_main_log, new_main_log)
    print("4. 主程序页面：删除日志滚动条")
else:
    print("4. 未找到主程序页面日志滚动条代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.5"', 'APP_VERSION = "v4.5.6"')
print("5. 版本号已更新到 v4.5.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
