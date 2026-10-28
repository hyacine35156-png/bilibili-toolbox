# -*- coding: utf-8 -*-
"""日程任务参数模板（v6.6.1 B+C 融合方案）。

解决核心痛点：原来日程任务只有 id/name/type/time，没有任何执行参数，
执行时必须去读其他页面的 UI 控件 -> 用户被迫切屏配置，非常麻烦。

本模块提供：
  1. 参数模板库（schedule_templates.json）—— 配一次，多处复用
  2. 任务参数快照（存在 schedule_config.json 的 params 字段）
  3. 从各页面读取当前参数（兼容旧任务 / 「带入当前页面」按钮）
  4. 各类型参数的默认值与校验
"""

import json
from config import BASE_DIR
from storage import atomic_write_json, safe_load_json

TEMPLATES_FILE = BASE_DIR / "schedule_templates.json"

# 各任务类型的参数定义（用于 UI 动态渲染 + 校验）
TASK_PARAM_SPEC = {
    "watch": {
        "label": "看播参数",
        "icon": "📺",
        "fields": [
            {"key": "accounts", "label": "观看账户", "type": "accounts", "default": []},
            {"key": "rooms", "label": "直播间", "type": "rooms", "default": []},
            {"key": "duration_minutes", "label": "目标时长(分钟)", "type": "int",
             "default": 3, "min": 1, "max": 1440},
            {"key": "heartbeat_interval", "label": "心跳间隔(秒)", "type": "int",
             "default": 60, "min": 10, "max": 600},
        ],
    },
    "danmaku": {
        "label": "弹幕参数",
        "icon": "💬",
        "fields": [
            {"key": "accounts", "label": "发送账户", "type": "accounts", "default": []},
            {"key": "room", "label": "直播间", "type": "room", "default": ""},
            {"key": "account_mode", "label": "发送模式", "type": "choice",
             "choices": [("single", "单账户"), ("multi", "多账户"), ("rotate", "轮流")],
             "default": "multi"},
            {"key": "max_send_count", "label": "最大条数(0=不限)", "type": "int",
             "default": 50, "min": 0, "max": 9999},
        ],
    },
    "rush": {
        "label": "抢码参数（只需选启动范围）",
        "icon": "⚡",
        "fields": [
            {"key": "rush_mode", "label": "抢码模式", "type": "choice",
             "choices": [("old", "旧模式"), ("new", "新模式")], "default": "new"},
            {"key": "start_scope", "label": "启动范围", "type": "choice",
             "choices": [("all", "启动全部"), ("select", "仅选中")], "default": "all"},
            {"key": "selected_groups", "label": "选中的任务组", "type": "groups",
             "default": []},
        ],
    },
    "shutdown": {
        "label": "关机参数",
        "icon": "⏻",
        "fields": [
            {"key": "delay_seconds", "label": "延迟关机(秒)", "type": "int",
             "default": 60, "min": 0, "max": 3600},
            {"key": "skip_confirm", "label": "跳过确认弹窗", "type": "bool",
             "default": False},
        ],
    },
}


def task_param_spec(task_type):
    """取某类型的参数定义，未知类型返回 None。"""
    return TASK_PARAM_SPEC.get(task_type)


def default_params(task_type):
    """返回某类型的默认参数 dict。"""
    spec = TASK_PARAM_SPEC.get(task_type)
    if not spec:
        return {}
    out = {}
    for f in spec.get("fields", []):
        out[f["key"]] = f.get("default")
    return out


def load_templates():
    """加载模板库，返回 dict: {name: {type, params, created_at}}"""
    data = safe_load_json(TEMPLATES_FILE, {})
    if not isinstance(data, dict):
        return {}
    return data


def save_templates(tpls):
    """保存模板库。"""
    try:
        atomic_write_json(TEMPLATES_FILE, tpls)
        return True
    except Exception:
        return False


