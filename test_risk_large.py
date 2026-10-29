#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控间隔大样本测试
每个账号每个频率测100次，调查风控率
避免数据相互影响：频率间冷却120s，账号间冷却300s
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入项目模块
from main_gui_pro import (
    cookies_from_account,
    get_mission_info,
    receive_reward,
    AccountManager,
    MISSION_RECEIVE_API,
    HEADERS,
)

# 测试参数
TEST_TASK_ID = "6ERAcwloghvsaz00"  # 累计1天投稿-上半（已领取）
TEST_ACT_ID = "1ERAzwloghvb5600"
FREQUENCIES = [500, 550, 600, 650, 700, 750, 800]  # ms
REQUESTS_PER_TEST = 100
COOLDOWN_BETWEEN_FREQ = 120  # 同账号不同频率间冷却（秒）
COOLDOWN_BETWEEN_ACCOUNT = 300  # 不同账号间冷却（秒）

# 结果保存
RESULTS_FILE = "risk_test_results_large.json"
LOG_FILE = "risk_test_large_log.txt"

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_accounts():
    """加载所有账号"""
    account_mgr = AccountManager()
    accounts = account_mgr.accounts
    log(f"加载到 {len(accounts)} 个账号")
    for acc in accounts:
        log(f"  - {acc.get('name', '未知')}")
    return accounts

def build_task_info():
    """构建任务信息"""
    return {
        "act_id": TEST_ACT_ID,
        "act_name": "崩坏星穹铁道4.5版本激励计划",
        "task_name": "累计1天投稿-上半",
        "reward_info": {"award_name": "星琼*50-上半任务1"},
    }

