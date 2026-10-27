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


# ============================================================
# v6.4.2：按【任务名 + 日期 + 时间区间】批量剔除（用户需求）
# ============================================================

def parse_filter_spec(task_name="", date_str="", time_from="", time_to=""):
    """解析剔除条件。

    参数（都可空）：
      task_name  任务名（支持部分匹配，如 "累积3天开播"）
      date_str   日期 YYYY-MM-DD，空=不限日期
      time_from  起始时间 HH:MM 或 HH:MM:SS，空=不限
      time_to    结束时间 HH:MM 或 HH:MM:SS，空=不限

    返回 dict：{task_name, date_str, from_sec, to_sec, valid, msg}
    """
    spec = {"task_name": str(task_name or "").strip(),
            "date_str": str(date_str or "").strip(),
            "from_sec": None, "to_sec": None,
            "valid": True, "msg": ""}

    def _to_sec(t):
        t = str(t or "").strip()
        if not t:
            return None
        parts = t.replace("：", ":").split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
                return None
            return h * 3600 + m * 60 + s
        except Exception:
            return None

    if spec["date_str"]:
        import re as _re
        if not _re.match(r"^\d{4}-\d{2}-\d{2}$", spec["date_str"]):
            spec["valid"] = False
            spec["msg"] = "日期格式应为 YYYY-MM-DD"
            return spec

    spec["from_sec"] = _to_sec(time_from)
    spec["to_sec"] = _to_sec(time_to)

    if str(time_from or "").strip() and spec["from_sec"] is None:
        spec["valid"] = False
        spec["msg"] = "起始时间格式应为 HH:MM"
        return spec
    if str(time_to or "").strip() and spec["to_sec"] is None:
        spec["valid"] = False
        spec["msg"] = "结束时间格式应为 HH:MM"
        return spec

    if (spec["from_sec"] is not None and spec["to_sec"] is not None
            and spec["from_sec"] > spec["to_sec"]):
        spec["valid"] = False
        spec["msg"] = "起始时间不能晚于结束时间"
        return spec

    if not (spec["task_name"] or spec["date_str"]
            or spec["from_sec"] is not None or spec["to_sec"] is not None):
        spec["valid"] = False
        spec["msg"] = "请至少填写一个条件"

    return spec


def match_filter(rec, spec):
    """判断一条记录是否满足剔除条件。"""
    if not spec or not spec.get("valid"):
        return False

    # --- 任务名（部分匹配，忽略大小写）---
    tn = spec.get("task_name") or ""
    if tn:
        if tn.lower() not in str(rec.get("task_name", "")).lower():
            return False

    ts = str(rec.get("ts", ""))
    if len(ts) < 19:
        return False

    # --- 日期 ---
    ds = spec.get("date_str") or ""
    if ds and not ts.startswith(ds + " "):
        return False

    # --- 时间区间 ---
    f = spec.get("from_sec")
    t = spec.get("to_sec")
    if f is None and t is None:
        return True   # 只按任务名/日期筛

    try:
        sec = int(ts[11:13]) * 3600 + int(ts[14:16]) * 60 + int(ts[17:19])
    except Exception:
        return False

    if f is not None and sec < f:
        return False
    if t is not None and sec > t:
        return False
    return True


def batch_exclude(records, spec, excluded_set):
    """按条件批量剔除。返回 (新set, 命中数, 命中记录列表)。"""
    s = set(excluded_set)
    hits = []
    for r in records:
        if match_filter(r, spec):
            k = make_record_key(r)
            s.add(k)
            hits.append(r)
    return s, len(hits), hits


def batch_restore(records, spec, excluded_set):
    """按条件批量恢复。返回 (新set, 恢复数, 记录列表)。"""
    s = set(excluded_set)
    hits = []
    for r in records:
        if match_filter(r, spec):
            k = make_record_key(r)
            if k in s:
                s.discard(k)
            hits.append(r)
    return s, len(hits), hits


def _rollover_if_needed():
    try:
        if RESULTS_FILE.exists() and RESULTS_FILE.stat().st_size > _MAX_BYTES:
            stamp = time.strftime("%Y%m%d_%H%M%S")
            os.replace(str(RESULTS_FILE), str(RESULTS_FILE.with_suffix(f".{stamp}.jsonl")))
    except Exception:
        pass


