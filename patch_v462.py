#!/usr/bin/env python3
"""v4.6.2: 弹幕列表头部改成两排布局"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 弹幕列表头部改成两排布局
# ============================================================
old_danmaku_header = '''        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(danmaku_header, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(danmaku_header, "+ 添加", command=self.add_single_danmaku,
                   width=110, height=30, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(danmaku_header, "批量生成", command=self.batch_generate_danmaku,
                   width=150, height=34, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT)
        DarkButton(danmaku_header, "保存列表", command=self.save_danmaku,
                   width=120, height=34, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 4))'''

new_danmaku_header = '''        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))

        # 第一排：标题
        header_row1 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row1.pack(fill=tk.X)
        tk.Label(header_row1, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)

        # 第二排：按钮
        header_row2 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row2.pack(fill=tk.X, pady=(6, 0))
        DarkButton(header_row2, "+ 添加", command=self.add_single_danmaku,
                   width=130, height=36, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(header_row2, "批量生成", command=self.batch_generate_danmaku,
                   width=150, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(header_row2, "保存列表", command=self.save_danmaku,
                   width=140, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))'''

if old_danmaku_header in content:
    content = content.replace(old_danmaku_header, new_danmaku_header)
    print("1. 弹幕列表头部改成两排布局")
else:
    print("1. 未找到弹幕列表头部代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.1"', 'APP_VERSION = "v4.6.2"')
print("2. 版本号已更新到 v4.6.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
