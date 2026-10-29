#!/usr/bin/env python3
"""v4.5.3: 调大默认窗口大小，适配高DPI显示器"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 调大默认窗口大小和最小窗口大小
# ============================================================
old_geometry = '''        self.root.geometry("1000x850")
        self.root.minsize(900, 720)'''

new_geometry = '''        self.root.geometry("1400x1000")
        self.root.minsize(1100, 800)'''

if old_geometry in content:
    content = content.replace(old_geometry, new_geometry)
    print("1. 调大默认窗口大小: 1000x850 -> 1400x1000")
    print("   调大最小窗口大小: 900x720 -> 1100x800")
else:
    print("1. 未找到窗口大小设置代码")

# ============================================================
# 2. 修改加载窗口大小的逻辑，如果保存的大小太小则用新默认值
# ============================================================
old_load_geometry = '''        # 恢复窗口大小和位置
        if self.config.get("window_geometry"):
            try:
                self.root.geometry(self.config["window_geometry"])
            except Exception:
                pass'''

new_load_geometry = '''        # 恢复窗口大小和位置（如果保存的大小太小则用新默认值）
        if self.config.get("window_geometry"):
            try:
                geom = self.config["window_geometry"]
                # 解析宽度，如果小于1200则用新默认值
                width_str = geom.split("x")[0]
                if width_str.isdigit() and int(width_str) >= 1200:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1400x1000")
            except Exception:
                self.root.geometry("1400x1000")'''

if old_load_geometry in content:
    content = content.replace(old_load_geometry, new_load_geometry)
    print("2. 修改加载逻辑：保存的窗口宽度<1200时自动用新默认值")
else:
    print("2. 未找到加载窗口大小代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.2"', 'APP_VERSION = "v4.5.3"')
print("3. 版本号已更新到 v4.5.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
