import json, requests, re
from pathlib import Path

# 读取账户数据
with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
print('使用账户:', acc['name'])

cookies = {
    'SESSDATA': acc['SESSDATA'],
    'bili_jct': acc['bili_jct'],
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/blackboard/era/AnRiPi9wfny8e6fQ.html',
}

# 访问领奖页面
print('\n=== 访问领奖页面 ===')
award_url = 'https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghviw00'
resp = requests.get(award_url, headers=headers, cookies=cookies)
print('状态码:', resp.status_code)
html = resp.text
print('HTML长度:', len(html))

# 查找JavaScript文件
js_files = re.findall(r'src="([^"]+\.js[^"]*)"', html)
print('\n找到的JS文件:')
for js in js_files[:20]:
    print(' ', js)

# 查找task_id相关
task_matches = re.findall(r'.{0,100}task_id.{0,100}', html)
print('\ntask_id相关:')
for m in task_matches[:5]:
    print(' ', m.strip()[:150])

# 查找API相关
api_matches = re.findall(r'.{0,100}(?:api|activity|mission|award|exchange|receive).{0,100}', html, re.IGNORECASE)
print('\nAPI相关:')
for m in api_matches[:10]:
    print(' ', m.strip()[:150])

# 查找页面中的JSON数据
json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html)
if json_matches:
    print('\n找到INITIAL_STATE:')
    print(json_matches[0][:500])

# 查找所有script标签中的内容
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f'\n找到 {len(scripts)} 个script标签')
for i, script in enumerate(scripts):
    if len(script) > 100:
        print(f'\nScript {i} (长度{len(script)}):')
        # 查找API相关
        apis = re.findall(r'["\'](/(?:x|api|activity|mission|award|exchange|receive)[a-zA-Z0-9_/]+)["\']', script)
        if apis:
            print('  API:', list(set(apis)))
