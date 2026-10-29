#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试查询任务的完整stock_info结构"""

import json
import requests
import urllib.parse
import hashlib
import time
from functools import reduce

# 读取账户信息
with open(r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\accounts.json", 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 找到灵砂是无敌的账户
account = None
for acc in accounts:
    if acc.get('name') == '灵砂是无敌的':
        account = acc
        break

if not account:
    print("未找到账户")
    exit(1)

cookies = {
    'SESSDATA': account.get('sessdata', ''),
    'bili_jct': account.get('bilijct', ''),
}

# WBI签名
mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    params = {
        k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params

def get_wbi_keys():
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', cookies=cookies, timeout=10)
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

# 测试任务列表（鸣潮3.6的任务）
test_tasks = [
    ("累计3天投稿≥1000播放≥10币", "需要查找task_id"),
]

# 先查询所有任务的task_id
# 从任务配置文件中读取
import os
config_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data"
for file in os.listdir(config_path):
    if file.endswith('.json') and 'task' in file.lower():
        print(f"找到任务配置文件: {file}")

# 读取抢码任务组配置
rush_groups_path = os.path.join(config_path, 'rush_groups.json')
if os.path.exists(rush_groups_path):
    with open(rush_groups_path, 'r', encoding='utf-8') as f:
        rush_groups = json.load(f)
    print(f"\n任务组配置:")
    print(json.dumps(rush_groups, ensure_ascii=False, indent=2))
    
    # 查询每个任务的详细信息
    img_key, sub_key = get_wbi_keys()
    for group_name, group_data in rush_groups.items():
        print(f"\n===== 任务组: {group_name} =====")
        for task in group_data.get('tasks', []):
            task_id = task.get('task_id')
            task_name = task.get('name')
            print(f"\n任务: {task_name} (task_id={task_id})")
            
            params = {
                'task_id': task_id,
                'csrf': cookies['bili_jct'],
            }
            params = encWbi(params, img_key, sub_key)
            
            try:
                resp = requests.get(
                    'https://api.bilibili.com/x/activity_components/mission/info',
                    params=params,
                    cookies=cookies,
                    timeout=10
                )
                data = resp.json()
                if data.get('code') == 0:
                    info = data.get('data', {})
                    print(f"  status: {info.get('status')}")
                    print(f"  task_finished: {info.get('task_finished')}")
                    print(f"  stock_info: {json.dumps(info.get('stock_info', {}), ensure_ascii=False)}")
                    print(f"  status_text: {info.get('status_text', '')}")
                    print(f"  message: {info.get('message', '')}")
                else:
                    print(f"  查询失败: {data}")
            except Exception as e:
                print(f"  查询异常: {e}")
else:
    print(f"未找到任务组配置文件: {rush_groups_path}")
