#!/usr/bin/env python3
"""分析鸣潮3.6创作激励活动页面的任务API"""
import requests
import re
import json

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/",
}

# 1. 获取活动页面HTML
print("=" * 60)
print("1. 获取活动页面")
url = "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html"
resp = requests.get(url, headers=headers, timeout=15)
print(f"  状态码: {resp.status_code}")
print(f"  页面大小: {len(resp.text)} 字符")

# 2. 提取页面中的API接口
print("\n" + "=" * 60)
print("2. 提取页面中的API接口")
# 查找所有API URL
api_patterns = [
    r'https?://[a-zA-Z0-9./_-]*(?:api|activity|task|live|blackboard)[a-zA-Z0-9./_-]*',
    r'["\'](/api/[^"\']+)["\']',
    r'["\'](https?://[^"\']*(?:task|activity|reward|progress)[^"\']*)["\']',
]
all_apis = set()
for pattern in api_patterns:
    matches = re.findall(pattern, resp.text)
    for m in matches:
        if isinstance(m, tuple):
            m = m[0]
        if len(m) > 10 and 'bilibili' in m or m.startswith('/api'):
            all_apis.add(m)

print(f"  找到 {len(all_apis)} 个API链接:")
for api in sorted(all_apis)[:30]:
    print(f"    {api}")

# 3. 查找JS文件（可能包含API调用）
print("\n" + "=" * 60)
print("3. 查找JS文件")
js_pattern = r'src=["\']([^"\']*\.js[^"\']*)["\']'
js_files = re.findall(js_pattern, resp.text)
print(f"  找到 {len(js_files)} 个JS文件:")
for js in js_files[:10]:
    print(f"    {js}")

# 4. 查找活动ID/配置
print("\n" + "=" * 60)
print("4. 查找活动配置")
config_patterns = [
    r'activity_id["\']?\s*[:=]\s*["\']?(\d+)',
    r'act_id["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
    r'sid["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
    r'activity["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
]
for pattern in config_patterns:
    matches = re.findall(pattern, resp.text, re.IGNORECASE)
    if matches:
        print(f"  模式 {pattern[:30]}: {matches[:5]}")

# 5. 查找任务相关关键词
print("\n" + "=" * 60)
print("5. 查找任务相关关键词")
keywords = ["观看人数", "开播任务", "任务进度", "领取资格", "task", "reward", "progress", "mission"]
for kw in keywords:
    count = resp.text.lower().count(kw.lower())
    if count > 0:
        print(f"  '{kw}': 出现 {count} 次")
        # 显示上下文
        idx = resp.text.lower().find(kw.lower())
        if idx > 0:
            context = resp.text[max(0,idx-50):idx+100].replace('\n', ' ')
            print(f"    上下文: ...{context}...")

# 6. 尝试常见的活动任务API
print("\n" + "=" * 60)
print("6. 尝试常见活动任务API")
# 从URL中提取活动ID
activity_id = "HpDsExY0QvdjkK74"
test_apis = [
    f"https://api.bilibili.com/x/activity/info?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/task/list?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/task/progress?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/reward/list?sid={activity_id}",
    f"https://api.bilibili.com/x/activity/live/task?sid={activity_id}",
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/task?sid={activity_id}",
    f"https://api.live.bilibili.com/xlive/app-activity/v1/activity/info?sid={activity_id}",
]
for api in test_apis:
    try:
        resp = requests.get(api, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
                code = data.get("code")
                msg = data.get("message", "")
                print(f"  ✓ {api.split('?')[0].split('/')[-1]}: code={code}, msg={msg[:50]}")
                if code == 0 and data.get("data"):
                    print(f"    数据: {json.dumps(data.get('data'), ensure_ascii=False)[:300]}")
            except:
                print(f"  ? {api.split('?')[0].split('/')[-1]}: 非JSON响应 ({resp.text[:100]})")
        else:
            print(f"  ✗ {api.split('?')[0].split('/')[-1]}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ✗ {api.split('?')[0].split('/')[-1]}: 异常 {e}")

print("\n" + "=" * 60)
print("探测完成")
