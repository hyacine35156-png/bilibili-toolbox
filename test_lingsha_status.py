# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
from main_gui_pro import get_mission_info, cookies_from_account

with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

account = None
for acc in accounts:
    if "灵砂" in acc.get("name", ""):
        account = acc
        break

print(f"测试账户: {account['name']}")
cookies = cookies_from_account(account)

# 测试几个任务
task_ids = [
    ("6ERAcwloghvp8b00", "累计1天投稿≥100播放"),
    ("6ERAcwloghvod500", "累计1天开播"),
    ("6ERAcwloghvp1h00", "累计2天开播"),
]

for task_id, task_name in task_ids:
    print(f"\n=== {task_name} ({task_id}) ===")
    info, msg = get_mission_info(task_id, cookies)
    if info:
        print(f"  task_finished: {info.get('task_finished')}")
        print(f"  status: {info.get('status')}")
        print(f"  message: {info.get('message')}")
        print(f"  check_error_type: {info.get('check_error_type')}")
        stock = info.get("stock_info", {})
        print(f"  total_stock: {stock.get('total_stock')}, total_remain: {stock.get('total_remain_num')}, day_remain: {stock.get('day_remain_num')}")
    else:
        print(f"  ✗ 查询失败: {msg}")
