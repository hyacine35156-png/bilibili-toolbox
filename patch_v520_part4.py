#!/usr/bin/env python3
"""v5.2.0 part4: 清理引用已删除控件的旧方法"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 删除看播页面的旧方法（_on_room_selected, _update_watch_del_btn_state, _delete_watch_room_history）
# ============================================================
old_watch_methods = '''    def _on_room_selected(self, event=None):
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
            self.log(f"已删除看播直播间历史记录: {selected}")

    def get_user_room_id(self, mid):'''

new_watch_methods = '''    def get_user_room_id(self, mid):'''

if old_watch_methods in content:
    content = content.replace(old_watch_methods, new_watch_methods)
    print("1. 已删除看播页面的旧方法")
else:
    print("1. 未找到看播页面的旧方法")

# ============================================================
# 2. 删除弹幕工具页面的旧方法（_update_danmaku_del_btn_state, _delete_danmaku_room_history, _get_user_room_id）
# ============================================================
old_danmaku_methods = '''    def _update_danmaku_del_btn_state(self):
        """根据下拉框选中内容更新删除按钮状态：仅纯数字历史记录可删"""
        try:
            selected = self.room_combo.get().strip()
            if selected and selected.isdigit() and selected in self.config.get("room_history", []):
                self.room_del_btn.config(state=tk.NORMAL)
            else:
                self.room_del_btn.config(state=tk.DISABLED)
        except Exception:
            self.room_del_btn.config(state=tk.DISABLED)

    def _delete_danmaku_room_history(self):
        """删除当前选中的弹幕直播间历史记录"""
        selected = self.room_combo.get().strip()
        if not selected or not selected.isdigit():
            messagebox.showinfo("提示", "请先从下拉框选择要删除的历史直播间号")
            return
        if "room_history" not in self.config:
            self.config["room_history"] = []
        if selected in self.config["room_history"]:
            self.config["room_history"].remove(selected)
            self.save_config()
            self._refresh_danmaku_room_combo_values()
            self.room_combo.set("")
            self._update_danmaku_del_btn_state()
            self.log(f"已删除直播间历史记录: {selected}")
        else:
            messagebox.showinfo("提示", f"直播间号 {selected} 不在历史记录中")

    def _get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None

    def _get_danmaku_selected_accounts(self):'''

new_danmaku_methods = '''    def _get_danmaku_selected_accounts(self):'''

if old_danmaku_methods in content:
    content = content.replace(old_danmaku_methods, new_danmaku_methods)
    print("2. 已删除弹幕工具页面的旧方法")
else:
    print("2. 未找到弹幕工具页面的旧方法")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
