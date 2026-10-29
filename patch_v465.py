#!/usr/bin/env python3
"""v4.6.5: 删除账户管理底部的账户信息区域，默认窗口改成1800x1400"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 删除账户管理底部的账户信息标签创建
# ============================================================
old_account_info_create = '''        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 10), padx=12)

        self.account_info = tk.Label(left_card, text="未选择账户", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 8), wraplength=200, justify=tk.LEFT)
        self.account_info.pack(anchor=tk.W, padx=15, pady=(0, 12))

        # 右侧：设置 + 弹幕 + 日志'''

new_account_info_create = '''        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 12), padx=12)

        # 右侧：设置 + 弹幕 + 日志'''

if old_account_info_create in content:
    content = content.replace(old_account_info_create, new_account_info_create)
    print("1. 已删除账户管理底部的账户信息标签创建")
else:
    print("1. 未找到账户信息标签创建代码")

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
# 4. 默认窗口大小改成1800x1400
# ============================================================
old_geometry = '''        self.root.geometry("1600x1250")
        self.root.minsize(1400, 1000)'''

new_geometry = '''        self.root.geometry("1800x1400")
        self.root.minsize(1500, 1100)'''

if old_geometry in content:
    content = content.replace(old_geometry, new_geometry)
    print("4. 默认窗口: 1600x1250 -> 1800x1400, 最小: 1400x1000 -> 1500x1100")
else:
    print("4. 未找到默认窗口大小设置")

# ============================================================
# 5. 加载保存的窗口大小时，默认值改成1800x1400
# ============================================================
old_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1400:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1250")'''

new_load_geom = '''                if width_str.isdigit() and int(width_str) >= 1500:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1800x1400")'''

if old_load_geom in content:
    content = content.replace(old_load_geom, new_load_geom)
    print("5. 加载窗口大小阈值: 1400 -> 1500, 默认值: 1600x1250 -> 1800x1400")
else:
    print("5. 未找到加载窗口大小代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.4"', 'APP_VERSION = "v4.6.5"')
print("6. 版本号已更新到 v4.6.5")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
