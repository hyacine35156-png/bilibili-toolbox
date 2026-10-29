# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
import requests
from main_gui_pro import HEADERS, cookies_from_account

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = None
for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        account = acc
        break

print(f"账户: {account['name']}")
print(f"bili_jct: {account.get('bili_jct', '')[:16]}...")
print(f"sessdata: {account.get('sessdata', '')[:30]}...")

cookies = cookies_from_account(account)

# 测试1: 验证登录状态（导航栏用户信息API）
print("\n=== 测试1: 登录状态验证 ===")
try:
    resp = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=HEADERS, cookies=cookies, timeout=10)
    data = resp.json()
    print(f"code: {data.get('code')}")
    print(f"message: {data.get('message')}")
    if data.get("code") == 0:
        d = data.get("data", {})
        print(f"✓ 已登录: {d.get('uname')} (UID: {d.get('mid')})")
        print(f"  vipStatus: {d.get('vipStatus')}")
    else:
        print(f"✗ 未登录或cookies失效")
except Exception as e:
    print(f"✗ 异常: {e}")

# 测试2: 直接看API返回的完整数据（已领取的任务）
print("\n=== 测试2: 已领取任务完整数据 ===")
from main_gui_pro import get_mission_info
# 累计1天开播（用户说已领取）
info, msg = get_mission_info("6ERAcwloghvod500", cookies)
if info:
    print(f"task_name: {info.get('task_name')}")
    print(f"task_finished: {info.get('task_finished')}")
    print(f"status: {info.get('status')}")
    print(f"message: {info.get('message')}")
    print(f"check_error_code: {info.get('check_error_code')}")
    print(f"check_error_type: {info.get('check_error_type')}")
    print(f"article_display_date: {info.get('article_display_date')}")
    # 打印所有字段名
    print(f"\n所有字段: {list(info.keys())}")
else:
    print(f"查询失败: {msg}")
