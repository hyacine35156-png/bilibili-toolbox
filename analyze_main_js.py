import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# 下载主JS文件
js_url = 'https://activity.hdslb.com/blackboard/activity3ERA4wloghvc9700/js/index.c24946f8.js'
print('下载主JS文件...')
resp = requests.get(js_url, headers=headers)
js = resp.text
print('文件长度:', len(js))

# 查找所有API路径
api_paths = re.findall(r'["\'](/(?:x|api|activity|mission|award|exchange|receive|point|task|draw|lottery|claim|redeem)[a-zA-Z0-9_/]+)["\']', js)
print('\n找到的API路径:')
for p in sorted(set(api_paths)):
    print(' ', p)

# 查找包含bilibili.com的API URL
urls = re.findall(r'https?://[a-zA-Z0-9.-]*bilibili\.com/(?:x|api|activity|mission|award|exchange|receive)[a-zA-Z0-9_/]*', js)
print('\n找到的API URL:')
for u in sorted(set(urls))[:30]:
    print(' ', u)

# 查找关键词
for keyword in ['receive', 'exchange', 'award', 'mission', 'task', 'draw', 'lottery', 'point', 'claim', 'redeem', '领取', '兑换']:
    matches = re.findall(r'.{0,100}' + keyword + r'.{0,100}', js, re.IGNORECASE)
    if matches:
        print(f'\n关键词 "{keyword}" 出现 {len(matches)} 次，前3个:')
        for m in matches[:3]:
            print('  ', m.strip()[:180])

# 查找请求方法调用
method_calls = re.findall(r'\.(?:get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']', js, re.IGNORECASE)
print('\n找到的请求URL:')
for u in sorted(set(method_calls))[:30]:
    print(' ', u)
