import json
import struct
import time
import requests
import websocket

room_id = 1791983148

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com/",
}

resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}", headers=HEADERS, timeout=10)
data = resp.json()["data"]
token = data["token"]

HEADER_STRUCT = struct.Struct('>I2H2I')

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

def test_connection(name, ws_url, uid, token, protover=2):
    """测试单个连接"""
    print(f"测试: {name}")
    print(f"  服务器: {ws_url}")
    print(f"  uid: {uid}, token: {'有' if token else '无'}, protover: {protover}")
    try:
        ws = websocket.create_connection(
            ws_url,
            header=["User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
            timeout=10,
            origin="https://live.bilibili.com"
        )

        auth_data = {
            "uid": uid,
            "roomid": room_id,
            "protover": protover,
            "platform": "web",
            "clientver": "2.6.41",
            "type": 2,
            "key": token
        }
        ws.send(pack_data(7, json.dumps(auth_data, separators=(',', ':')).encode()), opcode=websocket.ABNF.OPCODE_BINARY)

        result = ws.recv()
        if len(result) >= 16:
            total_len, header_len, ver, op, seq = HEADER_STRUCT.unpack_from(result, 0)
            if op == 8:
                body = result[header_len:total_len]
                resp_data = json.loads(body.decode('utf-8'))
                if resp_data.get("code") == 0:
                    print(f"  ✓ 认证成功!")
                    # 测试心跳
                    ws.send(pack_data(2, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
                    hb_result = ws.recv()
                    if len(hb_result) >= 16:
                        _, _, _, hb_op, _ = HEADER_STRUCT.unpack_from(hb_result, 0)
                        if hb_op == 3:
                            pop = struct.unpack('>I', hb_result[16:20])[0]
                            print(f"  ✓ 心跳成功, 直播间人气: {pop}")
                    ws.close()
                    return True
                else:
                    print(f"  ✗ 认证失败: {resp_data}")
            else:
                print(f"  ✗ 未知操作码: {op}")
        ws.close()
    except Exception as e:
        print(f"  ✗ 错误: {type(e).__name__}: {e}")
    print()
    return False

# 测试各种组合
print("=" * 60)
print("WebSocket连接测试矩阵")
print("=" * 60)
print()

# 测试1: 主服务器 + uid=0 + token
test_connection("主服务器+匿名+token", "wss://broadcastlv.chat.bilibili.com/sub", 0, token)

# 测试2: 主服务器 + 真实uid + token
test_connection("主服务器+真实uid+token", "wss://broadcastlv.chat.bilibili.com/sub", 1728555907, token)

# 测试3: 主服务器 + uid=0 + 无token
test_connection("主服务器+匿名+无token", "wss://broadcastlv.chat.bilibili.com/sub", 0, "")

# 测试4: comet服务器 + uid=0 + token
test_connection("comet服务器+匿名+token", "wss://zj-cn-live-comet.chat.bilibili.com/sub", 0, token)

# 测试5: protover=1
test_connection("主服务器+匿名+token+protover1", "wss://broadcastlv.chat.bilibili.com/sub", 0, token, protover=1)
