# -*- coding: utf-8 -*-
"""统一 HTTP 客户端（O6）。

原来 bili_api / watch_live / new_mode 各自 requests.get/post，问题：
  - 超时值不统一（10s/15s/无）
  - 重试策略分散，有的重试有的不重试
  - 没有统一代理支持
  - 无法统计请求耗时

本模块提供：
  http_get / http_post      带连接池、默认超时、指数退避重试
  set_proxy / get_proxy     全局代理（从 data/config.json 读取）
  recent_stats()            最近请求耗时统计（供抢码分析用）
"""

import json
import random
import threading
import time

import requests
from requests.adapters import HTTPAdapter

from config import HEADERS

# 默认超时（秒）：(连接, 读取)
DEFAULT_TIMEOUT = (5, 10)
# 抢码等对时效敏感的接口用更短超时
FAST_TIMEOUT = (3, 5)

# 可重试的状态码
RETRY_STATUS = {429, 500, 502, 503, 504}
# 最多尝试次数（含首次）
MAX_ATTEMPTS = 3

_STATS_LOCK = threading.Lock()
_STATS = []          # 最近 N 条 {url, method, status, ms, attempt}
_STATS_MAX = 500

_PROXY = {"url": ""}

_session_lock = threading.Lock()
_session = None


def _build_session():
    s = requests.Session()
    # 连接池：抢码场景并发度高，池子给足
    adapter = HTTPAdapter(pool_connections=32, pool_maxsize=64, max_retries=0)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def get_session():
    global _session
    with _session_lock:
        if _session is None:
            _session = _build_session()
            _apply_proxy(_session)
        return _session


def _apply_proxy(session):
    """把全局代理应用到 session。"""
    try:
        proxy = get_proxy()
        if proxy:
            session.proxies.update({"http": proxy, "https": proxy})
        else:
            session.proxies.clear()
    except Exception:
        pass


def set_proxy(proxy_url):
    """设置全局代理，如 http://127.0.0.1:7890。传空字符串取消。"""
    global _session
    _PROXY["url"] = (proxy_url or "").strip()
    with _session_lock:
        if _session is not None:
            _apply_proxy(_session)
    return _PROXY["url"]


def get_proxy():
    return _PROXY["url"]


def load_proxy_from_config(config_path):
    """从 data/config.json 读取 proxy 字段并应用。"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        proxy = cfg.get("proxy", "")
        if proxy:
            set_proxy(proxy)
        return proxy
    except Exception:
        return ""


def _record(url, method, status, ms, attempt):
    with _STATS_LOCK:
        _STATS.append({
            "url": url,
            "method": method,
            "status": status,
            "ms": round(ms, 1),
            "attempt": attempt,
            "ts": time.time(),
        })
        if len(_STATS) > _STATS_MAX:
            del _STATS[:len(_STATS) - _STATS_MAX]


def recent_stats(n=100):
    """返回最近 n 条请求统计（副本）。"""
    with _STATS_LOCK:
        return list(_STATS[-n:])


def stats_summary(n=100):
    """汇总最近 n 条：平均/最大耗时、失败数、按状态码分布。"""
    with _STATS_LOCK:
        data = list(_STATS[-n:])
    if not data:
        return {"count": 0}
    ms = [d["ms"] for d in data]
    codes = {}
    fails = 0
    for d in data:
        codes[d["status"]] = codes.get(d["status"], 0) + 1
        if d["status"] == 0 or d["status"] >= 400:
            fails += 1
    return {
        "count": len(data),
        "avg_ms": round(sum(ms) / len(ms), 1),
        "max_ms": round(max(ms), 1),
        "min_ms": round(min(ms), 1),
        "fails": fails,
        "codes": codes,
    }


def _should_retry(exc=None, status=None):
    if status is not None and status in RETRY_STATUS:
        return True
    if exc is not None:
        name = type(exc).__name__
        # 网络类异常可重试
        if name in ("ConnectionError", "Timeout", "ReadTimeout",
                    "ConnectTimeout", "ChunkedEncodingError", "SSLError"):
            return True
    return False


def _backoff(attempt, base=0.6, cap=4.0):
    """指数退避 + 抖动，避免大量并发同时重试。"""
    delay = min(cap, base * (2 ** (attempt - 1)))
    return delay * (0.6 + random.random() * 0.8)


def request(method, url, *, headers=None, cookies=None, params=None,
            data=None, json_body=None, timeout=None, session=None,
            max_attempts=MAX_ATTEMPTS, allow_retry=True):
    """统一请求入口。返回 (response 或 None, 异常 或 None)。

    不抛异常，调用方自己判断 resp 是否为 None。
    """
    sess = session or get_session()
    hdrs = dict(HEADERS)
    if headers:
        hdrs.update(headers)
    to = timeout or DEFAULT_TIMEOUT
    attempts = max(1, max_attempts) if allow_retry else 1

    last_exc = None
    for attempt in range(1, attempts + 1):
        t0 = time.time()
        try:
            resp = sess.request(
                method, url,
                headers=hdrs, cookies=cookies, params=params,
                data=data, json=json_body, timeout=to,
            )
            elapsed = (time.time() - t0) * 1000
            _record(url, method, resp.status_code, elapsed, attempt)

            if allow_retry and _should_retry(status=resp.status_code) and attempt < attempts:
                time.sleep(_backoff(attempt))
                continue
            return resp, None
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            _record(url, method, 0, elapsed, attempt)
            last_exc = e
            if allow_retry and _should_retry(exc=e) and attempt < attempts:
                time.sleep(_backoff(attempt))
                continue
            return None, e
    return None, last_exc


def http_get(url, **kwargs):
    return request("GET", url, **kwargs)


def http_post(url, **kwargs):
    return request("POST", url, **kwargs)


def reset_stats():
    with _STATS_LOCK:
        _STATS.clear()
