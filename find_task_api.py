#!/usr/bin/env python3
"""查找任务数据API和观看人数统计方式"""
import requests
import re
import json

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html",
}

# 1. 从页面中提取完整的任务配置JSON
print("=" * 60)
print("1. 提取完整任务配置")
url = "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html"
resp = requests.get(url, headers=headers, timeout=15)
html = resp.text

# 查找包含awardsid的完整JSON对象
# 先找到"观看人数"的位置，然后向前向后查找完整的JSON
idx = html.find("观看人数")
if idx > 0:
    # 向前查找最近的{
    start = html.rfind('{', 0, idx)
    # 向后查找匹配的}
    depth = 0
    end = start
    for i in range(start, min(start+5000, len(html))):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    task_json = html[start:end+1]
    print(f"  观看人数任务JSON ({len(task_json)} 字符):")
    print(f"  {task_json[:1000]}")
    print()

    # 尝试解析
    try:
        task_data = json.loads(task_json)
        print(f"  解析成功:")
        print(f"    alias: {task_data.get('alias')}")
        print(f"    awardsid: {task_data.get('awardsid')}")
        print(f"    awardname: {task_data.get('awardname')}")
        print(f"    list: {task_data.get('list')}")
        print(f"    其他keys: {list(task_data.keys())}")
    except Exception as e:
        print(f"  解析失败: {e}")

# 2. 查找活动ID（window.activity.id）
print("\n" + "=" * 60)
print("2. 查找活动ID")
# 查找 window.activity 相关配置
activity_patterns = [
    r'window\.activity\s*=\s*({.*?});',
    r'"activity"\s*:\s*({[^}]+})',
    r'activity_id["\']?\s*[:=]\s*["\']?(\d+)',
    r'"id"\s*:\s*(\d+)\s*,\s*"name"',
]
for pattern in activity_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"  模式: {pattern[:40]}")
        for m in matches[:3]:
            if isinstance(m, str) and len(m) > 100:
                print(f"    数据块 ({len(m)} 字符): {m[:200]}")
            else:
                print(f"    匹配: {m}")

# 3. 尝试B站活动平台的任务API
print("\n" + "=" * 60)
print("3. 尝试活动平台任务API")
# 从页面URL提取活动标识
activity_sid = "HpDsExY0QvdjkK74"

# 常见的活动平台API
api_tests = [
    # 活动信息
    f"https://api.bilibili.com/x/activity/info?sid={activity_sid}",
    f"https://api.bilibili.com/x/activity/iir?sid={activity_sid}",
    # 任务列表
    f"https://api.bilibili.com/x/activity/task/list?sid={activity_sid}",
    f"https://api.bilibili.com/x/activity/task/info?sid={activity_sid}",
    # 任务进度
    f"https://api.bilibili.com/x/activity/task/progress?sid={activity_sid}",
    f"https://api.bilibili.com/x/activity/user/task?sid={activity_sid}",
    # 奖励
    f"https://api.bilibili.com/x/activity/reward/list?sid={activity_sid}",
    # 直播任务
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/task?sid={activity_sid}",
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/info?sid={activity_sid}",
    # 活动平台新API
    f"https://api.bilibili.com/x/activity/plat/info?sid={activity_sid}",
    f"https://api.bilibili.com/x/activity/plat/task?sid={activity_sid}",
]

for api in api_tests:
    try:
        resp = requests.get(api, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                code = data.get("code")
                msg = data.get("message", "")
                api_name = api.split('?')[0].split('/')[-1]
                if code == 0:
                    print(f"  ✓ {api_name}: code=0, 有数据!")
                    print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:500]}")
                elif code != -404 and code != 404:
                    print(f"  ? {api_name}: code={code}, msg={msg[:60]}")
            except:
                pass
    except:
        pass

# 4. 分析任务配置中的统计字段
print("\n" + "=" * 60)
print("4. 分析任务统计字段")
# 查找所有任务配置，看看有没有统计类型字段
all_tasks = re.findall(r'\{"alias":"([^"]+)".*?"list":\[\{([^}]+)\}\]', html)
print(f"  找到 {len(all_tasks)} 个任务:")
for alias, list_item in all_tasks:
    print(f"    {alias}: {list_item}")

# 5. 查找页面中的API基础URL
print("\n" + "=" * 60)
print("5. 查找API基础URL配置")
base_url_patterns = [
    r'["\']((?:https?:)?//[^"\']*api[^"\']*)["\']',
    r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'apiBase["\']?\s*[:=]\s*["\']([^"\']+)["\']',
]
for pattern in base_url_patterns:
    matches = re.findall(pattern, html)
    for m in set(matches):
        if 'bilibili' in m and 'hdslb' not in m and len(m) < 100:
            print(f"  {m}")

print("\n" + "=" * 60)
print("分析完成")
