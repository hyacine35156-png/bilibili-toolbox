#!/usr/bin/env python3
"""v4.5.8: 修复添加账户弹窗高度，加大按钮尺寸（字体不变）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 修复添加账户弹窗：重写初始化，确保窗口大小正确
# ============================================================
old_dialog_init = '''class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add
        self.transient(parent)

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)'''

new_dialog_init = '''class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)'''

if old_dialog_init in content:
    content = content.replace(old_dialog_init, new_dialog_init)
    print("1. 修复添加账户弹窗初始化：移除transient")
else:
    print("1. 未找到添加账户弹窗初始化代码")

# ============================================================
# 2. 修复添加账户弹窗结尾：正确设置窗口大小500x600
# ============================================================
old_dialog_end = '''        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=100, height=32).pack(side=tk.RIGHT)

        # 确保窗口大小正确（在所有组件创建后设置）
        self.update_idletasks()
        self.geometry("460x500")
        self.minsize(460, 500)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 230
        y = (self.winfo_screenheight() // 2) - 250
        self.geometry(f"460x500+{x}+{y}")
        self.grab_set()'''

new_dialog_end = '''        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=130, height=38).pack(side=tk.RIGHT)

        # 确保窗口大小正确（在所有组件创建后设置）
        self.update_idletasks()
        self.geometry("500x600")
        self.minsize(500, 600)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 300
        self.geometry(f"500x600+{x}+{y}")
        self.grab_set()'''

if old_dialog_end in content:
    content = content.replace(old_dialog_end, new_dialog_end)
    print("2. 修复添加账户弹窗结尾：窗口大小460x500 -> 500x600")
else:
    print("2. 未找到添加账户弹窗结尾代码")

# ============================================================
# 3. 加大添加账户弹窗的其他按钮尺寸
# ============================================================
content = content.replace('width=90, height=32, bg_color="#444466"', 'width=110, height=38, bg_color="#444466"')
content = content.replace('width=80, height=32, bg_color="#555577"', 'width=100, height=38, bg_color="#555577"')
print("3. 加大添加账户弹窗按钮尺寸")

# ============================================================
# 4. 全局DarkButton默认尺寸再加大（字体保持11号不变）
# ============================================================
old_default_size = '''    def __init__(self, parent, text, command=None, width=140, height=40,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):'''

new_default_size = '''    def __init__(self, parent, text, command=None, width=150, height=44,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):'''

if old_default_size in content:
    content = content.replace(old_default_size, new_default_size)
    print("4. DarkButton默认尺寸: 140x40 -> 150x44（字体保持11号不变）")
else:
    print("4. 未找到DarkButton默认尺寸代码")

# ============================================================
# 5. 抢码页面主按钮再加大（120x36 -> 130x40）
# ============================================================
content = content.replace('width=120, height=36, bg_color="#444466"', 'width=130, height=40, bg_color="#444466"')
content = content.replace('width=120, height=36, bg_color="#ff6b35"', 'width=130, height=40, bg_color="#ff6b35"')
content = content.replace('width=120, height=36, bg_color="#e74c3c"', 'width=130, height=40, bg_color="#e74c3c"')
content = content.replace('width=120, height=36, bg_color="#9b59b6"', 'width=130, height=40, bg_color="#9b59b6"')
content = content.replace('width=100, height=36, bg_color=COLORS["danger"]', 'width=110, height=40, bg_color=COLORS["danger"]')
print("5. 抢码页面主按钮: 120x36 -> 130x40")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.7"', 'APP_VERSION = "v4.5.8"')
print("6. 版本号已更新到 v4.5.8")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
