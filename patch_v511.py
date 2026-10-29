#!/usr/bin/env python3
"""v5.1.1: 修复删除账户自动保存+看播删除按钮状态+减小删除按钮面积"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 减小删除按钮面积（弹幕工具 + 看播任务）
# ============================================================
# 弹幕工具删除按钮
old_danmaku_del = '''        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                       bd=0, padx=8, pady=2, cursor="hand2", state=tk.DISABLED, command=self._delete_danmaku_room_history)'''
new_danmaku_del = '''        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                       bd=0, padx=4, pady=1, cursor="hand2", state=tk.DISABLED, command=self._delete_danmaku_room_history)'''
if old_danmaku_del in content:
    content = content.replace(old_danmaku_del, new_danmaku_del)
    print("1. 弹幕工具删除按钮面积已减小")
else:
    print("1. 未找到弹幕工具删除按钮代码")

# 看播任务删除按钮
old_watch_del = '''        self.watch_room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                             bd=0, padx=8, pady=2, cursor="hand2", state=tk.DISABLED, command=self._delete_watch_room_history)'''
new_watch_del = '''        self.watch_room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                             bd=0, padx=4, pady=1, cursor="hand2", state=tk.DISABLED, command=self._delete_watch_room_history)'''
if old_watch_del in content:
    content = content.replace(old_watch_del, new_watch_del)
    print("2. 看播任务删除按钮面积已减小")
else:
    print("2. 未找到看播任务删除按钮代码")

# ============================================================
# 3. 修复看播_on_room_selected：确保自动获取直播间号后正确更新删除按钮状态
# ============================================================
old_on_room = '''    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", "")
                    if mid:
                        room_id = self.get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self._update_watch_del_btn_state()
        self.save_watch_config()'''

new_on_room = '''    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        is_user_room = selected.startswith("【") and "】直播间" in selected
        if is_user_room:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", "")
                    if mid:
                        room_id = self.get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                            self.room_combo.set("")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        # 无论什么情况，都更新删除按钮状态（用户直播间自动获取的也禁用）
        self._update_watch_del_btn_state()
        self.save_watch_config()'''

if old_on_room in content:
    content = content.replace(old_on_room, new_on_room)
    print("3. 看播_on_room_selected已修复（确保删除按钮状态正确）")
else:
    print("3. 未找到看播_on_room_selected方法")

# ============================================================
# 4. 修复删除账户自动保存问题：在AccountManager中添加_deleting标志
# ============================================================
old_account_mgr_init = '''class AccountManager:
    def __init__(self):
        self.accounts = []
        self.load()'''

new_account_mgr_init = '''class AccountManager:
    def __init__(self):
        self.accounts = []
        self._deleting = False  # 删除标志，防止删除时自动保存
        self.load()'''

if old_account_mgr_init in content:
    content = content.replace(old_account_mgr_init, new_account_mgr_init)
    print("4. AccountManager已添加_deleting标志")
else:
    print("4. 未找到AccountManager初始化代码")

# 修改delete_account方法，设置_deleting标志
old_account_delete = '''    def delete_account(self, name):
        self.accounts = [a for a in self.accounts if a["name"] != name]
        self.save()'''

new_account_delete = '''    def delete_account(self, name):
        self._deleting = True
        self.accounts = [a for a in self.accounts if a["name"] != name]
        self.save()
        self._deleting = False'''

if old_account_delete in content:
    content = content.replace(old_account_delete, new_account_delete)
    print("5. AccountManager.delete_account已添加_deleting标志")
else:
    print("5. 未找到AccountManager.delete_account方法")

# ============================================================
# 5. 弹幕工具页面删除账户：确保删除后刷新所有相关列表
# ============================================================
old_danmaku_delete = '''    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        if custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.log(f"已删除账户: {acc['name']}")'''

new_danmaku_delete = '''    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        if custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新直播间下拉框选项（用户列表变了）
            if hasattr(self, '_refresh_danmaku_room_combo_values'):
                self._refresh_danmaku_room_combo_values()
            self.log(f"已删除账户: {acc['name']}")'''

if old_danmaku_delete in content:
    content = content.replace(old_danmaku_delete, new_danmaku_delete)
    print("6. 弹幕工具delete_account已修复（删除后刷新所有列表）")
else:
    print("6. 未找到弹幕工具delete_account方法")

# ============================================================
# 6. 账户管理页面删除账户：确保删除后刷新所有相关列表
# ============================================================
old_manager_delete = '''    def _manager_delete_account(self):
        """账户管理页面删除账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_manager_list()
            self._manager_show_info(None)
            self.log(f"已删除账户: {acc['name']}")'''

new_manager_delete = '''    def _manager_delete_account(self):
        """账户管理页面删除账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_manager_list()
            self._manager_show_info(None)
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新所有直播间下拉框选项（用户列表变了）
            if hasattr(self, '_refresh_danmaku_room_combo_values'):
                self._refresh_danmaku_room_combo_values()
            if hasattr(self, 'watch_frame') and hasattr(self.watch_frame, '_refresh_room_combo_values'):
                self.watch_frame._refresh_room_combo_values()
            self.log(f"已删除账户: {acc['name']}")'''

if old_manager_delete in content:
    content = content.replace(old_manager_delete, new_manager_delete)
    print("7. 账户管理_manager_delete_account已修复（删除后刷新所有列表）")
else:
    print("7. 未找到账户管理_manager_delete_account方法")

# 版本号
content = content.replace('APP_VERSION = "v5.1.0"', 'APP_VERSION = "v5.1.1"')
print("8. 版本号: v5.1.0 -> v5.1.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
