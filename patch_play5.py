#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改为保持flv长连接持续读取，模拟真实播放器"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 替换play_thread中的flv直链播放部分，改为保持长连接
old_flv_play = '''                    # 旧版API返回的可能是flv直链，不是m3u8
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
                            continue'''

new_flv_play = '''                    # 旧版API返回的可能是flv直链，不是m3u8
                    if ".flv" in play_url or ".m3u8" not in play_url:
                        # 直链格式：保持长连接持续读取流数据（模拟真实播放器）
                        try:
                            resp = requests.get(play_url, headers=headers, timeout=30, stream=True)
                            if resp.status_code == 200:
                                self.log(f"  [{name}] 已建立播放连接，持续读取中...")
                                # 持续读取流数据，每次读一小块，保持连接不断开
                                bytes_read = 0
                                connection_start = time.time()
                                while not self.stop_flag["stop"]:
                                    try:
                                        chunk = resp.raw.read(8192)  # 每次读8KB
                                        if not chunk:
                                            break
                                        bytes_read += len(chunk)
                                        play_count += 1
                                        # 每读约1MB打印一次进度
                                        if bytes_read % 1048576 < 8192:
                                            elapsed = int(time.time() - connection_start)
                                            self.log(f"  [{name}] 播放中，已下载{bytes_read//1024}KB，持续{elapsed}秒")
                                        # 控制读取速度（约500KB/s，模拟正常播放）
                                        time.sleep(0.016)
                                        # 每60秒刷新一次播放地址（直播流地址可能过期）
                                        if time.time() - connection_start > 60:
                                            break
                                    except Exception:
                                        break
                                resp.close()
                                last_m3u8_refresh = time.time()
                                if self.stop_flag["stop"]:
                                    break
                                continue
                            else:
                                self.log(f"  [{name}] 流请求失败: HTTP {resp.status_code}")
                                time.sleep(5)
                                continue
                        except Exception as e:
                            self.log(f"  [{name}] 流请求异常: {e}")
                            time.sleep(5)
                            continue'''

content = content.replace(old_flv_play, new_flv_play, 1)

# 更新版本号
content = content.replace('APP_VERSION = "v3.8.1"', 'APP_VERSION = "v3.8.2"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.8.2")
print(f"文件大小: {len(content)} 字符")
