file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在start_watch函数中添加调试日志和异常处理
old_start_watch = '''    def start_watch(self):
        if self.running:
            return
        room_ids = self._get_watch_room_ids()
        if not room_ids:
            messagebox.showwarning("提示", "请至少选择一个直播间（可在账户管理页面添加）")
            return
        # 从复选框获取选中账户
        selected_names = [name for name, var in self.account_vars.items() if var.get()]
        if not selected_names:
            messagebox.showwarning("提示", "请至少勾选一个账户")
            return
        selected_accounts = [acc for acc in self.account_mgr.accounts if acc.get("name", "") in selected_names]
        if not selected_accounts:
            messagebox.showwarning("提示", "未找到选中的账户")
            return
        self.running = True
        self.stop_flag = {"stop": False}
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)'''

new_start_watch = '''    def start_watch(self):
        try:
            self.log("[调试] start_watch被调用")
            if self.running:
                self.log("[调试] 已经在运行中，直接返回")
                return
            room_ids = self._get_watch_room_ids()
            self.log(f"[调试] 获取到直播间ID: {room_ids}")
            if not room_ids:
                messagebox.showwarning("提示", "请至少选择一个直播间（可在账户管理页面添加）")
                return
            # 从复选框获取选中账户
            selected_names = [name for name, var in self.account_vars.items() if var.get()]
            self.log(f"[调试] 选中的账户名: {selected_names}")
            if not selected_names:
                messagebox.showwarning("提示", "请至少勾选一个账户")
                return
            selected_accounts = [acc for acc in self.account_mgr.accounts if acc.get("name", "") in selected_names]
            self.log(f"[调试] 找到的账户对象数量: {len(selected_accounts)}")
            if not selected_accounts:
                messagebox.showwarning("提示", "未找到选中的账户")
                return
            self.running = True
            self.stop_flag = {"stop": False}
            self.log("[调试] 开始设置按钮状态")
            self.start_btn.config(state=tk.DISABLED)
            self.log("[调试] start_btn状态已设置为禁用")
            self.stop_btn.config(state=tk.NORMAL)
            self.log("[调试] stop_btn状态已设置为启用")'''

if old_start_watch in content:
    content = content.replace(old_start_watch, new_start_watch)
    print("✓ 已在start_watch函数中添加调试日志和异常处理")
else:
    print("✗ 未找到start_watch函数")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
