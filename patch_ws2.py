#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复WebSocket连接：去掉ping/pong，添加自动重连"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 找到connect_ws_danmaku方法并替换
old_method_start = "    def connect_ws_danmaku(self, account, room_id):"
old_method_end = "    def close_all_ws(self):"

start_idx = content.find(old_method_start)
end_idx = content.find(old_method_end)

if start_idx == -1 or end_idx == -1:
    print("找不到方法位置")
    exit(1)

new_method = '''    def connect_ws_danmaku(self, account, room_id):
        """建立WebSocket弹幕连接，让账户出现在在线观众列表中，支持自动重连"""
        if not WEBSOCKET_AVAILABLE:
            self.log(f"  websocket-client未安装，跳过弹幕连接")
            return None

        name = account.get("name", "未知")
        uid = int(account.get("DedeUserID", "0") or "0")

        # B站弹幕协议
        HEADER_STRUCT = struct.Struct('>I2H2I')
        OP_HEARTBEAT = 2
        OP_AUTH = 7

        def pack_data(op, data_bytes):
            header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
            return header + data_bytes

        client = {
            "ws": None, "running": False, "connected": False,
            "heartbeat_thread": None, "reconnect_count": 0,
            "account": account, "room_id": room_id, "name": name
        }

        def do_connect():
            """执行实际连接"""
            try:
                # 获取token
                token, host = self.get_danmu_token(account, room_id)
                if not token:
                    self.log(f"  [{name}] ✗ 获取弹幕token失败")
                    return False

                def on_message(ws, message):
                    try:
                        if len(message) < 16:
                            return
                        _, _, _, op, _ = HEADER_STRUCT.unpack_from(message, 0)
                        if op == 8:  # 认证响应
                            body = message[16:]
                            result = json.loads(body.decode('utf-8'))
                            if result.get("code") == 0:
                                client["connected"] = True
                                client["reconnect_count"] = 0
                                self.log(f"  [{name}] ✓ 弹幕连接认证成功，已计入在线观众")
                                if name in self.account_stats:
                                    self.account_stats[name]["ws_connected"] = True
                                    self.after(0, self.refresh_status_tree)
                            else:
                                self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")
                    except Exception:
                        pass

                def on_error(ws, error):
                    if client["running"] and client["connected"]:
                        err_str = str(error)
                        if "ping/pong" not in err_str and "Connection to remote host was lost" not in err_str:
                            self.log(f"  [{name}] 弹幕连接错误: {error}")

                def on_close(ws, *args):
                    was_connected = client["connected"]
                    client["connected"] = False
                    if name in self.account_stats:
                        self.account_stats[name]["ws_connected"] = False
                    # 自动重连
                    if client["running"] and was_connected:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 10:
                            delay = min(5 * client["reconnect_count"], 30)
                            self.log(f"  [{name}] 弹幕连接断开，{delay}秒后自动重连(第{client['reconnect_count']}次)")
                            threading.Timer(delay, do_connect).start()
                        else:
                            self.log(f"  [{name}] 弹幕重连次数过多，停止重连")

                def on_open(ws):
                    auth_data = {
                        "uid": uid,
                        "roomid": int(room_id),
                        "protover": 2,
                        "platform": "web",
                        "clientver": "2.6.41",
                        "type": 2,
                        "key": token
                    }
                    ws.send(pack_data(OP_AUTH, json.dumps(auth_data, separators=(',', ':')).encode()),
                           opcode=websocket.ABNF.OPCODE_BINARY)

                ws_url = f"wss://{host}/sub"
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                client["ws"] = ws
                # 不使用库级别的ping/pong（B站不响应），只用应用层心跳
                threading.Thread(target=ws.run_forever,
                               kwargs={"origin": "https://live.bilibili.com"},
                               daemon=True).start()
                return True
            except Exception as e:
                self.log(f"  [{name}] 弹幕连接异常: {e}")
                return False

        def heartbeat_loop():
            while client["running"]:
                try:
                    if client["connected"] and client["ws"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                except Exception:
                    pass
                time.sleep(30)

        # 初始连接
        client["running"] = True
        client["heartbeat_thread"] = threading.Thread(target=heartbeat_loop, daemon=True)
        client["heartbeat_thread"].start()
        do_connect()
        return client

'''

content = content[:start_idx] + new_method + content[end_idx:]

# 更新版本号
content = content.replace('APP_VERSION = "v3.6.0"', 'APP_VERSION = "v3.6.1"', 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！v3.6.1")
print(f"文件大小: {len(content)} 字符")
