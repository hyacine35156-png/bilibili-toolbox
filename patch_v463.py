#!/usr/bin/env python3
"""v4.6.3: 账户管理页面三个按钮改成三排，加大左侧卡片宽度"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 加大左侧账户管理卡片宽度：240 -> 280
# ============================================================
old_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=240)'''

new_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=280)'''

if old_left_width in content:
    content = content.replace(old_left_width, new_left_width)
    print("1. 左侧账户管理卡片宽度: 240 -> 280")
else:
    print("1. 未找到左侧卡片宽度设置")

# ============================================================
# 2. 三个按钮改成三排，每个单独一排
# ============================================================
old_buttons = '''        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=10)

        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=150, height=34).pack(side=tk.LEFT, padx=(0, 4))
        DarkButton(btn_frame, "删除", command=self.delete_account,
                   width=150, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT)

        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 10), padx=12)'''

new_buttons = '''        # 第一排：添加账户
        DarkButton(left_card, "+ 添加账户", command=self.add_account,
                   width=250, height=36).pack(pady=(10, 6), padx=12)

        # 第二排：删除
        DarkButton(left_card, "删除", command=self.delete_account,
                   width=250, height=36, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6), padx=12)

        # 第三排：验证登录
        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 10), padx=12)'''

if old_buttons in content:
    content = content.replace(old_buttons, new_buttons)
    print("2. 三个按钮改成三排：添加账户、删除、验证登录各占一排")
else:
    print("2. 未找到账户管理按钮代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.2"', 'APP_VERSION = "v4.6.3"')
print("3. 版本号已更新到 v4.6.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
