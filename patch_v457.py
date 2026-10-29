#!/usr/bin/env python3
"""v4.5.7: 加大按钮面积和抢码日志栏高度"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 全局调大DarkButton默认尺寸和字体
# ============================================================
old_darkbutton_init = '''    def __init__(self, parent, text, command=None, width=120, height=36,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):'''

new_darkbutton_init = '''    def __init__(self, parent, text, command=None, width=140, height=40,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):'''

if old_darkbutton_init in content:
    content = content.replace(old_darkbutton_init, new_darkbutton_init)
    print("1. DarkButton默认尺寸: 120x36 -> 140x40")
else:
    print("1. 未找到DarkButton初始化代码")

# 调大按钮字体
old_button_font = '''        self.create_text(self.width//2, self.height//2, text=self.text, fill=self.text_color,
                         font=("微软雅黑", 10, "bold"))'''

new_button_font = '''        self.create_text(self.width//2, self.height//2, text=self.text, fill=self.text_color,
                         font=("微软雅黑", 11, "bold"))'''

if old_button_font in content:
    content = content.replace(old_button_font, new_button_font)
    print("   按钮字体: 10号 -> 11号")
else:
    print("   未找到按钮字体代码")

# ============================================================
# 2. 抢码页面主按钮从100x32加大到120x36
# ============================================================
content = content.replace('width=100, height=32, bg_color="#444466"', 'width=120, height=36, bg_color="#444466"')
content = content.replace('width=100, height=32, bg_color="#ff6b35"', 'width=120, height=36, bg_color="#ff6b35"')
content = content.replace('width=100, height=32, bg_color="#e74c3c"', 'width=120, height=36, bg_color="#e74c3c"')
content = content.replace('width=100, height=32, bg_color="#9b59b6"', 'width=120, height=36, bg_color="#9b59b6"')
content = content.replace('width=80, height=32, bg_color=COLORS["danger"]', 'width=100, height=36, bg_color=COLORS["danger"]')
print("2. 抢码页面主按钮: 100x32 -> 120x36")

# ============================================================
# 3. 抢码页面定时任务列表按钮从110x26加大到120x30
# ============================================================
content = content.replace('width=110, height=26, bg_color=COLORS["accent"]', 'width=120, height=30, bg_color=COLORS["accent"]')
content = content.replace('width=80, height=26, bg_color=COLORS["success"]', 'width=90, height=30, bg_color=COLORS["success"]')
content = content.replace('width=80, height=26, bg_color=COLORS["danger"]', 'width=90, height=30, bg_color=COLORS["danger"]')
print("3. 抢码定时任务列表按钮加大")

# ============================================================
# 4. 抢码日志栏设置最小高度（height=15行）
# ============================================================
old_rush_log_text = '''        self.rush_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                      insertbackground=COLORS["accent"], font=("Consolas", 9),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.rush_log_text.pack(fill=tk.BOTH, expand=True)'''

new_rush_log_text = '''        self.rush_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                      insertbackground=COLORS["accent"], font=("Consolas", 10),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.rush_log_text.pack(fill=tk.BOTH, expand=True)'''

if old_rush_log_text in content:
    content = content.replace(old_rush_log_text, new_rush_log_text)
    print("4. 抢码日志栏: 字体9->10号, 设置最小高度15行")
else:
    print("4. 未找到抢码日志Text代码")

# ============================================================
# 5. 日程页面按钮从70x32/90x28加大
# ============================================================
content = content.replace('width=70, height=32, bg_color="#3498db"', 'width=80, height=36, bg_color="#3498db"')
content = content.replace('width=70, height=32, bg_color=COLORS["success"]', 'width=80, height=36, bg_color=COLORS["success"]')
content = content.replace('width=70, height=32, bg_color="#9b59b6"', 'width=80, height=36, bg_color="#9b59b6"')
content = content.replace('width=100, height=32, bg_color=COLORS["danger"]', 'width=110, height=36, bg_color=COLORS["danger"]')
content = content.replace('width=100, height=32, bg_color="#e67e22"', 'width=110, height=36, bg_color="#e67e22"')
content = content.replace('width=90, height=28, bg_color="#27ae60"', 'width=100, height=32, bg_color="#27ae60"')
content = content.replace('width=90, height=28, bg_color="#3498db"', 'width=100, height=32, bg_color="#3498db"')
content = content.replace('width=90, height=28, bg_color=COLORS["danger"]', 'width=100, height=32, bg_color=COLORS["danger"]')
print("5. 日程页面按钮加大")

# ============================================================
# 6. 看播页面按钮从120x32加大到130x36
# ============================================================
content = content.replace('width=120, height=32, bg_color=COLORS["success"]', 'width=130, height=36, bg_color=COLORS["success"]')
content = content.replace('width=120, height=32, bg_color=COLORS["danger"]', 'width=130, height=36, bg_color=COLORS["danger"]')
print("6. 看播页面按钮加大")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.6"', 'APP_VERSION = "v4.5.7"')
print("7. 版本号已更新到 v4.5.7")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
