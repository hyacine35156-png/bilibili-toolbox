import json, requests, re

# 下载并分析JavaScript文件
js_files = [
    'https://s1.hdslb.com/bfs/activity-plat/static/10613/11875/11876/cdc19f701f98475d2e815e921da304be/EraTasklistPc_gJcjPZNwCi.js',
    'https://s1.hdslb.com/bfs/activity-plat/static/10613/11875/11876/cdc19f701f98475d2e815e921da304be/EraPointExchangePc_ihTkNU5tpD.js',
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

for js_url in js_files:
    print(f'\n=== 分析: {js_url.split("/")[-1]} ===')
    resp = requests.get(js_url, headers=headers)
    js_content = resp.text
    print('JS长度:', len(js_content))

    # 查找API路径
    api_paths = re.findall(r'["\'](/x/[a-zA-Z0-9_/]+)["\']', js_content)
    print('找到的API路径:', list(set(api_paths))[:20])

    # 查找包含receive/exchange/award/mission的API
    for keyword in ['receive', 'exchange', 'award', 'mission', 'task', 'draw', 'lottery']:
        matches = re.findall(r'.{0,60}' + keyword + r'.{0,60}', js_content, re.IGNORECASE)
        if matches:
            print(f'\n关键词 "{keyword}" 前3个:')
            for m in matches[:3]:
                print('  ', m.strip()[:120])

    # 查找请求方法
    methods = re.findall(r'(?:get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']', js_content, re.IGNORECASE)
    print('\n找到的请求URL:', list(set(methods))[:10])
