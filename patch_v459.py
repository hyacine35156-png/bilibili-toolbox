#!/usr/bin/env python3
"""v4.5.9: 统一加大所有按钮尺寸（字号不变），默认窗口再放大"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 默认窗口大小再放大：1400x1000 -> 1600x1100
# ============================================================
old_geometry = '''        self.root.geometry("1400x1000")
        self.root.minsize(1100, 800)'''

new_geometry = '''        self.root.geometry("1600x1100")
        self.root.minsize(1300, 900)'''

if old_geometry in content:
    content = content.replace(old_geometry, new_geometry)
    print("1. 默认窗口: 1400x1000 -> 1600x1100, 最小: 1100x800 -> 1300x900")
else:
    print("1. 未找到默认窗口大小设置")

# ============================================================
# 2. 统一加大所有按钮尺寸（按尺寸分组批量替换，字号保持11号不变）
# ============================================================
replacements = [
    # 极小按钮 -> 小按钮
    ('width=45, height=22', 'width=60, height=28'),
    ('width=60, height=24', 'width=70, height=28'),
    ('width=60, height=26', 'width=70, height=30'),
    ('width=60, height=30', 'width=70, height=34'),
    # 小按钮 -> 中小按钮
    ('width=70, height=26', 'width=80, height=30'),
    ('width=70, height=32', 'width=85, height=36'),
    ('width=80, height=26', 'width=90, height=30'),
    ('width=80, height=30', 'width=90, height=34'),
    ('width=80, height=36', 'width=90, height=38'),
    # 中小按钮 -> 中按钮
    ('width=90, height=28', 'width=100, height=32'),
    ('width=90, height=30', 'width=100, height=34'),
    ('width=100, height=30', 'width=110, height=34'),
    ('width=100, height=32', 'width=110, height=36'),
    ('width=100, height=38', 'width=110, height=40'),
    # 中按钮 -> 中大按钮
    ('width=110, height=26', 'width=120, height=30'),
    ('width=110, height=30', 'width=120, height=34'),
    ('width=110, height=36', 'width=120, height=38'),
    ('width=110, height=38', 'width=120, height=40'),
    ('width=110, height=40', 'width=120, height=42'),
    # 中大按钮 -> 大按钮
    ('width=120, height=30', 'width=130, height=34'),
    ('width=120, height=32', 'width=130, height=36'),
    ('width=120, height=36', 'width=130, height=38'),
    ('width=120, height=40', 'width=130, height=42'),
    # 大按钮 -> 更大按钮
    ('width=130, height=36', 'width=140, height=40'),
    ('width=130, height=38', 'width=140, height=42'),
    ('width=130, height=40', 'width=140, height=44'),
    # 特大按钮
    ('width=200, height=30', 'width=220, height=36'),
]

count = 0
for old, new in replacements:
    if old in content:
        n = content.count(old)
        content = content.replace(old, new)
        count += n
        print(f"   {old} -> {new} ({n}处)")

print(f"2. 共替换 {count} 处按钮尺寸")

# ============================================================
# 3. 加载保存的窗口大小时，宽度小于1400自动用新默认值
# ============================================================
old_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1200:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1400x1000")'''

new_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1400:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1100")'''

if old_load_geom in content:
    content = content.replace(old_load_geom, new_load_geom)
    print("3. 加载窗口大小阈值: 1200 -> 1400, 默认值: 1400x1000 -> 1600x1100")
else:
    print("3. 未找到加载窗口大小代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.8"', 'APP_VERSION = "v4.5.9"')
print("4. 版本号已更新到 v4.5.9")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
