import json, requests

# 读取账户数据
with open('dist/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[0]
print('使用账户:', acc['name'])
print('bili_jct:', acc['bili_jct'])

cookies = {
    'SESSDATA': acc['SESSDATA'],
    'bili_jct': acc['bili_jct'],
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghviiw00',
    'Origin': 'https://www.bilibili.com',
    'Content-Type': 'application/x-www-form-urlencoded',
}

# 任务信息
task_info = {
    'task_id': '6ERAcwloghviiw00',
    'act_id': '1ERAzwloghvn7l00',
    'act_name': '鸣潮3.6版本创作激励计划',
    'task_name': '【第一期】累计2天投稿且累计播放量≥300，累计投币≥3',
    'award_name': '120星声',
}

# 测试领取API（在请求体中加csrf）
print('\n=== 测试领取API（请求体中加csrf）===')
receive_url = 'https://api.bilibili.com/x/activity_components/mission/receive'

data = {
    'task_id': task_info['task_id'],
    'activity_id': task_info['act_id'],
    'activity_name': task_info['act_name'],
    'task_name': task_info['task_name'],
    'reward_name': task_info['award_name'],
    'gaia_vtoken': '',
    'receive_from': 'missionPage',
    'csrf': acc['bili_jct'],
}

resp = requests.post(receive_url, headers=headers, cookies=cookies, data=data)
print('状态码:', resp.status_code)
print('返回内容:', resp.text[:2000])

# 解析返回
try:
    result = resp.json()
    print('\n=== 返回解析 ===')
    print('code:', result.get('code'))
    print('message:', result.get('message'))
    if result.get('data'):
        print('data:', json.dumps(result.get('data'), ensure_ascii=False)[:1000])
except Exception as e:
    print('解析失败:', e)

# 测试2: 同时在请求头和请求体中加csrf
print('\n=== 测试2: 同时在请求头和请求体中加csrf ===')
headers2 = headers.copy()
headers2['x-csrf-token'] = acc['bili_jct']
resp2 = requests.post(receive_url, headers=headers2, cookies=cookies, data=data)
print('返回内容:', resp2.text[:1000])