def upsert_template(name, task_type, params):
    """新建或更新模板。"""
    import time
    tpls = load_templates()
    tpls[name] = {
        "type": task_type,
        "params": dict(params or {}),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return save_templates(tpls)


def delete_template(name):
    """删除模板。"""
    tpls = load_templates()
    if name in tpls:
        del tpls[name]
        return save_templates(tpls)
    return False


def templates_of_type(task_type):
    """返回指定类型的模板名列表。"""
    return [n for n, t in load_templates().items()
            if t.get("type") == task_type]


# ---------------- 从其他页面读取当前参数（兼容旧任务）----------------

def collect_watch_params(app):
    """从看播页读取当前参数（旧任务/带入当前页面用）。"""
    try:
        wp = getattr(app, "watch_page", None)
        if wp is None:
            app._ensure_page_built("watch")
            wp = getattr(app, "watch_page", None)
        if wp is None:
            return default_params("watch")
        accounts = [n for n, v in getattr(wp, "account_vars", {}).items()
                    if v.get()]
        rooms = []
        try:
            rooms = wp._get_watch_room_ids()
        except Exception:
            pass
        duration = 3
        try:
            duration = int(wp.duration_var.get())
        except Exception:
            pass
        hb = 60
        try:
            hb = int(wp.interval_var.get())
        except Exception:
            pass
        return {
            "accounts": accounts,
            "rooms": [str(r) for r in rooms],
            "duration_minutes": duration,
            "heartbeat_interval": hb,
        }
    except Exception:
        return default_params("watch")


def collect_danmaku_params(app):
    """从弹幕页读取当前参数。"""
    try:
        accounts = []
        try:
            accounts = [a.get("name", "") for a in
                        app._get_danmaku_selected_accounts()]
        except Exception:
            pass
        room = ""
        try:
            room = str(app._get_danmaku_room_id() or "")
        except Exception:
            pass
        mode = "multi"
        try:
            mode = app.account_mode_var.get()
        except Exception:
            pass
        cnt = 50
        try:
            cnt = int(app.max_send_entry.get().strip())
        except Exception:
            pass
        return {
            "accounts": accounts,
            "room": room,
            "account_mode": mode,
            "max_send_count": cnt,
        }
    except Exception:
        return default_params("danmaku")


def collect_rush_params(app):
    """抢码只需选择启动范围。"""
    mode = "new"
    try:
        mode = app.rush_page.current_rush_mode or "new"
    except Exception:
        pass
    return {
        "rush_mode": mode,
        "start_scope": "all",
        "selected_groups": [],
    }


def collect_shutdown_params(app):
    """从关机页读取延迟时间。"""
    delay = 60
    try:
        delay = int(app.shutdown_page.shutdown_delay.get().strip())
    except Exception:
        pass
    return {"delay_seconds": delay, "skip_confirm": False}


COLLECTORS = {
    "watch": collect_watch_params,
    "danmaku": collect_danmaku_params,
    "rush": collect_rush_params,
    "shutdown": collect_shutdown_params,
}


def collect_current_params(app, task_type):
    """收集指定类型在当前页面的参数。"""
    fn = COLLECTORS.get(task_type)
    if fn is None:
        return default_params(task_type)
    try:
        return fn(app)
    except Exception:
        return default_params(task_type)


def validate_params(task_type, params):
    """校验参数，返回 (是否通过, 错误信息)。"""
    spec = TASK_PARAM_SPEC.get(task_type)
    if not spec:
        return True, ""
    params = params or {}
    for f in spec.get("fields", []):
        key = f["key"]
        typ = f["type"]
        val = params.get(key)
        # 必填项校验
        if typ == "accounts":
            if not val:
                return False, "请至少选择一个账户"
        elif typ == "rooms":
            if not val:
                return False, "请至少选择一个直播间"
        elif typ == "room":
            if not val:
                return False, "请选择一个直播间"
        elif typ == "int":
            try:
                iv = int(val)
            except Exception:
                return False, "「%s」必须是数字" % f.get("label", key)
            lo = f.get("min")
            hi = f.get("max")
            if lo is not None and iv < lo:
                return False, "「%s」不能小于 %d" % (f.get("label", key), lo)
            if hi is not None and iv > hi:
                return False, "「%s」不能大于 %d" % (f.get("label", key), hi)
    return True, ""


def describe_params(task_type, params):
    """生成参数摘要（给列表行显示用）。"""
    params = params or {}
    if task_type == "watch":
        accs = params.get("accounts") or []
        rooms = params.get("rooms") or []
        return "%d账户/%d房间/%d分钟" % (
            len(accs), len(rooms), int(params.get("duration_minutes", 0) or 0))
    if task_type == "danmaku":
        accs = params.get("accounts") or []
        return "%d账户/%d条" % (
            len(accs), int(params.get("max_send_count", 0) or 0))
    if task_type == "rush":
        scope = params.get("start_scope", "all")
        n = len(params.get("selected_groups") or [])
        return "全部启动" if scope == "all" else "选中% d组" % n
    if task_type == "shutdown":
        return "延迟% d秒" % int(params.get("delay_seconds", 0) or 0)
    return ""