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
    'Referer': 'https://www.bilibili.com/',
}

# 获取活动主页面HTML
print('=== 获取活动主页面HTML ===')
resp = requests.get('https://www.bilibili.com/blackboard/era/AnRiPi9wfny8e6fQ.html', headers=headers, cookies=cookies)
print('状态码:', resp.status_code)
html = resp.text
print('HTML长度:', len(html))

# 查找task_id
task_ids = re.findall(r'task_id[=:"\s]+([a-zA-Z0-9]+)', html)
print('找到的task_id:', list(set(task_ids)))

# 查找API相关的URL
api_urls = re.findall(r'https?://[a-zA-Z0-9./_-]+(?:activity|mission|award|exchange|receive)[a-zA-Z0-9./_-]*', html)
print('找到的API URL:', list(set(api_urls))[:20])

# 查找web_location
web_locations = re.findall(r'web_location[=:"\s]+([0-9.]+)', html)
print('找到的web_location:', list(set(web_locations)))

# 查找era相关的ID
era_ids = re.findall(r'era/([a-zA-Z0-9]+)', html)
print('找到的era_id:', list(set(era_ids))[:10])

# 查找关键词
for keyword in ['领取', '兑换', 'receive', 'exchange', 'award', 'mission', 'stock', '库存', '去完成']:
    matches = re.findall(r'.{0,80}' + keyword + r'.{0,80}', html)
    if matches:
        print(f'\n关键词 "{keyword}" 出现 {len(matches)} 次，前2个:')
        for m in matches[:2]:
            print('  ', m.strip()[:150])
