#!/usr/bin/env python3
"""v5.2.4: 调整账户管理页面布局，缩小账户详细信息，扩大直播间管理"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 账户详细信息：固定宽度400，不自动扩展
# ============================================================
old_right_card = '''        # 右侧：账户详细信息
        right_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))'''

new_right_card = '''        # 右侧：账户详细信息
        right_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        right_card.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 8))
        right_card.pack_propagate(False)
        right_card.configure(width=400)'''

if old_right_card in content:
    content = content.replace(old_right_card, new_right_card)
    print("1. 账户详细信息: 固定宽度400，不自动扩展")
else:
    print("1. 未找到账户详细信息代码")

# ============================================================
# 2. 直播间管理：保持自动扩展，获得更多空间
# ============================================================
old_room_card = '''        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))'''

new_room_card = '''        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))'''

if old_room_card in content:
    content = content.replace(old_room_card, new_room_card)
    print("2. 直播间管理: 保持自动扩展，移除左侧间距")
else:
    print("2. 未找到直播间管理代码")

# 版本号
content = content.replace('APP_VERSION = "v5.2.3"', 'APP_VERSION = "v5.2.4"')
print("3. 版本号: v5.2.3 -> v5.2.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
