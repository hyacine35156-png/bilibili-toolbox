#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加播放线程详细调试日志，改用旧版playUrl API"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换get_play_url方法，改用旧版API并添加调试
old_get_play = '''    def get_play_url(self, account, room_id):
        """获取直播流URL（模拟播放器）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
            }
            url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={room_id}&protocol=0,1&format=0,1,2&codec=0,1&qn=10000&platform=web&ptype=8&dolby=5&panorama=1"
            resp = requests.get(url, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                playurl_info = data.get("playurl_info", {})
                playurl = playurl_info.get("playurl", {})
                stream_list = playurl.get("stream", [])
                if stream_list:
                    # 取第一个流的第一个格式的第一个编码
                    stream = stream_list[0]
                    format_list = stream.get("format", [])
                    if format_list:
                        fmt = format_list[0]
                        codec_list = fmt.get("codec", [])
                        if codec_list:
                            codec = codec_list[0]
                            base_url = codec.get("base_url", "")
                            url_info = codec.get("url_info", [])
                            if url_info and base_url:
                                host = url_info[0].get("host", "")
                                extra = url_info[0].get("extra", "")
                                full_url = f"{host}{base_url}{extra}"
                                return True, full_url
                return False, "未找到直播流地址"
            return False, f"获取失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"获取异常: {e}"'''

new_get_play = '''    def get_play_url(self, account, room_id):
        """获取直播流URL（旧版API，更简单可靠）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            # 旧版API：直接返回播放地址列表
            url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={room_id}&quality=4&platform=web"
            resp = requests.get(url, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                durl = data.get("durl", [])
                if durl:
                    play_url = durl[0].get("url", "")
                    if play_url:
                        return True, play_url
                return False, f"未找到直播流地址，data={str(data)[:200]}"
            return False, f"API返回code={result.get('code')}, msg={result.get('message')}"
        except Exception as e:
            return False, f"获取异常: {e}"'''

content = content.replace(old_get_play, new_get_play, 1)

# 2. 改进play_thread，添加详细调试日志
old_play_thread_start = '''    def play_thread(self, account, room_id):
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
                        continue'''

new_play_thread_start = '''    def play_thread(self, account, room_id):
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
        self.log(f"  [{name}] 播放线程已启动")
        
        while not self.stop_flag["stop"]:
            try:
                # 每60秒刷新一次播放地址（直播流地址会变）
                now = time.time()
                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue
                    # 旧版API返回的可能是flv直链，不是m3u8
                    if ".flv" in play_url or ".m3u8" not in play_url:
                        # 直链格式：直接请求流数据
                        try:
                            resp = requests.get(play_url, headers=headers, timeout=10, stream=True)
                            if resp.status_code == 200:
                                # 持续读取流数据（模拟播放）
                                data = resp.raw.read(102400)
                                play_count += 1
                                last_m3u8_refresh = now
                                if play_count % 12 == 0:
                                    self.log(f"  [{name}] 持续播放中(直链)，已下载{play_count}次，每次100KB")
                                resp.close()
                                time.sleep(5)
                                continue
                            else:
                                self.log(f"  [{name}] 流请求失败: HTTP {resp.status_code}")
                                time.sleep(5)
                                continue
                        except Exception as e:
                            self.log(f"  [{name}] 流请求异常: {e}")
                            time.sleep(5)
                            continue
                    # m3u8格式
                    resp = requests.get(play_url, headers=headers, timeout=10)
                    if resp.status_code == 200 and "#EXTM3U" in resp.text:
                        lines = resp.text.split("\\n")
                        current_ts_urls = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                        base_url = play_url.rsplit("/", 1)[0]
                        last_m3u8_refresh = now
                        self.log(f"  [{name}] 获取m3u8成功，{len(current_ts_urls)}个分片")
                    else:
                        self.log(f"  [{name}] m3u8请求失败: HTTP {resp.status_code}, content={resp.text[:100]}")
                        time.sleep(5)
                        continue'''

content = content.replace(old_play_thread_start, new_play_thread_start, 1)

# 3. 更新版本号
content = content.replace('APP_VERSION = "v3.8.0"', 'APP_VERSION = "v3.8.1"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.8.1")
print(f"文件大小: {len(content)} 字符")
