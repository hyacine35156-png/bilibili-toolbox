import json, requests, re

# 读取账户数据
with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
cookies = {
    'SESSDATA': acc['SESSDATA'],
    'bili_jct': acc['bili_jct'],
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# 获取活动主页面HTML
resp = requests.get('https://www.bilibili.com/blackboard/era/AnRiPi9wfny8e6fQ.html', headers=headers, cookies=cookies)
html = resp.text

# 查找包含星声奖励的任务块
print('=== 查找星声奖励任务 ===')
# 查找包含"星声"和ztasksid的上下文
matches = re.findall(r'.{0,300}(?:60|120|180|300|500)星声.{0,300}', html)
for i, m in enumerate(matches[:10]):
    print(f'\n[{i}]', m.strip()[:500])
    # 查找其中的ztasksid
    ztasks = re.findall(r'ztasksid["\s:=]+([a-zA-Z0-9]+)', m)
    if ztasks:
        print('  ztasksid:', ztasks)
    awards = re.findall(r'awardsid["\s:=]+([a-zA-Z0-9]+)', m)
    if awards:
        print('  awardsid:', awards)

# 查找投稿领星声相关的任务
print('\n\n=== 查找投稿领星声任务 ===')
matches = re.findall(r'.{0,200}投稿.{0,200}', html)
for i, m in enumerate(matches[:10]):
    if '星声' in m or 'ztasksid' in m:
        print(f'\n[{i}]', m.strip()[:400])
        ztasks = re.findall(r'ztasksid["\s:=]+([a-zA-Z0-9]+)', m)
        if ztasks:
            print('  ztasksid:', ztasks)

# 直接查找所有包含ztasksid和awardname的JSON块
print('\n\n=== 查找任务-JSON块 ===')
# 查找包含ztasksid的较大JSON块
json_pattern = re.compile(r'\{[^{}]*(?:ztasksid|awardname|awardName)[^{}]*\}', re.DOTALL)
json_matches = json_pattern.findall(html)
print(f'找到 {len(json_matches)} 个JSON块')
for i, block in enumerate(json_matches[:20]):
    if '星声' in block:
        print(f'\n[{i}]', block[:300])
