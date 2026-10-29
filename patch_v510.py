#!/usr/bin/env python3
"""v5.1.0: 看播直播间同步调整(FocusOut+删除按钮)+删除按钮智能启用(仅历史记录可删)"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 看播任务直播间下拉框旁边增加删除按钮
# ============================================================
old_watch_room = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

new_watch_room = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.watch_room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                             bd=0, padx=8, pady=2, cursor="hand2", state=tk.DISABLED, command=self._delete_watch_room_history)
        self.watch_room_del_btn.pack(side=tk.LEFT, padx=(0, 20))'''

if old_watch_room in content:
    content = content.replace(old_watch_room, new_watch_room)
    print("1. 看播直播间下拉框已增加删除按钮(默认禁用)")
else:
    print("1. 未找到看播直播间下拉框代码")

# ============================================================
# 2. 看播任务KeyRelease改成FocusOut + 绑定选中变化事件
# ============================================================
old_watch_bind = '''            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)'''

new_watch_bind = '''            self.room_combo.bind("<FocusOut>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)
            self.room_combo.bind("<KeyRelease>", lambda e: self._update_watch_del_btn_state())'''

if old_watch_bind in content:
    content = content.replace(old_watch_bind, new_watch_bind)
    print("2. 看播保存触发已改为FocusOut + 绑定删除按钮状态更新")
else:
    print("2. 未找到看播绑定事件代码")

# ============================================================
# 3. 在看播_on_room_selected方法中增加删除按钮状态更新
# ============================================================
old_on_room_selected = '''    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", acc.get("uid", ""))
                    if mid:
                        room_id = self._get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self.save_watch_config()'''

new_on_room_selected = '''    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", acc.get("uid", ""))
                    if mid:
                        room_id = self._get_user_room_id(mid)
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
        self.save_watch_config()

    def _update_watch_del_btn_state(self):
        """根据下拉框选中内容更新删除按钮状态：仅纯数字历史记录可删"""
        try:
            selected = self.room_combo.get().strip()
            if selected and selected.isdigit() and selected in self.watch_config.get("room_history", []):
                self.watch_room_del_btn.config(state=tk.NORMAL)
            else:
                self.watch_room_del_btn.config(state=tk.DISABLED)
        except Exception:
            self.watch_room_del_btn.config(state=tk.DISABLED)

    def _delete_watch_room_history(self):
        """删除当前选中的看播直播间历史记录"""
        selected = self.room_combo.get().strip()
        if not selected or not selected.isdigit():
            return
        if "room_history" not in self.watch_config:
            self.watch_config["room_history"] = []
        if selected in self.watch_config["room_history"]:
            self.watch_config["room_history"].remove(selected)
            self.save_watch_config()
            self._refresh_room_combo_values()
            self.room_combo.set("")
            self._update_watch_del_btn_state()
            self.log(f"已删除看播直播间历史记录: {selected}")'''

if old_on_room_selected in content:
    content = content.replace(old_on_room_selected, new_on_room_selected)
    print("3. 看播_on_room_selected已更新(删除按钮状态+删除方法)")
else:
    print("3. 未找到看播_on_room_selected方法")

# ============================================================
# 4. 弹幕工具删除按钮：默认禁用 + 选中变化时更新状态
# ============================================================
old_danmaku_del_btn = '''        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                       bd=0, padx=8, pady=2, cursor="hand2", command=self._delete_danmaku_room_history)'''

new_danmaku_del_btn = '''        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 9, "bold"),
                                       bd=0, padx=8, pady=2, cursor="hand2", state=tk.DISABLED, command=self._delete_danmaku_room_history)'''

if old_danmaku_del_btn in content:
    content = content.replace(old_danmaku_del_btn, new_danmaku_del_btn)
    print("4. 弹幕删除按钮已改为默认禁用")
else:
    print("4. 未找到弹幕删除按钮代码")

# ============================================================
# 5. 弹幕工具绑定删除按钮状态更新
# ============================================================
old_danmaku_bind = '''        self.room_combo.bind("<FocusOut>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)'''

new_danmaku_bind = '''        self.room_combo.bind("<FocusOut>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)
        self.room_combo.bind("<KeyRelease>", lambda e: self._update_danmaku_del_btn_state())'''

if old_danmaku_bind in content:
    content = content.replace(old_danmaku_bind, new_danmaku_bind)
    print("5. 弹幕绑定已增加删除按钮状态更新")
else:
    print("5. 未找到弹幕绑定代码")

# ============================================================
# 6. 弹幕_on_danmaku_room_selected增加删除按钮状态更新
# ============================================================
old_danmaku_on_selected_end = '''        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self.save_config()'''

new_danmaku_on_selected_end = '''        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self._update_danmaku_del_btn_state()
        self.save_config()

    def _update_danmaku_del_btn_state(self):
        """根据下拉框选中内容更新删除按钮状态：仅纯数字历史记录可删"""
        try:
            selected = self.room_combo.get().strip()
            if selected and selected.isdigit() and selected in self.config.get("room_history", []):
                self.room_del_btn.config(state=tk.NORMAL)
            else:
                self.room_del_btn.config(state=tk.DISABLED)
        except Exception:
            self.room_del_btn.config(state=tk.DISABLED)'''

if old_danmaku_on_selected_end in content:
    content = content.replace(old_danmaku_on_selected_end, new_danmaku_on_selected_end)
    print("6. 弹幕_on_danmaku_room_selected已更新(删除按钮状态)")
else:
    print("6. 未找到弹幕_on_danmaku_room_selected结尾代码")

# ============================================================
# 7. 弹幕删除方法增加状态更新
# ============================================================
old_danmaku_delete_end = '''            self._refresh_danmaku_room_combo_values()
            self.room_combo.set("")
            self.log(f"已删除直播间历史记录: {selected}")
        else:
            messagebox.showinfo("提示", f"直播间号 {selected} 不在历史记录中")'''

new_danmaku_delete_end = '''            self._refresh_danmaku_room_combo_values()
            self.room_combo.set("")
            self._update_danmaku_del_btn_state()
            self.log(f"已删除直播间历史记录: {selected}")
        else:
            messagebox.showinfo("提示", f"直播间号 {selected} 不在历史记录中")'''

if old_danmaku_delete_end in content:
    content = content.replace(old_danmaku_delete_end, new_danmaku_delete_end)
    print("7. 弹幕删除方法已增加状态更新")
else:
    print("7. 未找到弹幕删除方法结尾代码")

# 版本号
content = content.replace('APP_VERSION = "v5.0.9"', 'APP_VERSION = "v5.1.0"')
print("8. 版本号: v5.0.9 -> v5.1.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
