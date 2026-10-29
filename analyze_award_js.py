import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# 下载领奖页面的主JS文件
js_url = 'https://activity.hdslb.com/blackboard/activity3ERA4wloghvc9700/js/index.c24946f8.js'
print('下载领奖页面JS文件...')
resp = requests.get(js_url, headers=headers)
js = resp.text
print('文件长度:', len(js))

# 查找基础URL的定义（O变量）
print('\n=== 查找基础URL定义 ===')
# 查找类似 O = "https://..." 的定义
base_urls = re.findall(r'(?:var|let|const)\s+(\w+)\s*=\s*["\'](https?://[^"\']+)["\']', js)
for name, url in base_urls:
    if 'bilibili' in url or 'activity' in url or 'api' in url:
        print(f'  {name} = {url}')

# 查找所有包含api.bilibili.com的字符串
api_strings = re.findall(r'["\']([^"\']*api\.bilibili\.com[^"\']*)["\']', js)
print('\n=== 包含api.bilibili.com的字符串 ===')
for s in sorted(set(api_strings)):
    print(' ', s)

# 查找mission相关的代码
print('\n=== mission相关代码 ===')
mission_matches = re.findall(r'.{0,150}mission.{0,150}', js)
for i, m in enumerate(mission_matches[:5]):
    print(f'  [{i}]', m.strip()[:250])
    print()

# 查找receive相关的代码
print('\n=== receive相关代码 ===')
receive_matches = re.findall(r'.{0,200}receive.{0,200}', js)
for i, m in enumerate(receive_matches[:5]):
    print(f'  [{i}]', m.strip()[:300])
    print()

# 查找task_id相关的代码
print('\n=== task_id相关代码 ===')
task_matches = re.findall(r'.{0,100}task_id.{0,100}', js)
for i, m in enumerate(task_matches[:5]):
    print(f'  [{i}]', m.strip()[:200])

# 查找gaia_vtoken相关
print('\n=== gaia_vtoken相关 ===')
gaia_matches = re.findall(r'.{0,100}gaia_vtoken.{0,100}', js)
for i, m in enumerate(gaia_matches[:5]):
    print(f'  [{i}]', m.strip()[:200])
