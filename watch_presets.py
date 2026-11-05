# -*- coding: utf-8 -*-
"""看播快捷方案（v6.7.22 新增）。

用途：把「账户组合 + 直播间列表 + 每日时长 + 心跳间隔」保存为命名方案，
      看播页和日程任务都可直接选用，不用每次手动勾选。

存储：data/watch_presets.json
      {
        "presets": [
          {"name": "方案名", "accounts": [...], "rooms": [...],
           "duration_minutes": 15, "heartbeat_interval": 60,
           "note": "", "created_at": "2026-11-05 12:00:00"}
        ]
      }
"""

import time

from config import WATCH_PRESETS_FILE
from storage import atomic_write_json, safe_load_json


def load_presets():
    """读取所有看播方案。返回列表（字段已做容错）。"""
    data = safe_load_json(WATCH_PRESETS_FILE, {"presets": []})
    if not isinstance(data, dict):
        return []
    raw = data.get("presets")
    if not isinstance(raw, list):
        return []
    out = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name,
            "accounts": list(it.get("accounts") or []),
            "rooms": [str(r) for r in (it.get("rooms") or [])],
            "duration_minutes": int(it.get("duration_minutes") or 10),
            "heartbeat_interval": int(it.get("heartbeat_interval") or 60),
            "note": str(it.get("note") or ""),
            "created_at": str(it.get("created_at") or ""),
        })
    return out


def save_presets(presets):
    """保存方案列表。返回是否成功。"""
    try:
        atomic_write_json(WATCH_PRESETS_FILE, {"presets": list(presets or [])})
        return True
    except Exception:
        return False


def make_preset(name, accounts, rooms, duration_minutes=10,
                heartbeat_interval=60, note=""):
    """构造一个方案字典。"""
    return {
        "name": str(name or "").strip(),
        "accounts": list(accounts or []),
        "rooms": [str(r) for r in (rooms or [])],
        "duration_minutes": int(duration_minutes or 10),
        "heartbeat_interval": int(heartbeat_interval or 60),
        "note": str(note or ""),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def upsert_preset(presets, preset):
    """按名称新增或覆盖方案。返回 (新列表, 是否替换)。"""
    name = str(preset.get("name") or "").strip()
    out = list(presets or [])
    for i, p in enumerate(out):
        if str(p.get("name") or "").strip() == name:
            out[i] = preset
            return out, True
    out.append(preset)
    return out, False


def delete_preset(presets, name):
    """按名称删除方案。返回新列表。"""
    target = str(name or "").strip()
    return [p for p in (presets or [])
            if str(p.get("name") or "").strip() != target]


def get_preset(presets, name):
    """按名称取方案，找不到返回 None。"""
    target = str(name or "").strip()
    for p in (presets or []):
        if str(p.get("name") or "").strip() == target:
            return p
    return None


def summarize(preset):
    """一行摘要，用于下拉框显示。"""
    if not preset:
        return ""
    return "%s（%d账户/%d房间/%s分钟）" % (
        preset.get("name", ""),
        len(preset.get("accounts") or []),
        len(preset.get("rooms") or []),
        preset.get("duration_minutes", 0),
    )
