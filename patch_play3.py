#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改为独立线程持续播放视频流，模拟真实浏览器行为"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换simulate_play为持续播放线程方法
old_simulate = '''    def simulate_play(self, account, room_id):
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

new_play_thread = '''    def play_thread(self, account, room_id):
        """持续播放线程：模拟真实浏览器持续下载视频流"""
        name = account.get("name", "未知")
        cookie = self.get_cookie(account)
        headers = {
            **HEADERS,
            "Cookie": cookie,
            "Referer": f"https://live.bilibili.com/{room_id}",
            "Origin": "https://live.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        play_count = 0
        last_m3u8_refresh = 0
        current_ts_urls = []
        base_url = ""
        
        while not self.stop_flag["stop"]:
            try:
                # 每60秒刷新一次m3u8播放列表（直播流地址会变）
                now = time.time()
                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue
                    resp = requests.get(play_url, headers=headers, timeout=10)
                    if resp.status_code == 200 and "#EXTM3U" in resp.text:
                        lines = resp.text.split("\\n")
                        current_ts_urls = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                        base_url = play_url.rsplit("/", 1)[0]
                        last_m3u8_refresh = now
                    else:
                        time.sleep(5)
                        continue
                
                # 持续下载ts分片（每5秒一个，模拟播放）
                if current_ts_urls:
                    # 轮流下载ts分片
                    ts_url = current_ts_urls[play_count % len(current_ts_urls)]
                    if not ts_url.startswith("http"):
                        ts_url = f"{base_url}/{ts_url}"
                    try:
                        ts_resp = requests.get(ts_url, headers=headers, timeout=8, stream=True)
                        if ts_resp.status_code == 200:
                            # 下载前100KB（模拟播放，不完整下载）
                            ts_resp.raw.read(102400)
                            play_count += 1
                            if play_count % 12 == 0:  # 每分钟打印一次
                                self.log(f"  [{name}] 持续播放中，已下载{play_count}个分片")
                    except Exception:
                        pass
                
                # 模拟播放速度：每5秒一个ts分片（每个ts约1-3秒）
                time.sleep(5)
            except Exception as e:
                self.log(f"  [{name}] 播放线程异常: {e}")
                time.sleep(3)
        
        self.log(f"  [{name}] 播放线程已停止")

    def start_play_threads(self, selected_accounts, room_ids):
        """为每个账户启动持续播放线程"""
        self.play_threads = []
        for acc in selected_accounts:
            for rid in room_ids:
                t = threading.Thread(target=self.play_thread, args=(acc, rid), daemon=True)
                t.start()
                self.play_threads.append(t)
                time.sleep(0.5)  # 错开启动，避免同时请求'''

content = content.replace(old_simulate, new_play_thread, 1)

# 2. 移除等待循环中的播放模拟（改用独立线程）
old_wait_play = '''                # 每15秒执行一次播放模拟（确保5人同时观看状态）
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

new_wait_play = '''                # 播放模拟已移到独立线程（持续播放）'''

content = content.replace(old_wait_play, new_wait_play, 1)

# 3. 移除心跳循环中的播放模拟注释
old_heartbeat_play = '''                # 播放模拟已移到等待循环（每15秒一次）'''
new_heartbeat_play = '''                # 播放模拟在独立线程中持续执行'''
content = content.replace(old_heartbeat_play, new_heartbeat_play, 1)

# 4. 在_watch_loop的进入直播间后，启动播放线程
old_after_enter = '''            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
        # 心跳循环'''

new_after_enter = '''            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
        # 启动持续播放线程（模拟真实浏览器播放）
        self.log("启动持续播放线程...")
        self.start_play_threads(selected_accounts, room_ids)
        # 心跳循环'''

content = content.replace(old_after_enter, new_after_enter, 1)

# 5. 在stop_watch中停止播放线程
old_stop_close = '''        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()'''

new_stop_close = '''        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()
        # 停止播放线程（stop_flag已设置，线程会自动退出）'''

content = content.replace(old_stop_close, new_stop_close, 1)

# 6. 在_on_watch_finished中也确保停止
old_finished_close = '''    def _on_watch_finished(self):
        self.close_all_ws()'''

new_finished_close = '''    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        self.close_all_ws()'''

content = content.replace(old_finished_close, new_finished_close, 1)

# 7. 更新版本号
content = content.replace('APP_VERSION = "v3.7.2"', 'APP_VERSION = "v3.8.0"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.8.0")
print(f"文件大小: {len(content)} 字符")
