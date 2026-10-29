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


# ============================================================
# v6.3.0 新增：稀有货币判定 + 手动剔除
# ============================================================

# 四个游戏的"稀有货币"关键词（用户已确认：抽卡券也算稀有）
#   原神        -> 原石
#   星铁        -> 星琼、星轨通票
#   绝区零      -> 菲林、原装母带
#   鸣潮        -> 星声、唤声涡纹
RARE_KEYWORDS = {
    "原神": ["原石"],
    "崩坏星穹铁道": ["星琼", "星轨通票"],
    "绝区零": ["菲林", "原装母带"],
    "鸣潮": ["星声", "唤声涡纹"],
}

# 版本名 -> 游戏名（版本形如 "原神7.1" / "崩坏星穹铁道4.6"）
def game_of_version(version):
    """从版本名推断游戏名。未知返回空串。"""
    v = str(version or "")
    for g in RARE_KEYWORDS:
        if g in v:
            return g
    return ""

# 奖励名 -> 所属游戏（用于历史记录无 version 字段时的兜底推断）
_AWARD_GAME_HINT = {
    "原石": "原神",
    "摩拉": "原神",
    "精锻用魔矿": "原神",
    "大英雄的经验": "原神",
    "冒险家的经验": "原神",
    "星琼": "崩坏星穹铁道",
    "星轨通票": "崩坏星穹铁道",
    "冒险记录": "崩坏星穹铁道",
    "遗失碎金": "崩坏星穹铁道",
    "漫游指南": "崩坏星穹铁道",
    "信用点": "崩坏星穹铁道",
    "菲林": "绝区零",
    "丁尼": "绝区零",
    "资深调查员记录": "绝区零",
    "原装母带": "绝区零",
    "音擎能源模块": "绝区零",
    "星声": "鸣潮",
    "唤声涡纹": "鸣潮",
    "贝币": "鸣潮",
    "中级共鸣促剂": "鸣潮",
    "中级能源核心": "鸣潮",
    "中级复苏吸雾": "鸣潮",
}


def is_rare_award(award, version=""):
    """判断一个奖励是否属于"稀有货币"。

    返回 True / False / None
      True  = 稀有（保留在统计里）
      False = 非稀有（可被"仅看稀有"过滤掉）
      None  = 无法判定（奖励名或版本都识别不出，按稀有处理，避免误删）
    """
    a = str(award or "")
    if not a:
        return None
    game = game_of_version(version)
    if not game:
        # 无版本信息时，用奖励名反推游戏
        for kw, g in _AWARD_GAME_HINT.items():
            if kw in a:
                game = g
                break
    if not game:
        return None
    kws = RARE_KEYWORDS.get(game, [])
    if not kws:
        return None
    return any(k in a for k in kws)


def is_task_rare(task_name, task_id="", version=""):
    """判断一个任务是否产出稀有货币。

    优先用任务库（tasks_official.json）精确匹配，匹配不到再用任务名兜底。
    返回 True/False/None，语义同 is_rare_award。
    """
    info = lookup_task_award(task_name, task_id, version)
    if info:
        return is_rare_award(info.get("award", ""), info.get("version", "") or version)
    return None


# 任务库缓存（避免每次都读文件）
_task_index = {"loaded": False, "by_id": {}, "by_name": {}}


def _load_task_index():
    """懒加载任务库索引。"""
    if _task_index["loaded"]:
        return
    _task_index["loaded"] = True
    try:
        from config import TASKS_FILE
        if not TASKS_FILE.exists():
            return
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        tasks = data.get("tasks", []) if isinstance(data, dict) else data
        by_id = {}
        by_name = {}
        for t in tasks or []:
            if not isinstance(t, dict):
                continue
            tid = str(t.get("task_id", ""))
            nm = str(t.get("name", ""))
            item = {"award": t.get("award", ""), "version": t.get("version", "")}
            if tid:
                by_id[tid] = item
            if nm:
                by_name.setdefault(nm, []).append(item)
        _task_index["by_id"] = by_id
        _task_index["by_name"] = by_name
    except Exception:
        pass


