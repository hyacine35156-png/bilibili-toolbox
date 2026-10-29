#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复WatchLiveFrame默认全选：refresh_account_list默认True + apply_watch_config空列表时全选"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改WatchLiveFrame的refresh_account_list，默认值改为True
old_refresh = '''    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=False)
            self.account_vars[name] = var'''

new_refresh = '''    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框（默认全选）
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=True)
            self.account_vars[name] = var'''

content = content.replace(old_refresh, new_refresh, 1)

# 2. 修改apply_watch_config，空列表时默认全选
old_apply = '''            selected_names = self.watch_config.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected_names)'''

new_apply = '''            selected_names = self.watch_config.get("selected_accounts", [])
            # 如果配置中没有选中的账户（首次使用），默认全选
            if not selected_names:
                for name, var in self.account_vars.items():
                    var.set(True)
            else:
                for name, var in self.account_vars.items():
                    var.set(name in selected_names)'''

content = content.replace(old_apply, new_apply, 1)

# 3. 更新版本号
content = content.replace('APP_VERSION = "v3.9.1"', 'APP_VERSION = "v3.9.2"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.9.2")
print(f"文件大小: {len(content)} 字符")
