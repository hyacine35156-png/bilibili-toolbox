#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量验证所有task_id是否正确"""

import sys
import json
import time
from pathlib import Path

# 添加项目目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from main_gui_pro import ALL_TASKS, get_mission_info, cookies_from_account

# 读取账户
accounts_file = Path(__file__).parent / "dist" / "accounts.json"
with open(accounts_file, "r", encoding="utf-8") as f:
    accounts = json.load(f)

# 用"灵砂是无敌的"账户
account = None
for acc in accounts:
    if acc["name"] == "灵砂是无敌的":
        account = acc
        break

if not account:
    print("未找到账户'灵砂是无敌的'")
    sys.exit(1)

cookies = cookies_from_account(account)
print(f"使用账户: {account['name']}")
print(f"共 {len(ALL_TASKS)} 个任务需要验证")
print("=" * 80)

results = []
success_count = 0
fail_count = 0

for i, task in enumerate(ALL_TASKS, 1):
    task_id = task["task_id"]
    version = task["version"]
    period = task["period"]
    task_type = task["type"]
    name = task["name"]
    award = task["award"]
    
    print(f"\n[{i}/{len(ALL_TASKS)}] 正在验证: [{version}][{period}][{task_type}] {name}")
    print(f"  task_id: {task_id}")
    
    try:
        info, msg = get_mission_info(task_id, cookies)
        
        if info:
            act_id = info.get("act_id", "空")
            act_name = info.get("act_name", "空")
            task_name = info.get("task_name", "空")
            reward_name = info.get("reward_info", {}).get("award_name", "空")
            
            print(f"  ✅ 查询成功")
            print(f"     act_id: {act_id}")
            print(f"     act_name: {act_name}")
            print(f"     task_name: {task_name}")
            print(f"     reward: {reward_name}")
            
            results.append({
                "index": i,
                "version": version,
                "period": period,
                "type": task_type,
                "name": name,
                "award": award,
                "task_id": task_id,
                "status": "success",
                "act_id": act_id,
                "act_name": act_name,
                "task_name_api": task_name,
                "reward_api": reward_name,
            })
            success_count += 1
        else:
            print(f"  ❌ 查询失败: {msg}")
            results.append({
                "index": i,
                "version": version,
                "period": period,
                "type": task_type,
                "name": name,
                "award": award,
                "task_id": task_id,
                "status": "fail",
                "error": msg,
            })
            fail_count += 1
    except Exception as e:
        print(f"  ❌ 查询异常: {e}")
        results.append({
            "index": i,
            "version": version,
            "period": period,
            "type": task_type,
            "name": name,
            "award": award,
            "task_id": task_id,
            "status": "error",
            "error": str(e),
        })
        fail_count += 1
    
    # 延迟，避免请求过于频繁
    if i < len(ALL_TASKS):
        time.sleep(1.5)

print("\n" + "=" * 80)
print(f"验证完成！成功: {success_count}, 失败: {fail_count}")
print("=" * 80)

# 输出失败的任务
if fail_count > 0:
    print("\n❌ 失败的任务列表:")
    for r in results:
        if r["status"] != "success":
            print(f"  [{r['index']}] [{r['version']}][{r['period']}][{r['type']}] {r['name']}")
            print(f"      task_id: {r['task_id']}")
            print(f"      错误: {r.get('error', '未知')}")

# 输出所有任务的act_id（用于更新缓存）
print("\n" + "=" * 80)
print("所有任务的act_id（用于更新缓存）:")
print("=" * 80)
act_id_map = {}
for r in results:
    if r["status"] == "success":
        act_id_map[r["task_id"]] = r["act_id"]
        print(f'  "{r["task_id"]}": "{r["act_id"]}",  # [{r["version"]}] {r["name"]}')

# 保存结果到文件
output_file = Path(__file__).parent / "task_verification_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到: {output_file}")
