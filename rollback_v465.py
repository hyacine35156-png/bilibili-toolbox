#!/usr/bin/env python3
"""回退到v4.6.5：撤销v4.6.6到v4.6.9的所有改动"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 删除账户信息标签（撤销v4.6.6的恢复）
# ============================================================
old_account_info = '''        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 10), padx=12)

        self.account_info = tk.Label(left_card, text="未选择账户", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 8), wraplength=200, justify=tk.LEFT)
        self.account_info.pack(anchor=tk.W, padx=15, pady=(0, 12))

        # 右侧：设置 + 弹幕 + 日志'''

new_account_info = '''        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 12), padx=12)

        # 右侧：设置 + 弹幕 + 日志'''

if old_account_info in content:
    content = content.replace(old_account_info, new_account_info)
    print("1. 已删除账户信息标签")
else:
    print("1. 未找到账户信息标签代码（可能已删除）")

# ============================================================
# 2. 删除on_account_select中的account_info.config调用
# ============================================================
old_on_select = '''        acc = self.account_mgr.accounts[selection[0]]
        self.account_info.config(
            text=f"账户: {acc['name']}\\n用户: {acc.get('username', '未知')}\\nDedeID: {acc.get('DedeUserID', '未设置')}",
            fg=COLORS["text_secondary"]
        )
        # 保存当前选中的账户'''

new_on_select = '''        acc = self.account_mgr.accounts[selection[0]]
        # 保存当前选中的账户'''

if old_on_select in content:
    content = content.replace(old_on_select, new_on_select)
    print("2. 已删除on_account_select中的account_info.config调用")
else:
    print("2. 未找到on_account_select中的account_info代码")

# ============================================================
# 3. 删除delete_account中的account_info.config调用
# ============================================================
old_delete = '''            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.account_info.config(text="未选择账户", fg=COLORS["text_muted"])
            self.log(f"已删除账户: {acc['name']}")'''

new_delete = '''            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.log(f"已删除账户: {acc['name']}")'''

if old_delete in content:
    content = content.replace(old_delete, new_delete)
    print("3. 已删除delete_account中的account_info.config调用")
else:
    print("3. 未找到delete_account中的account_info代码")

# ============================================================
# 4. 把添加账户弹窗高度改回500x600（撤销v4.6.7和v4.6.8）
# ============================================================
old_dialog_geom = '''        self.geometry("500x800")
        self.minsize(500, 800)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 400
        self.geometry(f"500x800+{x}+{y}")'''

new_dialog_geom = '''        self.geometry("500x600")
        self.minsize(500, 600)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 300
        self.geometry(f"500x600+{x}+{y}")'''

if old_dialog_geom in content:
    content = content.replace(old_dialog_geom, new_dialog_geom)
    print("4. 添加账户弹窗高度: 500x800 -> 500x600")
else:
    print("4. 未找到添加账户弹窗大小代码")

# ============================================================
# 5. 把字段间距改回原来的值（撤销v4.6.8）
# ============================================================
old_label_pady = '''            lbl.pack(anchor=tk.W, pady=(5, 2))'''
new_label_pady = '''            lbl.pack(anchor=tk.W, pady=(8, 3))'''
if old_label_pady in content:
    content = content.replace(old_label_pady, new_label_pady)
    print("5a. 字段标签间距: (5,2) -> (8,3)")
else:
    print("5a. 未找到字段标签间距代码")

old_entry_pady = '''            entry.pack(anchor=tk.W, pady=(0, 3))'''
new_entry_pady = '''            entry.pack(anchor=tk.W, pady=(0, 5))'''
if old_entry_pady in content:
    content = content.replace(old_entry_pady, new_entry_pady)
    print("5b. 字段输入框间距: (0,3) -> (0,5)")
else:
    print("5b. 未找到字段输入框间距代码")

old_btn_pady = '''        btn_frame.pack(fill=tk.X, pady=(15, 0))'''
new_btn_pady = '''        btn_frame.pack(fill=tk.X, pady=(20, 0))'''
if old_btn_pady in content:
    content = content.replace(old_btn_pady, new_btn_pady)
    print("5c. 按钮框架间距: (15,0) -> (20,0)")
else:
    print("5c. 未找到按钮框架间距代码")

# ============================================================
# 6. 版本号改回v4.6.5
# ============================================================
content = content.replace('APP_VERSION = "v4.6.9"', 'APP_VERSION = "v4.6.5"')
content = content.replace('APP_VERSION = "v4.6.8"', 'APP_VERSION = "v4.6.5"')
content = content.replace('APP_VERSION = "v4.6.7"', 'APP_VERSION = "v4.6.5"')
content = content.replace('APP_VERSION = "v4.6.6"', 'APP_VERSION = "v4.6.5"')
print("6. 版本号已改回 v4.6.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
