#!/usr/bin/env python3
"""v5.2.6: 删除看播页面直播间下拉框中的"无"选项"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. _add_watch_room_bar：删除"无"选项，默认值为空
# ============================================================
old_add_bar = '''    def _add_watch_room_bar(self):
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

new_add_bar = '''    def _add_watch_room_bar(self):
        """添加一个直播间选择栏"""
        bar = tk.Frame(self.watch_room_container, bg=COLORS["bg_card"])
        bar.pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(bar, width=20, values=[], state="readonly")
        combo.pack(side=tk.LEFT)
        combo.set("")
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
    print("1. _add_watch_room_bar已删除'无'选项")
else:
    print("1. 未找到_add_watch_room_bar代码")

# ============================================================
# 2. _refresh_room_combo_values：只显示直播间名称，不包含"无"
# ============================================================
old_refresh = '''    def _refresh_room_combo_values(self):
        """刷新所有直播间下拉框的选项"""
        values = ["无"]
        for room in self.room_mgr.rooms:
            values.append(room["name"])
        for bar, combo, del_btn in self.watch_room_bars:
            current = combo.get()
            combo["values"] = values
            if current and current in values:
                combo.set(current)
            elif current == "无":
                combo.set("无")
            else:
                combo.set("无")'''

new_refresh = '''    def _refresh_room_combo_values(self):
        """刷新所有直播间下拉框的选项"""
        values = []
        for room in self.room_mgr.rooms:
            values.append(room["name"])
        for bar, combo, del_btn in self.watch_room_bars:
            current = combo.get()
            combo["values"] = values
            if current and current in values:
                combo.set(current)
            else:
                combo.set("")'''

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh)
    print("2. _refresh_room_combo_values已删除'无'选项")
else:
    print("2. 未找到_refresh_room_combo_values代码")

# ============================================================
# 3. _get_watch_room_ids：判断选中值是否为空，而不是"无"
# ============================================================
old_get_ids = '''    def _get_watch_room_ids(self):
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

new_get_ids = '''    def _get_watch_room_ids(self):
        """获取所有选中的直播间号"""
        room_ids = []
        for bar, combo, del_btn in self.watch_room_bars:
            selected = combo.get().strip()
            if selected:
                for room in self.room_mgr.rooms:
                    if room["name"] == selected:
                        room_ids.append(room["id"])
                        break
        return room_ids'''

if old_get_ids in content:
    content = content.replace(old_get_ids, new_get_ids)
    print("3. _get_watch_room_ids已修改判断条件")
else:
    print("3. 未找到_get_watch_room_ids代码")

# ============================================================
# 4. save_watch_config：保存选中的名称列表，空值不保存
# ============================================================
old_save = '''            room_selections = []
            for bar, combo, del_btn in self.watch_room_bars:
                room_selections.append(combo.get())
            self.watch_config["room_selections"] = room_selections
            self.watch_config["room_bar_count"] = len(self.watch_room_bars)'''

new_save = '''            room_selections = []
            for bar, combo, del_btn in self.watch_room_bars:
                val = combo.get()
                room_selections.append(val if val else "")
            self.watch_config["room_selections"] = room_selections
            self.watch_config["room_bar_count"] = len(self.watch_room_bars)'''

if old_save in content:
    content = content.replace(old_save, new_save)
    print("4. save_watch_config已修改空值处理")
else:
    print("4. 未找到save_watch_config代码")

# ============================================================
# 5. apply_watch_config：恢复选择时空值不设置为"无"
# ============================================================
old_apply = '''            # 恢复直播间选择
            saved_selections = self.watch_config.get("room_selections", [])
            for i, (bar, combo, del_btn) in enumerate(self.watch_room_bars):
                if i < len(saved_selections):
                    combo.set(saved_selections[i])
                else:
                    combo.set("无")'''

new_apply = '''            # 恢复直播间选择
            saved_selections = self.watch_config.get("room_selections", [])
            for i, (bar, combo, del_btn) in enumerate(self.watch_room_bars):
                if i < len(saved_selections) and saved_selections[i]:
                    combo.set(saved_selections[i])
                else:
                    combo.set("")'''

if old_apply in content:
    content = content.replace(old_apply, new_apply)
    print("5. apply_watch_config已修改空值处理")
else:
    print("5. 未找到apply_watch_config代码")

# 版本号
content = content.replace('APP_VERSION = "v5.2.5"', 'APP_VERSION = "v5.2.6"')
print("6. 版本号: v5.2.5 -> v5.2.6")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
