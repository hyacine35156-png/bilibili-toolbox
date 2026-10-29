import json, requests

with open('dist/data/accounts.json','r',encoding='utf-8') as f:
    accounts = json.load(f)
acc = accounts[5]
sessdata = acc.get('SESSDATA','')
cookies = {'SESSDATA':sessdata}
headers = {'User-Agent':'Mozilla/5.0'}

url = 'https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc&room_id=1791983148'
r = requests.get(url, cookies=cookies, headers=headers, timeout=10)
d = r.json()

if d.get('code') == 0:
    gift_list = d.get('data', {}).get('list', [])
    print(f"总礼物数: {len(gift_list)}")
    
    # 筛选price=100且非包裹限定的礼物
    print("\n=== price=100 且 非包裹限定(bag_gift=0或不存在) ===")
    count = 0
    for gift in gift_list:
        price = gift.get('price', 0)
        coin_type = gift.get('coin_type', '')
        bag_gift = gift.get('bag_gift', 0)
        name = gift.get('name', '')
        gift_id = gift.get('id', '')
        corner = gift.get('corner_mark', '')
        if price == 100 and coin_type == 'gold' and bag_gift == 0 and not corner:
            print(f"  id={gift_id}, name={name}, price={price}, coin_type={coin_type}, bag_gift={bag_gift}, corner={corner}")
            count += 1
    print(f"\n共 {count} 个可直接用电池送的1电池礼物")
    
    # 也列出所有price=100的礼物，看bag_gift字段
    print("\n=== 所有price=100礼物(含bag_gift) ===")
    for gift in gift_list:
        price = gift.get('price', 0)
        coin_type = gift.get('coin_type', '')
        if price == 100 and coin_type == 'gold':
            name = gift.get('name', '')
            gift_id = gift.get('id', '')
            bag_gift = gift.get('bag_gift', 0)
            corner = gift.get('corner_mark', '')
            print(f"  id={gift_id}, name={name}, bag_gift={bag_gift}, corner={corner}")
