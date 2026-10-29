#!/usr/bin/env python3
"""v4.6.4: 默认窗口大小改成1600x1250"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 默认窗口大小：1600x1100 -> 1600x1250
# ============================================================
old_geometry = '''        self.root.geometry("1600x1100")
        self.root.minsize(1300, 900)'''

new_geometry = '''        self.root.geometry("1600x1250")
        self.root.minsize(1400, 1000)'''

if old_geometry in content:
    content = content.replace(old_geometry, new_geometry)
    print("1. 默认窗口: 1600x1100 -> 1600x1250, 最小: 1300x900 -> 1400x1000")
else:
    print("1. 未找到默认窗口大小设置")

# ============================================================
# 2. 加载保存的窗口大小时，默认值改成1600x1250
# ============================================================
old_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1400:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1100")'''

new_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1400:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1250")'''

if old_load_geom in content:
    content = content.replace(old_load_geom, new_load_geom)
    print("2. 加载窗口大小默认值: 1600x1100 -> 1600x1250")
else:
    print("2. 未找到加载窗口大小代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.3"', 'APP_VERSION = "v4.6.4"')
print("3. 版本号已更新到 v4.6.4")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
