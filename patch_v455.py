#!/usr/bin/env python3
"""v4.5.5: 修复添加账户弹窗显示异常（窗口太小内容被截断）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 修复添加账户弹窗：把geometry设置移到最后，并确保窗口大小正确
# ============================================================
old_dialog_init = '''class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.geometry("460x500")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)'''

new_dialog_init = '''class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add
        self.transient(parent)

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)'''

if old_dialog_init in content:
    content = content.replace(old_dialog_init, new_dialog_init)
    print("1. 修复添加账户弹窗初始化：移除提前设置geometry，改为最后设置")
else:
    print("1. 未找到添加账户弹窗初始化代码")

# ============================================================
# 在弹窗最后添加geometry设置和grab_set
# ============================================================
old_dialog_end = '''        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=100, height=32).pack(side=tk.RIGHT)

    def toggle_show(self):'''

new_dialog_end = '''        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
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
        self.grab_set()

    def toggle_show(self):'''

if old_dialog_end in content:
    content = content.replace(old_dialog_end, new_dialog_end)
    print("2. 在弹窗最后添加geometry设置、居中显示和grab_set")
else:
    print("2. 未找到添加账户弹窗结尾代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.4"', 'APP_VERSION = "v4.5.5"')
print("3. 版本号已更新到 v4.5.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
