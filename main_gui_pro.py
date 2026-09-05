#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站自动发弹幕工具 - 美观深色主题版
功能：多账户管理、一键发送、实时日志
打包：pyinstaller --onefile --windowed --name B站弹幕工具 main_gui_pro.py
"""

import json
import os
import time
import random
import threading
import hashlib
import urllib.parse
import struct
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
from pathlib import Path

import requests

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# ========== 配色方案 ==========
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_input": "#0f3460",
    "accent": "#00d9ff",
    "accent_hover": "#00b8d9",
    "danger": "#ff4757",
    "success": "#2ed573",
    "warning": "#ffa502",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b8",
    "text_muted": "#6c6c8a",
    "border": "#2a2a4a",
}

# ========== 常量 ==========
# exe所在目录（用于定位）
_EXE_DIR = Path(__file__).parent if not getattr(__import__("sys"), "frozen", False) else Path(__import__("sys").executable).parent
# 所有配置文件存到data子文件夹，避免铺满桌面
BASE_DIR = _EXE_DIR / "data"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# 自动迁移旧配置文件（从exe同目录迁移到data子目录）
def _migrate_old_files():
    old_files = [
        "accounts.json", "danmaku_list.txt", "config.json",
        "act_id_cache.json", "watch_config.json", "rush_config.json",
        "scheduled_tasks.json", "shutdown_config.json",
    ]
    for fname in old_files:
        old_path = _EXE_DIR / fname
        new_path = BASE_DIR / fname
        if old_path.exists() and not new_path.exists():
            try:
                import shutil
                shutil.move(str(old_path), str(new_path))
                print(f"已迁移配置文件: {fname} -> data/")
            except Exception as e:
                print(f"迁移 {fname} 失败: {e}")
    # 迁移logs和backup目录
    for dname in ["logs", "backup"]:
        old_dir = _EXE_DIR / dname
        new_dir = BASE_DIR / dname
        if old_dir.exists() and old_dir.is_dir() and not new_dir.exists():
            try:
                import shutil
                shutil.move(str(old_dir), str(new_dir))
                print(f"已迁移目录: {dname}/ -> data/{dname}/")
            except Exception as e:
                print(f"迁移 {dname} 失败: {e}")

_migrate_old_files()

ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"

# 程序版本号
APP_VERSION = "v4.7.6"

SEND_API = "https://api.live.bilibili.com/msg/send"
USER_INFO_API = "https://api.bilibili.com/x/web-interface/nav"

# 抢码相关API
MISSION_INFO_API = "https://api.bilibili.com/x/activity_components/mission/info"
MISSION_RECEIVE_API = "https://api.bilibili.com/x/activity_components/mission/receive"

# 活动任务列表（按版本+期数+类型分类）
ALL_TASKS = [
    # ===== 鸣潮3.6 =====
    # 上半（第一期）- 投稿任务
    {"version": "鸣潮3.6", "period": "上半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghviah00", "award": "60星声"},
    {"version": "鸣潮3.6", "period": "上半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghviiw00", "award": "120星声"},
    {"version": "鸣潮3.6", "period": "上半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvim200", "award": "180星声"},
    {"version": "鸣潮3.6", "period": "上半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghviy100", "award": "300星声"},
    {"version": "鸣潮3.6", "period": "上半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghviag00", "award": "500星声"},
    # 上半 - 直播任务
    {"version": "鸣潮3.6", "period": "上半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvigp00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.6", "period": "上半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvu0900", "award": "中级能源核心*2"},
    {"version": "鸣潮3.6", "period": "上半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvibr00", "award": "贝币*10000"},
    {"version": "鸣潮3.6", "period": "上半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvord00", "award": "中级复苏吸雾*2"},
    # 上半（第一期）- 直播里程碑
    {"version": "鸣潮3.6", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA1wloghvb6100", "award": "星声*180"},
    {"version": "鸣潮3.6", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghvb5v00", "award": "星声*300"},
    {"version": "鸣潮3.6", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA1wloghvny900", "award": "唤声涡纹*3"},
    # 下半（第二期）- 投稿任务
    {"version": "鸣潮3.6", "period": "下半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghvy7300", "award": "60星声"},
    {"version": "鸣潮3.6", "period": "下半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghvu0800", "award": "120星声"},
    {"version": "鸣潮3.6", "period": "下半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvigh00", "award": "180星声"},
    {"version": "鸣潮3.6", "period": "下半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghvipm00", "award": "300星声"},
    {"version": "鸣潮3.6", "period": "下半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghvicf00", "award": "500星声"},
    # 下半 - 直播任务
    {"version": "鸣潮3.6", "period": "下半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvu4d00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.6", "period": "下半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvihz00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.6", "period": "下半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvotr00", "award": "贝币*10000"},
    {"version": "鸣潮3.6", "period": "下半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvip100", "award": "中级复苏吸雾*2"},
    # 下半（第二期）- 直播里程碑
    {"version": "鸣潮3.6", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA2wloghvivx00", "award": "星声*180"},
    {"version": "鸣潮3.6", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghvnev00", "award": "星声*300"},
    {"version": "鸣潮3.6", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA2wloghvimi00", "award": "唤声涡纹*3"},
    # 全版本（新人开播奖励等）
    {"version": "鸣潮3.6", "period": "全版本", "type": "新人开播", "name": "累计1天开播", "task_id": "18ERA2wloghvimu00", "award": "星声*50"},
    {"version": "鸣潮3.6", "period": "全版本", "type": "新人开播", "name": "累计2天开播", "task_id": "18ERA2wloghvik700", "award": "星声*80"},
    {"version": "鸣潮3.6", "period": "全版本", "type": "新人开播", "name": "累计3天开播", "task_id": "18ERA2wloghvihn00", "award": "星声*120"},
    {"version": "鸣潮3.6", "period": "全版本", "type": "新人开播", "name": "累计7天开播", "task_id": "18ERA1wloghvbkm00", "award": "星声*180"},
    {"version": "鸣潮3.6", "period": "全版本", "type": "新人开播", "name": "累计14天开播", "task_id": "18ERA1wloghvb6w00", "award": "唤声涡纹*2"},

    # ===== 原神7.0（只保留直播里程碑和看播里程碑）=====
    # 直播里程碑任务（累计直播天数）
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播1天", "task_id": "18ERA2wloghvipp00", "award": "原石*200"},
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播5天", "task_id": "18ERA2wloghvi9y00", "award": "原石*600"},
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播10天", "task_id": "18ERA1wloghvbk100", "award": "原石*1000"},
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播20天", "task_id": "18ERA1wloghvbxf00", "award": "原石*1000"},
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播30天", "task_id": "18ERA2wloghvi1c00", "award": "原石*1000"},
    {"version": "原神7.0", "period": "全版本", "type": "直播里程碑", "name": "累计直播40天", "task_id": "18ERA2wloghvixf00", "award": "原石*1000"},
    # 看播里程碑任务（累计看播天数）
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播1天", "task_id": "18ERA2wloghvi2800", "award": "原石*50"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播5天", "task_id": "18ERA1wloghvbce00", "award": "原石*50"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播10天", "task_id": "18ERA1wloghvbz900", "award": "原石*100"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播20天", "task_id": "18ERA2wloghvi6p00", "award": "原石*100"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播30天", "task_id": "18ERA2wloghvibn00", "award": "原石*200"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播40天", "task_id": "18ERA1wloghvbke00", "award": "原石*200"},

    # ===== 崩坏星穹铁道4.5（限时投稿任务）=====
    # 限时任务1（8月26日-9月10日）- 投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "限时任务1", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvsaz00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.5", "period": "限时任务1", "type": "投稿", "name": "累计3天投稿三连×2", "task_id": "6ERAcwloghvsrw00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.5", "period": "限时任务1", "type": "投稿", "name": "累计5天投稿三连≥5且播放≥1000", "task_id": "6ERAcwloghvsry00", "award": "星琼*300"},
    # 限时任务2（9月11日-9月27日）- 投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "限时任务2", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvyud00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.5", "period": "限时任务2", "type": "投稿", "name": "累计3天投稿三连×2", "task_id": "6ERAcwloghvybs00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.5", "period": "限时任务2", "type": "投稿", "name": "累计5天投稿三连×10且播放≥1000", "task_id": "6ERAcwloghvang00", "award": "星琼*300"},
    # 限时直播任务
    {"version": "崩坏星穹铁道4.5", "period": "限时直播", "type": "直播", "name": "8月26日-9月1日开播≥60分钟且弹幕人数≥4人", "task_id": "6ERAcwloghvymk00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.5", "period": "限时直播", "type": "直播", "name": "9月11日-9月17日开播≥60分钟且弹幕人数≥4人", "task_id": "6ERAcwloghvy6e00", "award": "星琼*50"},
    # 新人限定任务
    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积1天开播", "task_id": "18ERA1wloghvv2w00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积3天开播", "task_id": "18ERA1wloghvbfe00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积7天开播", "task_id": "18ERA1wloghvbuc00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.5", "period": "新人限定", "type": "直播", "name": "累积14天开播", "task_id": "18ERA1wloghvbww00", "award": "星琼*200"},
]

# 兼容旧代码
MINGCHAO_TASKS = [t for t in ALL_TASKS if t["version"] == "鸣潮3.6"]

# task_id到act_id的缓存字典（查询成功时自动保存，查询失败时使用）
TASK_ACT_ID_CACHE = {}

# 版本默认act_id（同一版本的所有任务共享同一个act_id）
VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.6": "1ERAzwloghvn7l00",
    "原神7.0": "1ERAzwloghvcpc00",
    "崩坏星穹铁道4.5": "1ERAzwloghvb5600",
}

# 从ALL_TASKS自动填充初始缓存（按版本设置默认act_id）
for _task in ALL_TASKS:
    _version = _task.get("version", "")
    _task_id = _task.get("task_id", "")
    if _version in VERSION_DEFAULT_ACT_ID and _task_id:
        TASK_ACT_ID_CACHE[_task_id] = VERSION_DEFAULT_ACT_ID[_version]

def load_act_id_cache():
    """从文件加载act_id缓存"""
    global TASK_ACT_ID_CACHE
    try:
        if ACT_ID_CACHE_FILE.exists():
            with open(ACT_ID_CACHE_FILE, "r", encoding="utf-8") as f:
                saved_cache = json.load(f)
                if isinstance(saved_cache, dict):
                    TASK_ACT_ID_CACHE.update(saved_cache)
                    print(f"已加载 {len(saved_cache)} 条act_id缓存")
    except Exception as e:
        print(f"加载act_id缓存失败: {e}")

def save_act_id_cache():
    """保存act_id缓存到文件"""
    try:
        with open(ACT_ID_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TASK_ACT_ID_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存act_id缓存失败: {e}")

# 程序启动时加载缓存
load_act_id_cache()

# WBI签名映射表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
    25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]

# 常用弹幕词库（100条，用于批量生成）
DANMAKU_POOL = [
    "666", "主播好强", "来了来了", "哈哈哈哈", "学到了", "太强了", "牛逼",
    "666666", "主播牛逼", "哈哈", "这波操作可以", "厉害了", "我的天",
    "好看好看", "支持主播", "打卡", "签到", "晚上好", "主播好",
    "第一次来", "老粉了", "主播加油", "冲冲冲", "可以可以", "牛啊",
    "这也太强了吧", "学到了学到了", "哈哈笑死", "主播声音好听",
    "关注了关注了", "已关注", "主播今天状态不错", "这把稳了",
    "漂亮", "好球", "精彩", "666主播", "爱了爱了", "绝了",
    "这操作绝了", "主播太厉害了", "笑死我了", "哈哈哈太搞笑了",
    "前排", "沙发", "板凳", "打卡签到", "今日份打卡", "来啦来啦",
    "主播辛苦了", "感谢主播", "谢谢主播", "主播早点休息", "晚安",
    "下次一定", "一定一定", "必须的", "没毛病", "说得对", "有道理",
    "涨知识了", "干货满满", "收藏了", "转发了", "推荐推荐",
    "这把能赢吗", "稳了稳了", "翻了翻了", "可惜了", "差一点",
    "没事没事", "下一把", "再来一把", "继续继续", "不慌不慌",
    "问题不大", "小问题", "这波不亏", "血赚", "血亏", "赚翻了",
    "亏麻了", "赢麻了", "杀疯了", "秀起来了", "操作起来了",
    "家人们谁懂啊", "真的会谢", "我不理解", "离大谱", "太离谱了",
    "就这？", "就这水平？", "不过如此", "拿下拿下", "拿捏了",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}


# ========== 数据管理 ==========
class AccountManager:
    def __init__(self):
        self.accounts = []
        self.load()

    def load(self):
        if ACCOUNTS_FILE.exists():
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
            except Exception:
                self.accounts = []

    def save(self):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def add_account(self, name, sessdata, bili_jct, dede_userid=""):
        for acc in self.accounts:
            if acc["name"] == name:
                return False, f"账户名「{name}」已存在"
        cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
        if dede_userid:
            cookie_str += f"; DedeUserID={dede_userid}"
        ok, msg = verify_login(cookie_str)
        if not ok:
            return False, f"登录验证失败: {msg}"
        account = {
            "name": name,
            "SESSDATA": sessdata,
            "bili_jct": bili_jct,
            "DedeUserID": dede_userid,
            "username": msg,
        }
        self.accounts.append(account)
        self.save()
        return True, f"账户「{name}」添加成功（登录用户: {msg}）\n已保存到: {ACCOUNTS_FILE}"

    def delete_account(self, name):
        self.accounts = [a for a in self.accounts if a["name"] != name]
        self.save()

    def get_account(self, name):
        for acc in self.accounts:
            if acc["name"] == name:
                return acc
        return None

    def get_cookie_string(self, name):
        acc = self.get_account(name)
        if not acc:
            return ""
        parts = [f"SESSDATA={acc['SESSDATA']}", f"bili_jct={acc['bili_jct']}"]
        if acc.get("DedeUserID"):
            parts.append(f"DedeUserID={acc['DedeUserID']}")
        return "; ".join(parts)


def verify_login(cookie_str):
    headers = {**HEADERS, "Cookie": cookie_str}
    try:
        resp = requests.get(USER_INFO_API, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            return True, data["data"].get("uname", "未知用户")
        return False, data.get("message", "cookie无效或已过期")
    except Exception as e:
        return False, f"网络异常: {e}"


def send_danmaku(cookie_str, csrf, room_id, msg):
    headers = {**HEADERS, "Cookie": cookie_str}
    payload = {
        "csrf": csrf, "roomid": room_id, "msg": msg,
        "rnd": int(time.time()), "color": 16777215,
        "fontsize": 25, "mode": 1, "bubble": 0,
    }
    try:
        resp = requests.post(SEND_API, data=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return True, "发送成功"
        return False, f"[{data.get('code')}] {data.get('message', '未知错误')}"
    except Exception as e:
        return False, f"网络异常: {e}"


# ========== 抢码相关函数 ==========
def get_wbi_keys(cookies_dict):
    """获取WBI签名密钥"""
    headers = {**HEADERS, "Referer": "https://www.bilibili.com/"}
    try:
        resp = requests.get(USER_INFO_API, headers=headers, cookies=cookies_dict, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            wbi_img = data["data"]["wbi_img"]
            img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
            sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
            return img_key, sub_key
    except Exception:
        pass
    return None, None


def get_mixin_key(orig):
    """生成混淆密钥"""
    return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]


def wbi_sign(params, img_key, sub_key):
    """对参数进行WBI签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    params["wts"] = int(time.time())
    sorted_params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(sorted_params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    sorted_params["w_rid"] = w_rid
    return sorted_params


def get_mission_info(task_id, cookies_dict):
    """获取任务信息（库存、资格等）"""
    img_key, sub_key = get_wbi_keys(cookies_dict)
    if not img_key:
        return None, "获取WBI密钥失败"

    headers = {
        **HEADERS,
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
    }
    params = {
        "task_id": task_id,
        "web_location": "888.126558",
    }
    signed_params = wbi_sign(params, img_key, sub_key)

    try:
        resp = requests.get(MISSION_INFO_API, headers=headers, cookies=cookies_dict, params=signed_params, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data"), "成功"
        return None, f"[{data.get('code')}] {data.get('message', '未知错误')}"
    except Exception as e:
        return None, f"网络异常: {e}"


def parse_award_stock(award_description):
    """
    从奖励描述文本中解析总库存和每日限量
    例如："本奖品共7700份，数量有限，先到先得，每日限量发放460份"
    返回: (total_stock, daily_limit)
    """
    import re
    total_stock = 0
    daily_limit = 0

    if not award_description:
        return 0, 0

    # 匹配"本奖品共7700份"或"共7700份"
    total_match = re.search(r'共\s*(\d+)\s*份', award_description)
    if total_match:
        total_stock = int(total_match.group(1))

    # 匹配"每日限量发放460份"或"每日限量460份"或"每日发放460份"
    daily_match = re.search(r'每日[^0-9]*(\d+)\s*份', award_description)
    if daily_match:
        daily_limit = int(daily_match.group(1))

    return total_stock, daily_limit


def parse_stock_info(task_info, debug=False, _depth=0, _seen_ids=None):
    """
    通用库存解析函数，尝试多种可能的字段结构
    返回: (day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log)
    """
    # 递归深度限制，防止无限递归
    if _depth > 3:
        return 0, 0, {}, "max_depth", 0, 0, []

    # 循环引用检测
    if _seen_ids is None:
        _seen_ids = set()
    obj_id = id(task_info)
    if obj_id in _seen_ids:
        return 0, 0, {}, "circular_ref", 0, 0, []
    _seen_ids.add(obj_id)

    day_stock = 0
    total_stock = 0
    stock_raw = {}
    stock_source = "unknown"
    award_total_stock = 0
    award_daily_limit = 0
    debug_log = []

    if not isinstance(task_info, dict):
        return 0, 0, {}, "invalid", 0, 0, debug_log

    # 从reward_info.award_description中解析总库存和每日限量
    reward_info = task_info.get("reward_info", {})
    if isinstance(reward_info, dict):
        award_description = reward_info.get("award_description", "")
        award_total_stock, award_daily_limit = parse_award_stock(award_description)
        if debug:
            debug_log.append(f"从描述解析: 总库存={award_total_stock}, 每日限量={award_daily_limit}")

    if debug:
        # 调试：输出所有可能包含库存的字段
        debug_log.append("开始解析库存...")
        debug_log.append(f"顶层字段: {list(task_info.keys())}")
        for key, val in task_info.items():
            if any(kw in key.lower() for kw in ["stock", "remain", "left", "count", "num", "total", "award", "reward", "prize", "gift"]):
                val_str = json.dumps(val, ensure_ascii=False)[:200] if isinstance(val, (dict, list)) else str(val)
                debug_log.append(f"找到相关字段: {key} = {val_str}")

    # 尝试1: stock_info中的库存字段（total_stock=剩余总量，day_stock=今日剩余）
    stock_info = task_info.get("stock_info", {})
    if isinstance(stock_info, dict) and stock_info:
        if debug:
            debug_log.append(f"stock_info内容: {json.dumps(stock_info, ensure_ascii=False)}")

        # total_stock = 剩余总量（活动所有剩余）
        # day_stock = 今日剩余
        # 注意：total_remain_num/day_remain_num 不是实际剩余，不要使用
        total_stock = int(stock_info.get("total_stock", 0) or 0)
        day_stock = int(stock_info.get("day_stock", 0) or 0)
        stock_source = "stock_info"
        stock_raw = stock_info

        if debug:
            debug_log.append(f"使用stock字段: 剩余总量={total_stock}, 今日剩余={day_stock}")

    # 尝试2: 任务级别的库存字段（task_stock, mission_stock, current_stock等）
    for key in ["task_stock", "mission_stock", "current_stock", "remain_stock", "left_stock", "available_stock", "stock_num", "stock_count", "remain_count", "left_count"]:
        val = task_info.get(key, 0)
        if val and int(val) > 0:
            if debug:
                debug_log.append(f"找到任务级别库存字段: {key} = {val}")
            day_stock = int(val)
            total_stock = int(task_info.get("total_stock", task_info.get("total", val)) or val)
            stock_raw = {key: val}
            stock_source = f"task.{key}"
            return day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log

    # 尝试3: award_info / reward_info / prize_info / gift_info 中的库存
    for key in ["award_info", "reward_info", "prize_info", "gift_info", "item_info"]:
        info = task_info.get(key, {})
        if isinstance(info, dict) and info:
            if debug:
                debug_log.append(f"{key}内容: {json.dumps(info, ensure_ascii=False)[:300]}")
            for stock_key in ["stock", "remain", "remain_stock", "stock_num", "left", "count", "num", "total", "available", "remain_count", "left_count", "stock_count"]:
                val = info.get(stock_key, 0)
                if val and int(val) > 0:
                    if debug:
                        debug_log.append(f"找到{key}.{stock_key} = {val}")
                    day_stock = int(val)
                    total_stock = int(info.get("total_stock", info.get("total", val)) or val)
                    stock_raw = info
                    stock_source = f"{key}.{stock_key}"
                    return day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log

    # 尝试4: 如果stock_info有值但可能是活动级别，尝试在stock_info中找任务级别的库存
    if isinstance(stock_info, dict) and stock_info:
        for key in ["task_stock", "mission_stock", "current_stock", "remain_stock", "left_stock", "available_stock", "day_remain", "day_left", "day_available"]:
            val = stock_info.get(key, 0)
            if val and int(val) > 0:
                if debug:
                    debug_log.append(f"找到stock_info.{key} = {val}")
                day_stock = int(val)
                total_stock = int(stock_info.get("total_stock", stock_info.get("total", val)) or val)
                stock_raw = stock_info
                stock_source = f"stock_info.{key}"
                return day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log

    # 尝试5: 嵌套在data / mission_info / act_info / activity_info / task_info中（限制递归深度）
    if _depth < 2:  # 只递归一层，防止无限递归
        for nested_key in ["data", "mission_info", "act_info", "activity_info", "task_info", "detail"]:
            nested = task_info.get(nested_key, {})
            if isinstance(nested, dict) and nested:
                d, t, r, s, at, ad, _ = parse_stock_info(nested, debug=False, _depth=_depth+1, _seen_ids=_seen_ids)
                if d > 0 or t > 0:
                    if debug:
                        debug_log.append(f"嵌套{nested_key}中找到库存: {s} = {d}/{t}")
                    return d, t, r, f"{nested_key}.{s}", award_total_stock, award_daily_limit, debug_log

    # 尝试6: 查找包含stock/remain/left/count/num的任意字段
    for key, val in task_info.items():
        key_lower = key.lower()
        if any(kw in key_lower for kw in ["stock", "remain", "left", "available"]) and isinstance(val, (int, float)) and val > 0:
            if debug:
                debug_log.append(f"自动找到字段: {key} = {val}")
            day_stock = int(val)
            total_stock = int(val)
            stock_raw = {key: val}
            stock_source = f"auto.{key}"
            return day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log

    # 如果都没找到，返回stock_info的值（可能是活动级别库存）
    if day_stock > 0 or total_stock > 0:
        if debug:
            debug_log.append(f"使用stock_info作为库存（可能是活动级别）: {day_stock}/{total_stock}")
        return day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log

    if debug:
        debug_log.append("未找到任何库存字段")
    return 0, 0, {}, "not_found", award_total_stock, award_daily_limit, debug_log


def receive_reward(task_id, task_info, cookies_dict, csrf):
    """领取奖励"""
    headers = {
        **HEADERS,
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
        "Origin": "https://www.bilibili.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # 从task_info中提取activity_id，尝试多种可能的字段名和层级
    activity_id = ""
    activity_name = ""
    task_name = ""
    reward_name = ""

    # 尝试顶层字段
    for key in ["act_id", "activity_id", "ActivityId", "id"]:
        if task_info.get(key):
            activity_id = str(task_info[key])
            break

    # 尝试嵌套字段
    if not activity_id:
        for sub_key in ["act_info", "activity_info", "mission_info", "data"]:
            sub = task_info.get(sub_key, {})
            if isinstance(sub, dict):
                for key in ["act_id", "activity_id", "ActivityId", "id"]:
                    if sub.get(key):
                        activity_id = str(sub[key])
                        break
            if activity_id:
                break

    # 兜底：如果activity_id还是空的，根据task_id从ALL_TASKS查找版本，然后用版本默认act_id
    if not activity_id and task_id:
        for _t in ALL_TASKS:
            if _t.get("task_id") == task_id:
                _version = _t.get("version", "")
                activity_id = VERSION_DEFAULT_ACT_ID.get(_version, "")
                break

    # 提取活动名称
    for key in ["act_name", "activity_name", "ActivityName", "name"]:
        if task_info.get(key):
            activity_name = str(task_info[key])
            break
    if not activity_name:
        for sub_key in ["act_info", "activity_info", "mission_info"]:
            sub = task_info.get(sub_key, {})
            if isinstance(sub, dict):
                for key in ["act_name", "activity_name", "name"]:
                    if sub.get(key):
                        activity_name = str(sub[key])
                        break
            if activity_name:
                break

    # 提取任务名称
    for key in ["task_name", "TaskName", "name", "title"]:
        if task_info.get(key):
            task_name = str(task_info[key])
            break

    # 提取奖励名称
    reward_info = task_info.get("reward_info", {})
    if isinstance(reward_info, dict):
        for key in ["award_name", "name", "reward_name"]:
            if reward_info.get(key):
                reward_name = str(reward_info[key])
                break
    if not reward_name:
        for key in ["reward_name", "award_name"]:
            if task_info.get(key):
                reward_name = str(task_info[key])
                break

    data = {
        "task_id": task_id,
        "activity_id": activity_id,
        "ActivityId": activity_id,
        "act_id": activity_id,
        "activity_name": activity_name,
        "ActivityName": activity_name,
        "act_name": activity_name,
        "task_name": task_name,
        "TaskName": task_name,
        "reward_name": reward_name,
        "RewardName": reward_name,
        "gaia_vtoken": "",
        "receive_from": "missionPage",
        "csrf": csrf,
    }

    try:
        resp = requests.post(MISSION_RECEIVE_API, headers=headers, cookies=cookies_dict, data=data, timeout=10)
        result = resp.json()
        code = result.get("code")
        message = result.get("message", "")

        if code == 0:
            return True, "领取成功", result.get("data")

        # 识别已领取状态
        already_received_keywords = ["已领取", "已经领取", "重复领取", "已完成", "任务已完成", "不可重复领取"]
        if any(keyword in message for keyword in already_received_keywords):
            return True, "已领取", result.get("data")

        return False, f"[{code}] {message}", None
    except Exception as e:
        return False, f"网络异常: {e}", None


def cookies_from_account(acc):
    """从账户数据生成cookies字典"""
    cookies = {
        "SESSDATA": acc["SESSDATA"],
        "bili_jct": acc["bili_jct"],
    }
    if acc.get("DedeUserID"):
        cookies["DedeUserID"] = acc["DedeUserID"]
    return cookies


# ========== 自定义美观组件 ==========
class DarkButton(tk.Canvas):
    """自定义深色主题按钮"""
    def __init__(self, parent, text, command=None, width=170, height=44,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):
        super().__init__(parent, width=width, height=height, bg=COLORS["bg_card"],
                         highlightthickness=0, bd=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.text = text
        self.width = width
        self.height = height
        self._draw(self.bg_color)
        self.bind("<Enter>", lambda e: self._draw(self.hover_color))
        self.bind("<Leave>", lambda e: self._draw(self.bg_color))
        self.bind("<Button-1>", self._on_click)

    def _draw(self, color):
        self.delete("all")
        # 圆角矩形
        r = 8
        self.create_rectangle(r, 0, self.width - r, self.height, fill=color, outline=color)
        self.create_rectangle(0, r, self.width, self.height - r, fill=color, outline=color)
        self.create_oval(0, 0, 2*r, 2*r, fill=color, outline=color)
        self.create_oval(self.width-2*r, 0, self.width, 2*r, fill=color, outline=color)
        self.create_oval(0, self.height-2*r, 2*r, self.height, fill=color, outline=color)
        self.create_oval(self.width-2*r, self.height-2*r, self.width, self.height, fill=color, outline=color)
        self.create_text(self.width//2, self.height//2, text=self.text, fill=self.text_color,
                         font=("微软雅黑", 11, "bold"))

    def _on_click(self, e):
        if self.command:
            self.command()

    def set_state(self, state):
        if state == "disabled":
            self._draw("#444444")
            self.unbind("<Button-1>")
        else:
            self._draw(self.bg_color)
            self.bind("<Button-1>", self._on_click)


class DarkEntry(ttk.Entry):
    """深色输入框"""
    def __init__(self, parent, **kwargs):
        style = ttk.Style()
        style.configure("Dark.TEntry",
                        fieldbackground=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        insertcolor=COLORS["accent"],
                        bordercolor=COLORS["border"],
                        lightcolor=COLORS["border"],
                        darkcolor=COLORS["border"],
                        padding=6)
        super().__init__(parent, style="Dark.TEntry", **kwargs)


# ========== 添加账户对话框 ==========
def custom_askyesno(parent, title, message):
    """自定义确认弹窗，使用DarkButton保证按钮大小一致"""
    result = {"value": False, "done": False}

    confirm_win = tk.Toplevel(parent)
    confirm_win.title(title)
    confirm_win.configure(bg=COLORS["bg_dark"])
    confirm_win.transient(parent)
    confirm_win.grab_set()

    # 内容
    content_frame = tk.Frame(confirm_win, bg=COLORS["bg_dark"], padx=30, pady=25)
    content_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(content_frame, text=message, bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
             font=("微软雅黑", 11), wraplength=350, justify=tk.LEFT).pack(pady=(0, 20))

    # 按钮
    btn_frame = tk.Frame(content_frame, bg=COLORS["bg_dark"])
    btn_frame.pack()

    def on_confirm():
        result["value"] = True
        result["done"] = True
        confirm_win.destroy()

    def on_cancel():
        result["value"] = False
        result["done"] = True
        confirm_win.destroy()

    DarkButton(btn_frame, "确认", command=on_confirm,
               width=150, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
    DarkButton(btn_frame, "取消", command=on_cancel,
               width=150, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    # 居中显示
    confirm_win.update_idletasks()
    x = (confirm_win.winfo_screenwidth() // 2) - 200
    y = (confirm_win.winfo_screenheight() // 2) - 100
    confirm_win.geometry(f"+{x}+{y}")
    confirm_win.resizable(False, False)

    # 等待用户点击
    confirm_win.wait_window()
    return result["value"]


class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(frame, text="添加B站账户", bg=COLORS["bg_dark"],
                         fg=COLORS["accent"], font=("微软雅黑", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 15))

        def add_field(label_text, show=None):
            lbl = tk.Label(frame, text=label_text, bg=COLORS["bg_dark"],
                           fg=COLORS["text_secondary"], font=("微软雅黑", 9))
            lbl.pack(anchor=tk.W, pady=(8, 3))
            entry = DarkEntry(frame, width=42)
            if show:
                entry.config(show=show)
            entry.pack(anchor=tk.W, pady=(0, 5))
            return entry

        self.name_entry = add_field("账户备注名（如：小号1）")
        self.sess_entry = add_field("SESSDATA", show="*")
        self.jct_entry = add_field("bili_jct", show="*")
        self.dede_entry = add_field("DedeUserID（可选）")

        btn_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        DarkButton(btn_frame, "显示/隐藏", command=self.toggle_show,
                   width=150, height=42, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT)
        DarkButton(btn_frame, "取消", command=self.destroy,
                   width=160, height=42, bg_color="#555577", text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=160, height=42).pack(side=tk.RIGHT)

        # 确保窗口大小正确（在所有组件创建后设置）
        self.update_idletasks()
        self.geometry("500x600")
        self.minsize(500, 600)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 300
        self.geometry(f"500x600+{x}+{y}")
        self.grab_set()

    def toggle_show(self):
        current = self.sess_entry.cget("show")
        new = "" if current == "*" else "*"
        self.sess_entry.config(show=new)
        self.jct_entry.config(show=new)

    def on_submit(self):
        name = self.name_entry.get().strip()
        sessdata = self.sess_entry.get().strip()
        bili_jct = self.jct_entry.get().strip()
        dede = self.dede_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请填写账户备注名")
            return
        if not sessdata or not bili_jct:
            messagebox.showwarning("提示", "SESSDATA 和 bili_jct 不能为空")
            return
        if self.on_add:
            ok, msg = self.on_add(name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)


# ========== 抢码工具窗口 ==========
class RushRewardFrame(tk.Frame):
    def __init__(self, parent, account_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.running = False
        self.rush_thread = None
        self._initializing = True  # 初始化标志，期间禁止save_rush_config覆盖加载的配置
        self.rush_config = self.load_rush_config()

        # 定时任务相关
        self.scheduled_tasks = self.load_scheduled_tasks()
        self.scheduled_task_threads = {}  # task_id -> thread
        self.scheduled_task_stop_flags = {}  # task_id -> stop_flag

        # 定时关机相关
        self.shutdown_mode = "none"  # none / scheduled / delay
        self.shutdown_thread = None
        self.shutdown_stop_flag = {"stop": False}
        self.shutdown_remaining = 0  # 剩余秒数

        # 初始化日志文件
        self.log_file = None
        self.init_log_file()

        self.build_ui()
        self.refresh_account_list()
        self.apply_rush_config()
        self.bind_auto_save()
        self._initializing = False  # 初始化完成，允许保存
        self.refresh_scheduled_task_list()
        self.log("抢码工具已启动，选择任务和账户后点击「开始监控」")
        self.log("提示：领取需要先完成投稿任务并绑定游戏账号")

    def on_close(self):
        """保存配置（标签页模式下不需要销毁）"""
        self.save_rush_config()
        self.save_scheduled_tasks()
        # 停止所有定时任务线程
        for task_id, stop_flag in self.scheduled_task_stop_flags.items():
            stop_flag["stop"] = True

    def load_scheduled_tasks(self):
        """加载定时任务列表"""
        tasks_file = BASE_DIR / "scheduled_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    # 重置所有任务状态为等待中
                    for task in tasks:
                        task["status"] = "等待中"
                    return tasks
            except Exception:
                pass
        return []

    def save_scheduled_tasks(self):
        """保存定时任务列表"""
        try:
            tasks_file = BASE_DIR / "scheduled_tasks.json"
            # 保存时不包含线程对象
            tasks_to_save = []
            for task in self.scheduled_tasks:
                task_copy = {k: v for k, v in task.items() if k != "thread"}
                tasks_to_save.append(task_copy)
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_rush_config(self):
        """加载抢码工具配置"""
        default = {
            "version": "鸣潮3.6",
            "period": "上半",
            "task_type": "投稿",
            "interval": "3",
            "task_name": "",
            "selected_accounts": [],
            "duration": "20",
            "interval_mode": "random",
            "fixed_interval": "699",
            "min_interval": "600",
            "max_interval": "800",
            "schedule_hour": "00",
            "schedule_minute": "59",
            "schedule_second": "54",
        }
        rush_config_file = BASE_DIR / "rush_config.json"
        if rush_config_file.exists():
            try:
                with open(rush_config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    # 空值不覆盖默认值（room_id为空时用弹幕工具默认房间号1791983148）
                    for k, v in cfg.items():
                        if v is not None and v != "" and v != []:
                            default[k] = v
            except Exception:
                pass
        return default

    def save_rush_config(self):
        """保存抢码工具配置"""
        if getattr(self, '_initializing', False):
            return  # 初始化期间不保存，防止覆盖加载的配置
        try:
            self.rush_config["version"] = self.version_var.get()
            self.rush_config["period"] = self.period_var.get()
            self.rush_config["task_type"] = self.task_type_var.get()
            self.rush_config["interval"] = self.interval_entry.get().strip()
            self.rush_config["task_name"] = self.task_var.get()
            # 保存选中的账户
            selected_name = self.rush_account_var.get()
            self.rush_config["selected_accounts"] = [selected_name] if selected_name else []
            self.rush_config["duration"] = self.duration_entry.get().strip()
            self.rush_config["interval_mode"] = self.interval_mode.get()
            self.rush_config["fixed_interval"] = self.fixed_interval_entry.get().strip()
            self.rush_config["min_interval"] = self.min_interval_entry.get().strip()
            self.rush_config["max_interval"] = self.max_interval_entry.get().strip()
            self.rush_config["schedule_hour"] = self.schedule_hour_var.get().strip()
            self.rush_config["schedule_minute"] = self.schedule_minute_var.get().strip()
            self.rush_config["schedule_second"] = self.schedule_second_var.get().strip()

            rush_config_file = BASE_DIR / "rush_config.json"
            with open(rush_config_file, "w", encoding="utf-8") as f:
                json.dump(self.rush_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def apply_rush_config(self):
        """应用抢码工具配置（直接更新下拉框选项，不触发级联方法的自动保存）"""
        try:
            # 1. 设置版本
            if self.rush_config.get("version"):
                self.version_var.set(self.rush_config["version"])

            # 2. 根据版本直接更新期数下拉框选项（不调用on_version_change，避免触发自动保存和重置）
            version = self.version_var.get()
            version_periods = []
            for t in ALL_TASKS:
                if t["version"] == version and t["period"] not in version_periods:
                    version_periods.append(t["period"])
            self.period_combo.config(values=version_periods)

            # 3. 设置保存的期数
            saved_period = self.rush_config.get("period", "")
            if saved_period and saved_period in version_periods:
                self.period_var.set(saved_period)
            elif version_periods:
                self.period_var.set(version_periods[0])

            # 4. 根据版本和期数直接更新类型下拉框选项
            period = self.period_var.get()
            version_types = []
            for t in ALL_TASKS:
                if t["version"] == version and t["period"] == period and t["type"] not in version_types:
                    version_types.append(t["type"])
            self.type_combo.config(values=version_types)

            # 5. 设置保存的类型
            saved_type = self.rush_config.get("task_type", "")
            if saved_type and saved_type in version_types:
                self.task_type_var.set(saved_type)
            elif version_types:
                self.task_type_var.set(version_types[0])

            # 6. 更新任务列表（update_task_list内部不会调用save_rush_config，安全）
            self.update_task_list()

            # 7. 恢复查询间隔
            if self.rush_config.get("interval"):
                self.interval_entry.delete(0, tk.END)
                self.interval_entry.insert(0, self.rush_config["interval"])

            # 8. 延迟设置任务名称（等待任务列表更新完成）
            saved_task_name = self.rush_config.get("task_name", "")
            if saved_task_name:
                self.after(300, lambda: self.task_var.set(saved_task_name))

            # 9. 恢复账户模式

            # 10. 恢复领取时长
            if self.rush_config.get("duration"):
                self.duration_entry.delete(0, tk.END)
                self.duration_entry.insert(0, self.rush_config["duration"])

            # 11. 恢复间隔模式
            if self.rush_config.get("interval_mode"):
                self.interval_mode.set(self.rush_config["interval_mode"])

            # 12. 恢复固定间隔
            if self.rush_config.get("fixed_interval"):
                self.fixed_interval_entry.delete(0, tk.END)
                self.fixed_interval_entry.insert(0, self.rush_config["fixed_interval"])

            # 13. 恢复随机间隔范围
            if self.rush_config.get("min_interval"):
                self.min_interval_entry.delete(0, tk.END)
                self.min_interval_entry.insert(0, self.rush_config["min_interval"])
            if self.rush_config.get("max_interval"):
                self.max_interval_entry.delete(0, tk.END)
                self.max_interval_entry.insert(0, self.rush_config["max_interval"])

            # 14. 应用间隔模式（显示/隐藏输入框）
            self.after(50, self.toggle_interval_mode)

            # 15. 恢复定时领取时间
            if self.rush_config.get("schedule_hour"):
                self.schedule_hour_var.set(self.rush_config["schedule_hour"])
            if self.rush_config.get("schedule_minute"):
                self.schedule_minute_var.set(self.rush_config["schedule_minute"])
            if self.rush_config.get("schedule_second"):
                self.schedule_second_var.set(self.rush_config["schedule_second"])

            # 16. 恢复选中的账户（延迟等待账户列表刷新完成）
            selected_names = self.rush_config.get("selected_accounts", [])
            if selected_names:
                self.after(400, lambda: self.restore_selected_accounts(selected_names))

            # 17. 最后保存一次配置，确保所有恢复的值正确持久化
            self.after(600, self.save_rush_config)
        except Exception as e:
            pass

    def restore_selected_accounts(self, selected_names):
        """恢复选中的账户"""
        try:
            if selected_names and len(selected_names) > 0:
                self.rush_account_var.set(selected_names[0])
        except Exception:
            pass

    def bind_auto_save(self):
        """绑定自动保存事件"""
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: (self.on_version_change(), self.save_rush_config()))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: (self.on_period_change(), self.save_rush_config()))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: (self.update_task_list(), self.save_rush_config()))
        self.task_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.duration_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.fixed_interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.min_interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.max_interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.interval_mode.trace_add("write", lambda *a: self.save_rush_config())
        self.schedule_hour_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.schedule_minute_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.schedule_second_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.rush_account_var.trace_add("write", lambda *a: self.save_rush_config())

    def build_ui(self):
        # 顶部标题
        header = tk.Frame(self, bg=COLORS["bg_card"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="⚡ 自动抢码工具", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold")).pack(side=tk.LEFT, padx=20)
        self.rush_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.rush_status.pack(side=tk.RIGHT, padx=20)

        # 主内容区
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 上半部分：设置
        settings_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(settings_card, text="抢码设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：版本选择 + 期数选择 + 任务类型
        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="版本", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.version_var = tk.StringVar(value="鸣潮3.6")
        self.version_combo = ttk.Combobox(row1, textvariable=self.version_var,
                                           values=["鸣潮3.6", "原神7.0", "崩坏星穹铁道4.5"], state="readonly",
                                           width=14, font=("微软雅黑", 11))
        self.version_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: self.on_version_change())

        tk.Label(row1, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.period_var = tk.StringVar(value="上半")
        self.period_combo = ttk.Combobox(row1, textvariable=self.period_var,
                                          values=["上半", "下半", "全版本", "限时任务1", "限时任务2", "限时直播", "新人限定"], state="readonly",
                                          width=10, font=("微软雅黑", 11))
        self.period_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: self.on_period_change())

        tk.Label(row1, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.task_type_var = tk.StringVar(value="投稿")
        self.type_combo = ttk.Combobox(row1, textvariable=self.task_type_var,
                                        values=["投稿", "直播", "直播里程碑", "看播里程碑", "新人开播"], state="readonly",
                                        width=12, font=("微软雅黑", 11))
        self.type_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.update_task_list())

        tk.Label(row1, text="查询间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.interval_entry = DarkEntry(row1, width=6)
        self.interval_entry.insert(0, "3")
        self.interval_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row1, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        # 第二行：具体任务选择
        row1b = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1b.pack(fill=tk.X, pady=3)
        tk.Label(row1b, text="任务", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.task_var = tk.StringVar()
        self.task_combo = ttk.Combobox(row1b, textvariable=self.task_var, values=[],
                                        state="readonly", width=45, font=("微软雅黑", 11))
        self.task_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.on_version_change()  # 初始化期数、类型下拉框选项和任务列表

        # 第二行：账户选择（下拉框）
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        self.rush_account_var = tk.StringVar()
        self.rush_account_combo = ttk.Combobox(row2, textvariable=self.rush_account_var,
                                                 values=[], state="readonly",
                                                 font=("微软雅黑", 10), width=25)
        self.rush_account_combo.pack(side=tk.LEFT, padx=(15, 0))

        # 第三行：状态显示
        row3 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=(8, 0))
        self.stock_label = tk.Label(row3, text="库存状态：等待查询", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.stock_label.pack(side=tk.LEFT)
        self.qualify_label = tk.Label(row3, text="领取资格：等待查询", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.qualify_label.pack(side=tk.LEFT, padx=(20, 0))
        self.task_finish_label = tk.Label(row3, text="任务完成：等待查询", bg=COLORS["bg_card"],
                                           fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.task_finish_label.pack(side=tk.LEFT, padx=(20, 0))

        # 第四行：领取设置（时长、间隔）
        row4 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row4.pack(fill=tk.X, pady=(8, 0))
        tk.Label(row4, text="领取时长", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.duration_entry = DarkEntry(row4, width=6)
        self.duration_entry.insert(0, "20")
        self.duration_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row4, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        tk.Label(row4, text="间隔模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=(20, 0))
        self.interval_mode = tk.StringVar(value="random")
        ttk.Radiobutton(row4, text="固定", variable=self.interval_mode, value="fixed",
                        style="Dark.TRadiobutton", command=self.toggle_interval_mode).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Radiobutton(row4, text="随机", variable=self.interval_mode, value="random",
                        style="Dark.TRadiobutton", command=self.toggle_interval_mode).pack(side=tk.LEFT, padx=(0, 8))

        # 固定间隔输入框
        self.fixed_interval_entry = DarkEntry(row4, width=6)
        self.fixed_interval_entry.insert(0, "699")
        self.fixed_interval_entry.pack(side=tk.LEFT, padx=(0, 2))

        # 随机间隔输入框（最小~最大）
        self.min_interval_entry = DarkEntry(row4, width=6)
        self.min_interval_entry.insert(0, "600")
        self.max_interval_entry = DarkEntry(row4, width=6)
        self.max_interval_entry.insert(0, "800")
        self.tilde_label = tk.Label(row4, text="~", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                                     font=("微软雅黑", 11))
        self.ms_label = tk.Label(row4, text="毫秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                                  font=("微软雅黑", 11))

        # 初始化为随机模式
        self.toggle_interval_mode()

        # 第五行：定时时间（时、分、秒三个独立输入框）
        row5 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row5.pack(fill=tk.X, pady=(6, 0))
        tk.Label(row5, text="定时时间", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        # 时：00-23
        hour_values = [f"{h:02d}" for h in range(24)]
        self.schedule_hour_var = tk.StringVar(value="00")
        self.schedule_hour_combo = ttk.Combobox(row5, textvariable=self.schedule_hour_var,
                                                   values=hour_values, state="readonly", width=4,
                                                   font=("微软雅黑", 11))
        self.schedule_hour_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="时", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        # 分：00-59
        minute_values = [f"{m:02d}" for m in range(60)]
        self.schedule_minute_var = tk.StringVar(value="59")
        self.schedule_minute_combo = ttk.Combobox(row5, textvariable=self.schedule_minute_var,
                                                     values=minute_values, state="readonly", width=4,
                                                     font=("微软雅黑", 11))
        self.schedule_minute_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="分", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        # 秒：00-59
        second_values = [f"{s:02d}" for s in range(60)]
        self.schedule_second_var = tk.StringVar(value="54")
        self.schedule_second_combo = ttk.Combobox(row5, textvariable=self.schedule_second_var,
                                                     values=second_values, state="readonly", width=4,
                                                     font=("微软雅黑", 11))
        self.schedule_second_combo.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        # 按钮行
        btn_row = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        self.query_btn = DarkButton(btn_row, "🔍 查询状态", command=self.query_status,
                                     width=160, height=44, bg_color="#444466", text_color="#ffffff")
        self.query_btn.pack(side=tk.LEFT)
        self.manual_receive_btn = DarkButton(btn_row, "🎯 手动领取", command=self.manual_receive,
                                              width=160, height=44, bg_color="#ff6b35", text_color="#ffffff")
        self.manual_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_receive_now_btn = DarkButton(btn_row, "🚀 开始领取", command=self.start_receive_now,
                                                 width=160, height=44, bg_color="#e74c3c", text_color="#ffffff")
        self.start_receive_now_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.schedule_receive_btn = DarkButton(btn_row, "⏰ 定时领取", command=self.schedule_receive,
                                                width=160, height=44, bg_color="#9b59b6", text_color="#ffffff")
        self.schedule_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_rush_btn = DarkButton(btn_row, "▶ 开始监控", command=self.start_rush,
                                          width=160, height=44, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_rush_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_rush_btn = DarkButton(btn_row, "■ 停止", command=self.stop_rush,
                                         width=160, height=42, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_rush_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_rush_btn.set_state("disabled")

        # 定时任务列表区域
        schedule_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        schedule_card.pack(fill=tk.X, pady=(8, 8))

        schedule_header = tk.Frame(schedule_card, bg=COLORS["bg_card"])
        schedule_header.pack(fill=tk.X, padx=15, pady=(8, 4))
        tk.Label(schedule_header, text="⏰ 定时任务列表（多线程独立运行）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(schedule_header, "+ 添加当前设置", command=self.add_scheduled_task,
                   width=200, height=38, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "▶ 全部开始", command=self.start_all_scheduled_tasks,
                   width=140, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "■ 全部停止", command=self.stop_all_scheduled_tasks,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)

        # 定时任务列表
        list_frame = tk.Frame(schedule_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 表头
        header_frame = tk.Frame(list_frame, bg=COLORS["bg_input"])
        header_frame.pack(fill=tk.X, pady=(0, 8))
        # 用固定像素宽度的Frame容器，确保表头和数据行严格对齐
        col_widths = [300, 100, 150, 130, 70, 140]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]
        # 每列左边距：首列25，时长/间隔列后加大到35
        col_paddings = [25, 18, 18, 35, 18, 18]
        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=32)
            col_frame.pack(side=tk.LEFT, padx=(col_paddings[i], 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=6)

        # 任务列表容器（可滚动）
        self.schedule_list_frame = tk.Frame(list_frame, bg=COLORS["bg_card"])
        self.schedule_list_frame.pack(fill=tk.X)

        # 下半部分：日志
        log_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_card, text="抢码日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.rush_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                      insertbackground=COLORS["accent"], font=("Consolas", 10),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.rush_log_text.pack(fill=tk.BOTH, expand=True)

    def refresh_account_list(self):
        account_names = [acc["name"] for acc in self.account_mgr.accounts]
        self.rush_account_combo["values"] = account_names
        # 默认选中"灵砂是无敌的"账户，否则选第一个
        default_name = "灵砂是无敌的"
        if default_name in account_names:
            self.rush_account_var.set(default_name)
        elif account_names:
            self.rush_account_var.set(account_names[0])

    def get_selected_accounts(self):
        selected_name = self.rush_account_var.get()
        if not selected_name:
            return []
        for acc in self.account_mgr.accounts:
            if acc["name"] == selected_name:
                return [acc]
        return []

    # ========== 定时任务相关方法 ==========
    def refresh_scheduled_task_list(self):
        """刷新定时任务列表显示"""
        # 清空现有内容
        for widget in self.schedule_list_frame.winfo_children():
            widget.destroy()

        if not self.scheduled_tasks:
            tk.Label(self.schedule_list_frame, text="暂无定时任务，设置好参数后点击「+ 添加当前设置」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=10)
            return

        for idx, task in enumerate(self.scheduled_tasks):
            row_frame = tk.Frame(self.schedule_list_frame, bg=COLORS["bg_card"])
            row_frame.pack(fill=tk.X, pady=3)

            # 交替背景色
            if idx % 2 == 0:
                row_frame.configure(bg=COLORS["bg_input"])

            # 用固定像素宽度的Frame容器，确保和表头严格对齐
            col_widths = [300, 100, 150, 130, 70, 140]

            # 任务名称
            name_text = task.get("task_name", "未知任务")[:30]
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=44)
            col1.pack(side=tk.LEFT, padx=(25, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=44)
            col2.pack(side=tk.LEFT, padx=(18, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=44)
            col3.pack(side=tk.LEFT, padx=(18, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=44)
            col4.pack(side=tk.LEFT, padx=(35, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=44)
            col5.pack(side=tk.LEFT, padx=(18, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=12)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=44)
            col6.pack(side=tk.LEFT, padx=(18, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=6)

            task_id = task.get("id")
            if status in ["等待中", "已完成", "已领取", "失败"]:
                DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),
                           width=75, height=28, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))
            else:
                DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),
                           width=75, height=28, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 4))

            DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),
                       width=75, height=28, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    def add_scheduled_task(self):
        """添加当前设置为定时任务"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return

        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get())
                min_interval = fixed_interval
                max_interval = fixed_interval
            else:
                min_interval = float(self.min_interval_entry.get())
                max_interval = float(self.max_interval_entry.get())
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的时间参数")
            return

        # 生成唯一ID
        import uuid
        task_id = str(uuid.uuid4())[:8]

        scheduled_task = {
            "id": task_id,
            "task_id": task["task_id"],
            "task_name": task["name"],
            "award": task.get("award", ""),
            "version": task.get("version", ""),
            "period": task.get("period", ""),
            "task_type": task.get("type", ""),
            "schedule_hour": f"{h:02d}",
            "schedule_minute": f"{m:02d}",
            "schedule_second": f"{s:02d}",
            "duration": str(duration),
            "interval_mode": interval_mode,
            "fixed_interval": str(fixed_interval) if interval_mode == "fixed" else "",
            "min_interval": str(min_interval),
            "max_interval": str(max_interval),
            "account_names": [acc["name"] for acc in accounts],
            "status": "等待中",
        }

        self.scheduled_tasks.append(scheduled_task)
        self.save_scheduled_tasks()
        self.refresh_scheduled_task_list()
        self.log(f"✓ 已添加定时任务: {task['name']} @ {h:02d}:{m:02d}:{s:02d}")

    def start_scheduled_task(self, task_id):
        """启动单个定时任务"""
        task = None
        for t in self.scheduled_tasks:
            if t["id"] == task_id:
                task = t
                break

        if not task:
            return

        if task.get("status") == "运行中":
            return

        # 获取账户对象
        accounts = []
        for acc_name in task.get("account_names", []):
            for acc in self.account_mgr.accounts:
                if acc["name"] == acc_name:
                    accounts.append(acc)
                    break

        if not accounts:
            self.log(f"✗ 定时任务「{task['task_name']}」启动失败：未找到账户")
            return

        # 设置停止标志
        stop_flag = {"stop": False}
        self.scheduled_task_stop_flags[task_id] = stop_flag

        # 更新状态
        task["status"] = "运行中"
        self.refresh_scheduled_task_list()

        # 启动线程
        thread = threading.Thread(
            target=self.scheduled_task_worker,
            args=(task, accounts, stop_flag),
            daemon=True
        )
        self.scheduled_task_threads[task_id] = thread
        thread.start()

        self.log(f"▶ 定时任务已启动: {task['task_name']} @ {task['schedule_hour']}:{task['schedule_minute']}:{task['schedule_second']}")

    def stop_scheduled_task(self, task_id):
        """停止单个定时任务"""
        if task_id in self.scheduled_task_stop_flags:
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        for task in self.scheduled_tasks:
            if task["id"] == task_id:
                task["status"] = "已停止"
                break

        self.refresh_scheduled_task_list()
        self.log(f"■ 定时任务已停止")

    def delete_scheduled_task(self, task_id):
        """删除定时任务"""
        # 先停止
        if task_id in self.scheduled_task_stop_flags:
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        # 从列表中删除
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t["id"] != task_id]

        # 清理线程和标志
        self.scheduled_task_threads.pop(task_id, None)
        self.scheduled_task_stop_flags.pop(task_id, None)

        self.save_scheduled_tasks()
        self.refresh_scheduled_task_list()
        self.log(f"✓ 定时任务已删除")

    def start_all_scheduled_tasks(self):
        """启动所有定时任务（每隔5秒启动一个，避免请求频率过高）"""
        tasks_to_start = []
        for task in self.scheduled_tasks:
            if task.get("status") != "运行中":
                tasks_to_start.append(task["id"])

        if not tasks_to_start:
            self.log("⚠ 没有需要启动的定时任务")
            return

        self.log(f"▶ 即将循序启动 {len(tasks_to_start)} 个定时任务（每个间隔5秒）")

        # 用后台线程循序启动
        def _start_sequentially():
            for i, task_id in enumerate(tasks_to_start):
                if i > 0:
                    self.log(f"  ⏳ 等待5秒后启动下一个任务...")
                    time.sleep(5)
                self.start_scheduled_task(task_id)
            self.log(f"✓ 全部 {len(tasks_to_start)} 个定时任务已启动完成")

        threading.Thread(target=_start_sequentially, daemon=True).start()

    def stop_all_scheduled_tasks(self):
        """停止所有定时任务"""
        for task_id in list(self.scheduled_task_stop_flags.keys()):
            self.scheduled_task_stop_flags[task_id]["stop"] = True

        for task in self.scheduled_tasks:
            if task.get("status") == "运行中":
                task["status"] = "已停止"

        self.refresh_scheduled_task_list()
        self.log(f"■ 已停止所有定时任务")

    def scheduled_task_worker(self, task, accounts, stop_flag):
        """定时任务工作线程"""
        task_id = task["id"]
        task_name = task["task_name"]

        try:
            # 计算目标时间
            h = int(task["schedule_hour"])
            m = int(task["schedule_minute"])
            s = int(task["schedule_second"])
            target_seconds = h * 3600 + m * 60 + s

            now = time.localtime()
            current_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
            wait_seconds = target_seconds - current_seconds
            if wait_seconds < 0:
                wait_seconds += 86400  # 等到明天

            target_timestamp = time.time() + wait_seconds
            self.log(f"⏰ 定时任务「{task_name}」等待 {wait_seconds:.0f} 秒后领取")

            # 一开始就获取任务信息（actid），到点后可以立即领取
            task_info = {
                "act_id": "",
                "act_name": task_name,
                "task_name": task_name,
                "reward_info": {"award_name": task.get("award", "")},
            }
            try:
                cookies = cookies_from_account(accounts[0])
                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    task_info = info
                    act_id = info.get("act_id", "")
                    self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
                else:
                    self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
            except Exception as e:
                self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

            # 精确等待到目标时间
            while not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if remaining <= 0:
                    break
                if remaining > 3:
                    time.sleep(0.2)
                else:
                    time.sleep(0.005)

            if stop_flag["stop"]:
                self.log(f"■ 定时任务「{task_name}」已取消")
                return

            # 到点了，开始领取（任务信息已提前查询好）
            self.log(f"★ 定时任务「{task_name}」到点！开始领取")

            duration = float(task["duration"])
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                fixed_interval = float(task.get("fixed_interval", 699))
                min_interval = fixed_interval / 1000.0
                max_interval = fixed_interval / 1000.0
            else:
                min_interval = float(task.get("min_interval", 600)) / 1000.0
                max_interval = float(task.get("max_interval", 800)) / 1000.0
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval

            # 领取循环
            start_time = time.time()
            attempt = 0
            success = False
            acc_index = 0
            stock_empty_count = 0  # 连续检测到库存为空的次数
            max_stock_seen = 0  # 见过的最大库存（用于判断库存是否曾经>0）
            last_stock_check = 0  # 上次查询库存的时间

            # 领取开始前先查询一次库存，记录初始库存
            try:
                first_account = accounts[0]
                cookies = cookies_from_account(first_account)
                info, _ = get_mission_info(task["task_id"], cookies)
                if info:
                    day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                    initial_stock = max(day_s, total_s)
                    if initial_stock > max_stock_seen:
                        max_stock_seen = initial_stock
                    self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")
            except Exception:
                pass

            while not stop_flag["stop"] and (time.time() - start_time) < duration and not success:
                account = accounts[acc_index % len(accounts)]
                acc_index += 1
                attempt += 1

                # 每隔5次尝试或每隔5秒查询一次库存，跟踪库存变化
                current_time = time.time()
                if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                    last_stock_check = current_time
                    try:
                        cookies = cookies_from_account(account)
                        info, _ = get_mission_info(task["task_id"], cookies)
                        if info:
                            day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                            current_stock = max(day_s, total_s)
                            if current_stock > max_stock_seen:
                                max_stock_seen = current_stock
                    except Exception:
                        pass

                try:
                    ok, msg = self.do_receive_fast(task, task_info, account)
                except Exception as e:
                    ok, msg = False, f"异常: {e}"

                if ok:
                    success = True
                    if "已领取" in msg:
                        self.log(f"✓ 定时任务「{task_name}」已领取（第{attempt}次）")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已领取"
                                break
                    else:
                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已完成"
                                break
                    break
                else:
                    self.log(f"  第{attempt}次: {msg} ({account['name']})")

                # 检测库存是否为空（错误码75255或消息包含"库存已经使用完"）
                if "库存已经使用完" in msg or "75255" in msg:
                    if max_stock_seen > 0:
                        # 曾经见过库存>0，现在掉到0，说明确实抢完了，再抢一次后停止
                        stock_empty_count += 1
                        if stock_empty_count == 1:
                            self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                        elif stock_empty_count >= 2:
                            self.log(f"  ⚠ 库存确认为空，自动停止领取")
                            break
                    else:
                        # 一直没见过库存>0，可能是还没到发放时间，继续抢不停止
                        stock_empty_count = 0
                        if attempt % 5 == 0:
                            self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
                else:
                    stock_empty_count = 0  # 重置计数

                # 随机等待间隔（模拟人类点击）
                import random
                random_interval = random.uniform(min_interval, max_interval)
                self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
                next_attempt = time.time() + random_interval
                while time.time() < next_attempt and not stop_flag["stop"]:
                    time.sleep(0.001)

            elapsed = time.time() - start_time
            if not success and not stop_flag["stop"]:
                self.log(f"✗ 定时任务「{task_name}」领取结束，共尝试 {attempt} 次，未成功")
                for t in self.scheduled_tasks:
                    if t["id"] == task_id:
                        t["status"] = "失败"
                        break
            elif stop_flag["stop"]:
                self.log(f"■ 定时任务「{task_name}」已停止")
                for t in self.scheduled_tasks:
                    if t["id"] == task_id:
                        t["status"] = "已停止"
                        break

        except Exception as e:
            self.log(f"✗ 定时任务「{task_name}」异常: {e}")
            for t in self.scheduled_tasks:
                if t["id"] == task_id:
                    t["status"] = "失败"
                    break

        # 刷新UI
        self.after(0, self.refresh_scheduled_task_list)
        # 清理
        self.scheduled_task_threads.pop(task_id, None)
        self.scheduled_task_stop_flags.pop(task_id, None)

    # ========== 定时关机相关方法 ==========
    def on_shutdown_mode_change(self):
        """关机模式切换时显示/隐藏对应的设置"""
        mode = self.shutdown_mode_var.get()
        if mode == "scheduled":
            self.scheduled_shutdown_frame.pack(fill=tk.X, pady=2)
            self.delay_shutdown_frame.pack_forget()
        elif mode == "delay":
            self.delay_shutdown_frame.pack(fill=tk.X, pady=2)
            self.scheduled_shutdown_frame.pack_forget()
        else:
            self.scheduled_shutdown_frame.pack_forget()
            self.delay_shutdown_frame.pack_forget()
        self.save_rush_config()

    def start_shutdown(self):
        """启动定时关机"""
        mode = self.shutdown_mode_var.get()
        if mode == "none":
            messagebox.showwarning("提示", "请先选择关机模式（定时关机或延时关机）")
            return

        # 如果已经有关机线程在运行，先取消
        if self.shutdown_thread and self.shutdown_thread.is_alive():
            self.cancel_shutdown()

        # 计算关机时间
        now = datetime.now()
        if mode == "scheduled":
            try:
                hour = int(self.shutdown_hour.get().strip())
                minute = int(self.shutdown_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
                return
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)
            delay_seconds = (target_time - now).total_seconds()
            self.log(f"⏻ 定时关机已启动，将在 {hour:02d}:{minute:02d} 关机（约 {int(delay_seconds//60)} 分钟后）")
        elif mode == "delay":
            try:
                delay_minutes = float(self.shutdown_delay.get().strip())
                if delay_minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的延时分钟数（大于0）")
                return
            delay_seconds = delay_minutes * 60
            target_time = now + timedelta(seconds=delay_seconds)
            self.log(f"⏻ 延时关机已启动，将在 {delay_minutes} 分钟后关机（{target_time.strftime('%H:%M:%S')}）")

        self.shutdown_remaining = int(delay_seconds)
        self.shutdown_stop_flag = {"stop": False}
        self.shutdown_mode = mode

        # 启动关机线程
        self.shutdown_thread = threading.Thread(
            target=self.shutdown_worker,
            args=(delay_seconds,),
            daemon=True
        )
        self.shutdown_thread.start()

        # 更新UI状态
        self.start_shutdown_btn.set_state("disabled")
        self.cancel_shutdown_btn.set_state("normal")
        self.update_shutdown_status()

    def cancel_shutdown(self):
        """取消定时关机"""
        if self.shutdown_stop_flag:
            self.shutdown_stop_flag["stop"] = True

        if self.shutdown_thread and self.shutdown_thread.is_alive():
            self.shutdown_thread.join(timeout=2)

        self.shutdown_mode = "none"
        self.shutdown_remaining = 0

        # 更新UI状态
        self.start_shutdown_btn.set_state("normal")
        self.cancel_shutdown_btn.set_state("disabled")
        self.shutdown_status_label.config(text="● 已取消", fg=COLORS["text_muted"])
        self.log("⏻ 定时关机已取消")

    def shutdown_worker(self, delay_seconds):
        """关机工作线程"""
        try:
            start_time = time.time()
            while time.time() - start_time < delay_seconds:
                if self.shutdown_stop_flag["stop"]:
                    return
                remaining = int(delay_seconds - (time.time() - start_time))
                self.shutdown_remaining = remaining
                self.after(0, self.update_shutdown_status)
                time.sleep(1)

            # 时间到，执行关机
            if not self.shutdown_stop_flag["stop"]:
                self.log("⏻ 正在执行关机...")
                self.after(0, self.update_shutdown_status)
                time.sleep(1)
                # 执行Windows关机命令
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
        except Exception as e:
            self.log(f"✗ 定时关机异常: {e}")

    def update_shutdown_status(self):
        """更新关机状态显示"""
        if self.shutdown_remaining > 0:
            hours = self.shutdown_remaining // 3600
            minutes = (self.shutdown_remaining % 3600) // 60
            seconds = self.shutdown_remaining % 60
            if hours > 0:
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = f"{minutes:02d}:{seconds:02d}"
            self.shutdown_status_label.config(text=f"● 倒计时: {time_str}", fg=COLORS["warning"])
        else:
            self.shutdown_status_label.config(text="● 未启动", fg=COLORS["text_muted"])

    def toggle_interval_mode(self):
        """切换固定/随机间隔模式，显示/隐藏对应的输入框"""
        mode = self.interval_mode.get()
        if mode == "fixed":
            # 固定模式：显示固定间隔输入框，隐藏随机间隔输入框
            self.fixed_interval_entry.pack(side=tk.LEFT, padx=(0, 4))
            self.min_interval_entry.pack_forget()
            self.tilde_label.pack_forget()
            self.max_interval_entry.pack_forget()
            self.ms_label.pack(side=tk.LEFT)
        else:
            # 随机模式：隐藏固定间隔输入框，显示随机间隔输入框
            self.fixed_interval_entry.pack_forget()
            self.min_interval_entry.pack(side=tk.LEFT, padx=(0, 2))
            self.tilde_label.pack(side=tk.LEFT)
            self.max_interval_entry.pack(side=tk.LEFT, padx=(2, 4))
            self.ms_label.pack(side=tk.LEFT)
        self.save_rush_config()

    def on_version_change(self):
        """版本切换时更新期数下拉框选项，并自动重置期数为该版本的第一个可用期数"""
        version = self.version_var.get()
        # 获取该版本所有可用的期数
        version_periods = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] not in version_periods:
                version_periods.append(t["period"])
        # 更新期数下拉框的选项
        self.period_combo.config(values=version_periods)
        # 如果当前期数不在该版本的可用期数中，自动切换到第一个可用期数
        if self.period_var.get() not in version_periods and version_periods:
            self.period_var.set(version_periods[0])
        self.on_period_change()
        self.save_rush_config()

    def on_period_change(self):
        """期数切换时更新类型下拉框选项，并自动重置类型为该期数的第一个可用类型"""
        version = self.version_var.get()
        period = self.period_var.get()
        # 获取该版本该期数所有可用的任务类型
        version_types = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] not in version_types:
                version_types.append(t["type"])
        # 更新类型下拉框的选项
        self.type_combo.config(values=version_types)
        # 如果当前类型不在该版本该期数的可用类型中，自动切换到第一个可用类型
        if self.task_type_var.get() not in version_types and version_types:
            self.task_type_var.set(version_types[0])
        self.update_task_list()

    def update_task_list(self):
        """根据版本、期数和任务类型更新任务下拉框"""
        version = self.version_var.get()
        period = self.period_var.get()
        task_type = self.task_type_var.get()
        filtered = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
        # 如果当前类型没有任务，自动切换到该期数第一个有任务的类型
        if not filtered:
            version_types = []
            for t in ALL_TASKS:
                if t["version"] == version and t["period"] == period and t["type"] not in version_types:
                    version_types.append(t["type"])
            if version_types:
                self.task_type_var.set(version_types[0])
                task_type = version_types[0]
                filtered = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
        task_names = [f'{t["name"]} ({t["award"]})' for t in filtered]
        self.task_combo.config(values=task_names)
        if task_names:
            self.task_combo.current(0)
        # 保存筛选后的任务列表
        self.filtered_tasks = filtered

    def get_current_task(self):
        idx = self.task_combo.current()
        if idx < 0 or not hasattr(self, 'filtered_tasks'):
            return None
        if idx >= len(self.filtered_tasks):
            return None
        return self.filtered_tasks[idx]

    def init_log_file(self):
        """初始化日志文件"""
        try:
            LOG_DIR.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.log_file = LOG_DIR / f"抢码日志_{timestamp}.txt"
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write(f"===== B站抢码工具日志 =====\n")
                f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"日志文件: {self.log_file}\n")
                f.write(f"============================\n\n")
        except Exception as e:
            print(f"初始化日志文件失败: {e}")
            self.log_file = None

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.rush_log_text.config(state=tk.NORMAL)
        self.rush_log_text.insert(tk.END, line)
        self.rush_log_text.see(tk.END)
        self.rush_log_text.config(state=tk.DISABLED)
        # 同时写入日志文件
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass

    def query_status(self):
        """手动查询任务状态"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        self.stock_label.config(text="库存：查询中...", fg=COLORS["text_muted"])
        self.qualify_label.config(text="领取资格：查询中...", fg=COLORS["text_muted"])

        def query_worker():
            try:
                acc = accounts[0]
                cookies = cookies_from_account(acc)
                self.log(f"查询: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
                self.log(f"  账户: {acc['name']}, task_id: {task['task_id']}")

                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    # 调试：输出完整的任务信息，排查库存字段结构
                    self.log(f"[调试] 任务信息完整数据: {json.dumps(info, ensure_ascii=False)[:1000]}")

                    # 显示act_id
                    act_id = info.get("act_id", "")
                    if act_id:
                        self.log(f"  ✓ act_id: {act_id}")
                    else:
                        self.log(f"  ⚠ act_id为空，版本默认: {VERSION_DEFAULT_ACT_ID.get(task.get('version', ''), '未找到')}")

                    # 使用通用库存解析函数，尝试多种字段结构（开启调试模式）
                    day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, debug_log = parse_stock_info(info, debug=True)
                    status = info.get("status", 0)
                    message = info.get("message", "")
                    task_finished = info.get("task_finished", False)

                    # 输出库存调试信息到日志
                    for log_line in debug_log:
                        self.log(f"[库存调试] {log_line}")
                    self.log(f"[库存调试] 解析结果: 今日剩余={day_stock}%, 活动剩余={total_stock}%, 来源={stock_source}")
                    self.log(f"[库存调试] 描述解析: 总库存={award_total_stock}, 每日限量={award_daily_limit}")
                    if stock_raw:
                        self.log(f"[库存调试] 库存原始数据: {json.dumps(stock_raw, ensure_ascii=False)[:300]}")

                    # 获取当前时间作为更新时间
                    update_time = time.strftime("%H:%M:%S")

                    if task_finished and status in [0, 1]:
                        self.qualify_label.config(text=f"领取资格：已完成任务，可以领取", fg=COLORS["success"])
                    else:
                        self.qualify_label.config(text=f"领取资格：{message} (状态:{status})", fg=COLORS["warning"])

                    # 更新任务完成情况
                    if task_finished:
                        self.task_finish_label.config(text="任务完成：已完成 ✓", fg=COLORS["success"])
                    else:
                        self.task_finish_label.config(text="任务完成：未完成", fg=COLORS["warning"])

                    # 更新库存显示，明确标注剩余总量（百分比）和今日剩余
                    stock_parts_final = []
                    if award_total_stock > 0:
                        stock_parts_final.append(f"总库存{award_total_stock}")
                    # total_stock 本身就是百分比数值，如46表示46%
                    stock_parts_final.append(f"剩余总量{total_stock}%")
                    if award_daily_limit > 0:
                        stock_parts_final.append(f"每日限量{award_daily_limit}")
                    stock_parts_final.append(f"今日剩余{day_stock}%")
                    stock_text_final = " / ".join(stock_parts_final)

                    if day_stock > 0:
                        self.stock_label.config(text=f"库存：{stock_text_final} ✓ | 更新：{update_time}", fg=COLORS["success"])
                    else:
                        self.stock_label.config(text=f"库存：{stock_text_final} (今日已领完) | 更新：{update_time}", fg=COLORS["warning"])

                    self.log(f"  库存: {stock_text_final} | 来源:{stock_source} | 更新:{update_time}")
                    self.log(f"  状态: {message} (status={status}, 任务完成={task_finished})")
                    self.log(f"  任务名: {info.get('task_name', '')}")
                else:
                    self.stock_label.config(text="库存：查询失败", fg=COLORS["danger"])
                    self.qualify_label.config(text="领取资格：查询失败", fg=COLORS["danger"])
                    self.task_finish_label.config(text="任务完成：查询失败", fg=COLORS["danger"])
                    self.log(f"  查询失败: {msg}")
            except Exception as e:
                import traceback
                self.stock_label.config(text="库存：查询异常", fg=COLORS["danger"])
                self.qualify_label.config(text="领取资格：查询异常", fg=COLORS["danger"])
                self.task_finish_label.config(text="任务完成：查询异常", fg=COLORS["danger"])
                self.log(f"  查询异常: {e}")
                self.log(f"  异常详情: {traceback.format_exc()}")

        threading.Thread(target=query_worker, daemon=True).start()

    def do_receive_once(self, task, account):
        """执行一次领取，返回(是否成功, 消息)"""
        cookies = cookies_from_account(account)
        csrf = account["bili_jct"]
        # 先查询任务信息（用于获取activity_id等字段）
        info, msg = get_mission_info(task["task_id"], cookies)
        if not info:
            self.log(f"  ⚠ 查询任务信息失败: {msg}，使用备用数据尝试领取")
            # 使用备用数据尝试领取（直接根据版本获取act_id）
            version = task.get("version", "")
            backup_act_id = VERSION_DEFAULT_ACT_ID.get(version, "")
            info = {
                "act_id": backup_act_id,
                "act_name": task.get("name", ""),
                "task_name": task.get("name", ""),
                "reward_info": {"award_name": task.get("award", "")},
            }
        else:
            # 查询成功，显示act_id
            act_id = info.get("act_id", "")
            if act_id:
                self.log(f"  ✓ act_id: {act_id}")
        # 直接尝试领取，不先判断状态（避免状态判断错误导致无法领取）
        ok, result, data = receive_reward(task["task_id"], info, cookies, csrf)
        if ok:
            return True, "领取成功"
        return False, result

    def manual_receive(self):
        """手动领取：立即尝试领取一次"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return
        acc = accounts[0]
        self.log(f"手动领取: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        self.log(f"  账户: {acc['name']}")
        ok, msg = self.do_receive_once(task, acc)
        if ok:
            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
            self.log(f"  账户：{acc['name']}")
        else:
            self.log(f"✗ 领取失败：{msg}")

    def start_receive_now(self):
        """开始领取：点击后立即按上面设置的数据持续领取（不等待定时时间）"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        # 解析参数（领取时长、间隔）
        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get()) / 1000.0
                min_interval = fixed_interval
                max_interval = fixed_interval
                if duration <= 0 or fixed_interval <= 0:
                    raise ValueError
            else:
                min_interval = float(self.min_interval_entry.get()) / 1000.0
                max_interval = float(self.max_interval_entry.get()) / 1000.0
                if duration <= 0 or min_interval <= 0 or max_interval <= 0:
                    raise ValueError
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和间隔（毫秒）")
            return

        # 验证账户
        valid_accounts = []
        for acc in accounts:
            ok, msg = verify_login(self.account_mgr.get_cookie_string(acc["name"]))
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过")
        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了")
            return

        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.start_receive_now_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")
        self.rush_status.config(text="● 领取中", fg=COLORS["success"])

        self.log("=" * 40)
        self.log(f"🚀 开始领取（立即执行）")
        self.log(f"任务: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        if interval_mode == "fixed":
            self.log(f"领取时长: {duration}秒 | 固定间隔: {min_interval*1000:.0f}毫秒")
        else:
            self.log(f"领取时长: {duration}秒 | 随机间隔: {min_interval*1000:.0f}~{max_interval*1000:.0f}毫秒")
        self.log(f"账户: {', '.join([a['name'] for a in valid_accounts])}")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.receive_now_loop,
            args=(task, valid_accounts, duration, min_interval, max_interval),
            daemon=True
        )
        self.rush_thread.start()

    def receive_now_loop(self, task, accounts, duration, min_interval, max_interval):
        """立即领取循环：不等待定时时间，直接开始持续领取"""
        # 一开始就获取任务信息（actid）
        task_info = self.build_task_info_from_task(task)
        try:
            first_account = accounts[0]
            cookies = cookies_from_account(first_account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if info:
                task_info = info
                act_id = info.get('act_id', '')
                self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
            else:
                self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
        except Exception as e:
            self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

        # 立即开始领取
        self.log(f"★ 立即开始领取！")
        actual_start = time.time()
        try:
            self.after(0, lambda: self.rush_status.config(text="● 领取中", fg=COLORS["success"]))
        except Exception:
            pass
        if min_interval == max_interval:
            self.log(f"  持续 {duration} 秒，固定间隔 {min_interval*1000:.0f} 毫秒")
        else:
            self.log(f"  持续 {duration} 秒，随机间隔 {min_interval*1000:.0f}~{max_interval*1000:.0f} 毫秒")

        # 快速领取循环（复用定时领取的领取逻辑）
        start_time = time.time()
        attempt = 0
        success = False
        acc_index = 0
        stock_empty_count = 0
        max_stock_seen = 0
        last_stock_check = 0

        # 从任务信息中获取初始库存
        try:
            if task_info:
                day_s, total_s, _, _, _, _, _ = parse_stock_info(task_info)
                initial_stock = max(day_s, total_s)
                if initial_stock > max_stock_seen:
                    max_stock_seen = initial_stock
                self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")
        except Exception:
            pass

        while self.running and (time.time() - start_time) < duration and not success:
            account = accounts[acc_index % len(accounts)]
            acc_index += 1
            attempt += 1

            # 每隔5次尝试或每隔5秒查询一次库存
            current_time = time.time()
            if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                last_stock_check = current_time
                try:
                    cookies = cookies_from_account(account)
                    info, _ = get_mission_info(task["task_id"], cookies)
                    if info:
                        day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                        current_stock = max(day_s, total_s)
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测库存是否为空
            if "库存已经使用完" in msg or "75255" in msg:
                if max_stock_seen > 0:
                    stock_empty_count += 1
                    if stock_empty_count == 1:
                        self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                    elif stock_empty_count >= 2:
                        self.log(f"  ⚠ 库存确认为空，自动停止领取")
                        break
                else:
                    stock_empty_count = 0
                    if attempt % 5 == 0:
                        self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
            else:
                stock_empty_count = 0

            # 随机等待间隔
            import random
            random_interval = random.uniform(min_interval, max_interval)
            self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
            next_attempt_time = time.time() + random_interval
            while time.time() < next_attempt_time and self.running:
                time.sleep(0.001)

        elapsed = time.time() - start_time
        if not success:
            self.log(f"领取结束，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒，未成功")
        else:
            self.log(f"领取完成，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒")

        try:
            self.after(0, self.stop_rush)
        except Exception:
            pass

    def schedule_receive(self):
        """定时领取：在指定时间开始，持续领取指定时长"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户")
            return

        # 解析参数
        try:
            duration = float(self.duration_entry.get())
            interval_mode = self.interval_mode.get()
            if interval_mode == "fixed":
                fixed_interval = float(self.fixed_interval_entry.get()) / 1000.0
                min_interval = fixed_interval
                max_interval = fixed_interval
                if duration <= 0 or fixed_interval <= 0:
                    raise ValueError
            else:
                min_interval = float(self.min_interval_entry.get()) / 1000.0
                max_interval = float(self.max_interval_entry.get()) / 1000.0
                if duration <= 0 or min_interval <= 0 or max_interval <= 0:
                    raise ValueError
                if min_interval > max_interval:
                    min_interval, max_interval = max_interval, min_interval
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和间隔（毫秒）")
            return

        try:
            h = int(self.schedule_hour_var.get().strip())
            m = int(self.schedule_minute_var.get().strip())
            s = int(self.schedule_second_var.get().strip())
            if h < 0 or h > 23 or m < 0 or m > 59 or s < 0 or s > 59:
                raise ValueError
            target_seconds = h * 3600 + m * 60 + s
        except ValueError:
            messagebox.showwarning("提示", "定时时间格式错误，时(0-23) 分(0-59) 秒(0-59)")
            return

        # 验证账户
        valid_accounts = []
        for acc in accounts:
            ok, msg = verify_login(self.account_mgr.get_cookie_string(acc["name"]))
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过")
        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了")
            return

        self.running = True
        self.manual_receive_btn.set_state("disabled")
        self.start_receive_now_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")
        self.rush_status.config(text="● 等待定时", fg=COLORS["warning"])

        self.log("=" * 40)
        self.log(f"定时领取已设置 | 目标时间: {h:02d}:{m:02d}:{s:02d}")
        self.log(f"任务: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        if interval_mode == "fixed":
            self.log(f"领取时长: {duration}秒 | 固定间隔: {min_interval*1000:.0f}毫秒")
        else:
            self.log(f"领取时长: {duration}秒 | 随机间隔: {min_interval*1000:.0f}~{max_interval*1000:.0f}毫秒")
        self.log(f"账户: {', '.join([a['name'] for a in valid_accounts])}")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.schedule_receive_loop,
            args=(task, valid_accounts, target_seconds, duration, min_interval, max_interval),
            daemon=True
        )
        self.rush_thread.start()

    def build_task_info_from_task(self, task):
        """从任务列表数据构造task_info，根据版本设置正确的活动名称和act_id"""
        version = task.get("version", "")
        if "原神" in version:
            act_name = "原神7.0版本创作激励计划"
        elif "崩坏" in version or "星穹" in version:
            act_name = "崩坏星穹铁道4.5版本创作激励计划"
        else:
            act_name = "鸣潮3.6版本创作激励计划"
        # 直接根据版本获取act_id（同一版本所有任务共享同一个act_id）
        act_id = VERSION_DEFAULT_ACT_ID.get(version, task.get("act_id", ""))
        return {
            "act_id": act_id,
            "act_name": act_name,
            "task_name": task["name"],
            "reward_info": {"award_name": task["award"]},
        }

    def do_receive_fast(self, task, task_info, account):
        """快速领取：直接尝试领取"""
        cookies = cookies_from_account(account)
        csrf = account["bili_jct"]
        ok, result, data = receive_reward(task["task_id"], task_info, cookies, csrf)
        if ok:
            return True, "领取成功"
        return False, result

    def schedule_receive_loop(self, task, accounts, target_seconds, duration, min_interval, max_interval):
        """定时领取循环：精确等待到目标时间，然后快速领取"""
        # 计算目标时间戳
        now = time.localtime()
        current_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
        wait_seconds = target_seconds - current_seconds
        if wait_seconds < 0:
            wait_seconds += 86400  # 等到明天

        target_timestamp = time.time() + wait_seconds
        self.log(f"等待 {wait_seconds:.0f} 秒后开始领取（目标: {time.strftime('%H:%M:%S', time.localtime(target_timestamp))}）")

        # 一开始就获取任务信息（actid），到点后可以立即领取
        task_info = self.build_task_info_from_task(task)  # 备用任务信息
        try:
            first_account = accounts[0]
            cookies = cookies_from_account(first_account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if info:
                task_info = info
                act_id = info.get('act_id', '')
                self.log(f"  ✓ 已获取任务信息，act_id: {act_id}")
            else:
                self.log(f"  ⚠ 获取任务信息失败: {msg}，使用备用数据")
        except Exception as e:
            self.log(f"  ⚠ 获取任务信息异常: {e}，使用备用数据")

        # 精确等待到目标时间
        last_log = 0
        while self.running:
            remaining = target_timestamp - time.time()
            if remaining <= 0:
                break
            # 每10秒输出一次剩余时间
            if int(remaining) != last_log and int(remaining) % 10 == 0 and int(remaining) > 0:
                last_log = int(remaining)
                self.log(f"  还剩 {int(remaining)} 秒...")
            # 最后3秒用更短的睡眠间隔提高精度
            if remaining > 3:
                time.sleep(0.2)
            else:
                time.sleep(0.005)

        if not self.running:
            self.log("定时领取已取消")
            return

        # 到点了，立即开始领取（任务信息已提前查询好）
        actual_start = time.time()
        try:
            self.after(0, lambda: self.rush_status.config(text="● 领取中", fg=COLORS["success"]))
        except Exception:
            pass
        self.log(f"★ 到点！立即开始领取（延迟 {actual_start - target_timestamp:.3f} 秒）")
        if min_interval == max_interval:
            self.log(f"  持续 {duration} 秒，固定间隔 {min_interval*1000:.0f} 毫秒")
        else:
            self.log(f"  持续 {duration} 秒，随机间隔 {min_interval*1000:.0f}~{max_interval*1000:.0f} 毫秒")

        # 快速领取循环
        start_time = time.time()
        attempt = 0
        success = False
        acc_index = 0
        stock_empty_count = 0  # 连续检测到库存为空的次数
        max_stock_seen = 0  # 见过的最大库存（用于判断库存是否曾经>0）
        last_stock_check = 0  # 上次查询库存的时间

        # 从提前查询的任务信息中获取初始库存
        try:
            if task_info:
                day_s, total_s, _, _, _, _, _ = parse_stock_info(task_info)
                initial_stock = max(day_s, total_s)
                if initial_stock > max_stock_seen:
                    max_stock_seen = initial_stock
                self.log(f"  初始库存: 今日剩余={day_s}%, 剩余总量={total_s}%")
        except Exception:
            pass

        while self.running and (time.time() - start_time) < duration and not success:
            account = accounts[acc_index % len(accounts)]
            acc_index += 1
            attempt += 1

            # 每隔5次尝试或每隔5秒查询一次库存，跟踪库存变化
            current_time = time.time()
            if attempt % 5 == 1 or (current_time - last_stock_check) > 5:
                last_stock_check = current_time
                try:
                    cookies = cookies_from_account(account)
                    info, _ = get_mission_info(task["task_id"], cookies)
                    if info:
                        day_s, total_s, _, _, _, _, _ = parse_stock_info(info)
                        current_stock = max(day_s, total_s)
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测库存是否为空（错误码75255或消息包含"库存已经使用完"）
            if "库存已经使用完" in msg or "75255" in msg:
                if max_stock_seen > 0:
                    # 曾经见过库存>0，现在掉到0，说明确实抢完了，再抢一次后停止
                    stock_empty_count += 1
                    if stock_empty_count == 1:
                        self.log(f"  ⚠ 库存曾有{max_stock_seen}%现已为空，将再尝试一次后停止")
                    elif stock_empty_count >= 2:
                        self.log(f"  ⚠ 库存确认为空，自动停止领取")
                        break
                else:
                    # 一直没见过库存>0，可能是还没到发放时间，继续抢不停止
                    stock_empty_count = 0
                    if attempt % 5 == 0:
                        self.log(f"  ⚠ 库存持续为空（尚未见发放），继续等待抢码")
            else:
                stock_empty_count = 0  # 重置计数

            # 随机等待间隔（模拟人类点击）
            import random
            random_interval = random.uniform(min_interval, max_interval)
            self.log(f"  第{attempt}次后等待 {random_interval*1000:.0f}ms")
            next_attempt_time = time.time() + random_interval
            while time.time() < next_attempt_time and self.running:
                time.sleep(0.001)

        elapsed = time.time() - start_time
        if not success:
            self.log(f"领取结束，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒，未成功")
        else:
            self.log(f"领取完成，共尝试 {attempt} 次，耗时 {elapsed:.2f} 秒")

        try:
            self.after(0, self.stop_rush)
        except Exception:
            pass

    def start_rush(self):
        """开始自动监控抢码"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务")
            return

        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择一个账户")
            return
        rush_accounts = [accounts[0]]

        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的查询间隔（秒）")
            return

        # 验证账户
        valid_accounts = []
        for acc in rush_accounts:
            cookies = cookies_from_account(acc)
            ok, msg = verify_login(self.account_mgr.get_cookie_string(acc["name"]))
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过")

        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了")
            return

        self.running = True
        self.start_rush_btn.set_state("disabled")
        self.stop_rush_btn.set_state("normal")
        self.query_btn.set_state("disabled")
        self.manual_receive_btn.set_state("disabled")
        self.schedule_receive_btn.set_state("disabled")
        self.rush_status.config(text="● 监控中", fg=COLORS["success"])

        acc_names = "、".join([a["name"] for a in valid_accounts])
        self.log("=" * 40)
        self.log(f"开始监控 | [{task['period']}][{task['type']}] {task['name']}")
        self.log(f"奖励: {task['award']} | task_id: {task['task_id']}")
        self.log(f"账户: {acc_names} | 间隔: {interval}秒")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.rush_loop, args=(task, valid_accounts, interval), daemon=True
        )
        self.rush_thread.start()

    def stop_rush(self):
        """停止监控/领取"""
        self.running = False
        self.start_rush_btn.set_state("normal")
        self.stop_rush_btn.set_state("disabled")
        self.query_btn.set_state("normal")
        self.manual_receive_btn.set_state("normal")
        self.start_receive_now_btn.set_state("normal")
        self.schedule_receive_btn.set_state("normal")
        self.rush_status.config(text="● 已停止", fg=COLORS["warning"])
        self.log("-" * 40)
        self.log("已停止")

    def rush_loop(self, task, accounts, interval):
        """自动抢码循环"""
        acc_index = 0
        query_count = 0
        success = False

        while self.running and not success:
            # 选择账户（单账户模式）
            account = accounts[0]

            cookies = cookies_from_account(account)
            csrf = account["bili_jct"]
            query_count += 1

            # 查询任务信息（带重试机制）
            info = None
            msg = ""
            for retry in range(2):
                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    break
                if retry < 1:
                    time.sleep(0.5)

            if not info:
                self.log(f"[{query_count}] 查询失败 ({account['name']}): {msg}")
            else:
                # 调试：输出完整的任务信息，排查库存字段结构
                if query_count <= 3:
                    self.log(f"[调试] 任务信息完整数据: {json.dumps(info, ensure_ascii=False)[:500]}")

                # 使用通用库存解析函数，尝试多种字段结构
                day_stock, total_stock, stock_raw, stock_source, award_total_stock, award_daily_limit, _ = parse_stock_info(info)
                status = info.get("status", 0)
                task_finished = info.get("task_finished", False)

                # 获取当前时间作为更新时间
                update_time = time.strftime("%H:%M:%S")

                # 构建完整的库存显示文本
                stock_parts = []
                if award_total_stock > 0:
                    stock_parts.append(f"总{award_total_stock}")
                stock_parts.append(f"剩总量{total_stock}%")
                if award_daily_limit > 0:
                    stock_parts.append(f"日限{award_daily_limit}")
                stock_parts.append(f"今日{day_stock}%")
                stock_text = "/".join(stock_parts)

                try:
                    self.after(0, lambda: self.stock_label.config(
                        text=f"库存：{stock_text} | 更新：{update_time}",
                        fg=COLORS["success"] if day_stock > 0 else COLORS["warning"]
                    ))
                    # 更新任务完成情况
                    if task_finished:
                        self.after(0, lambda: self.task_finish_label.config(
                            text="任务完成：已完成 ✓", fg=COLORS["success"]
                        ))
                    else:
                        self.after(0, lambda: self.task_finish_label.config(
                            text="任务完成：未完成", fg=COLORS["warning"]
                        ))
                except Exception:
                    pass

                if query_count % 10 == 0 or day_stock > 0:
                    self.log(f"[{query_count}] {account['name']} | 库存:{stock_text} | 来源:{stock_source} | 状态:{info.get('message','')} | 更新:{update_time}")

                # 判断是否可以领取（增加更多库存字段的判断）
                can_receive = (
                    day_stock > 0
                    and task_finished
                    and status in [0, 1]
                )

                if can_receive:
                    self.log(f"★ 发现可领取！库存={day_stock}，正在领取...")
                    ok, result, data = receive_reward(task["task_id"], info, cookies, csrf)
                    if ok:
                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                        self.log(f"  账户：{account['name']}")
                        if data:
                            self.log(f"  返回数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                        success = True
                        try:
                            self.after(0, self.stop_rush)
                        except Exception:
                            pass
                        break
                    else:
                        self.log(f"  领取失败: {result}")
                        # 如果是库存不足，继续监控；如果是其他错误，等待后重试
                        if "库存" in result or "无资格" in result:
                            pass
                        else:
                            time.sleep(2)

            # 等待间隔
            waited = 0
            while waited < interval and self.running:
                time.sleep(0.3)
                waited += 0.3

        if not success:
            self.log(f"监控结束，共查询 {query_count} 次")



# ========== 看播任务工具 ==========
class WatchLiveFrame(tk.Frame):
    """看播任务工具：模拟观看B站直播间，完成看播里程碑任务"""

    ROOM_ENTRY_API = "https://api.live.bilibili.com/room/v1/Room/room_entry_action"
    HEARTBEAT_API = "https://api.live.bilibili.com/User/userOnlineHeart"

    def __init__(self, parent, account_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.running = False
        self.watch_thread = None
        self.stop_flag = {"stop": False}
        self.account_stats = {}
        self.ws_clients = {}  # 存储WebSocket弹幕连接 {账户名: client}
        self.account_vars = {}  # 每个账户名对应一个BooleanVar
        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.x25kn_threads = {}  # X25Kn观看心跳线程 {账户名: thread}
        self.x25kn_stop = {}  # X25Kn停止标志 {账户名: bool}
        self.x25kn_state = {}  # X25Kn协议状态 {账户名: dict}
        self.watch_config = self.load_watch_config()
        self.build_ui()
        self.refresh_account_list()
        self.apply_watch_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，勾选账户和直播间后点击「开始看播」")

    def load_watch_config(self):
        default = {"room_id": "1791983148", "daily_minutes": 30, "heartbeat_interval": 60, "selected_accounts": [], "room_history": []}
        config_file = BASE_DIR / "watch_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_watch_config(self):
        try:
            current_room = self.room_combo.get().strip()
            # 如果是纯数字直播间号，保存到历史记录
            if current_room and current_room.isdigit() and current_room not in self.watch_config.get("room_history", []):
                history = self.watch_config.get("room_history", [])
                history.insert(0, current_room)
                self.watch_config["room_history"] = history[:20]  # 最多保存20条
                self._refresh_room_combo_values()
            self.watch_config["room_id"] = current_room
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.watch_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def apply_watch_config(self):
        try:
            self._refresh_room_combo_values()
            self.room_combo.set(self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            # 如果配置中没有选中的账户（首次使用），默认全选
            if not selected_names:
                for name, var in self.account_vars.items():
                    var.set(True)
            else:
                for name, var in self.account_vars.items():
                    var.set(name in selected_names)
        except Exception:
            pass

    def bind_auto_save(self):
        try:
            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.room_combo.bind("<<ComboboxSelected>>", self._on_room_selected)
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
        except Exception:
            pass

    def _refresh_room_combo_values(self):
        """刷新直播间下拉框选项：用户直播间 + 历史记录"""
        values = []
        # 添加所有用户的直播间选项
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            values.append(f"【{name}】直播间")
        # 添加历史记录分隔
        if self.watch_config.get("room_history"):
            values.append("--- 历史记录 ---")
            values.extend(self.watch_config["room_history"])
        self.room_combo["values"] = values

    def _on_room_selected(self, event=None):
        """选择直播间下拉框时：如果选的是用户名，自动获取直播间号"""
        selected = self.room_combo.get().strip()
        if selected.startswith("【") and "】直播间" in selected:
            # 提取用户名
            name = selected[1:selected.index("】")]
            # 找到对应用户
            for acc in self.account_mgr.accounts:
                if acc.get("name") == name:
                    mid = acc.get("DedeUserID", "")
                    if mid:
                        room_id = self.get_user_room_id(mid)
                        if room_id:
                            self.room_combo.set(str(room_id))
                            self.log(f"已获取「{name}」的直播间号: {room_id}")
                        else:
                            self.log(f"获取「{name}」直播间号失败，请手动输入")
                    break
        elif selected == "--- 历史记录 ---":
            # 选了分隔符，清空
            self.room_combo.set("")
        self.save_watch_config()

    def get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None

    def _on_account_check(self):
        """复选框点击时保存配置"""
        self.save_watch_config()

    def on_close(self):
        self.stop_watch()
        self.save_watch_config()

    def build_ui(self):
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧账户（复选框多选）
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        # 全选/取消全选按钮
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.select_all_btn = tk.Button(btn_frame, text="全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._select_all_accounts)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.deselect_all_btn = tk.Button(btn_frame, text="取消全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._deselect_all_accounts)
        self.deselect_all_btn.pack(side=tk.LEFT)
        # 复选框区域（无滚动条，账户数量少直接显示）
        list_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.account_scrollable_frame = list_frame

        # 右侧
        right = tk.Frame(main, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # ===== 底部容器：日志 + 控制栏（先pack到BOTTOM，确保固定在窗口最底部）=====
        bottom_container = tk.Frame(right, bg=COLORS["bg_dark"])
        bottom_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        # 日志卡片（固定高度160px）
        log_card = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        log_card.pack_propagate(False)
        log_card.configure(height=160)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(settings_card, text="看播设置", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间(选用户/手动输入):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[])
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.duration_var = tk.IntVar(value=30)
        self.duration_combo = ttk.Combobox(row1, textvariable=self.duration_var, width=8, values=[10, 15, 20, 30, 45, 60, 90, 120], state="readonly")
        self.duration_combo.pack(side=tk.LEFT, padx=(8, 0))

        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="心跳间隔(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=60)
        self.interval_combo = ttk.Combobox(row2, textvariable=self.interval_var, width=8, values=[30, 45, 50, 60, 70, 90, 120], state="readonly")
        self.interval_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.start_btn = DarkButton(row2, "▶ 开始看播", command=self.start_watch, width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = DarkButton(row2, "■ 停止看播", command=self.stop_watch, width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.config(state=tk.DISABLED)

        # 状态卡片
        status_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        status_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(status_card, text="观看状态", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        tree_frame = tk.Frame(status_card, bg=COLORS["bg_card"])
        tree_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        columns = ("account", "status", "watch_time", "heartbeat", "target")
        self.status_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=5)
        self.status_tree.heading("account", text="账户")
        self.status_tree.heading("status", text="状态")
        self.status_tree.heading("watch_time", text="已观看")
        self.status_tree.heading("heartbeat", text="心跳次数")
        self.status_tree.heading("target", text="目标时长")
        self.status_tree.column("account", width=140, anchor=tk.CENTER)
        self.status_tree.column("status", width=80, anchor=tk.CENTER)
        self.status_tree.column("watch_time", width=100, anchor=tk.CENTER)
        self.status_tree.column("heartbeat", width=80, anchor=tk.CENTER)
        self.status_tree.column("target", width=100, anchor=tk.CENTER)
        self.status_tree.pack(fill=tk.X)

        # 日志卡片
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))
        self.log_text = tk.Text(log_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("Consolas", 9), bd=0, highlightthickness=0, wrap=tk.WORD, insertbackground=COLORS["text_primary"])
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框（默认全选）
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=True)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_scrollable_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w", padx=8, pady=4, command=self._on_account_check)
            cb.pack(fill=tk.X, anchor="w")
            self.account_checkbuttons.append(cb)
        self.refresh_status_tree()

    def _select_all_accounts(self):
        for var in self.account_vars.values():
            var.set(True)
        self.save_watch_config()

    def _deselect_all_accounts(self):
        for var in self.account_vars.values():
            var.set(False)
        self.save_watch_config()

    def refresh_status_tree(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name, {"status": "待开始", "watch_seconds": 0, "heartbeat_count": 0})
            watch_min = stats.get("watch_seconds", 0) // 60
            watch_sec = stats.get("watch_seconds", 0) % 60
            ws_status = "✓在线" if stats.get("ws_connected", False) else ""
            status_text = stats.get("status", "待开始")
            if ws_status:
                status_text = f"{status_text} {ws_status}"
            self.status_tree.insert("", tk.END, values=(name, status_text, f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_msg)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def get_danmu_token(self, account, room_id):
        """用登录cookie获取弹幕服务器token"""
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie}
            resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}",
                               headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data["data"].get("token", ""), data["data"].get("host", "broadcastlv.chat.bilibili.com")
        except Exception as e:
            self.log(f"  获取弹幕token异常: {e}")
        return "", "broadcastlv.chat.bilibili.com"

    def connect_ws_danmaku(self, account, room_id):
        """建立WebSocket弹幕连接，让账户出现在在线观众列表中，支持自动重连"""
        if not WEBSOCKET_AVAILABLE:
            self.log(f"  websocket-client未安装，跳过弹幕连接")
            return None

        name = account.get("name", "未知")
        uid = int(account.get("DedeUserID", "0") or "0")

        # B站弹幕协议
        HEADER_STRUCT = struct.Struct('>I2H2I')
        OP_HEARTBEAT = 2
        OP_AUTH = 7

        def pack_data(op, data_bytes):
            header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
            return header + data_bytes

        client = {
            "ws": None, "running": False, "connected": False,
            "heartbeat_thread": None, "reconnect_count": 0,
            "account": account, "room_id": int(room_id), "name": name
        }

        def do_connect():
            """执行实际连接"""
            try:
                # 获取token
                token, host = self.get_danmu_token(account, room_id)
                if not token:
                    self.log(f"  [{name}] ✗ 获取弹幕token失败")
                    return False

                def on_message(ws, message):
                    try:
                        if len(message) < 16:
                            return
                        _, _, _, op, _ = HEADER_STRUCT.unpack_from(message, 0)
                        if op == 8:  # 认证响应
                            body = message[16:]
                            result = json.loads(body.decode('utf-8'))
                            if result.get("code") == 0:
                                client["connected"] = True
                                client["reconnect_count"] = 0
                                self.log(f"  [{name}] ✓ 弹幕连接认证成功(uid={uid})，等待计入在线观众")
                                if name in self.account_stats:
                                    self.account_stats[name]["ws_connected"] = True
                                    self.after(0, self.refresh_status_tree)
                            else:
                                self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")
                        elif op == 3:  # 心跳响应，包含人气值
                            try:
                                popularity = struct.unpack('>I', message[16:20])[0]
                                client["last_popularity"] = popularity
                            except Exception:
                                pass
                    except Exception:
                        pass

                def on_error(ws, error):
                    if client["running"] and client["connected"]:
                        err_str = str(error)
                        if "ping/pong" not in err_str and "Connection to remote host was lost" not in err_str:
                            self.log(f"  [{name}] 弹幕连接错误: {error}")

                def on_close(ws, *args):
                    was_connected = client["connected"]
                    client["connected"] = False
                    if name in self.account_stats:
                        self.account_stats[name]["ws_connected"] = False
                    # 自动重连
                    if client["running"] and was_connected:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 10:
                            delay = min(5 * client["reconnect_count"], 30)
                            self.log(f"  [{name}] 弹幕连接断开，{delay}秒后自动重连(第{client['reconnect_count']}次)")
                            threading.Timer(delay, do_connect).start()
                        else:
                            self.log(f"  [{name}] 弹幕重连次数过多，停止重连")

                def on_open(ws):
                    auth_data = {
                        "uid": uid,
                        "roomid": int(room_id),
                        "protover": 2,
                        "platform": "web",
                        "clientver": "2.6.41",
                        "type": 2,
                        "key": token
                    }
                    ws.send(pack_data(OP_AUTH, json.dumps(auth_data, separators=(',', ':')).encode()),
                           opcode=websocket.ABNF.OPCODE_BINARY)

                ws_url = f"wss://{host}/sub"
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                client["ws"] = ws
                # 不使用库级别的ping/pong（B站不响应），只用应用层心跳
                threading.Thread(target=ws.run_forever,
                               kwargs={"origin": "https://live.bilibili.com"},
                               daemon=True).start()
                return True
            except Exception as e:
                self.log(f"  [{name}] 弹幕连接异常: {e}")
                return False

        def heartbeat_loop():
            hb_count = 0
            while client["running"]:
                try:
                    if client["connected"] and client["ws"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                        hb_count += 1
                        # 每2次心跳（60秒）显示一次连接状态
                        if hb_count % 2 == 0:
                            self.log(f"  [{name}] 弹幕连接正常，已发送{hb_count}次心跳")
                    elif not client["connected"]:
                        # 连接未建立，不打印（避免刷屏）
                        pass
                except Exception as e:
                    self.log(f"  [{name}] 弹幕心跳异常: {e}")
                time.sleep(30)

        # 初始连接
        client["running"] = True
        client["heartbeat_thread"] = threading.Thread(target=heartbeat_loop, daemon=True)
        client["heartbeat_thread"].start()
        do_connect()
        return client

    def close_all_ws(self):
        """关闭所有WebSocket弹幕连接（带超时，避免卡住）"""
        for name, client in self.ws_clients.items():
            if client:
                client["running"] = False
                if client.get("ws"):
                    try:
                        # 设置关闭超时，避免阻塞
                        ws = client["ws"]
                        ws.sock = None  # 强制断开
                        ws.close()
                    except Exception:
                        pass
        self.ws_clients.clear()

    def get_cookie(self, account):
        return f"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}"

    def enter_room(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": int(room_id), "platform": "pc", "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.ROOM_ENTRY_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "进入直播间成功"
            return False, f"进入失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"进入异常: {e}"

    def send_heartbeat(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": int(room_id), "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.HEARTBEAT_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "心跳成功"
            return False, f"心跳失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"心跳异常: {e}"

    def get_play_url(self, account, room_id):
        """获取直播流URL（旧版API，flv直链，稳定可靠）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 旧版API：直接返回flv播放地址
            url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={room_id}&quality=4&platform=web"
            resp = requests.get(url, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                durl = data.get("durl", [])
                if durl:
                    play_url = durl[0].get("url", "")
                    if play_url:
                        return True, play_url
                return False, f"未找到直播流地址，data={str(data)[:200]}"
            return False, f"API返回code={result.get('code')}, msg={result.get('message')}"
        except Exception as e:
            return False, f"获取异常: {e}"

    def get_room_info(self, account, room_id):
        """获取房间信息（浏览器加载页面时会调用）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
            }
            url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}"
            resp = requests.get(url, headers=headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    # ========== X25Kn 观看心跳上报协议（v4.0.0新增）==========
    X25KN_E_URL = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
    X25KN_X_URL = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X"
    X25KN_HMAC_FUNCS = ["md5", "sha1", "sha256", "sha224", "sha512", "sha384"]
    X25KN_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    def x25kn_sign(self, payload_json, rules, secret_key):
        """按secret_rule用secret_key做HMAC链式签名"""
        import hmac
        result = payload_json
        key_bytes = secret_key.encode("utf-8")
        for r in rules:
            if 0 <= r < len(self.X25KN_HMAC_FUNCS):
                mac = hmac.new(key_bytes, result.encode("utf-8"),
                               getattr(hashlib, self.X25KN_HMAC_FUNCS[r]))
                result = mac.hexdigest()
        return result

    def x25kn_get_buvid(self, account):
        """获取LIVE_BUVID（通过SPI接口）"""
        try:
            cookie = self.get_cookie(account)
            headers = {"User-Agent": self.X25KN_UA, "Cookie": cookie}
            resp = requests.get("https://api.bilibili.com/x/frontend/finger/spi", headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("b_3"):
                return data["data"]["b_3"]
        except Exception:
            pass
        # fallback：随机生成
        import random, string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=37)) + "infoc"

    def x25kn_get_area_info(self, account, room_id):
        """获取直播间area_id和parent_area_id"""
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}"}
            # 旧版API（新版getInfoByRoom可能返回-352风控）
            resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
                                headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data["data"]["area_id"], data["data"]["parent_area_id"], data["data"]["uid"]
        except Exception:
            pass
        return 874, 3, 3690972101740709  # 鸣潮分区默认值

    def x25kn_enter(self, account, room_id, area_id, parent_id, up_id, buvid, uuid_str):
        """E接口：进入房间，返回{timestamp, secret_key, secret_rule, heartbeat_interval}"""
        try:
            cookie = self.get_cookie(account)
            bili_jct = account.get("bili_jct", "")
            ts = int(time.time() * 1000)
            form = {
                "id": json.dumps([parent_id, area_id, 0, int(room_id)], separators=(",", ":")),
                "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
                "ts": ts,
                "is_patch": 0,
                "heart_beat": "[]",
                "ua": self.X25KN_UA,
                "csrf_token": bili_jct,
                "csrf": bili_jct,
                "visit_id": "",
                "ruid": up_id,
            }
            headers = {
                "User-Agent": self.X25KN_UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
                "Origin": "https://live.bilibili.com",
                "Referer": f"https://live.bilibili.com/{room_id}",
            }
            resp = requests.post(self.X25KN_E_URL, data=form, headers=headers, timeout=15)
            result = resp.json()
            if result.get("code") == 0 and result.get("data"):
                return result["data"]
            return {"_error": True, "code": result.get("code"), "message": result.get("message"), "raw": result}
        except Exception as e:
            return {"_error": True, "code": -1, "message": f"异常: {type(e).__name__}: {e}"}

    def x25kn_heartbeat(self, account, room_id, area_id, parent_id, up_id, seq,
                        buvid, uuid_str, ets, secret_key, secret_rule, heartbeat_interval):
        """X接口：心跳，返回{timestamp, secret_key, secret_rule, heartbeat_interval}"""
        try:
            cookie = self.get_cookie(account)
            bili_jct = account.get("bili_jct", "")
            ts = int(time.time() * 1000)
            sign_payload = {
                "platform": "web",
                "parent_id": parent_id,
                "area_id": area_id,
                "seq_id": seq,
                "room_id": int(room_id),
                "buvid": buvid,
                "uuid": uuid_str,
                "ets": ets,
                "time": heartbeat_interval,
                "ts": ts,
            }
            sign_input = json.dumps(sign_payload, separators=(",", ":"))
            s = self.x25kn_sign(sign_input, secret_rule, secret_key)
            form = {
                "s": s,
                "id": json.dumps([parent_id, area_id, seq, int(room_id)], separators=(",", ":")),
                "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
                "ruid": up_id,
                "ets": ets,
                "benchmark": secret_key,
                "time": heartbeat_interval,
                "ts": ts,
                "ua": self.X25KN_UA,
                "csrf_token": bili_jct,
                "csrf": bili_jct,
                "visit_id": "",
            }
            headers = {
                "User-Agent": self.X25KN_UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
                "Origin": "https://live.bilibili.com",
                "Referer": f"https://live.bilibili.com/{room_id}",
            }
            resp = requests.post(self.X25KN_X_URL, data=form, headers=headers, timeout=15)
            result = resp.json()
            if result.get("code") == 0 and result.get("data"):
                return result["data"]
            return {"_error": True, "code": result.get("code"), "message": result.get("message"), "raw": result}
        except Exception as e:
            return {"_error": True, "code": -1, "message": f"异常: {type(e).__name__}: {e}"}

    def x25kn_thread_func(self, account, room_id, area_id, parent_id, up_id, name):
        """X25Kn观看心跳线程：E接口进入后，按心跳间隔循环X接口"""
        import uuid as uuid_lib
        buvid = self.x25kn_get_buvid(account)
        uuid_str = str(uuid_lib.uuid4())
        self.log(f"  [{name}] X25Kn获取LIVE_BUVID: {buvid[:20]}...")

        # E接口
        e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
        if not e_data or e_data.get("_error"):
            err_msg = ""
            if e_data and e_data.get("_error"):
                err_msg = f"（code={e_data.get('code')}, message={e_data.get('message')}）"
            self.log(f"  [{name}] ✗ X25Kn E接口失败{err_msg}，观看心跳未启动")
            return

        secret_key = e_data["secret_key"]
        secret_rule = e_data["secret_rule"]
        ets = e_data["timestamp"]
        heartbeat_interval = int(e_data.get("heartbeat_interval") or 60)
        if heartbeat_interval < 5 or heartbeat_interval > 300:
            heartbeat_interval = 60

        self.x25kn_state[name] = {
            "secret_key": secret_key, "secret_rule": secret_rule, "ets": ets,
            "seq": 0, "interval": heartbeat_interval, "buvid": buvid, "uuid": uuid_str,
            "beat_count": 0,
        }
        self.log(f"  [{name}] ✓ X25Kn E接口成功，rule={secret_rule}，间隔{heartbeat_interval}s")

        # 等待第一个心跳间隔
        for _ in range(heartbeat_interval):
            if self.x25kn_stop.get(name, False) or self.stop_flag["stop"]:
                return
            time.sleep(1)

        # 循环X接口
        consecutive_fail = 0
        while not self.x25kn_stop.get(name, False) and not self.stop_flag["stop"]:
            state = self.x25kn_state.get(name)
            if not state:
                break
            next_seq = state["seq"] + 1
            result = self.x25kn_heartbeat(
                account, room_id, area_id, parent_id, up_id, next_seq,
                state["buvid"], state["uuid"], state["ets"],
                state["secret_key"], state["secret_rule"], state["interval"]
            )
            if result and not result.get("_error"):
                state["seq"] = next_seq
                state["secret_key"] = result.get("secret_key", state["secret_key"])
                state["secret_rule"] = result.get("secret_rule", state["secret_rule"])
                state["ets"] = result.get("timestamp", state["ets"])
                next_interval = int(result.get("heartbeat_interval") or state["interval"])
                if 5 <= next_interval <= 300:
                    state["interval"] = next_interval
                state["beat_count"] += 1
                consecutive_fail = 0
                if state["beat_count"] % 2 == 0:
                    self.log(f"  [{name}] X25Kn心跳 #{state['beat_count']} 成功")
            else:
                consecutive_fail += 1
                err_msg = ""
                if result and result.get("_error"):
                    err_msg = f"（code={result.get('code')}, message={result.get('message')}）"
                self.log(f"  [{name}] X25Kn心跳失败{err_msg}（连续{consecutive_fail}次），重新E接口...")
                if consecutive_fail >= 3:
                    # 重新E接口
                    e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
                    if e_data and not e_data.get("_error"):
                        state["secret_key"] = e_data["secret_key"]
                        state["secret_rule"] = e_data["secret_rule"]
                        state["ets"] = e_data["timestamp"]
                        state["seq"] = 0
                        consecutive_fail = 0
                        self.log(f"  [{name}] X25Kn已重新E接口")
                    else:
                        time.sleep(10)

            # 等待心跳间隔
            interval = state.get("interval", 60)
            for _ in range(interval):
                if self.x25kn_stop.get(name, False) or self.stop_flag["stop"]:
                    return
                time.sleep(1)

    def play_thread(self, account, room_id):
        """持续播放线程：模拟真实浏览器持续下载视频流"""
        name = account.get("name", "未知")
        cookie = self.get_cookie(account)
        headers = {
            **HEADERS,
            "Cookie": cookie,
            "Referer": f"https://live.bilibili.com/{room_id}",
            "Origin": "https://live.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        play_count = 0
        last_m3u8_refresh = 0
        current_ts_urls = []
        base_url = ""
        self.log(f"  [{name}] 播放线程已启动")
        
        while not self.stop_flag["stop"]:
            try:
                # 每60秒刷新一次播放地址（直播流地址会变）
                now = time.time()
                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    self.log(f"  [{name}] 正在获取播放地址...")
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue
                    self.log(f"  [{name}] 播放地址获取成功: {play_url[:80]}...")
                    # flv直链：保持长连接持续读取（模拟真实播放器）
                    try:
                        self.log(f"  [{name}] 正在连接视频流...")
                        resp = requests.get(play_url, headers=headers, timeout=(10, 30), stream=True)
                        if resp.status_code != 200:
                            self.log(f"  [{name}] 视频流连接失败: HTTP {resp.status_code}")
                            resp.close()
                            time.sleep(5)
                            continue
                        self.log(f"  [{name}] ✓ 视频流连接成功，开始播放...")
                        # 持续读取流数据，保持连接不断开
                        bytes_read = 0
                        play_start = time.time()
                        while not self.stop_flag["stop"]:
                            try:
                                chunk = resp.raw.read(8192)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                                play_count += 1
                                # 每下载约1MB打印一次
                                if bytes_read % 1048576 < 8192:
                                    elapsed = int(time.time() - play_start)
                                    self.log(f"  [{name}] 播放中，已下载{bytes_read//1024}KB，持续{elapsed}秒")
                                # 控制读取速度（约500KB/s，模拟正常播放）
                                time.sleep(0.016)
                                # 每60秒刷新一次播放地址
                                if time.time() - play_start > 60:
                                    break
                            except Exception as e:
                                self.log(f"  [{name}] 读取流异常: {e}")
                                break
                        resp.close()
                        last_m3u8_refresh = time.time()
                        if self.stop_flag["stop"]:
                            break
                        continue
                    except Exception as e:
                        self.log(f"  [{name}] 视频流异常: {e}")
                        time.sleep(5)
                        continue
                    # m3u8格式
                    resp = requests.get(play_url, headers=headers, timeout=10)
                    if resp.status_code == 200 and "#EXTM3U" in resp.text:
                        lines = resp.text.split("\n")
                        current_ts_urls = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                        base_url = play_url.rsplit("/", 1)[0]
                        last_m3u8_refresh = now
                        self.log(f"  [{name}] 获取m3u8成功，{len(current_ts_urls)}个分片")
                    else:
                        self.log(f"  [{name}] m3u8请求失败: HTTP {resp.status_code}, content={resp.text[:100]}")
                        time.sleep(5)
                        continue
                
                # 持续下载ts分片（每5秒一个，模拟播放）
                if current_ts_urls:
                    # 轮流下载ts分片
                    ts_url = current_ts_urls[play_count % len(current_ts_urls)]
                    if not ts_url.startswith("http"):
                        ts_url = f"{base_url}/{ts_url}"
                    try:
                        ts_resp = requests.get(ts_url, headers=headers, timeout=8, stream=True)
                        if ts_resp.status_code == 200:
                            # 下载前100KB（模拟播放，不完整下载）
                            ts_resp.raw.read(102400)
                            play_count += 1
                            if play_count % 12 == 0:  # 每分钟打印一次
                                self.log(f"  [{name}] 持续播放中，已下载{play_count}个分片")
                    except Exception:
                        pass
                
                # 模拟播放速度：每5秒一个ts分片（每个ts约1-3秒）
                time.sleep(5)
            except Exception as e:
                self.log(f"  [{name}] 播放线程异常: {e}")
                time.sleep(3)
        
        self.log(f"  [{name}] 播放线程已停止")

    def start_play_threads(self, selected_accounts, room_ids):
        """为每个账户启动持续播放线程"""
        self.play_threads = []
        for acc in selected_accounts:
            for rid in room_ids:
                t = threading.Thread(target=self.play_thread, args=(acc, rid), daemon=True)
                t.start()
                self.play_threads.append(t)
                time.sleep(0.5)  # 错开启动，避免同时请求

    def start_watch(self):
        if self.running:
            return
        room_input = self.room_combo.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请选择或输入直播间号")
            return
        # 解析多个直播间号（逗号、空格、分号分隔）
        room_ids = []
        for r in room_input.replace("，", ",").replace(";", ",").replace(" ", ",").split(","):
            r = r.strip()
            if r and r.isdigit():
                room_ids.append(r)
        if not room_ids:
            messagebox.showwarning("提示", "请输入有效的直播间号（数字），多个用逗号分隔")
            return
        # 从复选框获取选中账户
        selected_names = [name for name, var in self.account_vars.items() if var.get()]
        if not selected_names:
            messagebox.showwarning("提示", "请至少勾选一个账户")
            return
        selected_accounts = [acc for acc in self.account_mgr.accounts if acc.get("name", "") in selected_names]
        if not selected_accounts:
            messagebox.showwarning("提示", "未找到选中的账户")
            return
        self.running = True
        self.stop_flag = {"stop": False}
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.room_combo.config(state=tk.DISABLED)
        self.duration_combo.config(state=tk.DISABLED)
        self.interval_combo.config(state=tk.DISABLED)
        # 禁用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.DISABLED)
        self.select_all_btn.config(state=tk.DISABLED)
        self.deselect_all_btn.config(state=tk.DISABLED)
        self.account_stats = {}
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "play_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}
        room_display = ", ".join(room_ids)
        self.log(f"开始看播，直播间: {room_display}（共{len(room_ids)}个），账户: {len(selected_accounts)}个")
        self.log(f"目标时长: {self.duration_var.get()} 分钟，心跳间隔: {self.interval_var.get()} 秒")
        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
        self.watch_thread.start()

    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_combo.config(state="normal")
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()
        # 停止播放线程（stop_flag已设置，线程会自动退出）
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")

    def _watch_loop(self, room_ids, selected_accounts):
        import random
        base_interval = self.interval_var.get()
        target_seconds = self.duration_var.get() * 60
        # 进入所有直播间
        for acc in selected_accounts:
            if self.stop_flag["stop"]:
                break
            name = acc.get("name", "未知")
            entered_count = 0
            for rid in room_ids:
                if self.stop_flag["stop"]:
                    break
                self.log(f"  [{name}] 正在进入直播间 {rid}...")
                success, msg = self.enter_room(acc, rid)
                if success:
                    entered_count += 1
                    self.log(f"  [{name}] ✓ 直播间 {rid} {msg}")
                else:
                    self.log(f"  [{name}] ✗ 直播间 {rid} {msg}")
                time.sleep(random.uniform(0.5, 1.5))
            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
                self.account_stats[name]["ws_connected"] = False
                # 获取房间信息（浏览器加载页面时会调用）
                self.get_room_info(acc, room_ids[0])
                # 建立WebSocket弹幕连接（对第一个直播间建立连接，让账户出现在在线观众列表）
                if WEBSOCKET_AVAILABLE and room_ids:
                    self.log(f"  [{name}] 正在建立弹幕连接...")
                    ws_client = self.connect_ws_danmaku(acc, room_ids[0])
                    if ws_client:
                        self.ws_clients[name] = ws_client
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
        # 启动X25Kn观看心跳上报线程（v4.0.0核心功能：让B站统计系统认为在"观看"）
        self.log("启动X25Kn观看心跳上报...")
        # 获取房间区域信息（用第一个账户获取一次即可）
        area_id, parent_id, up_id = self.x25kn_get_area_info(selected_accounts[0], room_ids[0])
        self.log(f"  房间区域: parent_id={parent_id}, area_id={area_id}, up_id={up_id}")
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name)
            if not stats or stats["status"] != "观看中":
                continue
            self.x25kn_stop[name] = False
            t = threading.Thread(target=self.x25kn_thread_func,
                                 args=(acc, room_ids[0], area_id, parent_id, up_id, name),
                                 daemon=True)
            self.x25kn_threads[name] = t
            t.start()
            time.sleep(0.5)

        # 启动持续播放线程（模拟真实浏览器播放）
        self.log("启动持续播放线程...")
        self.start_play_threads(selected_accounts, room_ids)
        # 心跳循环
        while not self.stop_flag["stop"]:
            all_done = True
            for name, stats in self.account_stats.items():
                if stats["status"] == "观看中" and stats["watch_seconds"] < target_seconds:
                    all_done = False
                    break
            if all_done:
                self.log("所有账户已达到目标观看时长，自动停止")
                break
            interval = base_interval * random.uniform(0.8, 1.2)
            wait_segments = int(interval)
            for _ in range(wait_segments):
                if self.stop_flag["stop"]:
                    break
                time.sleep(1)
                for name, stats in self.account_stats.items():
                    if stats["status"] == "观看中":
                        stats["watch_seconds"] += 1
                if int(time.time()) % 10 == 0:
                    self.refresh_status_tree()
                # 每60秒检查一次弹幕连接状态
                if int(time.time()) % 60 == 0:
                    ws_connected = sum(1 for s in self.account_stats.values() if s.get("ws_connected", False))
                    ws_total = len(self.account_stats)
                    if ws_total > 0:
                        self.log(f"弹幕连接状态: {ws_connected}/{ws_total} 个在线")
                # 播放模拟已移到独立线程（持续播放）
            if self.stop_flag["stop"]:
                break
            for acc in selected_accounts:
                if self.stop_flag["stop"]:
                    break
                name = acc.get("name", "未知")
                stats = self.account_stats.get(name)
                if not stats or stats["status"] != "观看中":
                    continue
                if stats["watch_seconds"] >= target_seconds:
                    stats["status"] = "已完成"
                    self.log(f"  [{name}] ✓ 已达到目标时长 ({self.duration_var.get()}分钟)")
                    self.refresh_status_tree()
                    continue
                # 对每个直播间发送心跳
                for rid in room_ids:
                    if self.stop_flag["stop"]:
                        break
                    success, msg = self.send_heartbeat(acc, rid)
                    stats["heartbeat_count"] += 1
                    stats["last_heartbeat"] = datetime.now()
                    if not success:
                        self.log(f"  [{name}] 直播间{rid} 心跳失败: {msg}")
                    time.sleep(random.uniform(0.3, 0.8))
                # 播放模拟在独立线程中持续执行
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    watch_min = stats["watch_seconds"] // 60
                    self.log(f"  [{name}] 心跳累计 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)

    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        self.close_all_ws()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_combo.config(state="normal")
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        self.interval_combo.config(state="readonly")
        self.account_listbox.config(state=tk.NORMAL)
        self.refresh_status_tree()
        self.log("看播任务结束")


# ========== 主界面 ==========


# ========== 日程任务 ==========
class ScheduleFrame(tk.Frame):
    """日程任务：定时执行抢码/看播/发弹幕"""
    def __init__(self, parent, account_mgr, app):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.app = app  # DanmakuApp实例，用于访问其他页面
        self.account_mgr = account_mgr
        self.schedule_tasks = []
        self.scheduler_running = False
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = None
        self.selected_ids = set()  # 多选的任务ID集合
        self.schedule_presets = self.load_schedule_presets()  # 日程方案列表
        self.build_ui()
        self.load_schedule()
        self._load_form_settings()
        self.start_scheduler()

    def build_ui(self):
        # 顶部：添加任务卡片
        add_card = tk.Frame(self, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        add_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(add_card, text="➕ 添加日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        add_inner = tk.Frame(add_card, bg=COLORS["bg_card"])
        add_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：任务名称 + 类型
        row1 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_name_entry = DarkEntry(row1, width=20)
        self.task_name_entry.pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_type_var = tk.StringVar(value="rush")
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 类型切换时自动填名称+控制时间输入框
        self.task_type_var.trace_add("write", self._on_type_changed)

        # 第二行：执行时间
        row2 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)

        tk.Label(row2, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.schedule_hour = DarkEntry(row2, width=5)
        self.schedule_hour.insert(0, "20")
        self.schedule_hour.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.schedule_minute = DarkEntry(row2, width=5)
        self.schedule_minute.insert(0, "00")
        self.schedule_minute.pack(side=tk.LEFT, padx=(2, 10))
        self.time_hint_label = tk.Label(row2, text="（每天自动执行，使用各页面当前已设置的参数）", bg=COLORS["bg_card"],
                                         fg=COLORS["text_muted"], font=("微软雅黑", 8))
        self.time_hint_label.pack(side=tk.LEFT)

        # 第三行：添加按钮
        row3 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=(8, 0))

        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=160, height=40, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "✏ 编辑", command=self.edit_selected_task,
                   width=150, height=38, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "▶ 执行", command=self.run_selected_task,
                   width=150, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "☑ 全选", command=self.toggle_select_all,
                   width=150, height=38, bg_color="#9b59b6", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "⚡ 全部启用", command=self.enable_all_tasks,
                   width=140, height=38, bg_color="#e67e22", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 调度器状态
        self.scheduler_status_label = tk.Label(row3, text="● 调度器运行中", bg=COLORS["bg_card"],
                                                fg=COLORS["success"], font=("微软雅黑", 10, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        # 方案管理行
        preset_row = tk.Frame(add_inner, bg=COLORS["bg_card"])
        preset_row.pack(fill=tk.X, pady=(8, 0))

        tk.Label(preset_row, text="📦 方案管理:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)

        tk.Label(preset_row, text="方案名:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.preset_name_entry = DarkEntry(preset_row, width=15)
        self.preset_name_entry.pack(side=tk.LEFT)

        DarkButton(preset_row, "💾 保存方案", command=self.save_schedule_preset,
                   width=140, height=38, bg_color="#27ae60", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(preset_row, text="选择方案:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(15, 2))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var,
                                           values=[], state="readonly", width=15, font=("微软雅黑", 9))
        self.preset_combo.pack(side=tk.LEFT)

        DarkButton(preset_row, "📂 加载方案", command=self.load_schedule_preset,
                   width=140, height=38, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(preset_row, "🗑 删除方案", command=self.delete_schedule_preset,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        self._refresh_preset_combo()

        # 底部：任务列表 + 日志
        bottom = tk.Frame(self, bg=COLORS["bg_dark"])
        bottom.pack(fill=tk.BOTH, expand=True)

        # 左侧：任务列表
        list_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 日程任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        self.task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 右侧：日志
        log_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(log_card, text="📝 执行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 6))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(fill=tk.BOTH, expand=True)

        self.selected_task_id = None

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.schedule_log_text.config(state=tk.NORMAL)
        self.schedule_log_text.insert(tk.END, line)
        self.schedule_log_text.see(tk.END)
        self.schedule_log_text.config(state=tk.DISABLED)

    def sync_log_to_modules(self, msg):
        """将日志同步到所有相关模块页面"""
        try:
            # 同步到抢码页面
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)
        except:
            pass
        try:
            # 同步到看播页面
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)
        except:
            pass
        try:
            # 同步到弹幕页面（主页面日志）
            if hasattr(self.app, 'log'):
                self.app.log(msg)
        except:
            pass

    def _on_type_changed(self, *args):
        """类型切换时：自动填名称 + 控制时间输入框"""
        task_type = self.task_type_var.get()
        self._auto_fill_name(task_type)

        if task_type == "rush":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        elif task_type == "shutdown":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（关机时间在「定时关机」页面设置，此处无需填写）",
                                         fg=COLORS["warning"])
        else:
            self.schedule_hour.config(state=tk.NORMAL)
            self.schedule_minute.config(state=tk.NORMAL)
            self.time_hint_label.config(text="（每天自动执行，使用各页面当前已设置的参数）",
                                         fg=COLORS["text_muted"])

    def _auto_fill_name(self, task_type):
        """根据类型自动填写任务名称（看播1、看播2...）"""
        type_prefix = {
            "watch": "看播",
            "danmaku": "弹幕",
            "rush": "抢码",
            "shutdown": "关机",
        }
        prefix = type_prefix.get(task_type, "任务")
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        # 切换类型时强制更新名称（不管当前是什么）
        self.task_name_entry.delete(0, tk.END)
        self.task_name_entry.insert(0, auto_name)

    def add_schedule_task(self):
        name = self.task_name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入任务名称")
            return

        task_type = self.task_type_var.get()
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}

        if task_type == "rush":
            # 抢码不需要时间，添加后立即执行
            hour = -1
            minute = -1
            time_str = "立即执行"
        elif task_type == "shutdown":
            # 关机任务时间从关机页面读取，不在日程页面设置
            hour = -2
            minute = -2
            time_str = "关机页面设置"
        else:
            try:
                hour = int(self.schedule_hour.get().strip())
                minute = int(self.schedule_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
                return
            time_str = f"{hour:02d}:{minute:02d}"

        task = {
            "id": f"schedule_{int(time.time()*1000)}",
            "name": name,
            "type": task_type,
            "type_name": type_names[task_type],
            "hour": hour,
            "minute": minute,
            "time_str": time_str,
            "enabled": True,
            "last_run": "",
            "status": "等待中",
        }
        self.schedule_tasks.append(task)
        self.refresh_task_list()
        self.save_schedule()
        # 保存表单设置
        self._save_form_settings()

        if task_type == "rush":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，立即执行")
            # 抢码任务添加后立即执行
            self.after(100, lambda t=task: self.execute_task(t))
        elif task_type == "shutdown":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天按关机页面设置的时间执行")
        else:
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {time_str} 执行")

        # 添加后自动填下一个名称
        self._auto_fill_name(task_type)

    def refresh_task_list(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not self.schedule_tasks:
            tk.Label(self.task_list_frame, text="暂无日程任务，设置好参数后点击「+ 添加任务」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=30)
            return

        for idx, task in enumerate(self.schedule_tasks):
            is_selected = (task["id"] == self.selected_task_id)
            is_checked = (task["id"] in self.selected_ids)
            bg_color = COLORS["accent"] if is_selected else (COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            text_color = "#000000" if is_selected else COLORS["text_primary"]

            row_frame = tk.Frame(self.task_list_frame, bg=bg_color)
            row_frame.pack(fill=tk.X, pady=3)
            row_frame.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 选择复选框（多选）
            check_var = tk.BooleanVar(value=is_checked)
            def toggle_check(var=check_var, tid=task["id"]):
                if var.get():
                    self.selected_ids.add(tid)
                else:
                    self.selected_ids.discard(tid)
            check_chk = tk.Checkbutton(row_frame, variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                        fg=text_color, font=("微软雅黑", 8))
            check_chk.pack(side=tk.LEFT, padx=(4, 0), pady=8)


            # 任务名称（双击编辑）
            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)
            name_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))
            name_label.bind("<Double-Button-1>", lambda e, tid=task["id"]: self._edit_task_by_id(tid))

            # 类型
            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=6, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(4, 0))
            type_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 时间
            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(4, 0))
            time_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 状态
            if not task["enabled"]:
                status_text = "已取消"
                status_fg = COLORS["text_muted"]
            else:
                status_text = task.get("status", "等待中")
                if status_text == "执行中":
                    status_fg = COLORS["danger"]
                elif status_text in ["已完成", "已结束"]:
                    status_fg = COLORS["success"]
                elif "已结束" in status_text:
                    status_fg = COLORS["success"]
                elif status_text == "失败":
                    status_fg = COLORS["warning"]
                else:
                    status_fg = COLORS["text_muted"]
            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=7, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(4, 0))
            status_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 上次执行
            last_run = task.get("last_run", "-")
            if last_run and last_run != "-":
                try:
                    from datetime import datetime as _dt
                    _parsed = _dt.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    last_run = _parsed.strftime("%m-%d %H:%M")
                except:
                    pass
            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=12, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(4, 0))
            last_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))
            # 启用/取消按钮
            if task["enabled"]:
                btn_text = "取消"
                btn_bg = COLORS["warning"]
                def toggle_task(t=task):
                    t["enabled"] = False
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"⏸ 已取消日程「{t['name']}」")
            else:
                btn_text = "启用"
                btn_bg = COLORS["success"]
                def toggle_task(t=task):
                    t["enabled"] = True
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"✅ 已启用日程「{t['name']}」")
            toggle_btn = DarkButton(row_frame, btn_text, command=toggle_task,
                                     width=90, height=34, bg_color=btn_bg, text_color="#ffffff")
            toggle_btn.pack(side=tk.RIGHT, padx=(4, 4), pady=6)

    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def toggle_select_all(self):
        """全选/取消全选"""
        if len(self.selected_ids) == len(self.schedule_tasks):
            # 已全选，取消全选
            self.selected_ids.clear()
            self.log("☐ 已取消全选")
        else:
            # 全选
            self.selected_ids = {t["id"] for t in self.schedule_tasks}
            self.log(f"☑ 已全选 {len(self.schedule_tasks)} 个任务")
        self.refresh_task_list()

    def delete_selected_tasks(self):
        """批量删除勾选的任务"""
        if not self.selected_ids:
            messagebox.showwarning("提示", "请先勾选要删除的任务（每行左侧复选框）")
            return
        count = len(self.selected_ids)
        if custom_askyesno(self.app.root, "确认", f"确定删除选中的 {count} 个任务吗？"):
            names = [t["name"] for t in self.schedule_tasks if t["id"] in self.selected_ids]
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] not in self.selected_ids]
            if self.selected_task_id in self.selected_ids:
                self.selected_task_id = None
            self.selected_ids.clear()
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已批量删除 {count} 个任务: {', '.join(names)}")

    def toggle_select_all(self):
        """全选/取消全选"""
        if len(self.selected_ids) == len(self.schedule_tasks):
            # 已全选，取消全选
            self.selected_ids.clear()
            self.log("☐ 已取消全选")
        else:
            # 全选
            self.selected_ids = {t["id"] for t in self.schedule_tasks}
            self.log(f"☑ 已全选 {len(self.schedule_tasks)} 个任务")
        self.refresh_task_list()

    def delete_selected_tasks(self):
        """批量删除勾选的任务"""
        if not self.selected_ids:
            messagebox.showwarning("提示", "请先勾选要删除的任务（每行左侧复选框）")
            return
        count = len(self.selected_ids)
        if custom_askyesno(self.app.root, "确认", f"确定删除选中的 {count} 个任务吗？"):
            names = [t["name"] for t in self.schedule_tasks if t["id"] in self.selected_ids]
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] not in self.selected_ids]
            if self.selected_task_id in self.selected_ids:
                self.selected_task_id = None
            self.selected_ids.clear()
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已批量删除 {count} 个任务: {', '.join(names)}")

    def delete_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要删除的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task and custom_askyesno(self.app.root, "确认", f"确定删除任务「{task['name']}」吗？"):
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] != self.selected_task_id]
            self.selected_task_id = None
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已删除任务「{task['name']}」")

    def edit_selected_task(self):
        """编辑选中的日程任务"""
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要编辑的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if not task:
            return

        # 创建编辑窗口
        edit_win = tk.Toplevel(self.app.root)
        edit_win.title(f"编辑任务 - {task['name']}")
        edit_win.geometry("380x280")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.resizable(False, False)
        edit_win.attributes("-topmost", True)
        edit_win.grab_set()
        edit_win.update_idletasks()
        x = (edit_win.winfo_screenwidth() // 2) - 190
        y = (edit_win.winfo_screenheight() // 2) - 140
        edit_win.geometry(f"380x280+{x}+{y}")

        tk.Label(edit_win, text="✏ 编辑日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 14, "bold")).pack(pady=(15, 10))

        # 任务名称
        name_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        name_entry = DarkEntry(name_frame, width=22)
        name_entry.insert(0, task["name"])
        name_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 任务类型
        type_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        type_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(type_frame, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        edit_type_var = tk.StringVar(value=task["type"])
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}
        for val, label in type_names.items():
            ttk.Radiobutton(type_frame, text=label, variable=edit_type_var, value=val,
                            style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(6, 0))

        # 执行时间
        time_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        time_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(time_frame, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        hour_entry = DarkEntry(time_frame, width=5)
        hour_entry.insert(0, f"{task.get('hour', 20):02d}" if task.get("hour", -1) >= 0 else "20")
        hour_entry.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(time_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        minute_entry = DarkEntry(time_frame, width=5)
        minute_entry.insert(0, f"{task.get('minute', 0):02d}" if task.get("minute", -1) >= 0 else "00")
        minute_entry.pack(side=tk.LEFT, padx=(0, 0))
        time_hint = tk.Label(time_frame, text="", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                             font=("微软雅黑", 8))
        time_hint.pack(side=tk.LEFT, padx=(10, 0))

        def on_type_change(*args):
            if edit_type_var.get() == "rush":
                hour_entry.config(state=tk.DISABLED)
                minute_entry.config(state=tk.DISABLED)
                time_hint.config(text="（立即执行）", fg=COLORS["warning"])
            else:
                hour_entry.config(state=tk.NORMAL)
                minute_entry.config(state=tk.NORMAL)
                time_hint.config(text="")
        edit_type_var.trace_add("write", on_type_change)
        on_type_change()

        # 按钮
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(pady=(15, 10))

        def save_edit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("提示", "请输入任务名称", parent=edit_win)
                return
            new_type = edit_type_var.get()
            if new_type == "rush":
                new_hour = -1
                new_minute = -1
                new_time_str = "立即执行"
            else:
                try:
                    new_hour = int(hour_entry.get().strip())
                    new_minute = int(minute_entry.get().strip())
                    if not (0 <= new_hour <= 23 and 0 <= new_minute <= 59):
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("提示", "请输入有效的时间", parent=edit_win)
                    return
                new_time_str = f"{new_hour:02d}:{new_minute:02d}"

            task["name"] = new_name
            task["type"] = new_type
            task["type_name"] = type_names[new_type]
            task["hour"] = new_hour
            task["minute"] = new_minute
            task["time_str"] = new_time_str
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"✏ 已修改任务「{new_name}」({type_names[new_type]})，{new_time_str}")
            edit_win.destroy()

        DarkButton(btn_frame, "保存", command=save_edit,
                   width=150, height=34, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
        DarkButton(btn_frame, "取消", command=edit_win.destroy,
                   width=150, height=34, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    def _edit_task_by_id(self, task_id):
        """根据ID编辑任务（双击调用）"""
        self.selected_task_id = task_id
        self.refresh_task_list()
        self.edit_selected_task()

    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务")
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)

    def enable_all_tasks(self):
        """全部启用：让所有任务按设定时间执行（不立即执行）"""
        disabled_tasks = [t for t in self.schedule_tasks if not t["enabled"]]
        if not disabled_tasks:
            messagebox.showinfo("提示", "所有日程任务都已启用")
            return
        if not custom_askyesno(self.app.root, "确认", f"确定启用全部 {len(disabled_tasks)} 个已取消的日程任务吗？\n启用后任务将按设定时间自动执行"):
            return
        for task in disabled_tasks:
            task["enabled"] = True
        self.save_schedule()
        self.refresh_task_list()
        self.log(f"⚡ 已全部启用 {len(disabled_tasks)} 个日程任务，将按设定时间执行")

    def execute_task(self, task, manual=False):
        """执行指定任务"""
        task["status"] = "执行中"
        task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.refresh_task_list()

        prefix = "手动执行" if manual else "定时触发"
        msg = f"{'⚡' if manual else '⏰'} [日程] {prefix}任务「{task['name']}」({task['type_name']})"
        self.log(msg)
        # 同步到所有相关模块页面
        self.sync_log_to_modules(msg)

        try:
            if task["type"] == "watch":
                # 不跳转，直接后台启动看播
                self.app.root.after(100, lambda: self._start_watch_safe(task))
            elif task["type"] == "danmaku":
                # 不跳转，直接后台启动弹幕
                self.app.root.after(100, lambda: self._start_danmaku_safe(task))
            elif task["type"] == "rush":
                # 抢码任务不跳转，直接后台执行，等所有子任务结束才标记完成
                self.app.root.after(100, lambda: self._start_rush_safe(task))
                self.app.root.after(3000, lambda: self._monitor_rush_completion(task))
            elif task["type"] == "shutdown":
                # 执行关机（带确认）
                self.app.root.after(0, lambda: self._execute_shutdown_safe(task))

            # 标记完成：
            # - 抢码任务由监控线程处理
            # - 关机任务立即标记
            # - 弹幕和看播任务启动监控线程，等任务实际停止后标记
            if task["type"] == "shutdown":
                self.app.root.after(2000, lambda: self._mark_task_done(task))
            elif task["type"] in ["danmaku", "watch"]:
                self.app.root.after(3000, lambda: self._monitor_long_task(task))

        except Exception as e:
            task["status"] = "失败"
            self.refresh_task_list()
            self.log(f"✗ 任务「{task['name']}」执行失败: {e}")

    def _start_watch_safe(self, task):
        try:
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'start_watch'):
                self.app.watch_page.start_watch()
                msg = f"✓ [日程] 看播任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                # 同时写看播页面日志
                if hasattr(self.app.watch_page, 'log'):
                    self.app.watch_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动看播失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)

    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                msg = f"✓ [日程] 弹幕任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                # 同时写主页面日志（弹幕工具的日志）
                if hasattr(self.app, 'log'):
                    self.app.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动弹幕失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            if hasattr(self.app, 'log'):
                self.app.log(msg)

    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_all_scheduled_tasks'):
                self.app.rush_page.start_all_scheduled_tasks()
                msg = f"✓ [日程] 抢码任务「{task['name']}」已全部启动"
                self.log(msg)
                # 同时写抢码页面日志
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
            elif hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                msg = f"✓ [日程] 抢码监控「{task['name']}」已启动"
                self.log(msg)
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动抢码失败: {e}"
            self.log(msg)
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)

    def _execute_shutdown_safe(self, task):
        """执行关机任务（带确认弹窗，超时60秒自动关机）"""
        try:
            self.log(f"⏻ 关机任务「{task['name']}」已触发，弹出确认窗口...")
            # 创建确认对话框
            confirm_win = tk.Toplevel(self.app.root)
            confirm_win.title("关机确认")
            confirm_win.geometry("360x200")
            confirm_win.configure(bg=COLORS["bg_card"])
            confirm_win.resizable(False, False)
            # 置顶
            confirm_win.attributes("-topmost", True)
            confirm_win.grab_set()

            # 居中
            confirm_win.update_idletasks()
            x = (confirm_win.winfo_screenwidth() // 2) - 180
            y = (confirm_win.winfo_screenheight() // 2) - 100
            confirm_win.geometry(f"360x200+{x}+{y}")

            tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                     font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
            tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
            countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                       fg=COLORS["warning"], font=("微软雅黑", 12, "bold"))
            countdown_label.pack(pady=(8, 15))

            result = {"confirmed": False, "window": confirm_win}

            def confirm_shutdown():
                result["confirmed"] = True
                confirm_win.destroy()

            def cancel_shutdown():
                result["confirmed"] = False
                confirm_win.destroy()

            btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
            btn_frame.pack()
            DarkButton(btn_frame, "确认关机", command=confirm_shutdown,
                       width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
            DarkButton(btn_frame, "取消", command=cancel_shutdown,
                       width=140, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

            # 倒计时
            remaining = [60]
            def update_countdown():
                if remaining[0] > 0 and confirm_win.winfo_exists():
                    remaining[0] -= 1
                    countdown_label.config(text=f"{remaining[0]}秒后自动关机...")
                    confirm_win.after(1000, update_countdown)
                elif confirm_win.winfo_exists():
                    # 超时自动确认
                    result["confirmed"] = True
                    confirm_win.destroy()
            confirm_win.after(1000, update_countdown)

            # 等待对话框关闭
            self.app.root.wait_window(confirm_win)

            if result["confirmed"]:
                self.log(f"⏻ 确认关机，正在执行关机命令...")
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
            else:
                self.log(f"■ 关机任务「{task['name']}」已取消")
        except Exception as e:
            self.log(f"✗ 关机任务执行失败: {e}")

    def _monitor_rush_completion(self, task):
        """监控抢码子任务，等所有子任务结束后标记日程任务完成"""
        def monitor_loop():
            max_wait = 7200  # 最多等2小时
            waited = 0
            check_interval = 5  # 每5秒检查一次
            last_running_count = -1  # 记录上次的运行中数量，只在变化时写日志
            while waited < max_wait:
                try:
                    if not hasattr(self.app, 'rush_page') or not hasattr(self.app.rush_page, 'scheduled_tasks'):
                        break
                    rush_tasks = self.app.rush_page.scheduled_tasks
                    if not rush_tasks:
                        break
                    # 检查是否还有运行中或等待中的子任务
                    running = [t for t in rush_tasks if t.get("status") in ["运行中", "等待中"]]
                    if not running:
                        # 所有子任务都结束了
                        self.app.root.after(0, lambda: self._mark_rush_done(task))
                        return
                    # 只有在数量变化时才写日志，避免刷屏
                    if len(running) != last_running_count:
                        running_names = [t.get("task_name", "?") for t in running]
                        self.log(f"⏳ 抢码任务「{task['name']}」等待中，还有 {len(running)} 个子任务运行中: {', '.join(running_names[:3])}")
                        last_running_count = len(running)
                except Exception as e:
                    self.log(f"⚠ 抢码监控异常: {e}")
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_rush_done(task, timeout=True))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _mark_rush_done(self, task, timeout=False):
        """标记抢码任务完成"""
        if timeout:
            task["status"] = "已结束(超时)"
            self.log(f"⏰ 抢码任务「{task['name']}」监控超时(2小时)，标记为已结束")
        else:
            task["status"] = "已结束"
            self.log(f"✓ 抢码任务「{task['name']}」所有子任务已完成")
        self.refresh_task_list()
        self.save_schedule()

    def _monitor_long_task(self, task):
        """监控弹幕/看播等长时间运行任务，等任务实际停止后标记完成"""
        def monitor_loop():
            max_wait = 86400  # 最多等24小时
            waited = 0
            check_interval = 10  # 每10秒检查一次
            task_type = task["type"]
            while waited < max_wait:
                try:
                    is_running = False
                    if task_type == "danmaku":
                        # 检查弹幕发送状态
                        if hasattr(self.app, 'running'):
                            is_running = self.app.running
                    elif task_type == "watch":
                        # 检查看播状态
                        if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'running'):
                            is_running = self.app.watch_page.running
                    
                    if not is_running:
                        # 任务已停止，标记完成
                        msg = f"✓ [日程] {task['type_name']}任务「{task['name']}」已完成"
                        self.app.root.after(0, lambda: self._mark_task_done_with_log(task, msg))
                        return
                except Exception as e:
                    pass  # 监控异常不影响任务
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_task_done(task))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _mark_task_done_with_log(self, task, msg):
        """标记任务完成并写日志"""
        task["status"] = "已结束"
        self.log(msg)
        self.sync_log_to_modules(msg)
        self.refresh_task_list()
        self.save_schedule()

    def _mark_task_done(self, task):
        task["status"] = "已结束"
        self.refresh_task_list()
        self.save_schedule()

    def start_scheduler(self):
        """启动调度器"""
        if self.scheduler_running:
            return
        self.scheduler_running = True
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.scheduler_status_label.config(text="● 调度器运行中", fg=COLORS["success"])
        self.log("⏰ 日程调度器已启动")

    def _scheduler_loop(self):
        """调度器主循环：每秒检查一次，到点执行任务"""
        last_minute = -1
        warned_tasks = set()  # 已提前1分钟写过日志的任务ID
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    # 新的一分钟，清空已警告集合（用于第二天重复）
                    warned_tasks.clear()

                    for task in self.schedule_tasks:
                        if not task["enabled"]:
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        # 关机任务：动态从关机页面读取时间
                        if task["type"] == "shutdown" and task.get("hour", -1) == -2:
                            try:
                                if hasattr(self.app, 'shutdown_page') and self.app.shutdown_page:
                                    shutdown_hour = int(self.app.shutdown_page.shutdown_hour.get().strip())
                                    shutdown_minute = int(self.app.shutdown_page.shutdown_minute.get().strip())
                                    task_minute = shutdown_hour * 60 + shutdown_minute
                                else:
                                    continue
                            except (ValueError, AttributeError):
                                continue
                        else:
                            task_minute = task["hour"] * 60 + task["minute"]

                        # 抢码任务：提前1分钟写日志（如果不足1分钟则立即写）
                        if task["type"] == "rush":
                            time_diff = task_minute - current_minute
                            if time_diff <= 1 and task["id"] not in warned_tasks:
                                warned_tasks.add(task["id"])
                                warn_msg = f"⏳ [日程] 抢码任务「{task['name']}」将在 {task['time_str']} 执行，准备中..."
                                self.log(warn_msg)
                                self.sync_log_to_modules(warn_msg)

                        if task_minute == current_minute:
                            # 到点执行
                            self.app.root.after(0, lambda t=task: self.execute_task(t))
                            # 重置状态为等待中（明天再执行）
                            self.app.root.after(5000, lambda t=task: self._reset_task_status(t))

            except Exception as e:
                self.log(f"调度器异常: {e}")

            time.sleep(1)

    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if "已结束" in task.get("status", ""):
            task["status"] = "等待中"
            self.refresh_task_list()

    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_stop["stop"] = True
        self.scheduler_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=2)
        self.scheduler_status_label.config(text="● 调度器已停止", fg=COLORS["text_muted"])
        self.log("⏰ 日程调度器已停止")

    def save_schedule(self):
        """保存日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            # 只保存可序列化的字段
            save_data = []
            for task in self.schedule_tasks:
                save_data.append({
                    "id": task["id"],
                    "name": task["name"],
                    "type": task["type"],
                    "type_name": task["type_name"],
                    "hour": task["hour"],
                    "minute": task["minute"],
                    "time_str": task["time_str"],
                    "enabled": task["enabled"],
                    "last_run": task.get("last_run", ""),
                })
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_schedule_presets(self):
        """加载日程方案列表"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            if preset_file.exists():
                with open(preset_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载日程方案失败: {e}")
        return {}

    def save_schedule_presets_to_file(self):
        """保存日程方案列表到文件"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            with open(preset_file, "w", encoding="utf-8") as f:
                json.dump(self.schedule_presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"✗ 保存日程方案失败: {e}")

    def _refresh_preset_combo(self):
        """刷新方案下拉列表"""
        try:
            preset_names = list(self.schedule_presets.keys())
            self.preset_combo.config(values=preset_names)
            if preset_names and not self.preset_var.get():
                self.preset_var.set(preset_names[0])
        except Exception:
            pass

    def save_schedule_preset(self):
        """保存当前日程为方案"""
        preset_name = self.preset_name_entry.get().strip()
        if not preset_name:
            messagebox.showwarning("提示", "请输入方案名称")
            return

        # 深拷贝当前日程任务，避免后续修改影响方案
        import copy
        preset_data = {
            "name": preset_name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tasks": copy.deepcopy(self.schedule_tasks)
        }

        self.schedule_presets[preset_name] = preset_data
        self.save_schedule_presets_to_file()
        self._refresh_preset_combo()
        self.log(f"💾 已保存方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")

    def load_schedule_preset(self):
        """加载方案到当前日程"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要加载的方案")
            return

        # 确认是否覆盖当前日程
        if self.schedule_tasks:
            result = custom_askyesno(self.app.root, "确认", f"当前有 {len(self.schedule_tasks)} 个日程任务，加载方案将覆盖当前日程，是否继续？")
            if not result:
                return

        import copy
        preset_data = self.schedule_presets[preset_name]
        self.schedule_tasks = copy.deepcopy(preset_data["tasks"])

        # 重置任务状态
        for task in self.schedule_tasks:
            task["status"] = "等待中"
            task["last_run"] = ""
            task["enabled"] = task.get("enabled", True)

        self.save_schedule()
        self.refresh_task_list()
        self.log(f"📂 已加载方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")

    def delete_schedule_preset(self):
        """删除选中的方案"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要删除的方案")
            return

        result = custom_askyesno(self.app.root, "确认", f"确定要删除方案「{preset_name}」吗？")
        if not result:
            return

        del self.schedule_presets[preset_name]
        self.save_schedule_presets_to_file()
        self._refresh_preset_combo()
        self.preset_name_entry.delete(0, tk.END)
        self.log(f"🗑 已删除方案「{preset_name}」")

    def _save_form_settings(self):
        """保存表单设置（类型、时间）"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            settings = {
                "task_type": self.task_type_var.get(),
                "hour": self.schedule_hour.get(),
                "minute": self.schedule_minute.get(),
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_form_settings(self):
        """加载表单设置"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.task_type_var.set(settings.get("task_type", "watch"))
                h = settings.get("hour", "20")
                m = settings.get("minute", "00")
                self.schedule_hour.delete(0, tk.END)
                self.schedule_hour.insert(0, h)
                self.schedule_minute.delete(0, tk.END)
                self.schedule_minute.insert(0, m)
                # 触发类型切换回调
                self._on_type_changed()
        except Exception:
            pass

    def load_schedule(self):
        """加载日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    saved_tasks = json.load(f)
                for task in saved_tasks:
                    task["status"] = "等待中"
                    self.schedule_tasks.append(task)
                self.refresh_task_list()
                self.log(f"已加载 {len(saved_tasks)} 个日程任务")
        except Exception as e:
            self.log(f"加载日程配置失败: {e}")

    def on_close(self):
        """关闭时保存配置并停止调度器"""
        self.save_schedule()
        self._save_form_settings()
        self.stop_scheduler()


class DanmakuApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务")
        self.root.geometry("1800x1400")
        self.root.minsize(1500, 1100)
        self.root.configure(bg=COLORS["bg_dark"])

        self.account_mgr = AccountManager()
        self.danmaku_list = self.load_danmaku()
        self.config = self.load_config()
        self.running = False
        self.send_thread = None

        # 定时关机相关
        self.shutdown_mode = "none"  # none / scheduled / delay
        self.shutdown_thread = None
        self.shutdown_stop_flag = {"stop": False}
        self.shutdown_remaining = 0  # 剩余秒数
        self.shutdown_tasks = []  # 关机任务列表

        self.setup_styles()
        self.build_ui()
        self.refresh_account_list()
        self.refresh_danmaku_list()
        # 恢复上次选中的标签页
        saved_tab = self.config.get("current_tab", "rush")
        if saved_tab == "danmaku":
            self.switch_tab("danmaku")
        elif saved_tab == "shutdown":
            self.switch_tab("shutdown")
        elif saved_tab == "schedule":
            self.switch_tab("schedule")
        # 恢复上次选中的账户
        self.restore_selected_account()
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("程序启动，已加载 " + str(len(self.account_mgr.accounts)) + " 个账户，" + str(len(self.danmaku_list)) + " 条弹幕")
        self.log("数据目录: " + str(BASE_DIR))
        self.log("(配置文件已自动存到data子文件夹，不会铺满桌面)")

    def restore_selected_account(self):
        """恢复上次选中的账户"""
        saved_name = self.config.get("selected_account", "")
        if not saved_name:
            return
        for i, acc in enumerate(self.account_mgr.accounts):
            if acc.get("name", "") == saved_name:
                try:
                    self.account_listbox.selection_set(i)
                    self.account_listbox.see(i)
                    self.on_account_select(None)
                except Exception:
                    pass
                break

    def on_closing(self):
        """窗口关闭时保存所有配置"""
        try:
            self.save_config()
            self.save_danmaku_silent()
            # 保存抢码工具配置
            if hasattr(self, 'rush_page'):
                self.rush_page.on_close()
            # 保存看播任务配置
            if hasattr(self, 'watch_page'):
                self.watch_page.on_close()
            # 保存日程任务配置并停止调度器
            if hasattr(self, 'schedule_page'):
                self.schedule_page.on_close()
            # 取消定时关机
            self.cancel_shutdown()
            # 保存关机配置
            self.save_shutdown_config()
        except Exception:
            pass
        self.root.destroy()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=COLORS["bg_dark"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])
        style.configure("Dark.TLabel", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=("微软雅黑", 9))
        style.configure("Title.TLabel", background=COLORS["bg_card"], foreground=COLORS["accent"], font=("微软雅黑", 11, "bold"))
        style.configure("Dark.TRadiobutton", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=("微软雅黑", 9))
        style.configure("Dark.Horizontal.TScrollbar", background=COLORS["bg_input"], troughcolor=COLORS["bg_card"], bordercolor=COLORS["bg_card"], arrowcolor=COLORS["accent"])

    def build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg=COLORS["bg_card"])
        title_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(title_frame, text="● B站工具箱", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=(8, 0))

        self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.header_status.pack(side=tk.RIGHT, padx=20)

        # 标签切换栏
        tab_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=52)
        tab_bar.pack(fill=tk.X)
        tab_bar.pack_propagate(False)

        self.tab_rush = tk.Label(tab_bar, text="⚡ 抢码工具", bg=COLORS["accent"], fg="#000000",
                                  font=("微软雅黑", 12, "bold"), padx=24, pady=10, cursor="hand2")
        self.tab_rush.pack(side=tk.LEFT, padx=(15, 5), pady=6)
        self.tab_rush.bind("<Button-1>", lambda e: self.switch_tab("rush"))

        self.tab_danmaku = tk.Label(tab_bar, text="💬 弹幕工具", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_danmaku.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_danmaku.bind("<Button-1>", lambda e: self.switch_tab("danmaku"))

        self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_shutdown.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_shutdown.bind("<Button-1>", lambda e: self.switch_tab("shutdown"))

        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))

        self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))

        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        # 主内容区（标签页容器）
        self.tab_container = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.tab_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 弹幕工具页面
        self.danmaku_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.danmaku_page.pack(fill=tk.BOTH, expand=True)
        self.danmaku_page.pack_forget()

        # 抢码工具页面
        self.rush_page = RushRewardFrame(self.tab_container, self.account_mgr)
        self.rush_page.pack(fill=tk.BOTH, expand=True)

        # 定时关机页面
        self.shutdown_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.shutdown_page.pack(fill=tk.BOTH, expand=True)
        self.shutdown_page.pack_forget()
        self.build_shutdown_page()

        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        # 日程任务页面
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

        self.current_tab = "rush"

        # 左侧：账户管理
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)

        tk.Label(left_card, text="账户管理", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)

        self.account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                           selectbackground=COLORS["accent"], selectforeground="#000000",
                                           font=("微软雅黑", 9), bd=0, highlightthickness=0,
                                           activestyle="none", exportselection=False)
        self.account_listbox.pack(fill=tk.BOTH, expand=True)
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)

        # 第一排：添加账户
        DarkButton(left_card, "+ 添加账户", command=self.add_account,
                   width=250, height=36).pack(pady=(10, 6), padx=12)

        # 第二排：删除
        DarkButton(left_card, "删除", command=self.delete_account,
                   width=250, height=36, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6), padx=12)

        # 第三排：验证登录
        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=250, height=36, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 12), padx=12)

        # 右侧：设置 + 弹幕 + 日志
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))

        tk.Label(settings_card, text="发送设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行
        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="直播间号", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=14)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="发送间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.interval_min = DarkEntry(row1, width=5)
        self.interval_min.insert(0, "5")
        self.interval_min.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row1, text="-", bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(side=tk.LEFT)
        self.interval_max = DarkEntry(row1, width=5)
        self.interval_max.insert(0, "10")
        self.interval_max.pack(side=tk.LEFT, padx=(4, 20))

        tk.Label(row1, text="模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="random")
        ttk.Radiobutton(row1, text="随机", variable=self.mode_var, value="random", style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="顺序", variable=self.mode_var, value="sequence", style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 第二行：发送账户模式
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)

        tk.Label(row2, text="账户模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.account_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(row2, text="单账户", variable=self.account_mode_var, value="single", style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row2, text="多账户轮流", variable=self.account_mode_var, value="rotate", style="Dark.TRadiobutton").pack(side=tk.LEFT)
        tk.Label(row2, text="（所有账户依次轮流发）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(8, 0))

        # 第三行：发送条数限制
        row3 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=3)

        tk.Label(row3, text="发送限制", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.max_send_entry = DarkEntry(row3, width=8)
        self.max_send_entry.insert(0, "0")
        self.max_send_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row3, text="条后停止（0=不限制）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # ===== 底部容器：日志 + 控制栏（固定高度，先pack到BOTTOM）=====
        bottom_container = tk.Frame(right, bg=COLORS["bg_dark"])
        bottom_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        # 日志卡片（固定高度160px）
        log_card = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        log_card.pack_propagate(False)
        log_card.configure(height=160)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 控制栏（两排布局，固定高度100px）
        danmaku_ctrl = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X)
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=100)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

        # 第一排：按钮
        btn_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X)

        self.start_btn = DarkButton(btn_row, "▶ 启动发送", command=self.start_sending,
                                     width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = DarkButton(btn_row, "■ 停止发送", command=self.stop_sending,
                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.stop_btn.set_state("disabled")

        # 第二排：状态标签
        status_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        status_row.pack(fill=tk.X, pady=(6, 0))

        self.status_label = tk.Label(status_row, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.LEFT)

        # ===== 中间：弹幕列表卡片（expand=True，占据剩余空间）=====
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))

        # 第一排：标题
        header_row1 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row1.pack(fill=tk.X)
        tk.Label(header_row1, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)

        # 第二排：按钮
        header_row2 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row2.pack(fill=tk.X, pady=(6, 0))
        DarkButton(header_row2, "+ 添加", command=self.add_single_danmaku,
                   width=130, height=36, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(header_row2, "批量生成", command=self.batch_generate_danmaku,
                   width=150, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(header_row2, "保存列表", command=self.save_danmaku,
                   width=140, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 三列弹幕列表（使用grid布局，三列平均分配宽度）
        columns_frame = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 设置三列等宽
        for i in range(3):
            columns_frame.grid_columnconfigure(i, weight=1, uniform="column")

        self.danmaku_texts = []
        for i in range(3):
            col_frame = tk.Frame(columns_frame, bg=COLORS["bg_card"])
            col_frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
            col_frame.grid_rowconfigure(1, weight=1)
            col_frame.grid_columnconfigure(0, weight=1)

            # 列标题
            tk.Label(col_frame, text=f"第{i+1}列", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 8)).grid(row=0, column=0, sticky="w", pady=(0, 2))

            text_with_scroll = tk.Frame(col_frame, bg=COLORS["bg_card"])
            text_with_scroll.grid(row=1, column=0, sticky="nsew")
            text_with_scroll.grid_rowconfigure(0, weight=1)
            text_with_scroll.grid_columnconfigure(0, weight=1)

            text_widget = tk.Text(text_with_scroll, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                  insertbackground=COLORS["accent"], font=("微软雅黑", 9),
                                  bd=0, highlightthickness=0, wrap=tk.WORD, width=20)
            text_widget.grid(row=0, column=0, sticky="nsew")
            self.danmaku_texts.append(text_widget)

        # 加载保存的配置
        self.apply_config()

    # ---------- 账户管理 ----------
    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"  {acc['name']}"
            self.account_listbox.insert(tk.END, display)

    def on_account_select(self, event):
        selection = self.account_listbox.curselection()
        if not selection:
            return
        acc = self.account_mgr.accounts[selection[0]]
        # 保存当前选中的账户
        self.save_config()

    def get_current_account(self):
        selection = self.account_listbox.curselection()
        if not selection:
            return None
        return self.account_mgr.accounts[selection[0]]

    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()

    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        if custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.log(f"已删除账户: {acc['name']}")

    def verify_current_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择账户")
            return
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        ok, msg = verify_login(cookie_str)
        if ok:
            messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}")
            self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
        else:
            messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}")
            self.log(f"账户「{acc['name']}」验证失败: {msg}")

    def switch_tab(self, tab_name):
        """切换标签页"""
        if tab_name == self.current_tab:
            return

        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))

        if tab_name == "danmaku":
            self.danmaku_page.pack(fill=tk.BOTH, expand=True)
            self.tab_danmaku.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "danmaku"
        elif tab_name == "rush":
            self.rush_page.pack(fill=tk.BOTH, expand=True)
            self.tab_rush.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "rush"
            # 切换到抢码工具时刷新账户列表
            self.rush_page.refresh_account_list()
        elif tab_name == "shutdown":
            self.shutdown_page.pack(fill=tk.BOTH, expand=True)
            self.tab_shutdown.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "shutdown"
            # 刷新关机任务列表
            self.refresh_shutdown_task_list()
        elif tab_name == "watch":
            self.watch_page.pack(fill=tk.BOTH, expand=True)
            self.tab_watch.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "watch"
            # 切换到看播任务时刷新账户列表
            self.watch_page.refresh_account_list()
        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"
        # 保存当前标签页
        self.save_config()

    # ========== 定时关机页面 ==========
    def build_shutdown_page(self):
        """构建定时关机页面"""
        # 主容器
        main = tk.Frame(self.shutdown_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # 顶部：关机设置卡片
        setup_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        setup_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(setup_card, text="⏻ 定时关机设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        setup_content = tk.Frame(setup_card, bg=COLORS["bg_card"])
        setup_content.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 关机模式选择
        mode_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        mode_frame.pack(fill=tk.X, pady=4)
        tk.Label(mode_frame, text="关机模式:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.shutdown_mode_var = tk.StringVar(value="none")
        tk.Radiobutton(mode_frame, text="不关机", variable=self.shutdown_mode_var, value="none",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=("微软雅黑", 10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))
        tk.Radiobutton(mode_frame, text="定时关机", variable=self.shutdown_mode_var, value="scheduled",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=("微软雅黑", 10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))
        tk.Radiobutton(mode_frame, text="延时关机", variable=self.shutdown_mode_var, value="delay",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=("微软雅黑", 10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))

        # 定时关机时间设置
        self.scheduled_shutdown_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        self.scheduled_shutdown_frame.pack(fill=tk.X, pady=4)
        tk.Label(self.scheduled_shutdown_frame, text="关机时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.shutdown_hour = DarkEntry(self.scheduled_shutdown_frame, width=5)
        self.shutdown_hour.insert(0, "23")
        self.shutdown_hour.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(self.scheduled_shutdown_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.shutdown_minute = DarkEntry(self.scheduled_shutdown_frame, width=5)
        self.shutdown_minute.insert(0, "00")
        self.shutdown_minute.pack(side=tk.LEFT, padx=(2, 10))
        tk.Label(self.scheduled_shutdown_frame, text="（如果时间已过，将在第二天同一时间关机）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(side=tk.LEFT)

        # 延时关机时间设置
        self.delay_shutdown_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        self.delay_shutdown_frame.pack(fill=tk.X, pady=4)
        tk.Label(self.delay_shutdown_frame, text="延时分钟:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.shutdown_delay = DarkEntry(self.delay_shutdown_frame, width=8)
        self.shutdown_delay.insert(0, "60")
        self.shutdown_delay.pack(side=tk.LEFT, padx=(10, 10))
        tk.Label(self.delay_shutdown_frame, text="分钟后关机", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)

        # 任务名称
        name_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, pady=4)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.shutdown_task_name = DarkEntry(name_frame, width=30)
        self.shutdown_task_name.insert(0, "定时关机任务")
        self.shutdown_task_name.pack(side=tk.LEFT, padx=(10, 0))

        # 控制按钮
        btn_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        self.add_shutdown_task_btn = DarkButton(btn_frame, "+ 添加关机任务", command=self.add_shutdown_task,
                                                  width=160, height=40, bg_color=COLORS["accent"], text_color="#000000")
        self.add_shutdown_task_btn.pack(side=tk.LEFT)
        self.cancel_all_shutdown_btn = DarkButton(btn_frame, "■ 取消全部任务", command=self.cancel_all_shutdown,
                                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.cancel_all_shutdown_btn.pack(side=tk.LEFT, padx=(10, 0))

        # 当前状态显示
        status_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        status_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(status_frame, text="当前状态:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.shutdown_status_label = tk.Label(status_frame, text="● 无运行中的关机任务", bg=COLORS["bg_card"],
                                               fg=COLORS["text_muted"], font=("微软雅黑", 10, "bold"))
        self.shutdown_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # 初始隐藏定时和延时设置
        self.scheduled_shutdown_frame.pack_forget()
        self.delay_shutdown_frame.pack_forget()

        # 底部：关机任务列表卡片
        list_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(fill=tk.BOTH, expand=True)

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 关机任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（点击「取消」可单独取消某个任务）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        # 任务列表容器
        self.shutdown_task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.shutdown_task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 加载关机配置
        self.load_shutdown_config()

    def on_shutdown_mode_change(self):
        """关机模式切换时显示/隐藏对应的设置"""
        mode = self.shutdown_mode_var.get()
        if mode == "scheduled":
            self.scheduled_shutdown_frame.pack(fill=tk.X, pady=4)
            self.delay_shutdown_frame.pack_forget()
        elif mode == "delay":
            self.delay_shutdown_frame.pack(fill=tk.X, pady=4)
            self.scheduled_shutdown_frame.pack_forget()
        else:
            self.scheduled_shutdown_frame.pack_forget()
            self.delay_shutdown_frame.pack_forget()
        self.save_shutdown_config()

    def add_shutdown_task(self):
        """添加关机任务"""
        mode = self.shutdown_mode_var.get()
        if mode == "none":
            messagebox.showwarning("提示", "请先选择关机模式（定时关机或延时关机）")
            return

        task_name = self.shutdown_task_name.get().strip() or "定时关机任务"

        # 计算关机时间
        now = datetime.now()
        if mode == "scheduled":
            try:
                hour = int(self.shutdown_hour.get().strip())
                minute = int(self.shutdown_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）")
                return
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)
            delay_seconds = (target_time - now).total_seconds()
            time_desc = f"{hour:02d}:{minute:02d}"
        elif mode == "delay":
            try:
                delay_minutes = float(self.shutdown_delay.get().strip())
                if delay_minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的延时分钟数（大于0）")
                return
            delay_seconds = delay_minutes * 60
            target_time = now + timedelta(seconds=delay_seconds)
            time_desc = f"{delay_minutes}分钟后"

        # 创建任务
        task_id = f"shutdown_{int(time.time()*1000)}"
        task = {
            "id": task_id,
            "name": task_name,
            "mode": mode,
            "time_desc": time_desc,
            "target_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
            "delay_seconds": int(delay_seconds),
            "remaining": int(delay_seconds),
            "status": "等待中",
            "stop_flag": {"stop": False},
            "thread": None,
        }

        # 启动任务线程
        task["thread"] = threading.Thread(
            target=self.shutdown_task_worker,
            args=(task,),
            daemon=True
        )
        task["thread"].start()

        self.shutdown_tasks.append(task)
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()
        self.log(f"⏻ 已添加关机任务「{task_name}」，将在 {time_desc} 关机（{target_time.strftime('%Y-%m-%d %H:%M:%S')}）")

    def shutdown_task_worker(self, task):
        """关机任务工作线程"""
        try:
            start_time = time.time()
            total_seconds = task["delay_seconds"]
            while time.time() - start_time < total_seconds:
                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    return
                remaining = int(total_seconds - (time.time() - start_time))
                task["remaining"] = remaining
                task["status"] = "倒计时中"
                self.root.after(0, self.refresh_shutdown_task_list)
                self.root.after(0, self.update_shutdown_status)
                time.sleep(1)

            # 时间到，弹出确认窗口
            if not task["stop_flag"]["stop"]:
                task["status"] = "待确认"
                self.root.after(0, self.refresh_shutdown_task_list)
                self.log(f"⏻ 任务「{task['name']}」时间到，弹出关机确认窗口...")

                # 在UI线程弹出确认对话框
                confirm_result = {"confirmed": False, "done": False}

                def show_confirm_dialog():
                    try:
                        confirm_win = tk.Toplevel(self.root)
                        confirm_win.title("关机确认")
                        confirm_win.geometry("360x200")
                        confirm_win.configure(bg=COLORS["bg_card"])
                        confirm_win.resizable(False, False)
                        confirm_win.attributes("-topmost", True)
                        confirm_win.grab_set()
                        confirm_win.update_idletasks()
                        x = (confirm_win.winfo_screenwidth() // 2) - 180
                        y = (confirm_win.winfo_screenheight() // 2) - 100
                        confirm_win.geometry(f"360x200+{x}+{y}")

                        tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                                 font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
                        tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                                 fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
                        countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                                   fg=COLORS["warning"], font=("微软雅黑", 12, "bold"))
                        countdown_label.pack(pady=(8, 15))

                        def do_confirm():
                            confirm_result["confirmed"] = True
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        def do_cancel():
                            confirm_result["confirmed"] = False
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
                        btn_frame.pack()
                        DarkButton(btn_frame, "确认关机", command=do_confirm,
                                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
                        DarkButton(btn_frame, "取消", command=do_cancel,
                                   width=140, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

                        remaining = [60]
                        def tick():
                            if remaining[0] > 0 and confirm_win.winfo_exists():
                                remaining[0] -= 1
                                countdown_label.config(text=f"{remaining[0]}秒后自动关机...")
                                confirm_win.after(1000, tick)
                            elif confirm_win.winfo_exists():
                                confirm_result["confirmed"] = True
                                confirm_result["done"] = True
                                confirm_win.destroy()
                        confirm_win.after(1000, tick)

                        self.root.wait_window(confirm_win)
                    except Exception as e:
                        confirm_result["confirmed"] = True  # 弹窗失败则直接关机
                        confirm_result["done"] = True

                self.after(0, show_confirm_dialog)

                # 等待确认结果（最多等90秒）
                wait_count = 0
                while not confirm_result["done"] and wait_count < 90:
                    if task["stop_flag"]["stop"]:
                        break
                    time.sleep(1)
                    wait_count += 1

                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.after(0, self.refresh_shutdown_task_list)
                    return

                if confirm_result["confirmed"]:
                    task["status"] = "执行中"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.log(f"⏻ 确认关机，正在执行关机命令...")
                    time.sleep(1)
                    import subprocess
                    subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
                else:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    self.log(f"■ 关机任务「{task['name']}」已取消")
        except Exception as e:
            task["status"] = "异常"
            self.log(f"✗ 关机任务「{task['name']}」异常: {e}")
            self.root.after(0, self.refresh_shutdown_task_list)
            self.root.after(0, self.update_shutdown_status)

    def cancel_shutdown_task(self, task_id):
        """取消单个关机任务"""
        for task in self.shutdown_tasks:
            if task["id"] == task_id:
                task["stop_flag"]["stop"] = True
                task["status"] = "已取消"
                if task["thread"] and task["thread"].is_alive():
                    task["thread"].join(timeout=2)
                self.log(f"■ 已取消关机任务「{task['name']}」")
                break
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def cancel_all_shutdown(self):
        """取消所有关机任务"""
        if not self.shutdown_tasks:
            messagebox.showinfo("提示", "当前没有运行中的关机任务")
            return
        for task in self.shutdown_tasks:
            if task["status"] in ["等待中", "倒计时中"]:
                task["stop_flag"]["stop"] = True
                task["status"] = "已取消"
                if task["thread"] and task["thread"].is_alive():
                    task["thread"].join(timeout=2)
        self.log("■ 已取消所有关机任务")
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def cancel_shutdown(self):
        """取消所有关机（用于程序关闭时）"""
        for task in self.shutdown_tasks:
            task["stop_flag"]["stop"] = True
            if task["thread"] and task["thread"].is_alive():
                task["thread"].join(timeout=1)

    def refresh_shutdown_task_list(self):
        """刷新关机任务列表显示"""
        # 清空现有内容
        for widget in self.shutdown_task_list_frame.winfo_children():
            widget.destroy()

        if not self.shutdown_tasks:
            tk.Label(self.shutdown_task_list_frame, text="暂无关机任务，设置好参数后点击「+ 添加关机任务」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=30)
            return

        for idx, task in enumerate(self.shutdown_tasks):
            row_frame = tk.Frame(self.shutdown_task_list_frame, bg=COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            row_frame.pack(fill=tk.X, pady=3)

            # 任务名称
            name_label = tk.Label(row_frame, text=task["name"], bg=row_frame["bg"], fg=COLORS["text_primary"],
                                  font=("微软雅黑", 10, "bold"), width=20, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(10, 0), pady=8)

            # 关机时间
            time_label = tk.Label(row_frame, text=task["time_desc"], bg=row_frame["bg"], fg=COLORS["text_secondary"],
                                  font=("微软雅黑", 9), width=15, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(10, 0))

            # 目标时间
            target_label = tk.Label(row_frame, text=task["target_time"], bg=row_frame["bg"], fg=COLORS["text_muted"],
                                    font=("微软雅黑", 9), width=20, anchor=tk.W)
            target_label.pack(side=tk.LEFT, padx=(10, 0))

            # 倒计时/状态
            if task["status"] == "倒计时中":
                hours = task["remaining"] // 3600
                minutes = (task["remaining"] % 3600) // 60
                seconds = task["remaining"] % 60
                if hours > 0:
                    countdown_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    countdown_str = f"{minutes:02d}:{seconds:02d}"
                status_label = tk.Label(row_frame, text=f"⏳ {countdown_str}", bg=row_frame["bg"], fg=COLORS["warning"],
                                        font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)
            elif task["status"] == "已取消":
                status_label = tk.Label(row_frame, text="■ 已取消", bg=row_frame["bg"], fg=COLORS["text_muted"],
                                        font=("微软雅黑", 9), width=12, anchor=tk.W)
            elif task["status"] == "执行中":
                status_label = tk.Label(row_frame, text="⚡ 执行中", bg=row_frame["bg"], fg=COLORS["danger"],
                                        font=("微软雅黑", 10, "bold"), width=12, anchor=tk.W)
            else:
                status_label = tk.Label(row_frame, text=f"● {task['status']}", bg=row_frame["bg"], fg=COLORS["text_muted"],
                                        font=("微软雅黑", 9), width=12, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(10, 0))

            # 取消按钮
            if task["status"] in ["等待中", "倒计时中"]:
                cancel_btn = DarkButton(row_frame, "取消", command=lambda tid=task["id"]: self.cancel_shutdown_task(tid),
                                        width=90, height=28, bg_color=COLORS["danger"], text_color="#ffffff")
                cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))

            # 删除按钮（已取消/已完成的任务可以删除）
            if task["status"] in ["已取消", "执行中"]:
                delete_btn = DarkButton(row_frame, "删除", command=lambda tid=task["id"]: self.delete_shutdown_task(tid),
                                        width=90, height=28, bg_color="#444466", text_color="#ffffff")
                delete_btn.pack(side=tk.RIGHT, padx=(0, 5))

    def delete_shutdown_task(self, task_id):
        """删除关机任务"""
        self.shutdown_tasks = [t for t in self.shutdown_tasks if t["id"] != task_id]
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def update_shutdown_status(self):
        """更新关机状态显示"""
        running_tasks = [t for t in self.shutdown_tasks if t["status"] in ["等待中", "倒计时中"]]
        if running_tasks:
            # 找到最近的一个任务
            nearest = min(running_tasks, key=lambda t: t["remaining"])
            hours = nearest["remaining"] // 3600
            minutes = (nearest["remaining"] % 3600) // 60
            seconds = nearest["remaining"] % 60
            if hours > 0:
                countdown_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                countdown_str = f"{minutes:02d}:{seconds:02d}"
            self.shutdown_status_label.config(text=f"● {len(running_tasks)}个任务运行中，最近: {countdown_str}", fg=COLORS["warning"])
        else:
            self.shutdown_status_label.config(text="● 无运行中的关机任务", fg=COLORS["text_muted"])

    def save_shutdown_config(self):
        """保存关机配置"""
        try:
            config = {
                "shutdown_mode": self.shutdown_mode_var.get(),
                "shutdown_hour": self.shutdown_hour.get().strip(),
                "shutdown_minute": self.shutdown_minute.get().strip(),
                "shutdown_delay": self.shutdown_delay.get().strip(),
                "task_name": self.shutdown_task_name.get().strip(),
            }
            shutdown_config_file = BASE_DIR / "shutdown_config.json"
            with open(shutdown_config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_shutdown_config(self):
        """加载关机配置"""
        try:
            shutdown_config_file = BASE_DIR / "shutdown_config.json"
            if shutdown_config_file.exists():
                with open(shutdown_config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if config.get("shutdown_mode"):
                    self.shutdown_mode_var.set(config["shutdown_mode"])
                    self.on_shutdown_mode_change()
                if config.get("shutdown_hour"):
                    self.shutdown_hour.delete(0, tk.END)
                    self.shutdown_hour.insert(0, config["shutdown_hour"])
                if config.get("shutdown_minute"):
                    self.shutdown_minute.delete(0, tk.END)
                    self.shutdown_minute.insert(0, config["shutdown_minute"])
                if config.get("shutdown_delay"):
                    self.shutdown_delay.delete(0, tk.END)
                    self.shutdown_delay.insert(0, config["shutdown_delay"])
                if config.get("task_name"):
                    self.shutdown_task_name.delete(0, tk.END)
                    self.shutdown_task_name.insert(0, config["task_name"])
        except Exception:
            pass

    # ---------- 配置管理 ----------
    def load_config(self):
        default_config = {
            "room_id": "1791983148",
            "interval_min": "5",
            "interval_max": "10",
            "send_mode": "random",
            "account_mode": "single",
            "send_limit": "0",
            "selected_account": "",
            "current_tab": "rush",
            "window_geometry": "",
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default_config.update(cfg)
            except Exception:
                pass
        return default_config

    def save_config(self):
        try:
            self.config["room_id"] = self.room_entry.get().strip()
            self.config["interval_min"] = self.interval_min.get().strip()
            self.config["interval_max"] = self.interval_max.get().strip()
            self.config["send_mode"] = self.mode_var.get()
            self.config["account_mode"] = self.account_mode_var.get()
            self.config["send_limit"] = self.max_send_entry.get().strip()
            self.config["current_tab"] = self.current_tab
            self.config["window_geometry"] = self.root.geometry()
            # 保存当前选中的账户
            try:
                selection = self.account_listbox.curselection()
                if selection:
                    idx = selection[0]
                    if idx < len(self.account_mgr.accounts):
                        self.config["selected_account"] = self.account_mgr.accounts[idx].get("name", "")
            except Exception:
                pass
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def apply_config(self):
        if self.config.get("room_id"):
            self.room_entry.insert(0, self.config["room_id"])
        if self.config.get("interval_min"):
            self.interval_min.delete(0, tk.END)
            self.interval_min.insert(0, self.config["interval_min"])
        if self.config.get("interval_max"):
            self.interval_max.delete(0, tk.END)
            self.interval_max.insert(0, self.config["interval_max"])
        if self.config.get("send_mode"):
            self.mode_var.set(self.config["send_mode"])
        if self.config.get("account_mode"):
            self.account_mode_var.set(self.config["account_mode"])
        if self.config.get("send_limit"):
            self.max_send_entry.delete(0, tk.END)
            self.max_send_entry.insert(0, self.config["send_limit"])
        # 恢复窗口大小和位置（如果保存的大小太小则用新默认值）
        if self.config.get("window_geometry"):
            try:
                geom = self.config["window_geometry"]
                # 解析宽度，如果小于1200则用新默认值
                width_str = geom.split("x")[0]
                if width_str.isdigit() and int(width_str) >= 1500:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1800x1400")
            except Exception:
                self.root.geometry("1400x1000")
        # 绑定自动保存
        self.room_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_min.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_max.bind("<FocusOut>", lambda e: self.save_config())
        self.max_send_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.mode_var.trace_add("write", lambda *a: self.save_config())
        self.account_mode_var.trace_add("write", lambda *a: self.save_config())
        # 窗口大小变化时保存
        self.root.bind("<Configure>", lambda e: self.save_config() if e.widget == self.root else None)

    # ---------- 弹幕列表（三列） ----------
    def get_all_danmaku(self):
        """从三列中获取所有弹幕，按列顺序合并"""
        all_lines = []
        for text_widget in self.danmaku_texts:
            content = text_widget.get("1.0", tk.END).strip()
            if content:
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                all_lines.extend(lines)
        return all_lines

    def distribute_danmaku_to_columns(self, danmaku_list):
        """把弹幕列表平均分配到三列"""
        # 清空所有列
        for text_widget in self.danmaku_texts:
            text_widget.delete("1.0", tk.END)

        if not danmaku_list:
            return

        # 计算每列的数量
        total = len(danmaku_list)
        col_count = (total + 2) // 3  # 向上取整

        # 分配到三列
        for i in range(3):
            start = i * col_count
            end = min(start + col_count, total)
            if start < total:
                column_lines = danmaku_list[start:end]
                self.danmaku_texts[i].insert("1.0", "\n".join(column_lines))

    def add_single_danmaku(self):
        text = simpledialog.askstring("添加弹幕", "请输入弹幕内容：", parent=self.root)
        if text and text.strip():
            text = text.strip()
            # 获取当前所有弹幕
            all_danmaku = self.get_all_danmaku()
            all_danmaku.append(text)
            # 重新分配到三列
            self.distribute_danmaku_to_columns(all_danmaku)
            self.danmaku_list = all_danmaku
            self.save_danmaku()
            self.log(f"已添加弹幕: {text}")

    def batch_generate_danmaku(self):
        count = simpledialog.askinteger("批量生成弹幕", "请输入生成数量（1-100）：",
                                         parent=self.root, minvalue=1, maxvalue=100, initialvalue=20)
        if not count:
            return
        if count > len(DANMAKU_POOL):
            count = len(DANMAKU_POOL)
        selected = random.sample(DANMAKU_POOL, count)
        # 获取当前所有弹幕
        all_danmaku = self.get_all_danmaku()
        all_danmaku.extend(selected)
        # 重新分配到三列
        self.distribute_danmaku_to_columns(all_danmaku)
        self.danmaku_list = all_danmaku
        self.save_danmaku()
        self.log(f"批量生成 {count} 条弹幕，当前共 {len(all_danmaku)} 条")

    def load_danmaku(self):
        if DANMAKU_FILE.exists():
            with open(DANMAKU_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return ["666", "主播好强", "来了来了", "哈哈哈哈", "学到了"]

    def save_danmaku(self):
        all_danmaku = self.get_all_danmaku()
        with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(all_danmaku))
        self.danmaku_list = all_danmaku
        self.log(f"弹幕列表已保存，共 {len(all_danmaku)} 条")
        messagebox.showinfo("成功", f"弹幕列表已保存，共 {len(all_danmaku)} 条")

    def save_danmaku_silent(self):
        """静默保存弹幕列表（不弹提示框）"""
        try:
            all_danmaku = self.get_all_danmaku()
            with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(all_danmaku))
            self.danmaku_list = all_danmaku
        except Exception:
            pass

    def refresh_danmaku_list(self):
        self.distribute_danmaku_to_columns(self.danmaku_list)

    # ---------- 日志 ----------
    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ---------- 发送控制 ----------
    def start_sending(self):
        account_mode = self.account_mode_var.get()
        if account_mode == "single":
            acc = self.get_current_account()
            if not acc:
                messagebox.showwarning("提示", "请先选择一个账户")
                return
            accounts = [acc]
        else:
            accounts = self.account_mgr.accounts
            if len(accounts) < 1:
                messagebox.showwarning("提示", "没有可用账户，请先添加账户")
                return

        room_id = self.room_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）")
            return
        # 从三列中获取所有弹幕
        lines = self.get_all_danmaku()
        if not lines:
            messagebox.showwarning("提示", "弹幕列表为空，请先添加弹幕内容")
            return
        self.danmaku_list = lines

        # 获取发送条数限制（0表示不限制）
        try:
            max_send_count = int(self.max_send_entry.get().strip())
            if max_send_count < 0:
                max_send_count = 0
        except ValueError:
            max_send_count = 0
        try:
            interval_min = float(self.interval_min.get())
            interval_max = float(self.interval_max.get())
            if interval_min <= 0 or interval_max <= 0 or interval_min > interval_max:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的发送间隔（秒），且最小值 ≤ 最大值")
            return

        # 验证账户登录
        valid_accounts = []
        for acc in accounts:
            cookie_str = self.account_mgr.get_cookie_string(acc["name"])
            ok, msg = verify_login(cookie_str)
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过: {msg}")

        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了，请更新cookie后重试")
            return

        if account_mode == "rotate" and len(valid_accounts) < 2:
            messagebox.showwarning("提示", "多账户轮流模式至少需要2个有效账户，当前只有1个")
            return

        self.running = True
        self.start_btn.set_state("disabled")
        self.stop_btn.set_state("normal")
        if account_mode == "single":
            status_text = f"状态：运行中（账户: {valid_accounts[0]['name']}）"
        else:
            status_text = f"状态：运行中（多账户轮流，共{len(valid_accounts)}个账户）"
        self.status_label.config(text=status_text, fg=COLORS["success"])
        self.header_status.config(text="● 运行中", fg=COLORS["success"])

        self.log("=" * 40)
        if account_mode == "single":
            self.log(f"启动发送 | 账户: {valid_accounts[0]['name']}")
        else:
            acc_names = "、".join([a['name'] for a in valid_accounts])
            self.log(f"启动发送 | 多账户轮流: {acc_names}")
        self.log(f"直播间: {room_id} | 弹幕: {len(self.danmaku_list)}条 | 间隔: {interval_min}-{interval_max}秒")
        if max_send_count > 0:
            self.log(f"发送限制: 最多发送 {max_send_count} 条后自动停止")
        self.log("-" * 40)

        self.send_thread = threading.Thread(
            target=self.send_loop, args=(valid_accounts, int(room_id), interval_min, interval_max, account_mode, max_send_count), daemon=True
        )
        self.send_thread.start()

    def stop_sending(self):
        self.running = False
        self.start_btn.set_state("normal")
        self.stop_btn.set_state("disabled")
        self.status_label.config(text="状态：已停止", fg=COLORS["warning"])
        self.header_status.config(text="● 已停止", fg=COLORS["warning"])
        self.log("-" * 40)
        self.log("已停止发送")

    def send_loop(self, accounts, room_id, interval_min, interval_max, account_mode, max_send_count=0):
        mode = self.mode_var.get()
        index = 0
        send_count = 0
        fail_count = 0
        acc_index = 0

        while self.running:
            # 检查是否达到最大发送条数
            if max_send_count > 0 and send_count >= max_send_count:
                self.log(f"✓ 已达到最大发送条数 {max_send_count}，自动停止")
                self.root.after(0, self.stop_sending)
                break

            # 选择当前账户
            if account_mode == "single":
                account = accounts[0]
            else:
                account = accounts[acc_index % len(accounts)]
                acc_index += 1

            cookie_str = self.account_mgr.get_cookie_string(account["name"])
            csrf = account["bili_jct"]

            # 选择弹幕
            if mode == "random":
                msg = random.choice(self.danmaku_list)
            else:
                msg = self.danmaku_list[index % len(self.danmaku_list)]
                index += 1

            success = False
            for retry in range(3):
                if not self.running:
                    break
                ok, result = send_danmaku(cookie_str, csrf, room_id, msg)
                if ok:
                    success = True
                    send_count += 1
                    fail_count = 0
                    if account_mode == "single":
                        self.log(f"✓ [{send_count}/{max_send_count if max_send_count > 0 else '∞'}] {msg}")
                    else:
                        self.log(f"✓ [{send_count}/{max_send_count if max_send_count > 0 else '∞'}] [{account['name']}] {msg}")
                    break
                else:
                    if retry < 2:
                        self.log(f"  重试{retry+1} ({account['name']}): {result}")
                        time.sleep(random.uniform(2, 4))

            if not success:
                fail_count += 1
                self.log(f"✗ 失败({fail_count}) [{account['name']}]: {msg} - {result}")
                if fail_count >= 5:
                    self.log("连续失败5次，自动停止")
                    self.root.after(0, self.stop_sending)
                    break

            wait_time = random.uniform(interval_min, interval_max)
            waited = 0
            while waited < wait_time and self.running:
                time.sleep(0.5)
                waited += 0.5

        self.log(f"本次结束，共成功发送 {send_count} 条")


def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        # 尝试设置Per-Monitor DPI Aware（Windows 8.1+）
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # 降级为System DPI Aware（Windows Vista+）
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
