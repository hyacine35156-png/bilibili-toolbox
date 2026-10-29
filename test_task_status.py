# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
import json
from main_gui_pro import get_mission_info, cookies_from_account

# 读取账户
with open("dist/data/accounts.json", "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 用t0级长夜月lover测试
account = None
for acc in accounts:
    if "t0" in acc.get("name", "") and "长夜月" in acc.get("name", ""):
        account = acc
        break

if not account:
    print("未找到t0账户")
    sys.exit(1)

print(f"测试账户: {account['name']}")
cookies = cookies_from_account(account)
print(f"cookies键: {list(cookies.keys())}")

# 测试一个任务（累计1天投稿≥100播放，task_id=6ERAcwloghvp8b00）
task_id = "6ERAcwloghvp8b00"
print(f"\n=== 查询任务: {task_id} ===")
info, msg = get_mission_info(task_id, cookies)
if info:
    print(f"✓ 查询成功")
    print(f"\n所有字段:")
    for k, v in info.items():
        if isinstance(v, (dict, list)):
            print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:200]}")
        else:
            print(f"  {k}: {v}")
    
    print(f"\n关键字段:")
    print(f"  task_finished: {info.get('task_finished')}")
    print(f"  finished: {info.get('finished')}")
    print(f"  is_finished: {info.get('is_finished')}")
    print(f"  status: {info.get('status')}")
    print(f"  task_status: {info.get('task_status')}")
else:
    print(f"✗ 查询失败: {msg}")
