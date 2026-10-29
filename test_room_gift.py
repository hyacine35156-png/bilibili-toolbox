import json, requests

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
cookies = {'SESSDATA':sessdata}
headers = {'User-Agent':'Mozilla/5.0'}

room_id = '1791983148'

# 1. 查直播间完整信息
print("=== 直播间完整信息 ===")
url = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
d = r.json()
if d.get('code') == 0:
    data = d.get('data', {})
    print('room_id:', data.get('room_id'))
    print('uid(主播):', data.get('uid'))
    print('title:', data.get('title'))
    print('area_id:', data.get('area_id'))
    print('area_name:', data.get('area_name'))
    print('parent_area_id:', data.get('parent_area_id'))
    print('parent_area_name:', data.get('parent_area_name'))
    print('live_status:', data.get('live_status'))
    print('is_sp:', data.get('is_sp'))
    print('special_type:', data.get('special_type'))

# 2. 查直播间支持的礼物列表
print("\n=== 直播间礼物配置 ===")
url = f'https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc&room_id={room_id}'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
d = r.json()
print('code:', d.get('code'))
if d.get('code') == 0:
    gift_list = d.get('data', {}).get('list', [])
    print('礼物总数:', len(gift_list))
    # 找小花花
    for gift in gift_list:
        name = gift.get('name','')
        if '花' in name or '瓜' in name or '好诶' in name:
            print(f"  {name} id={gift.get('id')} price={gift.get('price')} corner={gift.get('corner_mark')}")

# 3. 换一个直播间测试（用一个热门直播间）
print("\n=== 换直播间测试: 直播间1 (随便一个) ===")
# 用灵砂是无敌的自己的直播间已经测过了，换一个思路
# 直接查一下这个直播间是否开启了"禁止送礼"
url = f'https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid={room_id}'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
print('anchor_in_room status:', r.status_code)
try:
    d = r.json()
    print('code:', d.get('code'))
    print('data:', json.dumps(d.get('data'), ensure_ascii=False)[:300])
except:
    print('非JSON响应')
