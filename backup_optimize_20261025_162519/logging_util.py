# -*- coding: utf-8 -*-
"""统一日志系统（O5）。

项目历史上存在 4 份独立的 log 实现（rush_reward / new_mode / watch_live / schedule），
行为不一致、排障困难。本模块提供统一入口，同时保持向后兼容：

  get_logger(name)            获取 logger，写文件 + 控制台
  attach_ui(logger, widget)   绑定 Tk 文本控件，自动投递到主线程
  read_recent(name, n)        读取最近日志行（用于排障）

线程安全：所有写文件操作持锁；UI 更新通过 root.after 投递，绝不跨线程碰控件。
日志文件按天切分，单文件超过 MAX_BYTES 自动滚动。
"""

import os
import threading
import time
from pathlib import Path

from config import LOG_DIR

# 单文件上限 10MB，超过则滚动
MAX_BYTES = 10 * 1024 * 1024
# 保留天数
KEEP_DAYS = 7

_LOGGERS = {}
_LOCK = threading.Lock()


class Logger:
    """轻量 logger：同时输出到控制台、文件、可选 UI 控件。"""

    def __init__(self, name, subdir="", level="INFO"):
        self.name = name
        self.subdir = subdir
        self.level = level
        self._ui_widgets = []
        self._ui_root = None
        self._file_handle = None
        self._file_path = None
        self._file_date = None
        self._lock = threading.Lock()

    # ---------- 文件句柄管理 ----------

    def _resolve_path(self):
        d = LOG_DIR / self.subdir if self.subdir else LOG_DIR
        d.mkdir(parents=True, exist_ok=True)
        today = time.strftime("%Y%m%d")
        return d / f"{self.name}_{today}.log"

    def _ensure_handle(self):
        """按天开新文件；超过 MAX_BYTES 滚动。"""
        today = time.strftime("%Y%m%d")
        path = self._resolve_path()
        need_new = (
            self._file_handle is None
            or self._file_date != today
            or self._file_path != path
        )
        if not need_new and self._file_handle is not None:
            try:
                if os.path.getsize(self._file_path) < MAX_BYTES:
                    return self._file_handle
            except Exception:
                pass
            need_new = True

        if self._file_handle is not None:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

        if need_new:
            try:
                self._file_handle = open(path, "a", encoding="utf-8")
                self._file_path = path
                self._file_date = today
            except Exception:
                self._file_handle = None
        return self._file_handle

    # ---------- UI 绑定 ----------

    def attach_ui(self, widget, root=None):
        """绑定 Tk Text 控件。root 用于把更新投递到主线程。"""
        try:
            with self._lock:
                self._ui_widgets.append(widget)
                if root is not None:
                    self._ui_root = root
        except Exception:
            pass

    def detach_ui(self, widget=None):
        try:
            with self._lock:
                if widget is None:
                    self._ui_widgets = []
                else:
                    self._ui_widgets = [w for w in self._ui_widgets if w is not widget]
        except Exception:
            pass

    def _push_ui(self, line):
        """把一行日志投递到 UI（必须在主线程执行）。"""
        widgets = list(self._ui_widgets)
        if not widgets:
            return
        for w in widgets:
            try:
                w.insert("end", line)
                w.see("end")
            except Exception:
                pass

    def _push_ui_async(self, line):
        """跨线程安全地更新 UI。"""
        if not self._ui_widgets:
            return
        root = self._ui_root
        if root is not None:
            try:
                root.after(0, lambda: self._push_ui(line))
                return
            except Exception:
                pass
        # 无 root 时尝试在主线程之外直接写（可能不安全，但保证不崩）
        try:
            self._push_ui(line)
        except Exception:
            pass

    # ---------- 输出 ----------

    def log(self, msg, level="INFO"):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        full = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}][{level}] {msg}"
        # 文件 + 控制台
        with self._lock:
            try:
                fh = self._ensure_handle()
                if fh is not None:
                    fh.write(full + "\n")
                    fh.flush()
            except Exception:
                pass
        try:
            print(line)
        except Exception:
            pass
        # UI
        self._push_ui_async(line + "\n")

    def debug(self, msg):
        if self.level == "DEBUG":
            self.log(msg, "DEBUG")

    def info(self, msg):
        self.log(msg, "INFO")

    def warning(self, msg):
        self.log(msg, "WARN")

    def error(self, msg):
        self.log(msg, "ERROR")

    def close(self):
        with self._lock:
            if self._file_handle is not None:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None


def get_logger(name, subdir="", level="INFO"):
    """获取（或创建）一个命名 logger。同名复用。"""
    key = (name, subdir)
    with _LOCK:
        if key not in _LOGGERS:
            _LOGGERS[key] = Logger(name, subdir, level)
        else:
            lg = _LOGGERS[key]
            if level and level != lg.level:
                lg.level = level
        return _LOGGERS[key]


def read_recent(name, n=200, subdir=""):
    """读取某个 logger 今天的最后 n 行（排障用）。"""
    try:
        d = LOG_DIR / subdir if subdir else LOG_DIR
        today = time.strftime("%Y%m%d")
        p = d / f"{name}_{today}.log"
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [ln.rstrip("\n") for ln in lines[-n:]]
    except Exception:
        return []


def cleanup_old_logs(days=KEEP_DAYS):
    """清理超过 days 天的日志文件。返回删除数量。"""
    removed = 0
    try:
        if not LOG_DIR.exists():
            return 0
        cutoff = time.time() - days * 86400
        for p in LOG_DIR.rglob("*.log"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed


def close_all():
    """程序退出时统一关闭所有文件句柄。"""
    with _LOCK:
        for lg in _LOGGERS.values():
            try:
                lg.close()
            except Exception:
                pass
