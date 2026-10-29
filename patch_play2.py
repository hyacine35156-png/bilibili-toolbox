#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改进播放模拟（更频繁+真实下载）+ 修复停止卡住"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 改进simulate_play方法：更真实地播放，下载多个ts分片
old_simulate = '''    def simulate_play(self, account, room_id):
        """模拟播放器播放：请求直播流（m3u8），让账户被计入观看人数"""
        try:
            success, play_url = self.get_play_url(account, room_id)
            if not success:
                return False, play_url
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 请求m3u8文件（模拟播放器加载播放列表）
            resp = requests.get(play_url, headers=headers, timeout=15, stream=True)
            if resp.status_code == 200:
                # 读取一部分内容（模拟播放器开始播放）
                content = resp.content[:2048]
                # 如果是m3u8，解析出第一个ts分片并请求（模拟实际播放）
                if b"#EXTM3U" in content or b".m3u8" in play_url:
                    try:
                        text = resp.text
                        lines = text.split("\\n")
                        ts_urls = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
                        if ts_urls:
                            # 请求第一个ts分片（模拟播放第一帧）
                            ts_url = ts_urls[0]
                            if not ts_url.startswith("http"):
                                # 相对路径，拼接基础URL
                                base = play_url.rsplit("/", 1)[0]
                                ts_url = f"{base}/{ts_url}"
                            ts_resp = requests.get(ts_url, headers=headers, timeout=10, stream=True)
                            # 读取一小部分（模拟播放，不下载完整文件）
                            ts_resp.content[:1024]
                            return True, "播放模拟成功(m3u8+ts)"
                    except Exception:
                        pass
                return True, "播放模拟成功(流请求)"
            return False, f"请求失败: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"播放异常: {e}"'''

new_simulate = '''    def simulate_play(self, account, room_id):
        """模拟播放器播放：持续请求视频流分片，让账户被计入观看人数"""
        try:
            success, play_url = self.get_play_url(account, room_id)
            if not success:
                return False, play_url
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 请求m3u8播放列表
            resp = requests.get(play_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return False, f"m3u8请求失败: HTTP {resp.status_code}"
            text = resp.text
            if "#EXTM3U" not in text:
                return False, "非m3u8格式"
            # 解析ts分片URL
            lines = text.split("\\n")
            ts_urls = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
            if not ts_urls:
                return False, "无ts分片"
            base = play_url.rsplit("/", 1)[0]
            # 下载前3个ts分片的部分数据（模拟持续播放3秒）
            downloaded = 0
            for i, ts_url in enumerate(ts_urls[:3]):
                if self.stop_flag and self.stop_flag.get("stop"):
                    break
                if not ts_url.startswith("http"):
                    ts_url = f"{base}/{ts_url}"
                try:
                    ts_resp = requests.get(ts_url, headers=headers, timeout=8, stream=True)
                    if ts_resp.status_code == 200:
                        # 读取前50KB（模拟播放，不完整下载）
                        chunk = ts_resp.raw.read(51200)
                        downloaded += len(chunk)
                except Exception:
                    pass
                time.sleep(0.3)
            if downloaded > 0:
                return True, f"播放模拟成功(下载{downloaded//1024}KB)"
            return False, "ts下载失败"
        except Exception as e:
            return False, f"播放异常: {e}"'''

content = content.replace(old_simulate, new_simulate, 1)

# 2. 改进播放模拟频率：每15秒一次（在等待循环中执行，不依赖心跳轮次）
# 找到等待循环，添加播放模拟计时器
old_wait_loop = '''            for _ in range(wait_segments):
                if self.stop_flag["stop"]:
                    break
                time.sleep(1)
                for name, stats in self.account_stats.items():
                    if stats["status"] == "观看中":
                        stats["watch_seconds"] += 1
                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()
                # 每60秒检查一次弹幕连接状态
                if int(time.time()) % 60 == 0:
                    ws_connected = sum(1 for s in self.account_stats.values() if s.get("ws_connected", False))
                    ws_total = len(self.account_stats)
                    if ws_total > 0:
                        self.log(f"弹幕连接状态: {ws_connected}/{ws_total} 个在线")'''

new_wait_loop = '''            for _ in range(wait_segments):
                if self.stop_flag["stop"]:
                    break
                time.sleep(1)
                for name, stats in self.account_stats.items():
                    if stats["status"] == "观看中":
                        stats["watch_seconds"] += 1
                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()
                # 每60秒检查一次弹幕连接状态
                if int(time.time()) % 60 == 0:
                    ws_connected = sum(1 for s in self.account_stats.values() if s.get("ws_connected", False))
                    ws_total = len(self.account_stats)
                    if ws_total > 0:
                        self.log(f"弹幕连接状态: {ws_connected}/{ws_total} 个在线")
                # 每15秒执行一次播放模拟（确保5人同时观看状态）
                if int(time.time()) % 15 == 0:
                    for acc in selected_accounts:
                        if self.stop_flag["stop"]:
                            break
                        name = acc.get("name", "未知")
                        stats = self.account_stats.get(name)
                        if not stats or stats["status"] != "观看中":
                            continue
                        for rid in room_ids:
                            if self.stop_flag["stop"]:
                                break
                            play_success, play_msg = self.simulate_play(acc, rid)
                            if play_success:
                                stats["play_count"] = stats.get("play_count", 0) + 1
                            else:
                                self.log(f"  [{name}] 播放: {play_msg}")
                            time.sleep(0.2)'''

content = content.replace(old_wait_loop, new_wait_loop, 1)

# 3. 移除心跳循环中的播放模拟（已移到等待循环，避免重复）
old_heartbeat_play = '''                # 模拟播放器播放（每分钟一次，确保5人同时观看状态）
                if True:
                    for rid in room_ids:
                        if self.stop_flag["stop"]:
                            break
                        play_success, play_msg = self.simulate_play(acc, rid)
                        if play_success:
                            stats["play_count"] = stats.get("play_count", 0) + 1
                        else:
                            self.log(f"  [{name}] 直播间{rid} 播放模拟: {play_msg}")
                        time.sleep(random.uniform(0.5, 1.0))'''

new_heartbeat_play = '''                # 播放模拟已移到等待循环（每15秒一次）'''

content = content.replace(old_heartbeat_play, new_heartbeat_play, 1)

# 4. 修复close_all_ws：添加超时，避免卡住
old_close_ws = '''    def close_all_ws(self):
        """关闭所有WebSocket弹幕连接"""
        for name, client in self.ws_clients.items():
            if client:
                client["running"] = False
                if client.get("ws"):
                    try:
                        client["ws"].close()
                    except Exception:
                        pass
        self.ws_clients.clear()'''

new_close_ws = '''    def close_all_ws(self):
        """关闭所有WebSocket弹幕连接（带超时，避免卡住）"""
        for name, client in self.ws_clients.items():
            if client:
                client["running"] = False
                if client.get("ws"):
                    try:
                        # 设置关闭超时，避免阻塞
                        ws = client["ws"]
                        ws.sock = None  # 强制断开
                        ws.close()
                    except Exception:
                        pass
        self.ws_clients.clear()'''

content = content.replace(old_close_ws, new_close_ws, 1)

# 5. 修复stop_watch：确保立即停止，不等待
old_stop = '''    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        # 关闭所有WebSocket弹幕连接
        self.close_all_ws()
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")'''

new_stop = '''    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")'''

content = content.replace(old_stop, new_stop, 1)

# 6. 更新版本号
content = content.replace('APP_VERSION = "v3.7.1"', 'APP_VERSION = "v3.7.2"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.7.2")
print(f"文件大小: {len(content)} 字符")
