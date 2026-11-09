# -*- coding: utf-8 -*-
"""看播快捷方案（v6.7.32 扩展为全参数方案）。

用途：把看播页的**全部**设置保存为命名方案，一键还原，不用逐项重选。

保存的参数（共 11 项）：
  1. accounts            账户勾选列表
  2. rooms               直播间房间号列表
  3. duration_minutes    每日时长（分钟）
  4. heartbeat_interval  心跳间隔（秒）
  5. gift_account        送礼账户
  6. gift_room           送礼直播间
  7. gift_num            送礼物数量（1 或 10）
  8. gift_interval       送礼间隔（秒）
  9. gift_count          送礼次数
  10. note               备注
  11. created_at         创建时间

存储：data/watch_presets.json
      {"presets": [{"name": "...", ...}]}

兼容性：旧方案（v6.7.22 只有前 4 项）读取时自动补默认值，不会丢失。
"""

import time

from config import WATCH_PRESETS_FILE
from storage import atomic_write_json, safe_load_json


# 方案字段定义：(字段名, 默认值, 类型)
PRESET_FIELDS = [
    ("accounts", [], list),
    ("rooms", [], list),
    ("duration_minutes", 10, int),
    ("heartbeat_interval", 60, int),
    ("gift_account", "", str),
    ("gift_room", "", str),
    ("gift_num", 1, int),
    ("gift_interval", 10, int),
    ("gift_count", 0, int),
    ("note", "", str),
    ("created_at", "", str),
]


def _coerce(value, default, typ):
    """把 value 转成 typ；失败返回 default。

    v6.7.32 修复：value 为 None 时原实现会得到字符串 'None'，
    现统一返回 default。
    """
    if value is None:
        return default if typ is not list else list(default)
    try:
        if typ is list:
            if isinstance(value, (list, tuple)):
                return list(value)
            return list(default)
        if typ is int:
            return int(value)
        s = str(value).strip()
        return s if s else default
    except Exception:
        return default


def load_presets():
    """读取所有看播方案。旧方案自动补齐缺失字段。"""
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
        p = {"name": name}
        for fname, fdefault, ftype in PRESET_FIELDS:
            p[fname] = _coerce(it.get(fname), fdefault, ftype)
        # rooms 统一转字符串
        p["rooms"] = [str(r) for r in p["rooms"]]
        out.append(p)
    return out


def save_presets(presets):
    """保存方案列表。返回是否成功。"""
    try:
        atomic_write_json(WATCH_PRESETS_FILE, {"presets": list(presets or [])})
        return True
    except Exception:
        return False


def make_preset(name, accounts, rooms, duration_minutes=10,
                heartbeat_interval=60, note="",
                gift_account="", gift_room="", gift_num=1,
                gift_interval=10, gift_count=0):
    """构造一个全参数方案字典。"""
    return {
        "name": str(name or "").strip(),
        "accounts": list(accounts or []),
        "rooms": [str(r) for r in (rooms or [])],
        "duration_minutes": int(duration_minutes or 10),
        "heartbeat_interval": int(heartbeat_interval or 60),
        "gift_account": str(gift_account or ""),
        "gift_room": str(gift_room or ""),
        "gift_num": int(gift_num or 1),
        "gift_interval": int(gift_interval or 10),
        "gift_count": int(gift_count or 0),
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
    """一行摘要，用于下拉框显示（含送礼标记）。"""
    if not preset:
        return ""
    s = "%s（%d账户/%d房间/%s分钟" % (
        preset.get("name", ""),
        len(preset.get("accounts") or []),
        len(preset.get("rooms") or []),
        preset.get("duration_minutes", 0),
    )
    gifts = int(preset.get("gift_count") or 0)
    if gifts > 0:
        s += "/送礼%d次" % gifts
    return s + "）"


def describe(preset):
    """多行详细描述，用于应用后的日志与提示。"""
    if not preset:
        return ""
    lines = [
        "账户: %s" % (", ".join(preset.get("accounts") or []) or "无"),
        "直播间: %s" % (", ".join(preset.get("rooms") or []) or "无"),
        "每日时长: %s 分钟" % preset.get("duration_minutes", 0),
        "心跳间隔: %s 秒" % preset.get("heartbeat_interval", 0),
    ]
    if int(preset.get("gift_count") or 0) > 0:
        lines += [
            "送礼账户: %s" % (preset.get("gift_account") or "未设置"),
            "送礼直播间: %s" % (preset.get("gift_room") or "未设置"),
            "礼物数量: %s" % preset.get("gift_num", 1),
            "送礼间隔: %s 秒" % preset.get("gift_interval", 0),
            "送礼次数: %s" % preset.get("gift_count", 0),
        ]
    return "\n".join(lines)