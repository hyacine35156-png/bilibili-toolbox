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

# 提取所有任务块
# 任务块格式：包含awardName、checkpoints（含alias、awardname、awardsid、ztasksid）
print('\n=== 提取所有任务 ===')

# 找到所有包含taskItem的JSON块
# 用正则匹配 taskItem 到下一个组件之间的内容
task_pattern = re.compile(r'"taskItem":\{(.*?)\}(?,"[a-zA-Z_]+":\{|"[a-zA-Z_]+":\[)', re.DOTALL)
task_matches = task_pattern.findall(html)
print(f'找到 {len(task_matches)} 个任务块')

all_tasks = []
for i, task_str in enumerate(task_matches):
    # 提取awardName
    award_name_match = re.search(r'"awardName":"([^"]+)"', task_str)
    award_name = award_name_match.group(1) if award_name_match else '未知'

    # 提取所有checkpoints
    checkpoints = re.findall(r'\{[^{}]*"alias":"([^"]+)"[^{}]*"awardname":"([^"]+)"[^{}]*"awardsid":"([^"]+)"[^{}]*"ztasksid":"([^"]+)"[^{}]*\}', task_str)

    if checkpoints:
        print(f'\n[{i}] 任务组: {award_name}')
        for alias, awardname, awardsid, ztasksid in checkpoints:
            print(f'  - {alias}')
            print(f'    奖励: {awardname}, awardsid: {awardsid}, ztasksid: {ztasksid}')
            all_tasks.append({
                'alias': alias,
                'awardname': awardname,
                'awardsid': awardsid,
                'ztasksid': ztasksid,
                'group': award_name,
            })

print(f'\n\n共提取 {len(all_tasks)} 个任务')

# 按奖励名称分类
print('\n=== 按奖励名称分类 ===')
by_award = {}
for t in all_tasks:
    award = t['awardname']
    if award not in by_award:
        by_award[award] = []
    by_award[award].append(t)

for award, tasks in by_award.items():
    print(f'\n{award} ({len(tasks)}个):')
    for t in tasks:
        print(f'  - {t["alias"]} (ztasksid: {t["ztasksid"]})')

# 保存到文件
with open('all_tasks.json', 'w', encoding='utf-8') as f:
    json.dump(all_tasks, f, ensure_ascii=False, indent=2)
print('\n已保存到 all_tasks.json')
