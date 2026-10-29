#!/usr/bin/env python3
"""深入分析活动页面，查找活动ID和任务API"""
import requests
import re
import json

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/",
}

# 获取活动页面
url = "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html"
resp = requests.get(url, headers=headers, timeout=15)
html = resp.text

# 1. 查找所有数字ID（可能是活动ID）
print("=" * 60)
print("1. 查找可能的活动ID（数字）")
# 查找 window.__INITIAL_STATE__ 或类似的初始化数据
init_patterns = [
    r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
    r'window\.__activity_data__\s*=\s*({.*?});',
    r'__NEXT_DATA__.*?>({.*?})</script>',
    r'"activity_id"\s*:\s*(\d+)',
    r'"act_id"\s*:\s*(\d+)',
    r'"sid"\s*:\s*(\d+)',
    r'"id"\s*:\s*(\d+)\s*,\s*"name"',
]
for pattern in init_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"  模式: {pattern[:40]}")
        for m in matches[:3]:
            if isinstance(m, str) and len(m) > 200:
                print(f"    找到数据块 ({len(m)} 字符)")
                # 尝试解析JSON
                try:
                    data = json.loads(m)
                    print(f"    JSON解析成功，keys: {list(data.keys())[:10]}")
                except:
                    print(f"    JSON解析失败，前200字符: {m[:200]}")
            else:
                print(f"    匹配: {m}")

# 2. 查找页面中的JSON数据块
print("\n" + "=" * 60)
print("2. 查找页面中的JSON数据")
json_pattern = r'<script[^>]*>\s*window\.__([A-Z_]+)__\s*=\s*({.*?})\s*;</script>'
matches = re.findall(json_pattern, html, re.DOTALL)
for name, data in matches:
    print(f"  window.__{name}__ ({len(data)} 字符)")
    try:
        j = json.loads(data)
        print(f"    keys: {list(j.keys())[:15]}")
        # 查找活动ID
        for key in ['activity_id', 'act_id', 'sid', 'id']:
            if key in j:
                print(f"    {key}: {j[key]}")
    except:
        print(f"    解析失败")

# 3. 查找API调用模式
print("\n" + "=" * 60)
print("3. 查找API调用模式")
api_call_patterns = [
    r'["\']((?:https?:)?//[^"\']*(?:api|activity|task|live)[^"\']*)["\']',
    r'\.get\(["\']([^"\']+)["\']',
    r'\.post\(["\']([^"\']+)["\']',
    r'fetch\(["\']([^"\']+)["\']',
    r'url\s*:\s*["\']([^"\']+)["\']',
]
all_api_calls = set()
for pattern in api_call_patterns:
    matches = re.findall(pattern, html)
    for m in matches:
        if len(m) > 5 and ('api' in m or 'activity' in m or 'task' in m or 'live' in m or m.startswith('/')):
            all_api_calls.add(m)

print(f"  找到 {len(all_api_calls)} 个API调用:")
for api in sorted(all_api_calls)[:40]:
    print(f"    {api}")

# 4. 查找任务配置数据
print("\n" + "=" * 60)
print("4. 查找任务配置")
# 查找包含"观看人数"或"开播"的JSON数据
task_keywords = ['观看人数', '开播', '观看', 'online', 'viewer']
for kw in task_keywords:
    idx = html.find(kw)
    if idx > 0:
        # 向前查找最近的{
        start = html.rfind('{', 0, idx)
        # 向后查找最近的}
        end = html.find('}', idx)
        if start > 0 and end > 0 and end - start < 2000:
            context = html[start:end+1]
            print(f"  关键词 '{kw}' 附近的JSON:")
            print(f"    {context[:500]}")
            print()

# 5. 下载并分析主要的活动JS文件
print("\n" + "=" * 60)
print("5. 分析活动JS文件")
js_files = re.findall(r'src=["\']([^"\']*activity[^"\']*\.js[^"\']*)["\']', html)
print(f"  找到 {len(js_files)} 个活动相关JS:")
for js in js_files[:5]:
    if js.startswith('//'):
        js = 'https:' + js
    print(f"    下载: {js}")
    try:
        js_resp = requests.get(js, headers=headers, timeout=15)
        js_content = js_resp.text
        # 查找API调用
        api_matches = re.findall(r'["\'](/api/[^"\']+)["\']', js_content)
        if api_matches:
            print(f"      API调用: {list(set(api_matches))[:10]}")
        # 查找任务相关
        task_matches = re.findall(r'["\']([^"\']*(?:task|activity|reward|progress)[^"\']*)["\']', js_content, re.IGNORECASE)
        if task_matches:
            print(f"      任务相关: {list(set(task_matches))[:10]}")
    except Exception as e:
        print(f"      下载失败: {e}")

print("\n" + "=" * 60)
print("分析完成")
