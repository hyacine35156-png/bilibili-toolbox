import json
import re
import requests

room_id = "1791983148"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://live.bilibili.com/",
}

session = requests.Session()
session.headers.update(HEADERS)
resp = session.get(f"https://live.bilibili.com/{room_id}", timeout=15)

# 解析 __NEPTUNE_IS_MY_WAIFU__
match = re.search(r'window\.__NEPTUNE_IS_MY_WAIFU__\s*=\s*(\{.*?\})\s*</script>', resp.text, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    print("__NEPTUNE_IS_MY_WAIFU__ 所有键:")
    for key in data.keys():
        print(f"  - {key}")
    print()

    # 查找所有包含token/danmaku/host的字段
    def find_tokens(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(word in k.lower() for word in ['token', 'danmaku', 'danmu', 'host', 'websocket', 'ws']):
                    print(f"  找到: {path}.{k} = {str(v)[:200]}")
                find_tokens(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:3]):
                find_tokens(item, f"{path}[{i}]")

    print("搜索token/danmaku相关字段:")
    find_tokens(data)
    print()

# 搜索HTML中所有的token
print("HTML中所有'token'出现位置:")
for m in re.finditer(r'.{0,50}token.{0,100}', resp.text, re.IGNORECASE):
    print(f"  {m.group()[:150]}")
print()

# 试试其他API
print("试试备用API:")
apis = [
    f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}",
    f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}",
]
for api in apis:
    try:
        r = session.get(api, timeout=10)
        print(f"  {api[:60]}...")
        print(f"    返回: {r.text[:300]}")
        print()
    except Exception as e:
        print(f"  错误: {e}")
