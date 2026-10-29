import json
import struct
import websocket

room_id = 1791983148
test_uid = 1728555907  # t0级长夜月lover的UID

HEADER_STRUCT = struct.Struct('>I2H2I')

def pack_data(op, data_bytes):
    header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
    return header + data_bytes

print("测试: 真实uid + protover=2 + 标准请求头")
print("=" * 60)

try:
    # 不手动加Origin，让websocket库自己处理
    ws = websocket.create_connection(
        "wss://broadcastlv.chat.bilibili.com/sub",
        header=[
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ],
        timeout=15,
        origin="https://live.bilibili.com"
    )
    print("WebSocket连接建立成功!")

    # 发送认证包 (真实uid, protover=2)
    auth_data = {
        "uid": test_uid,
        "roomid": room_id,
        "protover": 2,
        "platform": "web",
        "clientver": "2.6.41",
        "type": 2,
        "key": ""
    }
    auth_bytes = json.dumps(auth_data, separators=(',', ':')).encode()
    ws.send(pack_data(7, auth_bytes), opcode=websocket.ABNF.OPCODE_BINARY)
    print(f"认证包已发送 (uid={test_uid}, protover=2)")

    # 接收响应
    result = ws.recv()
    print(f"收到响应，长度: {len(result)}")
    if len(result) >= 16:
        total_len, header_len, ver, op, seq = HEADER_STRUCT.unpack_from(result, 0)
        print(f"  操作码: {op} (8=认证响应)")
        if op == 8:
            body = result[header_len:total_len]
            print(f"  响应内容: {body.decode('utf-8', errors='ignore')}")

    # 发送心跳
    ws.send(pack_data(2, b"[object Object]"), opcode=websocket.ABNF.OPCODE_BINARY)
    print("心跳包已发送")

    # 接收心跳响应
    result = ws.recv()
    print(f"收到心跳响应，长度: {len(result)}")
    if len(result) >= 16:
        total_len, header_len, ver, op, seq = HEADER_STRUCT.unpack_from(result, 0)
        print(f"  操作码: {op} (3=心跳响应)")
        if op == 3:
            popularity = struct.unpack('>I', result[header_len:header_len+4])[0]
            print(f"  直播间人气: {popularity}")

    ws.close()
    print("\n✓ 测试成功! WebSocket连接正常")

except Exception as e:
    print(f"\n✗ 错误: {type(e).__name__}: {e}")
