#!/usr/bin/env python3
"""v5.2.1: 修复WatchLiveFrame缺少room_mgr属性的错误"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修改WatchLiveFrame.__init__，添加room_mgr参数
# ============================================================
old_init = '''    def __init__(self, parent, account_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr'''

new_init = '''    def __init__(self, parent, account_mgr, room_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("1. WatchLiveFrame.__init__已添加room_mgr参数")
else:
    print("1. 未找到WatchLiveFrame.__init__代码")

# ============================================================
# 2. 修改创建WatchLiveFrame的地方，传入room_mgr
# ============================================================
old_create = '''        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr)'''
new_create = '''        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr, self.room_mgr)'''

if old_create in content:
    content = content.replace(old_create, new_create)
    print("2. 创建WatchLiveFrame已传入room_mgr")
else:
    print("2. 未找到创建WatchLiveFrame代码")

# 版本号
content = content.replace('APP_VERSION = "v5.2.0"', 'APP_VERSION = "v5.2.1"')
print("3. 版本号: v5.2.0 -> v5.2.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
