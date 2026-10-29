import json
import struct
import requests
import websocket

room_id = 1791983148

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

acc = accounts[0]  # t0级长夜月lover
uid = int(acc.get("DedeUserID", "0"))
cookie = f"SESSDATA={acc.get('SESSDATA', '')}; bili_jct={acc.get('bili_jct', '')}"

print(f"测试账户: {acc.get('name')} (uid={uid})")
print()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com/",
    "Cookie": cookie,
}

# 测试1: 用登录cookie调用getConf
print("测试1: 用登录cookie调用getConf")
resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}", headers=HEADERS, timeout=10)
data = resp.json()
print(f"  code: {data.get('code')}")
if data.get("code") == 0:
    token = data["data"]["token"]
    print(f"  token: {token[:50]}...")
    print(f"  有host_server_list: {'host_server_list' in data['data']}")
print()

# 测试2: 用这个token + 真实uid连接
print("测试2: 登录cookie获取的token + 真实uid连接")
HEADER_STRUCT = struct.Struct('>I2H2I')

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

try:
    ws = websocket.create_connection(
        "wss://broadcastlv.chat.bilibili.com/sub",
        header=["User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
        timeout=10,
        origin="https://live.bilibili.com"
    )

    auth_data = {
        "uid": uid,
        "roomid": room_id,
        "protover": 2,
        "platform": "web",
        "clientver": "2.6.41",
        "type": 2,
        "key": token
    }
    ws.send(pack_data(7, json.dumps(auth_data, separators=(',', ':')).encode()), opcode=websocket.ABNF.OPCODE_BINARY)

    result = ws.recv()
    if len(result) >= 16:
        _, _, _, op, _ = HEADER_STRUCT.unpack_from(result, 0)
        if op == 8:
            body = result[16:]
            resp_data = json.loads(body.decode('utf-8'))
            if resp_data.get("code") == 0:
                print("  ✓ 认证成功!")
                # 心跳
                ws.send(pack_data(2, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
                hb = ws.recv()
                if len(hb) >= 16:
                    _, _, _, hb_op, _ = HEADER_STRUCT.unpack_from(hb, 0)
                    if hb_op == 3:
                        pop = struct.unpack('>I', hb[16:20])[0]
                        print(f"  ✓ 心跳成功, 人气: {pop}")
                ws.close()
            else:
                print(f"  ✗ 认证失败: {resp_data}")
        else:
            print(f"  ✗ 未知操作码: {op}")
except Exception as e:
    print(f"  ✗ 错误: {type(e).__name__}: {e}")
