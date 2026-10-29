#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风控间隔大样本测试（多账号并发版）
每个账号独立线程，并发运行
同账号不同频率间冷却120s，避免风控累积
"""

import sys
import os
import json
import time
import requests
import threading
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_gui_pro import (
    cookies_from_account,
    get_mission_info,
    receive_reward,
    AccountManager,
    MISSION_RECEIVE_API,
    HEADERS,
)

# 测试参数
TEST_TASK_ID = "6ERAcwloghvsaz00"
TEST_ACT_ID = "1ERAzwloghvb5600"
FREQUENCIES = [850, 900, 950, 1000]
REQUESTS_PER_TEST = 100
COOLDOWN_BETWEEN_FREQ = 120  # 同账号不同频率间冷却（秒）

RESULTS_FILE = "risk_test_results_800_1000.json"
LOG_FILE = "risk_test_800_1000_log.txt"
LOG_LOCK = threading.Lock()
RESULTS_LOCK = threading.Lock()

def log(msg, acc_name=""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}]"
    if acc_name:
        prefix += f" [{acc_name}]"
    line = f"{prefix} {msg}"
    with LOG_LOCK:
        print(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def load_accounts():
    """直接从dist/data加载账号"""
    accounts_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "data", "accounts.json")
    if os.path.exists(accounts_file):
        with open(accounts_file, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        log(f"从 dist/data/accounts.json 加载到 {len(accounts)} 个账号，并发测试")
        for acc in accounts:
            log(f"  - {acc.get('name', '未知')}")
        return accounts
    else:
        log(f"账号文件不存在: {accounts_file}")
        return []

def build_task_info():
    return {
        "act_id": TEST_ACT_ID,
        "act_name": "崩坏星穹铁道4.5版本激励计划",
        "task_name": "累计1天投稿-上半",
        "reward_info": {"award_name": "星琼*50-上半任务1"},
    }

def test_single_frequency(account, interval_ms, task_info, acc_name):
    """测试单个账号单个频率"""
    cookies = cookies_from_account(account)
    csrf = account.get("bili_jct", "")
    session = requests.Session()
    session.headers.update(HEADERS)

    stats = {
        "total": 0,
        "success": 0,
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
                code = ""
                if msg.startswith("["):
                    end = msg.find("]")
                    if end > 0:
                        code = msg[1:end]

                if code in stats["error_codes"]:
                    stats["error_codes"][code] += 1
                else:
                    stats["error_codes"][code] = 1

                if "-702" in msg or "702" == code:
                    stats["risk_-702"] += 1
                elif "-705" in msg or "705" == code:
                    stats["risk_-705"] += 1
                elif "-509" in msg or "509" == code:
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

        if (i + 1) % 25 == 0:
            risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
            log(f"频率{interval_ms}ms 进度{i+1}/{REQUESTS_PER_TEST}, 通过={stats['success']}, 风控={risk_total}", acc_name)

        if i < REQUESTS_PER_TEST - 1:
            elapsed = time.time() - t0
            sleep_time = max(0, interval_s - elapsed)
            time.sleep(sleep_time)

    risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
    stats["risk_rate"] = risk_total / stats["total"] if stats["total"] > 0 else 0
    stats["pass_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0

    if stats["rtt_list"]:
        stats["rtt_avg"] = sum(stats["rtt_list"]) / len(stats["rtt_list"])
        stats["rtt_min"] = min(stats["rtt_list"])
        stats["rtt_max"] = max(stats["rtt_list"])
    else:
        stats["rtt_avg"] = 0
        stats["rtt_min"] = 0
        stats["rtt_max"] = 0

    return stats

def account_worker(account, task_info, all_results):
    """单个账号的测试线程"""
    acc_name = account.get("name", "未知")
    log(f"线程启动", acc_name)

    for freq_idx, interval_ms in enumerate(FREQUENCIES):
        log(f"开始频率 {interval_ms}ms ({freq_idx+1}/{len(FREQUENCIES)})", acc_name)

        stats = test_single_frequency(account, interval_ms, task_info, acc_name)

        with RESULTS_LOCK:
            if acc_name not in all_results:
                all_results[acc_name] = {}
            all_results[acc_name][str(interval_ms)] = stats
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)

        risk_total = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
        log(f"频率{interval_ms}ms完成: 通过={stats['success']} 风控={risk_total}({stats['risk_rate']*100:.1f}%) 其他={stats['other_error']} RTT={stats['rtt_avg']:.0f}ms", acc_name)

        if freq_idx < len(FREQUENCIES) - 1:
            log(f"冷却 {COOLDOWN_BETWEEN_FREQ}s...", acc_name)
            time.sleep(COOLDOWN_BETWEEN_FREQ)

    log(f"全部频率测试完成！", acc_name)

def main():
    log("=" * 60)
    log("风控间隔大样本测试（多账号并发版）开始")
    log(f"频率档位: {FREQUENCIES}ms")
    log(f"每档请求次数: {REQUESTS_PER_TEST}")
    log(f"同账号频率间冷却: {COOLDOWN_BETWEEN_FREQ}s")
    log(f"预计总时长: 约{int((len(FREQUENCIES) * (REQUESTS_PER_TEST * 0.7 + (len(FREQUENCIES)-1) * COOLDOWN_BETWEEN_FREQ)) / 60)}分钟")
    log("=" * 60)

    accounts = load_accounts()
    task_info = build_task_info()
    all_results = {}

    threads = []
    for account in accounts:
        t = threading.Thread(target=account_worker, args=(account, task_info, all_results), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(1)  # 错开启动，避免同时爆发

    # 等待所有线程完成
    for t in threads:
        t.join()

    # 汇总结果
    log("\n" + "=" * 60)
    log("全部测试完成！汇总结果：")
    log("=" * 60)

    freq_summary = {}
    for interval_ms in FREQUENCIES:
        key = str(interval_ms)
        total_risk_rate = 0
        total_pass_rate = 0
        count = 0
        for acc_name in all_results:
            if acc_name.startswith("_"):
                continue
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

    all_results["_summary_by_frequency"] = freq_summary
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    log(f"\n结果已保存到: {RESULTS_FILE}")
    log(f"日志已保存到: {LOG_FILE}")

if __name__ == "__main__":
    main()
