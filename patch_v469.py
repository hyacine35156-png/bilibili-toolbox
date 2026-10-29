#!/usr/bin/env python3
"""v4.6.9: 加大窗口顶部标题栏、标签切换栏、页面标题字体"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 主窗口顶部标题栏
# ============================================================
# "● B站工具箱" 大标题：14号 bold -> 16号 bold
content = content.replace(
    'tk.Label(title_frame, text="● B站工具箱", bg=COLORS["bg_card"],\n                 fg=COLORS["accent"], font=("微软雅黑", 14, "bold"))',
    'tk.Label(title_frame, text="● B站工具箱", bg=COLORS["bg_card"],\n                 fg=COLORS["accent"], font=("微软雅黑", 16, "bold"))'
)
print("1. 主标题: 14号bold -> 16号bold")

# "弹幕+抢码+定时关机" 副标题：9号 -> 11号
content = content.replace(
    'tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],\n                 fg=COLORS["text_muted"], font=("微软雅黑", 9))',
    'tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],\n                 fg=COLORS["text_muted"], font=("微软雅黑", 11))'
)
print("2. 副标题: 9号 -> 11号")

# 顶部状态"● 未运行"：9号 -> 11号
content = content.replace(
    'self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],\n                                       fg=COLORS["text_muted"], font=("微软雅黑", 9))',
    'self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],\n                                       fg=COLORS["text_muted"], font=("微软雅黑", 11))'
)
print("3. 顶部状态: 9号 -> 11号")

# ============================================================
# 2. 标签切换栏
# ============================================================
# 标签栏高度：44 -> 52
content = content.replace(
    'tab_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=44)',
    'tab_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=52)'
)
print("4. 标签栏高度: 44 -> 52")

# 抢码工具（选中）：10号 bold -> 12号 bold
content = content.replace(
    'self.tab_rush = tk.Label(tab_bar, text="⚡ 抢码工具", bg=COLORS["accent"], fg="#000000",\n                                  font=("微软雅黑", 10, "bold"), padx=20, pady=8, cursor="hand2")',
    'self.tab_rush = tk.Label(tab_bar, text="⚡ 抢码工具", bg=COLORS["accent"], fg="#000000",\n                                  font=("微软雅黑", 12, "bold"), padx=24, pady=10, cursor="hand2")'
)
print("5. 抢码工具标签(选中): 10号bold -> 12号bold")

# 弹幕工具：10号 -> 12号
content = content.replace(
    'self.tab_danmaku = tk.Label(tab_bar, text="💬 弹幕工具", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                     font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")',
    'self.tab_danmaku = tk.Label(tab_bar, text="💬 弹幕工具", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                     font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")'
)
print("6. 弹幕工具标签: 10号 -> 12号")

# 定时关机：10号 -> 12号
content = content.replace(
    'self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")',
    'self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")'
)
print("7. 定时关机标签: 10号 -> 12号")

# 看播任务：10号 -> 12号
content = content.replace(
    'self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                   font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")',
    'self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                   font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")'
)
print("8. 看播任务标签: 10号 -> 12号")

# 日程任务：10号 -> 12号
content = content.replace(
    'self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")',
    'self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],\n                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")'
)
print("9. 日程任务标签: 10号 -> 12号")

# ============================================================
# 3. 抢码工具页面标题
# ============================================================
# "⚡ 自动抢码工具" 标题：13号 bold -> 15号 bold
content = content.replace(
    'tk.Label(header, text="⚡ 自动抢码工具", bg=COLORS["bg_card"],\n                 fg=COLORS["accent"], font=("微软雅黑", 13, "bold"))',
    'tk.Label(header, text="⚡ 自动抢码工具", bg=COLORS["bg_card"],\n                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold"))'
)
print("10. 抢码页面标题: 13号bold -> 15号bold")

# 抢码页面状态"● 未运行"：9号 -> 11号
content = content.replace(
    'self.rush_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],\n                                     fg=COLORS["text_muted"], font=("微软雅黑", 9))',
    'self.rush_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],\n                                     fg=COLORS["text_muted"], font=("微软雅黑", 11))'
)
print("11. 抢码页面状态: 9号 -> 11号")

# ============================================================
# 4. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.8"', 'APP_VERSION = "v4.6.9"')
print("12. 版本号: v4.6.8 -> v4.6.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
