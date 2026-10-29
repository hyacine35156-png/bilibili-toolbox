#!/usr/bin/env python3
"""v5.2.0 part2: 弹幕工具页面直播间选择改成只显示名称(不显示数字)"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 弹幕工具页面：把直播间下拉框改成只显示名称
# ============================================================
old_danmaku_room = '''        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=24, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                       bd=0, padx=4, pady=1, cursor="hand2", state=tk.DISABLED, command=self._delete_danmaku_room_history)
        self.room_del_btn.pack(side=tk.LEFT, padx=(0, 20))'''

new_danmaku_room = '''        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[], state="readonly")
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))'''

if old_danmaku_room in content:
    content = content.replace(old_danmaku_room, new_danmaku_room)
    print("1. 弹幕工具直播间下拉框已改为只显示名称(只读)")
else:
    print("1. 未找到弹幕工具直播间下拉框代码")

# ============================================================
# 2. 弹幕工具：添加刷新直播间下拉框选项的方法
# ============================================================
old_danmaku_refresh = '''    def _refresh_danmaku_room_combo_values(self):
        """刷新弹幕直播间下拉框选项：用户直播间 + 历史记录"""
        if not hasattr(self, 'room_combo'):
            return
        values = []
        # 添加所有用户的直播间选项
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(f"【{name}】直播间")
        # 添加历史记录分隔
        if self.config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.config["room_history"])
        self.room_combo["values"] = values'''

new_danmaku_refresh = '''    def _refresh_danmaku_room_combo_values(self):
        """刷新弹幕直播间下拉框选项：只显示直播间名称，不显示数字ID"""
        if not hasattr(self, 'room_combo'):
            return
        values = [room["name"] for room in self.room_mgr.rooms]
        self.room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.room_combo.get() not in values:
            self.room_combo.set("")

    def _get_danmaku_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None'''

if old_danmaku_refresh in content:
    content = content.replace(old_danmaku_refresh, new_danmaku_refresh)
    print("2. 弹幕工具刷新直播间下拉框方法已更新")
else:
    print("2. 未找到_refresh_danmaku_room_combo_values方法")

# ============================================================
# 3. 弹幕工具：修改_on_danmaku_room_selected方法（删除旧逻辑）
# ============================================================
old_danmaku_on_selected = '''    def _on_danmaku_room_selected(self, event=None):
        """选择弹幕直播间下拉框时：如果选的是用户名，自动获取直播间号"""
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
        self._update_danmaku_del_btn_state()
        self.save_config()'''

new_danmaku_on_selected = '''    def _on_danmaku_room_selected(self, event=None):
        """选择弹幕直播间下拉框时：保存配置"""
        self.save_config()'''

if old_danmaku_on_selected in content:
    content = content.replace(old_danmaku_on_selected, new_danmaku_on_selected)
    print("3. 弹幕_on_danmaku_room_selected已简化")
else:
    print("3. 未找到_on_danmaku_room_selected方法")

# ============================================================
# 4. 弹幕工具：删除不再需要的方法（_update_danmaku_del_btn_state, _delete_danmaku_room_history, _get_user_room_id）
# ============================================================
# 这些方法暂时保留，不删除，避免引用错误

# ============================================================
# 5. 弹幕工具：修改start_sending中的直播间号获取逻辑
# ============================================================
old_start_room = '''        room_id = self.room_combo.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请选择或输入有效的直播间号（数字）")
            return'''

new_start_room = '''        room_id = self._get_danmaku_room_id()
        if not room_id:
            messagebox.showwarning("提示", "请先选择直播间（可在账户管理页面添加）")
            return'''

if old_start_room in content:
    content = content.replace(old_start_room, new_start_room)
    print("4. 弹幕start_sending直播间获取逻辑已更新")
else:
    print("4. 未找到start_sending直播间获取代码")

# ============================================================
# 6. 弹幕工具：修改save_config中的直播间保存逻辑
# ============================================================
old_save_room = '''            self.config["room_id"] = self.room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            room_id = self.room_combo.get().strip()
            if room_id.isdigit():
                if "room_history" not in self.config:
                    self.config["room_history"] = []
                if room_id not in self.config["room_history"]:
                    self.config["room_history"].insert(0, room_id)
                    self.config["room_history"] = self.config["room_history"][:10]  # 最多保留10条
                    self._refresh_danmaku_room_combo_values()'''

new_save_room = '''            self.config["room_id"] = self.room_combo.get().strip()  # 保存直播间名称'''

if old_save_room in content:
    content = content.replace(old_save_room, new_save_room)
    print("5. 弹幕save_config直播间保存逻辑已更新")
else:
    print("5. 未找到save_config直播间保存代码")

# ============================================================
# 7. 弹幕工具：修改apply_config中的直播间加载逻辑
# ============================================================
old_apply_room = '''        if self.config.get("room_id"):
            self.room_combo.set(self.config["room_id"])
        # 初始化直播间下拉框选项
        self._refresh_danmaku_room_combo_values()'''

new_apply_room = '''        # 初始化直播间下拉框选项
        self._refresh_danmaku_room_combo_values()
        if self.config.get("room_id"):
            self.room_combo.set(self.config["room_id"])'''

if old_apply_room in content:
    content = content.replace(old_apply_room, new_apply_room)
    print("6. 弹幕apply_config直播间加载逻辑已更新")
else:
    print("6. 未找到apply_config直播间加载代码")

# ============================================================
# 8. 弹幕工具：修改绑定事件（删除KeyRelease和删除按钮状态更新）
# ============================================================
old_bind_room = '''        self.room_combo.bind("<FocusOut>", lambda e: self.save_config())
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)
        self.room_combo.bind("<KeyRelease>", lambda e: self._update_danmaku_del_btn_state())'''

new_bind_room = '''        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)'''

if old_bind_room in content:
    content = content.replace(old_bind_room, new_bind_room)
    print("7. 弹幕绑定事件已更新")
else:
    print("7. 未找到弹幕绑定事件代码")

# ============================================================
# 9. 弹幕工具：删除账户后刷新直播间下拉框
# ============================================================
old_danmaku_delete_refresh = '''            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新直播间下拉框选项（用户列表变了）
            if hasattr(self, '_refresh_danmaku_room_combo_values'):
                self._refresh_danmaku_room_combo_values()'''

new_danmaku_delete_refresh = '''            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()'''

if old_danmaku_delete_refresh in content:
    content = content.replace(old_danmaku_delete_refresh, new_danmaku_delete_refresh)
    print("8. 弹幕删除账户后刷新逻辑已更新")
else:
    print("8. 未找到弹幕删除账户后刷新代码")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
