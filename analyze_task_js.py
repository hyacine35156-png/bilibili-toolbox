#!/usr/bin/env python3
"""深入分析任务组件JS，找任务进度API和统计逻辑"""
import requests
import re
import json

cookie = "SESSDATA=719a9f90%2C1803972528%2Cafcbd%2A92CjAXVzI_SFYa5fg54z4gm7Vi1l6NUX1q08UcLDnNHI_jwaqvmhuBRYd2fBzfc8b9agQSVkZ4b3R6eDhxd2V5eWhLQzJqQi1lTm9IS1NiSVpoajl2RUZKRUtzNUVwZ19CX0hYT1lTTHlEWDVzN25fY1FKN2ppVE1sbHppZjJmRi1yRzBwaUxtM25nIIEC; bili_jct=499f38b6a5bdf6dc1b48ea9333bca67d; DedeUserID=3690972101740709"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Cookie": cookie,
    "Referer": "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html",
}

# 1. 获取页面中的所有JS文件
print("=" * 60)
print("1. 获取活动页面JS文件列表")
url = "https://www.bilibili.com/blackboard/era/HpDsExY0QvdjkK74.html"
resp = requests.get(url, headers=headers, timeout=15)
html = resp.text

# 查找所有JS文件（包括activity-plat的）
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
# 也查找页面中引用的其他JS
js_files += re.findall(r'["\']((?:https?:)?//[^"\']*activity[^"\']*\.js[^"\']*)["\']', html)

print(f"  找到 {len(js_files)} 个JS文件")

# 2. 下载并分析任务相关的JS
print("\n" + "=" * 60)
print("2. 分析任务相关JS")
task_keywords = ['task', 'progress', 'mission', 'reward', 'send_points', 'cur_value', 'limit', '观看人数', '开播']

for js in js_files:
    if js.startswith('//'):
        js = 'https:' + js
    elif js.startswith('/'):
        js = 'https://www.bilibili.com' + js
    
    js_name = js.split('/')[-1]
    # 只分析可能与任务相关的JS
    if not any(kw in js_name.lower() for kw in ['task', 'eva', 'activity', 'open', 'live', 'index', 'app']):
        continue
    
    try:
        js_resp = requests.get(js, headers=headers, timeout=15)
        js_content = js_resp.text
        
        # 查找API调用
        api_calls = re.findall(r'["\'](/(?:x|api|activity|live)/[^"\']{5,80})["\']', js_content)
        task_apis = [api for api in set(api_calls) if any(kw in api.lower() for kw in ['task', 'progress', 'mission', 'reward', 'points', 'activity'])]
        
        # 查找任务相关关键词
        has_task_content = any(kw in js_content for kw in task_keywords)
        
        if task_apis or has_task_content:
            print(f"\n  ★ {js_name} ({len(js_content)} 字符)")
            if task_apis:
                print(f"    任务API: {task_apis}")
            # 查找send_points相关代码
            if 'send_points' in js_content:
                idx = js_content.find('send_points')
                context = js_content[max(0,idx-200):idx+300]
                print(f"    send_points上下文: {context[:400]}")
            # 查找cur_value相关代码
            if 'cur_value' in js_content:
                idx = js_content.find('cur_value')
                context = js_content[max(0,idx-100):idx+200]
                print(f"    cur_value上下文: {context[:300]}")
            # 查找任务进度获取逻辑
            if 'progress' in js_content.lower():
                progress_matches = re.findall(r'["\']([^"\']*progress[^"\']*)["\']', js_content, re.IGNORECASE)
                if progress_matches:
                    print(f"    progress相关: {list(set(progress_matches))[:5]}")
                    
    except Exception as e:
        pass

# 3. 专门分析EvaTaskButton.js
print("\n" + "=" * 60)
print("3. 专门分析EvaTaskButton.js")
for js in js_files:
    if 'EvaTaskButton' in js or 'TaskButton' in js:
        if js.startswith('//'):
            js = 'https:' + js
        print(f"  下载: {js}")
        try:
            js_resp = requests.get(js, headers=headers, timeout=15)
            js_content = js_resp.text
            # 查找所有API路径
            all_apis = re.findall(r'["\'](/[^"\']{5,100})["\']', js_content)
            print(f"  所有API路径: {list(set(all_apis))[:20]}")
            # 查找request调用
            request_calls = re.findall(r'(?:url|api|endpoint)\s*[:=]\s*["\']([^"\']+)["\']', js_content)
            print(f"  request URL: {list(set(request_calls))[:10]}")
            # 查找任务状态判断逻辑
            if 'status' in js_content:
                status_matches = re.findall(r'status\s*[=!]==?\s*(\d+)', js_content)
                print(f"  状态判断: {list(set(status_matches))}")
            # 查找完整的任务数据结构
            if 'taskItem' in js_content:
                idx = js_content.find('taskItem')
                context = js_content[max(0,idx-100):idx+500]
                print(f"  taskItem上下文: {context[:600]}")
        except Exception as e:
            print(f"  错误: {e}")

# 4. 分析活动页面的数据源配置
print("\n" + "=" * 60)
print("4. 分析活动页面数据源配置")
# EVA框架的数据源通常在页面的__INITIAL_STATE__或类似变量中
# 查找页面中的数据配置
data_patterns = [
    r'window\.__([A-Z_]+)__\s*=\s*({.*?});',
    r'"dataSource"\s*:\s*({.*?})',
    r'"api"\s*:\s*"([^"]+)"',
    r'"fetch"\s*:\s*"([^"]+)"',
]
for pattern in data_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"  模式: {pattern[:40]}")
        for m in matches[:3]:
            if isinstance(m, tuple):
                m = m[0] if len(m) > 0 else str(m)
            print(f"    匹配: {str(m)[:300]}")

print("\n" + "=" * 60)
print("分析完成")
