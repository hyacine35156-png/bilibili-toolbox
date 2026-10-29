#!/usr/bin/env python3
"""用正确的活动ID调用任务API"""
import requests
import json

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html",
    "Origin": "https://www.bilibili.com",
}

activity_id = "3ERAcwloghvegb00"

# 1. 活动信息API
print("=" * 60)
print("1. 活动信息API")
info_apis = [
    f"https://api.bilibili.com/x/activity/info?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/iir?sid={activity_id}&mobi_app=web",
    f"https://api.bilibili.com/x/activity/iir?activity_id={activity_id}",
    f"https://api.bilibili.com/x/activity/plat/info?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/detail?sid={activity_id}",
]
for api in info_apis:
    try:
        resp = requests.get(api, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                code = data.get("code")
                msg = data.get("message", "")
                api_name = api.split('?')[0].split('/')[-1]
                if code == 0:
                    print(f"  ✓ {api_name}: code=0!")
                    print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:800]}")
                else:
                    print(f"  ? {api_name}: code={code}, msg={msg[:80]}")
            except:
                print(f"  ? {api_name}: 非JSON")
    except Exception as e:
        print(f"  ✗ {api.split('?')[0].split('/')[-1]}: {e}")

# 2. 任务列表/进度API
print("\n" + "=" * 60)
print("2. 任务列表/进度API")
task_apis = [
    f"https://api.bilibili.com/x/activity/task/list?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/task/info?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/task/progress?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/user/task?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/plat/task?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/mission/list?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/mission/progress?sid={activity_id}",
    # 带mobi_app参数
    f"https://api.bilibili.com/x/activity/task/list?sid={activity_id}&mobi_app=web",
    f"https://api.bilibili.com/x/activity/task/progress?sid={activity_id}&mobi_app=web",
]
for api in task_apis:
    try:
        resp = requests.get(api, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                code = data.get("code")
                msg = data.get("message", "")
                api_name = api.split('?')[0].split('/')[-1]
                if code == 0:
                    print(f"  ✓ {api_name}: code=0!")
                    print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:800]}")
                elif code != -404 and code != 404:
                    print(f"  ? {api_name}: code={code}, msg={msg[:80]}")
            except:
                pass
    except:
        pass

# 3. 直播任务相关API
print("\n" + "=" * 60)
print("3. 直播任务相关API")
live_task_apis = [
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/task?sid={activity_id}",
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/info?sid={activity_id}",
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/progress?sid={activity_id}",
    f"https://api.live.bilibili.com/xlive/app-ucenter/v1/userTask/GetUserTaskProgress",
    # 直播间数据
    f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id=1791983148",
]
for api in live_task_apis:
    try:
        resp = requests.get(api, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                code = data.get("code")
                msg = data.get("message", "")
                api_name = api.split('?')[0].split('/')[-1]
                if code == 0:
                    print(f"  ✓ {api_name}: code=0!")
                    d = data.get("data", {})
                    # 查找观看人数字段
                    for key in ['online', 'watched_num', 'view_num', 'count', 'total', 'online_count']:
                        if key in d:
                            print(f"    {key}: {d[key]}")
                    if 'room_info' in d:
                        ri = d['room_info']
                        print(f"    room_info.online: {ri.get('online')}")
                        print(f"    room_info.watched_num: {ri.get('watched_num')}")
                    print(f"    完整数据: {json.dumps(d, ensure_ascii=False)[:500]}")
                else:
                    print(f"  ? {api_name}: code={code}, msg={msg[:60]}")
            except:
                pass
    except:
        pass

# 4. 尝试POST方法领取/查询任务
print("\n" + "=" * 60)
print("4. 尝试POST方法")
post_apis = [
    ("https://api.bilibili.com/x/activity/task/progress", {"sid": activity_id}),
    ("https://api.bilibili.com/x/activity/user/task", {"sid": activity_id}),
]
for url, data in post_apis:
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        if resp.status_code == 200:
            try:
                result = resp.json()
                print(f"  POST {url.split('/')[-1]}: code={result.get('code')}, msg={result.get('message','')[:60]}")
                if result.get("code") == 0:
                    print(f"    数据: {json.dumps(result.get('data'), ensure_ascii=False)[:500]}")
            except:
                pass
    except:
        pass

print("\n" + "=" * 60)
print("探测完成")
