import json
import requests

accounts_file = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\accounts.json"

with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

acc = accounts[0]
cookie = f"SESSDATA={acc.get('SESSDATA', '')}; bili_jct={acc.get('bili_jct', '')}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://live.bilibili.com",
    "Cookie": cookie,
}

room_id = "1791983148"

# 测试1: 获取房间信息
print("测试1: 获取房间信息")
resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}", headers=HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:500]}")
print()

# 测试2: 获取弹幕token (旧API)
print("测试2: 获取弹幕token (旧API)")
resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}&type=0", headers=HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:500]}")
print()

# 测试3: 获取弹幕配置 (新API)
print("测试3: 获取弹幕配置 (新API)")
resp = requests.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}", headers=HEADERS, timeout=10)
print(f"  状态码: {resp.status_code}")
print(f"  返回: {resp.text[:800]}")
print()