def record(task_id="", task_name="", account="", act_id="",
           result="failed", code="", message="", latency_ms=0, attempt=1,
           advance_ms=0, award="", version="", extra=None,
           session_id="", ntp_offset_ms=0, target_ts=0, fire_ts=0,
           one_way_ms=0, probe_rtt_med=0, probe_valid=0, probe_total=0,
           spin_error_ms=0, is_first_shot=False, arrive_dev_ms=None,
           probe_samples="", window_seconds=0, priority=0, target_time_str=""):
    """追加一条抢码结果。任何异常都吞掉，绝不影响抢码主流程。

    v6.2.0 新增 advance_ms：本次使用的提前量。
    v6.3.0 新增 award/version：奖励名称 + 版本，供稀有奖励筛选。
    v6.4.0 新增程序运行指标（P0-P2 全部 15 项的数据底座）：
      session_id      场次ID（同一次目标时刻的所有请求共用）
      ntp_offset_ms   该场抢码时的时钟偏差（正数=本地慢）
      target_ts       目标时刻（epoch 秒，毫秒精度）
      fire_ts         实际发送时刻（本地 epoch，毫秒精度）
      one_way_ms      估算单程网络延迟（半RTT）
      probe_rtt_med   探针RTT中位数
      probe_valid     探针有效样本数（排除风控响应）
      probe_total     探针总样本数
      spin_error_ms   自旋等待误差（计划发送 vs 实际发送）
      is_first_shot   是否首发请求
      arrive_dev_ms   到达偏差（真实服务器时钟，正数=晚到），仅首发有值
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
        # ---- v6.4.0 程序运行指标 ----
        "session_id": str(session_id or ""),
        "ntp_offset_ms": round(float(ntp_offset_ms or 0), 1),
        "target_ts": round(float(target_ts or 0), 3),
        "fire_ts": round(float(fire_ts or 0), 3),
        "one_way_ms": round(float(one_way_ms or 0), 1),
        "probe_rtt_med": round(float(probe_rtt_med or 0), 1),
        "probe_valid": int(probe_valid or 0),
        "probe_total": int(probe_total or 0),
        "spin_error_ms": round(float(spin_error_ms or 0), 1),
        "is_first_shot": bool(is_first_shot),
        "arrive_dev_ms": (None if arrive_dev_ms is None
                           else round(float(arrive_dev_ms), 1)),
        # ---- v6.4.1 补充字段（供剩余 11 项指标计算）----
        "probe_samples": str(probe_samples or ""),   # 逗号分隔的原始样本
        "window_seconds": int(window_seconds or 0),  # 任务窗口期秒数
        "priority": int(priority or 0),              # 任务优先级
        "target_time_str": str(target_time_str or ""),  # 目标时刻文本
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



# ============================================================
# v6.4.1：按「抢码场次」分组统计（替代自然小时）
# ============================================================

# 时段窗口定义（分钟偏移，正数=目标后，负数=目标前）
# 用户要求：整点场次统计 x点前后各20分钟；半整点场次前后各5分钟
SESSION_WINDOW_MIN = 20      # 整点场次：目标前20分 ~ 目标后20分
SESSION_WINDOW_HALF = 5      # 半整点场次（xx:30）：目标前5分 ~ 目标后5分


def _session_label(hour, minute):
    """把 (时,分) 转成【抢码场次】标签（v6.4.2）。

    固定 5 个场次，其余全部归「其他时段」：
      00点场    目标 00:00 -> 22:40 ~ 00:20  (前后各20分钟)
      00:30场   目标 00:30 -> 00:25 ~ 00:35  (前后各5分钟，用户单独要求)
      01点场    目标 01:00 -> 00:40 ~ 01:20
      02点场    目标 02:00 -> 01:40 ~ 02:20
      18点场    目标 18:00 -> 17:40 ~ 18:20
      其他时段  其余所有时间

    注意：00:30 场的窗口与 00点场可能重叠边界，按"先判半点、再判整点"的顺序，
    00:25~00:35 只会归入 00:30 场，不会误入 00点场。
    """
    # 场次定义：(目标小时, 目标分钟, 窗口半宽分钟, 标签)
    SESSIONS = [
        (0, 0, 20, "00点场"),
        (0, 30, 5, "00:30场"),
        (1, 0, 20, "01点场"),
        (2, 0, 20, "02点场"),
        (18, 0, 20, "18点场"),
    ]

    cur_min = hour * 60 + minute

    # 先判半点场（窗口窄，优先级高），再判整点场
    for order, (h, m, win, name) in enumerate(
            sorted(SESSIONS, key=lambda x: x[2])):
        target_min = h * 60 + m
        diff = cur_min - target_min
        while diff > 720:
            diff -= 1440
        while diff < -720:
            diff += 1440
        if -win <= diff <= win:
            return name

    return "其他时段"


def _record_session_ts(rec):
    """从一条记录推断它所属场次的目标时刻（epoch 秒）。

    优先级：
      1. target_ts 字段（v6.4.0+ 新记录有）
      2. target_time_str + ts 推算（按 ts 当天日期套用目标时分秒）
      3. 退化：直接用 ts
    返回 (epoch, 是否精确匹配)
    """
    import datetime as _dt

    tts = float(rec.get("target_ts") or 0)
    if tts > 0:
        return tts, True

    tstr = str(rec.get("target_time_str") or "").strip()
    ts_str = str(rec.get("ts") or "").strip()
    if tstr and ts_str:
        try:
            base = _dt.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            parts = tstr.replace(".", ":").split(":")
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
            ss = int(parts[2]) if len(parts) > 2 else 0
            target = base.replace(hour=hh, minute=mm, second=ss, microsecond=0)
            # 跨日修正：若目标时刻比记录时刻晚很多（>12h），说明是前一天
            if (target - base).total_seconds() > 12 * 3600:
                target -= _dt.timedelta(days=1)
            elif (base - target).total_seconds() > 12 * 3600:
                target += _dt.timedelta(days=1)
            return target.timestamp(), True
        except Exception:
            pass

    # 退化：用记录自身的 ts
    if ts_str:
        try:
            return _dt.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp(), False
        except Exception:
            pass
    return 0, False


def _group_by_session(records, is_ok, is_risk):
    """按场次分组统计风控情况（v6.4.1）。

    返回 list，每项：
      key          分组键（内部）
      label        显示标签（如 "00点场" / "00:30场" / "其他时段"）
      total        请求数
      success      成功数
      risk         风控数
      success_rate 成功率
      is_other     是否为"其他时段"
    """
    groups = {}

    for r in records:
        ts_epoch, exact = _record_session_ts(r)
        if not ts_epoch:
            label = "其他时段"
            key = "other"
        else:
            import datetime as _dt
            dt_obj = _dt.datetime.fromtimestamp(ts_epoch)
            label = _session_label(dt_obj.hour, dt_obj.minute)
            key = label if label != "其他时段" else "other"

        d = groups.setdefault(key, {
            "key": key, "label": label, "total": 0,
            "success": 0, "risk": 0, "is_other": (key == "other"),
        })
        d["total"] += 1
        if is_ok(r):
            d["success"] += 1
        if is_risk(r):
            d["risk"] += 1

    out = list(groups.values())
    for d in out:
        d["success_rate"] = (round(100.0 * d["success"] / d["total"], 1)
                             if d["total"] else 0)

    # 排序：4个场次按时间先后，其他放最后
    ORDER = {"00点场": 0, "00:30场": 1, "01点场": 2, "02点场": 3, "18点场": 4}

    def _sort_key(d):
        return (1, 0) if d["is_other"] else (0, ORDER.get(d["label"], 99))

    return sorted(out, key=_sort_key)


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

    # ---- 风控高发时段（v6.4.1 重写：按"抢码场次"分组，而非自然小时）----
    #
    # 原逻辑问题：简单按 ts[11:13] 取自然小时，
    # 但抢码是围绕"目标时刻"的一场战役，跨小时的记录会被拆成两组。
    #   例：23:59:00 预热 + 23:59:59 首发 + 00:00:05 重试
    #       会被拆成 "23点" 和 "00点" 两个时段，统计失去意义。
    #
    # 新逻辑：用场次目标时刻（target_time_str / target_ts）归类，
    # 按用户要求定义时段窗口：
    #   整点场次 0点：  23:40 ~ 00:20 都属于"0点场"
    #   半整点场次 0:30：00:25 ~ 00:35 单独归为"0:30场"
    #   其余时间：     归为"其他时段"
    #
    # 这样每个"场次"的预热/首发/重试全部归到同一组，风控统计才有意义。
    by_hour = _group_by_session(records, _is_ok, _is_risk)

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
            # v6.4.0: 透传程序运行指标字段（供评分与指标展示使用）
            "session_id": str(r.get("session_id", "")),
            "ntp_offset_ms": float(r.get("ntp_offset_ms", 0) or 0),
            "target_ts": float(r.get("target_ts", 0) or 0),
            "fire_ts": float(r.get("fire_ts", 0) or 0),
            "one_way_ms": float(r.get("one_way_ms", 0) or 0),
            "probe_rtt_med": float(r.get("probe_rtt_med", 0) or 0),
            "probe_valid": int(r.get("probe_valid", 0) or 0),
            "probe_total": int(r.get("probe_total", 0) or 0),
            "spin_error_ms": float(r.get("spin_error_ms", 0) or 0),
            "is_first_shot": bool(r.get("is_first_shot", False)),
            "arrive_dev_ms": r.get("arrive_dev_ms"),
            # v6.4.1: 其余指标所需字段
            "latency_ms": float(r.get("latency_ms", 0) or 0),
            "attempt": int(r.get("attempt", 1) or 1),
            "probe_samples": str(r.get("probe_samples", "")),
            "window_seconds": int(r.get("window_seconds", 0) or 0),
            "priority": int(r.get("priority", 0) or 0),
            "target_time_str": str(r.get("target_time_str", "")),
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


# ============================================================
# v6.4.0 新增：程序运行指标 + 综合抢码状态评分
# ============================================================

# 到达偏差分级（毫秒）：(上限, 分数, 等级名)
ARRIVE_GRADES = [
    (-20, 0,   "早到"),
    (0,   40,  "边缘早"),
    (20,  85,  "优秀"),
    (50,  100, "优秀"),
    (80,  90,  "良好"),
    (100, 80,  "良好"),
    (150, 60,  "偏晚"),
    (200, 45,  "偏晚"),
    (500, 20,  "太晚"),
    (999999, 0, "失效"),
]


def grade_arrive(dev_ms):
    """到达偏差分级。返回 (分数0-100, 等级名, 颜色key)。"""
    if dev_ms is None:
        return 0, "无数据", "muted"
    for upper, score, name in ARRIVE_GRADES:
        if dev_ms <= upper:
            if name == "优秀":
                return score, name, "ok"
            if name in ("良好", "边缘早"):
                return score, name, "mid"
            return score, name, "bad"
    return 0, "失效", "bad"


def grade_spin(err_ms):
    """自旋等待精度分级。"""
    a = abs(float(err_ms or 0))
    if a < 5:
        return 100, "优秀", "ok"
    if a < 10:
        return 85, "良好", "ok"
    if a < 20:
        return 60, "正常", "mid"
    if a < 50:
        return 30, "偏大", "bad"
    return 0, "异常", "bad"


def grade_probe(valid, total):
    """探针有效性分级。"""
    if not total:
        return 0, "无数据", "muted"
    ratio = valid / total
    if valid >= 4:
        return 100, f"{valid}/{total} 良好", "ok"
    if valid == 3:
        return 75, f"{valid}/{total} 偏低", "mid"
    if valid == 2:
        return 45, f"{valid}/{total} 偏低", "bad"
    return 0, f"{valid}/{total} 失效", "bad"


def grade_account(risk_cnt, abnormal_cnt):
    """账户健康度分级。"""
    if abnormal_cnt > 0:
        return 20, "有异常", "bad"
    if risk_cnt == 0:
        return 100, "健康", "ok"
    if risk_cnt <= 3:
        return 85, "轻度风控", "ok"
    if risk_cnt <= 6:
        return 60, "中度风控", "mid"
    if risk_cnt <= 15:
        return 35, "重度风控", "bad"
    return 10, "被盯上", "bad"


# ============================================================
# v6.4.1：完整 16 项指标计算（A时间/B网络/C效率/D有效性/E归因）
# ============================================================

def _median(vals):
    """安全中位数。"""
    xs = [float(v) for v in vals if v is not None]
    if not xs:
        return None
    xs.sort()
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _parse_probe_samples(s):
    """解析逗号分隔的探针样本字符串。"""
    out = []
    for part in str(s or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(float(part))
        except Exception:
            pass
    return out


# ============================================================
# v6.4.2：库存窗口分析（每个任务一个窗口）
# ============================================================

STOCK_OUT_CODE = "75255"   # [-75255] 库存已经使用完


def _session_target_of_burst(ts_first):
    """从一个"请求爆发"的首条记录时刻，推断该场次的目标时刻（epoch 秒）。

    原理：首条请求在目标时刻前后（提前量 10~2000ms）发出，
    所以首条记录的秒数基本就是目标秒。这里向上取整到整秒。
    """
    import datetime as _dt
    if not ts_first:
        return 0
    try:
        t = _dt.datetime.strptime(str(ts_first), "%Y-%m-%d %H:%M:%S")
        return t.timestamp()
    except Exception:
        return 0


def stock_windows(d=None):
    """按【任务】统计库存窗口（v6.4.2 第⑤页数据）。

    用户要求：「库存窗口我建议单拎出来，做成第五个页面，
             每个任务对应一个窗口（只要返回库存已使用完就计入）」

    定义：
      对每个任务，收集所有 code==75255（库存已用完）的记录，
      计算它们相对【本场目标时刻】的偏移秒数。
      窗口 = 从目标后第一次出现 75255，到最后一次出现 75255 的区间。

    返回 list，每项：
      task       任务名
      count      75255 次数
      sessions   涉及场次数
      first_off  最早偏移（秒，相对目标）
      last_off   最晚偏移（秒）
      window_s   窗口跨度（秒）
      samples    明细 [(场次标签, 偏移秒, 账户)]
      verdict    结论文本（如 "约 8 秒内告罄"）
    """
    if d is None:
        d = dashboard()
    recs = d.get("records", []) or []

    # 只保留库存耗尽记录
    stock_recs = [r for r in recs if str(r.get("code", "")).strip() == STOCK_OUT_CODE]
    if not stock_recs:
        return []

    # 按 (账号, 时间) 聚类成"爆发"，每个爆发对应一场抢码
    # 用 ts 排序后，间隔 > 120 秒视为新场次
    import datetime as _dt

    def _ts_epoch(r):
        try:
            return _dt.datetime.strptime(
                str(r.get("ts", "")), "%Y-%m-%d %H:%M:%S").timestamp()
        except Exception:
            return 0

    all_sorted = sorted(stock_recs, key=_ts_epoch)

    # 建立 时间 -> 该场目标时刻 的映射
    # 用同一账号的连续请求聚类：间隔>120s 开新爆发
    bursts = []
    cur = []
    last_t = 0
    for r in all_sorted:
        t = _ts_epoch(r)
        if not t:
            continue
        if cur and (t - last_t) > 120:
            bursts.append(cur)
            cur = []
        cur.append((r, t))
        last_t = t
    if cur:
        bursts.append(cur)

    # 每个爆发用首条记录推断目标时刻
    rec_target = {}
    for b in bursts:
        tgt = _session_target_of_burst(b[0][0].get("ts"))
        # 目标时刻取整到最近的整分钟或半点（抢码目标都是整点/半点）
        if tgt:
            import math as _m
            tgt = _m.floor(tgt / 30.0) * 30.0
        for r, t in b:
            rec_target[id(r)] = tgt

    # 按任务汇总
    by_task = {}
    for r in stock_recs:
        task = str(r.get("task_name", "") or "?")
        t = _ts_epoch(r)
        tgt = rec_target.get(id(r), 0)
        # 若记录自带 target_ts 则优先用
        _tts = float(r.get("target_ts") or 0)
        if _tts > 0:
            tgt = _tts
        off = (t - tgt) if tgt else None
        item = by_task.setdefault(task, {
            "task": task, "count": 0, "offsets": [], "samples": [],
            "accounts": set(),
        })
        item["count"] += 1
        item["accounts"].add(str(r.get("account", "") or "?"))
        if off is not None and -120 < off < 900:
            item["offsets"].append(off)
            import datetime as _dt2
            _lab = ""
            try:
                _lb = _dt2.datetime.fromtimestamp(tgt)
                _lab = _session_label(_lb.hour, _lb.minute)
            except Exception:
                pass
            item["samples"].append((_lab, round(off, 1),
                                    str(r.get("account", "") or "?")))

    out = []
    for task, it in by_task.items():
        offs = sorted(it["offsets"])
        sessions = len(set(s[0] for s in it["samples"] if s[0]))
        if offs:
            first_off = offs[0]
            last_off = offs[-1]
            win = round(last_off - first_off, 1)
            # 结论
            if win <= 0:
                verdict = "单点告罄（仅1次样本）"
            elif win <= 3:
                verdict = "极快告罄（%.0f秒内）" % win
            elif win <= 10:
                verdict = "快速告罄（%.0f秒内）" % win
            elif win <= 60:
                verdict = "约 %.0f 秒告罄" % win
            else:
                verdict = "库存可持续 %.0f 秒" % win
        else:
            first_off = last_off = None
            win = None
            verdict = "无法对齐目标时刻（缺数据）"

        out.append({
            "task": task,
            "count": it["count"],
            "sessions": sessions,
            "account_n": len(it["accounts"]),
            "first_off": first_off,
            "last_off": last_off,
            "window_s": win,
            "samples": sorted(it["samples"], key=lambda x: x[1]),
            "verdict": verdict,
        })

    # 按窗口跨度排序（最快告罄的排前面，最需要重视）
    out.sort(key=lambda x: (x["window_s"] is None, x["window_s"] or 0))
    return out


def metrics_all(d):
    """计算全部 16 项指标（v6.4.1 新增）。

    返回 list，每项：
      group    分组（A时间精度 / B网络质量 / C请求效率 / D有效性 / E归因）
      name     指标名
      value    当前值（展示文本）
      score    0-100 分（None = 未采集）
      grade    等级文本
      color    颜色 key（ok/mid/bad/muted）
      tip      说明/建议
      weight   若参与综合评分则给权重，否则 0（仅展示）
    """
    recs = d.get("records", []) or []
    ov = d.get("overview") or {}
    out = []

    def add(group, name, value, score, grade, color, tip, weight=0):
        out.append({"group": group, "name": name, "value": value,
                    "score": score, "grade": grade, "color": color,
                    "tip": tip, "weight": weight})

    # 首发记录（v6.4.2: 兼容旧数据 —— 无 is_first_shot 字段时用 attempt==1 判断）
    firsts = [r for r in recs
              if r.get("is_first_shot") or
              (not r.get("is_first_shot") and int(r.get("attempt") or 1) == 1
               and "is_first_shot" not in r)]
    # 全部 RTT
    rtts = [float(r.get("latency_ms") or 0) for r in recs if r.get("latency_ms")]

    # ============ A. 时间精度类（5 项）============
    # A1 精准首发到达偏差（参与评分 26）
    av = [r.get("arrive_dev_ms") for r in firsts
          if r.get("arrive_dev_ms") is not None]
    if av:
        m = _median(av)
        sc, nm, cl = grade_arrive(m)
        add("A.时间精度", "精准首发到达偏差", f"{m:+.0f}ms", sc, nm, cl,
            "理想 0~50ms，负数=早到会被拒", 26)
    else:
        add("A.时间精度", "精准首发到达偏差", "无数据", None, "未采集", "muted",
            "需抢码一次后才有数据", 26)

    # A2 自旋等待精度（参与评分 8）
    sp = [abs(float(r.get("spin_error_ms") or 0)) for r in firsts
          if r.get("spin_error_ms")]
    if sp:
        m = _median(sp)
        sc, nm, cl = grade_spin(m)
        add("A.时间精度", "自旋等待精度", f"{m:.1f}ms", sc, nm, cl,
            "计划发送与实际发送的时间差，<5ms 优秀", 8)
    else:
        add("A.时间精度", "自旋等待精度", "无数据", None, "未采集", "muted",
            "需抢码一次后才有数据", 8)

    # A3 时钟偏差（仅展示，不参与评分 —— 已自动补偿，不影响精度）
    ntp = [float(r.get("ntp_offset_ms") or 0) for r in recs
           if r.get("ntp_offset_ms")]
    if ntp:
        m = _median(ntp)
        a = abs(m)
        if a <= 50:
            cl, nm = "ok", "正常"
        elif a <= 150:
            cl, nm = "mid", "偏大"
        elif a <= 300:
            cl, nm = "bad", "严重"
        else:
            cl, nm = "bad", "需修复"
        add("A.时间精度", "时钟偏差(NTP)", f"{m:+.0f}ms", None, nm, cl,
            "本地与服务器的时间差，程序会自动补偿")
    else:
        add("A.时间精度", "时钟偏差(NTP)", "无数据", None, "未采集", "muted",
            "需抢码一次后才有数据")

    # A4 提前量设计值 vs 实际使用
    advs = [float(r.get("advance_ms") or 0) for r in recs if r.get("advance_ms")]
    if advs and ntp:
        m_adv = _median(advs)
        m_ntp = _median(ntp)
        # 设计值 = ntp + 半RTT - 60
        ow = [float(r.get("one_way_ms") or 0) for r in recs if r.get("one_way_ms")]
        m_ow = _median(ow) if ow else 0
        expect = m_ntp + m_ow - 60
        diff = m_adv - expect
        cl = "ok" if abs(diff) <= 10 else ("mid" if abs(diff) <= 30 else "bad")
        nm = "一致" if abs(diff) <= 10 else ("略偏" if abs(diff) <= 30 else "偏差大")
        add("A.时间精度", "提前量设计vs实际", f"差 {diff:+.0f}ms", None, nm, cl,
            f"设计 {expect:.0f}ms / 实际 {m_adv:.0f}ms，应接近0")
    else:
        add("A.时间精度", "提前量设计vs实际", "无数据", None, "未采集", "muted",
            "需抢码一次后才有数据")

    # A5 NTP 补偿净效果（提前量中 offset 占比）
    if advs and ntp:
        m_adv = _median(advs)
        m_ntp = _median(ntp)
        if m_adv > 0:
            ratio = abs(m_ntp) / m_adv * 100
            if ratio <= 30:
                cl, nm = "ok", "依赖低"
            elif ratio <= 60:
                cl, nm = "mid", "依赖中"
            else:
                cl, nm = "bad", "依赖高"
            add("A.时间精度", "NTP补偿净效果", f"占比 {ratio:.0f}%", None, nm, cl,
                "时钟偏差占提前量比例，越低说明时钟越准")
        else:
            add("A.时间精度", "NTP补偿净效果", "无数据", None, "未采集", "muted",
                "提前量为0")
    else:
        add("A.时间精度", "NTP补偿净效果", "无数据", None, "未采集", "muted",
            "需抢码一次后才有数据")

    # ============ B. 网络质量类（4 项）============
    # B1 首发 RTT
    # 首发RTT：firsts 已在上面兼容旧数据，latency_ms 旧数据也有
    frt = [float(r.get("latency_ms") or 0) for r in firsts if r.get("latency_ms")]
    if frt:
        m = _median(frt)
        if m <= 150:
            sc, cl, nm = 100, "ok", "优秀"
        elif m <= 300:
            sc, cl, nm = 70, "mid", "良好"
        elif m <= 500:
            sc, cl, nm = 40, "bad", "偏慢"
        else:
            sc, cl, nm = 10, "bad", "很慢"
        add("B.网络质量", "首发RTT", f"{m:.0f}ms", sc, nm, cl,
            "首发请求往返耗时，<150ms 优秀")
    else:
        add("B.网络质量", "首发RTT", "无数据", None, "未采集", "muted", "需抢码一次")

    # B2 预热成效（首发RTT / 探针RTT，应<=1.3 说明连接复用了）
    prm = [float(r.get("probe_rtt_med") or 0) for r in firsts
           if r.get("probe_rtt_med")]
    if frt and prm:
        f = _median(frt)
        p = _median(prm)
        if p > 0:
            ratio = f / p
            if ratio <= 1.3:
                sc, cl, nm = 100, "ok", "复用成功"
            elif ratio <= 2.0:
                sc, cl, nm = 60, "mid", "部分复用"
            else:
                sc, cl, nm = 20, "bad", "预热失效"
            add("B.网络质量", "预热成效", f"{ratio:.2f}x", sc, nm, cl,
                f"首发{f:.0f}ms / 探针{p:.0f}ms，≤1.3 说明连接已复用")
        else:
            add("B.网络质量", "预热成效", "无数据", None, "未采集", "muted",
                "探针RTT为0")
    else:
        add("B.网络质量", "预热成效", "无数据", None, "未采集", "muted", "需抢码一次")

    # B3 RTT 抖动（探针样本 P75-P25）
    jit = []
    for r in recs:
        s = _parse_probe_samples(r.get("probe_samples"))
        if len(s) >= 3:
            s.sort()
            jit.append(s[int(len(s) * 0.75)] - s[int(len(s) * 0.25)])
    if jit:
        m = _median(jit)
        if m < 50:
            sc, cl, nm = 100, "ok", "稳定"
        elif m < 150:
            sc, cl, nm = 70, "mid", "一般"
        else:
            sc, cl, nm = 30, "bad", "波动大"
        add("B.网络质量", "RTT抖动", f"{m:.0f}ms", sc, nm, cl,
            "P75-P25，波动越小说明网络越稳")
    else:
        add("B.网络质量", "RTT抖动", "无数据", None, "未采集", "muted",
            "需探针样本≥3个")

    # B4 探针有效性（参与评分 12）
    pv = [r for r in recs if r.get("probe_total")]
    if pv:
        last = pv[-1]
        sc, nm, cl = grade_probe(int(last.get("probe_valid", 0) or 0),
                                 int(last.get("probe_total", 0) or 0))
        add("B.网络质量", "探针有效性",
            f"{last.get('probe_valid', 0)}/{last.get('probe_total', 0)}",
            sc, nm, cl, "有效样本越多，提前量算得越准", 12)
    else:
        add("B.网络质量", "探针有效性", "无数据", None, "未采集", "muted", "需抢码一次", 12)

    # ============ C. 请求效率类（5 项）============
    # C1 首发命中率（参与评分 8）
    sessions = {}
    for r in recs:
        sid = r.get("session_id", "")
        if not sid:
            continue
        sessions.setdefault(sid, {"first_ok": False, "any_ok": False, "cnt": 0})
        s = sessions[sid]
        s["cnt"] += 1
        if r.get("result") in ("success", "already"):
            s["any_ok"] = True
            if r.get("is_first_shot"):
                s["first_ok"] = True
    if sessions:
        n = len(sessions)
        fn = sum(1 for s in sessions.values() if s["first_ok"])
        an = sum(1 for s in sessions.values() if s["any_ok"])
        rate = fn / n * 100
        sc = min(100, rate / 30 * 100)
        nm = ("优秀" if rate >= 30 else "良好" if rate >= 10
              else "偏低" if rate > 0 else "未命中")
        add("C.请求效率", "首发命中率", f"{rate:.0f}% ({fn}/{n}场)", sc, nm,
            "ok" if rate >= 10 else "bad",
            f"任意命中 {an}/{n} 场。注意：抢不到常因库存/竞争，非程序问题", 8)
    else:
        add("C.请求效率", "首发命中率", "无数据", None, "未采集", "muted",
            "需抢码一次", 8)

    # C2 重试命中分布（成功发生在第几次）
    hit_attempts = [int(r.get("attempt") or 1) for r in recs
                    if r.get("result") in ("success", "already")]
    if hit_attempts:
        import collections as _col
        buckets = _col.Counter()
        for a in hit_attempts:
            if a == 1:
                buckets["第1次"] += 1
            elif a <= 3:
                buckets["第2-3次"] += 1
            elif a <= 10:
                buckets["第4-10次"] += 1
            else:
                buckets["第10次后"] += 1
        dist = " / ".join(f"{k}:{v}" for k, v in buckets.items())
        first_rate = buckets["第1次"] / len(hit_attempts) * 100
        sc = round(first_rate)
        nm = ("首发即中" if first_rate >= 60 else
              "多需重试" if first_rate >= 20 else "依赖重试")
        cl = "ok" if first_rate >= 60 else ("mid" if first_rate >= 20 else "bad")
        add("C.请求效率", "重试命中分布", dist, sc, nm, cl,
            f"成功{len(hit_attempts)}次，其中{first_rate:.0f}%是第1次就中")
    else:
        add("C.请求效率", "重试命中分布", "无成功记录", None, "未采集", "muted",
            "还没有成功过")

    # C3 风控恢复时长（从风控到下次成功的间隔）
    import datetime as _dt
    recoveries = []
    prev_risk_ts = None
    for r in recs:
        c = str(r.get("code", ""))
        ts = str(r.get("ts", ""))
        try:
            t = _dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if c in ("-702", "-509", "-705"):
            prev_risk_ts = t
        elif r.get("result") in ("success", "already") and prev_risk_ts is not None:
            recoveries.append((t - prev_risk_ts).total_seconds())
            prev_risk_ts = None
    # v6.4.2: 过滤异常值（负值或过大的间隔是时间戳解析错误导致）
    recoveries = [r for r in recoveries if 0 < r < 3600]
    if recoveries:
        m = _median(recoveries)
        if m <= 3:
            sc, cl, nm = 100, "ok", "恢复快"
        elif m <= 10:
            sc, cl, nm = 70, "mid", "正常"
        else:
            sc, cl, nm = 30, "bad", "恢复慢"
        add("C.请求效率", "风控恢复时长", f"{m:.1f}s", sc, nm, cl,
            "风控后被拒到下次成功的间隔，越短说明退避有效")
    else:
        add("C.请求效率", "风控恢复时长", "无数据", None, "未采集", "muted",
            "需要风控后成功过的场景")

    # C4 间隔合规率（参与评分 12）
    gaps = []
    for i in range(1, len(recs)):
        try:
            a = _dt.datetime.strptime(str(recs[i-1].get("ts", "")), "%Y-%m-%d %H:%M:%S")
            b = _dt.datetime.strptime(str(recs[i].get("ts", "")), "%Y-%m-%d %H:%M:%S")
            dd = abs((b - a).total_seconds() * 1000)
            if 0 < dd < 60000:
                gaps.append(dd)
        except Exception:
            pass
    if gaps:
        ok_n = sum(1 for g in gaps if g >= 800)
        rate = ok_n / len(gaps) * 100
        sc = round(rate)
        nm = ("合规" if rate >= 99 else "基本合规" if rate >= 90 else "有风险")
        cl = "ok" if rate >= 99 else ("mid" if rate >= 90 else "bad")
        add("C.请求效率", "间隔合规率", f"{rate:.0f}%", sc, nm, cl,
            "请求间隔 ≥800ms 才安全（<800 必被风控）", 12)
    else:
        add("C.请求效率", "间隔合规率", "数据不足", None, "未采集", "muted",
            "需至少2条记录", 12)

    # C5 无效请求率（参与评分 12）
    if recs:
        nq = sum(1 for r in recs if str(r.get("code", "")) == "202032")
        wr = nq / len(recs) * 100
        if wr <= 5:
            sc, cl, nm = 100, "ok", "很好"
        elif wr <= 15:
            sc, cl, nm = 75, "mid", "可接受"
        elif wr <= 35:
            sc, cl, nm = 45, "bad", "浪费多"
        else:
            sc, cl, nm = 10, "bad", "严重浪费"
        add("C.请求效率", "无效请求率", f"{wr:.0f}% ({nq}/{len(recs)})",
            sc, nm, cl, "202032=任务未完成就硬抢，纯粹浪费请求", 12)
    else:
        add("C.请求效率", "无效请求率", "无数据", None, "未采集", "muted", "无数据", 12)

    # ============ D. 有效性类（2 项）============
    # D1 窗口期利用率（有效尝试 / 理论最大尝试）
    win = [int(r.get("window_seconds") or 0) for r in recs
           if r.get("window_seconds")]
    if win and sessions:
        w = _median(win)
        # 理论最大 = 窗口秒 / 基础间隔(0.9秒)
        theory = max(1, int(w / 0.9))
        # 说明: window_seconds 是单任务窗口，theory 是单场单任务理论最大次数
        # 实际每场平均尝试次数
        sess_cnt = {}
        for r in recs:
            sid = r.get("session_id", "")
            if sid:
                sess_cnt[sid] = sess_cnt.get(sid, 0) + 1
        if sess_cnt:
            # 每场平均实际尝试次数
            actual = sum(sess_cnt.values()) / len(sess_cnt)
            # v6.4.2: 利用率 = 实际场次尝试次数 / 单场理论最大次数
            util = min(100.0, actual / theory * 100)
            sc = min(100, round(util))
            nm = ("充分利用" if util >= 70 else
                  "一般" if util >= 40 else "利用不足")
            cl = "ok" if util >= 70 else ("mid" if util >= 40 else "bad")
            add("D.有效性", "窗口期利用率", f"{util:.0f}% ({actual:.0f}/{theory}次)",
                sc, nm, cl, f"窗口{w:.0f}秒理论上限{theory}次，实际平均{actual:.0f}次")
        else:
            add("D.有效性", "窗口期利用率", "无数据", None, "未采集", "muted",
                "需场次数据")
    else:
        add("D.有效性", "窗口期利用率", "无数据", None, "未采集", "muted",
            "需记录窗口期与场次")

    # D2 库存窗口（目标后多少秒内还能抢到）
    stock_win = []
    for r in recs:
        if r.get("result") not in ("success", "already"):
            continue
        tts = float(r.get("target_ts") or 0)
        fts = float(r.get("fire_ts") or 0)
        if tts and fts:
            # 用 ts 与 target_ts 估算：这里用 fire_ts 相对 target
            # 但重试的 fire_ts 是首发时刻，改用 ts 无法精确
            # 简化：用 latency 与 attempt 推算（不可靠），跳过
            stock_win.append(fts - tts)
    # 用更可靠的方式：从日志的 ts 与 target_time_str 比较
    stock_ok = []
    for r in recs:
        if r.get("result") not in ("success", "already"):
            continue
        tts = float(r.get("target_ts") or 0)
        tstr = str(r.get("ts", ""))
        if not tts or not tstr:
            continue
        try:
            t = _dt.datetime.strptime(tstr, "%Y-%m-%d %H:%M:%S").timestamp()
            dev = t - tts
            if 0 <= dev < 600:   # v6.4.2: 只保留目标后的正偏差
                stock_ok.append(dev)
        except Exception:
            pass
    if stock_ok:
        m = _median(stock_ok)
        if m <= 5:
            sc, cl, nm = 90, "ok", f"{m:.0f}s内"
        elif m <= 30:
            sc, cl, nm = 70, "mid", f"{m:.0f}s内"
        else:
            sc, cl, nm = 40, "bad", f"{m:.0f}s内"
        add("D.有效性", "库存窗口", f"成功于目标后{m:.0f}s", sc, nm, cl,
            "成功时刻距目标多久，用来判断窗口期该设多长")
    else:
        add("D.有效性", "库存窗口", "无成功记录", None, "未采集", "muted",
            "还没有成功过")

    # ============ E. 归因类（2 项）============
    # E1 错误码归因
    if recs:
        import collections as _col2
        cc = _col2.Counter()
        for r in recs:
            c = str(r.get("code", "")).strip() or "成功"
            cc[c] += 1
        top = cc.most_common(3)
        desc = " / ".join(f"{c}×{n}" for c, n in top)
        worst = top[0][1] / len(recs) * 100
        sc = round(100 - worst)
        LABEL = {"202032": "任务未完成", "-705": "风控", "-702": "风控",
                 "-509": "风控", "75255": "库存空", "202129": "已结束",
                 "202118": "其他", "202101": "账户异常", "成功": "成功"}
        main_c = top[0][0]
        nm = LABEL.get(main_c, main_c)
        cl = "ok" if worst < 40 else ("mid" if worst < 70 else "bad")
        add("E.归因", "错误码归因", desc, sc, nm, cl,
            f"最大占比 {worst:.0f}% - {LABEL.get(main_c, main_c)}",
            12)   # v6.4.2: 风控严重度合并到此项，权重 12 使总和=100
    else:
        add("E.归因", "错误码归因", "无数据", None, "未采集", "muted", "无数据")

    # E2 账户健康度（参与评分 10）
    ar = {}
    aa = {}
    for r in recs:
        an = r.get("account", "") or "?"
        c = str(r.get("code", ""))
        if c in ("-702", "-509", "-705"):
            ar[an] = ar.get(an, 0) + 1
        if c in ("202101", "-101"):
            aa[an] = aa.get(an, 0) + 1
    if recs:
        wr = max(ar.values()) if ar else 0
        wa = max(aa.values()) if aa else 0
        sc, nm, cl = grade_account(wr, wa)
        add("E.归因", "账户健康度", f"最差风控{wr}次", sc, nm, cl,
            "按最差账户评估，有异常需更换账户", 10)
    else:
        add("E.归因", "账户健康度", "无数据", None, "未采集", "muted", "无数据", 10)

    return out


def score_snapshot(d):
    """根据 metrics_all 计算【综合抢码状态分】（v6.4.2 重写）。

    与 metrics_all 共用同一份指标数据，保证指标页和评分完全一致。

    权重按【可控性】分层（总和 100）：
      程序正确性组（82分）—— 完全由程序/配置决定
        精准首发到达偏差  26   自旋等待精度      8
        探针有效性        12   间隔合规率       12
        无效请求率        12   错误码归因       12
      环境账户组（10分）—— 账户状态
        账户健康度        10
      结果参考组（8分）—— 随机性最大，仅参考
        首发命中率         8

    返回 dict：
      total_score      总分（全部已采集项加权）
      program_score    程序健康分（不含命中率，这才是程序水平）
      result_score     结果参考分（命中率，随机）
      items            参与评分的分项
      all_metrics      全部18项指标
      suggestions      改进建议
    """
    metrics = metrics_all(d)

    scored = [m for m in metrics if m["weight"] > 0]
    got = [m for m in scored if m["score"] is not None]

    PROGRAM_GROUP = {"精准首发到达偏差", "自旋等待精度", "探针有效性",
                     "间隔合规率", "无效请求率", "错误码归因", "账户健康度"}
    RESULT_GROUP = {"首发命中率"}

    def _weighted(subset):
        if not subset:
            return None
        w = sum(m["weight"] for m in subset)
        if not w:
            return None
        return round(sum(m["score"] * m["weight"] for m in subset) / w)

    prog_items = [m for m in got if m["name"] in PROGRAM_GROUP]
    res_items = [m for m in got if m["name"] in RESULT_GROUP]

    if got:
        w_sum = sum(m["weight"] for m in got)
        total_score = round(sum(m["score"] * m["weight"] for m in got) / w_sum)
    else:
        total_score = 0

    program_score = _weighted(prog_items)
    result_score = _weighted(res_items)

    def _level(sc):
        if sc is None:
            return "未采集", "muted"
        if sc >= 85:
            return "优秀", "ok"
        if sc >= 70:
            return "良好", "mid"
        if sc >= 50:
            return "一般", "mid"
        if sc >= 30:
            return "偏低", "bad"
        return "很差", "bad"

    level, lcolor = _level(total_score)
    p_level, p_color = _level(program_score)

    suggestions = []
    HINTS = {
        "精准首发到达偏差": "调整晚到补偿，让到达更贴近 0~50ms",
        "自旋等待精度": "自旋误差大，关闭后台程序或提高进程优先级",
        "探针有效性": "探针常被风控，减少探针次数或换时间段",
        "间隔合规率": "请求间隔过密，提高基础间隔到 800ms 以上",
        "无效请求率": "大量任务未完成就硬抢，先完成任务再抢",
        "错误码归因": "主要错误是风控，降低频率或更换账户",
        "账户健康度": "有账户被风控/异常，检查并更换账户",
        "首发命中率": "抢不到常因库存/竞争，可尝试多账户并行",
    }
    for m in sorted(got, key=lambda x: x["score"]):
        if m["score"] < 60 and len(suggestions) < 3:
            hint = HINTS.get(m["name"])
            if hint:
                suggestions.append(hint)

    return {
        "total_score": total_score,
        "level": level,
        "level_color": lcolor,
        "program_score": program_score,
        "program_level": p_level,
        "program_color": p_color,
        "program_collected": len(prog_items),
        "program_total": len([m for m in scored if m["name"] in PROGRAM_GROUP]),
        "result_score": result_score,
        "result_collected": len(res_items),
        "result_total": len([m for m in scored if m["name"] in RESULT_GROUP]),
        "items": scored,
        "all_metrics": metrics,
        "suggestions": suggestions,
        "collected": len(got),
        "total_items": len(scored),
    }

def clear_results():
    """清空结果文件（测试/重置用）。"""
    try:
        with _LOCK:
            if RESULTS_FILE.exists():
                RESULTS_FILE.unlink()
        return True
    except Exception:
        return False
