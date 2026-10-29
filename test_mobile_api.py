import json
import requests

room_id = "1791983148"

# 移动端User-Agent
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://live.bilibili.com/",
}

# 测试各种API
apis = [
    ("移动端API1", f"https://api.live.bilibili.com/xlive/app-room/v1/index/getDanmuInfo?room_id={room_id}"),
    ("移动端API2", f"https://api.live.bilibili.com/xlive/app-room/v1/index/getInfoByRoom?room_id={room_id}"),
    ("PC API带id", f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}&type=0"),
    ("旧API", f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}"),
]

for name, api in apis:
    print(f"测试: {name}")
    print(f"  URL: {api[:70]}...")
    try:
        resp = requests.get(api, headers=MOBILE_HEADERS, timeout=10)
        data = resp.json()
        print(f"  code: {data.get('code')}")
        if data.get("code") == 0:
            print(f"  ✓ 成功!")
            print(f"  data keys: {list(data.get('data', {}).keys())}")
            if "token" in data.get("data", {}):
                print(f"  token: {data['data']['token'][:50]}...")
            if "host_list" in data.get("data", {}):
                print(f"  host_list: {len(data['data']['host_list'])} 个")
        else:
            print(f"  message: {data.get('message')}")
    except Exception as e:
        print(f"  错误: {e}")
    print()
