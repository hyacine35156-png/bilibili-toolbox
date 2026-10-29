import json, requests, hashlib, time, urllib.parse
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

# WBI签名映射表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

def get_mixin_key(orig: str) -> str:
    return ''.join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]

def get_wbi_keys():
    """从nav接口获取wbi keys"""
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, cookies=cookies)
    data = resp.json()
    wbi_img = data['data']['wbi_img']
    img_url = wbi_img['img_url']
    sub_url = wbi_img['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def wbi_sign(params: dict, img_key: str, sub_key: str) -> dict:
    """对参数进行WBI签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    params['wts'] = int(time.time())
    # 排序参数
    sorted_params = dict(sorted(params.items()))
    # URL编码
    query = urllib.parse.urlencode(sorted_params)
    # MD5签名
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    sorted_params['w_rid'] = w_rid
    return sorted_params

# 获取wbi keys
print('\n=== 获取WBI keys ===')
img_key, sub_key = get_wbi_keys()
print('img_key:', img_key)
print('sub_key:', sub_key)

# 测试获取任务信息
print('\n=== 测试获取任务信息（带WBI签名）===')
task_url = 'https://api.bilibili.com/x/activity_components/mission/info'
params = {
    'task_id': '6ERAcwloghviw00',
    'web_location': '888.126558',
}
signed_params = wbi_sign(params, img_key, sub_key)
print('签名后的参数:', signed_params)

resp = requests.get(task_url, headers=headers, cookies=cookies, params=signed_params)
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
    else:
        print('获取失败:', data.get('code'), data.get('message'))
except Exception as e:
    print('解析失败:', e)
