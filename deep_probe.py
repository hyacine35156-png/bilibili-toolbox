#!/usr/bin/env python3
"""深入查找任务进度API和观看人数统计方式"""
import requests
import json
import re

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html",
}

# 1. 下载活动平台的核心JS，分析API调用
print("=" * 60)
print("1. 分析活动平台JS中的API调用")

# 获取页面中的JS文件
url = "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html"
resp = requests.get(url, headers=headers, timeout=15)
html = resp.text

# 查找所有JS文件
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
print(f"  找到 {len(js_files)} 个JS文件")

# 下载并分析每个JS文件中的API调用
all_apis = set()
for js in js_files:
    if js.startswith('//'):
        js = 'https:' + js
    elif js.startswith('/'):
        js = 'https://www.bilibili.com' + js
    try:
        js_resp = requests.get(js, headers=headers, timeout=15)
        js_content = js_resp.text
        # 查找API调用
        api_matches = re.findall(r'["\'](/(?:x|api|activity|live)/[^"\']+)["\']', js_content)
        for api in api_matches:
            if len(api) > 5 and len(api) < 100:
                all_apis.add(api)
        # 查找任务相关关键词
        if 'task' in js_content.lower() or 'progress' in js_content.lower() or 'mission' in js_content.lower():
            js_name = js.split('/')[-1]
            # 查找具体的API路径
            task_apis = re.findall(r'["\']([^"\']*(?:task|progress|mission|reward)[^"\']*)["\']', js_content, re.IGNORECASE)
            if task_apis:
                print(f"  {js_name}: 任务相关API: {list(set(task_apis))[:5]}")
    except Exception as e:
        pass

print(f"\n  所有API路径 ({len(all_apis)} 个):")
for api in sorted(all_apis):
    print(f"    {api}")

# 2. 尝试找到的API
print("\n" + "=" * 60)
print("2. 尝试找到的API")
activity_id = "3ERAcwloghvegb00"
for api in sorted(all_apis):
    if any(kw in api.lower() for kw in ['task', 'progress', 'mission', 'reward', 'activity', 'live']):
        full_url = f"https://api.bilibili.com{api}"
        if '?' in full_url:
            full_url += f"&sid={activity_id}"
        else:
            full_url += f"?sid={activity_id}"
        try:
            resp = requests.get(full_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    code = data.get("code")
                    if code == 0:
                        print(f"  ✓ {api}: code=0!")
                        print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:500]}")
                    elif code not in [-404, 404, -400]:
                        print(f"  ? {api}: code={code}, msg={data.get('message','')[:60]}")
                except:
                    pass
        except:
            pass

# 3. 分析直播间观看人数统计
print("\n" + "=" * 60)
print("3. 直播间观看人数统计分析")
room_id = 1791983148
# 获取直播间详细信息
url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}"
resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()
if data.get("code") == 0:
    room_info = data.get("data", {}).get("room_info", {})
    print(f"  直播间标题: {room_info.get('title')}")
    print(f"  分区: {room_info.get('parent_area_name')} - {room_info.get('area_name')}")
    print(f"  area_id: {room_info.get('area_id')}")
    print(f"  parent_area_id: {room_info.get('parent_area_id')}")
    print(f"  在线人数(online): {room_info.get('online')}")
    print(f"  看过数(watched_num): {room_info.get('watched_num')}")
    print(f"  开播时间: {room_info.get('live_start_time')}")
    print(f"  直播状态: {room_info.get('live_status')} (1=直播中)")

# 4. 获取直播间在线观众列表
print("\n" + "=" * 60)
print("4. 直播间在线观众列表")
url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?room_id={room_id}"
resp = requests.get(url, headers=headers, timeout=10)
try:
    data = resp.json()
    print(f"  code: {data.get('code')}")
    if data.get("code") == 0:
        print(f"  数据: {json.dumps(data.get('data'), ensure_ascii=False)[:500]}")
except:
    print(f"  响应: {resp.text[:200]}")

print("\n" + "=" * 60)
print("分析完成")
