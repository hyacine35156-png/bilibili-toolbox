#!/usr/bin/env python3
"""v4.4.2: 修复弹幕页面布局 - 日志区域加大 + 启动停止按钮可见"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 弹幕列表卡片：从 expand=True 改为不expand，给日志和按钮腾空间
# ============================================================
old_danmaku_card = '''        # 弹幕列表卡片
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))'''

new_danmaku_card = '''        # 弹幕列表卡片（占据主要空间，但限制最大比例）
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))'''

# 这个不需要改，保持expand=True

# ============================================================
# 2. 日志卡片：去掉固定高度限制，改为合理的最小高度
# ============================================================
old_log_card = '''        # 日志卡片（设置最小高度220px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=220)'''

new_log_card = '''        # 日志卡片（固定高度180px，确保能显示多行日志）
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(6, 0))
        log_card.pack_propagate(False)
        log_card.configure(height=180)'''

if old_log_card in content:
    content = content.replace(old_log_card, new_log_card)
    print("1. 日志卡片改为固定高度180px，不再expand")
else:
    print("1. 未找到日志卡片代码")

# ============================================================
# 3. 控制栏（启动/停止按钮）：确保在日志下方，固定高度
# ============================================================
old_ctrl = '''        # 底部控制栏按钮（移到弹幕页面内部，只在弹幕页显示）
        # 在日志卡片下方添加控制栏
        danmaku_ctrl = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X, pady=(6, 0))

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.X, padx=15, pady=10)'''

new_ctrl = '''        # 底部控制栏按钮（移到弹幕页面内部，只在弹幕页显示）
        # 在日志卡片下方添加控制栏，固定高度
        danmaku_ctrl = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X, pady=(6, 0))
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=60)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15)'''

if old_ctrl in content:
    content = content.replace(old_ctrl, new_ctrl)
    print("2. 控制栏设置固定高度60px")
else:
    print("2. 未找到控制栏代码")

# ============================================================
# 4. 调整右侧区域整体布局：确保所有元素都能显示
# ============================================================
# 找到right区域的创建代码
old_right = '''        # 右侧：设置+弹幕列表+日志
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)'''

# 这个不需要改

# ============================================================
# 5. 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.4.1"', 'APP_VERSION = "v4.4.2"')
print("3. 版本号已更新到 v4.4.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
