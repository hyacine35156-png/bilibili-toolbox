# -*- coding: utf-8 -*-
"""抢码结果结构化记录（O4）。

原来抢码成功/失败只写文本日志，事后无法统计"哪个任务成功率高""哪个时段风控重"。

本模块把每次领取尝试追加写入 data/rush_results.jsonl（每行一个 JSON）：
  为什么用 jsonl 而不是 json：
  - 追加写无需读-改-写，多线程天然安全，不会像 JSON 数组那样并发丢数据
  - 即使写坏一行，也只影响那一行，不会整个文件失效

字段：
  ts, task_id, task_name, account, act_id, result(success/already/failed/skipped),
  code, message, latency_ms, attempt
"""

import json
import os
import threading
import time
from collections import Counter

from config import BASE_DIR

RESULTS_FILE = BASE_DIR / "rush_results.jsonl"
_MAX_BYTES = 20 * 1024 * 1024   # 20MB 后滚动
_LOCK = threading.Lock()


def _rollover_if_needed():
    try:
        if RESULTS_FILE.exists() and RESULTS_FILE.stat().st_size > _MAX_BYTES:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            os.replace(str(RESULTS_FILE), str(RESULTS_FILE.with_suffix(f".{stamp}.jsonl")))
    except Exception:
        pass


