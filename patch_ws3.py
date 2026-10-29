#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""添加WebSocket连接状态监控和测试弹幕功能"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在heartbeat_loop中添加连接状态日志
old_heartbeat = '''        def heartbeat_loop():
            while client["running"]:
                try:
                    if client["connected"] and client["ws"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                except Exception:
                    pass
                time.sleep(30)'''

new_heartbeat = '''        def heartbeat_loop():
            hb_count = 0
            while client["running"]:
                try:
                    if client["connected"] and client["ws"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                        hb_count += 1
                        # 每2次心跳（60秒）显示一次连接状态
                        if hb_count % 2 == 0:
                            self.log(f"  [{name}] 弹幕连接正常，已发送{hb_count}次心跳")
                    elif not client["connected"]:
                        # 连接未建立，不打印（避免刷屏）
                        pass
                except Exception as e:
                    self.log(f"  [{name}] 弹幕心跳异常: {e}")
                time.sleep(30)'''

content = content.replace(old_heartbeat, new_heartbeat, 1)

# 2. 在on_message中添加心跳响应的人气值日志
old_auth_resp = '''                    if result.get("code") == 0:
                                client["connected"] = True
                                client["reconnect_count"] = 0
                                self.log(f"  [{name}] ✓ 弹幕连接认证成功，已计入在线观众")
                                if name in self.account_stats:
                                    self.account_stats[name]["ws_connected"] = True
                                    self.after(0, self.refresh_status_tree)
                            else:
                                self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")'''

new_auth_resp = '''                    if result.get("code") == 0:
                                client["connected"] = True
                                client["reconnect_count"] = 0
                                self.log(f"  [{name}] ✓ 弹幕连接认证成功(uid={uid})，等待计入在线观众")
                                if name in self.account_stats:
                                    self.account_stats[name]["ws_connected"] = True
                                    self.after(0, self.refresh_status_tree)
                            else:
                                self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")
                    elif op == 3:  # 心跳响应，包含人气值
                        try:
                            popularity = struct.unpack('>I', message[16:20])[0]
                            client["last_popularity"] = popularity
                        except Exception:
                            pass'''

content = content.replace(old_auth_resp, new_auth_resp, 1)

# 3. 在_watch_loop的心跳循环中添加弹幕连接状态检查
old_watch_check = '''                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()'''

new_watch_check = '''                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()
                # 每60秒检查一次弹幕连接状态
                if int(time.time()) % 60 == 0:
                    ws_connected = sum(1 for s in self.account_stats.values() if s.get("ws_connected", False))
                    ws_total = len(self.account_stats)
                    if ws_total > 0:
                        self.log(f"弹幕连接状态: {ws_connected}/{ws_total} 个在线")'''

content = content.replace(old_watch_check, new_watch_check, 1)

# 4. 更新版本号
content = content.replace('APP_VERSION = "v3.6.1"', 'APP_VERSION = "v3.6.2"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.6.2")
print(f"文件大小: {len(content)} 字符")
