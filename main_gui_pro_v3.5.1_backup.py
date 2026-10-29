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
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
from pathlib import Path

import requests

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
BASE_DIR = Path(__file__).parent if not getattr(__import__("sys"), "frozen", False) else Path(__import__("sys").executable).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"

# 程序版本号
APP_VERSION = "v3.5.1"

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
    def __init__(self, parent, text, command=None, width=120, height=36,
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
                         font=("微软雅黑", 10, "bold"))

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
class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.geometry("460x500")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add
        self.transient(parent)
        self.grab_set()

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
                   width=90, height=32, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT)
        DarkButton(btn_frame, "取消", command=self.destroy,
                   width=80, height=32, bg_color="#555577", text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=100, height=32).pack(side=tk.RIGHT)

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
            "rush_account_mode": "single",
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
            self.rush_config["rush_account_mode"] = self.rush_account_mode.get()
            # 保存选中的账户
            selected = []
            for i in self.rush_account_list.curselection():
                if i < len(self.account_mgr.accounts):
                    selected.append(self.account_mgr.accounts[i]["name"])
            self.rush_config["selected_accounts"] = selected
            self.rush_config["duration"] = self.duration_entry.get().strip()
            self.rush_config["interval_mode"] = self.interval_mode.get()
            self.rush_config["fixed_interval"] = self.fixed_interval_entry.get().strip()
            self.rush_config["min_interval"] = self.min_interval_entry.get().strip()
            self.rush_config["max_interval"] = self.max_interval_entry.get().strip()
            self.rush_config["schedule_hour"] = self.schedule_hour_entry.get().strip()
            self.rush_config["schedule_minute"] = self.schedule_minute_entry.get().strip()
            self.rush_config["schedule_second"] = self.schedule_second_entry.get().strip()

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
            if self.rush_config.get("rush_account_mode"):
                self.rush_account_mode.set(self.rush_config["rush_account_mode"])

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
                self.schedule_hour_entry.delete(0, tk.END)
                self.schedule_hour_entry.insert(0, self.rush_config["schedule_hour"])
            if self.rush_config.get("schedule_minute"):
                self.schedule_minute_entry.delete(0, tk.END)
                self.schedule_minute_entry.insert(0, self.rush_config["schedule_minute"])
            if self.rush_config.get("schedule_second"):
                self.schedule_second_entry.delete(0, tk.END)
                self.schedule_second_entry.insert(0, self.rush_config["schedule_second"])

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
            self.rush_account_list.selection_clear(0, tk.END)
            for i, acc in enumerate(self.account_mgr.accounts):
                if acc["name"] in selected_names:
                    self.rush_account_list.selection_set(i)
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
        self.schedule_hour_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_minute_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_second_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.rush_account_mode.trace_add("write", lambda *a: self.save_rush_config())
        self.rush_account_list.bind("<<ListboxSelect>>", lambda e: self.save_rush_config())

    def build_ui(self):
        # 顶部标题
        header = tk.Frame(self, bg=COLORS["bg_card"], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="⚡ 自动抢码工具", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT, padx=20)
        self.rush_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 9))
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
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.version_var = tk.StringVar(value="鸣潮3.6")
        self.version_combo = ttk.Combobox(row1, textvariable=self.version_var,
                                           values=["鸣潮3.6", "原神7.0", "崩坏星穹铁道4.5"], state="readonly",
                                           width=14, font=("微软雅黑", 9))
        self.version_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: self.on_version_change())

        tk.Label(row1, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.period_var = tk.StringVar(value="上半")
        self.period_combo = ttk.Combobox(row1, textvariable=self.period_var,
                                          values=["上半", "下半", "全版本", "限时任务1", "限时任务2", "限时直播", "新人限定"], state="readonly",
                                          width=10, font=("微软雅黑", 9))
        self.period_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: self.on_period_change())

        tk.Label(row1, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.task_type_var = tk.StringVar(value="投稿")
        self.type_combo = ttk.Combobox(row1, textvariable=self.task_type_var,
                                        values=["投稿", "直播", "直播里程碑", "看播里程碑", "新人开播"], state="readonly",
                                        width=12, font=("微软雅黑", 9))
        self.type_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.update_task_list())

        tk.Label(row1, text="查询间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.interval_entry = DarkEntry(row1, width=6)
        self.interval_entry.insert(0, "3")
        self.interval_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row1, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)

        # 第二行：具体任务选择
        row1b = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1b.pack(fill=tk.X, pady=3)
        tk.Label(row1b, text="任务", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.task_var = tk.StringVar()
        self.task_combo = ttk.Combobox(row1b, textvariable=self.task_var, values=[],
                                        state="readonly", width=45, font=("微软雅黑", 9))
        self.task_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.on_version_change()  # 初始化期数、类型下拉框选项和任务列表

        # 第二行：账户选择
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="抢码账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.rush_account_mode = tk.StringVar(value="single")
        ttk.Radiobutton(row2, text="单账户", variable=self.rush_account_mode, value="single",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row2, text="多账户轮流", variable=self.rush_account_mode, value="rotate",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        self.rush_account_list = tk.Listbox(row2, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                             selectbackground=COLORS["accent"], selectforeground="#000000",
                                             font=("微软雅黑", 8), bd=0, highlightthickness=0,
                                             height=3, exportselection=False, selectmode=tk.EXTENDED)
        self.rush_account_list.pack(side=tk.LEFT, padx=(15, 0), fill=tk.X, expand=True)

        # 第三行：状态显示
        row3 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=(8, 0))
        self.stock_label = tk.Label(row3, text="库存状态：等待查询", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.stock_label.pack(side=tk.LEFT)
        self.qualify_label = tk.Label(row3, text="领取资格：等待查询", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.qualify_label.pack(side=tk.LEFT, padx=(20, 0))
        self.task_finish_label = tk.Label(row3, text="任务完成：等待查询", bg=COLORS["bg_card"],
                                           fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.task_finish_label.pack(side=tk.LEFT, padx=(20, 0))

        # 第四行：领取设置（时长、间隔）
        row4 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row4.pack(fill=tk.X, pady=(8, 0))
        tk.Label(row4, text="领取时长", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.duration_entry = DarkEntry(row4, width=6)
        self.duration_entry.insert(0, "20")
        self.duration_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row4, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)

        tk.Label(row4, text="间隔模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(20, 0))
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
                                     font=("微软雅黑", 9))
        self.ms_label = tk.Label(row4, text="毫秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                                  font=("微软雅黑", 9))

        # 初始化为随机模式
        self.toggle_interval_mode()

        # 第五行：定时时间（时、分、秒三个独立输入框）
        row5 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row5.pack(fill=tk.X, pady=(6, 0))
        tk.Label(row5, text="定时时间", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.schedule_hour_entry = DarkEntry(row5, width=4)
        self.schedule_hour_entry.insert(0, "00")
        self.schedule_hour_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="时", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.schedule_minute_entry = DarkEntry(row5, width=4)
        self.schedule_minute_entry.insert(0, "59")
        self.schedule_minute_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="分", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.schedule_second_entry = DarkEntry(row5, width=4)
        self.schedule_second_entry.insert(0, "54")
        self.schedule_second_entry.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row5, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)

        # 按钮行
        btn_row = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        self.query_btn = DarkButton(btn_row, "🔍 查询状态", command=self.query_status,
                                     width=100, height=32, bg_color="#444466", text_color="#ffffff")
        self.query_btn.pack(side=tk.LEFT)
        self.manual_receive_btn = DarkButton(btn_row, "🎯 手动领取", command=self.manual_receive,
                                              width=100, height=32, bg_color="#ff6b35", text_color="#ffffff")
        self.manual_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.schedule_receive_btn = DarkButton(btn_row, "⏰ 定时领取", command=self.schedule_receive,
                                                width=100, height=32, bg_color="#9b59b6", text_color="#ffffff")
        self.schedule_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_rush_btn = DarkButton(btn_row, "▶ 开始监控", command=self.start_rush,
                                          width=110, height=32, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_rush_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_rush_btn = DarkButton(btn_row, "■ 停止", command=self.stop_rush,
                                         width=80, height=32, bg_color=COLORS["danger"], text_color="#ffffff")
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
                   width=110, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "▶ 全部开始", command=self.start_all_scheduled_tasks,
                   width=80, height=26, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(schedule_header, "■ 全部停止", command=self.stop_all_scheduled_tasks,
                   width=80, height=26, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.RIGHT)

        # 定时任务列表
        list_frame = tk.Frame(schedule_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        # 表头
        header_frame = tk.Frame(list_frame, bg=COLORS["bg_input"])
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text="任务名称", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=4)
        tk.Label(header_frame, text="领取时间", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="时长/间隔", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=14, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="账户", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="状态", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(header_frame, text="操作", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 9, "bold"), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

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
                                      insertbackground=COLORS["accent"], font=("Consolas", 9),
                                      bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.rush_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rush_log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.rush_log_text.yview,
                                         style="Dark.Horizontal.TScrollbar")
        rush_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.rush_log_text.config(yscrollcommand=rush_log_scroll.set)

    def refresh_account_list(self):
        self.rush_account_list.delete(0, tk.END)
        default_index = -1
        for i, acc in enumerate(self.account_mgr.accounts):
            display = f"  {acc['name']}"
            self.rush_account_list.insert(tk.END, display)
            if acc["name"] == "灵砂是无敌的":
                default_index = i
        # 默认选中"灵砂是无敌的"账户
        if default_index >= 0:
            self.rush_account_list.selection_set(default_index)
            self.rush_account_list.see(default_index)

    def get_selected_accounts(self):
        selection = self.rush_account_list.curselection()
        if not selection:
            return []
        return [self.account_mgr.accounts[i] for i in selection]

    # ========== 定时任务相关方法 ==========
    def refresh_scheduled_task_list(self):
        """刷新定时任务列表显示"""
        # 清空现有内容
        for widget in self.schedule_list_frame.winfo_children():
            widget.destroy()

        if not self.scheduled_tasks:
            tk.Label(self.schedule_list_frame, text="暂无定时任务，设置好参数后点击「+ 添加当前设置」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(pady=10)
            return

        for idx, task in enumerate(self.scheduled_tasks):
            row_frame = tk.Frame(self.schedule_list_frame, bg=COLORS["bg_card"])
            row_frame.pack(fill=tk.X, pady=1)

            # 交替背景色
            if idx % 2 == 0:
                row_frame.configure(bg=COLORS["bg_input"])

            # 任务名称
            name_text = task.get("task_name", "未知任务")[:28]
            tk.Label(row_frame, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 8), width=30, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0), pady=3)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            tk.Label(row_frame, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 8, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            tk.Label(row_frame, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 8), width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:12] if accounts else "未设置"
            tk.Label(row_frame, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 8), width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            tk.Label(row_frame, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 8, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(8, 0))

            # 操作按钮
            btn_frame = tk.Frame(row_frame, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=(8, 0))

            task_id = task.get("id")
            if status in ["等待中", "已完成", "已领取", "失败"]:
                DarkButton(btn_frame, "开始", command=lambda tid=task_id: self.start_scheduled_task(tid),
                           width=45, height=22, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))
            else:
                DarkButton(btn_frame, "停止", command=lambda tid=task_id: self.stop_scheduled_task(tid),
                           width=45, height=22, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 2))

            DarkButton(btn_frame, "删除", command=lambda tid=task_id: self.delete_scheduled_task(tid),
                       width=45, height=22, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

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
            h = int(self.schedule_hour_entry.get().strip())
            m = int(self.schedule_minute_entry.get().strip())
            s = int(self.schedule_second_entry.get().strip())
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
        """启动所有定时任务"""
        count = 0
        for task in self.scheduled_tasks:
            if task.get("status") != "运行中":
                self.start_scheduled_task(task["id"])
                count += 1
        self.log(f"▶ 已启动 {count} 个定时任务")

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

            # 精确等待到目标时间，最后5秒提前查询任务信息
            task_info = {
                "act_id": "",
                "act_name": task_name,
                "task_name": task_name,
                "reward_info": {"award_name": task.get("award", "")},
            }
            task_info_fetched = False
            while not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if remaining <= 0:
                    break
                # 最后5秒提前查询任务信息，到点后可以立即领取
                if remaining <= 5 and not task_info_fetched:
                    task_info_fetched = True
                    try:
                        cookies = cookies_from_account(accounts[0])
                        info, msg = get_mission_info(task["task_id"], cookies)
                        if info:
                            task_info = info
                            self.log(f"  ✓ 提前获取任务信息")
                        else:
                            self.log(f"  ⚠ 提前查询任务信息失败: {msg}，使用备用数据")
                    except Exception as e:
                        self.log(f"  ⚠ 提前查询任务信息异常: {e}，使用备用数据")
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
                    self.log(f"  初始库存: 今日剩余={day_s}, 剩余总量={total_s}%")
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
                    self.log(f"[库存调试] 解析结果: 今日剩余={day_stock}, 活动剩余={total_stock}, 来源={stock_source}")
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
                    stock_parts_final.append(f"今日剩余{day_stock}")
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
            h = int(self.schedule_hour_entry.get().strip())
            m = int(self.schedule_minute_entry.get().strip())
            s = int(self.schedule_second_entry.get().strip())
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

        # 精确等待到目标时间
        last_log = 0
        task_info = self.build_task_info_from_task(task)  # 备用任务信息
        task_info_fetched = False
        while self.running:
            remaining = target_timestamp - time.time()
            if remaining <= 0:
                break
            # 每10秒输出一次剩余时间
            if int(remaining) != last_log and int(remaining) % 10 == 0 and int(remaining) > 0:
                last_log = int(remaining)
                self.log(f"  还剩 {int(remaining)} 秒...")
            # 最后5秒提前查询任务信息，到点后可以立即领取
            if remaining <= 5 and not task_info_fetched:
                task_info_fetched = True
                try:
                    first_account = accounts[0]
                    cookies = cookies_from_account(first_account)
                    info, msg = get_mission_info(task["task_id"], cookies)
                    if info:
                        task_info = info
                        act_id = info.get('act_id', '')
                        self.log(f"  ✓ 提前获取任务信息，act_id: {act_id}")
                    else:
                        self.log(f"  ⚠ 提前查询任务信息失败: {msg}，使用备用数据")
                except Exception as e:
                    self.log(f"  ⚠ 提前查询任务信息异常: {e}，使用备用数据")
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
                self.log(f"  初始库存: 今日剩余={day_s}, 剩余总量={total_s}%")
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

        mode = self.rush_account_mode.get()
        if mode == "single":
            accounts = self.get_selected_accounts()
            if not accounts:
                messagebox.showwarning("提示", "请先选择一个账户")
                return
            rush_accounts = [accounts[0]]
        else:
            rush_accounts = self.account_mgr.accounts
            if len(rush_accounts) < 1:
                messagebox.showwarning("提示", "没有可用账户")
                return

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
        self.log(f"账户: {acc_names} ({mode}) | 间隔: {interval}秒")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.rush_loop, args=(task, valid_accounts, interval, mode), daemon=True
        )
        self.rush_thread.start()

    def stop_rush(self):
        """停止监控/领取"""
        self.running = False
        self.start_rush_btn.set_state("normal")
        self.stop_rush_btn.set_state("disabled")
        self.query_btn.set_state("normal")
        self.manual_receive_btn.set_state("normal")
        self.schedule_receive_btn.set_state("normal")
        self.rush_status.config(text="● 已停止", fg=COLORS["warning"])
        self.log("-" * 40)
        self.log("已停止")

    def rush_loop(self, task, accounts, interval, mode):
        """自动抢码循环"""
        acc_index = 0
        query_count = 0
        success = False

        while self.running and not success:
            # 选择账户
            if mode == "single":
                account = accounts[0]
            else:
                account = accounts[acc_index % len(accounts)]
                acc_index += 1

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
                stock_parts.append(f"今日{day_stock}")
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
        self.account_vars = {}  # 每个账户名对应一个BooleanVar
        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.watch_config = self.load_watch_config()
        self.build_ui()
        self.refresh_account_list()
        self.apply_watch_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，勾选账户和直播间后点击「开始看播」")

    def load_watch_config(self):
        default = {"room_id": "1791983148", "daily_minutes": 30, "heartbeat_interval": 60, "selected_accounts": []}
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
            self.watch_config["room_id"] = self.room_entry.get().strip()
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
            self.room_entry.delete(0, tk.END)
            self.room_entry.insert(0, self.watch_config.get("room_id", ""))
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected_names)
        except Exception:
            pass

    def bind_auto_save(self):
        try:
            self.room_entry.bind("<KeyRelease>", lambda e: self.save_watch_config())
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
        except Exception:
            pass

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
        left_card.configure(width=220)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        # 全选/取消全选按钮
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.select_all_btn = tk.Button(btn_frame, text="全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._select_all_accounts)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.deselect_all_btn = tk.Button(btn_frame, text="取消全选", bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2", command=self._deselect_all_accounts)
        self.deselect_all_btn.pack(side=tk.LEFT)
        # 复选框滚动区域
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.account_canvas = tk.Canvas(list_frame, bg=COLORS["bg_input"], bd=0, highlightthickness=0)
        self.account_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.account_canvas.yview)
        self.account_scrollable_frame = tk.Frame(self.account_canvas, bg=COLORS["bg_input"])
        self.account_scrollable_frame.bind("<Configure>", lambda e: self.account_canvas.configure(scrollregion=self.account_canvas.bbox("all")))
        self.account_canvas.create_window((0, 0), window=self.account_scrollable_frame, anchor="nw")
        self.account_canvas.configure(yscrollcommand=self.account_scrollbar.set)
        self.account_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.account_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 右侧
        right = tk.Frame(main, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(settings_card, text="看播设置", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间号(多号逗号):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_entry = DarkEntry(row1, width=24)
        self.room_entry.pack(side=tk.LEFT, padx=(8, 20))
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
        self.start_btn = DarkButton(row2, "▶ 开始看播", command=self.start_watch, width=120, height=32, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = DarkButton(row2, "■ 停止看播", command=self.stop_watch, width=120, height=32, bg_color=COLORS["danger"], text_color="#ffffff")
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
        log_scroll = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(state=tk.DISABLED)

    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=False)
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
            self.status_tree.insert("", tk.END, values=(name, stats.get("status", "待开始"), f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_msg)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def get_cookie(self, account):
        return f"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}"

    def enter_room(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": room_id, "platform": "pc", "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
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
            data = {"room_id": room_id, "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.HEARTBEAT_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "心跳成功"
            return False, f"心跳失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"心跳异常: {e}"

    def start_watch(self):
        if self.running:
            return
        room_input = self.room_entry.get().strip()
        if not room_input:
            messagebox.showwarning("提示", "请输入直播间号")
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
        self.room_entry.config(state=tk.DISABLED)
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
            self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "status": "进入中", "last_heartbeat": None, "account": acc}
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
        self.room_entry.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
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
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
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
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    watch_min = stats["watch_seconds"] // 60
                    self.log(f"  [{name}] 心跳累计 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)

    def _on_watch_finished(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.room_entry.config(state=tk.NORMAL)
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
class DanmakuApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务")
        self.root.geometry("1000x850")
        self.root.minsize(900, 720)
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
        # 恢复上次选中的账户
        self.restore_selected_account()
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("程序启动，已加载 " + str(len(self.account_mgr.accounts)) + " 个账户，" + str(len(self.danmaku_list)) + " 条弹幕")
        self.log("数据目录: " + str(BASE_DIR))

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
                 fg=COLORS["accent"], font=("微软雅黑", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(8, 0))

        self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.header_status.pack(side=tk.RIGHT, padx=20)

        # 标签切换栏
        tab_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=44)
        tab_bar.pack(fill=tk.X)
        tab_bar.pack_propagate(False)

        self.tab_rush = tk.Label(tab_bar, text="⚡ 抢码工具", bg=COLORS["accent"], fg="#000000",
                                  font=("微软雅黑", 10, "bold"), padx=20, pady=8, cursor="hand2")
        self.tab_rush.pack(side=tk.LEFT, padx=(15, 5), pady=6)
        self.tab_rush.bind("<Button-1>", lambda e: self.switch_tab("rush"))

        self.tab_danmaku = tk.Label(tab_bar, text="💬 弹幕工具", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_danmaku.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_danmaku.bind("<Button-1>", lambda e: self.switch_tab("danmaku"))

        self.tab_shutdown = tk.Label(tab_bar, text="⏻ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_shutdown.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_shutdown.bind("<Button-1>", lambda e: self.switch_tab("shutdown"))

        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 10), padx=20, pady=8, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))

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

        self.current_tab = "rush"

        # 左侧：账户管理
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=240)

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

        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=10)

        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=100, height=30).pack(side=tk.LEFT, padx=(0, 4))
        DarkButton(btn_frame, "删除", command=self.delete_account,
                   width=60, height=30, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT)

        DarkButton(left_card, "验证登录", command=self.verify_current_account,
                   width=200, height=30, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 10), padx=12)

        self.account_info = tk.Label(left_card, text="未选择账户", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 8), wraplength=200, justify=tk.LEFT)
        self.account_info.pack(anchor=tk.W, padx=15, pady=(0, 12))

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

        # 弹幕列表卡片
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(danmaku_header, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(danmaku_header, "+ 添加", command=self.add_single_danmaku,
                   width=60, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(danmaku_header, "批量生成", command=self.batch_generate_danmaku,
                   width=70, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT)
        DarkButton(danmaku_header, "保存列表", command=self.save_danmaku,
                   width=80, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 4))

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

        # 日志卡片
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview, style="Dark.Horizontal.TScrollbar")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        # 底部控制栏按钮（footer已在前面创建并pack）
        ctrl_frame = tk.Frame(footer, bg=COLORS["bg_card"])
        ctrl_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        self.start_btn = DarkButton(ctrl_frame, "▶ 启动发送", command=self.start_sending,
                                     width=130, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, pady=10)

        self.stop_btn = DarkButton(ctrl_frame, "■ 停止发送", command=self.stop_sending,
                                    width=130, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0), pady=10)
        self.stop_btn.set_state("disabled")

        self.status_label = tk.Label(ctrl_frame, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.RIGHT)

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
        self.account_info.config(
            text=f"账户: {acc['name']}\n用户: {acc.get('username', '未知')}\nDedeID: {acc.get('DedeUserID', '未设置')}",
            fg=COLORS["text_secondary"]
        )
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
        if messagebox.askyesno("确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.account_info.config(text="未选择账户", fg=COLORS["text_muted"])
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

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))

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
                                                  width=120, height=32, bg_color=COLORS["accent"], text_color="#000000")
        self.add_shutdown_task_btn.pack(side=tk.LEFT)
        self.cancel_all_shutdown_btn = DarkButton(btn_frame, "■ 取消全部任务", command=self.cancel_all_shutdown,
                                                    width=120, height=32, bg_color=COLORS["danger"], text_color="#ffffff")
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
                    self.after(0, self.refresh_shutdown_task_list)
                    self.after(0, self.update_shutdown_status)
                    return
                remaining = int(total_seconds - (time.time() - start_time))
                task["remaining"] = remaining
                task["status"] = "倒计时中"
                self.after(0, self.refresh_shutdown_task_list)
                self.after(0, self.update_shutdown_status)
                time.sleep(1)

            # 时间到，执行关机
            if not task["stop_flag"]["stop"]:
                task["status"] = "执行中"
                self.after(0, self.refresh_shutdown_task_list)
                self.log(f"⏻ 任务「{task['name']}」时间到，正在执行关机...")
                time.sleep(1)
                # 执行Windows关机命令
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
        except Exception as e:
            task["status"] = "异常"
            self.log(f"✗ 关机任务「{task['name']}」异常: {e}")
            self.after(0, self.refresh_shutdown_task_list)
            self.after(0, self.update_shutdown_status)

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
            row_frame.pack(fill=tk.X, pady=1)

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
                                        width=60, height=24, bg_color=COLORS["danger"], text_color="#ffffff")
                cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))

            # 删除按钮（已取消/已完成的任务可以删除）
            if task["status"] in ["已取消", "执行中"]:
                delete_btn = DarkButton(row_frame, "删除", command=lambda tid=task["id"]: self.delete_shutdown_task(tid),
                                        width=60, height=24, bg_color="#444466", text_color="#ffffff")
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
        # 恢复窗口大小和位置
        if self.config.get("window_geometry"):
            try:
                self.root.geometry(self.config["window_geometry"])
            except Exception:
                pass
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
    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
