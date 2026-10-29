import json
import struct
import time
import threading
import requests
import websocket

room_id = 1791983148

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com/",
}

# 用getConf获取token和服务器
resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}", headers=HEADERS, timeout=10)
data = resp.json()["data"]
token = data["token"]
ws_host = data["host_server_list"][0]["host"]
ws_url = f"wss://{ws_host}/sub"

print(f"获取token成功: {token[:30]}...")
print(f"弹幕服务器: {ws_host}")
print()

HEADER_STRUCT = struct.Struct('>I2H2I')
OP_HEARTBEAT = 2
OP_AUTH = 7

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

class DanmakuClient:
    def __init__(self, name, uid, room_id, ws_url, token):
        self.name = name
        self.uid = uid
        self.room_id = room_id
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self.running = False
        self.connected = False

    def on_message(self, ws, message):
        if len(message) < 16:
            return
        total_len, header_len, ver, op, seq = HEADER_STRUCT.unpack_from(message, 0)
        if op == 8:
            body = message[header_len:total_len]
            result = json.loads(body.decode('utf-8'))
            if result.get("code") == 0:
                self.connected = True
                print(f"  [{self.name}] ✓ 认证成功 (uid={self.uid})")
            else:
                print(f"  [{self.name}] ✗ 认证失败: {result}")
        elif op == 3:
            popularity = struct.unpack('>I', message[header_len:header_len+4])[0]
            print(f"  [{self.name}] 直播间人气: {popularity}")

    def on_error(self, ws, error):
        print(f"  [{self.name}] 错误: {error}")

    def on_close(self, ws, *args):
        self.connected = False

    def on_open(self, ws):
        auth_data = {
            "uid": self.uid,
            "roomid": self.room_id,
            "protover": 2,
            "platform": "web",
            "clientver": "2.6.41",
            "type": 2,
            "key": self.token
        }
        ws.send(pack_data(OP_AUTH, json.dumps(auth_data, separators=(',', ':')).encode()), opcode=websocket.ABNF.OPCODE_BINARY)

    def heartbeat_loop(self):
        while self.running and self.ws:
            try:
                if self.connected:
                    self.ws.send(pack_data(OP_HEARTBEAT, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(30)
            except Exception:
                break

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.running = True
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10, "origin": "https://live.bilibili.com"}, daemon=True).start()

# 测试：3个账户
print("连接测试:")
print()

clients = []
test_accounts = [
    ("t0级长夜月lover", 1728555907),
    ("银河最强流萤", 3546714944310053),
    ("G_TURNER", 315151686),
]

for name, uid in test_accounts:
    print(f"连接 {name}...")
    client = DanmakuClient(name, uid, room_id, ws_url, token)
    client.connect()
    clients.append(client)
    time.sleep(1)

print()
print("等待15秒...")
time.sleep(15)

print()
print(f"认证成功: {sum(1 for c in clients if c.connected)}/{len(clients)}")
print("请查看直播间在线人数是否增加了3人")
print()
print("保持连接30秒后关闭...")
time.sleep(30)

for client in clients:
    client.running = False
    if client.ws:
        client.ws.close()

print("测试完成")
