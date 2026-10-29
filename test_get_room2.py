import requests, json

with open(r'dist\accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

acc = accounts[4]  # 灵砂是无敌的（主播）
name = acc.get('name', '未知')
uid = acc.get('DedeUserID', '')
cookie = 'SESSDATA=' + acc.get('SESSDATA','') + '; bili_jct=' + acc.get('bili_jct','') + '; DedeUserID=' + uid
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookie,
    'Referer': 'https://live.bilibili.com/'
}

print(f'测试账户: {name}, uid={uid}')

# 接口1: 获取自己的直播间信息
print('\n=== 接口1: xlive/web-ucenter/v1/cast/get_room_info ===')
try:
    resp = requests.get('https://api.live.bilibili.com/xlive/web-ucenter/v1/cast/get_room_info', headers=headers, timeout=10)
    print(f'状态码: {resp.status_code}')
    print(f'响应: {resp.text[:500]}')
except Exception as e:
    print(f'异常: {e}')

# 接口2: 旧版获取直播间信息（需要mid）
print(f'\n=== 接口2: room/v1/Room/getRoomInfoOld?mid={uid} ===')
try:
    resp = requests.get(f'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={uid}', headers=headers, timeout=10)
    print(f'状态码: {resp.status_code}')
    print(f'响应: {resp.text[:500]}')
except Exception as e:
    print(f'异常: {e}')

# 接口3: 用户空间信息
print(f'\n=== 接口3: x/space/acc/info?mid={uid} ===')
try:
    resp = requests.get(f'https://api.bilibili.com/x/space/acc/info?mid={uid}', headers=headers, timeout=10)
    print(f'状态码: {resp.status_code}')
    result = resp.json()
    if result.get('code') == 0:
        data = result.get('data', {})
        live_room = data.get('live_room', {})
        print(f'live_room: {json.dumps(live_room, ensure_ascii=False)}')
    else:
        print(f'响应: {resp.text[:300]}')
except Exception as e:
    print(f'异常: {e}')

# 接口4: 主播信息（带uid参数）
print(f'\n=== 接口4: live_user/v1/Master/info?uid={uid} ===')
try:
    resp = requests.get(f'https://api.live.bilibili.com/live_user/v1/Master/info?uid={uid}', headers=headers, timeout=10)
    print(f'状态码: {resp.status_code}')
    print(f'响应: {resp.text[:500]}')
except Exception as e:
    print(f'异常: {e}')
