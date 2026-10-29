#!/usr/bin/env python3
"""v5.2.3: 修复直播间管理空间、看播账户刷新、第一个直播间栏删除按钮"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 直播间管理右侧空间太小：增加右侧表单宽度和按钮宽度
# ============================================================
old_room_right = '''        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=280)
        room_right.pack(side=tk.LEFT, fill=tk.Y)
        room_right.pack_propagate(False)'''

new_room_right = '''        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=340)
        room_right.pack(side=tk.LEFT, fill=tk.Y)
        room_right.pack_propagate(False)'''

if old_room_right in content:
    content = content.replace(old_room_right, new_room_right)
    print("1. 直播间管理右侧表单宽度: 280 -> 340")
else:
    print("1. 未找到直播间管理右侧表单代码")

# 增加按钮宽度
old_buttons = '''        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=260, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=260, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=260, height=34, bg_color="#2980b9", text_color="#ffffff").pack()'''

new_buttons = '''        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=320, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=320, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=320, height=34, bg_color="#2980b9", text_color="#ffffff").pack()'''

if old_buttons in content:
    content = content.replace(old_buttons, new_buttons)
    print("2. 直播间管理按钮宽度: 260 -> 320")
else:
    print("2. 未找到直播间管理按钮代码")

# ============================================================
# 3. 看播区显示无账户：在add_account和delete_account后刷新看播页面
# ============================================================
old_add_account = '''    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()'''

new_add_account = '''    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()
        # 刷新看播页面账户列表
        if hasattr(self, 'watch_page'):
            self.watch_page.refresh_account_list()'''

if old_add_account in content:
    content = content.replace(old_add_account, new_add_account)
    print("3. add_account已添加看播页面刷新")
else:
    print("3. 未找到add_account代码")

old_delete_account = '''    def delete_account(self):
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
            self.log(f"已删除账户: {acc['name']}")'''

new_delete_account = '''    def delete_account(self):
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
            # 刷新看播页面账户列表
            if hasattr(self, 'watch_page'):
                self.watch_page.refresh_account_list()
            self.log(f"已删除账户: {acc['name']}")'''

if old_delete_account in content:
    content = content.replace(old_delete_account, new_delete_account)
    print("4. delete_account已添加看播页面刷新")
else:
    print("4. 未找到delete_account代码")

# ============================================================
# 5. 看播第一个直播间栏不需要删除按钮
# ============================================================
old_add_bar = '''    def _add_watch_room_bar(self):
        """添加一个直播间选择栏"""
        bar = tk.Frame(self.watch_room_container, bg=COLORS["bg_card"])
        bar.pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(bar, width=20, values=["无"], state="readonly")
        combo.pack(side=tk.LEFT)
        combo.set("无")
        del_btn = tk.Button(bar, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                            bd=0, padx=4, pady=1, cursor="hand2", command=lambda b=bar: self._remove_watch_room_bar(b))
        del_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.watch_room_bars.append((bar, combo, del_btn))
        self._refresh_room_combo_values()
        # 如果只有一个栏，禁用删除按钮
        if len(self.watch_room_bars) <= 1:
            self.watch_room_bars[0][2].config(state=tk.DISABLED)'''

new_add_bar = '''    def _add_watch_room_bar(self):
        """添加一个直播间选择栏"""
        bar = tk.Frame(self.watch_room_container, bg=COLORS["bg_card"])
        bar.pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(bar, width=20, values=["无"], state="readonly")
        combo.pack(side=tk.LEFT)
        combo.set("无")
        # 第一个栏不显示删除按钮，后面添加的栏才显示
        is_first = len(self.watch_room_bars) == 0
        del_btn = None
        if not is_first:
            del_btn = tk.Button(bar, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                bd=0, padx=4, pady=1, cursor="hand2", command=lambda b=bar: self._remove_watch_room_bar(b))
            del_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.watch_room_bars.append((bar, combo, del_btn))
        self._refresh_room_combo_values()'''

if old_add_bar in content:
    content = content.replace(old_add_bar, new_add_bar)
    print("5. _add_watch_room_bar已修改：第一个栏不显示删除按钮")
else:
    print("5. 未找到_add_watch_room_bar代码")

# 修改_remove_watch_room_bar方法，处理del_btn为None的情况
old_remove_bar = '''    def _remove_watch_room_bar(self, bar):
        """删除一个直播间选择栏"""
        if len(self.watch_room_bars) <= 1:
            return
        for i, (b, c, d) in enumerate(self.watch_room_bars):
            if b == bar:
                b.destroy()
                self.watch_room_bars.pop(i)
                break
        # 如果只剩一个栏，禁用删除按钮
        if len(self.watch_room_bars) <= 1:
            self.watch_room_bars[0][2].config(state=tk.DISABLED)
        else:
            for b, c, d in self.watch_room_bars:
                d.config(state=tk.NORMAL)'''

new_remove_bar = '''    def _remove_watch_room_bar(self, bar):
        """删除一个直播间选择栏"""
        if len(self.watch_room_bars) <= 1:
            return
        for i, (b, c, d) in enumerate(self.watch_room_bars):
            if b == bar:
                b.destroy()
                self.watch_room_bars.pop(i)
                break
        # 第一个栏没有删除按钮，后面的栏保持正常状态
        for idx, (b, c, d) in enumerate(self.watch_room_bars):
            if d is not None and idx > 0:
                d.config(state=tk.NORMAL)'''

if old_remove_bar in content:
    content = content.replace(old_remove_bar, new_remove_bar)
    print("6. _remove_watch_room_bar已修改：处理del_btn为None的情况")
else:
    print("6. 未找到_remove_watch_room_bar代码")

# 修改stop_watch方法，处理del_btn为None的情况
old_stop_watch = '''        # 恢复直播间选择控件
        for bar, combo, del_btn in self.watch_room_bars:
            combo.config(state="readonly")
            if del_btn:
                del_btn.config(state=tk.NORMAL)
        self.add_room_bar_btn.config(state=tk.NORMAL)'''

# 先搜索一下stop_watch中的相关代码
if old_stop_watch in content:
    content = content.replace(old_stop_watch, old_stop_watch)  # 已经是正确的
    print("7. stop_watch已正确处理del_btn为None的情况")
else:
    print("7. 未找到stop_watch相关代码（可能已经是正确的）")

# 版本号
content = content.replace('APP_VERSION = "v5.2.2"', 'APP_VERSION = "v5.2.3"')
print("8. 版本号: v5.2.2 -> v5.2.3")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
