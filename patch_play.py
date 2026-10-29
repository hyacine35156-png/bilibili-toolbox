#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加视频流播放模拟功能，让账户被计入观看人数"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在WatchLiveFrame类中添加获取直播流URL和模拟播放的方法
# 找到send_heartbeat方法，在它后面添加新方法

old_heartbeat_end = '''        except Exception as e:
            return False, f"心跳异常: {e}"

    def start_watch(self):'''

new_methods = '''        except Exception as e:
            return False, f"心跳异常: {e}"

    def get_play_url(self, account, room_id):
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
            return False, f"获取异常: {e}"

    def simulate_play(self, account, room_id):
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
            return False, f"播放异常: {e}"

    def start_watch(self):'''

content = content.replace(old_heartbeat_end, new_methods, 1)

# 2. 在_watch_loop的心跳循环中，添加播放模拟
# 找到发送心跳的代码，在后面添加播放模拟

old_heartbeat_loop = '''                # 对每个直播间发送心跳
                for rid in room_ids:
                    if self.stop_flag["stop"]:
                        break
                    success, msg = self.send_heartbeat(acc, rid)
                    stats["heartbeat_count"] += 1
                    stats["last_heartbeat"] = datetime.now()
                    if not success:
                        self.log(f"  [{name}] 直播间{rid} 心跳失败: {msg}")
                    time.sleep(random.uniform(0.3, 0.8))'''

new_heartbeat_loop = '''                # 对每个直播间发送心跳
                for rid in room_ids:
                    if self.stop_flag["stop"]:
                        break
                    success, msg = self.send_heartbeat(acc, rid)
                    stats["heartbeat_count"] += 1
                    stats["last_heartbeat"] = datetime.now()
                    if not success:
                        self.log(f"  [{name}] 直播间{rid} 心跳失败: {msg}")
                    time.sleep(random.uniform(0.3, 0.8))
                # 模拟播放器播放（每5轮心跳播放一次，避免请求过于频繁）
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    for rid in room_ids:
                        if self.stop_flag["stop"]:
                            break
                        play_success, play_msg = self.simulate_play(acc, rid)
                        if play_success:
                            stats["play_count"] = stats.get("play_count", 0) + 1
                        else:
                            self.log(f"  [{name}] 直播间{rid} 播放模拟: {play_msg}")
                        time.sleep(random.uniform(0.5, 1.0))'''

content = content.replace(old_heartbeat_loop, new_heartbeat_loop, 1)

# 3. 在account_stats初始化中添加play_count字段
old_stats_init = '''            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}'''

new_stats_init = '''            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "play_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}'''

content = content.replace(old_stats_init, new_stats_init, 1)

# 4. 更新版本号
content = content.replace('APP_VERSION = "v3.6.2"', 'APP_VERSION = "v3.7.0"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.7.0")
print(f"文件大小: {len(content)} 字符")