def test_single_frequency(account, interval_ms, task_info):
    """测试单个账号单个频率，返回统计结果"""
    cookies = cookies_from_account(account)
    csrf = account.get("bili_jct", "")
    session = requests.Session()
    session.headers.update(HEADERS)

    stats = {
        "total": 0,
        "success": 0,  # 领取成功或已领取（通过）
        "risk_-702": 0,
        "risk_-705": 0,
        "risk_-509": 0,
        "risk_other": 0,
        "other_error": 0,
        "error_codes": {},
        "rtt_list": [],
    }

    interval_s = interval_ms / 1000.0

    for i in range(REQUESTS_PER_TEST):
        stats["total"] += 1
        t0 = time.time()
        try:
            ok, msg, data = receive_reward(TEST_TASK_ID, task_info, cookies, csrf, session)
            rtt = (time.time() - t0) * 1000
            stats["rtt_list"].append(rtt)

            if ok:
                stats["success"] += 1
            else:
                # 解析错误码
                code = ""
                if msg.startswith("["):
                    end = msg.find("]")
                    if end > 0:
                        code = msg[1:end]

                if code in stats["error_codes"]:
                    stats["error_codes"][code] += 1
                else:
                    stats["error_codes"][code] = 1

                if "-702" in msg or "702" in code:
                    stats["risk_-702"] += 1
                elif "-705" in msg or "705" in code:
                    stats["risk_-705"] += 1
                elif "-509" in msg or "509" in code:
                    stats["risk_-509"] += 1
                elif "请求过于频繁" in msg or "请求频率过高" in msg:
                    stats["risk_other"] += 1
                else:
                    stats["other_error"] += 1

        except Exception as e:
            stats["other_error"] += 1
            if "exception" in stats["error_codes"]:
                stats["error_codes"]["exception"] += 1
            else:
                stats["error_codes"]["exception"] = 1

        # 打印进度（每10次）
        if (i + 1) % 20 == 0:
            risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
            log(f"    进度 {i+1}/{REQUESTS_PER_TEST}, 通过={stats['success']}, 风控={risk_total}, 其他={stats['other_error']}")

        # 等待到下次请求（最后一次不等）
        if i < REQUESTS_PER_TEST - 1:
            elapsed = time.time() - t0
            sleep_time = max(0, interval_s - elapsed)
            time.sleep(sleep_time)

    # 计算风控率
    risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
    stats["risk_rate"] = risk_total / stats["total"] if stats["total"] > 0 else 0
    stats["pass_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0

    # RTT统计
    if stats["rtt_list"]:
        stats["rtt_avg"] = sum(stats["rtt_list"]) / len(stats["rtt_list"])
        stats["rtt_min"] = min(stats["rtt_list"])
        stats["rtt_max"] = max(stats["rtt_list"])
    else:
        stats["rtt_avg"] = 0
        stats["rtt_min"] = 0
        stats["rtt_max"] = 0

    return stats

def main():
    log("=" * 60)
    log("风控间隔大样本测试开始")
    log(f"频率档位: {FREQUENCIES}ms")
    log(f"每档请求次数: {REQUESTS_PER_TEST}")
    log(f"频率间冷却: {COOLDOWN_BETWEEN_FREQ}s")
    log(f"账号间冷却: {COOLDOWN_BETWEEN_ACCOUNT}s")
    log("=" * 60)

    accounts = load_accounts()
    task_info = build_task_info()

    all_results = {}

    for acc_idx, account in enumerate(accounts):
        acc_name = account.get("name", f"账号{acc_idx}")
        log(f"\n{'='*60}")
        log(f"账号 {acc_idx+1}/{len(accounts)}: {acc_name}")
        log(f"{'='*60}")

        all_results[acc_name] = {}

        for freq_idx, interval_ms in enumerate(FREQUENCIES):
            log(f"\n--- 频率 {interval_ms}ms ({freq_idx+1}/{len(FREQUENCIES)}) ---")

            stats = test_single_frequency(account, interval_ms, task_info)
            all_results[acc_name][str(interval_ms)] = stats

            risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
            log(f"  结果: 总{stats['total']} 通过{stats['success']} 风控{risk_total}({stats['risk_rate']*100:.1f}%) 其他{stats['other_error']}")
            log(f"  风控码: -702={stats['risk_-702']} -705={stats['risk_-705']} -509={stats['risk_-509']} 其他={stats['risk_other']}")
            log(f"  RTT: avg={stats['rtt_avg']:.0f}ms min={stats['rtt_min']:.0f}ms max={stats['rtt_max']:.0f}ms")
            log(f"  错误码分布: {json.dumps(stats['error_codes'], ensure_ascii=False)}")

            # 保存中间结果
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)

            # 频率间冷却（最后一个频率不等）
            if freq_idx < len(FREQUENCIES) - 1:
                log(f"  冷却 {COOLDOWN_BETWEEN_FREQ}s...")
                time.sleep(COOLDOWN_BETWEEN_FREQ)

        # 账号间冷却（最后一个账号不等）
        if acc_idx < len(accounts) - 1:
            log(f"\n账号间冷却 {COOLDOWN_BETWEEN_ACCOUNT}s...")
            time.sleep(COOLDOWN_BETWEEN_ACCOUNT)

    # 汇总结果
    log("\n" + "=" * 60)
    log("测试完成！汇总结果：")
    log("=" * 60)

    # 按频率汇总（所有账号平均）
    freq_summary = {}
    for interval_ms in FREQUENCIES:
        key = str(interval_ms)
        total_risk_rate = 0
        total_pass_rate = 0
        count = 0
        for acc_name in all_results:
            if key in all_results[acc_name]:
                total_risk_rate += all_results[acc_name][key]["risk_rate"]
                total_pass_rate += all_results[acc_name][key]["pass_rate"]
                count += 1
        if count > 0:
            freq_summary[key] = {
                "avg_risk_rate": total_risk_rate / count,
                "avg_pass_rate": total_pass_rate / count,
                "account_count": count,
            }

    log("\n按频率汇总（所有账号平均）：")
    log(f"{'频率(ms)':<12} {'平均风控率':<12} {'平均通过率':<12} {'账号数':<8}")
    for interval_ms in FREQUENCIES:
        key = str(interval_ms)
        if key in freq_summary:
            s = freq_summary[key]
            log(f"{interval_ms:<12} {s['avg_risk_rate']*100:<11.1f}% {s['avg_pass_rate']*100:<11.1f}% {s['account_count']:<8}")

    # 保存汇总
    all_results["_summary_by_frequency"] = freq_summary
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    log(f"\n结果已保存到: {RESULTS_FILE}")
    log(f"日志已保存到: {LOG_FILE}")

if __name__ == "__main__":
    main()
