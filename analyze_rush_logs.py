# -*- coding: utf-8 -*-
"""
抢码日志分析脚本
- 提取0点和1点附近的抢码记录
- 筛选奖励为星琼/星声/原石/菲林/波纹的任务
- 统计成功率、尝试次数、耗时、错误类型等
"""
import os
import re
import json
from collections import defaultdict
from datetime import datetime

LOG_DIR = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\dist\data\logs"
OUTPUT_DIR = r"C:\Users\15868\Desktop"

# 有效奖励关键词
VALID_REWARDS = ["星琼", "星声", "原石", "菲林", "波纹"]

def is_valid_reward(reward_str):
    """判断奖励是否符合统计条件"""
    return any(kw in reward_str for kw in VALID_REWARDS)

def parse_log_file(filepath):
    """解析单个日志文件，返回所有抢码会话"""
    sessions = []
    current_session = None
    current_task = None
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配启动精准抢码
        m = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*启动精准抢码:\s*(.+)', line)
        if m:
            if current_session:
                sessions.append(current_session)
            current_session = {
                "start_time": m.group(1),
                "group_name": m.group(2),
                "target_time": "",
                "tasks": [],
                "file": os.path.basename(filepath)
            }
            current_task = None
            continue
        
        # 匹配目标时间
        m = re.match(r'\[\d{2}:\d{2}:\d{2}\]\s*目标时间:\s*(\d{2}:\d{2}:\d{2})', line)
        if m and current_session:
            current_session["target_time"] = m.group(1)
            continue
        
        # 匹配任务开始
        m = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*\[优先级(\d+)\]\s*开始:\s*(.+?)\s*=>\s*(.+?)\s*\(窗口期(\d+)秒\)', line)
        if m and current_session:
            if current_task:
                current_session["tasks"].append(current_task)
            current_task = {
                "start_time": m.group(1),
                "priority": int(m.group(2)),
                "name": m.group(3),
                "reward": m.group(4),
                "window": int(m.group(5)),
                "attempts": 0,
                "success": False,
                "success_attempt": 0,
                "success_time": "",
                "account": "",
                "errors": [],
                "end_time": "",
                "fail_reason": ""
            }
            continue
        
        # 匹配领取成功（行中包含🎉）
        m = re.search(r'🎉\s*第(\d+)次:\s*领取成功！\((.+?)\)', line)
        if m and current_task:
            current_task["success"] = True
            current_task["success_attempt"] = int(m.group(1))
            current_task["account"] = m.group(2)
            current_task["attempts"] = int(m.group(1))
            # 提取行首时间
            tm = re.match(r'\[(\d{2}:\d{2}:\d{2})\]', line)
            if tm:
                current_task["success_time"] = tm.group(1)
            continue
        
        # 匹配尝试（风控/错误）- 行中包含第N次
        m = re.search(r'\[[\d:.]+->[\d:.]+,\s*\d+ms\]\s*第(\d+)次:\s*(.+)', line)
        if m and current_task and not current_task["success"]:
            attempt_num = int(m.group(1))
            error_msg = m.group(2)
            current_task["attempts"] = attempt_num
            # 提取错误码
            err_match = re.search(r'\[(-\d+)\]', error_msg)
            if err_match:
                current_task["errors"].append(err_match.group(1))
            elif "库存" in error_msg:
                current_task["errors"].append("OUT_OF_STOCK")
            elif "已领取" in error_msg:
                current_task["errors"].append("ALREADY_CLAIMED")
            else:
                current_task["errors"].append("OTHER")
            continue
        
        # 匹配任务失败（未成功）
        if "✗ 未成功" in line and current_task:
            current_task["end_time"] = line[1:9] if line.startswith("[") else ""
            current_task["fail_reason"] = "未成功"
            continue
        
        # 匹配库存已使用完
        if "库存已使用完" in line and current_task and not current_task["success"]:
            current_task["fail_reason"] = "库存已使用完"
            if "OUT_OF_STOCK" not in current_task["errors"]:
                current_task["errors"].append("OUT_OF_STOCK")
            continue
    
    # 收尾
    if current_task:
        current_session["tasks"].append(current_task)
    if current_session:
        sessions.append(current_session)
    
    return sessions

