#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修改main_gui_pro.py，添加WebSocket弹幕连接功能"""

import re

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加import struct和websocket
old_import = "import urllib.parse\nfrom datetime import datetime, timedelta"
new_import = "import urllib.parse\nimport struct\nfrom datetime import datetime, timedelta"
content = content.replace(old_import, new_import, 1)

old_requests = "import requests\n\n# ========== 配色方案 =========="
new_requests = """import requests

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ========== 配色方案 =========="""
content = content.replace(old_requests, new_requests, 1)

# 2. 更新版本号
content = content.replace('APP_VERSION = "v3.5.1"', 'APP_VERSION = "v3.6.0"', 1)

# 3. 在WatchLiveFrame类的__init__中添加ws_clients
old_init = "        self.account_stats = {}\n        self.account_vars = {}  # 每个账户名对应一个BooleanVar"
new_init = "        self.account_stats = {}\n        self.ws_clients = {}  # 存储WebSocket弹幕连接 {账户名: client}\n        self.account_vars = {}  # 每个账户名对应一个BooleanVar"
content = content.replace(old_init, new_init, 1)

# 4. 在WatchLiveFrame类中添加WebSocket相关方法（在get_cookie方法之前）
old_get_cookie = "    def get_cookie(self, account):\n        return f\"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}\""

new_ws_methods = '''    def get_danmu_token(self, account, room_id):
        """用登录cookie获取弹幕服务器token"""
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie}
            resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}",
                               headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data["data"].get("token", ""), data["data"].get("host", "broadcastlv.chat.bilibili.com")
        except Exception as e:
            self.log(f"  获取弹幕token异常: {e}")
        return "", "broadcastlv.chat.bilibili.com"

    def connect_ws_danmaku(self, account, room_id):
        """建立WebSocket弹幕连接，让账户出现在在线观众列表中"""
        if not WEBSOCKET_AVAILABLE:
            self.log(f"  websocket-client未安装，跳过弹幕连接")
            return None

        name = account.get("name", "未知")
        uid = int(account.get("DedeUserID", "0") or "0")

        # 获取token
        token, host = self.get_danmu_token(account, room_id)
        if not token:
            self.log(f"  [{name}] ✗ 获取弹幕token失败")
            return None

        # B站弹幕协议
        HEADER_STRUCT = struct.Struct('>I2H2I')
        OP_HEARTBEAT = 2
        OP_AUTH = 7

        def pack_data(op, data_bytes):
            header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
            return header + data_bytes

        client = {"ws": None, "running": False, "connected": False, "heartbeat_thread": None}

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
                        self.log(f"  [{name}] ✓ 弹幕连接认证成功，已计入在线观众")
                        if name in self.account_stats:
                            self.account_stats[name]["ws_connected"] = True
                            self.after(0, self.refresh_status_tree)
                    else:
                        self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")
            except Exception:
                pass

        def on_error(ws, error):
            if client["running"]:
                self.log(f"  [{name}] 弹幕连接错误: {error}")

        def on_close(ws, *args):
            client["connected"] = False
            if name in self.account_stats:
                self.account_stats[name]["ws_connected"] = False

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

        def heartbeat_loop():
            while client["running"] and client["ws"]:
                try:
                    if client["connected"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                    time.sleep(30)
                except Exception:
                    break

        try:
            ws_url = f"wss://{host}/sub"
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            client["ws"] = ws
            client["running"] = True
            client["heartbeat_thread"] = threading.Thread(target=heartbeat_loop, daemon=True)
            client["heartbeat_thread"].start()
            threading.Thread(target=ws.run_forever,
                           kwargs={"ping_interval": 20, "ping_timeout": 10, "origin": "https://live.bilibili.com"},
                           daemon=True).start()
            return client
        except Exception as e:
            self.log(f"  [{name}] 弹幕连接异常: {e}")
            return None

    def close_all_ws(self):
        """关闭所有WebSocket弹幕连接"""
        for name, client in self.ws_clients.items():
            if client:
                client["running"] = False
                if client.get("ws"):
                    try:
                        client["ws"].close()
                    except Exception:
                        pass
        self.ws_clients.clear()

    def get_cookie(self, account):
        return f"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}"'''

content = content.replace(old_get_cookie, new_ws_methods, 1)

# 5. 修改_watch_loop，在进入直播间后建立WebSocket连接
old_enter_success = """            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))"""

new_enter_success = """            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
                self.account_stats[name]["ws_connected"] = False
                # 建立WebSocket弹幕连接（对第一个直播间建立连接，让账户出现在在线观众列表）
                if WEBSOCKET_AVAILABLE and room_ids:
                    self.log(f"  [{name}] 正在建立弹幕连接...")
                    ws_client = self.connect_ws_danmaku(acc, room_ids[0])
                    if ws_client:
                        self.ws_clients[name] = ws_client
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))"""

content = content.replace(old_enter_success, new_enter_success, 1)

# 6. 修改stop_watch，关闭所有WebSocket连接
old_stop = """        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")"""

new_stop = """        # 关闭所有WebSocket弹幕连接
        self.close_all_ws()
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")"""

content = content.replace(old_stop, new_stop, 1)

# 7. 修改refresh_status_tree，显示WebSocket连接状态
old_tree = """    def refresh_status_tree(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name, {"status": "待开始", "watch_seconds": 0, "heartbeat_count": 0})
            watch_min = stats.get("watch_seconds", 0) // 60
            watch_sec = stats.get("watch_seconds", 0) % 60
            self.status_tree.insert("", tk.END, values=(name, stats.get("status", "待开始"), f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))"""

new_tree = """    def refresh_status_tree(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name, {"status": "待开始", "watch_seconds": 0, "heartbeat_count": 0})
            watch_min = stats.get("watch_seconds", 0) // 60
            watch_sec = stats.get("watch_seconds", 0) % 60
            ws_status = "✓在线" if stats.get("ws_connected", False) else ""
            status_text = stats.get("status", "待开始")
            if ws_status:
                status_text = f"{status_text} {ws_status}"
            self.status_tree.insert("", tk.END, values=(name, status_text, f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))"""

content = content.replace(old_tree, new_tree, 1)

# 8. 修改_on_watch_finished，关闭WebSocket
old_finished = """    def _on_watch_finished(self):
        self.start_btn.config(state=tk.NORMAL)"""

new_finished = """    def _on_watch_finished(self):
        self.close_all_ws()
        self.start_btn.config(state=tk.NORMAL)"""

content = content.replace(old_finished, new_finished, 1)

# 9. 更新窗口标题
content = content.replace(
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务")',
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务(WebSocket在线)")',
    1
)

# 保存修改
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成！")
print(f"文件大小: {len(content)} 字符")
