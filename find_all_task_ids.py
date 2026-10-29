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
print('HTML长度:', len(html))

# 查找所有类似task_id的ID（格式：字母+数字，长度约16位）
print('\n=== 查找所有可能的ID ===')
# 查找awardsid
awardsids = re.findall(r'awardsid["\s:=]+([a-zA-Z0-9]+)', html)
print('awardsid:', list(set(awardsids)))

# 查找task_id
task_ids = re.findall(r'task_id["\s:=]+([a-zA-Z0-9]+)', html)
print('task_id:', list(set(task_ids)))

# 查找ztasksid
ztasksids = re.findall(r'ztasksid["\s:=]+([a-zA-Z0-9]+)', html)
print('ztasksid:', list(set(ztasksids)))

# 查找所有包含ERA的ID
era_ids = re.findall(r'([0-9]+ERA[a-zA-Z0-9]+)', html)
print('ERA格式ID:', list(set(era_ids))[:20])

# 查找所有类似6ERAcwloghviw00格式的ID
pattern = re.compile(r'\b([0-9]+[A-Z][a-zA-Z0-9]{10,})\b')
all_ids = pattern.findall(html)
print('\n所有类似格式的ID:')
for id in sorted(set(all_ids)):
    print(' ', id)

# 查找awardName和对应的ID
print('\n=== 查找奖励名称和ID ===')
award_matches = re.findall(r'awardName["\s:=]+([^",}]+)["\s,}]+', html)
print('awardName:', list(set(award_matches)))

awardname_matches = re.findall(r'awardname["\s:=]+([^",}]+)', html)
print('awardname:', list(set(awardname_matches)))

# 查找任务列表相关的JSON
print('\n=== 查找任务列表JSON ===')
# 查找包含award的JSON块
json_blocks = re.findall(r'\{[^{}]*award(?:name|sid|type)[^{}]*\}', html)
for i, block in enumerate(json_blocks[:10]):
    print(f'  [{i}]', block[:200])
