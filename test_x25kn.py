#!/usr/bin/env python3
"""测试X25Kn E/X协议纯Python实现"""
import hashlib
import hmac
import json
import random
import string
import time
import uuid
import urllib.request
import urllib.parse

ROOM_ID = 1791983148
UP_ID = 3690972101740709  # 灵砂是无敌的

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# 读取账户cookie
with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 用第一个账户测试
acc = accounts[0]
SESSDATA = acc['SESSDATA']
BILI_JCT = acc['bili_jct']
print(f"测试账户: {acc['username']}")

_X25KN_HMAC_FUNCS = ["md5", "sha1", "sha256", "sha224", "sha512", "sha384"]

def x25kn_sign(payload_json, rules, secret_key):
    result = payload_json
    key_bytes = secret_key.encode("utf-8")
    for r in rules:
        if 0 <= r < len(_X25KN_HMAC_FUNCS):
            mac = hmac.new(key_bytes, result.encode("utf-8"),
                           getattr(hashlib, _X25KN_HMAC_FUNCS[r]))
            result = mac.hexdigest()
    return result

def post_form(url, data, timeout=15):
    body = urllib.parse.urlencode(data).encode("utf-8")
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": f"SESSDATA={SESSDATA}; bili_jct={BILI_JCT}",
        "Origin": "https://live.bilibili.com",
        "Referer": f"https://live.bilibili.com/{ROOM_ID}",
    }
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(url, timeout=10):
    headers = {
        "User-Agent": UA,
        "Cookie": f"SESSDATA={SESSDATA}; bili_jct={BILI_JCT}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

# 1. 获取房间区域信息
print("\n=== 1. 获取房间信息 ===")
room_info = get_json(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={ROOM_ID}")
print(f"房间信息响应: code={room_info.get('code')}, message={room_info.get('message')}")
if room_info.get('code') != 0:
    print(f"完整响应: {json.dumps(room_info, ensure_ascii=False)[:500]}")
    # 用旧API
    room_info2 = get_json(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={ROOM_ID}")
    print(f"旧API响应: code={room_info2.get('code')}")
    if room_info2.get('code') == 0:
        area_id = room_info2['data']['area_id']
        parent_area_id = room_info2['data']['parent_area_id']
    else:
        print(f"旧API完整: {json.dumps(room_info2, ensure_ascii=False)[:500]}")
        area_id = 874  # 鸣潮分区
        parent_area_id = 3  # 手游分区
else:
    area_id = room_info['data']['room_info']['area_id']
    parent_area_id = room_info['data']['room_info']['parent_area_id']
print(f"area_id={area_id}, parent_area_id={parent_area_id}")

# 2. 获取LIVE_BUVID
print("\n=== 2. 获取LIVE_BUVID ===")
spi = get_json("https://api.bilibili.com/x/frontend/finger/spi")
buvid = spi['data']['b_3']
print(f"LIVE_BUVID={buvid}")

uuid_str = str(uuid.uuid4())

# 3. E接口
print("\n=== 3. E接口（进入房间）===")
ts = int(time.time() * 1000)
e_form = {
    "id": json.dumps([parent_area_id, area_id, 0, ROOM_ID], separators=(",", ":")),
    "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
    "ts": ts,
    "is_patch": 0,
    "heart_beat": "[]",
    "ua": UA,
    "csrf_token": BILI_JCT,
    "csrf": BILI_JCT,
    "visit_id": "",
    "ruid": UP_ID,
}
e_resp = post_form("https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E", e_form)
print(f"E响应: code={e_resp.get('code')}, message={e_resp.get('message')}")
if e_resp.get('code') == 0:
    e_data = e_resp['data']
    secret_key = e_data['secret_key']
    secret_rule = e_data['secret_rule']
    ets = e_data['timestamp']
    heartbeat_interval = int(e_data.get('heartbeat_interval') or 60)
    print(f"secret_key={secret_key}")
    print(f"secret_rule={secret_rule}")
    print(f"ets={ets}")
    print(f"heartbeat_interval={heartbeat_interval}")
    
    # 4. X接口（等待心跳间隔）
    print(f"\n=== 4. X接口（心跳）===")
    print(f"等待 {heartbeat_interval} 秒后发送第一次心跳...")
    time.sleep(heartbeat_interval)
    
    seq = 1
    ts2 = int(time.time() * 1000)
    sign_payload = {
        "platform": "web",
        "parent_id": parent_area_id,
        "area_id": area_id,
        "seq_id": seq,
        "room_id": ROOM_ID,
        "buvid": buvid,
        "uuid": uuid_str,
        "ets": ets,
        "time": heartbeat_interval,
        "ts": ts2,
    }
    sign_input = json.dumps(sign_payload, separators=(",", ":"))
    print(f"签名输入: {sign_input}")
    s = x25kn_sign(sign_input, secret_rule, secret_key)
    print(f"s={s}")
    
    x_form = {
        "s": s,
        "id": json.dumps([parent_area_id, area_id, seq, ROOM_ID], separators=(",", ":")),
        "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
        "ruid": UP_ID,
        "ets": ets,
        "benchmark": secret_key,
        "time": heartbeat_interval,
        "ts": ts2,
        "ua": UA,
        "csrf_token": BILI_JCT,
        "csrf": BILI_JCT,
        "visit_id": "",
    }
    x_resp = post_form("https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X", x_form)
    print(f"X响应: code={x_resp.get('code')}, message={x_resp.get('message')}")
    if x_resp.get('code') == 0:
        print(f"X数据: {json.dumps(x_resp['data'], ensure_ascii=False)}")
        print("\n✅ 成功！X25Kn E/X协议纯Python实现可用！")
    else:
        print(f"\n❌ X接口失败: {json.dumps(x_resp, ensure_ascii=False)}")
else:
    print(f"\n❌ E接口失败: {json.dumps(e_resp, ensure_ascii=False)}")
