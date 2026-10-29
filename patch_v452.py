#!/usr/bin/env python3
"""v4.5.2: 添加DPI感知，解决高DPI显示器上文字模糊问题"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 在main函数开头添加DPI感知设置
# ============================================================
old_main = '''def main():
    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()'''

new_main = '''def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        # 尝试设置Per-Monitor DPI Aware（Windows 8.1+）
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # 降级为System DPI Aware（Windows Vista+）
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()'''

if old_main in content:
    content = content.replace(old_main, new_main)
    print("1. 在main函数中添加DPI感知设置")
else:
    print("1. 未找到main函数代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.1"', 'APP_VERSION = "v4.5.2"')
print("2. 版本号已更新到 v4.5.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
