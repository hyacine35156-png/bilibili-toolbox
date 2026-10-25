# -*- coding: utf-8 -*-
"""更新检查（O10，保守实现）。

设计取舍：
  原方案 O10 是"自动下载替换 exe 并重启"，风险中高——自更新失败会导致
  程序再也打不开。这里只做**安全的版本检查与提示**：
    1. 后台请求 latest.json，比对版本号
    2. 有新版本时弹窗提示 + 给出下载链接
    3. 用户自行下载替换，程序不做任何自动替换

这样既解决"用户不知道有新版本"的问题，又完全没有自更新失败的风险。
将来若要做全自动更新，再在此基础上加 updater 与回滚。
"""

import json
import threading
import time
import webbrowser

import requests

import config

# 更新信息地址（放在 GitHub raw 或自己的托管上）
# 留空则跳过检查，避免无配置时产生无意义请求
UPDATE_INDEX_URL = ""

# 检查间隔（秒）：一天最多检查一次
CHECK_INTERVAL = 24 * 3600

REQUEST_TIMEOUT = 6

_state = {"last_check": 0, "checked": False, "result": None}


def parse_version(v):
    """把 v6.1.0 解析成 (6, 1, 0)。解析失败返回 ()。"""
    try:
        s = str(v or "").strip().lstrip("vV")
        parts = s.split(".")
        out = []
        for p in parts[:3]:
            digits = "".join(ch for ch in p if ch.isdigit())
            out.append(int(digits) if digits else 0)
        while len(out) < 3:
            out.append(0)
        return tuple(out)
    except Exception:
        return ()


def is_newer(remote_ver, local_ver):
    """remote 是否比 local 新。"""
    a = parse_version(remote_ver)
    b = parse_version(local_ver)
    if not a or not b:
        return False
    return a > b


def fetch_latest():
    """请求 latest.json。返回 dict 或 None。

    期望格式：
      {"version": "v6.2.0", "url": "https://...", "notes": "更新说明",
       "sha256": "可选"}
    """
    if not UPDATE_INDEX_URL:
        return None
    try:
        resp = requests.get(UPDATE_INDEX_URL, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict) or not data.get("version"):
            return None
        return data
    except Exception:
        return None


def check_for_update(force=False):
    """检查更新（同步）。

    返回 dict：
      {"has_update": bool, "local": ..., "remote": ..., "url": ..., "notes": ...}
    不需要检查时返回 {"has_update": False, "skipped": True}
    """
    now = time.time()
    if not force:
        if _state["checked"] and now - _state["last_check"] < CHECK_INTERVAL:
            return _state["result"] or {"has_update": False, "skipped": True}

    _state["last_check"] = now
    _state["checked"] = True

    local = getattr(config, "APP_VERSION", "")
    latest = fetch_latest()
    if not latest:
        result = {"has_update": False, "local": local, "skipped": True}
        _state["result"] = result
        return result

    remote = str(latest.get("version", ""))
    result = {
        "has_update": is_newer(remote, local),
        "local": local,
        "remote": remote,
        "url": str(latest.get("url", "")),
        "notes": str(latest.get("notes", "")),
    }
    _state["result"] = result
    return result


def check_in_background(on_result=None):
    """后台检查更新，不阻塞 UI。完成后回调 on_result(result)。"""
    def worker():
        try:
            r = check_for_update()
        except Exception as e:
            r = {"has_update": False, "error": str(e)}
        if on_result is not None:
            try:
                on_result(r)
            except Exception:
                pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def show_update_dialog(parent, result):
    """有更新时弹窗提示（只在主线程调用）。"""
    if not result or not result.get("has_update"):
        return False
    try:
        from tkinter import messagebox
        msg = (
            f"发现新版本！\n\n"
            f"当前版本: {result.get('local', '')}\n"
            f"最新版本: {result.get('remote', '')}\n"
        )
        notes = result.get("notes", "")
        if notes:
            msg += f"\n更新内容:\n{notes}\n"
        url = result.get("url", "")
        if url:
            msg += f"\n点「确定」打开下载页面（不会自动替换当前程序）。"
            if messagebox.askyesno("发现新版本", msg, parent=parent):
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
        else:
            messagebox.showinfo("发现新版本", msg, parent=parent)
        return True
    except Exception:
        return False


def set_update_url(url):
    """运行时设置更新检查地址。"""
    global UPDATE_INDEX_URL
    UPDATE_INDEX_URL = (url or "").strip()
    _state["checked"] = False
    _state["last_check"] = 0
    return UPDATE_INDEX_URL


def get_status():
    """当前检查状态，供 UI 展示。"""
    return {
        "url_configured": bool(UPDATE_INDEX_URL),
        "local_version": getattr(config, "APP_VERSION", ""),
        "last_check": _state["last_check"],
        "last_result": _state["result"],
    }
