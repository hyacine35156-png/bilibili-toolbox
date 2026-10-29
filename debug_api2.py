import json
import requests

room_id = "1791983148"

# 完整的浏览器请求头
FULL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://live.bilibili.com",
    "Referer": f"https://live.bilibili.com/{room_id}",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# 测试1: 匿名获取弹幕token
print("测试1: 匿名获取弹幕token")
resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}&type=0", headers=FULL_HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:800]}")
print()

# 测试2: 带cookie获取
accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)
acc = accounts[0]
cookie = f"SESSDATA={acc.get('SESSDATA', '')}; bili_jct={acc.get('bili_jct', '')}"
FULL_HEADERS["Cookie"] = cookie

print("测试2: 带cookie+完整请求头获取弹幕token")
resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}&type=0", headers=FULL_HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:800]}")
print()

# 测试3: 另一个API地址
print("测试3: 备用API地址")
resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?roomid={room_id}", headers=FULL_HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:500]}")
