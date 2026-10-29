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
    'Referer': 'https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghviw00',
    'Origin': 'https://www.bilibili.com',
}

# 测试1: 获取任务信息
print('\n=== 测试1: 获取任务信息 ===')
task_url = 'https://api.bilibili.com/x/activity_components/mission/info'
params = {
    'task_id': '6ERAcwloghviw00',
}
resp = requests.get(task_url, headers=headers, cookies=cookies, params=params)
print('状态码:', resp.status_code)
print('返回内容:', resp.text[:3000])

# 解析返回
try:
    data = resp.json()
    if data.get('code') == 0:
        task_info = data.get('data', {})
        print('\n任务信息解析:')
        print('  activity_id:', task_info.get('activity_id'))
        print('  act_name:', task_info.get('act_name'))
        print('  task_name:', task_info.get('task_name'))
        print('  reward_info:', task_info.get('reward_info'))
        print('  stock_info:', task_info.get('stock_info'))
        print('  message:', task_info.get('message'))
        print('  所有字段:', list(task_info.keys()))
except Exception as e:
    print('解析失败:', e)

# 测试2: 尝试不同的task_id格式
print('\n=== 测试2: 尝试其他可能的API路径 ===')
# 可能的基础URL
base_urls = [
    'https://api.bilibili.com/x/activity_components/mission/info',
    'https://api.bilibili.com/x/activity/mission/info',
    'https://activity.bilibili.com/x/activity_components/mission/info',
]

for base_url in base_urls:
    try:
        resp = requests.get(base_url, headers=headers, cookies=cookies, params={'task_id': '6ERAcwloghviw00'})
        data = resp.json()
        print(f'{base_url}: code={data.get("code")}, msg={data.get("message")}')
        if data.get('code') == 0:
            print('  成功! 数据:', json.dumps(data.get('data', {}), ensure_ascii=False)[:500])
    except Exception as e:
        print(f'{base_url}: 错误 - {e}')
