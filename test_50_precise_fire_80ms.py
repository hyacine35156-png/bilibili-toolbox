#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
50次精准首发测试（动态提前量80ms）
测试不同账号、不同任务的精准首发效果
"""

import sys
import os
import json
import time
import random
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入主程序模块
import main_gui_pro as main_module


def log(msg):
    """带时间戳的日志输出"""
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"
    print(f"[{timestamp}] {msg}", flush=True)


def run_test():
    """运行50次精准首发测试"""
    
    print("=" * 70)
    print("50次精准首发测试（动态提前量80ms）")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print("=" * 70)
    
    # 加载账户
    accounts_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "data", "accounts.json")
    with open(accounts_file, "r", encoding="utf-8") as f:
        accounts_list = json.load(f)
    
    accounts = [acc["name"] for acc in accounts_list]
    accounts_dict = {acc["name"]: acc for acc in accounts_list}
    log(f"加载到 {len(accounts)} 个账户")
    
    # 测试任务列表（不同游戏、不同类型）
    test_tasks = [
        {"game": "鸣潮3.6", "task_name": "开播时长60min", "task_id": "6ERAcwloghvu4d00", "act_id": "1ERAzwloghvn7l00"},
        {"game": "绝区零3.2", "task_name": "开播60min", "task_id": "6ERAcwloghvuse00", "act_id": "1ERAzwloghvbmi00"},
        {"game": "崩坏星穹铁道4.5", "task_name": "累计1天投稿-上半", "task_id": "6ERAcwloghvsaz00", "act_id": "1ERAzwloghvb5600"},
        {"game": "绝区零3.2", "task_name": "收获2电池", "task_id": "6ERAcwloghvyxs00", "act_id": "1ERAzwloghvbmi00"},
        {"game": "绝区零3.2", "task_name": "大于10条弹幕", "task_id": "6ERAcwloghvabs00", "act_id": "1ERAzwloghvbmi00"},
        {"game": "绝区零3.2", "task_name": "至少一名用户看播≥10分钟", "task_id": "6ERAcwloghvsp000", "act_id": "1ERAzwloghvbmi00"},
        {"game": "崩坏星穹铁道4.5", "task_name": "累计3天投稿三连×2", "task_id": "6ERAcwloghvsal00", "act_id": "1ERAzwloghvb5600"},
        {"game": "崩坏星穹铁道4.5", "task_name": "累计5天投稿三连≥5且播放≥1000", "task_id": "6ERAcwloghvudj00", "act_id": "1ERAzwloghvb5600"},
        {"game": "崩坏星穹铁道4.5", "task_name": "累计7天投稿总播≥2000且三连≥30", "task_id": "18ERA1wloghvbtg00", "act_id": "1ERAzwloghvb5600"},
        {"game": "崩坏星穹铁道4.5", "task_name": "累计10天投稿", "task_id": "18ERA1wloghvv0w00", "act_id": "1ERAzwloghvb5600"},
    ]
    
    results = []
    
    for i in range(50):
        task_idx = i % len(test_tasks)
        account_idx = i % len(accounts)
        task = test_tasks[task_idx]
        account_name = accounts[account_idx]
        account_cookies = accounts_dict[account_name]
        
        print()
        print("=" * 70)
        print(f"第 {i+1}/50 次测试")
        print(f"账号: {account_name}")
        print(f"任务: {task['game']} - {task['task_name']}")
        print("=" * 70)
        
        # 计算目标时间（当前时间后10-15秒，取整秒+000毫秒）
        now = time.time()
        target_seconds = int(now) + random.randint(10, 15)
        target_timestamp = float(target_seconds)  # 整秒，毫秒为000
        target_time = datetime.fromtimestamp(target_timestamp)
        target_time_str = target_time.strftime("%H:%M:%S.000")
        
        log(f"目标时间: {target_time_str}")
        
        # 等待到预热时间（目标时间前3秒）
        prewarm_time = target_timestamp - 3
        while time.time() < prewarm_time:
            time.sleep(0.1)
        
        log("到达预热时间，开始连接预热...")
        
        # 连接预热
        import requests
        session = requests.Session()
        try:
            start = time.time()
            resp = session.get("https://www.bilibili.com", timeout=5)
            rtt = (time.time() - start) * 1000
            log(f"  ✓ 连接已建立 (RTT={rtt:.1f}ms)")
        except Exception as e:
            log(f"  ⚠ 预热失败: {e}")
        
        # 清除session cookies（避免buvid3/b_nut与用户cookie合并导致[-351]错误）
        session.cookies.clear()
        
        # 动态提前量80ms
        dynamic_advance = 100
        fire_time = target_timestamp - dynamic_advance / 1000.0
        
        log(f"[精准首发] 目标 {target_time_str}，动态提前{dynamic_advance}ms发送")
        
        # 自旋等待
        while time.time() < fire_time:
            remaining = fire_time - time.time()
            if remaining > 0.1:
                time.sleep(remaining / 2)
            elif remaining > 0.01:
                time.sleep(0.005)
            # <10ms时自旋，不sleep
        
        actual_fire_time = time.time()
        fire_deviation = (actual_fire_time - target_timestamp) * 1000 + dynamic_advance  # 应该接近0
        
        log(f"[精准首发] 发送！目标偏差: {fire_deviation:.3f}ms")
        
        # 发送领取请求
        try:
            start = time.time()
            
            # 构造cookies（只包含必要字段，避免中文字符导致latin-1编码错误）
            cookies = {}
            for key in ["SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "buvid3", "b_nut"]:
                if key in account_cookies and isinstance(account_cookies[key], str):
                    cookies[key] = account_cookies[key]
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            }
            
            # 获取csrf
            csrf = cookies.get("bili_jct", "")
            
            data = {
                "task_id": task["task_id"],
                "activity_id": task["act_id"],
                "ActivityId": task["act_id"],
                "act_id": task["act_id"],
                "activity_name": task["game"],
                "ActivityName": task["game"],
                "act_name": task["game"],
                "task_name": task["task_name"],
                "TaskName": task["task_name"],
                "reward_name": "测试奖励",
                "RewardName": "测试奖励",
                "gaia_vtoken": "",
                "receive_from": "mission",
                "csrf": csrf,
            }
            
            import urllib.parse
            data_encoded = urllib.parse.urlencode(data).encode('utf-8')
            
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
            
            resp = session.post(
                "https://api.bilibili.com/x/activity_components/mission/receive",
                cookies=cookies,
                headers=headers,
                data=data_encoded,
                timeout=10
            )
            
            request_time = (time.time() - start) * 1000
            arrival_deviation = (time.time() - target_timestamp) * 1000
            
            # 解析响应
            try:
                result = resp.json()
                code = result.get("code", -999)
                message = result.get("message", "未知错误")
                
                if code == 0:
                    result_msg = "领取成功"
                elif code == -702:
                    result_msg = f"风控 [{code}] {message}"
                elif code == -705:
                    result_msg = f"风控 [{code}] {message}"
                elif code == -509:
                    result_msg = f"风控 [{code}] {message}"
                elif code == -351:
                    result_msg = f"反作弊 [{code}] {message}"
                elif code == 202032:
                    result_msg = f"[{code}] 无资格领取奖励"
                elif code == 202120:
                    result_msg = f"[{code}] 未到领取时间"
                elif code == 202100:
                    result_msg = f"[{code}] 该用户需要验证"
                elif code == 202118:
                    result_msg = f"[{code}] 命中任务发奖人群包"
                else:
                    result_msg = f"[{code}] {message}"
            except:
                result_msg = f"响应解析失败: {resp.text[:100]}"
            
            log(f"请求耗时: {request_time:.1f}ms")
            log(f"响应结果: {result_msg}")
            log(f"响应到达偏差: {arrival_deviation:.1f}ms")
            
            results.append({
                "index": i + 1,
                "account": account_name,
                "task": f"{task['game']} - {task['task_name']}",
                "target_time": target_time_str,
                "fire_deviation_ms": round(fire_deviation, 3),
                "request_time_ms": round(request_time, 1),
                "arrival_deviation_ms": round(arrival_deviation, 1),
                "result": result_msg,
                "is_late": arrival_deviation > 0,
            })
            
        except Exception as e:
            log(f"请求异常: {e}")
            results.append({
                "index": i + 1,
                "account": account_name,
                "task": f"{task['game']} - {task['task_name']}",
                "target_time": target_time_str,
                "fire_deviation_ms": round(fire_deviation, 3),
                "request_time_ms": 0,
                "arrival_deviation_ms": 0,
                "result": f"异常: {e}",
                "is_late": False,
            })
        
        # 关闭session
        session.close()
        
        # 测试间间隔2秒
        if i < 49:
            time.sleep(2)
    
    # 统计结果
    print()
    print("=" * 70)
    print("50次精准首发测试总结（动态提前量80ms）")
    print("=" * 70)
    
    # 发送偏差统计
    fire_deviations = [r["fire_deviation_ms"] for r in results if r["request_time_ms"] > 0]
    if fire_deviations:
        avg_fire = sum(fire_deviations) / len(fire_deviations)
        max_fire = max(fire_deviations)
        min_fire = min(fire_deviations)
        print()
        print("【发送偏差统计】")
        print(f"  平均值: {avg_fire:.3f}ms")
        print(f"  最大值: {max_fire:.3f}ms")
        print(f"  最小值: {min_fire:.3f}ms")
    
    # 请求耗时统计
    request_times = [r["request_time_ms"] for r in results if r["request_time_ms"] > 0]
    if request_times:
        avg_req = sum(request_times) / len(request_times)
        max_req = max(request_times)
        min_req = min(request_times)
        sorted_req = sorted(request_times)
        median_req = sorted_req[len(sorted_req) // 2]
        print()
        print("【请求耗时统计】")
        print(f"  平均值: {avg_req:.1f}ms")
        print(f"  最大值: {max_req:.1f}ms")
        print(f"  最小值: {min_req:.1f}ms")
        print(f"  中位数: {median_req:.1f}ms")
    
    # 响应偏差统计
    arrival_deviations = [r["arrival_deviation_ms"] for r in results if r["request_time_ms"] > 0]
    if arrival_deviations:
        avg_arr = sum(arrival_deviations) / len(arrival_deviations)
        max_arr = max(arrival_deviations)
        min_arr = min(arrival_deviations)
        sorted_arr = sorted(arrival_deviations)
        median_arr = sorted_arr[len(sorted_arr) // 2]
        print()
        print("【响应偏差统计】")
        print(f"  平均值: {avg_arr:.1f}ms")
        print(f"  最大值: {max_arr:.1f}ms")
        print(f"  最小值: {min_arr:.1f}ms")
        print(f"  中位数: {median_arr:.1f}ms")
    
    # 延后到达统计
    late_count = sum(1 for r in results if r["is_late"])
    early_count = sum(1 for r in results if not r["is_late"] and r["request_time_ms"] > 0)
    total_valid = late_count + early_count
    print()
    print("【延后到达统计】")
    print(f"  延后到达次数: {late_count}/{total_valid} ({late_count/total_valid*100:.1f}%)")
    print(f"  提前到达次数: {early_count}/{total_valid} ({early_count/total_valid*100:.1f}%)")
    
    # 响应偏差分布
    print()
    print("【响应偏差分布】")
    ranges = [
        ("<0ms (提前)", -9999, 0),
        ("0-50ms", 0, 50),
        ("50-100ms", 50, 100),
        ("100-150ms", 100, 150),
        ("150-200ms", 150, 200),
        ("200-300ms", 200, 300),
        ("300-500ms", 300, 500),
        ("500-1000ms", 500, 1000),
    ]
    for label, low, high in ranges:
        count = sum(1 for r in results if low <= r["arrival_deviation_ms"] < high and r["request_time_ms"] > 0)
        if count > 0:
            print(f"  {label}: {count}次 ({count/total_valid*100:.1f}%)")
    
    # 保存详细结果
    results_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_50_results_80ms.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"详细数据已保存到: {results_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_test()
