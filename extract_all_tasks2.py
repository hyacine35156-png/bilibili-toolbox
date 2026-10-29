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

# 直接提取所有checkpoints
# 格式: {"alias":"...","awardname":"...","awardsid":"...","awardtype":1,"count":1,"list":[...],"status":1,"ztasksid":"..."}
print('\n=== 提取所有任务checkpoints ===')

# 匹配包含alias、awardname、awardsid、ztasksid的JSON对象
pattern = r'\{[^{}]*"alias":"([^"]+)"[^{}]*"awardname":"([^"]+)"[^{}]*"awardsid":"([^"]+)"[^{}]*"ztasksid":"([^"]+)"[^{}]*\}'
matches = re.findall(pattern, html)
print(f'找到 {len(matches)} 个任务')

all_tasks = []
for alias, awardname, awardsid, ztasksid in matches:
    all_tasks.append({
        'alias': alias,
        'awardname': awardname,
        'awardsid': awardsid,
        'ztasksid': ztasksid,
    })
    print(f'  - {alias}')
    print(f'    奖励: {awardname}, ztasksid: {ztasksid}')

# 按奖励名称分类
print('\n\n=== 按奖励名称分类 ===')
by_award = {}
for t in all_tasks:
    award = t['awardname']
    if award not in by_award:
        by_award[award] = []
    by_award[award].append(t)

for award, tasks in sorted(by_award.items()):
    print(f'\n{award} ({len(tasks)}个):')
    for t in tasks:
        print(f'  - {t["alias"]}')
        print(f'    ztasksid: {t["ztasksid"]}')

# 按任务类型分类（投稿/直播/其他）
print('\n\n=== 按任务类型分类 ===')
for t in all_tasks:
    alias = t['alias']
    if '投稿' in alias:
        t['type'] = '投稿'
    elif '直播' in alias or '开播' in alias or '看直播' in alias:
        t['type'] = '直播'
    elif '关注' in alias:
        t['type'] = '关注'
    elif '看视频' in alias or '观看' in alias:
        t['type'] = '看视频'
    else:
        t['type'] = '其他'

by_type = {}
for t in all_tasks:
    typ = t['type']
    if typ not in by_type:
        by_type[typ] = []
    by_type[typ].append(t)

for typ, tasks in sorted(by_type.items()):
    print(f'\n【{typ}】({len(tasks)}个):')
    for t in tasks:
        print(f'  - {t["alias"]} => {t["awardname"]}')
        print(f'    ztasksid: {t["ztasksid"]}')

# 保存到文件
with open('all_tasks.json', 'w', encoding='utf-8') as f:
    json.dump(all_tasks, f, ensure_ascii=False, indent=2)
print(f'\n\n共 {len(all_tasks)} 个任务，已保存到 all_tasks.json')