def main():
    all_sessions = []
    
    # 遍历所有日志文件
    for filename in sorted(os.listdir(LOG_DIR)):
        if not filename.startswith("抢码日志_") or not filename.endswith(".txt"):
            continue
        filepath = os.path.join(LOG_DIR, filename)
        sessions = parse_log_file(filepath)
        all_sessions.extend(sessions)
    
    print(f"共解析 {len(all_sessions)} 个抢码会话")
    
    # 筛选0点和1点的会话
    target_sessions = []
    for s in all_sessions:
        target = s["target_time"]
        if target.startswith("00:") or target.startswith("01:"):
            target_sessions.append(s)
    
    print(f"0点/1点会话: {len(target_sessions)} 个")
    
    # 提取所有有效任务（奖励符合条件）
    all_tasks = []
    for s in target_sessions:
        for t in s["tasks"]:
            if is_valid_reward(t["reward"]):
                t["target_time"] = s["target_time"]
                t["group_name"] = s["group_name"]
                t["file"] = s["file"]
                all_tasks.append(t)
    
    print(f"有效任务（星琼/星声/原石/菲林/波纹）: {len(all_tasks)} 个")
    
    # 统计
    stats = {
        "total": len(all_tasks),
        "success": sum(1 for t in all_tasks if t["success"]),
        "fail": sum(1 for t in all_tasks if not t["success"]),
        "by_target": defaultdict(lambda: {"total": 0, "success": 0, "fail": 0}),
        "by_reward_type": defaultdict(lambda: {"total": 0, "success": 0, "fail": 0}),
        "by_priority": defaultdict(lambda: {"total": 0, "success": 0, "fail": 0}),
        "success_attempts_dist": defaultdict(int),
        "fail_reasons": defaultdict(int),
        "error_codes": defaultdict(int),
        "avg_attempts_success": 0,
        "avg_attempts_fail": 0,
        "task_names": defaultdict(lambda: {"total": 0, "success": 0, "fail": 0, "reward": ""}),
    }
    
    success_attempts = []
    fail_attempts = []
    
    for t in all_tasks:
        # 按目标时间
        target = t["target_time"][:2] + "点"
        stats["by_target"][target]["total"] += 1
        if t["success"]:
            stats["by_target"][target]["success"] += 1
        else:
            stats["by_target"][target]["fail"] += 1
        
        # 按奖励类型
        reward_type = "未知"
        for kw in VALID_REWARDS:
            if kw in t["reward"]:
                reward_type = kw
                break
        stats["by_reward_type"][reward_type]["total"] += 1
        if t["success"]:
            stats["by_reward_type"][reward_type]["success"] += 1
        else:
            stats["by_reward_type"][reward_type]["fail"] += 1
        
        # 按优先级
        prio = f"优先级{t['priority']}"
        stats["by_priority"][prio]["total"] += 1
        if t["success"]:
            stats["by_priority"][prio]["success"] += 1
        else:
            stats["by_priority"][prio]["fail"] += 1
        
        # 成功尝试次数分布
        if t["success"]:
            stats["success_attempts_dist"][t["success_attempt"]] += 1
            success_attempts.append(t["success_attempt"])
        else:
            fail_attempts.append(t["attempts"])
            # 失败原因
            if t["fail_reason"]:
                stats["fail_reasons"][t["fail_reason"]] += 1
            elif t["errors"]:
                # 取最后一个错误
                stats["fail_reasons"][t["errors"][-1]] += 1
            else:
                stats["fail_reasons"]["未知"] += 1
        
        # 错误码统计
        for err in t["errors"]:
            stats["error_codes"][err] += 1
        
        # 按任务名
        name = t["name"]
        stats["task_names"][name]["total"] += 1
        stats["task_names"][name]["reward"] = t["reward"]
        if t["success"]:
            stats["task_names"][name]["success"] += 1
        else:
            stats["task_names"][name]["fail"] += 1
    
    if success_attempts:
        stats["avg_attempts_success"] = round(sum(success_attempts) / len(success_attempts), 2)
    if fail_attempts:
        stats["avg_attempts_fail"] = round(sum(fail_attempts) / len(fail_attempts), 2)
    
    # 转换为普通dict
    stats["by_target"] = dict(stats["by_target"])
    stats["by_reward_type"] = dict(stats["by_reward_type"])
    stats["by_priority"] = dict(stats["by_priority"])
    stats["success_attempts_dist"] = dict(stats["success_attempts_dist"])
    stats["fail_reasons"] = dict(stats["fail_reasons"])
    stats["error_codes"] = dict(stats["error_codes"])
    stats["task_names"] = dict(stats["task_names"])
    
    # 保存原始数据
    with open(os.path.join(OUTPUT_DIR, "抢码分析_raw_data.json"), "w", encoding="utf-8") as f:
        json.dump({"tasks": all_tasks, "stats": stats}, f, ensure_ascii=False, indent=2)
    
    print("\n=== 统计结果 ===")
    print(f"总任务数: {stats['total']}")
    print(f"成功: {stats['success']} ({round(stats['success']/stats['total']*100,1)}%)")
    print(f"失败: {stats['fail']} ({round(stats['fail']/stats['total']*100,1)}%)")
    print(f"成功平均尝试次数: {stats['avg_attempts_success']}")
    print(f"失败平均尝试次数: {stats['avg_attempts_fail']}")
    
    return stats, all_tasks

if __name__ == "__main__":
    stats, tasks = main()
