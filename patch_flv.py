#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复m3u8请求卡住问题，改回flv直链持续播放"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换get_play_url，改用旧版API返回flv直链（更稳定）
old_get_play = '''    def get_play_url(self, account, room_id):
        """获取直播流URL（新版API，m3u8格式，更接近浏览器）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 新版API：获取m3u8格式播放地址
            url = f"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={room_id}&protocol=0,1&format=0,1,2&codec=0,1&qn=10000&platform=web&ptype=8&dolby=5&panorama=1"
            resp = requests.get(url, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                playurl_info = data.get("playurl_info", {})
                playurl = playurl_info.get("playurl", {})
                stream_list = playurl.get("stream", [])
                for stream in stream_list:
                    format_list = stream.get("format", [])
                    for fmt in format_list:
                        # 优先选m3u8格式（format_name=hls）
                        codec_list = fmt.get("codec", [])
                        for codec in codec_list:
                            base_url = codec.get("base_url", "")
                            url_info = codec.get("url_info", [])
                            if url_info and base_url:
                                host = url_info[0].get("host", "")
                                extra = url_info[0].get("extra", "")
                                full_url = f"{host}{base_url}{extra}"
                                return True, full_url
                return False, "未找到m3u8直播流地址"
            return False, f"API返回code={result.get('code')}, msg={result.get('message')}"
        except Exception as e:
            return False, f"获取异常: {e}"'''

new_get_play = '''    def get_play_url(self, account, room_id):
        """获取直播流URL（旧版API，flv直链，稳定可靠）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 旧版API：直接返回flv播放地址
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

# 2. 替换play_thread中的m3u8播放逻辑，改回flv直链持续播放
old_m3u8_play = '''                    # m3u8格式：持续下载ts分片（模拟真实浏览器播放）
                    try:
                        self.log(f"  [{name}] 正在请求m3u8...")
                        resp = requests.get(play_url, headers=headers, timeout=10)
                        self.log(f"  [{name}] m3u8响应: HTTP {resp.status_code}, 长度{len(resp.content)}")
                        if resp.status_code != 200 or "#EXTM3U" not in resp.text:
                            self.log(f"  [{name}] m3u8内容: {resp.text[:200]}")
                            time.sleep(5)
                            continue
                        # 解析ts分片URL
                        lines = resp.text.split("\\n")
                        ts_urls = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                        if not ts_urls:
                            time.sleep(5)
                            continue
                        base = play_url.rsplit("/", 1)[0]
                        self.log(f"  [{name}] 获取m3u8成功，{len(ts_urls)}个分片，开始播放...")
                        # 持续下载ts分片（每个ts约1-3秒，下载间隔模拟播放速度）
                        ts_index = 0
                        play_start = time.time()
                        while not self.stop_flag["stop"]:
                            # 每60秒刷新一次m3u8（直播流地址会变）
                            if time.time() - play_start > 60:
                                break
                            ts_url = ts_urls[ts_index % len(ts_urls)]
                            if not ts_url.startswith("http"):
                                ts_url = f"{base}/{ts_url}"
                            try:
                                ts_resp = requests.get(ts_url, headers=headers, timeout=10, stream=True)
                                if ts_resp.status_code == 200:
                                    # 下载ts分片（模拟播放，不完整下载）
                                    ts_data = ts_resp.content
                                    play_count += 1
                                    if play_count % 20 == 0:
                                        elapsed = int(time.time() - play_start)
                                        self.log(f"  [{name}] 播放中，已下载{play_count}个分片，持续{elapsed}秒")
                                ts_resp.close()
                            except Exception:
                                pass
                            ts_index += 1
                            # 模拟播放速度：每个ts约2秒，下载后等待
                            time.sleep(2)
                        last_m3u8_refresh = time.time()
                        if self.stop_flag["stop"]:
                            break
                        continue
                    except Exception as e:
                        self.log(f"  [{name}] 播放异常: {e}")
                        time.sleep(5)
                        continue'''

new_flv_play = '''                    # flv直链：保持长连接持续读取（模拟真实播放器）
                    try:
                        self.log(f"  [{name}] 正在连接视频流...")
                        resp = requests.get(play_url, headers=headers, timeout=(10, 30), stream=True)
                        if resp.status_code != 200:
                            self.log(f"  [{name}] 视频流连接失败: HTTP {resp.status_code}")
                            resp.close()
                            time.sleep(5)
                            continue
                        self.log(f"  [{name}] ✓ 视频流连接成功，开始播放...")
                        # 持续读取流数据，保持连接不断开
                        bytes_read = 0
                        play_start = time.time()
                        while not self.stop_flag["stop"]:
                            try:
                                chunk = resp.raw.read(8192)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                                play_count += 1
                                # 每下载约1MB打印一次
                                if bytes_read % 1048576 < 8192:
                                    elapsed = int(time.time() - play_start)
                                    self.log(f"  [{name}] 播放中，已下载{bytes_read//1024}KB，持续{elapsed}秒")
                                # 控制读取速度（约500KB/s，模拟正常播放）
                                time.sleep(0.016)
                                # 每60秒刷新一次播放地址
                                if time.time() - play_start > 60:
                                    break
                            except Exception as e:
                                self.log(f"  [{name}] 读取流异常: {e}")
                                break
                        resp.close()
                        last_m3u8_refresh = time.time()
                        if self.stop_flag["stop"]:
                            break
                        continue
                    except Exception as e:
                        self.log(f"  [{name}] 视频流异常: {e}")
                        time.sleep(5)
                        continue'''

content = content.replace(old_m3u8_play, new_flv_play, 1)

# 3. 更新版本号
content = content.replace('APP_VERSION = "v3.9.2"', 'APP_VERSION = "v3.9.3"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.9.3")
print(f"文件大小: {len(content)} 字符")
