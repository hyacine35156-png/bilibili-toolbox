#!/usr/bin/env python3
"""X25Kn E接口详细测试 - 打印完整请求和响应"""
import requests
import json
import time
import hashlib
import hmac
import uuid

# 读取账户
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

acc = accounts[0]  # 第一个账户
name = acc.get("name", "未知")
print(f"测试账户: {name}")
print(f"SESSDATA: {acc.get('SESSDATA', '')[:20]}...")
print(f"bili_jct: {acc.get('bili_jct', '')[:20]}...")
print(f"DedeUserID: {acc.get('DedeUserID', '')}")

# 构建cookie
cookie = f"SESSDATA={acc.get('SESSDATA','')}; bili_jct={acc.get('bili_jct','')}; DedeUserID={acc.get('DedeUserID','')}"

room_id = "1791983148"
area_id = 874
parent_id = 3
up_id = 3690972101740709

# 获取buvid
print("\n=== 获取LIVE_BUVID ===")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Cookie": cookie}
resp = requests.get("https://api.bilibili.com/x/frontend/finger/spi", headers=headers, timeout=10)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text[:500]}")
spi_data = resp.json()
buvid = spi_data.get("data", {}).get("b_3", "")
print(f"buvid: {buvid}")

uuid_str = str(uuid.uuid4())
print(f"uuid: {uuid_str}")

# E接口
print("\n=== X25Kn E接口 ===")
bili_jct = acc.get("bili_jct", "")
ts = int(time.time() * 1000)

form = {
    "id": json.dumps([parent_id, area_id, 0, room_id], separators=(",", ":")),
    "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
    "ts": ts,
    "is_patch": 0,
    "heart_beat": "[]",
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "csrf_token": bili_jct,
    "csrf": bili_jct,
    "visit_id": "",
    "ruid": up_id,
}

print(f"请求参数:")
for k, v in form.items():
    print(f"  {k}: {v}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": cookie,
    "Origin": "https://live.bilibili.com",
    "Referer": f"https://live.bilibili.com/{room_id}",
}

e_url = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
print(f"\n请求URL: {e_url}")
print(f"请求方法: POST")

try:
    resp = requests.post(e_url, data=form, headers=headers, timeout=15)
    print(f"\n响应状态码: {resp.status_code}")
    print(f"响应头: {dict(resp.headers)}")
    print(f"响应内容: {resp.text}")
    
    result = resp.json()
    print(f"\n解析结果:")
    print(f"  code: {result.get('code')}")
    print(f"  message: {result.get('message')}")
    print(f"  data: {result.get('data')}")
    
    if result.get("code") == 0 and result.get("data"):
        print("\n✓ E接口成功！")
        data = result["data"]
        print(f"  timestamp(ets): {data.get('timestamp')}")
        print(f"  secret_key: {data.get('secret_key')}")
        print(f"  secret_rule: {data.get('secret_rule')}")
        print(f"  heartbeat_interval: {data.get('heartbeat_interval')}")
    else:
        print(f"\n✗ E接口失败: code={result.get('code')}, message={result.get('message')}")
except Exception as e:
    print(f"\n✗ 请求异常: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
