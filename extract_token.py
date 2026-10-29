import json
import re
import requests

room_id = "1791983148"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://live.bilibili.com/",
    "Connection": "keep-alive",
}

print("访问直播间页面...")
session = requests.Session()
session.headers.update(HEADERS)

# 先访问直播间页面，获取cookie
resp = session.get(f"https://live.bilibili.com/{room_id}", timeout=15)
print(f"页面状态码: {resp.status_code}")
print(f"页面大小: {len(resp.text)} 字节")
print()

# 尝试从HTML中提取弹幕配置
# B站直播间页面通常内嵌了 __NEPTUNE_IS_MY_WAIFU__ 或 window.__INITIAL_STATE__

# 方法1: 查找 __NEPTUNE_IS_MY_WAIFU__
match = re.search(r'window\.__NEPTUNE_IS_MY_WAIFU__\s*=\s*(\{.*?\})\s*</script>', resp.text, re.DOTALL)
if match:
    print("找到 __NEPTUNE_IS_MY_WAIFU__")
    try:
        data = json.loads(match.group(1))
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print(f"解析失败: {e}")
else:
    print("未找到 __NEPTUNE_IS_MY_WAIFU__")

print()

# 方法2: 查找 roomInit 或 danmaku 相关的JSON
patterns = [
    r'"token"\s*:\s*"([^"]+)"',
    r'"host_list"\s*:\s*(\[.*?\])',
    r'"danmaku"\s*:\s*(\{.*?\})',
]

for pattern in patterns:
    matches = re.findall(pattern, resp.text)
    if matches:
        print(f"找到匹配 {pattern[:30]}...: {len(matches)} 个")
        for m in matches[:2]:
            print(f"  {str(m)[:200]}")
        print()

# 方法3: 用获取到的cookie再试getDanmuInfo API
print("用页面cookie再试getDanmuInfo API...")
resp2 = session.get(f"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={room_id}&type=0", timeout=10)
print(f"状态码: {resp2.status_code}")
print(f"返回: {resp2.text[:500]}")
