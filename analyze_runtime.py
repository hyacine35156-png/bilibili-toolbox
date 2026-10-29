import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# 下载主运行时文件
runtime_url = 'https://s1.hdslb.com/bfs/activity-plat/static/10613/11875/11876/cdc19f701f98475d2e815e921da304be/EvaRuntime_k6FWmzBxGC.js'
print('下载主运行时文件...')
resp = requests.get(runtime_url, headers=headers)
js = resp.text
print('文件长度:', len(js))

# 查找所有API路径
api_paths = re.findall(r'["\'](/(?:x|api|activity|mission|award|exchange|receive|point|task)[a-zA-Z0-9_/]+)["\']', js)
print('\n找到的API路径:')
for p in sorted(set(api_paths)):
    print(' ', p)

# 查找包含bilibili.com的URL
urls = re.findall(r'https?://[a-zA-Z0-9.-]*bilibili\.com[a-zA-Z0-9./_-]*', js)
print('\n找到的bilibili URL:')
for u in sorted(set(urls))[:30]:
    print(' ', u)

# 查找关键词
for keyword in ['receive', 'exchange', 'award', 'mission', 'task', 'draw', 'lottery', 'point', 'claim', 'redeem']:
    matches = re.findall(r'.{0,80}' + keyword + r'.{0,80}', js, re.IGNORECASE)
    if matches:
        print(f'\n关键词 "{keyword}" 出现 {len(matches)} 次，前3个:')
        for m in matches[:3]:
            print('  ', m.strip()[:150])
