"""
50次精准首发测试（改进版：每次测试后保存结果）
"""
import sys
import os
import json
import time
import random
import requests
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from main_gui_pro import (
    cookies_from_account,
    get_mission_info,
    receive_reward,
    HEADERS,
    VERSION_DEFAULT_ACT_ID,
)

def log(msg):
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    print(f"[{timestamp}] {msg}")

# ===== 读取账户配置 =====
accounts_path = os.path.join(os.path.dirname(__file__), 'dist', 'data', 'accounts.json')
with open(accounts_path, 'r', encoding='utf-8') as f:
    accounts = json.load(f)

# ===== 任务列表 =====
tasks = [
    ("6ERAcwloghvu4d00", "开播时长60min", "鸣潮3.6", "中级共鸣促剂*2"),
    ("6ERAcwloghvuse00", "开播60min", "绝区零3.2", "丁尼*1000"),
    ("6ERAcwloghvsaz00", "累计1天投稿-上半", "崩坏星穹铁道4.5", "星琼*50"),
    ("6ERAcwloghvyxs00", "收获2电池", "绝区零3.2", "丁尼*500"),
    ("6ERAcwloghvabs00", "大于10条弹幕", "绝区零3.2", "丁尼*500"),
    ("6ERAcwloghvsp000", "至少一名用户看播≥10分钟", "绝区零3.2", "丁尼*500"),
    ("6ERAcwloghvudj00", "累计3天投稿三连×2", "崩坏星穹铁道4.5", "星轨通票*1"),
    ("6ERAcwloghvsal00", "累计5天投稿三连≥5且播放≥1000", "崩坏星穹铁道4.5", "星琼*300"),
    ("18ERA1wloghvbtg00", "累计7天投稿总播≥2000且三连≥30", "崩坏星穹铁道4.5", "星琼*500"),
    ("6ERAcwloghvymq00", "累计10天投稿", "崩坏星穹铁道4.5", "星琼*1000"),
]

results_path = os.path.join(os.path.dirname(__file__), 'test_50_results.json')

# 加载已有结果（如果有）
if os.path.exists(results_path):
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f"加载已有结果: {len(results)} 条")
else:
    results = []

start_idx = len(results)
total_tests = 50

print("=" * 70)
print(f"50次精准首发测试（从第{start_idx+1}次开始）")
print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
print("=" * 70)

# ===== 循环测试 =====
for i in range(start_idx, total_tests):
    task_id, task_name, task_version, task_award = tasks[i % len(tasks)]
    account = accounts[i % len(accounts)]
    account_name = account.get('name', '未知')
    
    print()
    print("=" * 70)
    print(f"第 {i+1}/{total_tests} 次测试")
    print(f"账号: {account_name}")
    print(f"任务: {task_version} - {task_name}")
    print("=" * 70)
    
    cookies = cookies_from_account(account)
    csrf = account.get('bili_jct', '')
    
    # 获取act_id
    log("获取act_id...")
    try:
        info, msg = get_mission_info(task_id, cookies)
        act_id = info.get('act_id', VERSION_DEFAULT_ACT_ID.get(task_version, ''))
        log(f"  ✓ act_id: {act_id}")
    except Exception as e:
        act_id = VERSION_DEFAULT_ACT_ID.get(task_version, '')
        log(f"  ⚠ 获取任务信息失败: {e}，使用默认act_id: {act_id}")
    
    task_info = {
        "act_id": act_id,
        "act_name": f"{task_version}版本创作激励计划",
        "task_name": task_name,
        "reward_info": {"award_name": task_award},
    }
    
    # 设置目标时间：当前时间后8-12秒
    now = datetime.now()
    target_seconds = random.randint(8, 12)
    target_time = (now + timedelta(seconds=target_seconds)).replace(microsecond=0)
    target_timestamp = target_time.timestamp()
    target_time_str = target_time.strftime("%H:%M:%S.000")
    
    log(f"目标时间: {target_time_str}")
    
    # 连接预热
    prewarm_time = target_timestamp - 3
    while time.time() < prewarm_time:
        remaining = prewarm_time - time.time()
        if remaining > 1:
            time.sleep(min(remaining / 2, 0.5))
        elif remaining > 0.1:
            time.sleep(0.05)
    
    log("到达预热时间，开始连接预热...")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        resp = session.get("https://www.bilibili.com", timeout=5)
        log(f"  ✓ 连接已建立")
    except Exception as e:
        log(f"  ⚠ 预热失败: {e}")
    
    session.cookies.clear()
    
    # 动态提前量：固定50ms
    dynamic_advance = 50
    fire_time = target_timestamp - dynamic_advance / 1000.0
    
    log(f"[精准首发] 目标 {target_time_str}，动态提前{dynamic_advance}ms发送")
    
    # 自旋等待
    while time.time() < fire_time:
        remaining = fire_time - time.time()
        if remaining > 0.1:
            time.sleep(remaining / 2)
        elif remaining > 0.01:
            time.sleep(0.001)
    
    actual_fire = time.time()
    fire_deviation = (actual_fire - target_timestamp) * 1000
    log(f"[精准首发] 发送！目标偏差: {fire_deviation:.3f}ms")
    
    # 发送请求
    request_start = time.time()
    try:
        ok, msg, data = receive_reward(task_id, task_info, cookies, csrf, session=session)
    except Exception as e:
        ok, msg, data = False, f"异常: {e}", None
    request_end = time.time()
    request_time = (request_end - request_start) * 1000
    
    log(f"请求耗时: {request_time:.1f}ms")
    log(f"响应结果: {msg[:60]}")
    
    response_deviation = (request_end - target_timestamp) * 1000
    log(f"响应到达偏差: {response_deviation:.1f}ms")
    
    # 记录结果
    results.append({
        "test_num": i + 1,
        "account": account_name,
        "task": f"{task_version} - {task_name}",
        "target_time": target_time_str,
        "fire_deviation_ms": round(fire_deviation, 3),
        "request_time_ms": round(request_time, 1),
        "response_deviation_ms": round(response_deviation, 1),
        "response": msg[:60],
        "success": ok,
    })
    
    # 每次测试后保存结果
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    time.sleep(2)

