import sys
import os
import json
import time
import threading
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main_gui_pro import receive_reward

TEST_TASK_ID = "6ERAcwloghvsaz00"
TEST_ACT_ID = "1ERAzwloghvb5600"
FREQS = [850, 900, 950, 1000]
REQUESTS_PER_FREQ = 100
COOLDOWN_BETWEEN_FREQ = 120

def load_accounts():
    accounts_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "data", "accounts.json")
    if os.path.exists(accounts_file):
        with open(accounts_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

results = {}
lock = threading.Lock()
log_file = open("risk_test_800_1000_log.txt", "w", encoding="utf-8")

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file.write(line + "\n")
    log_file.flush()

def test_account(acc_name, cookies):
    log(f"[{acc_name}] 线程启动")
    for freq in FREQS:
        log(f"[{acc_name}] 开始频率 {freq}ms ({FREQS.index(freq)+1}/{len(FREQS)})")
        stats = {
            "total": 0, "success": 0,
            "risk_-702": 0, "risk_-705": 0, "risk_-509": 0, "risk_other": 0,
            "other_error": 0, "error_codes": {}, "rtt_list": []
        }
        for i in range(REQUESTS_PER_FREQ):
            t0 = time.time()
            try:
                ok, msg, data = receive_reward(TEST_TASK_ID, TEST_ACT_ID, cookies)
            except Exception as e:
                ok, msg = False, f"异常: {e}"
            rtt = (time.time() - t0) * 1000
            stats["total"] += 1
            stats["rtt_list"].append(rtt)

            code = ""
            if msg.startswith("["):
                end = msg.find("]")
                if end > 0:
                    code = msg[1:end]
            stats["error_codes"][code] = stats["error_codes"].get(code, 0) + 1

            if ok:
                stats["success"] += 1
            elif "-702" in msg or "702" == code:
                stats["risk_-702"] += 1
            elif "-705" in msg or "705" == code:
                stats["risk_-705"] += 1
            elif "-509" in msg or "509" == code:
                stats["risk_-509"] += 1
            elif "请求过于频繁" in msg or "请求频率过高" in msg:
                stats["risk_other"] += 1
            else:
                stats["other_error"] += 1

            if (i + 1) % 25 == 0:
                risk = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
                log(f"[{acc_name}] 频率{freq}ms 进度{i+1}/{REQUESTS_PER_FREQ}, 通过={stats['success']}, 风控={risk}")

            time.sleep(freq / 1000.0)

        risk = stats["risk_-702"] + stats["risk_-705"] + stats["risk_-509"] + stats["risk_other"]
        avg_rtt = sum(stats["rtt_list"]) / len(stats["rtt_list"]) if stats["rtt_list"] else 0
        stats["risk_rate"] = risk / stats["total"] * 100
        stats["pass_rate"] = stats["success"] / stats["total"] * 100
        stats["rtt_avg"] = avg_rtt
        stats["rtt_min"] = min(stats["rtt_list"]) if stats["rtt_list"] else 0
        stats["rtt_max"] = max(stats["rtt_list"]) if stats["rtt_list"] else 0

        with lock:
            if acc_name not in results:
                results[acc_name] = {}
            results[acc_name][str(freq)] = stats

        log(f"[{acc_name}] 频率{freq}ms完成: 通过={stats['success']} 风控={risk}({risk/REQUESTS_PER_FREQ*100:.1f}%) 其他={stats['other_error']} RTT={avg_rtt:.0f}ms")
        log(f"[{acc_name}] 冷却 {COOLDOWN_BETWEEN_FREQ}s...")
        time.sleep(COOLDOWN_BETWEEN_FREQ)

    log(f"[{acc_name}] 全部频率测试完成！")

def main():
    log("=" * 60)
    log("风控间隔测试（800-1000ms区间验证线性关系）")
    log(f"频率档位: {FREQS}ms")
    log(f"每档请求次数: {REQUESTS_PER_FREQ}")
    log(f"同账号频率间冷却: {COOLDOWN_BETWEEN_FREQ}s")
    log("=" * 60)

    accounts = load_accounts()
    log(f"从 dist/data/accounts.json 加载到 {len(accounts)} 个账号，并发测试")
    for acc in accounts:
        log(f"  - {acc['name']}")

    threads = []
    for acc in accounts:
        t = threading.Thread(target=test_account, args=(acc["name"], acc["cookies"]), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(1)

    for t in threads:
        t.join()

    log("\n" + "=" * 60)
    log("全部测试完成！汇总结果：")
    log("=" * 60)
    log("\n按频率汇总（所有账号平均）：")
    log(f"{'频率(ms)':<12} {'平均风控率':<14} {'平均通过率':<14} {'账号数':<8}")
    for freq in FREQS:
        risks = []
        passes = []
        for acc_name in results:
            if str(freq) in results[acc_name]:
                s = results[acc_name][str(freq)]
                risk = s["risk_-702"] + s["risk_-705"] + s["risk_-509"] + s["risk_other"]
                risks.append(risk / s["total"] * 100)
                passes.append(s["success"] / s["total"] * 100)
        avg_risk = sum(risks) / len(risks) if risks else 0
        avg_pass = sum(passes) / len(passes) if passes else 0
        log(f"{freq:<12} {avg_risk:<13.1f}% {avg_pass:<13.1f}% {len(risks):<8}")

    with open("risk_test_results_800_1000.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log(f"\n结果已保存到: risk_test_results_800_1000.json")
    log(f"日志已保存到: risk_test_800_1000_log.txt")
    log_file.close()

if __name__ == "__main__":
    main()
