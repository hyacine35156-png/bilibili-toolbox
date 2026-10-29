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

HEADER_STRUCT = struct.Struct('>I2H2I')

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

class AnonymousClient:
    def __init__(self, name):
        self.name = name
        self.ws = None
        self.running = False
        self.popularity = 0

    def on_message(self, ws, message):
        if len(message) < 16:
            return
        _, _, _, op, _ = HEADER_STRUCT.unpack_from(message, 0)
        if op == 3:  # 心跳响应
            self.popularity = struct.unpack('>I', message[16:20])[0]

    def on_error(self, ws, error):
        pass

    def on_close(self, ws, *args):
        pass

    def on_open(self, ws):
        # 获取新token
        resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}", headers=HEADERS, timeout=10)
        token = resp.json()["data"]["token"]

        auth_data = {
            "uid": 0,
            "roomid": room_id,
            "protover": 2,
            "platform": "web",
            "clientver": "2.6.41",
            "type": 2,
            "key": token
        }
        ws.send(pack_data(7, json.dumps(auth_data, separators=(',', ':')).encode()), opcode=websocket.ABNF.OPCODE_BINARY)

    def heartbeat_loop(self):
        while self.running and self.ws:
            try:
                self.ws.send(pack_data(2, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(10)  # 10秒发一次心跳，快速看到人气变化
            except Exception:
                break

    def connect(self):
        self.ws = websocket.WebSocketApp(
            "wss://broadcastlv.chat.bilibili.com/sub",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.running = True
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        threading.Thread(target=self.ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10, "origin": "https://live.bilibili.com"}, daemon=True).start()

# 测试：逐步增加连接数，观察人气值
print("=" * 60)
print("多匿名连接人气测试")
print("=" * 60)
print()

clients = []

# 先获取初始人气
resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=HEADERS, timeout=10)
initial_online = resp.json()["data"]["online"]
print(f"初始在线人数: {initial_online}")
print()

# 逐步增加连接
for i in range(5):
    client = AnonymousClient(f"匿名{i+1}")
    client.connect()
    clients.append(client)
    print(f"已连接 {i+1} 个匿名客户端...")
    time.sleep(5)

    # 显示各客户端看到的人气值
    popularities = [c.popularity for c in clients if c.popularity > 0]
    if popularities:
        print(f"  人气值(各客户端): {popularities}")
    print()

print("等待15秒稳定...")
time.sleep(15)

# 最终人气
popularities = [c.popularity for c in clients if c.popularity > 0]
print(f"最终人气值(各客户端): {popularities}")

resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=HEADERS, timeout=10)
final_online = resp.json()["data"]["online"]
print(f"API返回在线人数: {final_online}")
print()
print(f"结论: 初始{initial_online}人 -> 最终{final_online}人，增加了{final_online - initial_online}人")
print()

# 关闭所有连接
for client in clients:
    client.running = False
    if client.ws:
        client.ws.close()

print("测试完成，所有连接已关闭")