def record(task_id="", task_name="", account="", act_id="",
           result="failed", code="", message="", latency_ms=0, attempt=1,
           advance_ms=0, extra=None):
    """追加一条抢码结果。任何异常都吞掉，绝不影响抢码主流程。

    v6.2.0 新增 advance_ms：本次使用的提前量，用于统计"哪个提前量抢中最多"。
    """
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task_id": str(task_id or ""),
        "task_name": str(task_name or ""),
        "account": str(account or ""),
        "act_id": str(act_id or ""),
        "result": str(result or ""),
        "code": str(code or ""),
        "message": str(message or "")[:200],
        "latency_ms": round(float(latency_ms or 0), 1),
        "attempt": int(attempt or 1),
        "advance_ms": round(float(advance_ms or 0), 1),
    }
    if extra and isinstance(extra, dict):
        try:
            entry.update(extra)
        except Exception:
            pass
    try:
        with _LOCK:
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            _rollover_if_needed()
            with open(RESULTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return entry


def load_results(limit=5000):
    """读取最近的记录（最多 limit 条，返回列表）。"""
    out = []
    try:
        if not RESULTS_FILE.exists():
            return []
        with open(RESULTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return out
    return out[-limit:]


def summary(today_only=True, limit=5000):
    """统计汇总：总数、成功率、失败码 TopN、平均延迟、按任务分组。"""
    records = load_results(limit=limit)
    if today_only:
        today = time.strftime("%Y-%m-%d")
        records = [r for r in records if str(r.get("ts", "")).startswith(today)]

    total = len(records)
    if total == 0:
        return {"total": 0, "success": 0, "already": 0, "failed": 0,
                "success_rate": 0.0, "avg_latency_ms": 0, "top_codes": [],
                "by_task": [], "by_hour": []}

    cnt = Counter(r.get("result", "") for r in records)
    success = cnt.get("success", 0)
    already = cnt.get("already", 0)
    failed = cnt.get("failed", 0) + cnt.get("skipped", 0)

    # 只看真正的失败码
    codes = Counter(
        f"{r.get('code','')} {r.get('message','')[:30]}".strip()
        for r in records if r.get("result") == "failed"
    )
    top_codes = [{"code": c, "count": n} for c, n in codes.most_common(5)]

    lat = [float(r.get("latency_ms") or 0) for r in records if r.get("latency_ms")]
    avg_lat = round(sum(lat) / len(lat), 1) if lat else 0

    # 按任务
    by_task_map = {}
    for r in records:
        key = r.get("task_name") or r.get("task_id") or "?"
        d = by_task_map.setdefault(key, {"task": key, "total": 0, "success": 0})
        d["total"] += 1
        if r.get("result") in ("success", "already"):
            d["success"] += 1
    by_task = sorted(by_task_map.values(), key=lambda x: x["total"], reverse=True)[:10]
    for d in by_task:
        d["rate"] = round(100.0 * d["success"] / d["total"], 1) if d["total"] else 0

    # 按小时（观察风控时段）
    hour_map = {}
    for r in records:
        ts = str(r.get("ts", ""))
        hh = ts[11:13] if len(ts) >= 13 else "?"
        d = hour_map.setdefault(hh, {"hour": hh, "total": 0, "success": 0})
        d["total"] += 1
        if r.get("result") in ("success", "already"):
            d["success"] += 1
    by_hour = sorted(hour_map.values(), key=lambda x: x["hour"])

    return {
        "total": total,
        "success": success,
        "already": already,
        "failed": failed,
        "success_rate": round(100.0 * (success + already) / total, 1) if total else 0,
        "avg_latency_ms": avg_lat,
        "top_codes": top_codes,
        "by_task": by_task,
        "by_hour": by_hour,
    }


def dashboard(limit=20000):
    """抢码成功率仪表盘数据（v6.2.0 新增）。

    返回：
      overview     总览（总数/成功率/平均延迟）
      by_task      各任务历史成功率
      by_advance   各提前量区间的成功率（找出最优提前量）
      by_hour      风控高发时段（按小时统计失败率与风控次数）
      top_codes    失败码 Top10
    """
    records = load_results(limit=limit)
    total = len(records)

    def _is_ok(r):
        return r.get("result") in ("success", "already")

    def _is_risk(r):
        c = str(r.get("code", ""))
        m = str(r.get("message", ""))
        return c in ("-702", "-509", "-705") or "频繁" in m or "风控" in m

    if total == 0:
        return {"total": 0, "overview": {}, "by_task": [],
                "by_advance": [], "by_hour": [], "top_codes": []}

    ok_cnt = sum(1 for r in records if _is_ok(r))
    lat = [float(r.get("latency_ms") or 0) for r in records if r.get("latency_ms")]
    overview = {
        "total": total,
        "success": ok_cnt,
        "failed": total - ok_cnt,
        "success_rate": round(100.0 * ok_cnt / total, 1),
        "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else 0,
        "risk_count": sum(1 for r in records if _is_risk(r)),
    }

    # ---- 各任务成功率 ----
    task_map = {}
    for r in records:
        key = r.get("task_name") or r.get("task_id") or "?"
        d = task_map.setdefault(key, {"task": key, "total": 0, "success": 0, "risk": 0})
        d["total"] += 1
        if _is_ok(r):
            d["success"] += 1
        if _is_risk(r):
            d["risk"] += 1
    by_task = sorted(task_map.values(), key=lambda x: x["total"], reverse=True)[:15]
    for d in by_task:
        d["rate"] = round(100.0 * d["success"] / d["total"], 1) if d["total"] else 0

    # ---- 各提前量区间成功率（找最优提前量）----
    # 按 20ms 分桶
    adv_map = {}
    for r in records:
        a = float(r.get("advance_ms") or 0)
        if a <= 0:
            continue
        bucket = int(a // 20 * 20)
        d = adv_map.setdefault(bucket, {"advance": bucket, "total": 0, "success": 0})
        d["total"] += 1
        if _is_ok(r):
            d["success"] += 1
    by_advance = sorted(adv_map.values(), key=lambda x: x["advance"])
    for d in by_advance:
        d["rate"] = round(100.0 * d["success"] / d["total"], 1) if d["total"] else 0
    # 给每个提前量标注样本是否足够（<5 次视为样本不足）
    for d in by_advance:
        d["reliable"] = d["total"] >= 5

    # ---- 风控高发时段 ----
    hour_map = {}
    for r in records:
        ts = str(r.get("ts", ""))
        hh = ts[11:13] if len(ts) >= 13 else "?"
        d = hour_map.setdefault(hh, {"hour": hh, "total": 0, "success": 0, "risk": 0})
        d["total"] += 1
        if _is_ok(r):
            d["success"] += 1
        if _is_risk(r):
            d["risk"] += 1
    by_hour = sorted(hour_map.values(), key=lambda x: x["hour"])
    for d in by_hour:
        d["success_rate"] = round(100.0 * d["success"] / d["total"], 1) if d["total"] else 0

    # ---- 失败码 Top10 ----
    code_map = {}
    for r in records:
        if _is_ok(r):
            continue
        c = str(r.get("code", "")).strip() or "未知"
        code_map[c] = code_map.get(c, 0) + 1
    top_codes = sorted(code_map.items(), key=lambda x: x[1], reverse=True)[:10]
    top_codes = [{"code": c, "count": n} for c, n in top_codes]

    return {
        "total": total,
        "overview": overview,
        "by_task": by_task,
        "by_advance": by_advance,
        "by_hour": by_hour,
        "top_codes": top_codes,
    }


def best_advance(dashboard_data=None):
    """从仪表盘数据里挑出"样本足够且成功率最高"的提前量。"""
    d = dashboard_data or dashboard()
    best = None
    best_rate = -1
    for item in d.get("by_advance", []):
        if not item.get("reliable"):
            continue
        if item["rate"] > best_rate:
            best_rate = item["rate"]
            best = item
    return best


def risk_hours(dashboard_data=None, min_samples=3):
    """返回风控次数最多的小时列表。"""
    d = dashboard_data or dashboard()
    hours = [h for h in d.get("by_hour", []) if h.get("total", 0) >= min_samples]
    return sorted(hours, key=lambda x: x.get("risk", 0), reverse=True)


def clear_results():
    """清空结果文件（测试/重置用）。"""
    try:
        with _LOCK:
            if RESULTS_FILE.exists():
                RESULTS_FILE.unlink()
        return True
    except Exception:
        return False
