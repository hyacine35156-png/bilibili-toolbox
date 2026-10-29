"""
风控间隔实验 v7.1
- 使用主程序的receive_reward函数，确保参数正确
- 间隔档位: 500, 550, 600, 650, 700, 750, 800ms (50ms一档)
- 每档位约14-15次，总共约100次
- 6个账户轮流使用，避免单账户风控累积
- 使用已领取的任务测试，不会真的消耗奖励
"""
import sys
import os
import json
import time
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入主程序的函数
from main_gui_pro import receive_reward, get_mission_info, cookies_from_account, ALL_TASKS, VERSION_DEFAULT_ACT_ID

# 读取账户
with open('dist/data/accounts.json', 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# 测试用任务（已领取的任务，累计1天投稿-上半）
TEST_TASK_ID = "6ERAcwloghvsaz00"
TEST_TASK = next((t for t in ALL_TASKS if t["task_id"] == TEST_TASK_ID), None)

def is_risk_control(code, msg):
    """判断是否是风控"""
    risk_codes = [-702, -705, -509, -412]
    if code in risk_codes:
        return True
    risk_msgs = ["请求频率过高", "请求过于频繁", "request was banned", "风控"]
    for rm in risk_msgs:
        if rm in msg:
            return True
    return False

# 先获取任务信息
print("获取任务信息...")
task_info = None
for acc in accounts[:3]:
    cookies = cookies_from_account(acc)
    info, msg = get_mission_info(TEST_TASK_ID, cookies)
    if info:
        task_info = info
        print(f"  ✓ 用账户 {acc['name']} 获取成功")
        break
    else:
        print(f"  ✗ {acc['name']}: {msg}")

if not task_info:
    print("使用备用任务信息")
    task_info = {
        "act_id": VERSION_DEFAULT_ACT_ID.get("崩坏星穹铁道4.5", ""),
        "act_name": "崩坏星穹铁道4.5版本激励计划",
        "task_name": "累计1天投稿-上半",
        "reward_info": {"award_name": "星琼*50-上半任务1"},
    }

# 实验配置
intervals = [500, 550, 600, 650, 700, 750, 800]  # ms
tests_per_interval = 15  # 每档位15次，7*15=105次
total_tests = len(intervals) * tests_per_interval

print("=" * 60)
print("风控间隔实验 v7.1")
print(f"间隔档位: {intervals}ms")
print(f"每档位测试: {tests_per_interval}次")
print(f"总测试次数: {total_tests}次")
print(f"账户数量: {len(accounts)}个")
print(f"测试任务: {TEST_TASK_ID} (已领取)")
print("=" * 60)

results = {}
for iv in intervals:
    results[iv] = {"pass": 0, "risk": 0, "other": 0, "details": []}

account_idx = 0
test_num = 0

for interval in intervals:
    print(f"\n--- 间隔 {interval}ms ---")
    for i in range(tests_per_interval):
        test_num += 1
        account = accounts[account_idx % len(accounts)]
        account_idx += 1

        cookies = cookies_from_account(account)
        csrf = cookies.get("bili_jct", "")

        try:
            start = time.time()
            code, msg = receive_reward(TEST_TASK_ID, task_info, cookies, csrf)
            elapsed = (time.time() - start) * 1000
        except Exception as e:
            code, msg, elapsed = -999, str(e), 0

        is_risk = is_risk_control(code, msg)

        if is_risk:
            results[interval]["risk"] += 1
            status = "风控"
        elif code == 0:
            results[interval]["pass"] += 1
            status = "通过"
        else:
            results[interval]["other"] += 1
            status = f"其他({code})"

        results[interval]["details"].append({
            "test": test_num,
            "account": account["name"],
            "code": code,
            "msg": str(msg)[:50],
            "elapsed_ms": round(elapsed, 1),
            "is_risk": is_risk,
        })

        print(f"  [{test_num:3d}/{total_tests}] {account['name'][:8]:8s} | {status:8s} | code={code:5d} | {elapsed:6.1f}ms | {str(msg)[:30]}")

        # 等待指定间隔
        if i < tests_per_interval - 1:
            time.sleep(interval / 1000.0)

# 汇总结果
print("\n" + "=" * 60)
print("实验结果汇总")
print("=" * 60)
print(f"{'间隔(ms)':<12} {'通过':<8} {'风控':<8} {'其他':<8} {'通过率':<10} {'风控率':<10}")
print("-" * 60)

summary = []
for interval in intervals:
    r = results[interval]
    total = r["pass"] + r["risk"] + r["other"]
    pass_rate = r["pass"] / total * 100 if total > 0 else 0
    risk_rate = r["risk"] / total * 100 if total > 0 else 0
    print(f"{interval:<12} {r['pass']:<8} {r['risk']:<8} {r['other']:<8} {pass_rate:<10.1f} {risk_rate:<10.1f}")
    summary.append({
        "interval_ms": interval,
        "pass": r["pass"],
        "risk": r["risk"],
        "other": r["other"],
        "pass_rate": round(pass_rate, 1),
        "risk_rate": round(risk_rate, 1),
    })

# 保存结果
output = {
    "experiment": "风控间隔实验 v7.1",
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "intervals": intervals,
    "tests_per_interval": tests_per_interval,
    "total_tests": total_tests,
    "summary": summary,
    "details": {str(k): v["details"] for k, v in results.items()},
}

with open('risk_interval_results_v7.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n详细结果已保存到 risk_interval_results_v7.json")
print("=" * 60)
