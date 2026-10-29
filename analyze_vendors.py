import requests, re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# 下载vendors文件
js_url = 'https://activity.hdslb.com/blackboard/activity3ERA4wloghvc9700/js/chunk-vendors.a49cd0f8.js'
print('下载vendors文件...')
resp = requests.get(js_url, headers=headers)
js = resp.text
print('文件长度:', len(js))

# 查找activity_components相关
print('\n=== activity_components相关 ===')
matches = re.findall(r'.{0,100}activity_components.{0,100}', js)
for i, m in enumerate(matches[:10]):
    print(f'  [{i}]', m.strip()[:200])

# 查找baseURL相关
print('\n=== baseURL相关 ===')
matches = re.findall(r'.{0,100}(?:baseURL|baseUrl|BASE_URL).{0,100}', js)
for i, m in enumerate(matches[:10]):
    print(f'  [{i}]', m.strip()[:200])

# 查找api.bilibili.com相关
print('\n=== api.bilibili.com相关 ===')
matches = re.findall(r'.{0,80}api\.bilibili\.com.{0,80}', js)
for i, m in enumerate(matches[:10]):
    print(f'  [{i}]', m.strip()[:180])

# 查找x/activity相关
print('\n=== x/activity相关 ===')
matches = re.findall(r'.{0,80}x/activity.{0,80}', js)
for i, m in enumerate(matches[:10]):
    print(f'  [{i}]', m.strip()[:180])

# 查找mission相关
print('\n=== mission相关 ===')
matches = re.findall(r'.{0,80}mission.{0,80}', js)
for i, m in enumerate(matches[:10]):
    print(f'  [{i}]', m.strip()[:180])

# 查找http开头的URL
print('\n=== http开头的URL ===')
urls = re.findall(r'["\'](https?://[^"\']+)["\']', js)
for u in sorted(set(urls))[:30]:
    if 'bilibili' in u or 'hdslb' in u:
        print(' ', u)
