# -*- coding: utf-8 -*-
"""抢码预案管理（v6.2.0 新增）。

场景：不同活动需要完全不同的抢码参数。
  例「绝区零3.3 整点抢」：目标 00:00:00.000、窗口120秒、间隔900ms
  例「鸣潮3.7 半整点抢」：目标 12:30:00.000、窗口60秒、间隔600ms

每次都要手动改一堆设置很麻烦，所以做成「预案」：
  - 把当前全部任务组（含每个任务的窗口期/间隔/优先级）打包成一个预案
  - 一键切换到某个预案
  - 可导出/导入预案文件，方便分享或备份

数据格式（data/rush_presets.json）：
{
  "presets": [
    {
      "name": "绝区零3.3 整点抢",
      "created_at": "2026-10-26 01:30:00",
      "note": "备注",
      "groups": [ ... 完整任务组结构 ... ],
      "ui_settings": { 目标时间/版本/账户等 }
    }
  ]
}
"""

from config import RUSH_PRESETS_FILE
from storage import atomic_write_json, safe_load_json


def load_presets():
    """载入所有预案。返回 list，失败返回空列表。"""
    try:
        data = safe_load_json(RUSH_PRESETS_FILE, {"presets": []})
        if isinstance(data, dict):
            presets = data.get("presets", [])
            if isinstance(presets, list):
                return presets
        elif isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_presets(presets):
    """写回预案文件。返回是否成功。"""
    try:
        atomic_write_json(RUSH_PRESETS_FILE, {"presets": list(presets)})
        return True
    except Exception:
        return False


def deep_copy_groups(groups):
    """深拷贝任务组，避免预案和运行时共用同一个对象被互相修改。"""
    import json
    try:
        return json.loads(json.dumps(groups or [], ensure_ascii=False))
    except Exception:
        return []


def make_preset(name, groups, ui_settings=None, note=""):
    """构造一个预案 dict（不落盘，由调用方决定何时保存）。"""
    import time
    return {
        "name": str(name or "").strip(),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": str(note or ""),
        "groups": deep_copy_groups(groups),
        "ui_settings": dict(ui_settings or {}),
    }


def upsert_preset(presets, preset):
    """新增或同名覆盖一个预案。返回 (新的 list, 是否覆盖了已有)。"""
    name = preset.get("name", "")
    out = []
    replaced = False
    for p in presets:
        if p.get("name") == name:
            out.append(preset)
            replaced = True
        else:
            out.append(p)
    if not replaced:
        out.append(preset)
    return out, replaced


def delete_preset(presets, name):
    """删除指定名字的预案。返回新的 list。"""
    return [p for p in presets if p.get("name") != name]


def get_preset(presets, name):
    """按名字取预案。"""
    for p in presets:
        if p.get("name") == name:
            return p
    return None


def summarize(preset):
    """生成预案摘要文本，用于列表显示。"""
    groups = preset.get("groups", [])
    n_tasks = sum(len(g.get("tasks", [])) for g in groups)
    times = []
    for g in groups[:3]:
        tt = str(g.get("target_time", "")).strip()
        if tt:
            times.append(tt)
    time_str = " / ".join(times[:2]) if times else "-"
    note = preset.get("note", "")
    extra = f" | {note}" if note else ""
    return f"{preset.get('name','')}　组{len(groups)}·任务{n_tasks}　目标 {time_str}{extra}"
