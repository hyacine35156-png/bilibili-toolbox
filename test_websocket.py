import json
import struct
import time
import threading
import requests
import websocket

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"

with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com",
}

room_id = "1791983148"  # 测试用直播间

# B站弹幕WebSocket协议
HEADER_STRUCT = struct.Struct('>I2H2I')  # 总长度, 头长度, 版本, 操作码, 序列
OP_HEARTBEAT = 2
OP_AUTH = 7
SEQ_ID = 1

def pack_data(op, data_bytes):
    """打包WebSocket数据包"""
    header = HEADER_STRUCT.pack(
        len(data_bytes) + 16,  # 总长度
        16,  # 协议头长度
        1,  # 协议版本
        op,  # 操作码
        SEQ_ID  # 序列ID
    )
    return header + data_bytes

def get_room_real_id(room_id):
    """获取房间真实ID"""
    try:
        resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
                           headers=HEADERS, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["room_id"]
    except Exception as e:
        print(f"获取房间真实ID失败: {e}")
    return int(room_id)

def get_danmu_token(real_room_id, cookie):
    """获取弹幕服务器token"""
    try:
        headers = {**HEADERS, "Cookie": cookie}
        resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={real_room_id}&type=0",
                           headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["token"], data["data"].get("host_list", [])
    except Exception as e:
        print(f"获取弹幕token失败: {e}")
    return None, []

class DanmakuClient:
    """单个账户的弹幕WebSocket连接"""
    def __init__(self, account, real_room_id, token):
        self.account = account
        self.name = account.get("name", "未知")
        self.uid = int(account.get("DedeUserID", "0") or "0")
        self.real_room_id = real_room_id
        self.token = token
        self.ws = None
        self.heartbeat_thread = None
        self.running = False
        self.connected = False

    def on_message(self, ws, message):
        """处理服务器消息"""
        try:
            if len(message) < 16:
                return
            total_len, header_len, ver, op, seq = HEADER_STRUCT.unpack_from(message, 0)
            if op == 8:  # 认证响应
                body = message[header_len:total_len]
                result = json.loads(body.decode('utf-8'))
                if result.get("code") == 0:
                    self.connected = True
                    print(f"  [{self.name}] ✓ WebSocket认证成功，已计入在线观众")
                else:
                    print(f"  [{self.name}] ✗ WebSocket认证失败: {result.get('message')}")
            elif op == 3:  # 心跳响应
                popularity = struct.unpack('>I', message[header_len:header_len+4])[0]
                # 不打印，避免刷屏
        except Exception as e:
            pass

    def on_error(self, ws, error):
        print(f"  [{self.name}] WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print(f"  [{self.name}] WebSocket连接已关闭")

    def on_open(self, ws):
        """连接建立后发送认证包"""
        auth_data = {
            "uid": self.uid,
            "roomid": self.real_room_id,
            "protover": 2,
            "platform": "web",
            "clientver": "2.6.41",
            "type": 2,
            "key": self.token
        }
        auth_bytes = json.dumps(auth_data).encode('utf-8')
        ws.send(pack_data(OP_AUTH, auth_bytes), opcode=websocket.ABNF.OPCODE_BINARY)

    def heartbeat_loop(self):
        """心跳循环"""
        while self.running and self.ws:
            try:
                if self.connected:
                    heartbeat_bytes = b"[object Object]"
                    self.ws.send(pack_data(OP_HEARTBEAT, heartbeat_bytes), opcode=websocket.ABNF.OPCODE_BINARY)
                time.sleep(30)
            except Exception:
                break

    def connect(self):
        """建立连接"""
        try:
            self.ws = websocket.WebSocketApp(
                "wss://broadcastlv.chat.bilibili.com/sub",
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            # 在后台线程运行websocket
            threading.Thread(target=self.ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10}, daemon=True).start()
            return True
        except Exception as e:
            print(f"  [{self.name}] 连接失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

# 测试：用前3个账户连接
print("=" * 60)
print("WebSocket弹幕连接测试")
print("=" * 60)
print()

real_room_id = get_room_real_id(room_id)
print(f"直播间 {room_id} 真实ID: {real_room_id}")
print()

clients = []
for acc in accounts[:3]:
    name = acc.get("name", "未知")
    cookie = f"SESSDATA={acc.get('SESSDATA', '')}; bili_jct={acc.get('bili_jct', '')}"
    print(f"账户: {name}")

    token, host_list = get_danmu_token(real_room_id, cookie)
    if token:
        print(f"  ✓ 获取弹幕token成功")
        client = DanmakuClient(acc, real_room_id, token)
        if client.connect():
            clients.append(client)
            print(f"  ✓ 正在建立WebSocket连接...")
    else:
        print(f"  ✗ 获取弹幕token失败")
    print()

print("等待10秒让连接建立...")
time.sleep(10)

print()
print("=" * 60)
print(f"连接状态: {sum(1 for c in clients if c.connected)}/{len(clients)} 个已认证")
print("请查看直播间在线人数是否增加")
print("=" * 60)
print()
print("保持连接30秒后自动关闭...")
time.sleep(30)

for client in clients:
    client.close()

print("测试完成，所有连接已关闭")
