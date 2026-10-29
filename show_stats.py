# -*- coding: utf-8 -*-
import json

with open(r"C:\Users\15868\Desktop\抢码分析_raw_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

stats = data["stats"]
tasks = data["tasks"]

print("=== 按目标时间 ===")
for k, v in stats["by_target"].items():
    rate = round(v["success"]/v["total"]*100,1) if v["total"] else 0
    print(f"  {k}: 总{v['total']} 成功{v['success']} 失败{v['fail']} 成功率{rate}%")

print("\n=== 按奖励类型 ===")
for k, v in stats["by_reward_type"].items():
    rate = round(v["success"]/v["total"]*100,1) if v["total"] else 0
    print(f"  {k}: 总{v['total']} 成功{v['success']} 失败{v['fail']} 成功率{rate}%")

print("\n=== 按优先级 ===")
for k, v in sorted(stats["by_priority"].items()):
    rate = round(v["success"]/v["total"]*100,1) if v["total"] else 0
    print(f"  {k}: 总{v['total']} 成功{v['success']} 失败{v['fail']} 成功率{rate}%")

print("\n=== 成功尝试次数分布 ===")
for k, v in sorted(stats["success_attempts_dist"].items(), key=lambda x: int(x[0])):
    print(f"  第{k}次成功: {v}次")

print("\n=== 失败原因 ===")
for k, v in sorted(stats["fail_reasons"].items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}次")

print("\n=== 错误码分布 ===")
for k, v in sorted(stats["error_codes"].items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}次")

print("\n=== 任务名统计（前15） ===")
for name, v in sorted(stats["task_names"].items(), key=lambda x: -x[1]["total"])[:15]:
    rate = round(v["success"]/v["total"]*100,1) if v["total"] else 0
    print(f"  {name[:40]}: 总{v['total']} 成功{v['success']} 成功率{rate}%")

# 验证：打印几个成功任务的详情
print("\n=== 成功任务样例（前5） ===")
success_tasks = [t for t in tasks if t["success"]]
for t in success_tasks[:5]:
    print(f"  [{t['target_time']}] {t['name'][:30]} => {t['reward']} | 第{t['success_attempt']}次成功 | 账户:{t['account']}")

# 验证：打印几个失败任务的详情
print("\n=== 失败任务样例（前5） ===")
fail_tasks = [t for t in tasks if not t["success"]]
for t in fail_tasks[:5]:
    print(f"  [{t['target_time']}] {t['name'][:30]} => {t['reward']} | 尝试{t['attempts']}次 | 错误:{t['errors'][:3]} | 原因:{t['fail_reason']}")
