#!/usr/bin/env python3
"""v5.2.0 part3: 看播页面直播间选择改成多栏选择(每栏选一个直播间)"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 看播页面：把单个直播间下拉框改成多栏选择
# ============================================================
old_watch_room_ui = '''        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.watch_room_del_btn = tk.Button(row1, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                             bd=0, padx=4, pady=1, cursor="hand2", state=tk.DISABLED, command=self._delete_watch_room_history)
        self.watch_room_del_btn.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

new_watch_room_ui = '''        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        # 直播间多栏选择容器
        self.watch_room_bars = []
        self.watch_room_container = tk.Frame(row1, bg=COLORS["bg_card"])
        self.watch_room_container.pack(side=tk.LEFT, padx=(8, 0))
        self._add_watch_room_bar()
        # 添加直播间栏按钮
        self.add_room_bar_btn = tk.Button(row1, text="+ 添加", bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 9),
                                           bd=0, padx=8, pady=2, cursor="hand2", command=self._add_watch_room_bar)
        self.add_room_bar_btn.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

if old_watch_room_ui in content:
    content = content.replace(old_watch_room_ui, new_watch_room_ui)
    print("1. 看播页面直播间UI已改为多栏选择")
else:
    print("1. 未找到看播页面直播间UI代码")

# ============================================================
# 2. 看播页面：添加多栏选择的方法
# ============================================================
old_refresh_room = '''    def _refresh_room_combo_values(self):
        """刷新直播间下拉框选项：用户直播间 + 历史记录"""
        values = []
        # 添加所有用户的直播间选项
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            values.append(f"【{name}】直播间")
        # 添加历史记录分隔
        if self.watch_config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.watch_config["room_history"])
        self.room_combo["values"] = values'''

new_refresh_room = '''    def _refresh_room_combo_values(self):
        """刷新所有直播间栏的下拉框选项"""
        values = ["无"] + [room["name"] for room in self.room_mgr.rooms]
        for bar, combo, del_btn in getattr(self, 'watch_room_bars', []):
            current = combo.get()
            combo["values"] = values
            if current not in values:
                combo.set("无")

    def _add_watch_room_bar(self):
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
            self.watch_room_bars[0][2].config(state=tk.DISABLED)

    def _remove_watch_room_bar(self, bar):
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
                d.config(state=tk.NORMAL)

    def _get_watch_room_ids(self):
        """获取所有选中的直播间号"""
        room_ids = []
        for bar, combo, del_btn in self.watch_room_bars:
            selected = combo.get().strip()
            if selected and selected != "无":
                for room in self.room_mgr.rooms:
                    if room["name"] == selected:
                        room_ids.append(room["id"])
                        break
        return room_ids'''

if old_refresh_room in content:
    content = content.replace(old_refresh_room, new_refresh_room)
    print("2. 已添加看播多栏选择方法")
else:
    print("2. 未找到_refresh_room_combo_values方法")

# ============================================================
# 3. 看播页面：修改start_watch中的直播间获取逻辑
# ============================================================
old_start_room = '''        room_input = self.room_combo.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请选择或输入直播间号")
            return
        # 解析多个直播间号（逗号、空格、分号分隔）
        room_ids = []
        for r in room_input.replace("，", ",").replace(";", ",").replace(" ", ",").split(","):
            r = r.strip()
            if r and r.isdigit():
                room_ids.append(r)
        if not room_ids:
            messagebox.showwarning("提示", "请输入有效的直播间号（数字），多个用逗号分隔")
            return'''

new_start_room = '''        room_ids = self._get_watch_room_ids()
        if not room_ids:
            messagebox.showwarning("提示", "请至少选择一个直播间（可在账户管理页面添加）")
            return'''

if old_start_room in content:
    content = content.replace(old_start_room, new_start_room)
    print("3. start_watch直播间获取逻辑已更新")
else:
    print("3. 未找到start_watch直播间获取代码")

# ============================================================
# 4. 看播页面：修改start_watch中的禁用/启用逻辑
# ============================================================
old_start_disable = '''        self.room_combo.config(state=tk.DISABLED)
        self.duration_combo.config(state=tk.DISABLED)
        self.interval_combo.config(state=tk.DISABLED)'''

new_start_disable = '''        for bar, combo, del_btn in self.watch_room_bars:
            combo.config(state=tk.DISABLED)
            del_btn.config(state=tk.DISABLED)
        self.add_room_bar_btn.config(state=tk.DISABLED)
        self.duration_combo.config(state=tk.DISABLED)
        self.interval_combo.config(state=tk.DISABLED)'''

if old_start_disable in content:
    content = content.replace(old_start_disable, new_start_disable)
    print("4. start_watch禁用逻辑已更新")
else:
    print("4. 未找到start_watch禁用逻辑")

# ============================================================
# 5. 看播页面：修改stop_watch中的启用逻辑
# ============================================================
old_stop_enable = '''        self.room_combo.config(state="normal")
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")'''

new_stop_enable = '''        for bar, combo, del_btn in self.watch_room_bars:
            combo.config(state="readonly")
            if len(self.watch_room_bars) > 1:
                del_btn.config(state=tk.NORMAL)
        self.add_room_bar_btn.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")'''

if old_stop_enable in content:
    content = content.replace(old_stop_enable, new_stop_enable)
    print("5. stop_watch启用逻辑已更新")
else:
    print("5. 未找到stop_watch启用逻辑")

# ============================================================
# 6. 看播页面：修改save_watch_config保存直播间选择
# ============================================================
old_save_room = '''            current_room = self.room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            if current_room and current_room.isdigit() and current_room not in self.watch_config.get("room_history", []):
                history = self.watch_config.get("room_history", [])
                history.insert(0, current_room)
                self.watch_config["room_history"] = history[:20]  # 最多保存20条
                self._refresh_room_combo_values()
            self.watch_config["room_id"] = current_room'''

new_save_room = '''            # 保存所有直播间栏的选择
            room_selections = []
            for bar, combo, del_btn in self.watch_room_bars:
                selected = combo.get().strip()
                if selected and selected != "无":
                    room_selections.append(selected)
            self.watch_config["room_selections"] = room_selections
            self.watch_config["room_bar_count"] = len(self.watch_room_bars)'''

if old_save_room in content:
    content = content.replace(old_save_room, new_save_room)
    print("6. save_watch_config直播间保存逻辑已更新")
else:
    print("6. 未找到save_watch_config直播间保存代码")

# ============================================================
# 7. 看播页面：修改apply_watch_config加载直播间选择
# ============================================================
old_apply_room = '''            self._refresh_room_combo_values()
            self.room_combo.set(self.watch_config.get("room_id", ""))'''

new_apply_room = '''            self._refresh_room_combo_values()
            # 恢复直播间栏数量
            bar_count = self.watch_config.get("room_bar_count", 1)
            while len(self.watch_room_bars) < bar_count:
                self._add_watch_room_bar()
            # 恢复直播间选择
            room_selections = self.watch_config.get("room_selections", [])
            for i, (bar, combo, del_btn) in enumerate(self.watch_room_bars):
                if i < len(room_selections):
                    combo.set(room_selections[i])
                else:
                    combo.set("无")'''

if old_apply_room in content:
    content = content.replace(old_apply_room, new_apply_room)
    print("7. apply_watch_config直播间加载逻辑已更新")
else:
    print("7. 未找到apply_watch_config直播间加载代码")

# ============================================================
# 8. 看播页面：修改bind_auto_save绑定
# ============================================================
old_bind = '''            self.room_combo.bind("<FocusOut>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)
            self.room_combo.bind("<KeyRelease>", lambda e: self._update_watch_del_btn_state())'''

new_bind = '''            # 直播间多栏选择的保存绑定在_add_watch_room_bar中'''

if old_bind in content:
    content = content.replace(old_bind, new_bind)
    print("8. bind_auto_save绑定已更新")
else:
    print("8. 未找到bind_auto_save绑定代码")

# ============================================================
# 9. 看播页面：删除不再需要的方法（_on_room_selected, _update_watch_del_btn_state, _delete_watch_room_history）
#    这些方法暂时保留，不删除，避免引用错误
# ============================================================

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
