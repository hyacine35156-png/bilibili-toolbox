import json, requests, hashlib, time, urllib.parse

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com/',
}

# WBI签名
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

def get_mixin_key(orig):
    return ''.join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]

def get_wbi_keys():
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, cookies=cookies)
    data = resp.json()
    wbi_img = data['data']['wbi_img']
    img_key = wbi_img['img_url'].rsplit('/', 1)[1].split('.')[0]
    sub_key = wbi_img['sub_url'].rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def wbi_sign(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key + sub_key)
    params['wts'] = int(time.time())
    sorted_params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(sorted_params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    sorted_params['w_rid'] = w_rid
    return sorted_params

img_key, sub_key = get_wbi_keys()

# 测试不同的task_id
task_ids = [
    '6ERAcwloghviw00',  # 用户截图中的
    '5ERAbwloghv9iv00',  # HTML中找到的awardsid
    '1ERA3wloghv6q200',  # activity_id
]

# 也测试不同的API路径
api_paths = [
    'https://api.bilibili.com/x/activity_components/mission/info',
    'https://api.bilibili.com/x/activity/mission/info',
    'https://api.bilibili.com/x/activity_components/award/info',
]

print('\n=== 测试不同的task_id和API路径 ===')
for api_path in api_paths:
    for task_id in task_ids:
        params = {
            'task_id': task_id,
            'web_location': '888.126558',
        }
        signed_params = wbi_sign(params, img_key, sub_key)
        try:
            resp = requests.get(api_path, headers=headers, cookies=cookies, params=signed_params, timeout=10)
            data = resp.json()
            code = data.get('code')
            msg = data.get('message')
            if code == 0:
                print(f'[成功] {api_path}?task_id={task_id}')
                print(f'  数据: {json.dumps(data.get("data", {}), ensure_ascii=False)[:500]}')
            else:
                print(f'[失败] {api_path}?task_id={task_id} => code={code}, msg={msg}')
        except Exception as e:
            print(f'[错误] {api_path}?task_id={task_id} => {e}')
