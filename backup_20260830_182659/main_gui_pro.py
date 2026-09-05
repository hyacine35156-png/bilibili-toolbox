#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站自动发弹幕工具 - 美观深色主题版
功能：多账户管理、一键发送、实时日志
打包：pyinstaller --onefile --windowed --name B站弹幕工具 main_gui_pro.py
"""

import json
import time
import random
import threading
import hashlib
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
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
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播10天", "task_id": "6ERAcwloghvi7000", "award": "原石*100"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播20天", "task_id": "6ERAcwloghvy8x00", "award": "原石*100"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播30天", "task_id": "6ERAcwloghvioc00", "award": "原石*200"},
    {"version": "原神7.0", "period": "全版本", "type": "看播里程碑", "name": "累计看播40天", "task_id": "6ERAcwloghviv800", "award": "原石*200"},

    # ===== 崩坏星穹铁道4.5（task_id待补充，需从活动页面获取）=====
    # 上半 - 投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "TODO_HSR_1", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "TODO_HSR_2", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "TODO_HSR_3", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "TODO_HSR_4", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "TODO_HSR_5", "award": "待补充"},
    # 上半 - 直播任务
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "直播", "name": "开播时长60min", "task_id": "TODO_HSR_6", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "直播", "name": "开播时长120min", "task_id": "TODO_HSR_7", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "直播", "name": "直播间弹幕20条", "task_id": "TODO_HSR_8", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "上半", "type": "直播", "name": "观看人数≥5人", "task_id": "TODO_HSR_9", "award": "待补充"},
    # 下半 - 投稿任务
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "TODO_HSR_10", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "TODO_HSR_11", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "TODO_HSR_12", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "TODO_HSR_13", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "TODO_HSR_14", "award": "待补充"},
    # 下半 - 直播任务
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "直播", "name": "开播时长60min", "task_id": "TODO_HSR_15", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "直播", "name": "开播时长120min", "task_id": "TODO_HSR_16", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "直播", "name": "直播间弹幕20条", "task_id": "TODO_HSR_17", "award": "待补充"},
    {"version": "崩坏星穹铁道4.5", "period": "下半", "type": "直播", "name": "观看人数≥5人", "task_id": "TODO_HSR_18", "award": "待补充"},
]

# 兼容旧代码
MINGCHAO_TASKS = [t for t in ALL_TASKS if t["version"] == "鸣潮3.6"]

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


def receive_reward(task_id, task_info, cookies_dict, csrf):
    """领取奖励"""
    headers = {
        **HEADERS,
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
        "Origin": "https://www.bilibili.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "task_id": task_id,
        "activity_id": task_info.get("act_id", ""),
        "activity_name": task_info.get("act_name", ""),
        "task_name": task_info.get("task_name", ""),
        "reward_name": task_info.get("reward_info", {}).get("award_name", ""),
        "gaia_vtoken": "",
        "receive_from": "missionPage",
        "csrf": csrf,
    }

    try:
        resp = requests.post(MISSION_RECEIVE_API, headers=headers, cookies=cookies_dict, data=data, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            return True, "领取成功", result.get("data")
        return False, f"[{result.get('code')}] {result.get('message', '未知错误')}", None
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
class RushRewardWindow(tk.Toplevel):
    def __init__(self, parent, account_mgr):
        super().__init__(parent)
        self.title("B站自动抢码工具 - 鸣潮3.6创作激励")
        self.geometry("820x720")
        self.minsize(760, 640)
        self.configure(bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.running = False
        self.rush_thread = None
        self.transient(parent)
        self.rush_config = self.load_rush_config()

        self.build_ui()
        self.refresh_account_list()
        self.apply_rush_config()
        self.bind_auto_save()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.log("抢码工具已启动，选择任务和账户后点击「开始监控」")
        self.log("提示：领取需要先完成投稿任务并绑定游戏账号")

    def on_close(self):
        """窗口关闭时保存配置"""
        self.save_rush_config()
        self.destroy()

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
            "receive_interval": "699",
            "schedule_hour": "00",
            "schedule_minute": "59",
            "schedule_second": "54",
        }
        rush_config_file = BASE_DIR / "rush_config.json"
        if rush_config_file.exists():
            try:
                with open(rush_config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_rush_config(self):
        """保存抢码工具配置"""
        try:
            self.rush_config["version"] = self.version_var.get()
            self.rush_config["period"] = self.period_var.get()
            self.rush_config["task_type"] = self.task_type_var.get()
            self.rush_config["interval"] = self.interval_entry.get().strip()
            self.rush_config["task_name"] = self.task_var.get()
            self.rush_config["rush_account_mode"] = self.rush_account_mode.get()
            # 保存选中的账户
            selected = []
            for i in self.account_listbox.curselection():
                if i < len(self.account_mgr.accounts):
                    selected.append(self.account_mgr.accounts[i]["name"])
            self.rush_config["selected_accounts"] = selected
            self.rush_config["duration"] = self.duration_entry.get().strip()
            self.rush_config["receive_interval"] = self.receive_interval_entry.get().strip()
            self.rush_config["schedule_hour"] = self.schedule_hour_entry.get().strip()
            self.rush_config["schedule_minute"] = self.schedule_minute_entry.get().strip()
            self.rush_config["schedule_second"] = self.schedule_second_entry.get().strip()

            rush_config_file = BASE_DIR / "rush_config.json"
            with open(rush_config_file, "w", encoding="utf-8") as f:
                json.dump(self.rush_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def apply_rush_config(self):
        """应用抢码工具配置"""
        try:
            if self.rush_config.get("version"):
                self.version_var.set(self.rush_config["version"])
            if self.rush_config.get("period"):
                self.period_var.set(self.rush_config["period"])
            if self.rush_config.get("task_type"):
                self.task_type_var.set(self.rush_config["task_type"])
            self.update_task_list()
            if self.rush_config.get("interval"):
                self.interval_entry.delete(0, tk.END)
                self.interval_entry.insert(0, self.rush_config["interval"])
            if self.rush_config.get("task_name"):
                # 等待任务列表更新后设置
                self.after(100, lambda: self.task_var.set(self.rush_config["task_name"]))
            if self.rush_config.get("rush_account_mode"):
                self.rush_account_mode.set(self.rush_config["rush_account_mode"])
            if self.rush_config.get("duration"):
                self.duration_entry.delete(0, tk.END)
                self.duration_entry.insert(0, self.rush_config["duration"])
            if self.rush_config.get("receive_interval"):
                self.receive_interval_entry.delete(0, tk.END)
                self.receive_interval_entry.insert(0, self.rush_config["receive_interval"])
            if self.rush_config.get("schedule_hour"):
                self.schedule_hour_entry.delete(0, tk.END)
                self.schedule_hour_entry.insert(0, self.rush_config["schedule_hour"])
            if self.rush_config.get("schedule_minute"):
                self.schedule_minute_entry.delete(0, tk.END)
                self.schedule_minute_entry.insert(0, self.rush_config["schedule_minute"])
            if self.rush_config.get("schedule_second"):
                self.schedule_second_entry.delete(0, tk.END)
                self.schedule_second_entry.insert(0, self.rush_config["schedule_second"])
            # 恢复选中的账户
            selected_names = self.rush_config.get("selected_accounts", [])
            if selected_names:
                self.after(200, lambda: self.restore_selected_accounts(selected_names))
        except Exception as e:
            pass

    def restore_selected_accounts(self, selected_names):
        """恢复选中的账户"""
        try:
            self.account_listbox.selection_clear(0, tk.END)
            for i, acc in enumerate(self.account_mgr.accounts):
                if acc["name"] in selected_names:
                    self.account_listbox.selection_set(i)
        except Exception:
            pass

    def bind_auto_save(self):
        """绑定自动保存事件"""
        self.version_combo.bind("<<ComboboxSelected>>", lambda e: (self.on_version_change(), self.save_rush_config()))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: (self.update_task_list(), self.save_rush_config()))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: (self.update_task_list(), self.save_rush_config()))
        self.task_combo.bind("<<ComboboxSelected>>", lambda e: self.save_rush_config())
        self.interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.duration_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.receive_interval_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_hour_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_minute_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.schedule_second_entry.bind("<FocusOut>", lambda e: self.save_rush_config())
        self.rush_account_mode.trace_add("write", lambda *a: self.save_rush_config())
        self.account_listbox.bind("<<ListboxSelect>>", lambda e: self.save_rush_config())

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
                                          values=["上半", "下半", "全版本"], state="readonly",
                                          width=8, font=("微软雅黑", 9))
        self.period_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.period_combo.bind("<<ComboboxSelected>>", lambda e: self.update_task_list())

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
        self.update_task_list()  # 初始化任务列表

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

        tk.Label(row4, text="领取间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(20, 0))
        self.receive_interval_entry = DarkEntry(row4, width=6)
        self.receive_interval_entry.insert(0, "699")
        self.receive_interval_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row4, text="毫秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT)

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
            display = f"  {acc['name']}  ({acc.get('username', '?')})"
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

    def on_version_change(self):
        """版本切换时更新任务列表"""
        self.update_task_list()
        self.save_rush_config()

    def update_task_list(self):
        """根据版本、期数和任务类型更新任务下拉框"""
        version = self.version_var.get()
        period = self.period_var.get()
        task_type = self.task_type_var.get()
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

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.rush_log_text.config(state=tk.NORMAL)
        self.rush_log_text.insert(tk.END, line)
        self.rush_log_text.see(tk.END)
        self.rush_log_text.config(state=tk.DISABLED)

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

        acc = accounts[0]
        cookies = cookies_from_account(acc)
        self.log(f"查询: [{task['period']}][{task['type']}] {task['name']} => {task['award']}")
        self.log(f"  账户: {acc['name']}, task_id: {task['task_id']}")

        info, msg = get_mission_info(task["task_id"], cookies)
        if info:
            stock = info.get("stock_info", {})
            day_stock = stock.get("day_stock", 0)
            total_stock = stock.get("total_stock", 0)
            status = info.get("status", 0)
            message = info.get("message", "")
            task_finished = info.get("task_finished", False)

            stock_text = f"今日库存: {day_stock} | 总库存: {total_stock}"
            if day_stock > 0:
                self.stock_label.config(text=f"库存状态：{stock_text} ✓", fg=COLORS["success"])
            else:
                self.stock_label.config(text=f"库存状态：{stock_text} (今日已领完)", fg=COLORS["warning"])

            if task_finished and status in [0, 1]:
                self.qualify_label.config(text=f"领取资格：已完成任务，可以领取", fg=COLORS["success"])
            else:
                self.qualify_label.config(text=f"领取资格：{message} (状态:{status})", fg=COLORS["warning"])

            self.log(f"  库存: 今日{day_stock} / 总{total_stock}")
            self.log(f"  状态: {message} (status={status}, 任务完成={task_finished})")
            self.log(f"  任务名: {info.get('task_name', '')}")
        else:
            self.stock_label.config(text="库存状态：查询失败", fg=COLORS["danger"])
            self.qualify_label.config(text="领取资格：查询失败", fg=COLORS["danger"])
            self.log(f"  查询失败: {msg}")

    def do_receive_once(self, task, account):
        """执行一次领取，返回(是否成功, 消息)"""
        cookies = cookies_from_account(account)
        csrf = account["bili_jct"]
        info, msg = get_mission_info(task["task_id"], cookies)
        if not info:
            return False, f"查询失败: {msg}"
        stock = info.get("stock_info", {})
        day_stock = stock.get("day_stock", 0)
        status = info.get("status", 0)
        task_finished = info.get("task_finished", False)
        if day_stock <= 0:
            return False, "今日库存已领完"
        if not task_finished or status not in [0, 1]:
            return False, f"无领取资格: {info.get('message', '')}"
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
            self.log(f"  🎉 {msg}")
            messagebox.showinfo("成功", f"领取成功！\n任务: {task['name']}\n奖励: {task['award']}")
        else:
            self.log(f"  ✗ {msg}")
            messagebox.showwarning("失败", f"领取失败: {msg}")

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
            receive_interval = float(self.receive_interval_entry.get()) / 1000.0  # 毫秒转秒
            if duration <= 0 or receive_interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和领取间隔（毫秒）")
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
        self.log(f"领取时长: {duration}秒 | 领取间隔: {receive_interval*1000:.0f}毫秒")
        self.log(f"账户: {', '.join([a['name'] for a in valid_accounts])}")
        self.log("-" * 40)

        self.rush_thread = threading.Thread(
            target=self.schedule_receive_loop,
            args=(task, valid_accounts, target_seconds, duration, receive_interval),
            daemon=True
        )
        self.rush_thread.start()

    def build_task_info_from_task(self, task):
        """从任务列表数据构造task_info，避免查询卡住"""
        return {
            "act_id": task.get("act_id", ""),
            "act_name": "鸣潮3.6版本创作激励计划",
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

    def schedule_receive_loop(self, task, accounts, target_seconds, duration, receive_interval):
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

        # 到点了，立即开始领取（不先查询，避免卡住）
        actual_start = time.time()
        try:
            self.after(0, lambda: self.rush_status.config(text="● 领取中", fg=COLORS["success"]))
        except Exception:
            pass
        self.log(f"★ 到点！立即开始领取（延迟 {actual_start - target_timestamp:.3f} 秒）")
        self.log(f"  持续 {duration} 秒，间隔 {receive_interval*1000:.0f} 毫秒")

        # 直接用任务列表数据构造task_info
        task_info = self.build_task_info_from_task(task)

        # 快速领取循环
        start_time = time.time()
        attempt = 0
        success = False
        acc_index = 0

        while self.running and (time.time() - start_time) < duration and not success:
            account = accounts[acc_index % len(accounts)]
            acc_index += 1
            attempt += 1

            try:
                ok, msg = self.do_receive_fast(task, task_info, account)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"  🎉 第{attempt}次尝试成功！账户: {account['name']}")
                try:
                    self.after(0, lambda: messagebox.showinfo("成功", f"领取成功！\n第{attempt}次尝试\n账户: {account['name']}"))
                except Exception:
                    pass
                break
            else:
                if attempt <= 10 or attempt % 20 == 0:
                    self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 精确等待间隔
            next_attempt_time = time.time() + receive_interval
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

            # 查询任务信息
            info, msg = get_mission_info(task["task_id"], cookies)

            if not info:
                self.log(f"[{query_count}] 查询失败 ({account['name']}): {msg}")
            else:
                stock = info.get("stock_info", {})
                day_stock = stock.get("day_stock", 0)
                total_stock = stock.get("total_stock", 0)
                status = info.get("status", 0)
                task_finished = info.get("task_finished", False)

                # 更新UI状态
                stock_text = f"今日{day_stock}/总{total_stock}"
                try:
                    self.after(0, lambda: self.stock_label.config(
                        text=f"库存状态：{stock_text}",
                        fg=COLORS["success"] if day_stock > 0 else COLORS["warning"]
                    ))
                except Exception:
                    pass

                if query_count % 10 == 0 or day_stock > 0:
                    self.log(f"[{query_count}] {account['name']} | 库存:今日{day_stock}/总{total_stock} | 状态:{info.get('message','')}")

                # 判断是否可以领取
                can_receive = (
                    day_stock > 0
                    and task_finished
                    and status in [0, 1]
                )

                if can_receive:
                    self.log(f"★ 发现可领取！库存={day_stock}，正在领取...")
                    ok, result, data = receive_reward(task["task_id"], info, cookies, csrf)
                    if ok:
                        self.log(f"🎉 领取成功！账户: {account['name']}")
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


# ========== 主界面 ==========
class DanmakuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B站自动发弹幕工具")
        self.root.geometry("1000x850")
        self.root.minsize(900, 720)
        self.root.configure(bg=COLORS["bg_dark"])

        self.account_mgr = AccountManager()
        self.danmaku_list = self.load_danmaku()
        self.config = self.load_config()
        self.running = False
        self.send_thread = None

        self.setup_styles()
        self.build_ui()
        self.refresh_account_list()
        self.refresh_danmaku_list()
        self.log("程序启动，已加载 " + str(len(self.account_mgr.accounts)) + " 个账户，" + str(len(self.danmaku_list)) + " 条弹幕")
        self.log("数据目录: " + str(BASE_DIR))

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

        tk.Label(title_frame, text="● B站自动发弹幕", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  多账户版", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(8, 0))

        # 抢码工具按钮
        DarkButton(header, "⚡ 抢码工具", command=self.open_rush_tool,
                   width=100, height=32, bg_color="#ff6b35", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 15))

        self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.header_status.pack(side=tk.RIGHT, padx=20)

        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        # 主内容区
        main = tk.Frame(self.root, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 左侧：账户管理
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
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
        self.account_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.account_listbox.yview, style="Dark.Horizontal.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.account_listbox.config(yscrollcommand=scrollbar.set)

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
        right = tk.Frame(main, bg=COLORS["bg_dark"])
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

        # 弹幕列表卡片
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(danmaku_header, text="弹幕列表（每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(danmaku_header, "+ 添加", command=self.add_single_danmaku,
                   width=60, height=26, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT, padx=(4, 0))
        DarkButton(danmaku_header, "批量生成", command=self.batch_generate_danmaku,
                   width=70, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT)
        DarkButton(danmaku_header, "保存列表", command=self.save_danmaku,
                   width=80, height=26, bg_color="#444466", text_color="#ffffff").pack(side=tk.RIGHT, padx=(0, 4))

        text_frame = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        self.danmaku_text = tk.Text(text_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                     insertbackground=COLORS["accent"], font=("微软雅黑", 9),
                                     bd=0, highlightthickness=0, wrap=tk.WORD)
        self.danmaku_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dm_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.danmaku_text.yview, style="Dark.Horizontal.TScrollbar")
        dm_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.danmaku_text.config(yscrollcommand=dm_scroll.set)

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
            display = f"  {acc['name']}  ({acc.get('username', '?')})"
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

    def open_rush_tool(self):
        """打开抢码工具窗口"""
        rush_window = RushRewardWindow(self.root, self.account_mgr)
        self.log("已打开抢码工具")

    # ---------- 配置管理 ----------
    def load_config(self):
        default_config = {
            "room_id": "1791983148",
            "interval_min": "5",
            "interval_max": "10",
            "send_mode": "random",
            "account_mode": "single",
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
        # 绑定自动保存
        self.room_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_min.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_max.bind("<FocusOut>", lambda e: self.save_config())
        self.mode_var.trace_add("write", lambda *a: self.save_config())
        self.account_mode_var.trace_add("write", lambda *a: self.save_config())

    # ---------- 弹幕列表 ----------
    def add_single_danmaku(self):
        text = simpledialog.askstring("添加弹幕", "请输入弹幕内容：", parent=self.root)
        if text and text.strip():
            text = text.strip()
            current = self.danmaku_text.get("1.0", tk.END).strip()
            if current:
                self.danmaku_text.insert(tk.END, "\n" + text)
            else:
                self.danmaku_text.insert(tk.END, text)
            self.danmaku_list = [line.strip() for line in self.danmaku_text.get("1.0", tk.END).split("\n") if line.strip()]
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
        current = self.danmaku_text.get("1.0", tk.END).strip()
        if current:
            self.danmaku_text.insert(tk.END, "\n" + "\n".join(selected))
        else:
            self.danmaku_text.insert(tk.END, "\n".join(selected))
        self.danmaku_list = [line.strip() for line in self.danmaku_text.get("1.0", tk.END).split("\n") if line.strip()]
        self.save_danmaku()
        self.log(f"批量生成 {count} 条弹幕，当前共 {len(self.danmaku_list)} 条")

    def load_danmaku(self):
        if DANMAKU_FILE.exists():
            with open(DANMAKU_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return ["666", "主播好强", "来了来了", "哈哈哈哈", "学到了"]

    def save_danmaku(self):
        content = self.danmaku_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.danmaku_list = lines
        self.log(f"弹幕列表已保存，共 {len(lines)} 条")
        messagebox.showinfo("成功", f"弹幕列表已保存，共 {len(lines)} 条")

    def refresh_danmaku_list(self):
        self.danmaku_text.delete("1.0", tk.END)
        self.danmaku_text.insert("1.0", "\n".join(self.danmaku_list))

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
        content = self.danmaku_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            messagebox.showwarning("提示", "弹幕列表为空，请先添加弹幕内容")
            return
        self.danmaku_list = lines
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
        self.log("-" * 40)

        self.send_thread = threading.Thread(
            target=self.send_loop, args=(valid_accounts, int(room_id), interval_min, interval_max, account_mode), daemon=True
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

    def send_loop(self, accounts, room_id, interval_min, interval_max, account_mode):
        mode = self.mode_var.get()
        index = 0
        send_count = 0
        fail_count = 0
        acc_index = 0

        while self.running:
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
                        self.log(f"✓ [{send_count}] {msg}")
                    else:
                        self.log(f"✓ [{send_count}] [{account['name']}] {msg}")
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
