# -*- coding: utf-8 -*-
"""全局设置模块（v6.7.0 新增）。

用途：集中存放「⚙ 设置」页底部全局设置区的配置项。
设计：JSON 文件持久化，读写都做异常兜底，任何设置项缺失时用默认值。
"""

import json
from config import BASE_DIR
from storage import atomic_write_json, safe_load_json

SETTINGS_FILE = BASE_DIR / "app_settings.json"

# 所有全局设置项的默认值
# 注意：新增设置项时同时在这里加默认值，并在设置页 UI 里加控件
DEFAULTS = {
    # 抢码前自动同步时间（只测量 NTP 偏差，不修改系统时间）
    "auto_ntp_before_rush": True,
    # 提前多少秒开始同步（默认 120 秒 = 2 分钟）
    "auto_ntp_lead_seconds": 120,
    # 同步结果弹窗自动关闭秒数（0 = 不自动关闭）
    "auto_ntp_popup_autoclose": 15,
    # 抢码页默认显示哪个模式（v6.7.4）
    #   False = 旧模式显示在第一页（默认）
    #   True  = 新模式·精准抢码显示在第一页
    "rush_new_mode_first": False,
}


def load_settings():
    """读取全部设置，缺失项用默认值补齐。"""
    data = safe_load_json(SETTINGS_FILE, {})
    if not isinstance(data, dict):
        data = {}
    out = dict(DEFAULTS)
    for k, v in data.items():
        if k in DEFAULTS:
            out[k] = v
    return out


def save_settings(settings):
    """保存全部设置。"""
    try:
        atomic_write_json(SETTINGS_FILE, dict(settings or {}))
        return True
    except Exception:
        return False


def get_setting(key, default=None):
    """读单个设置项。"""
    s = load_settings()
    if default is None:
        return s.get(key, DEFAULTS.get(key))
    return s.get(key, default)


def set_setting(key, value):
    """改单个设置项并保存。"""
    s = load_settings()
    s[key] = value
    return save_settings(s)


def should_auto_ntp():
    """是否开启「抢码前自动同步时间」。"""
    try:
        return bool(get_setting("auto_ntp_before_rush"))
    except Exception:
        return True


def auto_ntp_lead():
    """提前多少秒开始同步（下限 30，上限 600）。"""
    try:
        v = int(get_setting("auto_ntp_lead_seconds") or 120)
    except Exception:
        v = 120
    return max(30, min(600, v))


def auto_ntp_autoclose():
    """弹窗自动关闭秒数（0 表示不自动关闭，上限 120）。"""
    try:
        v = int(get_setting("auto_ntp_popup_autoclose") or 0)
    except Exception:
        v = 0
    return max(0, min(120, v))


def rush_new_mode_first():
    """抢码页是否默认显示「新模式·精准抢码」（v6.7.4）。"""
    try:
        return bool(get_setting("rush_new_mode_first"))
    except Exception:
        return False
