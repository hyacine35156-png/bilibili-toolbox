import json
import struct
import time
import threading
import requests
import websocket

room_id = 1791983148

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com/",
}

HEADER_STRUCT = struct.Struct('>I2H2I')

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

class RealUserClient:
    def __init__(self, account):
        self.name = account.get("name", "未知")
        self.uid = int(account.get("DedeUserID", "0"))
        self.cookie = f"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}"
        self.ws = None
        self.running = False
        self.connected = False
        self.popularity = 0

    def on_message(self, ws, message):
        if len(message) < 16:
            return
        _, _, _, op, _ = HEADER_STRUCT.unpack_from(message, 0)
        if op == 8:
            body = message[16:]
            result = json.loads(body.decode('utf-8'))
            if result.get("code") == 0:
                self.connected = True
                print(f"  [{self.name}] ✓ 认证成功 (uid={self.uid})")
            else:
                print(f"  [{self.name}] ✗ 认证失败: {result}")
        elif op == 3:
            self.popularity = struct.unpack('>I', message[16:20])[0]

    def on_error(self, ws, error):
        print(f"  [{self.name}] 错误: {error}")

    def on_close(self, ws, *args):
        self.connected = False

    def on_open(self, ws):
        # 用登录cookie获取token
        headers = {**HEADERS, "Cookie": self.cookie}
        resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}", headers=headers, timeout=10)
        token = resp.json()["data"]["token"]

        auth_data = {
            "uid": self.uid,
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
                if self.connected:
                    self.ws.send(pack_data(2, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(10)
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

# 测试：用前3个真实账户连接
print("=" * 60)
print("多真实账户连接测试")
print("=" * 60)
print()

# 初始在线人数
resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=HEADERS, timeout=10)
initial_online = resp.json()["data"]["online"]
print(f"初始在线人数: {initial_online}")
print()

clients = []
for acc in accounts[:3]:
    name = acc.get("name")
    print(f"连接 {name}...")
    client = RealUserClient(acc)
    client.connect()
    clients.append(client)
    time.sleep(2)

print()
print("等待20秒稳定...")
time.sleep(20)

# 最终状态
print()
print(f"认证成功: {sum(1 for c in clients if c.connected)}/{len(clients)}")
popularities = [c.popularity for c in clients if c.popularity > 0]
if popularities:
    print(f"各客户端人气值: {popularities}")

resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=HEADERS, timeout=10)
final_online = resp.json()["data"]["online"]
print(f"API返回在线人数: {final_online}")
print()
print(f"结论: 初始{initial_online}人 -> 最终{final_online}人，增加了{final_online - initial_online}人")
print()
print("请查看直播间在线观众列表，看看这3个账户是否出现在列表中")
print()
print("保持连接30秒后关闭...")
time.sleep(30)

for client in clients:
    client.running = False
    if client.ws:
        client.ws.close()

print("测试完成")
