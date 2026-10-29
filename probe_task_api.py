#!/usr/bin/env python3
"""探测B站直播任务完成条件API"""
import requests
import json

# 主播账户（灵砂是无敌的）
cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}

room_id = 1791983148

# 1. 获取直播间实时在线人数
print("=" * 60)
print("1. 直播间实时在线人数")
url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
if data.get("code") == 0:
    room_data = data.get("data", {})
    print(f"  在线人数(online): {room_data.get('online')}")
    print(f"  看过数: {room_data.get('watched_num', 'N/A')}")
    print(f"  房间状态: {room_data.get('live_status')} (0=未开播, 1=直播中)")

# 2. 获取直播间在线观众列表
print("\n" + "=" * 60)
print("2. 直播间在线观众列表")
url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}"
resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
print(f"  code: {data.get('code')}, message: {data.get('message')}")
if data.get("code") == 0:
    room_info = data.get("data", {}).get("room_info", {})
    print(f"  在线人数: {room_info.get('online')}")
    print(f"  看过数: {room_info.get('watched_num', 'N/A')}")

# 3. 直播任务进度
print("\n" + "=" * 60)
print("3. 直播APP任务进度")
url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/GetUserTaskProgress"
resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
print(f"  code: {data.get('code')}, message: {data.get('message')}")
if data.get("code") == 0:
    print(f"  数据: {json.dumps(data.get('data'), ensure_ascii=False, indent=2)[:2000]}")

# 4. 尝试获取任务列表
print("\n" + "=" * 60)
print("4. 直播任务列表")
task_urls = [
    "https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/GetTaskList",
    "https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/GetUserTaskList",
    "https://api.live.bilibili.com/xlive/web-room/v1/index/getUserTask",
]
for url in task_urls:
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        print(f"  {url.split('/')[-1]}: code={data.get('code')}, msg={data.get('message')}")
        if data.get("code") == 0 and data.get("data"):
            print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"  {url.split('/')[-1]}: 异常 {e}")

# 5. 主播中心数据
print("\n" + "=" * 60)
print("5. 主播中心直播数据")
url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/userInfo/getUserInfo"
resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
print(f"  code: {data.get('code')}, message: {data.get('message')}")
if data.get("code") == 0:
    print(f"  数据: {json.dumps(data.get('data'), ensure_ascii=False, indent=2)[:1500]}")

# 6. 直播间实时数据（可能包含观看人数统计）
print("\n" + "=" * 60)
print("6. 直播间实时数据接口")
realtime_urls = [
    f"https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?room_id={room_id}",
    f"https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomPlayInfo?room_id={room_id}",
]
for url in realtime_urls:
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        print(f"  {url.split('/')[-1]}: code={data.get('code')}")
        if data.get("code") == 0 and data.get("data"):
            d = data.get("data", {})
            # 查找在线人数字段
            for key in ["online", "watched_num", "view_num", "count", "total"]:
                if key in d:
                    print(f"    {key}: {d[key]}")
    except Exception as e:
        print(f"  异常: {e}")

print("\n" + "=" * 60)
print("探测完成")
