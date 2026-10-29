#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加播放线程详细调试日志 + 修复默认全选"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在play_thread中添加详细调试日志
old_play_refresh = '''                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue'''

new_play_refresh = '''                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    self.log(f"  [{name}] 正在获取播放地址...")
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue
                    self.log(f"  [{name}] 播放地址获取成功: {play_url[:80]}...")'''

content = content.replace(old_play_refresh, new_play_refresh, 1)

# 2. 在m3u8请求后添加详细日志
old_m3u8_req = '''                    try:
                        resp = requests.get(play_url, headers=headers, timeout=10)
                        if resp.status_code != 200 or "#EXTM3U" not in resp.text:
                            self.log(f"  [{name}] m3u8请求失败: HTTP {resp.status_code}")
                            time.sleep(5)
                            continue'''

new_m3u8_req = '''                    try:
                        self.log(f"  [{name}] 正在请求m3u8...")
                        resp = requests.get(play_url, headers=headers, timeout=10)
                        self.log(f"  [{name}] m3u8响应: HTTP {resp.status_code}, 长度{len(resp.content)}")
                        if resp.status_code != 200 or "#EXTM3U" not in resp.text:
                            self.log(f"  [{name}] m3u8内容: {resp.text[:200]}")
                            time.sleep(5)
                            continue'''

content = content.replace(old_m3u8_req, new_m3u8_req, 1)

# 3. 修复默认全选：在refresh_account_list中默认全选
# 找到refresh_account_list方法
old_refresh = '''    def refresh_account_list(self):
        """刷新账户列表（复选框形式）"""
        # 清除旧的复选框
        for cb in self.account_checkbuttons:
            cb.destroy()
        self.account_checkbuttons.clear()
        self.account_vars.clear()
        # 创建新的复选框
        for i, acc in enumerate(self.account_mgr.accounts):
            name = acc.get("name", f"账户{i+1}")
            var = tk.BooleanVar(value=False)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_frame, text=name, variable=var,
                                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w")
            cb.pack(fill=tk.X, padx=5, pady=1)
            self.account_checkbuttons.append(cb)'''

new_refresh = '''    def refresh_account_list(self):
        """刷新账户列表（复选框形式，默认全选）"""
        # 清除旧的复选框
        for cb in self.account_checkbuttons:
            cb.destroy()
        self.account_checkbuttons.clear()
        self.account_vars.clear()
        # 创建新的复选框（默认全选）
        for i, acc in enumerate(self.account_mgr.accounts):
            name = acc.get("name", f"账户{i+1}")
            var = tk.BooleanVar(value=True)  # 默认全选
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_frame, text=name, variable=var,
                                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w")
            cb.pack(fill=tk.X, padx=5, pady=1)
            self.account_checkbuttons.append(cb)'''

content = content.replace(old_refresh, new_refresh, 1)

# 4. 更新版本号
content = content.replace('APP_VERSION = "v3.9.0"', 'APP_VERSION = "v3.9.1"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.9.1")
print(f"文件大小: {len(content)} 字符")