# ===== 测试总结 =====
print()
print("=" * 70)
print(f"{len(results)}次精准首发测试总结")
print("=" * 70)

fire_deviations = [r['fire_deviation_ms'] for r in results]
response_deviations = [r['response_deviation_ms'] for r in results]
request_times = [r['request_time_ms'] for r in results]

print(f"\n【发送偏差统计】")
print(f"  平均值: {sum(fire_deviations)/len(fire_deviations):.3f}ms")
print(f"  最大值: {max(fire_deviations):.3f}ms")
print(f"  最小值: {min(fire_deviations):.3f}ms")
print(f"  标准差: {(sum((x - sum(fire_deviations)/len(fire_deviations))**2 for x in fire_deviations)/len(fire_deviations))**0.5:.3f}ms")

print(f"\n【请求耗时统计】")
print(f"  平均值: {sum(request_times)/len(request_times):.1f}ms")
print(f"  最大值: {max(request_times):.1f}ms")
print(f"  最小值: {min(request_times):.1f}ms")
print(f"  中位数: {sorted(request_times)[len(request_times)//2]:.1f}ms")

print(f"\n【响应偏差统计】")
print(f"  平均值: {sum(response_deviations)/len(response_deviations):.1f}ms")
print(f"  最大值: {max(response_deviations):.1f}ms")
print(f"  最小值: {min(response_deviations):.1f}ms")
print(f"  中位数: {sorted(response_deviations)[len(response_deviations)//2]:.1f}ms")

delayed_count = sum(1 for d in response_deviations if d > 0)
print(f"\n【延后到达统计】")
print(f"  延后到达次数: {delayed_count}/{len(results)} ({delayed_count/len(results)*100:.1f}%)")
print(f"  提前到达次数: {len(results) - delayed_count}/{len(results)} ({(len(results)-delayed_count)/len(results)*100:.1f}%)")

print(f"\n【响应偏差分布】")
ranges = [(0, 50), (50, 100), (100, 150), (150, 200), (200, 300), (300, 500), (500, 1000)]
for low, high in ranges:
    count = sum(1 for d in response_deviations if low <= d < high)
    if count > 0:
        print(f"  {low}-{high}ms: {count}次 ({count/len(results)*100:.1f}%)")
negative_count = sum(1 for d in response_deviations if d < 0)
if negative_count > 0:
    print(f"  <0ms (提前到达): {negative_count}次 ({negative_count/len(results)*100:.1f}%)")

print(f"\n详细数据已保存到: {results_path}")
print("=" * 70)
