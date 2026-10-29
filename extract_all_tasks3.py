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

# 搜索所有ztasksid，提取前后200个字符
print('\n=== 搜索所有ztasksid ===')
pattern = r'.{0,300}ztasksid["\s:=]+["\']?([a-zA-Z0-9]+)["\']?.{0,100}'
matches = re.findall(pattern, html)
print(f'找到 {len(matches)} 个ztasksid')

# 去重
seen = set()
unique_tasks = []
for match in matches:
    if match not in seen:
        seen.add(match)
        # 找到这个ztasksid在HTML中的位置，提取上下文
        idx = html.find(f'ztasksid":"{match}"')
        if idx < 0:
            idx = html.find(f'ztasksid:{match}')
        if idx < 0:
            idx = html.find(f'ztasksid="{match}"')
        if idx >= 0:
            context = html[max(0, idx-400):idx+50]
            # 提取alias
            alias_match = re.search(r'"alias":"([^"]+)"', context)
            alias = alias_match.group(1) if alias_match else '未知'
            # 提取awardname
            awardname_match = re.search(r'"awardname":"([^"]+)"', context)
            awardname = awardname_match.group(1) if awardname_match else '未知'
            # 提取awardsid
            awardsid_match = re.search(r'"awardsid":"([^"]+)"', context)
            awardsid = awardsid_match.group(1) if awardsid_match else '未知'

            unique_tasks.append({
                'alias': alias,
                'awardname': awardname,
                'awardsid': awardsid,
                'ztasksid': match,
            })
            print(f'  - {alias}')
            print(f'    奖励: {awardname}, ztasksid: {match}')

print(f'\n共 {len(unique_tasks)} 个唯一任务')

# 按任务类型分类
print('\n\n=== 按任务类型分类 ===')
for t in unique_tasks:
    alias = t['alias']
    if '投稿' in alias:
        t['type'] = '投稿'
    elif '直播' in alias or '开播' in alias or '看直播' in alias or '观看鸣潮' in alias:
        t['type'] = '直播'
    elif '关注' in alias:
        t['type'] = '关注'
    elif '看视频' in alias or '观看' in alias or '累计观看' in alias:
        t['type'] = '看视频'
    else:
        t['type'] = '其他'

by_type = {}
for t in unique_tasks:
    typ = t['type']
    if typ not in by_type:
        by_type[typ] = []
    by_type[typ].append(t)

for typ, tasks in sorted(by_type.items()):
    print(f'\n【{typ}】({len(tasks)}个):')
    for t in tasks:
        print(f'  - {t["alias"]} => {t["awardname"]}')
        print(f'    ztasksid: {t["ztasksid"]}')

# 按上下半分类（第一期=上半，第二期=下半）
print('\n\n=== 按上下半分类 ===')
for t in unique_tasks:
    alias = t['alias']
    if '第一期' in alias:
        t['period'] = '上半'
    elif '第二期' in alias:
        t['period'] = '下半'
    else:
        t['period'] = '日常'

by_period = {}
for t in unique_tasks:
    period = t['period']
    if period not in by_period:
        by_period[period] = []
    by_period[period].append(t)

for period, tasks in sorted(by_period.items()):
    print(f'\n【{period}】({len(tasks)}个):')
    for t in tasks:
        print(f'  [{t["type"]}] {t["alias"]} => {t["awardname"]}')
        print(f'    ztasksid: {t["ztasksid"]}')

# 保存到文件
with open('all_tasks.json', 'w', encoding='utf-8') as f:
    json.dump(unique_tasks, f, ensure_ascii=False, indent=2)
print(f'\n\n已保存到 all_tasks.json')