def lookup_task_award(task_name, task_id="", version=""):
    """查任务对应的奖励信息。返回 {"award":..,"version":..} 或 None。"""
    _load_task_index()
    tid = str(task_id or "")
    if tid and tid in _task_index["by_id"]:
        return _task_index["by_id"][tid]
    nm = str(task_name or "")
    cands = _task_index["by_name"].get(nm)
    if not cands:
        return None
    # 同名任务可能出现在多个版本，用 version 优先筛选
    v = str(version or "")
    if v:
        for c in cands:
            if c.get("version") == v:
                return c
    # 只有一个候选就直接用；多个且无法区分时返回 None（避免误判）
    return cands[0] if len(cands) == 1 else None


# ---------------- 手动剔除 ----------------

EXCLUDED_FILE = BASE_DIR / "rush_excluded.json"


def load_excluded():
    """读取手动剔除的记录键集合。

    剔除键 = "ts|task_name"（时间戳+任务名，足够唯一且不需记录行号）。
    返回 set。
    """
    try:
        if not EXCLUDED_FILE.exists():
            return set()
        data = json.loads(EXCLUDED_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            items = data.get("keys", [])
        elif isinstance(data, list):
            items = data
        else:
            items = []
        return set(str(x) for x in items)
    except Exception:
        return set()


def save_excluded(keys):
    """保存手动剔除集合。"""
    try:
        from storage import atomic_write_json
        atomic_write_json(EXCLUDED_FILE, {"keys": sorted(str(k) for k in keys)})
        return True
    except Exception:
        try:
            EXCLUDED_FILE.parent.mkdir(parents=True, exist_ok=True)
            EXCLUDED_FILE.write_text(
                json.dumps({"keys": sorted(str(k) for k in keys)}, ensure_ascii=False),
                encoding="utf-8")
            return True
        except Exception:
            return False


def make_record_key(rec):
    """从一条记录生成剔除键。"""
    return f"{rec.get('ts','')}|{rec.get('task_name','')}"


def toggle_excluded(rec, excluded_set):
    """把一条记录在剔除/恢复之间切换。返回新的 set 和当前是否已剔除。"""
    k = make_record_key(rec)
    s = set(excluded_set)
    if k in s:
        s.discard(k)
        now_excluded = False
    else:
        s.add(k)
        now_excluded = True
    return s, now_excluded


def _rollover_if_needed():
    try:
        if RESULTS_FILE.exists() and RESULTS_FILE.stat().st_size > _MAX_BYTES:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            os.replace(str(RESULTS_FILE), str(RESULTS_FILE.with_suffix(f".{stamp}.jsonl")))
    except Exception:
        pass


def record(task_id="", task_name="", account="", act_id="",
           result="failed", code="", message="", latency_ms=0, attempt=1,
           advance_ms=0, award="", version="", extra=None):
    """追加一条抢码结果。任何异常都吞掉，绝不影响抢码主流程。

    v6.2.0 新增 advance_ms：本次使用的提前量，用于统计"哪个提前量抢中最多"。
    v6.3.0 新增 award/version：奖励名称 + 所属游戏版本，
           用于按"稀有货币"筛选统计（方案B：新记录精确可筛）。
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
        "award": str(award or ""),
        "version": str(version or ""),
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


def dashboard(limit=20000, rare_only=False, include_excluded=False,
              excluded_set=None):
    """抢码成功率仪表盘数据（v6.2.0 新增，v6.3.0 支持过滤）。

    参数：
      rare_only         True = 只统计产出稀有货币的任务
      include_excluded  True = 连手动剔除的记录也纳入统计
      excluded_set      手动剔除键集合（None 则自动读取 rush_excluded.json）

    返回：
      overview     总览（总数/成功率/平均延迟/稀有统计）
      by_task      各任务历史成功率
      by_advance   各提前量区间的成功率（找出最优提前量）
      by_hour      风控高发时段（按小时统计失败率与风控次数）
      top_codes    失败码 Top10
      records      明细记录列表（供界面逐条剔除用）
      filters      过滤统计（总共/剔除数/稀有过/非稀有过）
    """
    all_records = load_results(limit=limit)

    if excluded_set is None:
        excluded_set = load_excluded()

    # ---- 过滤阶段 ----
    stat = {"raw_total": len(all_records), "excluded": 0,
            "non_rare": 0, "unknown_rare": 0, "kept": 0}
    records = []
    for r in all_records:
        key = make_record_key(r)
        is_excl = key in excluded_set
        if is_excl:
            stat["excluded"] += 1
            if not include_excluded:
                continue

        # 稀有判定：优先用记录里的 award/version，缺失则回任务库查
        award = str(r.get("award", ""))
        ver = str(r.get("version", ""))
        if not award:
            info = lookup_task_award(r.get("task_name", ""), r.get("task_id", ""), ver)
            if info:
                award = info.get("award", "")
                if not ver:
                    ver = info.get("version", "")

        rare = is_rare_award(award, ver)
        r["_award"] = award
        r["_version"] = ver
        r["_rare"] = rare
        r["_excluded"] = is_excl
        r["_key"] = key

        if rare is None:
            stat["unknown_rare"] += 1
        elif rare is False:
            stat["non_rare"] += 1
            if rare_only:
                continue

        records.append(r)

    stat["kept"] = len(records)
    total = len(records)

    def _is_ok(r):
        return r.get("result") in ("success", "already")

    def _is_risk(r):
        c = str(r.get("code", ""))
        m = str(r.get("message", ""))
        return c in ("-702", "-509", "-705") or "频繁" in m or "风控" in m

    if total == 0:
        return {"total": 0, "overview": {}, "by_task": [],
                "by_advance": [], "by_hour": [], "top_codes": [],
                "records": [], "filters": stat,
                "excluded_set": sorted(excluded_set)}

    ok_cnt = sum(1 for r in records if _is_ok(r))
    lat = [float(r.get("latency_ms") or 0) for r in records if r.get("latency_ms")]
    rare_recs = [r for r in records if r.get("_rare") is True]
    rare_ok = sum(1 for r in rare_recs if _is_ok(r))
    overview = {
        "total": total,
        "success": ok_cnt,
        "failed": total - ok_cnt,
        "success_rate": round(100.0 * ok_cnt / total, 1),
        "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else 0,
        "risk_count": sum(1 for r in records if _is_risk(r)),
        # v6.3.0 稀有统计
        "rare_total": len(rare_recs),
        "rare_success": rare_ok,
        "rare_rate": round(100.0 * rare_ok / len(rare_recs), 1) if rare_recs else 0,
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

    # ---- 明细记录（按时间倒序，供界面逐条剔除）----
    # 只保留界面需要的字段，避免把整个记录都塞给 UI
    detail = []
    for r in records:
        detail.append({
            "ts": str(r.get("ts", "")),
            "task_name": str(r.get("task_name", "")),
            "account": str(r.get("account", "")),
            "result": str(r.get("result", "")),
            "code": str(r.get("code", "")),
            "message": str(r.get("message", ""))[:60],
            "award": str(r.get("_award", "")),
            "version": str(r.get("_version", "")),
            "rare": r.get("_rare"),
            "excluded": bool(r.get("_excluded", False)),
            "key": str(r.get("_key", "")),
        })
    detail.sort(key=lambda x: x["ts"], reverse=True)

    return {
        "total": total,
        "overview": overview,
        "by_task": by_task,
        "by_advance": by_advance,
        "by_hour": by_hour,
        "top_codes": top_codes,
        "records": detail,
        "filters": stat,
        "excluded_set": sorted(excluded_set),
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
