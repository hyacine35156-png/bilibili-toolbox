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
import struct
import re
import os
import sys
import ctypes
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

# ========== 修复PyInstaller打包后certifi证书路径问题 ==========
try:
    import certifi
    _cert_path = certifi.where()
    if os.path.exists(_cert_path):
        os.environ['REQUESTS_CA_BUNDLE'] = _cert_path
        os.environ['CURL_CA_BUNDLE'] = _cert_path
except Exception:
    pass

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

def atomic_write_json(path, data):
    """原子写入JSON：先写临时文件，fsync后os.replace，断电不损坏"""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, str(path))

def safe_load_json(path, default=None):
    """安全加载JSON：解析失败时备份为.corrupt并告警，不静默清空"""
    if default is None:
        default = []
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        # 备份损坏文件
        try:
            corrupt_path = str(path) + ".corrupt"
            import shutil
            shutil.copy2(path, corrupt_path)
            print(f"⚠ 配置文件损坏已备份: {corrupt_path} ({e})")
        except Exception:
            pass
    return default

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

try:
    _migrate_old_files()
except Exception as e:
    print(f"配置文件迁移失败（不影响启动）: {e}")

ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"
CONFIG_FILE = BASE_DIR / "config.json"
ACT_ID_CACHE_FILE = BASE_DIR / "act_id_cache.json"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backup"

# 程序版本号
APP_VERSION = "v6.0.0"

# ========== 任务信息缓存 ==========
# 缓存已判定为"已领取"或"无剩余总量"的任务信息，避免重复查询API
# key: task_id, value: {finished, status, message, total_stock, day_stock, timestamp}
_mission_info_cache = {}
# 缓存有效期：24小时（秒）
_MISSION_CACHE_TTL = 24 * 3600

# ========== 卡密验证配置 ==========
CARD_API_BASE = "https://precious-tanuki-c4b16d.netlify.app/api"
CARD_VERIFY_URL = f"{CARD_API_BASE}/verify-card"
CARD_FILE = BASE_DIR / "card_auth.json"

TASK_GUIDE_TEXT = """═══════════════════════════════════════════════════════
                    B站工具箱 使用说明
═══════════════════════════════════════════════════════

【一、账户管理】
───────────────────────────────────────────────────────

  1.1 导入账户（重点）
  ─────────────────────────────────────────────────
  步骤：
    ① 点击「+ 添加账户」按钮
    ② 输入账户昵称（自定义，用于区分不同账户）
    ③ 输入 SESSDATA（从浏览器Cookie中复制）
    ④ 输入 bili_jct（CSRF Token，从Cookie中复制）
    ⑤ 输入 DedeUserID（用户UID，可选，从Cookie中复制）
    ⑥ 点击确定，系统自动验证登录有效性
    ⑦ 验证成功后账户自动保存，所有功能模块共享

  获取Cookie方法：
    ① 浏览器登录B站后，按 F12 打开开发者工具
    ② 切换到 Application（应用/存储）标签
    ③ 左侧找到 Cookies → https://www.bilibili.com
    ④ 分别复制 SESSDATA、bili_jct、DedeUserID 的值

  注意事项：
    • SESSDATA 是账户身份凭证，请勿泄露给他人
    • 账户数据保存在 data/accounts.json 文件中
    • 「验证登录」可检查当前账户是否有效
    • 「刷新信息」可更新账户的最新昵称

  1.2 直播间管理
  ─────────────────────────────────────────────────
  功能：统一管理所有直播间，各功能模块共享

  操作：
    • 「+ 添加直播间」手动添加（输入直播间号+显示名称+备注）
    • 「从账户导入」自动获取所有已导入账户的直播间
    • 「删除直播间」移除选中的直播间

  说明：
    • 直播间号是数字ID
    • 显示名称默认"用户名的房间"，可自定义修改
    • 选择直播间时只显示名称，不显示数字ID
    • 所有功能（弹幕/看播/送礼）共用此列表


【二、抢码工具】
───────────────────────────────────────────────────────

  2.1 功能说明
  ─────────────────────────────────────────────────
  自动监控并领取B站直播任务奖励（如游戏礼包码、道具等）

  2.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择抢码任务（每日任务/累计任务等，从下拉框选择）
    ② 选择参与抢码的账户（可多选，复选框勾选）
    ③ 设置领取时间（精确到秒，时:分:秒）
    ④ 点击「开始监控」，到点自动领取
    ⑤ 支持「开始领取」按配置自动执行所有任务

  2.3 注意事项
  ─────────────────────────────────────────────────
    • 库存为0时自动停止，避免无效请求占用线程
    • 多个任务间隔5秒循序启动，避免请求频率过高
    • 领取前自动获取任务act_id，缓存作为备份


【三、弹幕工具】
───────────────────────────────────────────────────────

  3.1 功能说明
  ─────────────────────────────────────────────────
  多账户自动发送弹幕到指定直播间

  3.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择发送弹幕的账户（可多选，复选框勾选）
    ② 选择直播间（下拉框，从账户管理页面添加）
    ③ 输入弹幕内容（支持多条，每行一条，随机/顺序发送）
    ④ 设置发送间隔（秒，两次弹幕之间的等待时间）
    ⑤ 点击「开始发送」，自动循环发送
    ⑥ 点击「停止发送」终止

  3.3 注意事项
  ─────────────────────────────────────────────────
    • 弹幕内容保存在 data/danmaku_list.txt
    • 发送间隔建议不低于5秒，避免被风控
    • 多账户同时发送时，每个账户独立计时


【四、看播任务】
───────────────────────────────────────────────────────

  4.1 功能说明
  ─────────────────────────────────────────────────
  模拟真实用户观看直播，建立弹幕连接+视频流下载，计入在线观众

  4.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择看播账户（可多选，默认全选，复选框勾选）
    ② 选择直播间（支持多栏，每栏选一个直播间）
       - 点击「+ 添加」增加直播间栏
       - 第一个栏不可删除，后面添加的栏可点✕删除
    ③ 设置每日时长（分钟，目标观看时长）
    ④ 设置心跳间隔（秒，弹幕连接心跳上报间隔，默认60秒）
    ⑤ 点击「开始看播」，模拟真实观看

  4.3 工作原理
  ─────────────────────────────────────────────────
    • 进入直播间 → 建立弹幕WebSocket连接 → 认证成功
    • 获取视频流地址 → 连接视频流 → 持续下载数据
    • 每60秒发送一次弹幕心跳，保持在线状态
    • 多账户同时观看，每个账户独立连接

  4.4 注意事项
  ─────────────────────────────────────────────────
    • 看播会下载视频流数据，消耗网络带宽
    • 心跳间隔建议60秒，过短可能被风控
    • 视频流地址每60秒自动刷新一次


【五、送礼功能】
───────────────────────────────────────────────────────

  5.1 功能说明
  ─────────────────────────────────────────────────
  多账户自动赠送礼物到指定直播间

  5.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择送礼账户（单选，下拉框选择，只能选已导入的账户）
    ② 选择直播间（下拉框，从账户管理页面添加）
    ③ 选择礼物（固定：牛蛙牛蛙，1电池/个）
    ④ 设置数量（1个 或 10个）
    ⑤ 设置送礼间隔（秒，两次送礼之间的等待时间）
    ⑥ 设置送礼次数（0=未设置，需输入大于0的次数才能开始；其他数字=送N次后停止）
    ⑦ 点击「查询电池」查看账户当前电池余额
    ⑧ 点击「开始送礼」自动执行

  5.3 注意事项
  ─────────────────────────────────────────────────
    • 电池为0的账户自动禁用送礼功能
    • 送礼会消耗真实电池，请谨慎使用
    • 部分直播间不支持某些礼物，会提示"该房间不支持投喂该礼物"
    • 送礼间隔建议不低于10秒


【六、日程任务】
───────────────────────────────────────────────────────

  6.1 功能说明
  ─────────────────────────────────────────────────
  定时自动执行各种任务，支持抢码/看播/弹幕/送礼/关机

  6.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择任务类型（抢码/看播/弹幕/送礼/关机）
    ② 任务名称自动填写（如"看播1"、"看播2"，可修改）
    ③ 设置执行时间（时:分:秒，下拉选择）
       - 抢码任务无需设置时间（各子任务运行时间不同）
    ④ 点击「添加开机任务」保存日程
    ⑤ 日程自动保存，重启软件不丢失

  6.3 日程管理
  ─────────────────────────────────────────────────
    • 左侧任务栏显示所有日程
    • 「启用」按钮：启动该日程（到点自动执行）
    • 「取消」按钮：停止该日程（不再执行）
    • 「编辑」按钮：修改日程参数
    • 复选框：多选日程，「批量删除」一键删除
    • 「全选」按钮：选中所有日程
    • 「全部启用」按钮：一键启用所有日程
    • 「一键执行」按钮：按时间顺序执行所有日程

  6.4 方案管理
  ─────────────────────────────────────────────────
    • 「保存方案」：将当前所有日程保存为一套方案
    • 「加载方案」：一键切换到已保存的方案
    • 「删除方案」：删除不需要的方案
    • 适合不同场景（如工作日/周末/活动期）快速切换

  6.5 注意事项
  ─────────────────────────────────────────────────
    • 任务执行完毕后状态显示"已结束"
    • 抢码任务结束=最后一个抢码子任务结束
    • 调度器日志与各模块日志同步显示
    • 抢码任务只在抢码前1分钟写入日志，不足1分钟立即写入


【七、定时关机】
───────────────────────────────────────────────────────

  7.1 功能说明
  ─────────────────────────────────────────────────
  定时自动关闭电脑

  7.2 使用步骤
  ─────────────────────────────────────────────────
    ① 选择关机方式：定时关机（指定时间）或 延时关机（倒计时）
    ② 设置关机时间（定时关机）或 延时分钟数（延时关机）
    ③ 点击「开始」启动倒计时
    ④ 关机前有确认提示，可点击取消

  7.3 注意事项
  ─────────────────────────────────────────────────
    • 关机任务可加入日程任务，自动执行
    • 关机时间在定时关机页面设置，日程中只选择任务
    • 关机前请保存所有工作，避免数据丢失


═══════════════════════════════════════════════════════
                    常见问题
═══════════════════════════════════════════════════════

  Q: 为什么看播任务显示"X25Kn E接口失败"？
  A: 观看心跳上报接口失败，不影响弹幕连接和视频流播放，
     在线观众计数主要靠弹幕WebSocket连接。

  Q: 抢码时提示"请求频率过高"怎么办？
  A: 错误码 -702/-705/-509 都是请求过于频繁。
     系统已自动间隔5秒循序启动任务，
     领取时也会自动退避重试，无需手动干预。

  Q: 送礼提示"该房间不支持投喂该礼物"怎么办？
  A: 错误码 200007/200036 表示该直播间不支持此礼物。
     牛蛙牛蛙是通用礼物，大部分直播间都支持，
     如果仍报错，请换一个直播间试试。

  Q: 账户数据会泄露吗？
  A: 所有数据保存在本地 data/ 目录下，不上传任何服务器。
     SESSDATA 等敏感信息请妥善保管，不要分享给他人。

═══════════════════════════════════════════════════════"""

SEND_API = "https://api.live.bilibili.com/msg/send"
USER_INFO_API = "https://api.bilibili.com/x/web-interface/nav"

# 抢码相关API
MISSION_INFO_API = "https://api.bilibili.com/x/activity_components/mission/info"
MISSION_RECEIVE_API = "https://api.bilibili.com/x/activity_components/mission/receive"
MISSION_MYLIST_API = "https://api.bilibili.com/x/activity_components/mission/mylist"

# 活动任务列表（按版本+期数+类型分类）
ALL_TASKS = [
    # ===== 鸣潮3.7 =====
    # 上半（第一期）- 投稿任务
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghvp8b00", "award": "60星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghvpff00", "award": "120星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvpvq00", "award": "180星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghvpb400", "award": "300星声"},
    {"version": "鸣潮3.7", "period": "上半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghvoao00", "award": "500星声"},
    # 上半 - 直播任务
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvod500", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvp1h00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvpo100", "award": "贝币*10000"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvoxr00", "award": "中级复苏吸雾*2"},
    # 上半 - 直播里程碑
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA1wloghvcsm00", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghv1nf00", "award": "星声*300"},
    {"version": "鸣潮3.7", "period": "上半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA1wloghvcvs00", "award": "唤声涡纹*3"},
    # 下半（第二期）- 投稿任务
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计1天投稿≥100播放", "task_id": "6ERAcwloghvpah00", "award": "60星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计2天投稿≥300播放≥3币", "task_id": "6ERAcwloghvoll00", "award": "120星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计3天投稿≥1000播放≥10币", "task_id": "6ERAcwloghvpg700", "award": "180星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计7天投稿≥2000播放≥20币", "task_id": "6ERAcwloghvpic00", "award": "300星声"},
    {"version": "鸣潮3.7", "period": "下半", "type": "投稿", "name": "累计14天投稿≥3000播放≥40币", "task_id": "6ERAcwloghvazd00", "award": "500星声"},
    # 下半 - 直播任务
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "开播时长60min", "task_id": "6ERAcwloghvoxc00", "award": "中级共鸣促剂*2"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "开播时长120min", "task_id": "6ERAcwloghvawq00", "award": "中级能源核心*2"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "直播间弹幕20条", "task_id": "6ERAcwloghvppd00", "award": "贝币*10000"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播", "name": "观看人数≥5人", "task_id": "6ERAcwloghvazv00", "award": "中级复苏吸雾*2"},
    # 下半 - 直播里程碑
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务3天", "task_id": "18ERA1wloghvcl800", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务5天", "task_id": "18ERA1wloghv17v00", "award": "星声*300"},
    {"version": "鸣潮3.7", "period": "下半", "type": "直播里程碑", "name": "完成全部每日任务10天", "task_id": "18ERA1wloghvcpj00", "award": "唤声涡纹*3"},
    # 全版本（新人开播奖励等）
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计1天开播", "task_id": "18ERA1wloghvcrq00", "award": "星声*50"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计2天开播", "task_id": "18ERA1wloghvcl700", "award": "星声*80"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计3天开播", "task_id": "18ERA1wloghvcje00", "award": "星声*120"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计7天开播", "task_id": "18ERA1wloghvcue00", "award": "星声*180"},
    {"version": "鸣潮3.7", "period": "全版本", "type": "新人开播", "name": "累计14天开播", "task_id": "18ERA1wloghvvc700", "award": "唤声涡纹*2"},

    # ===== 原神7.1 =====
    # 直播任务
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日开播满60分钟", "task_id": "6ERAcwloghvatw00", "award": "精锻用魔矿*5"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "分区开播满60分钟且直播间发送弹幕2人", "task_id": "6ERAcwloghvofk00", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间累计收到≥10电池价值的礼物", "task_id": "6ERAcwloghvpil00", "award": "大英雄的经验*2"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间弹幕数满6条", "task_id": "6ERAcwloghvofj00", "award": "冒险家的经验*6"},
    {"version": "原神7.1", "period": "全版本", "type": "直播", "name": "当日直播间至少有1名用户观看满10分钟", "task_id": "6ERAcwloghvp7k00", "award": "摩拉*11111"},
    # 直播里程碑任务
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积1天开播", "task_id": "18ERA1wloghvcxd00", "award": "原石*200"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积5天开播", "task_id": "18ERA1wloghvvzn00", "award": "原石*600"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积10天开播", "task_id": "18ERA1wloghvcdt00", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积20天开播", "task_id": "18ERA1wloghv1b900", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积30天开播", "task_id": "18ERA1wloghvcty00", "award": "原石*1000"},
    {"version": "原神7.1", "period": "全版本", "type": "直播里程碑", "name": "累积40天开播", "task_id": "18ERA1wloghvckw00", "award": "原石*1000"},
    # 看播里程碑任务
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积1天看播", "task_id": "18ERA1wloghvcxf00", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积5天看播", "task_id": "18ERA1wloghvcv400", "award": "原石*50"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积10天看播", "task_id": "18ERA1wloghvvcp00", "award": "原石*100"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积20天看播", "task_id": "18ERA1wloghv12p00", "award": "原石*100"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积30天看播", "task_id": "18ERA1wloghv1ng00", "award": "原石*200"},
    {"version": "原神7.1", "period": "全版本", "type": "看播里程碑", "name": "累积40天看播", "task_id": "18ERA1wloghv1me00", "award": "原石*200"},


    # ===== 崩坏星穹铁道4.6（投稿任务）=====
    # 上半 - 投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvp2600", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAcwloghvauo00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAcwloghvp6y00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAcwloghvp2500", "award": "星琼*500"},
    # 下半 - 投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计1天投稿", "task_id": "6ERAcwloghvpt100", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计3天投稿，且收到三连2", "task_id": "6ERAcwloghvp4g00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计5天投稿，总播≥1000且收到三连10", "task_id": "6ERAcwloghvpii00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "投稿", "name": "累计7天投稿，总播≥2000且收到三连30", "task_id": "6ERAcwloghvayj00", "award": "星琼*500"},
    # 特殊投稿任务
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量3万", "task_id": "6ERAcwloghvozs00", "award": "星琼*300"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量5万", "task_id": "6ERAcwloghvolz00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量10万", "task_id": "6ERAcwloghvpga00", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "全版本", "type": "投稿", "name": "累计播放量30万", "task_id": "6ERAcwloghvpnt00", "award": "星轨通票*10"},
    # 新人限定 - 直播任务
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积1天开播", "task_id": "18ERA1wloghvcjw00", "award": "星轨通票*1"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积3天开播", "task_id": "18ERA1wloghv18w00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积5天开播", "task_id": "18ERA1wloghvctt00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "新人限定", "type": "直播", "name": "【新人】累积10天开播", "task_id": "18ERA1wloghv1cn00", "award": "星琼*200"},


    # 每日任务
    {"version": "崩坏星穹铁道4.6", "period": "每日", "type": "直播", "name": "【每日】开播60分钟+观看15分钟", "task_id": "6ERAcwloghvalh00", "award": "冒险记录*6+遗失碎金*5"},
    {"version": "崩坏星穹铁道4.6", "period": "每日", "type": "直播", "name": "【每日】礼物≥10电池+弹幕≥4人", "task_id": "6ERAcwloghvoaq00", "award": "漫游指南*2+信用点*11111"},
    # 限时直播任务
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【限时】开播（9.28-10.4）", "task_id": "6ERAcwloghvpjz00", "award": "星琼*50"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【限时】开播（10.21-10.27）", "task_id": "6ERAcwloghvp4k00", "award": "星琼*50"},
    # 直播里程碑 - 上半
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积3天开播", "task_id": "18ERA1wloghvcg100", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积5天开播", "task_id": "18ERA1wloghvczg00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积10天开播", "task_id": "18ERA1wloghvcer00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "【里程碑】累积15天开播", "task_id": "18ERA1wloghv16700", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "上半", "type": "直播", "name": "直播间新增1名舰长", "task_id": "6ERAcwloghvasy00", "award": "星轨通票*3"},
    # 直播里程碑 - 下半
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积3天开播", "task_id": "18ERA1wloghv1ch00", "award": "星轨通票*2"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积5天开播", "task_id": "18ERA1wloghv1nd00", "award": "星琼*600"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积10天开播", "task_id": "18ERA1wloghvcsq00", "award": "星琼*800"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "【里程碑】累积15天开播", "task_id": "18ERA1wloghvcva00", "award": "星琼*1000"},
    {"version": "崩坏星穹铁道4.6", "period": "下半", "type": "直播", "name": "直播间新增1名舰长", "task_id": "6ERAcwloghvp7x00", "award": "星轨通票*3"},

    # ===== 绝区零3.2 =====
    # 全版本 - 直播里程碑任务
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计3天完成开播及互动任务", "task_id": "18ERA1wloghvv9m00", "award": "菲林*360"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计5天完成开播及互动任务", "task_id": "18ERA1wloghvbtf00", "award": "菲林*660"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计10天完成开播及互动任务", "task_id": "18ERA1wloghvv1m00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计20天完成开播及互动任务", "task_id": "18ERA1wloghvbfq00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计30天完成开播及互动任务", "task_id": "18ERA1wloghvvef00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "累计35天完成开播及互动任务", "task_id": "18ERA1wloghvc4600", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播里程碑", "name": "直播收获1名舰长", "task_id": "6ERAcwloghvuzk00", "award": "菲林*480"},
    # 全版本 - 每日直播任务
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日开播60分钟", "task_id": "6ERAcwloghvuse00", "award": "丁尼*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日直播间收到电池≥2", "task_id": "6ERAcwloghvyxs00", "award": "音擎能源模块*2"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日直播间弹幕≥10条", "task_id": "6ERAcwloghvabs00", "award": "资深调查员记录*2"},
    {"version": "绝区零3.2", "period": "全版本", "type": "直播", "name": "当日至少1名用户观看≥10分钟", "task_id": "6ERAcwloghvsp000", "award": "丁尼*5000"},
    # 全版本 - 投稿任务
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "投稿≥4，播放≥400", "task_id": "6ERAcwloghvy3000", "award": "菲林*80"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "投稿≥5，播放≥500", "task_id": "6ERAcwloghva2p00", "award": "原装母带*1"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥15万", "task_id": "6ERAcwloghvstw00", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "播放≥70万", "task_id": "6ERAcwloghva0600", "award": "菲林*1600"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥100", "task_id": "6ERAcwloghvydm00", "award": "菲林*30"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000", "task_id": "6ERAcwloghvuvr00", "award": "菲林*300"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "单稿播放≥10000的有效投稿≥3", "task_id": "6ERAcwloghva5u00", "award": "菲林*800"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿3天，且累计视频播放≥500", "task_id": "6ERAcwloghvany00", "award": "菲林*150"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿10天，且累计视频播放≥1000", "task_id": "6ERAcwloghvse600", "award": "菲林*300"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿20天，且累计视频播放≥3000", "task_id": "6ERAcwloghvyvy00", "award": "菲林*500"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿30天，且累计视频播放≥6000", "task_id": "6ERAcwloghvy3900", "award": "菲林*1000"},
    {"version": "绝区零3.2", "period": "全版本", "type": "投稿", "name": "累计投稿35天，且累计视频播放≥50000", "task_id": "6ERAcwloghvsp300", "award": "菲林*1000"},
]

# 兼容旧代码
MINGCHAO_TASKS = [t for t in ALL_TASKS if t["version"] == "鸣潮3.7"]

# task_id到act_id的缓存字典（查询成功时自动保存，查询失败时使用）
# 全局变量线程锁
_GLOBAL_LOCK = threading.Lock()
TASK_ACT_ID_CACHE = {}

# 版本默认act_id（同一版本的所有任务共享同一个act_id）
VERSION_DEFAULT_ACT_ID = {
    "鸣潮3.7": "1ERAzwloghv32n00",
    "原神7.1": "1ERA3wloghv6q200",
    "崩坏星穹铁道4.6": "1ERAzwloghv3q100",
    "绝区零3.2": "1ERAzwloghvbmi00",
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
        atomic_write_json(ACT_ID_CACHE_FILE, TASK_ACT_ID_CACHE)
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
_last_claim_data_global = None
_last_claim_result_global = None

class AccountManager:
    def __init__(self):
        self.accounts = []
        self.load()

    def load(self):
        self.accounts = safe_load_json(ACCOUNTS_FILE, [])

    def save(self):
        atomic_write_json(ACCOUNTS_FILE, self.accounts)

    def add_account(self, name, sessdata, bili_jct, dede_userid=""):
        MAX_ACCOUNTS = 8
        if len(self.accounts) >= MAX_ACCOUNTS:
            return False, f"最多只能添加 {MAX_ACCOUNTS} 个账户，当前已有 {len(self.accounts)} 个"
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

    def update_account(self, old_name, name, sessdata, bili_jct, dede_userid=""):
        """更新账户信息（先验证cookie有效性，失效则禁止修改）"""
        # 先验证新cookie是否有效
        cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
        if dede_userid:
            cookie_str += f"; DedeUserID={dede_userid}"
        ok, msg = verify_login(cookie_str)
        if not ok:
            return False, f"登录验证失败，无法修改账户信息: {msg}"
        # 检查新名称是否与其他账户冲突
        for acc in self.accounts:
            if acc["name"] == name and acc["name"] != old_name:
                return False, f"账户名「{name}」已存在"
        # 更新账户
        for acc in self.accounts:
            if acc["name"] == old_name:
                acc["name"] = name
                acc["SESSDATA"] = sessdata
                acc["bili_jct"] = bili_jct
                acc["DedeUserID"] = dede_userid
                acc["username"] = msg
                break
        self.save()
        return True, f"账户「{name}」更新成功（当前用户: {msg}）"

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


class RoomManager:
    """直播间管理器"""
    def __init__(self):
        self.rooms = []
        self.load()

    def load(self):
        config_file = BASE_DIR / "rooms_config.json"
        data = safe_load_json(config_file, {})
        self.rooms = data.get("rooms", []) if isinstance(data, dict) else []

    def save(self):
        config_file = BASE_DIR / "rooms_config.json"
        atomic_write_json(config_file, {"rooms": self.rooms})

    def add_room(self, room_id, name, remark=""):
        room_id = str(room_id).strip()
        if not room_id or not room_id.isdigit():
            return False, "直播间号必须是数字"
        for room in self.rooms:
            if room["id"] == room_id:
                return False, "直播间号已存在"
        self.rooms.append({"id": room_id, "name": name, "remark": remark})
        self.save()
        return True, "添加成功"

    def delete_room(self, room_id):
        self.rooms = [r for r in self.rooms if r["id"] != str(room_id)]
        self.save()

    def update_room(self, room_id, name=None, remark=None):
        for room in self.rooms:
            if room["id"] == str(room_id):
                if name is not None:
                    room["name"] = name
                if remark is not None:
                    room["remark"] = remark
                self.save()
                return True
        return False

    def get_room(self, room_id):
        for room in self.rooms:
            if room["id"] == str(room_id):
                return room
        return None

    def get_room_names(self):
        """获取所有直播间的显示名称列表"""
        return [f"{r['name']}（{r['id']}）" for r in self.rooms]

    def import_from_accounts(self, account_mgr, log_func=None):
        """从账户导入直播间（自动获取所有账户的直播间号）"""
        added = 0
        for acc in account_mgr.accounts:
            name = acc.get("name", "未知")
            mid = acc.get("DedeUserID", "")
            if not mid:
                continue
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid")
                    if room_id and data["data"].get("roomStatus") == 1:
                        room_name = f"{name}的房间"
                        if not self.get_room(room_id):
                            self.add_room(room_id, room_name, "从账户导入")
                            added += 1
                            if log_func:
                                log_func(f"已导入「{name}」的直播间: {room_id}")
            except Exception:
                pass
        if log_func:
            log_func(f"从账户导入完成，共新增 {added} 个直播间")
        return added


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
# WBI密钥缓存（减少重复网络请求）
_WBI_KEY_CACHE = {}  # {cookie_hash: (img_key, sub_key, expire_time)}
_WBI_CACHE_TTL = 3600  # 缓存1小时

def get_wbi_keys(cookies_dict):
    """获取WBI签名密钥（带缓存，减少重复请求）"""
    # 生成cookie的哈希作为缓存键
    try:
        cookie_str = str(sorted(cookies_dict.items())) if isinstance(cookies_dict, dict) else str(cookies_dict)
        cookie_hash = hashlib.md5(cookie_str.encode()).hexdigest()
    except Exception:
        cookie_hash = 'default'
    
    # 检查缓存
    now = time.time()
    if cookie_hash in _WBI_KEY_CACHE:
        img_key, sub_key, expire_time = _WBI_KEY_CACHE[cookie_hash]
        if now < expire_time and img_key and sub_key:
            return img_key, sub_key
    
    # 缓存未命中，请求网络
    headers = {**HEADERS, "Referer": "https://www.bilibili.com/"}
    try:
        resp = requests.get(USER_INFO_API, headers=headers, cookies=cookies_dict, timeout=10)
        data = resp.json()
        # wbi_img在登录和未登录时都会返回，不限制code==0
        wbi_img = data.get("data", {}).get("wbi_img")
        if wbi_img and wbi_img.get("img_url") and wbi_img.get("sub_url"):
            img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
            sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
            if img_key and sub_key:
                # 存入缓存
                _WBI_KEY_CACHE[cookie_hash] = (img_key, sub_key, now + _WBI_CACHE_TTL)
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




def check_all_tasks_finished(version, period, task_type, cookies):
    """查询某类型任务的所有完成情况
    返回: (all_finished: bool, details: list[dict])
    details中每个元素包含: task_id, name, finished, status, message, award
    注意: 查询失败的任务标记为finished=None，表示未知状态，不计入未完成
    """
    tasks = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
    if not tasks:
        return False, []

    details = []
    all_finished = True
    has_unknown = False

    for idx, task in enumerate(tasks):
        # 请求间隔，避免频率过高（每个任务之间等待500ms）
        if idx > 0:
            time.sleep(0.5)

        task_finished = None
        status = -1
        message = ""
        total_stock = 0
        day_stock = 0
        used_cache = False

        # 先检查缓存：已领取或无剩余总量的任务可以直接使用缓存
        # P1-O/P1-P: 缓存键加账号(cookies哈希)+日期，避免跨账号污染和跨日缓存
        task_id = task["task_id"]
        _today = time.strftime("%Y-%m-%d")
        _account_hash = str(hash(str(sorted(cookies.items()))))[:8] if cookies else "unknown"
        _cache_key = f"{task_id}_{_account_hash}_{_today}"
        if _cache_key in _mission_info_cache:
            cached = _mission_info_cache[_cache_key]
            cache_age = time.time() - cached.get("timestamp", 0)
            # 缓存有效条件：库存为0 或 已领取(status=6)，且缓存时间在24小时内
            # 注意：未完成但库存>0的任务不缓存（还有完成机会，需要每次扫一遍）
            # 注意：status=2每日库存上限且库存>0的任务不使用缓存（明日可能可领）
            cached_status = cached.get("status", -1)
            cached_total_stock = cached.get("total_stock", 0)
            cached_msg = cached.get("message", "")
            is_cached_daily_limit = (cached_status == 2 and ("每日库存" in cached_msg or "上限" in cached_msg or "今日" in cached_msg) and cached_total_stock > 0)
            if cache_age < _MISSION_CACHE_TTL:
                if (cached_total_stock == 0 or cached_status == 6) and not is_cached_daily_limit:
                    task_finished = cached.get("finished")
                    status = cached.get("status", -1)
                    message = cached.get("message", "")
                    total_stock = cached.get("total_stock", 0)
                    day_stock = cached.get("day_stock", 0)
                    used_cache = True

        # 如果使用了缓存，跳过API查询
        if not used_cache:
            # 重试机制：最多重试2次
            for retry in range(2):
                try:
                    info, msg = get_mission_info(task["task_id"], cookies)
                    if info:
                        task_finished = info.get("task_finished", False)
                        status = info.get("status", 0)
                        message = info.get("message", "")
                        # 解析库存信息（剩余总量）
                        try:
                            day_stock, total_stock, stock_raw, stock_source, _, _, _ = parse_stock_info(info)
                        except Exception:
                            day_stock, total_stock, stock_raw, stock_source = 0, 0, {}, "parse_error"
                        # 更新缓存：库存为0 或 已领取(status=6)的任务加入缓存
                        # 注意：未完成但库存>0的任务不缓存（还有完成机会，需要每次扫一遍）
                        # 注意：status=2每日库存上限且库存>0的任务不缓存（明日可能可领）
                        is_daily_limit = (status == 2 and ("每日库存" in message or "上限" in message or "今日" in message) and total_stock > 0)
                        if (total_stock == 0 or status == 6) and not is_daily_limit:
                            _mission_info_cache[_cache_key] = {
                                "finished": task_finished,
                                "status": status,
                                "message": message,
                                "total_stock": total_stock,
                                "day_stock": day_stock,
                                "timestamp": time.time()
                            }
                        break
                    else:
                        message = f"查询失败: {msg}"
                        # 如果是频率过高，等待1秒后重试
                        if "-702" in msg or "频率" in msg:
                            time.sleep(1.0)
                            continue
                        break
                except Exception as e:
                    message = f"异常: {str(e)}"
                    time.sleep(0.5)

        details.append({
            "task_id": task["task_id"],
            "name": task["name"],
            "finished": task_finished,
            "status": status,
            "message": message,
            "award": task.get("award", ""),
            "total_stock": total_stock,  # 剩余总量（百分比）
            "day_stock": day_stock,       # 今日剩余（百分比）
            "from_cache": used_cache      # 是否来自缓存
        })

        if task_finished is None:
            # 查询失败，标记为未知状态
            has_unknown = True
        elif not task_finished:
            all_finished = False

    # 如果有查询失败的任务，且所有成功查询的任务都已完成，则结果为未知（不判定为false）
    if has_unknown and all_finished:
        all_finished = None  # None表示未知

    return all_finished, details

def get_award_record(activity_id, cookies_dict):
    """获取领取记录（含兑换码）"""
    img_key, sub_key = get_wbi_keys(cookies_dict)
    if not img_key:
        return None, "获取WBI密钥失败"

    headers = {
        **HEADERS,
        "Referer": "https://www.bilibili.com/blackboard/era/award-exchange.html",
        "Origin": "https://www.bilibili.com",
        "Accept": "*/*",
    }
    params = {
        "activity_id": activity_id,
        "web_location": "888.126558",
    }
    signed_params = wbi_sign(params, img_key, sub_key)

    try:
        resp = requests.get(MISSION_MYLIST_API, headers=headers, cookies=cookies_dict, params=signed_params, timeout=10)
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


def receive_reward(task_id, task_info, cookies_dict, csrf, session=None):
    """领取奖励（session可选，复用预热连接）"""
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
        if session:
            resp = session.post(MISSION_RECEIVE_API, headers=headers, cookies=cookies_dict, data=data, timeout=10)
        else:
            resp = requests.post(MISSION_RECEIVE_API, headers=headers, cookies=cookies_dict, data=data, timeout=10)
        result = resp.json()
        code = result.get("code")
        message = result.get("message", "")

        if code == 0:
            # 保存最后一次领取成功的数据，供兑换码提取使用
            global _last_claim_data_global, _last_claim_result_global
            _last_claim_data_global = result.get("data")
            _last_claim_result_global = result
            return "success", "领取成功", result.get("data")

        # 识别已领取状态
        already_received_keywords = ["已领取", "已经领取", "重复领取", "已完成", "任务已完成", "不可重复领取"]
        if any(keyword in message for keyword in already_received_keywords):
            return "already", "已领取", result.get("data")

        return "failed", f"[{code}] {message}", None
    except Exception as e:
        return "failed", f"网络异常: {e}", None



# ========== 兑换码导出相关函数 ==========
CODE_EXPORT_FILE = str(BASE_DIR / "兑换码记录.json")

def _ensure_code_dir():
    """确保data目录存在"""
    d = os.path.dirname(CODE_EXPORT_FILE)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def extract_redeem_codes(data):
    """从API返回数据中递归提取兑换码"""
    codes = []
    if not data:
        return codes
    # 可能的兑换码字段名
    code_keys = ["cdk", "redeem_code", "redeemCode", "award_code", "awardCode",
                 "gift_code", "giftCode", "exchange_code", "exchangeCode",
                 "code", "key", "ticket", "coupon", "cdkey", "cd_key",
                 "cdkey_content", "cdkeyContent", "cdk_content", "cdkContent"]
    
    def search(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = k.lower()
                # 检查是否是兑换码字段
                if k_lower in [ck.lower() for ck in code_keys]:
                    if isinstance(v, str) and v and len(v) >= 4 and not v.startswith("http"):
                        # 排除明显不是兑换码的值
                        if v not in ["0", "1", "true", "false", "success", "ok"]:
                            codes.append({"field": k, "value": v, "path": path + "." + k})
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item and len(item) >= 4:
                                codes.append({"field": k, "value": item, "path": path + "." + k})
                search(v, path + "." + k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search(item, path + f"[{i}]")
    
    search(data)
    return codes

def save_redeem_code(task_name, account_name, data, task_period="", task_type=""):
    """领取成功后保存兑换码到本地文件（自动去重）"""
    try:
        _ensure_code_dir()
        codes = extract_redeem_codes(data)
        if not codes:
            return False, "未提取到兑换码"
        
        # 读取已有记录
        records = safe_load_json(CODE_EXPORT_FILE, [])
        
        # 构建已有兑换码集合（账户+兑换码 作为唯一键）
        existing_codes = set()
        for r in records:
            key = f"{r.get('account', '')}|{r.get('redeem_code', '')}"
            existing_codes.add(key)
        
        import time as _time
        timestamp = _time.strftime("%Y-%m-%d %H:%M:%S")
        
        saved_count = 0
        skipped_count = 0
        
        for code_info in codes:
            code_value = code_info["value"]
            # 检查是否已存在（相同账户+相同兑换码）
            unique_key = f"{account_name}|{code_value}"
            if unique_key in existing_codes:
                skipped_count += 1
                continue
            
            record = {
                "id": len(records) + 1,
                "time": timestamp,
                "task_name": task_name,
                "task_period": task_period,
                "task_type": task_type,
                "account": account_name,
                "code_field": code_info["field"],
                "redeem_code": code_value,
                "status": "未使用",
                "raw_path": code_info.get("path", "")
            }
            records.append(record)
            existing_codes.add(unique_key)
            saved_count += 1
        
        # 重新编号ID
        for i, r in enumerate(records):
            r["id"] = i + 1
        
        atomic_write_json(CODE_EXPORT_FILE, records)
        
        if skipped_count > 0:
            return True, f"已保存 {saved_count} 个兑换码，跳过 {skipped_count} 个重复"
        return True, f"已保存 {saved_count} 个兑换码"
    except Exception as e:
        return False, f"保存兑换码失败: {e}"

def load_redeem_codes():
    """读取所有兑换码记录"""
    try:
        if os.path.exists(CODE_EXPORT_FILE):
            with open(CODE_EXPORT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def update_redeem_code_status(record_id, status):
    """更新兑换码状态"""
    try:
        records = load_redeem_codes()
        for r in records:
            if r["id"] == record_id:
                r["status"] = status
                break
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, records)
        return True
    except:
        return False

def delete_redeem_code(record_id):
    """删除单条兑换码记录"""
    try:
        records = load_redeem_codes()
        records = [r for r in records if r["id"] != record_id]
        # 重新编号
        for i, r in enumerate(records):
            r["id"] = i + 1
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, records)
        return True
    except:
        return False

def clear_redeem_codes():
    """清空所有兑换码记录"""
    try:
        _ensure_code_dir()
        atomic_write_json(CODE_EXPORT_FILE, [])
        return True
    except:
        return False


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
    def __init__(self, parent, text, command=None, width=None, height=44,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):
        # 如果未指定宽度，根据文字自动计算
        if width is None:
            # 估算文字宽度（每个中文字符约12px，英文约7px，加上左右padding各20px）
            text_width = 0
            for ch in text:
                if '一' <= ch <= '鿿' or ch in "🚀⏹▶🔄⏰■":
                    text_width += 14
                else:
                    text_width += 8
            width = text_width + 70  # 左右padding各35px，留出空隙
            width = max(width, 100)  # 最小宽度100px
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
            try:
                self.command()
            except Exception as ex:
                import traceback
                print(f"[DarkButton错误] 按钮 {self.text} 的command执行异常: {ex}")
                traceback.print_exc()

    def set_state(self, state):
        if state == "disabled":
            self._draw("#444444")
            self.unbind("<Button-1>")
        else:
            self._draw(self.bg_color)
            self.bind("<Button-1>", self._on_click)

    def config(self, **kwargs):
        """兼容标准Tkinter按钮的config方法，支持state和text参数"""
        if "state" in kwargs:
            state = kwargs["state"]
            if state == tk.DISABLED:
                self.set_state("disabled")
            else:
                self.set_state("normal")
        if "text" in kwargs:
            self.text = kwargs["text"]
            # 重绘按钮文本，保持当前背景色
            current_bg = self.cget("bg")
            self._draw(current_bg if current_bg != COLORS["bg_card"] else self.bg_color)
        # 其他参数传给Canvas的config
        canvas_kwargs = {k: v for k, v in kwargs.items() if k not in ("state", "text")}
        if canvas_kwargs:
            super().config(**canvas_kwargs)


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
        if not sessdata or not bili_jct:
            messagebox.showwarning("提示", "SESSDATA 和 bili_jct 不能为空")
            return
        if self.on_add:
            # 备注名为空时，先验证获取用户名，默认使用用户名作为备注
            if not name:
                cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
                if dede:
                    cookie_str += f"; DedeUserID={dede}"
                ok, msg = verify_login(cookie_str)
                if not ok:
                    messagebox.showwarning("提示", f"登录验证失败: {msg}")
                    return
                name = msg  # 默认使用B站用户名作为备注
            ok, msg = self.on_add(name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)




class EditAccountDialog(tk.Toplevel):
    """编辑账户对话框（cookie失效时禁止修改）"""
    def __init__(self, parent, account, on_update=None):
        super().__init__(parent)
        self.title("编辑B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.account = account
        self.on_update = on_update
        self.old_name = account["name"]

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(frame, text="编辑B站账户", bg=COLORS["bg_dark"],
                         fg=COLORS["accent"], font=("微软雅黑", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 10))

        current_user = account.get("username", "未知")
        tk.Label(frame, text=f"当前登录用户: {current_user}", bg=COLORS["bg_dark"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 10))

        def add_field(label_text, show=None, default=""):
            lbl = tk.Label(frame, text=label_text, bg=COLORS["bg_dark"],
                           fg=COLORS["text_secondary"], font=("微软雅黑", 9))
            lbl.pack(anchor=tk.W, pady=(8, 3))
            entry = DarkEntry(frame, width=42)
            if show:
                entry.config(show=show)
            if default:
                entry.insert(0, default)
            entry.pack(anchor=tk.W, pady=(0, 5))
            return entry

        self.name_entry = add_field("账户备注名", default=account.get("name", ""))
        self.sess_entry = add_field("SESSDATA", show="*", default=account.get("SESSDATA", ""))
        self.jct_entry = add_field("bili_jct", show="*", default=account.get("bili_jct", ""))
        self.dede_entry = add_field("DedeUserID（可选）", default=account.get("DedeUserID", ""))

        btn_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        DarkButton(btn_frame, "显示/隐藏", command=self.toggle_show,
                   width=150, height=42, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT)
        DarkButton(btn_frame, "取消", command=self.destroy,
                   width=160, height=42, bg_color="#555577", text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(btn_frame, "验证并保存", command=self.on_submit,
                   width=160, height=42).pack(side=tk.RIGHT)

        self.update_idletasks()
        self.geometry("500x620")
        self.minsize(500, 620)
        self.resizable(False, False)
        x = (self.winfo_screenwidth() // 2) - 250
        y = (self.winfo_screenheight() // 2) - 310
        self.geometry(f"500x620+{x}+{y}")
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
        if self.on_update:
            ok, msg = self.on_update(self.old_name, name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)

# ========== 抢码工具窗口 ==========
class RushRewardFrame(tk.Frame):
    def __init__(self, parent, account_mgr, room_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
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

        # ========== 新模式精准抢码 ==========
        self.new_mode_running = False
        self.new_mode_thread = None
        self.new_mode_stop_flag = {"stop": False}
        self.rush_groups = self.load_rush_groups()
        self.current_group_id = None
        self.new_mode_mode_var = None
        # 调度器：每个组独立的运行状态和线程
        self.nm_group_threads = {}
        self.nm_group_stop_flags = {}
        self.nm_group_status = {}

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
        self.save_rush_groups()
        # 停止所有定时任务线程
        for task_id, stop_flag in self.scheduled_task_stop_flags.items():
            stop_flag["stop"] = True

    def load_scheduled_tasks(self):
        """加载定时任务列表，自动过滤掉已从ALL_TASKS中删除的任务"""
        tasks_file = BASE_DIR / "scheduled_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                # 过滤掉已从ALL_TASKS中删除的任务
                valid_task_ids = {t["task_id"] for t in ALL_TASKS}
                original_count = len(tasks)
                tasks = [t for t in tasks if t.get("task_id") in valid_task_ids]
                # 重置所有任务状态为等待中
                for task in tasks:
                    task["status"] = "等待中"
                # 如果有任务被清理，保存清理后的结果
                if len(tasks) != original_count:
                    try:
                        atomic_write_json(tasks_file, tasks)
                    except Exception:
                        pass
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
            atomic_write_json(tasks_file, tasks_to_save)
        except Exception:
            pass

    def load_rush_groups(self):
        """加载新模式任务组配置，自动过滤掉已从ALL_TASKS中删除的任务"""
        groups_file = BASE_DIR / "rush_groups.json"
        if groups_file.exists():
            try:
                with open(groups_file, "r", encoding="utf-8") as f:
                    groups = json.load(f)
                # 过滤掉已从ALL_TASKS中删除的任务（防止更新exe后旧任务重新出现）
                valid_task_ids = {t["task_id"] for t in ALL_TASKS}
                cleaned = False
                for group in groups:
                    original_count = len(group.get("tasks", []))
                    group["tasks"] = [t for t in group.get("tasks", []) if t.get("task_id") in valid_task_ids]
                    # 重新分配优先级
                    for i, t in enumerate(sorted(group["tasks"], key=lambda x: x.get("priority", 99))):
                        t["priority"] = i + 1
                    if len(group["tasks"]) != original_count:
                        cleaned = True
                # 删除空任务组
                groups = [g for g in groups if g.get("tasks")]
                if cleaned:
                    # 保存清理后的结果
                    try:
                        atomic_write_json(groups_file, groups)
                    except Exception:
                        pass
                return groups
            except Exception:
                pass
        return []

    def save_rush_groups(self):
        """保存新模式任务组配置"""
        try:
            groups_file = BASE_DIR / "rush_groups.json"
            atomic_write_json(groups_file, self.rush_groups)
        except Exception as e:
            self.nm_log(f"⚠ 保存任务组失败: {e}")

    def nm_save_ui_settings(self):
        """保存新模式UI设置"""
        try:
            settings = {
                "version": self.nm_version_var.get(),
                "period": self.nm_period_var.get(),
                "type": self.nm_type_var.get(),
                "task": self.nm_task_var.get(),
                "account": self.nm_account_var.get(),
                "window": self.nm_window_entry.get(),
                "group": self.nm_group_var.get(),
                "target_hour": self.nm_hour_var.get(),
                "target_minute": self.nm_minute_var.get(),
                "target_second": self.nm_second_var.get(),
                "target_ms": self.nm_ms_entry.get(),
            }
            settings_file = BASE_DIR / "rush_ui_settings.json"
            atomic_write_json(settings_file, settings)
        except Exception:
            pass

    def nm_load_ui_settings(self):
        """加载新模式UI设置"""
        try:
            settings_file = BASE_DIR / "rush_ui_settings.json"
            if not settings_file.exists():
                return
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            if settings.get("version"):
                self.nm_version_var.set(settings["version"])
                self.nm_on_version_change()
            if settings.get("period"):
                self.nm_period_var.set(settings["period"])
                self.nm_on_period_change()
            if settings.get("type"):
                self.nm_type_var.set(settings["type"])
                self.nm_update_task_list()
            if settings.get("task"):
                self.nm_task_var.set(settings["task"])
            if settings.get("account"):
                self.nm_account_var.set(settings["account"])
            if settings.get("window"):
                self.nm_window_entry.delete(0, tk.END)
                self.nm_window_entry.insert(0, settings["window"])
            if settings.get("group"):
                self.nm_group_var.set(settings["group"])
            if settings.get("group"):
                self.nm_group_var.set(settings["group"])
                self.nm_on_group_change()
            if settings.get("target_hour"):
                self.nm_hour_var.set(settings["target_hour"])
            if settings.get("target_minute"):
                self.nm_minute_var.set(settings["target_minute"])
            if settings.get("target_second"):
                self.nm_second_var.set(settings["target_second"])
            if settings.get("target_ms"):
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, settings["target_ms"])
        except Exception:
            pass

    def load_rush_config(self):
        """加载抢码工具配置"""
        default = {
            "version": "鸣潮3.7",
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
            atomic_write_json(rush_config_file, self.rush_config)
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

        # 模式切换栏
        mode_bar = tk.Frame(self, bg=COLORS["bg_card"], height=42)
        mode_bar.pack(fill=tk.X)
        mode_bar.pack_propagate(False)
        self.new_mode_mode_var = tk.StringVar(value="old")
        self.old_mode_btn = tk.Label(mode_bar, text="  旧模式  ", bg=COLORS["accent"], fg="#000000",
                                     font=("微软雅黑", 11, "bold"), padx=20, pady=6, cursor="hand2")
        self.old_mode_btn.pack(side=tk.LEFT, padx=(15, 5), pady=5)
        self.old_mode_btn.bind("<Button-1>", lambda e: self.switch_rush_mode("old"))
        self.new_mode_btn = tk.Label(mode_bar, text="  ✨ 新模式·精准抢码  ", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 11), padx=20, pady=6, cursor="hand2")
        self.new_mode_btn.pack(side=tk.LEFT, padx=(0, 15), pady=5)
        self.new_mode_btn.bind("<Button-1>", lambda e: self.switch_rush_mode("new"))

        # 旧模式内容区
        self.old_mode_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.old_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        main = self.old_mode_frame

        # 新模式内容区（默认隐藏）
        self.new_mode_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.build_new_mode_ui()

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
        self.version_var = tk.StringVar(value="鸣潮3.7")
        self.version_combo = ttk.Combobox(row1, textvariable=self.version_var,
                                           values=["鸣潮3.7", "原神7.1", "崩坏星穹铁道4.6", "绝区零3.2"], state="readonly",
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
        # 左侧按钮组
        left_frame = tk.Frame(btn_row, bg=COLORS["bg_card"])
        left_frame.pack(side=tk.LEFT)
        self.query_btn = DarkButton(left_frame, "🔍 查询状态", command=self.query_status,
                                     width=160, height=44, bg_color="#444466", text_color="#ffffff")
        self.query_btn.pack(side=tk.LEFT)
        self.manual_receive_btn = DarkButton(left_frame, "🎯 手动领取", command=self.manual_receive,
                                              width=160, height=44, bg_color="#ff6b35", text_color="#ffffff")
        self.manual_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_receive_now_btn = DarkButton(left_frame, "🚀 开始领取", command=self.start_receive_now,
                                                 width=160, height=44, bg_color="#e74c3c", text_color="#ffffff")
        self.start_receive_now_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.schedule_receive_btn = DarkButton(left_frame, "⏰ 定时领取", command=self.schedule_receive,
                                                width=160, height=44, bg_color="#9b59b6", text_color="#ffffff")
        self.schedule_receive_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.start_rush_btn = DarkButton(left_frame, "▶ 开始监控", command=self.start_rush,
                                          width=160, height=44, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_rush_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_rush_btn = DarkButton(left_frame, "■ 停止", command=self.stop_rush,
                                         width=160, height=42, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_rush_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.stop_rush_btn.set_state("disabled")
        # 右侧按钮组（查询全部完成、查询可领取、一键全部领取）
        right_frame = tk.Frame(btn_row, bg=COLORS["bg_card"])
        right_frame.pack(side=tk.RIGHT)
        self.claim_all_btn = DarkButton(right_frame, "🎁 一键全部领取", command=self.claim_all_finished,
                                         width=170, height=44, bg_color="#e67e22", text_color="#ffffff")
        self.claim_all_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self.check_all_finished_btn = DarkButton(right_frame, "✅ 查询全部完成", command=self.check_all_finished,
                                                  width=170, height=44, bg_color="#16a085", text_color="#ffffff")
        self.check_all_finished_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self.check_claimable_btn = DarkButton(right_frame, "📋 查询可领取", command=self.check_claimable_tasks,
                                               width=150, height=44, bg_color="#3498db", text_color="#ffffff")
        self.check_claimable_btn.pack(side=tk.RIGHT)

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
        col_widths = [550, 140, 300, 160, 110, 240]
        col_names = ["任务名称", "领取时间", "时长/间隔", "账户", "状态", "操作"]
        # 每列左边距：首列25，时长/间隔列后加大到35
        col_paddings = [25, 18, 18, 35, 18, 18]
        for i, (name, w) in enumerate(zip(col_names, col_widths)):
            col_frame = tk.Frame(header_frame, bg=COLORS["bg_input"], width=w, height=50)
            col_frame.pack(side=tk.LEFT, padx=(col_paddings[i], 0))
            col_frame.pack_propagate(False)
            tk.Label(col_frame, text=name, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 11, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=14)

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
            col_widths = [550, 140, 300, 160, 110, 240]

            # 任务名称（加版本信息括号，长文字自动换行）
            task_name = task.get("task_name", "未知任务")
            version = task.get("version", "")
            period = task.get("period", "")
            if version or period:
                version_info = f"{version}{period}" if version and period else (version or period)
                name_text = f"{task_name}（{version_info}）"
            else:
                name_text = task_name
            col1 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[0], height=60)
            col1.pack(side=tk.LEFT, padx=(25, 0))
            col1.pack_propagate(False)
            tk.Label(col1, text=name_text, bg=row_frame["bg"], fg=COLORS["text_primary"],
                     font=("微软雅黑", 10), anchor=tk.W, wraplength=col_widths[0]-20, justify=tk.LEFT).pack(side=tk.LEFT, padx=8, pady=8)

            # 领取时间
            time_text = f"{task.get('schedule_hour', '00')}:{task.get('schedule_minute', '00')}:{task.get('schedule_second', '00')}"
            col2 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[1], height=60)
            col2.pack(side=tk.LEFT, padx=(18, 0))
            col2.pack_propagate(False)
            tk.Label(col2, text=time_text, bg=row_frame["bg"], fg=COLORS["accent"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 时长/间隔
            interval_mode = task.get("interval_mode", "fixed")
            if interval_mode == "fixed":
                interval_text = f"{task.get('fixed_interval', '699')}ms"
            else:
                interval_text = f"{task.get('min_interval', '600')}~{task.get('max_interval', '800')}ms"
            dur_text = f"{task.get('duration', '20')}s/{interval_text}"
            col3 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[2], height=60)
            col3.pack(side=tk.LEFT, padx=(18, 0))
            col3.pack_propagate(False)
            tk.Label(col3, text=dur_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 账户
            accounts = task.get("account_names", [])
            acc_text = ",".join(accounts)[:10] if accounts else "未设置"
            col4 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[3], height=60)
            col4.pack(side=tk.LEFT, padx=(35, 0))
            col4.pack_propagate(False)
            tk.Label(col4, text=acc_text, bg=row_frame["bg"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 状态
            status = task.get("status", "等待中")
            status_color = COLORS["text_muted"]
            if status == "运行中":
                status_color = COLORS["success"]
            elif status == "已完成" or status == "已领取":
                status_color = COLORS["accent"]
            elif status == "失败":
                status_color = COLORS["danger"]
            col5 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[4], height=60)
            col5.pack(side=tk.LEFT, padx=(18, 0))
            col5.pack_propagate(False)
            tk.Label(col5, text=status, bg=row_frame["bg"], fg=status_color,
                     font=("微软雅黑", 10, "bold"), anchor=tk.W).pack(side=tk.LEFT, padx=8, pady=20)

            # 操作按钮
            col6 = tk.Frame(row_frame, bg=row_frame["bg"], width=col_widths[5], height=60)
            col6.pack(side=tk.LEFT, padx=(18, 0))
            col6.pack_propagate(False)
            btn_frame = tk.Frame(col6, bg=row_frame["bg"])
            btn_frame.pack(side=tk.LEFT, padx=4, pady=14)

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
                    initial_stock = day_s
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
                            current_stock = day_s
                            if current_stock > max_stock_seen:
                                max_stock_seen = current_stock
                    except Exception:
                        pass

                try:
                    ok, msg = self.do_receive_fast(task, task_info, account, None)
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
                        self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已完成"
                                break
                    break
                else:
                    self.log(f"  第{attempt}次: {msg} ({account['name']})")

                # 检测奖励是否已结束（202129），直接停止
                if "202129" in msg or "奖励领取已结束" in msg:
                    self.log(f"  ⚠ 奖励领取已结束，自动停止领取")
                    break

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

    def switch_rush_mode(self, mode):
        """切换抢码模式"""
        self.new_mode_mode_var.set(mode)
        if mode == "old":
            self.old_mode_btn.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 11, "bold"))
            self.new_mode_btn.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 11))
            self.new_mode_frame.pack_forget()
            self.old_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        else:
            self.new_mode_btn.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 11, "bold"))
            self.old_mode_btn.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 11))
            self.old_mode_frame.pack_forget()
            self.new_mode_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            self.refresh_new_mode_group_list()
            self.refresh_new_mode_task_list()

    def build_new_mode_ui(self):
        global ttk
        """构建新模式精准抢码UI（优化版：更直观，自动保存）"""
        frame = self.new_mode_frame

        # ===== 第一步：任务组管理（最顶部）=====
        group_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        group_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(group_card, text="① 任务组管理（选择/创建任务组，设置目标时间，自动保存）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        group_inner = tk.Frame(group_card, bg=COLORS["bg_card"])
        group_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：任务组选择+新建/删除
        grow1 = tk.Frame(group_inner, bg=COLORS["bg_card"])
        grow1.pack(fill=tk.X, pady=3)
        tk.Label(grow1, text="任务组", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_group_var = tk.StringVar()
        self.nm_group_combo = ttk.Combobox(grow1, textvariable=self.nm_group_var, values=[],
                                           state="readonly", width=20, font=("微软雅黑", 11))
        self.nm_group_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_group_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_on_group_change())

        self.nm_new_group_btn = tk.Button(grow1, text="+ 新建组", bg=COLORS["accent"], fg="#000000",
                                          font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_new_group)
        self.nm_new_group_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        self.nm_del_group_btn = tk.Button(grow1, text="删除当前组", bg="#c0392b", fg="#ffffff",
                                          font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_del_group)
        self.nm_del_group_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)

        # 第二行：目标时间设置（自动保存）
        grow2 = tk.Frame(group_inner, bg=COLORS["bg_card"])
        grow2.pack(fill=tk.X, pady=(8, 3))
        tk.Label(grow2, text="目标首发时间", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_hour_var = tk.StringVar(value="00")
        self.nm_hour_combo = ttk.Combobox(grow2, textvariable=self.nm_hour_var,
                                          values=[f"{h:02d}" for h in range(24)],
                                          state="readonly", width=4, font=("微软雅黑", 11))
        self.nm_hour_combo.pack(side=tk.LEFT, padx=(8, 2))
        self.nm_hour_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_auto_save_group())
        tk.Label(grow2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.nm_minute_var = tk.StringVar(value="00")
        self.nm_minute_combo = ttk.Combobox(grow2, textvariable=self.nm_minute_var,
                                            values=[f"{m:02d}" for m in range(60)],
                                            state="readonly", width=4, font=("微软雅黑", 11))
        self.nm_minute_combo.pack(side=tk.LEFT, padx=2)
        self.nm_minute_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_auto_save_group())
        tk.Label(grow2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.nm_second_var = tk.StringVar(value="00")
        self.nm_second_combo = ttk.Combobox(grow2, textvariable=self.nm_second_var,
                                            values=[f"{s:02d}" for s in range(60)],
                                            state="readonly", width=4, font=("微软雅黑", 11))
        self.nm_second_combo.pack(side=tk.LEFT, padx=2)
        self.nm_second_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_auto_save_group())
        tk.Label(grow2, text=".", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.nm_ms_var = tk.StringVar(value="000")
        self.nm_ms_entry = DarkEntry(grow2, width=4)
        self.nm_ms_entry.insert(0, "000")
        self.nm_ms_entry.pack(side=tk.LEFT, padx=2)
        self.nm_ms_entry.bind("<FocusOut>", lambda e: self.nm_auto_save_group())
        tk.Label(grow2, text="毫秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(2, 10))
        tk.Label(grow2, text="✓ 修改自动保存，组内所有任务统一首发时间", bg=COLORS["bg_card"],
                 fg=COLORS["success"], font=("微软雅黑", 10)).pack(side=tk.LEFT)


        # ===== 第二步：添加任务到当前组 =====
        add_card = tk.Frame(frame, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        add_card.pack(fill=tk.X, pady=(0, 8))
        tk.Label(add_card, text="② 添加任务到当前任务组（选择任务后点击添加）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        add_inner = tk.Frame(add_card, bg=COLORS["bg_card"])
        add_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：版本+期数+类型
        row1 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="版本", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_version_var = tk.StringVar(value="鸣潮3.7")
        self.nm_version_combo = ttk.Combobox(row1, textvariable=self.nm_version_var,
                                             values=["鸣潮3.7", "原神7.1", "崩坏星穹铁道4.6", "绝区零3.2"],
                                             state="readonly", width=14, font=("微软雅黑", 11))
        self.nm_version_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_version_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_on_version_change())

        tk.Label(row1, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_period_var = tk.StringVar()
        self.nm_period_combo = ttk.Combobox(row1, textvariable=self.nm_period_var,
                                            values=[],
                                            state="readonly", width=12, font=("微软雅黑", 11))
        self.nm_period_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_period_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_on_period_change())

        tk.Label(row1, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_type_var = tk.StringVar()
        self.nm_type_combo = ttk.Combobox(row1, textvariable=self.nm_type_var,
                                          values=[],
                                          state="readonly", width=12, font=("微软雅黑", 11))
        self.nm_type_combo.pack(side=tk.LEFT, padx=(8, 15))
        self.nm_type_combo.bind("<<ComboboxSelected>>", lambda e: self.nm_update_task_list())

        # 第二行：任务+账户
        row2 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="任务", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_task_var = tk.StringVar()
        self.nm_task_combo = ttk.Combobox(row2, textvariable=self.nm_task_var, values=[],
                                          state="readonly", width=35, font=("微软雅黑", 11))
        self.nm_task_combo.pack(side=tk.LEFT, padx=(8, 15))

        tk.Label(row2, text="账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_account_var = tk.StringVar()
        self.nm_account_combo = ttk.Combobox(row2, textvariable=self.nm_account_var, values=[],
                                             state="readonly", width=14, font=("微软雅黑", 11))
        self.nm_account_combo.pack(side=tk.LEFT, padx=(8, 15))

        # 第三行：窗口期+基础间隔+添加按钮
        row3 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="窗口期", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_window_var = tk.StringVar(value="15")
        self.nm_window_entry = DarkEntry(row3, width=5)
        self.nm_window_entry.insert(0, "15")
        self.nm_window_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row3, text="秒", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row3, text="基础间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.nm_base_interval_var = tk.StringVar(value="900")
        self.nm_base_interval_entry = DarkEntry(row3, width=6)
        self.nm_base_interval_entry.insert(0, "900")
        self.nm_base_interval_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row3, text="ms（风控后自动+20~40ms，上限1000ms）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 15))

        self.nm_add_task_btn = tk.Button(row3, text="+ 添加到当前组", bg=COLORS["accent"], fg="#000000",
                                         font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                                         command=self.nm_add_task)
        self.nm_add_task_btn.pack(side=tk.RIGHT, padx=10, ipadx=15, ipady=4)


        # ===== 主内容区域：左边任务列表+控制+调度器，右边日志 =====
        main_content = tk.Frame(frame, bg=COLORS["bg_dark"])
        main_content.pack(fill=tk.BOTH, expand=True)

        # 左边容器：组内任务 + 启动按钮 + 调度器
        left_container = tk.Frame(main_content, bg=COLORS["bg_dark"])
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 8))

        # 右边容器：日志区域（占据整个高度）
        right_container = tk.Frame(main_content, bg=COLORS["bg_dark"])
        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ===== 组内任务列表 =====
        list_card = tk.Frame(left_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(fill=tk.X, pady=(0, 4))
        list_title_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_title_frame.pack(fill=tk.X, padx=15, pady=(10, 8))
        tk.Label(list_title_frame, text="组内任务（按优先级依次执行）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        self.nm_query_all_btn = tk.Button(list_title_frame, text="🔍 批量查询状态", bg="#f39c12", fg="#ffffff",
                                          font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2",
                                          command=self.nm_query_all_tasks)
        self.nm_query_all_btn.pack(side=tk.RIGHT, ipadx=8, ipady=2)
        tk.Label(list_title_frame, text="●=可抢  ●=已领取  ●=不可抢  ●=未查询", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=10)

        # 表头
        list_header = tk.Frame(list_card, bg=COLORS["bg_input"])
        list_header.pack(fill=tk.X, padx=15)
        headers = [("状态", 4), ("优先级", 4), ("任务名称", 26), ("奖励", 12), ("窗口期", 5), ("账户", 10), ("操作(↑↓✎🔍×)", 22)]
        for text, width in headers:
            tk.Label(list_header, text=text, bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10, "bold"), width=width, anchor=tk.W).pack(side=tk.LEFT, padx=5, pady=5)

        # 任务列表容器（可滚动）
        list_container = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))
        self.nm_task_list_frame = tk.Frame(list_container, bg=COLORS["bg_card"])
        self.nm_task_list_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 启动控制 =====
        ctrl_card = tk.Frame(left_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        ctrl_card.pack(fill=tk.X, pady=(0, 8))
        ctrl_inner = tk.Frame(ctrl_card, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.X, padx=15, pady=4)

        self.nm_start_btn = DarkButton(ctrl_inner, text="🚀 启动精准抢码", command=self.nm_start_rush,
                                      height=44, bg_color=COLORS["accent"], text_color="#000000")
        self.nm_start_btn.pack(side=tk.LEFT, padx=6)
        self.nm_stop_btn = DarkButton(ctrl_inner, text="⏹ 停止", command=self.nm_stop_rush,
                                     height=44, bg_color="#c0392b", text_color="#ffffff")
        self.nm_stop_btn.pack(side=tk.LEFT, padx=6)
        self.nm_stop_btn.set_state("disabled")
        self.nm_sync_time_btn = DarkButton(ctrl_inner, text="🕐 同步系统时间", command=self.nm_sync_system_time,
                                           height=44, bg_color=COLORS["accent_hover"], text_color="#000000")
        self.nm_sync_time_btn.pack(side=tk.LEFT, padx=6)
        self.nm_query_time_btn = DarkButton(ctrl_inner, text="📊 查询时间状态", command=self.nm_query_time_status,
                                            height=44, bg_color="#2d3436", text_color=COLORS["text_primary"])
        self.nm_query_time_btn.pack(side=tk.LEFT, padx=6)
        self.nm_fix_time_btn = DarkButton(ctrl_inner, text="🔧 修复时间服务", command=self.nm_fix_time_service,
                                          height=44, bg_color="#e67e22", text_color="#ffffff")
        self.nm_fix_time_btn.pack(side=tk.LEFT, padx=6)
        self.nm_status_label = tk.Label(ctrl_inner, text="● 未运行", bg=COLORS["bg_card"],
                                        fg=COLORS["text_muted"], font=("微软雅黑", 11))
        self.nm_status_label.pack(side=tk.LEFT, padx=20)

        # ===== 日志 =====


        # ===== 任务组调度器（实时显示所有任务组状态）=====
        scheduler_card = tk.Frame(left_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        scheduler_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=(0, 0))
        scheduler_card.config(width=450)
        tk.Label(scheduler_card, text="📋 任务组调度器（实时更新，双击启动/停止）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        scheduler_inner = tk.Frame(scheduler_card, bg=COLORS["bg_card"])
        scheduler_inner.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # 使用Treeview显示调度器表格
        scheduler_style = ttk.Style()
        scheduler_style.configure("Scheduler.Treeview", 
            background=COLORS["bg_card"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_card"],
            font=("微软雅黑", 10),
            rowheight=28)
        scheduler_style.configure("Scheduler.Treeview.Heading",
            background=COLORS["bg_input"],
            foreground=COLORS["accent"],
            font=("微软雅黑", 10, "bold"))
        scheduler_style.map("Scheduler.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#000000")])
        
        scheduler_columns = ("group", "target_time", "status", "task_count", "remaining", "progress")
        self.nm_scheduler_tree = ttk.Treeview(scheduler_inner, columns=scheduler_columns, 
            show="headings", style="Scheduler.Treeview", height=10)
        
        self.nm_scheduler_tree.heading("group", text="任务组")
        self.nm_scheduler_tree.heading("target_time", text="目标时间")
        self.nm_scheduler_tree.heading("status", text="状态")
        self.nm_scheduler_tree.heading("task_count", text="任务数")
        self.nm_scheduler_tree.heading("remaining", text="剩余时间/进度")
        self.nm_scheduler_tree.heading("progress", text="完成情况")
        
        self.nm_scheduler_tree.column("group", width=120, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("target_time", width=100, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("status", width=80, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("task_count", width=60, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("remaining", width=140, anchor=tk.CENTER)
        self.nm_scheduler_tree.column("progress", width=150, anchor=tk.CENTER)
        
        # 不使用滚动条，高度由任务数量决定
        self.nm_scheduler_tree.pack(fill=tk.X, expand=True)
        
        # 双击事件：启动/停止选中的任务组
        self.nm_scheduler_tree.bind("<Double-1>", lambda e: self.nm_scheduler_toggle())
        
        # 操作按钮（圆角）
        scheduler_btn_frame = tk.Frame(scheduler_card, bg=COLORS["bg_card"])
        scheduler_btn_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        DarkButton(scheduler_btn_frame, text="▶ 启动选中组", command=self.nm_scheduler_start_selected,
                  height=44, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="⏹ 停止选中组", command=self.nm_scheduler_stop_selected,
                  height=44, bg_color="#c0392b", text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="⏹ 停止全部", command=self.nm_stop_rush,
                  height=44, bg_color="#e74c3c", text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="🔄 刷新", command=self.nm_update_scheduler,
                  height=44, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]).pack(side=tk.LEFT)
        
        # 状态颜色标签
        color_frame = tk.Frame(scheduler_btn_frame, bg=COLORS["bg_card"])
        color_frame.pack(side=tk.RIGHT)
        tk.Label(color_frame, text="● 未启动", bg=COLORS["bg_card"], fg="#95a5a6",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 等待中", bg=COLORS["bg_card"], fg="#3498db",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 运行中", bg=COLORS["bg_card"], fg=COLORS["success"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 已完成", bg=COLORS["bg_card"], fg="#27ae60",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(color_frame, text="● 已停止", bg=COLORS["bg_card"], fg="#f39c12",
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        
        # 启动定时更新（每秒更新一次）
        self.nm_scheduler_running = True
        self.nm_scheduler_update_loop()

        log_card = tk.Frame(right_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="抢码日志（详细模式）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        log_inner = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        self.nm_log_text = tk.Text(log_inner, bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                                   font=("Consolas", 10), wrap=tk.WORD, height=8)
        nm_log_scroll = ttk.Scrollbar(log_inner, command=self.nm_log_text.yview)
        self.nm_log_text.config(yscrollcommand=nm_log_scroll.set)
        nm_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.nm_log_text.pack(fill=tk.BOTH, expand=True)

        # 初始化任务列表（动态加载期数/类型/任务）
        self.nm_on_version_change()
        # 加载保存的UI设置
        self.nm_load_ui_settings()

    def nm_log(self, msg):
        """新模式日志输出（毫秒级时间戳）- 线程安全"""
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
        line = f"[{timestamp}] {msg}\n"
        # UI操作必须在主线程执行
        def _append_log():
            try:
                self.nm_log_text.insert(tk.END, line)
                self.nm_log_text.see(tk.END)
            except Exception:
                pass
        try:
            self.after(0, _append_log)
        except Exception:
            pass
        # 同时写主日志文件（文件IO是线程安全的）
        try:
            self.log(msg)
        except Exception:
            pass

    # ========== 新模式·任务组管理 ==========
    def refresh_new_mode_group_list(self):
        """刷新任务组下拉列表"""
        group_names = [g["group_name"] for g in self.rush_groups]
        self.nm_group_combo.config(values=group_names)
        if self.rush_groups and not self.current_group_id:
            self.current_group_id = self.rush_groups[0]["group_id"]
        if self.current_group_id:
            current = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
            if current:
                self.nm_group_var.set(current["group_name"])
            else:
                self.nm_group_var.set("")
        elif not self.rush_groups:
            self.nm_group_var.set("")
        # 同时刷新调度器
        if hasattr(self, 'nm_scheduler_frame'):
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    def refresh_new_mode_task_list(self):
        """刷新组内任务列表"""
        # 清空现有列表
        for widget in self.nm_task_list_frame.winfo_children():
            widget.destroy()
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        tasks = sorted(group.get("tasks", []), key=lambda t: t.get("priority", 99))
        for i, task in enumerate(tasks):
            row = tk.Frame(self.nm_task_list_frame, bg=COLORS["bg_card"])
            row.pack(fill=tk.X, pady=2)
            # 状态圆点
            status_color = task.get("status_color", "gray")
            color_map = {"green": "#2ecc71", "red": "#e74c3c", "blue": "#3498db", "gray": "#7f8c8d"}
            dot_color = color_map.get(status_color, "#7f8c8d")
            status_text = task.get("status_text", "未查询")
            tk.Label(row, text="●", bg=COLORS["bg_card"], fg=dot_color,
                     font=("微软雅黑", 12, "bold"), width=4, anchor=tk.W,
                     textvariable=None).pack(side=tk.LEFT, padx=5)
            # 给状态圆点添加tooltip
            try:
                from tkinter import ttk as _ttk
                status_label = row.winfo_children()[-1]
                ToolTip(status_label, status_text)
            except Exception:
                pass
            tk.Label(row, text=str(task.get("priority", i+1)), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), width=4, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("name", "")[:26], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 10), width=26, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("award", "")[:12], bg=COLORS["bg_card"],
                     fg=COLORS["success"], font=("微软雅黑", 10), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=f"{task.get('window_seconds', 15)}秒", bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=5, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=task.get("account_name", "")[:10], bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            # 操作按钮
            btn_frame = tk.Frame(row, bg=COLORS["bg_card"])
            btn_frame.pack(side=tk.LEFT, padx=5)
            tk.Button(btn_frame, text="↑", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                      font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_move_task(tid, -1)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="↓", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                      font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_move_task(tid, 1)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="✎", bg="#3498db", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_edit_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="🔍", bg="#f39c12", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda t=task: self.nm_query_single_task(t)).pack(side=tk.LEFT, padx=1)
            tk.Button(btn_frame, text="×", bg="#c0392b", fg="#ffffff",
                      font=("微软雅黑", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=2,
                      command=lambda tid=task["task_id"]: self.nm_remove_task(tid)).pack(side=tk.LEFT, padx=1)

    def nm_on_version_change(self):
        """版本切换：动态更新期数下拉框"""
        version = self.nm_version_var.get()
        periods = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] not in periods:
                periods.append(t["period"])
        self.nm_period_combo.config(values=periods)
        if periods:
            self.nm_period_var.set(periods[0])
        self.nm_on_period_change()

    def nm_on_period_change(self):
        """期数切换：动态更新类型下拉框"""
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        types = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] not in types:
                types.append(t["type"])
        self.nm_type_combo.config(values=types)
        if types:
            self.nm_type_var.set(types[0])
        self.nm_update_task_list()

    def nm_update_task_list(self):
        """更新新模式任务下拉列表"""
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        tasks = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
        task_names = [f"{t['name']} => {t['award']}" for t in tasks]
        self.nm_task_combo.config(values=task_names)
        if task_names:
            self.nm_task_var.set(task_names[0])
        elif hasattr(self, 'nm_task_var'):
            self.nm_task_var.set('')
        # 更新账户列表
        accounts = self.account_mgr.accounts
        account_names = [a["name"] for a in accounts]
        self.nm_account_combo.config(values=account_names)
        if account_names and not self.nm_account_var.get():
            self.nm_account_var.set(account_names[0])

    def nm_on_group_change(self):
        """任务组切换"""
        group_name = self.nm_group_var.get()
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if group:
            self.current_group_id = group["group_id"]
            target_str = group.get("target_time", "00:00:00.000")
            try:
                parts = target_str.split(":")
                self.nm_hour_var.set(parts[0])
                self.nm_minute_var.set(parts[1])
                sec_parts = parts[2].split(".")
                self.nm_second_var.set(sec_parts[0])
                ms_val = sec_parts[1] if len(sec_parts) > 1 else "000"
                self.nm_ms_var.set(ms_val)
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, ms_val)
            except Exception:
                self.nm_hour_var.set("00")
                self.nm_minute_var.set("00")
                self.nm_second_var.set("00")
                self.nm_ms_var.set("000")
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, "000")
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_update_ui_state()
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    def nm_new_group(self):
        """新建任务组"""
        from tkinter import simpledialog
        name = simpledialog.askstring("新建任务组", "请输入任务组名称:", parent=self)
        if not name:
            return
        group_id = f"group_{int(time.time())}"
        new_group = {
            "group_id": group_id,
            "group_name": name,
            "target_time": "00:00:00.000",
            "tasks": []
        }
        self.rush_groups.append(new_group)
        self.current_group_id = group_id
        self.save_rush_groups()
        self.refresh_new_mode_group_list()
        # 更新下拉框选中值
        if hasattr(self, 'nm_group_var'):
            self.nm_group_var.set(name)
        self.refresh_new_mode_task_list()
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()
        self.nm_log(f"新建任务组: {name}")

    def nm_del_group(self):
        """删除当前任务组"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        from tkinter import messagebox
        if not messagebox.askyesno("确认删除", f"确定删除任务组「{group['group_name']}」吗？"):
            return
        deleted_name = group['group_name']
        self.rush_groups = [g for g in self.rush_groups if g["group_id"] != self.current_group_id]
        self.current_group_id = self.rush_groups[0]["group_id"] if self.rush_groups else None
        # 保存后立即验证，确保数据真正写入文件
        self.save_rush_groups()
        try:
            groups_file = BASE_DIR / "rush_groups.json"
            with open(groups_file, "r", encoding="utf-8") as f:
                verify_data = json.load(f)
            if any(g.get("group_name") == deleted_name for g in verify_data):
                self.nm_log(f"⚠ 删除验证失败：文件中仍存在任务组「{deleted_name}」，重试保存...")
                self.save_rush_groups()
        except Exception as e:
            self.nm_log(f"⚠ 删除验证异常: {e}")
        # 如果没有组了，清空下拉框
        if not self.rush_groups:
            self.nm_group_var.set("")
            self.nm_group_combo.config(values=[])
        self.refresh_new_mode_group_list()
        self.refresh_new_mode_task_list()
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()
        self.nm_log(f"删除任务组: {deleted_name}")

    def nm_add_task(self):
        """添加任务到当前组"""
        if not self.current_group_id:
            self.nm_log("请先选择或创建任务组")
            return
        task_text = self.nm_task_var.get()
        if not task_text:
            self.nm_log("请选择任务")
            return
        account_name = self.nm_account_var.get()
        if not account_name:
            self.nm_log("请选择账户")
            return
        # 从ALL_TASKS找到对应任务
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        task = None
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] == task_type and f"{t['name']} => {t['award']}" == task_text:
                task = t
                break
        if not task:
            self.nm_log("未找到对应任务")
            return
        try:
            window_seconds = int(self.nm_window_entry.get())
        except ValueError:
            window_seconds = 15
        try:
            base_interval = int(self.nm_base_interval_entry.get()) / 1000.0
            if base_interval < 0.3:
                base_interval = 0.3
            if base_interval > 2.0:
                base_interval = 2.0
        except ValueError:
            base_interval = 0.9
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            # 检查是否已存在
            if any(t["task_id"] == task["task_id"] for t in group["tasks"]):
                self.nm_log(f"任务已存在: {task['name']}")
                return
            # 优先级自动分配：当前组内最大优先级+1
            existing_priorities = [t["priority"] for t in group["tasks"]]
            priority = max(existing_priorities) + 1 if existing_priorities else 1
            # 获取act_id并保存（添加任务时一次性获取，抢码时直接使用）
            act_id = task.get("act_id", "")
            try:
                cookies = cookies_from_account(account)
                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    # 尝试多种字段名和层级
                    for key in ["act_id", "activity_id", "ActivityId", "id"]:
                        if info.get(key):
                            act_id = str(info[key])
                            break
                    if not act_id:
                        for sub_key in ["act_info", "activity_info", "mission_info", "data"]:
                            sub = info.get(sub_key, {})
                            if isinstance(sub, dict):
                                for key in ["act_id", "activity_id", "ActivityId", "id"]:
                                    if sub.get(key):
                                        act_id = str(sub[key])
                                        break
                            if act_id:
                                break
            except Exception:
                pass
            if not act_id:
                act_id = VERSION_DEFAULT_ACT_ID.get(version, "")

            new_task = {
                "task_id": task["task_id"],
                "name": task["name"],
                "award": task["award"],
                "period": task["period"],
                "type": task["type"],
                "version": task["version"],
                "account_name": account_name,
                "priority": priority,
                "window_seconds": window_seconds,
                "base_interval": base_interval,
                "act_id": act_id,
                "status_color": "gray",
                "status_text": "查询中...",
                "task_finished": None,
                "stock_available": None
            }
            group["tasks"].append(new_task)
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_log(f"添加任务: {task['name']} (优先级{priority}, 窗口期{window_seconds}秒, 基础间隔{int(base_interval*1000)}ms)")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()
            # 异步查询任务状态
            self.after(100, lambda t=new_task: self.nm_query_task_status_async(t))

    def nm_query_task_status_async(self, task):
        """异步查询任务状态（在后台线程中执行，避免阻塞UI）"""
        import threading
        def query_thread():
            try:
                result = self._do_query_task_status(task)
                # 回到主线程更新UI
                self.after(0, lambda: self._update_task_status(task, result))
            except Exception as e:
                self.after(0, lambda: self._update_task_status(task, {"error": str(e)}))
        threading.Thread(target=query_thread, daemon=True).start()

    def _do_query_task_status(self, task):
        """实际执行任务状态查询（在后台线程中调用）"""
        try:
            account_name = task.get("account_name", "")
            account = self.account_mgr.get_account(account_name)
            if not account:
                return {"error": "账户不存在"}
            cookies = cookies_from_account(account)
            info, msg = get_mission_info(task["task_id"], cookies)
            if not info:
                return {"error": msg or "查询失败"}
            task_finished = info.get("task_finished", False)
            stock_info = info.get("stock_info", {})
            # 库存判断：看剩余总库存 total_stock > 0（不是每日库存）
            total_stock = stock_info.get("total_stock", 0)
            total_remain = stock_info.get("total_remain_num", 0)
            day_remain = stock_info.get("day_remain_num", 0)
            # 有剩余总库存才算可抢（total_stock是剩余百分比，total_remain是剩余数量）
            stock_available = (total_stock > 0) or (total_remain > 0)
            status = info.get("status", -1)
            status_map = {0: "可领取", 1: "可领取", 2: "已领取/每日上限", 6: "已领取过", 7: "无资格", 11: "未到时间"}
            status_text = status_map.get(status, f"状态{status}")
            return {
                "task_finished": task_finished,
                "stock_available": stock_available,
                "total_stock": total_stock,
                "total_remain": total_remain,
                "status": status,
                "status_text": status_text
            }
        except Exception as e:
            return {"error": str(e)}

    def _update_task_status(self, task, result):
        """更新任务状态并刷新UI（在主线程中调用）"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        for t in group["tasks"]:
            if t.get("task_id") == task.get("task_id"):
                if "error" in result:
                    t["status_color"] = "gray"
                    t["status_text"] = f"查询失败: {result['error'][:20]}"
                    t["task_finished"] = None
                    t["stock_available"] = None
                else:
                    t["task_finished"] = result.get("task_finished")
                    t["stock_available"] = result.get("stock_available")
                    status_code = result.get("status", -1)
                    # 蓝色：已经领取过（只有status=6表示已领取过）
                    if status_code == 6:
                        t["status_color"] = "blue"
                        t["status_text"] = f"📦 已领取(status={status_code}) | 已领取过 | {result.get('status_text', '')}"
                    # 绿色：任务已完成 AND 有剩余总量 AND 不是已领取过(6)和无资格(7)
                    elif result.get("task_finished") and result.get("stock_available") and status_code not in [6, 7]:
                        t["status_color"] = "green"
                        # 详细说明状态
                        if status_code == 0 or status_code == 1:
                            status_detail = "可领取"
                        elif status_code == 2:
                            status_detail = "每日上限（总库存还有，明日可领）"
                        elif status_code == 11:
                            status_detail = "未到时间（任务已完成，到时间可领）"
                        else:
                            status_detail = result.get("status_text", "")
                        t["status_text"] = f"✓ 可抢(status={status_code}) | 已完成 | 剩余库存充足 | {status_detail}"
                    else:
                        t["status_color"] = "red"
                        reasons = []
                        if status_code == 2:
                            reasons.append("每日上限/库存已领完")
                        elif status_code == 7:
                            reasons.append("无资格")
                        elif status_code == 11:
                            reasons.append("未到时间")
                        elif status_code not in [0, 1, 6]:
                            reasons.append(f"状态{status_code}")
                        if not result.get("task_finished"):
                            reasons.append("未完成")
                        if not result.get("stock_available"):
                            reasons.append("剩余库存为0")
                        reasons_str = ",".join(reasons)
                        t["status_text"] = f"✗ 不可抢(status={status_code}) | {reasons_str} | {result.get('status_text', '')}"
                break
        self.save_rush_groups()
        self.refresh_new_mode_task_list()
        if "error" not in result:
            self.nm_log(f"[状态查询] {task.get('name', '')}: {task.get('status_text', '')}")

    def nm_query_single_task(self, task):
        """手动查询单个任务状态"""
        task["status_color"] = "gray"
        task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        self.nm_log(f"[手动查询] {task.get('name', '')}...")
        self.nm_query_task_status_async(task)

    def nm_query_all_tasks(self):
        """查询当前组内所有任务状态"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            return
        self.nm_log(f"[批量查询] 开始查询 {len(group['tasks'])} 个任务状态...")
        for task in group["tasks"]:
            task["status_color"] = "gray"
            task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        # 逐个查询，间隔1秒避免风控
        import threading
        def query_all_thread():
            for task in group["tasks"]:
                try:
                    result = self._do_query_task_status(task)
                    self.after(0, lambda t=task, r=result: self._update_task_status(t, r))
                except Exception as e:
                    self.after(0, lambda t=task, err=str(e): self._update_task_status(t, {"error": err}))
                time.sleep(1.0)
            self.after(0, lambda: self.nm_log("[批量查询] 全部查询完成"))
        threading.Thread(target=query_all_thread, daemon=True).start()

    def nm_edit_task(self, task):
        """编辑组内任务"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return

        # 创建编辑对话框
        edit_win = tk.Toplevel(self)
        edit_win.title(f"编辑任务 - {task.get('name', '')[:20]}")
        edit_win.geometry("520x420")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.transient(self)
        edit_win.grab_set()
        # 居中显示
        edit_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        edit_win.geometry(f"+{x}+{y}")

        # 任务信息显示
        info_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        tk.Label(info_frame, text="任务:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)
        tk.Label(info_frame, text=task.get("name", ""), bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 10, "bold"), wraplength=380, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 5))
        tk.Label(info_frame, text=f"奖励: {task.get('award', '')}", bg=COLORS["bg_card"], fg=COLORS["success"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)

        # 编辑区域
        edit_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        edit_frame.pack(fill=tk.X, padx=15, pady=10)

        # 窗口期
        row1 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=10)
        tk.Label(row1, text="窗口期(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        window_var = tk.StringVar(value=str(task.get("window_seconds", 15)))
        window_entry = tk.Entry(row1, textvariable=window_var, width=12, font=("微软雅黑", 10),
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        window_entry.pack(side=tk.LEFT, padx=5)

        # 账户选择
        row2 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=10)
        tk.Label(row2, text="账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        account_var = tk.StringVar(value=task.get("account_name", ""))
        # 获取所有账户
        account_names = []
        try:
            if hasattr(self, 'account_mgr') and self.account_mgr:
                accounts = self.account_mgr.get_all_accounts()
                account_names = [a.get("name", "") for a in accounts]
        except Exception:
            pass
        if not account_names:
            account_names = [task.get("account_name", "")]
        account_combo = ttk.Combobox(row2, textvariable=account_var, values=account_names,
                                     state="readonly", width=20, font=("微软雅黑", 10))
        account_combo.pack(side=tk.LEFT, padx=5)

        # 基础间隔
        row3 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=10)
        tk.Label(row3, text="基础间隔(ms):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        interval_var = tk.StringVar(value=str(int(task.get("base_interval", 0.9) * 1000)))
        interval_entry = tk.Entry(row3, textvariable=interval_var, width=12, font=("微软雅黑", 10),
                                  bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        interval_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(row3, text="(风控后自动+1~5ms)", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)

        # 按钮区域
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        def save_edit():
            """保存修改"""
            try:
                window_val = int(window_var.get())
                interval_ms = int(interval_var.get())
                if interval_ms < 300:
                    interval_ms = 300
                if interval_ms > 2000:
                    interval_ms = 2000
                interval_val = interval_ms / 1000.0
            except ValueError:
                messagebox.showerror("错误", "窗口期和基础间隔必须是数字", parent=edit_win)
                return

            # 找到任务并更新
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["window_seconds"] = window_val
                    t["account_name"] = account_var.get()
                    t["base_interval"] = interval_val
                    # 同时更新account_id（如果能找到）
                    try:
                        if hasattr(self, 'account_mgr') and self.account_mgr:
                            accounts = self.account_mgr.get_all_accounts()
                            for a in accounts:
                                if a.get("name") == account_var.get():
                                    t["account_id"] = a.get("id", a.get("account_id", ""))
                                    break
                    except Exception:
                        pass
                    break

            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"[编辑] 任务「{task.get('name', '')}」已更新: 窗口期={window_val}秒, 账户={account_var.get()}, 间隔={interval_ms}ms")
            edit_win.destroy()
            # 编辑后重新查询状态
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["status_color"] = "gray"
                    t["status_text"] = "查询中..."
                    self.refresh_new_mode_task_list()
                    self.nm_query_task_status_async(t)
                    break

        tk.Button(btn_frame, text="保存", bg=COLORS["success"], fg="#ffffff",
                  font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  command=save_edit).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)
        tk.Button(btn_frame, text="取消", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                  font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                  command=edit_win.destroy).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)

    def nm_remove_task(self, task_id):
        """从组中删除任务，删除后重新按1,2,3...分配优先级"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            group["tasks"] = [t for t in group["tasks"] if t["task_id"] != task_id]
            # 重新按顺序分配优先级
            tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            for i, t in enumerate(tasks):
                t["priority"] = i + 1
            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"删除任务，优先级已重新分配")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    def nm_move_task(self, task_id, direction):
        """调整任务优先级（上移/下移）"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
        idx = next((i for i, t in enumerate(tasks) if t["task_id"] == task_id), -1)
        if idx < 0:
            return
        swap_idx = idx + direction
        if swap_idx < 0 or swap_idx >= len(tasks):
            return
        # 交换任务位置后重新按1,2,3...分配优先级
        tasks[idx], tasks[swap_idx] = tasks[swap_idx], tasks[idx]
        for i_task, t in enumerate(tasks):
            t["priority"] = i_task + 1
        self.save_rush_groups()
        self.refresh_new_mode_task_list()
        self.nm_log(f"任务顺序已调整，优先级重新分配")
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()

    def nm_auto_save_group(self):
        """自动保存当前任务组设置（目标时间修改时触发）"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        try:
            hour = self.nm_hour_var.get()
            minute = self.nm_minute_var.get()
            second = self.nm_second_var.get()
            ms = self.nm_ms_entry.get().strip() or "000"
            target_time = f"{hour}:{minute}:{second}.{ms}"
            group["target_time"] = target_time
            self.save_rush_groups()
            self.nm_log(f"[自动保存] 任务组「{group['group_name']}」目标时间已更新为 {target_time}")
            # 同时刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()
        except Exception as e:
            pass

    def nm_save_group_settings(self):
        """保存任务组设置"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            ms_val = self.nm_ms_entry.get().strip()
            if not ms_val or not ms_val.isdigit():
                ms_val = "000"
            ms_val = ms_val.zfill(3)[:3]
            group["target_time"] = f"{self.nm_hour_var.get()}:{self.nm_minute_var.get()}:{self.nm_second_var.get()}.{ms_val}"
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.nm_log(f"任务组设置已保存: 目标时间={group['target_time']}")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    # ========== 新模式·任务组调度器 ==========
    def nm_refresh_scheduler(self):
        """刷新调度器列表"""
        for widget in self.nm_scheduler_frame.winfo_children():
            widget.destroy()
        for group in self.rush_groups:
            gid = group["group_id"]
            row = tk.Frame(self.nm_scheduler_frame, bg=COLORS["bg_card"])
            row.pack(fill=tk.X, pady=1)
            status = self.nm_group_status.get(gid, "等待中")
            status_color = COLORS["success"] if status == "运行中" else COLORS["text_muted"]
            tk.Label(row, text=group["group_name"], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 9), width=18, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=group.get("target_time", "00:00:00.000"), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 9, "bold"), width=12, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=str(len(group.get("tasks", []))), bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 9), width=6, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            tk.Label(row, text=status, bg=COLORS["bg_card"],
                     fg=status_color, font=("微软雅黑", 9, "bold"), width=10, anchor=tk.W).pack(side=tk.LEFT, padx=5)
            # 操作按钮
            btn_frame = tk.Frame(row, bg=COLORS["bg_card"])
            btn_frame.pack(side=tk.LEFT, padx=5)
            if status == "运行中":
                tk.Button(btn_frame, text="停止", bg="#c0392b", fg="#ffffff",
                          font=("微软雅黑", 8), relief=tk.FLAT, cursor="hand2", width=5,
                          command=lambda g=gid: self.nm_stop_single_group(g)).pack(side=tk.LEFT, padx=2)
            else:
                tk.Button(btn_frame, text="开始", bg=COLORS["success"], fg="#ffffff",
                          font=("微软雅黑", 8), relief=tk.FLAT, cursor="hand2", width=5,
                          command=lambda g=gid: self.nm_start_single_group(g)).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="切换", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                      font=("微软雅黑", 8), relief=tk.FLAT, cursor="hand2", width=5,
                      command=lambda g=gid: self.nm_switch_to_group(g)).pack(side=tk.LEFT, padx=2)

    def nm_switch_to_group(self, group_id):
        """从调度器切换到指定组"""
        group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
        if group:
            self.nm_group_var.set(group["group_name"])
            self.nm_on_group_change()

    def nm_start_single_group(self, group_id):
        """启动单个任务组（独立线程）"""
        group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
        if not group:
            return
        if not group.get("tasks"):
            self.nm_log(f"[{group['group_name']}] 任务组为空，无法启动")
            return
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            self.nm_log(f"[{group['group_name']}] 已在运行中")
            return
        # 启动时不再从界面读取时间覆盖group
        # 时间修改由自动保存（nm_auto_save_group）负责
        stop_flag = {"stop": False}
        self.nm_group_stop_flags[group_id] = stop_flag
        self.nm_group_status[group_id] = "running"
        thread = threading.Thread(target=self.nm_rush_worker_for_group, args=(group, stop_flag), daemon=True)
        self.nm_group_threads[group_id] = thread
        thread.start()
        self.nm_refresh_scheduler()
        self.nm_log(f"[调度器] 启动任务组: {group['group_name']} (目标: {group['target_time']})")

    def nm_stop_single_group(self, group_id):
        """停止单个任务组"""
        if group_id in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_group_status[group_id] = "stopped"
            self.nm_refresh_scheduler()
            group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
            if group:
                self.nm_log(f"[调度器] 停止任务组: {group['group_name']}")

    def nm_start_all_groups(self):
        """启动所有任务组"""
        count = 0
        for group in self.rush_groups:
            if group.get("tasks"):
                gid = group["group_id"]
                if gid not in self.nm_group_threads or not self.nm_group_threads[gid].is_alive():
                    self.nm_start_single_group(gid)
                    count += 1
        self.nm_log(f"[调度器] 全部开始: 启动了 {count} 个任务组")

    def nm_stop_all_groups(self):
        """停止所有任务组"""
        for group_id in list(self.nm_group_stop_flags.keys()):
            self.nm_stop_single_group(group_id)
        self.nm_log("[调度器] 全部停止")

    def nm_rush_worker_for_group(self, group, stop_flag):
        """单个任务组的抢码线程（调度器版本，使用独立stop_flag）"""
        gid = group["group_id"]
        try:
            self.nm_rush_worker(group)
        finally:
            if stop_flag.get("stop"):
                self.nm_group_status[gid] = "stopped"
            else:
                self.nm_group_status[gid] = "finished"
            # UI更新必须在主线程执行
            try:
                self.after(0, self.nm_refresh_scheduler)
            except Exception:
                pass
    def nm_start_rush(self):
        """启动精准抢码（支持多组同时运行）"""
        # P1-6: 新旧抢码互斥闸门
        if self.running:
            self.nm_log("⚠ 监控抢码正在运行中，请先停止后再启动精准抢码")
            return
        if not self.current_group_id:
            self.nm_log("请先选择任务组")
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            self.nm_log("任务组为空，请先添加任务")
            return
        
        group_id = group["group_id"]
        group_name = group["group_name"]
        
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            self.nm_log(f"任务组「{group_name}」已在运行中")
            return
        
        # 启动时不再从界面读取时间覆盖group
        # 时间修改由自动保存（nm_auto_save_group）负责，确保组的target_time是最新的
        
        self.nm_group_stop_flags[group_id] = {"stop": False}
        self.nm_group_status[group_id] = "running"
        self.nm_update_ui_state()
        
        self.nm_log("=" * 50)
        self.nm_log(f"启动精准抢码: {group_name}")
        self.nm_log(f"目标时间: {group['target_time']}")
        self.nm_log(f"任务数量: {len(group['tasks'])}")
        running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()]) + 1
        self.nm_log(f"当前运行组数: {running_count}")
        
        thread = threading.Thread(target=self.nm_rush_worker, args=(group, group_id), daemon=True)
        self.nm_group_threads[group_id] = thread
        thread.start()

    def nm_stop_rush(self):
        """停止所有正在运行的精准抢码任务组"""
        running_count = 0
        for group_id, stop_flag in self.nm_group_stop_flags.items():
            if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
                stop_flag["stop"] = True
                running_count += 1
                group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                group_name = group["group_name"] if group else group_id
                self.nm_log(f"发送停止指令: {group_name}")
        
        if running_count == 0:
            self.nm_log("没有正在运行的任务组")
        else:
            self.nm_log(f"已向 {running_count} 个任务组发送停止指令，等待当前请求完成后停止...")


    def nm_sync_system_time(self):
        """同步系统时间（需要管理员权限，显示窗口+等待完成+弹结果）"""
        import subprocess
        try:
            self.nm_log("正在请求管理员权限同步系统时间...")

            # 用ShellExecuteExW获取进程句柄，可等待结束
            class SHELLEXECUTEINFOW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong), ("fMask", ctypes.c_ulong),
                    ("hwnd", ctypes.c_void_p), ("lpVerb", ctypes.c_wchar_p),
                    ("lpFile", ctypes.c_wchar_p), ("lpParameters", ctypes.c_wchar_p),
                    ("lpDirectory", ctypes.c_wchar_p), ("nShow", ctypes.c_int),
                    ("hInstApp", ctypes.c_void_p), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p),
                    ("dwHotKey", ctypes.c_ulong), ("hIcon", ctypes.c_void_p),
                    ("hProcess", ctypes.c_void_p),
                ]

            see = SHELLEXECUTEINFOW()
            see.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
            see.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
            see.lpVerb = "runas"
            see.lpFile = "cmd.exe"
            see.lpParameters = "/c w32tm /resync /force & echo. & echo 同步完成，按任意键关闭 & pause >nul"
            see.nShow = 1  # SW_SHOWNORMAL，显示黑窗口

            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(see))
            if ok and see.hProcess:
                self.nm_log("✓ UAC已授权，正在同步（黑窗口显示执行过程）...")
                ctypes.windll.kernel32.WaitForSingleObject(see.hProcess, 30000)
                ctypes.windll.kernel32.CloseHandle(see.hProcess)
                # 同步后立即测NTP偏差
                try:
                    r = subprocess.run(
                        ["w32tm", "/stripchart", "/computer:ntp.aliyun.com", "/samples:3", "/dataonly"],
                        capture_output=True, text=True, timeout=15)
                    offs = []
                    for line in r.stdout.split('\n'):
                        if ',' in line and ('s' in line):
                            try:
                                v = line.split(',')[1].strip().replace('s', '').replace('+', '')
                                offs.append(abs(float(v) * 1000))
                            except Exception:
                                pass
                    if offs:
                        avg = sum(offs) / len(offs)
                        if avg < 100:
                            self.nm_log(f"✓ 同步成功，当前NTP偏差{avg:.0f}ms")
                            messagebox.showinfo("同步成功", f"系统时间同步完成！\n\n当前NTP偏差: {avg:.0f}ms\n（安全阈值 100ms）")
                        else:
                            self.nm_log(f"⚠ 同步完成但偏差仍有{avg:.0f}ms")
                            messagebox.showwarning("同步完成", f"同步已执行，但偏差仍较大:\n\n当前NTP偏差: {avg:.0f}ms\n建议再次同步")
                    else:
                        self.nm_log("✓ 同步命令已执行")
                        messagebox.showinfo("同步完成", "同步命令已执行，请查看抢码日志NTP偏差")
                except Exception as e:
                    self.nm_log(f"✓ 同步已执行（状态查询失败: {e}）")
                    messagebox.showinfo("同步完成", "同步命令已执行完成")
            else:
                self.nm_log("✗ 同步失败或用户取消UAC")
                messagebox.showerror("同步失败", "同步失败或用户取消了UAC授权")
        except Exception as e:
            self.nm_log(f"✗ 同步系统时间失败: {e}")
            messagebox.showerror("同步失败", f"同步系统时间失败:\n{e}")


    def nm_query_time_status(self):
        """查询系统时间同步状态"""
        import subprocess
        try:
            self.nm_log("正在查询系统时间同步状态...")
            # 查询W32Time服务状态
            result = subprocess.run(
                ["w32tm", "/query", "/status"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.nm_log("=" * 40)
                self.nm_log("📊 系统时间同步状态")
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        self.nm_log(f"  {line}")
                self.nm_log("=" * 40)
            else:
                # 可能服务没启动，尝试启动
                self.nm_log("查询失败，尝试启动W32Time服务...")
                start_result = subprocess.run(
                    ["net", "start", "w32time"],
                    capture_output=True, text=True, timeout=10
                )
                if "已经启动" in start_result.stdout or "started" in start_result.stdout.lower():
                    self.nm_log("W32Time服务已启动，请重新查询")
                else:
                    self.nm_log(f"查询失败: {result.stderr}")
                    self.nm_log("提示: 请先点击「同步系统时间」按钮，通过UAC授权后再查询")
        except Exception as e:
            self.nm_log(f"查询失败: {e}")


    def nm_fix_time_service(self):
        """一键修复时间服务：停止→注销→重注册→启动→配NTP→同步"""
        import subprocess
        try:
            self.nm_log("=" * 50)
            self.nm_log("🔧 开始修复时间服务（需要管理员权限）...")
            self.nm_log("   步骤: 停止服务 → 注销 → 重注册 → 启动 → 配NTP → 同步")

            # 写一个临时bat脚本执行完整修复流程
            bat_content = """@echo off
chcp 65001 >nul
echo ========================================
echo   时间服务修复工具
echo ========================================
echo.
echo [1/6] 停止 W32Time 服务...
net stop w32time
echo.
echo [2/6] 注销时间服务...
w32tm /unregister
echo.
echo [3/6] 重新注册时间服务...
w32tm /register
echo.
echo [4/6] 启动 W32Time 服务...
net start w32time
echo.
echo [5/6] 配置NTP服务器(阿里云+微软)...
w32tm /config /syncfromflags:manual /manualpeerlist:"ntp.aliyun.com time.windows.com ntp.tencent.com"
w32tm /config /update
echo.
echo [6/6] 强制同步时间...
w32tm /resync /force
echo.
echo ========================================
echo   修复完成！
echo ========================================
echo.
pause
"""
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_time_service.bat")
            with open(bat_path, "w", encoding="gbk") as f:
                f.write(bat_content)

            # 用ShellExecuteExW以管理员权限运行bat，等待完成
            class SHELLEXECUTEINFOW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong), ("fMask", ctypes.c_ulong),
                    ("hwnd", ctypes.c_void_p), ("lpVerb", ctypes.c_wchar_p),
                    ("lpFile", ctypes.c_wchar_p), ("lpParameters", ctypes.c_wchar_p),
                    ("lpDirectory", ctypes.c_wchar_p), ("nShow", ctypes.c_int),
                    ("hInstApp", ctypes.c_void_p), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p),
                    ("dwHotKey", ctypes.c_ulong), ("hIcon", ctypes.c_void_p),
                    ("hProcess", ctypes.c_void_p),
                ]

            see = SHELLEXECUTEINFOW()
            see.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
            see.fMask = 0x00000040
            see.lpVerb = "runas"
            see.lpFile = bat_path
            see.nShow = 1

            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(see))
            if ok and see.hProcess:
                self.nm_log("✓ UAC已授权，正在执行修复（黑窗口显示进度）...")
                ctypes.windll.kernel32.WaitForSingleObject(see.hProcess, 60000)
                ctypes.windll.kernel32.CloseHandle(see.hProcess)
                # 清理临时bat
                try:
                    os.remove(bat_path)
                except Exception:
                    pass
                # 修复后测偏差
                try:
                    r = subprocess.run(
                        ["w32tm", "/stripchart", "/computer:ntp.aliyun.com", "/samples:5", "/dataonly"],
                        capture_output=True, text=True, timeout=20)
                    offs = []
                    for line in r.stdout.split('\n'):
                        if ',' in line and 's' in line:
                            try:
                                v = line.split(',')[1].strip().replace('s', '').replace('+', '')
                                offs.append(abs(float(v) * 1000))
                            except Exception:
                                pass
                    if offs:
                        avg = sum(offs) / len(offs)
                        if avg < 100:
                            self.nm_log(f"✓ 修复成功！当前NTP偏差{avg:.0f}ms")
                            messagebox.showinfo("修复成功", f"时间服务修复完成！\n\n当前NTP偏差: {avg:.0f}ms\n（已恢复正常）")
                        else:
                            self.nm_log(f"⚠ 修复完成但偏差仍有{avg:.0f}ms")
                            messagebox.showwarning("修复完成", f"修复已执行，但偏差仍较大:\n\n当前NTP偏差: {avg:.0f}ms\n\n建议:\n1. 检查网络是否能访问NTP服务器\n2. 检查是否有其他软件修改系统时间\n3. 重启电脑后再试")
                    else:
                        self.nm_log("✓ 修复命令已执行")
                        messagebox.showinfo("修复完成", "时间服务修复已执行，请查看抢码日志NTP偏差")
                except Exception as e:
                    self.nm_log(f"✓ 修复已执行（查询偏差失败: {e}）")
                    messagebox.showinfo("修复完成", "时间服务修复已执行")
            else:
                self.nm_log("✗ 修复失败或用户取消UAC")
                messagebox.showerror("修复失败", "修复失败或用户取消了UAC授权")
            self.nm_log("=" * 50)
        except Exception as e:
            self.nm_log(f"✗ 修复时间服务失败: {e}")
            messagebox.showerror("修复失败", f"修复时间服务失败:\n{e}")


    def nm_update_ui_state(self):
        """更新UI状态（启动按钮/停止按钮/状态标签）"""
        try:
            running_groups = []
            for group_id, thread in self.nm_group_threads.items():
                if thread.is_alive():
                    group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                    group_name = group["group_name"] if group else group_id
                    running_groups.append(group_name)
            
            running_count = len(running_groups)
            
            current_running = False
            if self.current_group_id and self.current_group_id in self.nm_group_threads:
                current_running = self.nm_group_threads[self.current_group_id].is_alive()
            
            if current_running:
                self.nm_start_btn.config(state=tk.DISABLED)
                self.nm_stop_btn.config(state=tk.NORMAL)
            else:
                self.nm_start_btn.config(state=tk.NORMAL)
                self.nm_stop_btn.config(state=tk.NORMAL if running_count > 0 else tk.DISABLED)
            
            if running_count > 0:
                if running_count == 1:
                    status_text = f"● 运行中: {running_groups[0]}"
                else:
                    status_text = f"● {running_count}个组运行中"
                self.nm_status_label.config(text=status_text, fg=COLORS["success"])
            else:
                self.nm_status_label.config(text="● 未运行", fg=COLORS["text_muted"])
            
            try:
                group_names = []
                for g in self.rush_groups:
                    name = g["group_name"]
                    if g["group_id"] in self.nm_group_threads and self.nm_group_threads[g["group_id"]].is_alive():
                        name = f"▶ {name} (运行中)"
                    group_names.append(name)
                self.nm_group_combo.config(values=group_names)
            except Exception:
                pass
        except Exception:
            pass

    def nm_scheduler_update_loop(self):
        """调度器定时更新循环（每秒更新一次）"""
        if hasattr(self, 'nm_scheduler_running') and self.nm_scheduler_running:
            try:
                self.nm_update_scheduler()
            except Exception:
                pass
            self.after(1000, self.nm_scheduler_update_loop)
    
    def nm_update_scheduler(self):
        """更新调度器显示"""
        if not hasattr(self, 'nm_scheduler_tree'):
            return
        
        try:
            # 清空现有数据
            for item in self.nm_scheduler_tree.get_children():
                self.nm_scheduler_tree.delete(item)
            
            now = time.time()
            
            for group in self.rush_groups:
                group_id = group["group_id"]
                group_name = group["group_name"]
                target_time = group.get("target_time", "00:00:00.000")
                tasks = group.get("tasks", [])
                task_count = len(tasks)
                
                # 判断状态
                is_running = False
                is_finished = False
                is_stopped = False
                current_task_idx = 0
                total_attempts = 0
                success_count = 0
                
                if group_id in self.nm_group_threads:
                    thread = self.nm_group_threads[group_id]
                    if thread.is_alive():
                        is_running = True
                    else:
                        # 线程已结束，检查状态
                        status = self.nm_group_status.get(group_id, "stopped")
                        if status == "finished":
                            is_finished = True
                        elif status == "stopped":
                            is_stopped = True
                
                # 计算剩余时间
                remaining_text = "-"
                status_text = "未启动"
                status_color = "#95a5a6"
                progress_text = "-"
                
                if is_running:
                    # 解析目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        if now < target_ts:
                            remaining = target_ts - now
                            remaining_text = f"等待 {int(remaining//3600):02d}:{int((remaining%3600)//60):02d}:{int(remaining%60):02d}"
                            status_text = "等待中"
                            status_color = "#3498db"
                        else:
                            remaining_text = "执行中..."
                            status_text = "运行中"
                            status_color = COLORS["success"]
                    except Exception:
                        remaining_text = "执行中..."
                        status_text = "运行中"
                        status_color = COLORS["success"]
                    
                    progress_text = f"运行中"
                    
                elif is_finished:
                    status_text = "已完成"
                    status_color = "#27ae60"
                    remaining_text = "已结束"
                    progress_text = "全部完成"
                    
                elif is_stopped:
                    status_text = "已停止"
                    status_color = "#f39c12"
                    remaining_text = "已停止"
                    progress_text = "用户停止"
                    
                else:
                    # 未启动，计算距离目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        remaining = target_ts - now
                        if remaining < 3600:
                            remaining_text = f"{int(remaining//60)}分{int(remaining%60)}秒后"
                        else:
                            remaining_text = f"{int(remaining//3600)}时{int((remaining%3600)//60)}分后"
                    except Exception:
                        remaining_text = "-"
                
                # 插入到表格
                display_name = f"▶ {group_name}" if is_running else group_name
                item = self.nm_scheduler_tree.insert("", tk.END, values=(
                    display_name, target_time, status_text, task_count, remaining_text, progress_text
                ))
                
                # 设置行颜色
                self.nm_scheduler_tree.tag_configure("running", background="#1a3a1a")
                self.nm_scheduler_tree.tag_configure("waiting", background="#1a2a3a")
                self.nm_scheduler_tree.tag_configure("finished", background="#1a3a2a")
                self.nm_scheduler_tree.tag_configure("stopped", background="#3a2a1a")
                
                if is_running:
                    if "等待" in remaining_text:
                        self.nm_scheduler_tree.item(item, tags=("waiting",))
                    else:
                        self.nm_scheduler_tree.item(item, tags=("running",))
                elif is_finished:
                    self.nm_scheduler_tree.item(item, tags=("finished",))
                elif is_stopped:
                    self.nm_scheduler_tree.item(item, tags=("stopped",))
                    
        except Exception as e:
            pass
        
        # 动态调整Treeview高度，显示全部任务组
        try:
            group_count = len(self.rush_groups)
            # 至少显示3行，最多显示20行
            display_height = max(3, min(group_count, 20))
            self.nm_scheduler_tree.configure(height=display_height)
        except Exception:
            pass
    
    def nm_scheduler_toggle(self):
        """双击调度器项：启动/停止"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        # 找到对应的组
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        
        # 检查是否在运行
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            # 停止
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            # 启动
            self.current_group_id = group_id
            # 同步界面显示：更新任务组选择和时间输入框，避免启动时覆盖错误时间
            self.nm_group_var.set(group_name)
            self.nm_on_group_change()
            self.nm_start_rush()
    
    def nm_scheduler_start_selected(self):
        """启动选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        self.current_group_id = group["group_id"]
        # 同步界面显示：更新任务组选择和时间输入框，避免启动时覆盖错误时间
        self.nm_group_var.set(group_name)
        self.nm_on_group_change()
        self.nm_start_rush()
    
    def nm_scheduler_stop_selected(self):
        """停止选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        if group_id in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            self.nm_log(f"任务组「{group_name}」未在运行")

    def nm_rush_worker(self, group, group_id=None):
        """精准抢码核心线程"""
        """精准抢码核心线程（支持多组独立运行）"""
        if group_id is None:
            group_id = group.get("group_id", "default")
        if group_id not in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id] = {"stop": False}
        stop_flag = self.nm_group_stop_flags[group_id]
        group_name = group.get("group_name", "未知")
        try:
            stop_flag["last_request_time"] = 0  # 每个任务组独立维护最后请求时间
            target_time_str = group.get("target_time", "00:00:00.000")
            # 解析目标时间（支持毫秒）
            parts = target_time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            sec_parts = parts[2].split(".")
            second = int(sec_parts[0])
            millisecond = int(sec_parts[1]) if len(sec_parts) > 1 else 0

            now = time.localtime()
            target_timestamp = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hour, minute, second, 0, 0, -1)) + millisecond / 1000.0
            if target_timestamp < time.time():
                target_timestamp += 86400  # 等到明天

            wait_seconds = target_timestamp - time.time()
            self.nm_log(f"等待 {wait_seconds:.1f} 秒后开始（目标: {time.strftime('%H:%M:%S', time.localtime(target_timestamp))}）")

            # ===== 阶段1: NTP同步（抢码前1分钟或立即）=====
            ntp_offset = 0  # NTP偏差（秒），正数表示本地慢
            if wait_seconds > 60:
                # 等到抢码前1分钟再同步
                sync_time = target_timestamp - 60
                while time.time() < sync_time and not stop_flag["stop"]:
                    time.sleep(1)
                if not stop_flag["stop"]:
                    ntp_offset = self.nm_ntp_sync()
            else:
                ntp_offset = self.nm_ntp_sync()

            # ===== 阶段2: 等待到目标时间前2.5秒，连接预热 =====
            prewarm_time = target_timestamp - 2.5
            while time.time() < prewarm_time and not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if int(remaining) % 10 == 0 and int(remaining) > 0:
                    self.nm_log(f"  还剩 {int(remaining)} 秒...")
                time.sleep(0.5)

            if stop_flag["stop"]:
                self.nm_log("抢码已取消")
                return

            # 连接预热：提前2.5秒建立连接（并行建立，act_id已在添加任务时获取）
            self.nm_log("[连接预热] 提前2.5秒建立TCP连接（并行建立，act_id已在添加任务时获取）...")
            sessions = {}
            task_infos = {}
            import threading as _prewarm_threading
            prewarm_results = {}
            prewarm_lock = _prewarm_threading.Lock()
            
            def _prewarm_single_task(task):
                """单个任务的连接预热（在线程中执行）"""
                account = self.account_mgr.get_account(task["account_name"])
                if not account:
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("error", f"账户不存在: {task['account_name']}", None, None)
                    return
                session = requests.Session()
                session.headers.update(HEADERS)
                try:
                    session.get("https://www.bilibili.com", timeout=5)
                    # 【重要】清除预热时自动获取的cookie（buvid3/b_nut等），
                    # 避免与用户cookie合并导致B站反作弊返回[-351]错误
                    session.cookies.clear()
                    task_info = self.build_task_info_from_task(task)
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("ok", "", session, task_info)
                except Exception as e:
                    task_info = self.build_task_info_from_task(task)
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("error", str(e), session, task_info)
            
            # 并行建立所有连接
            prewarm_tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            prewarm_threads = []
            for task in prewarm_tasks:
                t = _prewarm_threading.Thread(target=_prewarm_single_task, args=(task,), daemon=True)
                prewarm_threads.append(t)
                t.start()
            # 等待所有预热完成（最多4秒）
            for t in prewarm_threads:
                t.join(timeout=4)
            # 收集结果（按优先级顺序输出日志）
            for task in prewarm_tasks:
                result = prewarm_results.get(task["task_id"], ("error", "预热超时", None, None))
                status, msg, session, task_info = result
                if session:
                    sessions[task["task_id"]] = session
                if task_info:
                    task_infos[task["task_id"]] = task_info
                else:
                    task_infos[task["task_id"]] = self.build_task_info_from_task(task)
                if status == "ok":
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, act_id={task_infos[task['task_id']].get('act_id', '')}")
                else:
                    self.nm_log(f"  ⚠ {task['name']}: 连接预热异常: {msg}, 使用保存的act_id={task_infos[task['task_id']].get('act_id', '')}")

            # 计算提前量：基础提前量 + NTP偏差修正
            # NTP offset = ((t2-t1)+(t3-t4))/2，正数=本地慢于服务器，需要更多提前量
            base_advance = 100  # 基础提前量100ms（实测高峰期单向RTT约120ms，目标到达时间=目标后约20ms）
            ntp_correction = ntp_offset * 1000  # NTP偏差转ms
            dynamic_advance = base_advance + ntp_correction
            # 限制范围：0ms ~ 1500ms，避免异常值
            dynamic_advance = max(0, min(1500, dynamic_advance))

            # NTP偏差过大时强制警告（>100ms会显著影响首枪精度）
            if abs(ntp_correction) > 100:
                self.nm_log(f"[⚠️ NTP偏差警告] 当前偏差{ntp_correction:.0f}ms，超过100ms安全阈值！")
                self.nm_log(f"[⚠️ NTP偏差警告] 首枪 timing 误差可能超过±100ms，建议立即同步系统时间后重试")
                try:
                    self.after(0, lambda: messagebox.showwarning("NTP时间偏差过大",
                        f"当前系统时间与NTP服务器偏差 {ntp_correction:.0f}ms\n"
                        f"超过100ms安全阈值，抢码 timing 可能失准！\n\n"
                        f"建议：点击「同步系统时间」按钮或手动执行 w32tm /resync"))
                except Exception:
                    pass
            elif abs(ntp_correction) > 10:
                self.nm_log(f"[提前量修正] 基础{base_advance}ms + NTP偏差{ntp_correction:.0f}ms = {dynamic_advance:.0f}ms")
            else:
                self.nm_log(f"[固定提前量] {dynamic_advance:.0f}ms (首次请求目标后约50ms到达)")

            # ===== 阶段3: 精准首发（自旋等待到目标时间-动态提前量）=====
            fire_time = target_timestamp - dynamic_advance / 1000.0
            now_time = time.time()

            # P2-5: 用perf_counter做精确自旋等待，timeBeginPeriod提高Windows定时器精度
            try:
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass
            _perf_start = time.perf_counter()
            _time_start = now_time
            fire_time_perf = _perf_start + (fire_time - _time_start)

            # 如果预热超时导致fire_time已过，立即发送（不再等待）
            if now_time >= fire_time:
                self.nm_log(f"[精准首发] 预热已超时({(now_time - target_timestamp)*1000:.0f}ms)，立即发送")
            else:
                self.nm_log(f"[精准首发] 目标 {target_time_str}，提前{dynamic_advance:.0f}ms发送，自旋等待中...")
                while time.perf_counter() < fire_time_perf and not stop_flag["stop"]:
                    remaining = fire_time_perf - time.perf_counter()
                    if remaining > 0.1:
                        time.sleep(remaining / 2)
                    elif remaining > 0.02:
                        time.sleep(0.001)
                    # 小于20ms时自旋（忙等待），避免Windows sleep精度问题

            if stop_flag["stop"]:
                self.nm_log("抢码已取消")
                try:
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
                return

            actual_fire = time.time()
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
            self.nm_log(f"[精准首发] 发送！目标偏差: {(actual_fire - target_timestamp)*1000:.1f}ms")

            # ===== 阶段4: 按优先级依次执行任务 =====
            tasks_sorted = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            for task in tasks_sorted:
                if stop_flag["stop"]:
                    break

                task_deadline = target_timestamp + task.get("window_seconds", 15)
                if time.time() > task_deadline:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] {task['name']} 已过窗口期，跳过")
                    continue

                self.nm_log(f"[优先级{task.get('priority', '?')}] 开始: {task['name']} => {task['award']} (窗口期{task.get('window_seconds', 15)}秒)")

                success = self.nm_execute_task(task, task_infos.get(task["task_id"]),
                                               sessions.get(task["task_id"]), task_deadline, stop_flag)

                if success:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✓ 领取成功，立即启动下一个优先级")
                else:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✗ 未成功，启动下一个优先级")
                
                # 切换优先级前补足请求间隔，避免连续快速请求触发风控
                task_index = tasks_sorted.index(task)
                if task_index < len(tasks_sorted) - 1 and not stop_flag["stop"]:
                    switch_interval = task.get("base_interval", 0.9)
                    elapsed = time.time() - stop_flag.get("last_request_time", 0)
                    wait_time = switch_interval - elapsed
                    if wait_time > 0:
                        self.nm_log(f"  距上次请求 {elapsed*1000:.0f}ms，补足 {wait_time*1000:.0f}ms 后切换...")
                        time.sleep(wait_time)
                    else:
                        self.nm_log(f"  距上次请求 {elapsed*1000:.0f}ms，已超过间隔，立即切换")

            self.nm_log("=" * 50)
            self.nm_log("精准抢码全部结束")

        except Exception as e:
            self.nm_log(f"抢码异常: {e}")
            import traceback
            self.nm_log(traceback.format_exc())
        finally:
            self.nm_group_status[group_id] = "finished"
            if group_id in self.nm_group_threads:
                del self.nm_group_threads[group_id]
            try:
                self.after(0, lambda: self.nm_update_ui_state())
            except Exception:
                pass
            self.nm_log(f"任务组「{group_name}」已结束")
            running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()])
            if running_count > 0:
                self.nm_log(f"还有 {running_count} 个任务组正在运行")

    def nm_ntp_sync(self):
        """NTP时间同步（使用socket方式，不依赖第三方库）"""
        import struct
        import socket
        ntp_servers = ["ntp.aliyun.com", "ntp.tencent.com", "cn.pool.ntp.org", "time.windows.com"]
        for server in ntp_servers:
            client = None
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.settimeout(3)
                # NTP请求包：LI=0, VN=3, Mode=3 (client)
                data = b'\x1b' + 47 * b'\0'
                t1 = time.time()
                client.sendto(data, (server, 123))
                data, address = client.recvfrom(1024)
                t4 = time.time()
                if data:
                    # 解析NTP响应
                    unpacked = struct.unpack('!12I', data[0:48])
                    # 接收时间戳 (t2) 和 发送时间戳 (t3)
                    t2 = unpacked[8] - 2208988800 + unpacked[9] / 4294967296.0
                    t3 = unpacked[10] - 2208988800 + unpacked[11] / 4294967296.0
                    # 计算偏差: offset = ((t2-t1) + (t3-t4)) / 2
                    offset = ((t2 - t1) + (t3 - t4)) / 2.0
                    self.nm_log(f"[NTP同步] 服务器={server}, 偏差={offset*1000:.1f}ms")
                    if abs(offset) > 0.5:
                        self.nm_log(f"[NTP同步] 偏差较大，建议手动同步系统时间")
                    return offset
            except Exception:
                continue
            finally:
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
        self.nm_log("[NTP同步] 所有NTP服务器均不可用，使用本地时间")
        return 0

    def nm_execute_task(self, task, task_info, session, deadline, stop_flag):
        """执行单个任务的抢码（带风控递增延迟）"""
        account = self.account_mgr.get_account(task["account_name"])
        if not account:
            self.nm_log(f"  账户不存在: {task['account_name']}")
            return False

        cookies = cookies_from_account(account)
        if not task_info:
            task_info = self.build_task_info_from_task(task)

        # 预生成随机波动数列（±30ms），提前计算好避免运行时随机开销
        import random
        random_fluctuations = [random.randint(-30, 30) for _ in range(100)]

        base_interval = task.get("base_interval", 0.9)  # 从任务配置读取，默认900ms
        current_interval = base_interval
        attempt = 0
        success = False

        while time.time() < deadline and not stop_flag["stop"]:
            attempt += 1
            try:
                stop_flag["last_request_time"] = time.time()  # 记录请求发出时间（每组独立）
                ok, msg = self.do_receive_fast(task, task_info, account, session)
                recv_time = time.time()
                last_req = stop_flag.get("last_request_time", 0)
                rtt_ms = (recv_time - last_req) * 1000
                send_str = time.strftime("%H:%M:%S", time.localtime(last_req)) + "." + str(int((last_req % 1) * 1000)).zfill(3)
                recv_str = time.strftime("%H:%M:%S", time.localtime(recv_time)) + "." + str(int((recv_time % 1) * 1000)).zfill(3)
            except Exception as e:
                ok, msg = False, f"异常: {e}"
                recv_time = time.time()
                last_req = stop_flag.get("last_request_time", 0)
                rtt_ms = (recv_time - last_req) * 1000 if last_req > 0 else 0
                send_str = time.strftime("%H:%M:%S", time.localtime(last_req)) + "." + str(int((last_req % 1) * 1000)).zfill(3) if last_req > 0 else "??:??:??.???"
                recv_str = time.strftime("%H:%M:%S", time.localtime(recv_time)) + "." + str(int((recv_time % 1) * 1000)).zfill(3)

            if ok:
                success = True
                self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 🎉 第{attempt}次: 领取成功！({task['account_name']})")
                self.nm_log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                break
            else:
                # 判断是否是未到领奖时间（202120），这种情况不切下一个优先级
                if "202120" in msg or "未到领取时间" in msg or "未到领奖时间" in msg:
                    self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 未到领取时间，继续等待... ({msg[:30]})")
                elif "75255" in msg or "库存已经使用完" in msg or "库存已使用完" in msg:
                    # 从deadline反推目标时间，判断是否超过目标后5秒
                    _window = task.get("window_seconds", 15)
                    _target_time = deadline - _window
                    _elapsed_after_target = time.time() - _target_time
                    _over_5s = _elapsed_after_target > 5
                    if not _over_5s:
                        # 目标后5秒内：库存可能正在刷新，放慢间隔持续重试（不限时段）
                        current_interval = max(current_interval, 2.0)
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 库存已使用完（目标后{_elapsed_after_target:.1f}s<5s，持续重试）")
                    else:
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 库存已使用完（目标后{_elapsed_after_target:.1f}s），切下一个优先级")
                        break
                elif "202129" in msg or "奖励领取已结束" in msg:
                    self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 奖励领取已结束，切下一个优先级")
                    break
                elif "-705" in msg or "-509" in msg or "-702" in msg or "请求过于频繁" in msg or "请求频率过高" in msg:
                    # 风控，间隔保持基础间隔不变（靠±30ms波动）
                    self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 风控 {msg[:25]}，下次间隔 {current_interval*1000:.0f}ms")
                else:
                    # 无风控（未成功但也没被风控），恢复基础间隔
                    if current_interval != base_interval:
                        current_interval = base_interval
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: {msg[:40]}（风控已过，恢复基础间隔{base_interval*1000:.0f}ms）")
                    else:
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: {msg[:40]}")

            # 等待到下次尝试（从请求发出时间开始计算，叠加±30ms随机波动）
            fluctuation = random_fluctuations[min(attempt - 1, len(random_fluctuations) - 1)] / 1000.0
            next_time = stop_flag.get("last_request_time", time.time()) + current_interval + fluctuation
            while time.time() < next_time and time.time() < deadline and not stop_flag["stop"]:
                time.sleep(0.001)

        if not success and time.time() >= deadline:
            self.nm_log(f"  窗口期结束，共尝试{attempt}次")
        return success

    def on_version_change(self):
        """版本切换时更新期数下拉框选项"""
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
        """线程安全的日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        # 写入日志文件（线程安全）
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass
        # 通过主线程更新UI，避免Tkinter线程安全问题
        def _update():
            try:
                self.rush_log_text.config(state=tk.NORMAL)
                self.rush_log_text.insert(tk.END, line)
                self.rush_log_text.see(tk.END)
                self.rush_log_text.config(state=tk.DISABLED)
            except Exception:
                pass
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, _update)
            elif hasattr(self, 'app') and hasattr(self.app, 'root') and self.app.root:
                self.app.root.after(0, _update)
            else:
                _update()
        except Exception:
            _update()

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

                    if day_stock > 0 and total_stock > 0:
                        self.stock_label.config(text=f"库存：{stock_text_final} ✓ | 更新：{update_time}", fg=COLORS["success"])
                    else:
                        self.stock_label.config(text=f"库存：{stock_text_final} (今日已领完/总量不足) | 更新：{update_time}", fg=COLORS["warning"])

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
        status, result, data = receive_reward(task["task_id"], info, cookies, csrf)
        if status in ("success", "already"):
            return True, result, data
        return False, result, None

    def check_claimable_tasks(self):
        """查询所有活动中已完成但未领取的任务，输出到日志"""
        try:
            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户")
                return

            account = selected_accounts[0]
            cookies = {"SESSDATA": account.get("SESSDATA", ""), "bili_jct": account.get("bili_jct", "")}

            self.log(f"查询全部可领取任务（所有活动）")
            self.log(f"账户: {account['name']}")
            self.check_claimable_btn.config(state="disabled", text="查询中...")

            def check_thread():
                try:
                    # 查询所有任务，不筛选版本/期数/类型
                    all_details = []
                    cache_hit_count = 0
                    api_query_count = 0
                    # 获取所有唯一的(version, period, type)组合
                    combos = set()
                    for t in ALL_TASKS:
                        combos.add((t["version"], t["period"], t["type"]))
                    
                    self.after(0, lambda: self.log(f"共找到 {len(combos)} 个活动分类，开始查询..."))
                    
                    for idx, (version, period, task_type) in enumerate(combos):
                        if idx > 0:
                            time.sleep(1.0)  # 每个分类之间间隔1秒
                        self.after(0, lambda v=version, p=period, tt=task_type: self.log(f"  查询 [{v}][{p}][{tt}]..."))
                        all_finished, details = check_all_tasks_finished(version, period, task_type, cookies)
                        # 给每个任务添加分类信息
                        for d in details:
                            d["version"] = version
                            d["period"] = period
                            d["task_type"] = task_type
                        all_details.extend(details)
                    
                    # 统计缓存使用情况
                    cache_hit_count = sum(1 for d in all_details if d.get("from_cache", False))
                    api_query_count = len(all_details) - cache_hit_count
                    self.after(0, lambda: self.log(f"查询完成: 共{len(all_details)}个任务, 缓存命中{cache_hit_count}个, API查询{api_query_count}个"))
                    self.after(0, lambda: self._on_check_claimable_all(all_details))
                except Exception as e:
                    self.after(0, lambda: self._on_check_claimable_all([]))
                    self.log(f"查询异常: {str(e)}")

            threading.Thread(target=check_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("错误", f"查询失败: {str(e)}")
            self.check_claimable_btn.config(state="normal", text="📋 查询可领取")

    def _on_check_claimable_all(self, details):
        """查询全部可领取任务的回调（所有活动）"""
        self.check_claimable_btn.config(state="normal", text="📋 查询可领取")

        if not details:
            self.log("查询结果: 无匹配的任务")
            messagebox.showinfo("查询结果", "无匹配的任务")
            return

        # 筛选真正可领取的任务：已完成且 剩余总量 > 0 且 (status in [0,1] 或 status=2每日库存上限)
        # 注意：status=6（"查看奖励"）是已经领取过的，不算可领取！
        # status=2 有两种情况：已领取 或 每日库存已达上限（今日不能领但明天还能领）
        # 每日库存已达上限的判断：status==2 且 message包含"每日库存"或"上限" 且 total_stock > 0
        # 已完成但剩余总量为0（库存已领完）的也不纳入可领取统计
        def is_claimable(d):
            if d["finished"] is not True:
                return False
            if d.get("total_stock", 0) <= 0:
                return False
            if d["status"] in [0, 1]:
                return True
            if d["status"] == 2:
                msg = d.get("message", "")
                # 每日库存已达上限，今日不能领但明天还能领
                if "每日库存" in msg or "上限" in msg or "今日" in msg:
                    return True
            return False
        
        claimable_tasks = [d for d in details if is_claimable(d)]
        claimed_count = sum(1 for d in details if d["finished"] is True and d["status"] == 6)
        out_of_stock_count = sum(1 for d in details if d["finished"] is True and d.get("total_stock", 0) == 0)
        daily_limit_count = sum(1 for d in details if d["finished"] is True and d["status"] == 2 and d.get("total_stock", 0) > 0 and ("每日库存" in d.get("message", "") or "上限" in d.get("message", "") or "今日" in d.get("message", "")))
        unfinished_count = sum(1 for d in details if d["finished"] is False)
        total_count = len(details)

        self.log("=" * 50)
        self.log(f"可领取任务查询结果: 共{total_count}个任务, 可领取{len(claimable_tasks)}个, 已领取{claimed_count}个, 库存为0{out_of_stock_count}个, 每日上限{daily_limit_count}个, 未完成{unfinished_count}个")
        if out_of_stock_count > 0:
            self.log(f"  ⚠ 注意: 有{out_of_stock_count}个任务已完成，但剩余总量为0（库存已领完），不纳入可领取统计")
        if daily_limit_count > 0:
            self.log(f"  ℹ 提示: 有{daily_limit_count}个任务已完成，但今日库存已达上限（明日0点后可领），已纳入可领取统计")
        self.log("-" * 50)

        if claimable_tasks:
            self.log("以下任务可领取（已完成但未领取）:")
            # 按活动分类显示
            current_combo = None
            for d in claimable_tasks:
                version = d.get("version", "")
                period = d.get("period", "")
                task_type = d.get("task_type", "")
                combo = f"[{version}][{period}][{task_type}]"
                if combo != current_combo:
                    self.log(f"  --- {combo} ---")
                    current_combo = combo
                self.log(f"    🎁 {d['name']} => {d['award']}")
                if d["status"] == 2:
                    self.log(f"       状态: {d['message']} (status={d['status']}, 剩余总量={d.get('total_stock', 0)}%, 今日上限明日可领)")
                else:
                    self.log(f"       状态: {d['message']} (status={d['status']}, 剩余总量={d.get('total_stock', 0)}%)")
        else:
            self.log("没有可领取的任务")

        self.log("=" * 50)

        # 弹窗显示结果（只显示可领取的任务）
        if claimable_tasks:
            result_text = f"找到 {len(claimable_tasks)} 个可领取任务:\n\n"
            for d in claimable_tasks:
                version = d.get("version", "")
                period = d.get("period", "")
                result_text += f"🎁 [{version}][{period}] {d['name']} => {d['award']}\n"
            result_text += "\n详细信息请查看日志"
        else:
            result_text = "没有可领取的任务\n\n详细信息请查看日志"
        messagebox.showinfo("可领取任务查询结果", result_text)

    def check_all_finished(self):
        """查询当前选择类型的所有任务是否全部完成"""
        try:
            version = self.version_var.get()
            period = self.period_var.get()
            task_type = self.task_type_var.get()

            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户")
                return

            account = selected_accounts[0]
            cookies = {"SESSDATA": account.get("SESSDATA", ""), "bili_jct": account.get("bili_jct", "")}

            print(f"[DEBUG] check_all_finished called: version={version}, period={period}, type={task_type}")
            print(f"[DEBUG] account: {account.get('name', 'unknown')}")

            self.log(f"查询全部完成: [{version}][{period}][{task_type}]")
            self.log(f"账户: {account['name']}")
            self.check_all_finished_btn.config(state="disabled", text="查询中...")

            def check_thread():
                try:
                    print("[DEBUG] check_thread started")
                    all_finished, details = check_all_tasks_finished(version, period, task_type, cookies)
                    print(f"[DEBUG] check_thread finished: all_finished={all_finished}, details_count={len(details)}")
                    self.after(0, lambda: self._on_check_all_finished(all_finished, details))
                except Exception as e:
                    print(f"[DEBUG] check_thread exception: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self.after(0, lambda: self._on_check_all_finished(False, []))
                    self.log(f"查询异常: {str(e)}")

            threading.Thread(target=check_thread, daemon=True).start()
        except Exception as e:
            print(f"[DEBUG] check_all_finished exception: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"查询失败: {str(e)}")

    def _on_check_all_finished(self, all_finished, details):
        """查询全部完成的回调"""
        self.check_all_finished_btn.config(state="normal", text="✅ 查询全部完成")

        if not details:
            self.log("查询结果: 无匹配的任务")
            messagebox.showinfo("查询结果", "无匹配的任务")
            return

        # 统计
        finished_count = sum(1 for d in details if d["finished"] is True)
        unfinished_count = sum(1 for d in details if d["finished"] is False)
        unknown_count = sum(1 for d in details if d["finished"] is None)

        # 确定最终结果文本
        if all_finished is True:
            result_label = "全部已完成 ✓"
            result_value = "true"
        elif all_finished is False:
            result_label = "存在未完成任务 ✗"
            result_value = "false"
        else:
            result_label = "结果未知（有查询失败的任务）⚠"
            result_value = "unknown"

        # 输出每个任务的完成情况
        self.log("=" * 50)
        self.log(f"任务完成情况查询结果: {result_label}")
        self.log("-" * 50)
        for d in details:
            if d["finished"] is True:
                status_icon = "✓"
                status_text = "已完成"
            elif d["finished"] is False:
                status_icon = "✗"
                status_text = "未完成"
            else:
                status_icon = "?"
                status_text = "查询失败"
            self.log(f"  {status_icon} {d['name']} => {d['award']}")
            self.log(f"     状态: {d['message']} (status={d['status']}, {status_text})")
        self.log("-" * 50)
        self.log(f"统计: 已完成{finished_count}个, 未完成{unfinished_count}个, 查询失败{unknown_count}个")
        self.log(f"最终结果: {result_value}")
        self.log("=" * 50)

        # 弹窗显示结果
        result_text = f"全部完成: {result_value}\n\n"
        result_text += f"共 {len(details)} 个任务\n"
        result_text += f"已完成: {finished_count} 个\n"
        result_text += f"未完成: {unfinished_count} 个\n"
        if unknown_count > 0:
            result_text += f"查询失败: {unknown_count} 个（请稍后重试）\n"
        result_text += "\n"
        for d in details:
            if d["finished"] is True:
                status_icon = "✓"
            elif d["finished"] is False:
                status_icon = "✗"
            else:
                status_icon = "?"
            result_text += f"{status_icon} {d['name']}\n"
        messagebox.showinfo("任务完成情况", result_text)

    def claim_all_finished(self):
        """一键领取当前类型下所有已完成的任务"""
        try:
            version = self.version_var.get()
            period = self.period_var.get()
            task_type = self.task_type_var.get()

            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户")
                return

            account = selected_accounts[0]

            # 确认对话框
            confirm_msg = f"确定要一键领取 [{version}][{period}][{task_type}] 下所有已完成的任务吗？\n\n账户：{account['name']}"
            if not messagebox.askyesno("确认", confirm_msg):
                return

            self.log(f"一键全部领取: [{version}][{period}][{task_type}]")
            self.log(f"账户: {account['name']}")
            self.claim_all_btn.config(state="disabled", text="领取中...")

            def claim_thread():
                try:
                    # 筛选该类型下所有任务
                    tasks = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
                    if not tasks:
                        self.after(0, lambda: self._on_claim_all_finished([], 0, 0, "无匹配的任务"))
                        return

                    cookies = {"SESSDATA": account.get("SESSDATA", ""), "bili_jct": account.get("bili_jct", "")}
                    success_count = 0
                    fail_count = 0
                    skip_count = 0
                    results = []

                    self.after(0, lambda: self.log(f"共找到 {len(tasks)} 个任务，开始查询并领取..."))

                    for idx, task in enumerate(tasks):
                        # 请求间隔1秒
                        if idx > 0:
                            time.sleep(1.0)

                        task_name = task.get("name", "未知")
                        award = task.get("award", "")

                        # 查询任务完成状态
                        try:
                            info, msg = get_mission_info(task["task_id"], cookies)
                            if not info:
                                self.after(0, lambda tn=task_name, m=msg: self.log(f"  ⚠ {tn}: 查询失败 - {m}，跳过"))
                                fail_count += 1
                                results.append({"name": task_name, "award": award, "status": "查询失败", "success": False})
                                continue

                            task_finished = info.get("task_finished", False)
                            status = info.get("status", 0)

                            if not task_finished:
                                self.after(0, lambda tn=task_name: self.log(f"  ○ {tn}: 未完成，跳过"))
                                skip_count += 1
                                results.append({"name": task_name, "award": award, "status": "未完成", "success": False})
                                continue

                            # 已完成，尝试领取
                            self.after(0, lambda tn=task_name: self.log(f"  → {tn}: 已完成，正在领取..."))
                            time.sleep(1.0)  # 领取前间隔1秒

                            ok, result_msg, data = self.do_receive_once(task, account)
                            if ok:
                                self.after(0, lambda tn=task_name: self.log(f"  ✓ {tn}: 领取成功！"))
                                success_count += 1
                                results.append({"name": task_name, "award": award, "status": "领取成功", "success": True})
                            else:
                                self.after(0, lambda tn=task_name, rm=result_msg: self.log(f"  ✗ {tn}: 领取失败 - {rm}"))
                                fail_count += 1
                                results.append({"name": task_name, "award": award, "status": f"领取失败: {result_msg}", "success": False})

                        except Exception as e:
                            self.after(0, lambda tn=task_name, ex=str(e): self.log(f"  ✗ {tn}: 异常 - {ex}"))
                            fail_count += 1
                            results.append({"name": task_name, "award": award, "status": f"异常: {str(e)}", "success": False})

                    self.after(0, lambda: self._on_claim_all_finished(results, success_count, fail_count, skip_count, None))

                except Exception as e:
                    self.after(0, lambda: self._on_claim_all_finished([], 0, 0, 0, f"执行异常: {str(e)}"))

            threading.Thread(target=claim_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("错误", f"一键领取失败: {str(e)}")
            self.claim_all_btn.config(state="normal", text="🎁 一键全部领取")

    def _on_claim_all_finished(self, results, success_count, fail_count, skip_count, error):
        """一键全部领取的回调"""
        self.claim_all_btn.config(state="normal", text="🎁 一键全部领取")

        if error:
            self.log(f"一键全部领取失败: {error}")
            messagebox.showerror("错误", error)
            return

        self.log("=" * 50)
        self.log(f"一键全部领取完成: 成功 {success_count} 个, 失败 {fail_count} 个, 跳过 {skip_count} 个")
        self.log("-" * 50)
        for r in results:
            icon = "✓" if r["success"] else ("○" if "未完成" in r["status"] else "✗")
            self.log(f"  {icon} {r['name']} => {r['award']}")
            self.log(f"     {r['status']}")
        self.log("=" * 50)

        # 弹窗显示结果
        result_text = "一键全部领取完成\n\n"
        result_text += f"成功: {success_count} 个\n"
        result_text += f"失败: {fail_count} 个\n"
        result_text += f"跳过(未完成): {skip_count} 个\n\n"
        for r in results:
            icon = "✓" if r["success"] else ("○" if "未完成" in r["status"] else "✗")
            result_text += f"{icon} {r['name']}\n"
        messagebox.showinfo("一键全部领取结果", result_text)

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
        ok, msg, receive_data = self.do_receive_once(task, acc)
        if ok:
            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
            self.log(f"  账户：{acc['name']}")
            self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
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
                initial_stock = day_s
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
                        current_stock = day_s
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account, None)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测奖励是否已结束（202129），直接停止
            if "202129" in msg or "奖励领取已结束" in msg:
                self.log(f"  ⚠ 奖励领取已结束，自动停止领取")
                break

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
        if version == "原神7.1":
            act_name = "原神7.1版本UP主激励计划"
        elif "原神" in version:
            act_name = "原神7.0版本创作激励计划"
        elif "崩坏" in version or "星穹" in version:
            act_name = "崩坏星穹铁道4.5版本创作激励计划"
        else:
            act_name = "鸣潮3.7版本创作激励计划"
        # 直接根据版本获取act_id（同一版本所有任务共享同一个act_id）
        act_id = VERSION_DEFAULT_ACT_ID.get(version, task.get("act_id", ""))
        return {
            "act_id": act_id,
            "act_name": act_name,
            "task_name": task["name"],
            "reward_info": {"award_name": task["award"]},
        }

    def do_receive_fast(self, task, task_info, account, session=None):
        """快速领取：直接尝试领取（session可选，复用预热连接）"""
        cookies = cookies_from_account(account)
        csrf = account["bili_jct"]
        status, result, data = receive_reward(task["task_id"], task_info, cookies, csrf, session)
        if status in ("success", "already"):
            return True, result
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
                initial_stock = day_s
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
                        current_stock = day_s
                        if current_stock > max_stock_seen:
                            max_stock_seen = current_stock
                except Exception:
                    pass

            try:
                ok, msg = self.do_receive_fast(task, task_info, account, None)
            except Exception as e:
                ok, msg = False, f"异常: {e}"

            if ok:
                success = True
                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                self.log(f"  账户：{account['name']} | 第{attempt}次尝试")
                break
            else:
                self.log(f"  第{attempt}次: {msg} ({account['name']})")

            # 检测奖励是否已结束（202129），直接停止
            if "202129" in msg or "奖励领取已结束" in msg:
                self.log(f"  ⚠ 奖励领取已结束，自动停止领取")
                break

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
        # P1-6: 新旧抢码互斥闸门
        nm_running = any(t.is_alive() for t in self.nm_group_threads.values()) if hasattr(self, 'nm_group_threads') else False
        if nm_running:
            messagebox.showwarning("提示", "精准抢码正在运行中，请先停止后再启动监控抢码")
            return
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

                # 安全更新UI（用默认参数捕获变量当前值，避免闭包延迟绑定问题）
                def _update_ui(st=stock_text, ut=update_time, ds=day_stock, ts=total_stock, tf=task_finished, st_code=status, msg=info.get("message", "")):
                    try:
                        self.stock_label.config(
                            text=f"库存：{st} | 更新：{ut}",
                            fg=COLORS["success"] if (ds > 0 and ts > 0) else COLORS["warning"]
                        )
                        if tf:
                            self.task_finish_label.config(text="任务完成：已完成 ✓", fg=COLORS["success"])
                        else:
                            self.task_finish_label.config(text="任务完成：未完成", fg=COLORS["warning"])
                        # 更新领取资格
                        if tf and st_code in [0, 1]:
                            self.qualify_label.config(text="领取资格：已完成任务，可以领取", fg=COLORS["success"])
                        else:
                            self.qualify_label.config(text=f"领取资格：{msg} (状态:{st_code})", fg=COLORS["warning"])
                    except Exception:
                        pass
                self.after(0, _update_ui)

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
                    status, result, data = receive_reward(task["task_id"], info, cookies, csrf)
                    if status in ("success", "already"):
                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                        self.log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
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

# ========== 兑换码导出模块 ==========
class CodeExportFrame(tk.Frame):
    """兑换码导出页面"""
    def __init__(self, parent, account_mgr=None, room_mgr=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.selected_ids = set()
        self.current_activity_filter = "全部活动"
        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self, bg=COLORS["bg_card"], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🎁 兑换码导出", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(header, text="从领取记录导入兑换码，支持复制和导出",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 20))

        # 操作按钮栏
        btn_bar = tk.Frame(self, bg=COLORS["bg_card"], height=56)
        btn_bar.pack(fill=tk.X, pady=(0, 2))
        btn_bar.pack_propagate(False)

        btn_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        btn_frame.pack(side=tk.LEFT, padx=15, pady=8)

        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新列表", bg=COLORS["bg_input"],
                                      fg=COLORS["text_secondary"], font=("微软雅黑", 10),
                                      bd=0, padx=16, pady=6, cursor="hand2", command=self.refresh_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.import_btn = tk.Button(btn_frame, text="📥 从领取记录导入", bg="#FF8F00",
                                     fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                     bd=0, padx=16, pady=6, cursor="hand2", command=self.import_from_records)
        self.import_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_selected_btn = tk.Button(btn_frame, text="📋 复制选中", bg=COLORS["accent"],
                                            fg="#000000", font=("微软雅黑", 10, "bold"),
                                            bd=0, padx=16, pady=6, cursor="hand2", command=self.copy_selected)
        self.copy_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_all_btn = tk.Button(btn_frame, text="📋 复制全部", bg=COLORS["accent"],
                                       fg="#000000", font=("微软雅黑", 10, "bold"),
                                       bd=0, padx=16, pady=6, cursor="hand2", command=self.copy_all)
        self.copy_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_btn = tk.Button(btn_frame, text="💾 导出TXT", bg="#2E7D32",
                                     fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                     bd=0, padx=16, pady=6, cursor="hand2", command=self.export_txt)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_csv_btn = tk.Button(btn_frame, text="📊 导出CSV", bg="#1565C0",
                                          fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                          bd=0, padx=16, pady=6, cursor="hand2", command=self.export_csv)
        self.export_csv_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.delete_selected_btn = tk.Button(btn_frame, text="🗑 删除选中", bg="#C62828",
                                               fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                               bd=0, padx=16, pady=6, cursor="hand2", command=self.delete_selected)
        self.delete_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = tk.Button(btn_frame, text="🧹 清空全部", bg="#616161",
                                    fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                    bd=0, padx=16, pady=6, cursor="hand2", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT)

        # 活动筛选下拉框
        filter_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=(0, 15))
        
        tk.Label(filter_frame, text="活动筛选:", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        from tkinter import ttk
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        self.activity_filter_var = tk.StringVar(value="全部活动")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Filter.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        self.activity_filter_combo = ttk.Combobox(filter_frame, textvariable=self.activity_filter_var,
                                                    values=activity_list, state="readonly",
                                                    font=("微软雅黑", 10), width=18,
                                                    style='Filter.TCombobox')
        self.activity_filter_combo.pack(side=tk.LEFT)
        self.activity_filter_combo.bind("<<ComboboxSelected>>", self._on_activity_filter_change)

        # 统计信息
        self.stats_label = tk.Label(btn_bar, text="", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 10))
        self.stats_label.pack(side=tk.RIGHT, padx=20)

        # 列表区域
        list_container = tk.Frame(self, bg=COLORS["bg_card"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # 表头
        header_frame = tk.Frame(list_container, bg=COLORS["bg_input"], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        cols = [
            ("选择", 50),
            ("ID", 50),
            ("领取时间", 160),
            ("任务名称", 250),
            ("账户", 120),
            ("兑换码", 300),
            ("字段", 100),
            ("状态", 80),
            ("操作", 150),
        ]
        self.col_widths = [w for _, w in cols]
        for text, width in cols:
            tk.Label(header_frame, text=text, bg=COLORS["bg_input"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"),
                     width=width // 8, anchor="w").pack(side=tk.LEFT, padx=4, pady=8)

        # 可滚动列表
        self.canvas = tk.Canvas(list_container, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLORS["bg_dark"])

        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", 
                                  tags="scroll_frame")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("scroll_frame", width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_activity_filter_change(self, event=None):
        """活动筛选变更"""
        self.current_activity_filter = self.activity_filter_var.get()
        self.refresh_list()
    
    def _get_filtered_records(self, records=None):
        """获取筛选后的记录"""
        if records is None:
            records = self.records
        if self.current_activity_filter == "全部活动":
            return records
        # 根据task_name前缀筛选（task_name格式为"活动名称 奖励名称"）
        filtered = []
        for r in records:
            task_name = r.get("task_name", "")
            if task_name.startswith(self.current_activity_filter):
                filtered.append(r)
        return filtered

    def import_from_records(self):
        """从领取记录导入所有兑换码（选择活动或全部导入）"""
        # 创建活动选择对话框
        dialog = tk.Toplevel(self)
        dialog.title("选择活动")
        dialog.geometry("360x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 360) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="请选择要导入兑换码的活动：", 
                 font=("微软雅黑", 11), bg=COLORS["bg_dark"], fg=COLORS["text_primary"]).pack(pady=(20, 10))
        
        # 活动列表（从VERSION_DEFAULT_ACT_ID获取）
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        activity_var = tk.StringVar(value=activity_list[0])
        
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Activity.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        activity_combo = ttk.Combobox(dialog, textvariable=activity_var, 
                                        values=activity_list, state="readonly",
                                        font=("微软雅黑", 11), width=25,
                                        style='Activity.TCombobox')
        activity_combo.pack(pady=10)
        
        result = {"selected": None}
        
        def on_confirm():
            result["selected"] = activity_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="确定", bg=COLORS["accent"], fg="#000000",
                  font=("微软雅黑", 10, "bold"), bd=0, padx=25, pady=6, cursor="hand2",
                  command=on_confirm).pack(side=tk.LEFT, padx=10)
        
        tk.Button(btn_frame, text="取消", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                  font=("微软雅黑", 10), bd=0, padx=25, pady=6, cursor="hand2",
                  command=on_cancel).pack(side=tk.LEFT, padx=10)
        
        dialog.configure(bg=COLORS["bg_dark"])
        self.wait_window(dialog)
        
        selected_activity = result["selected"]
        if not selected_activity:
            return
        
        # 根据选择获取act_id列表
        if selected_activity == "全部活动":
            act_id_list = list(VERSION_DEFAULT_ACT_ID.values())
            activity_names = list(VERSION_DEFAULT_ACT_ID.keys())
        else:
            act_id_list = [VERSION_DEFAULT_ACT_ID.get(selected_activity, "")]
            activity_names = [selected_activity]
        
        # 过滤掉空的act_id
        valid_pairs = [(name, aid) for name, aid in zip(activity_names, act_id_list) if aid]
        if not valid_pairs:
            messagebox.showwarning("提示", "未找到有效的活动ID")
            return

        # 获取所有账户
        accounts = []
        try:
            if self.account_mgr and hasattr(self.account_mgr, 'accounts'):
                accounts = self.account_mgr.accounts
            else:
                # 从文件读取（使用统一的ACCOUNTS_FILE路径）
                if os.path.exists(str(ACCOUNTS_FILE)):
                    with open(str(ACCOUNTS_FILE), "r", encoding="utf-8") as f:
                        accounts = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"读取账户失败: {e}")
            return

        if not accounts:
            messagebox.showwarning("提示", "没有可用的账户，请先导入账户")
            return

        # 遍历所有活动和账户，调用领取记录API（后台线程执行，避免卡住UI）
        self._import_running = True
        if hasattr(self, 'import_btn'):
            self.import_btn.config(state=tk.DISABLED, text="导入中...")
        
        def _do_import():
            total_imported = 0
            total_skipped = 0
            account_results = []
            try:
                for activity_name, act_id in valid_pairs:
                    for acc in accounts:
                        try:
                            cookies = cookies_from_account(acc)
                            record_data, record_msg = get_award_record(act_id, cookies)
                            
                            if record_data and record_data.get("list"):
                                record_list = record_data["list"]
                                account_codes = 0
                                
                                for record in record_list:
                                    codes = extract_redeem_codes(record)
                                    for code_info in codes:
                                        record_activity_name = record.get("activity_name", "")
                                        award_name = record.get("award_name", "未知奖励")
                                        if record_activity_name:
                                            record_activity_name = re.sub(r'版本激励计划.*$', '', record_activity_name)
                                            record_activity_name = re.sub(r'激励计划.*$', '', record_activity_name)
                                            record_activity_name = record_activity_name.strip()
                                        task_name = f"{record_activity_name} {award_name}" if record_activity_name else award_name
                                        ok_save, save_msg = save_redeem_code(
                                            task_name, acc.get("name", "未知"), record,
                                            task_period="", task_type=record.get("type", "")
                                        )
                                        if ok_save:
                                            total_imported += 1
                                            account_codes += 1
                                        else:
                                            total_skipped += 1
                                account_results.append(f"  [{activity_name}] {acc['name']}: 导入 {account_codes} 个，共 {len(record_list)} 条记录")
                            else:
                                account_results.append(f"  [{activity_name}] {acc['name']}: 无领取记录 ({record_msg})")
                        except Exception as e:
                            account_results.append(f"  [{activity_name}] {acc['name']}: 异常 - {e}")
            finally:
                self._import_running = False
            self.after(0, lambda: self._on_import_finished(total_imported, total_skipped, account_results))
        
        threading.Thread(target=_do_import, daemon=True).start()
    
    def _on_import_finished(self, total_imported, total_skipped, account_results):
        """导入完成回调（主线程执行）"""
        self.refresh_list()
        if hasattr(self, 'import_btn'):
            self.import_btn.config(state=tk.NORMAL, text="从领取记录导入")
        result_msg = f"导入完成！\n\n共导入 {total_imported} 个兑换码\n跳过 {total_skipped} 个（重复）\n\n详情：\n" + "\n".join(account_results)
        messagebox.showinfo("导入结果", result_msg)
    def refresh_list(self):
        """刷新兑换码列表"""
        # 清空现有内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.selected_ids.clear()

        all_records = load_redeem_codes()
        self.records = all_records
        records = self._get_filtered_records(all_records)

        # 更新统计（显示筛选后的数量和总数）
        total = len(records)
        total_all = len(all_records)
        unused = sum(1 for r in records if r.get("status") == "未使用")
        used = sum(1 for r in records if r.get("status") == "已使用")
        if self.current_activity_filter == "全部活动":
            self.stats_label.config(text=f"共 {total} 条 | 未使用 {unused} | 已使用 {used}")
        else:
            self.stats_label.config(text=f"筛选 {total}/{total_all} 条 | 未使用 {unused} | 已使用 {used}")

        if not records:
            empty_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_dark"])
            empty_frame.pack(fill=tk.X, pady=40)
            tk.Label(empty_frame, text="📭 暂无兑换码记录", bg=COLORS["bg_dark"],
                     fg=COLORS["text_muted"], font=("微软雅黑", 14)).pack()
            tk.Label(empty_frame, text="点击「从领取记录导入」获取兑换码",
                     bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 10)).pack(pady=(8, 0))
            return

        for i, record in enumerate(records):
            try:
                row_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"])
                row_frame.pack(fill=tk.X, pady=1)

                # 确保record是字典
                if not isinstance(record, dict):
                    tk.Label(row_frame, text=f"记录格式错误: {str(record)[:50]}", bg=row_frame["bg"],
                             fg="#FF5252", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10, pady=6)
                    continue

                rec_id = record.get("id", i + 1)
                rec_time = record.get("time", "")
                rec_task = record.get("task_name", "")
                if record.get("task_period"):
                    rec_task = f"[{record['task_period']}] {rec_task}"
                rec_account = record.get("account", "")
                rec_code = record.get("redeem_code", "")
                rec_field = record.get("code_field", "")
                rec_status = record.get("status", "未使用")

                # 选择框
                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(row_frame, variable=var, bg=row_frame["bg"],
                                     activebackground=row_frame["bg"], command=lambda rid=rec_id, v=var: self._toggle_select(rid, v))
                cb.pack(side=tk.LEFT, padx=(10, 5), pady=6)

                # ID
                tk.Label(row_frame, text=str(rec_id), bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=4, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 时间
                tk.Label(row_frame, text=rec_time, bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=18, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 任务名称
                tk.Label(row_frame, text=rec_task, bg=row_frame["bg"],
                         fg=COLORS["text_primary"], font=("微软雅黑", 9),
                         width=28, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 账户
                tk.Label(row_frame, text=rec_account, bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=12, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 兑换码（可点击复制）
                code_label = tk.Label(row_frame, text=rec_code, bg=row_frame["bg"],
                                       fg="#4FC3F7", font=("Consolas", 10, "bold"),
                                       cursor="hand2", anchor="w")
                code_label.pack(side=tk.LEFT, padx=2, pady=6)
                code_label.bind("<Button-1>", lambda e, c=rec_code: self._copy_to_clipboard(c))

                # 字段
                tk.Label(row_frame, text=rec_field, bg=row_frame["bg"],
                         fg=COLORS["text_muted"], font=("微软雅黑", 8),
                         width=10, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 状态
                status_color = "#4CAF50" if rec_status == "未使用" else "#9E9E9E"
                tk.Label(row_frame, text=rec_status, bg=row_frame["bg"],
                         fg=status_color, font=("微软雅黑", 9, "bold"),
                         width=6, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 操作按钮
                op_frame = tk.Frame(row_frame, bg=row_frame["bg"])
                op_frame.pack(side=tk.LEFT, padx=(10, 5), pady=4)

                tk.Button(op_frame, text="复制", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                          font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                          command=lambda c=rec_code: self._copy_to_clipboard(c)).pack(side=tk.LEFT, padx=(0, 4))

                if rec_status == "未使用":
                    tk.Button(op_frame, text="标记已用", bg="#FF8F00", fg="#FFFFFF",
                              font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                              command=lambda rid=rec_id: self._mark_used(rid)).pack(side=tk.LEFT, padx=(0, 4))
                else:
                    tk.Button(op_frame, text="标记未用", bg="#1565C0", fg="#FFFFFF",
                              font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                              command=lambda rid=rec_id: self._mark_unused(rid)).pack(side=tk.LEFT, padx=(0, 4))

                tk.Button(op_frame, text="删除", bg="#C62828", fg="#FFFFFF",
                          font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                          command=lambda rid=rec_id: self._delete_one(rid)).pack(side=tk.LEFT)
            except Exception as e:
                # 渲染失败时显示错误信息，不中断整个列表
                err_frame = tk.Frame(self.scroll_frame, bg="#FFEBEE")
                err_frame.pack(fill=tk.X, pady=1)
                tk.Label(err_frame, text=f"记录 {i+1} 渲染失败: {str(e)}", bg="#FFEBEE",
                         fg="#C62828", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10, pady=6)

    def _toggle_select(self, record_id, var):
        if var.get():
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def _copy_to_clipboard(self, text):
        """复制到剪贴板"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except:
            pass

    def _mark_used(self, record_id):
        update_redeem_code_status(record_id, "已使用")
        self.refresh_list()

    def _mark_unused(self, record_id):
        update_redeem_code_status(record_id, "未使用")
        self.refresh_list()

    def _delete_one(self, record_id):
        delete_redeem_code(record_id)
        self.refresh_list()

    def copy_selected(self):
        """复制选中的兑换码（仅筛选后的记录）"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        codes = [r["redeem_code"] for r in filtered if r["id"] in self.selected_ids]
        if codes:
            self._copy_to_clipboard("\n".join(codes))

    def copy_all(self):
        """复制全部兑换码（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        codes = [r["redeem_code"] for r in filtered]
        self._copy_to_clipboard("\n".join(codes))

    def export_txt(self):
        """导出为TXT文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("===== B站工具箱 兑换码导出 =====\n")
                f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"活动筛选: {self.current_activity_filter}\n")
                f.write(f"共 {len(filtered)} 条\n")
                f.write("=" * 50 + "\n\n")
                for r in filtered:
                    f.write(f"ID: {r['id']}\n")
                    f.write(f"时间: {r.get('time', '')}\n")
                    f.write(f"任务: {r.get('task_name', '')}\n")
                    f.write(f"账户: {r.get('account', '')}\n")
                    f.write(f"兑换码: {r.get('redeem_code', '')}\n")
                    f.write(f"状态: {r.get('status', '')}\n")
                    f.write("-" * 40 + "\n")
            self._copy_to_clipboard(filepath)
        except Exception as e:
            pass

    def export_csv(self):
        """导出为CSV文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.csv")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("ID,领取时间,任务名称,账户,兑换码,字段,状态\n")
                for r in filtered:
                    f.write(f"{r['id']},{r.get('time','')},{r.get('task_name','')},{r.get('account','')},{r.get('redeem_code','')},{r.get('code_field','')},{r.get('status','')}\n")
        except Exception as e:
            pass

    def delete_selected(self):
        """删除选中的记录（仅筛选后的记录中选中的）—— 一次性过滤，避免循环删除时id错位"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        filtered_ids = set(r["id"] for r in filtered)
        to_delete = set(rid for rid in self.selected_ids if rid in filtered_ids)
        if not to_delete:
            return
        try:
            records = load_redeem_codes()
            records = [r for r in records if r["id"] not in to_delete]
            # 统一重新编号
            for i, r in enumerate(records):
                r["id"] = i + 1
            _ensure_code_dir()
            atomic_write_json(CODE_EXPORT_FILE, records)
        except Exception as e:
            print(f"批量删除失败: {e}")
        self.refresh_list()

    def clear_all(self):
        """清空全部记录"""
        clear_redeem_codes()
        self.refresh_list()



class WatchLiveFrame(tk.Frame):
    """看播任务工具：模拟观看B站直播间，完成看播里程碑任务"""

    ROOM_ENTRY_API = "https://api.live.bilibili.com/room/v1/Room/room_entry_action"
    HEARTBEAT_API = "https://api.live.bilibili.com/User/userOnlineHeart"

    def __init__(self, parent, account_mgr, room_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.root = parent.winfo_toplevel()  # P0-D: worker线程通过root.after回主线程
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
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
        # 送礼功能变量
        self.gift_running = False
        self.gift_threads = {}
        self.gift_stop = {}
        self.gift_config = self.load_gift_config()
        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.gift_account_var = tk.StringVar(value="")  # 送礼账户下拉选择
        self.gift_account_battery = {}  # 送礼账户电池余额缓存
        # 看播历史记录
        self.watch_history = self.load_watch_history()
        self.current_watch_record = None  # 当前进行中的看播记录
        self.watch_snapshot_timer = None  # 快照定时器
        self.build_ui()
        # 启动时检查是否有异常中断的快照
        self.after(500, self.check_watch_snapshot)
        self.refresh_account_list()
        self.apply_watch_config()
        self.apply_gift_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，勾选账户和直播间后点击「开始看播」")


    # ========== 看播历史记录功能 ==========
    def load_watch_history(self):
        """加载看播历史记录"""
        history_file = BASE_DIR / "watch_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_watch_history(self):
        """保存看播历史记录"""
        try:
            history_file = BASE_DIR / "watch_history.json"
            atomic_write_json(history_file, self.watch_history)
        except Exception as e:
            self.log(f"⚠ 保存看播历史失败: {e}")

    def start_watch_record(self, room_ids, selected_accounts):
        """开始一条新的看播记录"""
        import uuid
        self.current_watch_record = {
            "id": str(uuid.uuid4())[:8],
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start_timestamp": time.time(),
            "end_time": None,
            "duration_seconds": 0,
            "target_minutes": self.duration_var.get(),
            "room_ids": room_ids,
            "accounts": [],
            "status": "进行中",
            "anomalies": [],
            "heartbeat_interval": self.interval_var.get()
        }
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.current_watch_record["accounts"].append({
                "account_name": name,
                "watch_seconds": 0,
                "heartbeat_count": 0,
                "status": "进入中",
                "anomalies": []
            })
        self.log(f"[历史记录] 开始记录: {len(room_ids)}个直播间, {len(selected_accounts)}个账户")

    def update_watch_record_stats(self):
        """更新当前看播记录的统计数据"""
        if not self.current_watch_record:
            return
        total_seconds = 0
        for acc_rec in self.current_watch_record["accounts"]:
            name = acc_rec["account_name"]
            if name in self.account_stats:
                stats = self.account_stats[name]
                acc_rec["watch_seconds"] = stats.get("watch_seconds", 0)
                acc_rec["heartbeat_count"] = stats.get("heartbeat_count", 0)
                acc_rec["status"] = stats.get("status", "未知")
                total_seconds = max(total_seconds, acc_rec["watch_seconds"])
        self.current_watch_record["duration_seconds"] = total_seconds

    def add_watch_anomaly(self, anomaly_type, message, account_name=None, room_id=None):
        """添加异常事件到当前看播记录"""
        if not self.current_watch_record:
            return
        anomaly = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": anomaly_type,
            "message": message,
            "account": account_name,
            "room": room_id
        }
        self.current_watch_record["anomalies"].append(anomaly)
        # 如果指定了账户，也添加到账户的异常列表
        if account_name:
            for acc_rec in self.current_watch_record["accounts"]:
                if acc_rec["account_name"] == account_name:
                    acc_rec["anomalies"].append(anomaly)
                    break
        self.log(f"[异常] {anomaly_type}: {message}")

    def finish_watch_record(self, status="已完成"):
        """结束当前看播记录并保存到历史"""
        if not self.current_watch_record:
            return
        self.update_watch_record_stats()
        self.current_watch_record["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_watch_record["status"] = status
        # 插入到历史记录最前面
        self.watch_history.insert(0, self.current_watch_record)
        self.save_watch_history()
        self.log(f"[历史记录] 已保存: {status}, 时长{self.current_watch_record['duration_seconds']}秒, 异常{len(self.current_watch_record['anomalies'])}次")
        self.current_watch_record = None
        # 停止快照定时器
        if self.watch_snapshot_timer:
            try:
                self.after_cancel(self.watch_snapshot_timer)
            except Exception:
                pass
            self.watch_snapshot_timer = None
        # 删除快照文件
        try:
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            if snapshot_file.exists():
                snapshot_file.unlink()
        except Exception:
            pass

    def save_watch_snapshot(self):
        """保存看播快照（每5分钟一次，用于异常中断恢复）"""
        if not self.current_watch_record:
            return
        try:
            self.update_watch_record_stats()
            snapshot = {
                "record": self.current_watch_record,
                "snapshot_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "account_stats": {}
            }
            for name, stats in self.account_stats.items():
                snapshot["account_stats"][name] = {
                    "watch_seconds": stats.get("watch_seconds", 0),
                    "heartbeat_count": stats.get("heartbeat_count", 0),
                    "status": stats.get("status", "未知")
                }
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            atomic_write_json(snapshot_file, snapshot)
        except Exception as e:
            self.log(f"⚠ 保存看播快照失败: {e}")
        # 安排下一次快照（5分钟后）
        if self.running and self.current_watch_record:
            self.watch_snapshot_timer = self.after(300000, self.save_watch_snapshot)

    def check_watch_snapshot(self):
        """启动时检查是否有异常中断的快照"""
        try:
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            if not snapshot_file.exists():
                return
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            record = snapshot.get("record") or {}
            snapshot_time = snapshot.get("snapshot_time", "未知")
            # 将快照作为异常中断记录保存到历史
            record["end_time"] = snapshot_time
            record["status"] = "异常中断"
            record["anomalies"] = list(record.get("anomalies") or [])
            record["anomalies"].append({
                "time": snapshot_time,
                "type": "程序异常中断",
                "message": f"程序在{snapshot_time}异常退出，看播未正常结束",
                "account": None,
                "room": None
            })
            self.watch_history.insert(0, record)
            self.save_watch_history()
            # 弹窗警告
            from tkinter import messagebox
            self.after(100, lambda: messagebox.showwarning(
                "看播异常中断",
                f"检测到上次看播在 {snapshot_time} 异常中断！\n\n"
                f"直播间: {', '.join(record.get('room_ids', []))}\n"
                f"账户数: {len(record.get('accounts', []))}\n"
                f"已观看: {record.get('duration_seconds', 0)}秒\n\n"
                f"该记录已保存到历史记录中（标记为异常中断）。"
            ))
        except Exception as e:
            self.log(f"⚠ 检查看播快照失败: {e}")
        finally:
            # 删除快照文件（无论成功失败）
            try:
                if snapshot_file.exists():
                    snapshot_file.unlink()
            except Exception:
                pass


    def show_watch_history(self):
        """显示看播历史记录弹窗"""
        if not hasattr(self, 'history_window') or not self.history_window.winfo_exists():
            self.history_window = tk.Toplevel(self)
            self.history_window.title("看播历史记录")
            self.history_window.geometry("1300x750")
            self.history_window.configure(bg=COLORS["bg_dark"])
            self.history_window.transient(self.winfo_toplevel())
            self._build_history_ui()
        else:
            self.history_window.lift()
            self.history_window.focus_force()

    def _build_history_ui(self):
        """构建历史记录UI"""
        win = self.history_window
        # 顶部统计栏
        stats_frame = tk.Frame(win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        stats_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        self._update_history_stats(stats_frame)

        # 工具栏
        toolbar = tk.Frame(win, bg=COLORS["bg_dark"])
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(toolbar, text=f"共 {len(self.watch_history)} 条记录", bg=COLORS["bg_dark"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        DarkButton(toolbar, "导出Excel", command=self.export_watch_history_excel, width=100, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(toolbar, "刷新", command=self._refresh_history_view, width=80, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT)

        # 表格区域
        table_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 表头
        columns = ("开始时间", "结束时间", "时长", "直播间", "账户", "状态", "异常")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        col_widths = [160, 160, 90, 260, 300, 90, 100]
        for col, width in zip(columns, col_widths):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=width, anchor=tk.CENTER)
        # 样式
        style = ttk.Style()
        style.configure("History.Treeview", background=COLORS["bg_card"], fieldbackground=COLORS["bg_card"], foreground=COLORS["text_primary"], rowheight=28, font=("微软雅黑", 9))
        style.configure("History.Treeview.Heading", background=COLORS["bg_input"], foreground=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.history_tree.configure(style="History.Treeview")
        # 标签（标红）
        self.history_tree.tag_configure("anomaly", foreground=COLORS["danger"])
        self.history_tree.tag_configure("warning", foreground=COLORS["warning"])
        self.history_tree.tag_configure("success", foreground=COLORS["success"])

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击查看详情
        self.history_tree.bind("<Double-1>", self._show_history_detail)

        # 分页
        self.history_page = 0
        self.history_page_size = 20
        page_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        page_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.history_page_label = tk.Label(page_frame, text="", bg=COLORS["bg_dark"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.history_page_label.pack(side=tk.LEFT)
        DarkButton(page_frame, "上一页", command=lambda: self._history_prev_page(), width=80, height=30, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]).pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(page_frame, "下一页", command=lambda: self._history_next_page(), width=80, height=30, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]).pack(side=tk.RIGHT)

        self._refresh_history_view()

    def _update_history_stats(self, parent):
        """更新统计信息"""
        for widget in parent.winfo_children():
            widget.destroy()
        total = len(self.watch_history)
        total_seconds = sum(r.get("duration_seconds", 0) for r in self.watch_history)
        total_hours = total_seconds / 3600
        anomaly_count = sum(len(r.get("anomalies", [])) for r in self.watch_history)
        completed = sum(1 for r in self.watch_history if r.get("status") == "已完成")
        interrupted = sum(1 for r in self.watch_history if r.get("status") == "异常中断")

        stats = [
            ("总记录数", f"{total} 次"),
            ("总观看时长", f"{total_hours:.1f} 小时"),
            ("已完成", f"{completed} 次"),
            ("异常中断", f"{interrupted} 次"),
            ("异常事件", f"{anomaly_count} 次"),
        ]
        for i, (label, value) in enumerate(stats):
            frame = tk.Frame(parent, bg=COLORS["bg_card"])
            frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10, pady=8)
            tk.Label(frame, text=label, bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack()
            color = COLORS["danger"] if "异常" in label else COLORS["accent"]
            tk.Label(frame, text=value, bg=COLORS["bg_card"], fg=color, font=("微软雅黑", 13, "bold")).pack()

    def _refresh_history_view(self):
        """刷新历史记录表格"""
        # 重新加载
        self.watch_history = self.load_watch_history()
        # 更新统计
        stats_parent = self.history_window.winfo_children()[0]
        self._update_history_stats(stats_parent)
        # 清空表格
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        # 计算分页
        total_pages = max(1, (len(self.watch_history) + self.history_page_size - 1) // self.history_page_size)
        if self.history_page >= total_pages:
            self.history_page = total_pages - 1
        start = self.history_page * self.history_page_size
        end = start + self.history_page_size
        page_records = self.watch_history[start:end]

        for record in page_records:
            start_time = record.get("start_time", "-")
            end_time = record.get("end_time", "-")
            duration = f"{record.get('duration_seconds', 0)}秒"
            rooms = ", ".join(record.get("room_ids", []))
            if len(rooms) > 20:
                rooms = rooms[:20] + "..."
            accounts = ", ".join(a.get("account_name", "") for a in record.get("accounts", []))
            if len(accounts) > 25:
                accounts = accounts[:25] + "..."
            status = record.get("status", "-")
            anomaly_count = len(record.get("anomalies", []))
            anomaly_text = f"{anomaly_count}次" if anomaly_count > 0 else "无"

            # 确定标签
            tags = ()
            if anomaly_count > 0:
                tags = ("anomaly",)
            elif status == "已完成":
                tags = ("success",)
            elif status == "异常中断":
                tags = ("anomaly",)
            elif status == "已停止":
                tags = ("warning",)

            self.history_tree.insert("", tk.END, values=(start_time, end_time, duration, rooms, accounts, status, anomaly_text), tags=tags)

        self.history_page_label.config(text=f"第 {self.history_page + 1}/{total_pages} 页（每页{self.history_page_size}条）")

    def _history_prev_page(self):
        if self.history_page > 0:
            self.history_page -= 1
            self._refresh_history_view()

    def _history_next_page(self):
        total_pages = max(1, (len(self.watch_history) + self.history_page_size - 1) // self.history_page_size)
        if self.history_page < total_pages - 1:
            self.history_page += 1
            self._refresh_history_view()

    def _show_history_detail(self, event):
        """双击显示记录详情"""
        selection = self.history_tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.history_tree.item(item, "values")
        start_time = values[0]
        # 找到对应的记录
        record = None
        for r in self.watch_history:
            if r.get("start_time") == start_time:
                record = r
                break
        if not record:
            return

        detail_win = tk.Toplevel(self.history_window)
        detail_win.title(f"看播详情 - {start_time}")
        detail_win.geometry("700x550")
        detail_win.configure(bg=COLORS["bg_dark"])
        detail_win.transient(self.history_window)

        # 基本信息
        info_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(info_frame, text="基本信息", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        info_text = (
            f"开始时间: {record.get('start_time', '-')}\n"
            f"结束时间: {record.get('end_time', '-')}\n"
            f"观看时长: {record.get('duration_seconds', 0)}秒（目标{record.get('target_minutes', 0)}分钟）\n"
            f"直播间: {', '.join(record.get('room_ids', []))}\n"
            f"状态: {record.get('status', '-')}\n"
            f"心跳间隔: {record.get('heartbeat_interval', '-')}秒"
        )
        tk.Label(info_frame, text=info_text, bg=COLORS["bg_card"], fg=COLORS["text_primary"], font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(0, 10))

        # 账户统计
        acc_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        acc_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(acc_frame, text="账户统计", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        for acc in record.get("accounts", []):
            acc_text = f"  {acc.get('account_name', '-')}: 观看{acc.get('watch_seconds', 0)}秒, 心跳{acc.get('heartbeat_count', 0)}次, 状态{acc.get('status', '-')}"
            color = COLORS["danger"] if acc.get("anomalies") else COLORS["text_primary"]
            tk.Label(acc_frame, text=acc_text, bg=COLORS["bg_card"], fg=color, font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=15)

        # 异常事件
        anom_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        anom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tk.Label(anom_frame, text=f"异常事件（{len(record.get('anomalies', []))}次）", bg=COLORS["bg_card"], fg=COLORS["danger"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        if record.get("anomalies"):
            text_widget = tk.Text(anom_frame, bg=COLORS["bg_dark"], fg=COLORS["text_primary"], font=("微软雅黑", 9), height=8, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            for anom in record["anomalies"]:
                line = f"[{anom.get('time', '-')}] {anom.get('type', '-')}: {anom.get('message', '-')}"
                if anom.get("account"):
                    line += f"（账户: {anom['account']}）"
                if anom.get("room"):
                    line += f"（直播间: {anom['room']}）"
                text_widget.insert(tk.END, line + "\n")
            text_widget.config(state=tk.DISABLED)
        else:
            tk.Label(anom_frame, text="  无异常事件", bg=COLORS["bg_card"], fg=COLORS["success"], font=("微软雅黑", 10)).pack(anchor=tk.W, padx=15, pady=(0, 10))

    def export_watch_history_excel(self):
        """导出看播历史记录为Excel"""
        try:
            from tkinter import filedialog
            default_name = f"看播历史记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile=default_name,
                title="导出看播历史记录"
            )
            if not file_path:
                return

            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment
            except ImportError:
                self.log("⚠ 未安装openpyxl，尝试使用csv格式导出")
                # 降级为CSV
                csv_path = file_path.replace(".xlsx", ".csv")
                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(["开始时间", "结束时间", "观看时长(秒)", "目标时长(分钟)", "直播间", "账户", "状态", "异常次数", "异常详情"])
                    for r in self.watch_history:
                        anom_details = "; ".join(f"[{a.get('time','')}]{a.get('type','')}:{a.get('message','')}" for a in r.get("anomalies", []))
                        writer.writerow([
                            r.get("start_time", ""),
                            r.get("end_time", ""),
                            r.get("duration_seconds", 0),
                            r.get("target_minutes", 0),
                            ", ".join(r.get("room_ids", [])),
                            ", ".join(a.get("account_name", "") for a in r.get("accounts", [])),
                            r.get("status", ""),
                            len(r.get("anomalies", [])),
                            anom_details
                        ])
                self.log(f"✓ 已导出CSV: {csv_path}")
                return

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "看播历史记录"

            # 表头
            headers = ["开始时间", "结束时间", "观看时长(秒)", "目标时长(分钟)", "直播间", "账户", "状态", "异常次数", "异常详情"]
            header_fill = PatternFill(start_color="16213e", end_color="16213e", fill_type="solid")
            header_font = Font(color="00d9ff", bold=True, size=11)
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # 数据
            danger_fill = PatternFill(start_color="2d1b1b", end_color="2d1b1b", fill_type="solid")
            for row_idx, r in enumerate(self.watch_history, 2):
                anom_details = "; ".join(f"[{a.get('time','')}]{a.get('type','')}:{a.get('message','')}" for a in r.get("anomalies", []))
                values = [
                    r.get("start_time", ""),
                    r.get("end_time", ""),
                    r.get("duration_seconds", 0),
                    r.get("target_minutes", 0),
                    ", ".join(r.get("room_ids", [])),
                    ", ".join(a.get("account_name", "") for a in r.get("accounts", [])),
                    r.get("status", ""),
                    len(r.get("anomalies", [])),
                    anom_details
                ]
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=row_idx, column=col, value=value)
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    if len(r.get("anomalies", [])) > 0:
                        cell.fill = danger_fill
                        cell.font = Font(color="ff4757")

            # 列宽
            widths = [18, 18, 12, 14, 25, 30, 10, 10, 50]
            for col, width in enumerate(widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

            wb.save(file_path)
            self.log(f"✓ 已导出Excel: {file_path}")
            from tkinter import messagebox
            messagebox.showinfo("导出成功", f"看播历史记录已导出到:\n{file_path}")
        except Exception as e:
            import traceback
            self.log(f"[错误] 导出Excel失败: {e}")
            self.log(traceback.format_exc())
            from tkinter import messagebox
            messagebox.showerror("导出失败", f"导出Excel失败: {e}")

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
            # 保存所有直播间栏的选择
            room_selections = []
            for bar, combo, del_btn in self.watch_room_bars:
                selected = combo.get().strip()
                if selected:
                    room_selections.append(selected)
            self.watch_config["room_selections"] = room_selections
            self.watch_config["room_bar_count"] = len(self.watch_room_bars)
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            atomic_write_json(config_file, self.watch_config)
        except Exception:
            pass

    def apply_watch_config(self):
        try:
            self._refresh_room_combo_values()
            # 恢复直播间栏数量
            bar_count = self.watch_config.get("room_bar_count", 1)
            while len(self.watch_room_bars) < bar_count:
                self._add_watch_room_bar()
            # 恢复直播间选择
            room_selections = self.watch_config.get("room_selections", [])
            for i, (bar, combo, del_btn) in enumerate(self.watch_room_bars):
                if i < len(room_selections) and room_selections[i]:
                    combo.set(room_selections[i])
                else:
                    combo.set("")
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

    def load_gift_config(self):
        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,
            "selected_accounts": [],
            "room_history": []
        }
        config_file = BASE_DIR / "gift_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_gift_config(self):
        try:
            current_room = self.gift_room_combo.get().strip()
            self.gift_config["room_name"] = current_room  # 保存直播间名称
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            # 保存选中的送礼账户
            selected = self.gift_account_combo.get()
            self.gift_config["selected_account"] = selected
            config_file = BASE_DIR / "gift_config.json"
            atomic_write_json(config_file, self.gift_config)
        except Exception:
            pass

    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self._refresh_gift_room_combo_values()
            # 恢复直播间名称（兼容旧配置的room_id）
            room_name = cfg.get("room_name", cfg.get("room_id", ""))
            if room_name:
                self.gift_room_combo.set(room_name)
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected and selected in self.gift_account_combo["values"]:
                self.gift_account_combo.set(selected)
        except Exception:
            pass

    def _refresh_gift_room_combo_values(self):
        """刷新送礼直播间下拉框选项：只显示直播间管理中的直播间名称"""
        if not hasattr(self, 'gift_room_combo') or not self.gift_room_combo.winfo_exists():
            return
        values = []
        for room in self.room_mgr.rooms:
            values.append(room["name"])
        self.gift_room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.gift_room_combo.get() not in values:
            self.gift_room_combo.set("")

    def _on_gift_room_selected(self, event=None):
        """选择送礼直播间下拉框时：保存配置"""
        self.save_gift_config()

    def _get_gift_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.gift_room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None

    def bind_auto_save(self):
        try:
            # 直播间多栏选择的保存绑定在_add_watch_room_bar中
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            # 送礼下拉框绑定
            self.gift_room_combo.bind("<<ComboboxSelected>>", self._on_gift_room_selected)
            self.gift_num_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        except Exception:
            pass

    def _refresh_room_combo_values(self):
        """刷新所有直播间栏的下拉框选项"""
        values = [room["name"] for room in self.room_mgr.rooms]
        for bar, combo, del_btn in getattr(self, 'watch_room_bars', []):
            current = combo.get()
            combo["values"] = values
            if current not in values:
                combo.set("")

    def _add_watch_room_bar(self):
        """添加一个直播间选择栏"""
        bar = tk.Frame(self.watch_room_container, bg=COLORS["bg_card"])
        bar.pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(bar, width=20, values=[], state="readonly")
        combo.pack(side=tk.LEFT)
        combo.set("")
        # 第一个栏不显示删除按钮，后面添加的栏才显示
        is_first = len(self.watch_room_bars) == 0
        del_btn = None
        if not is_first:
            del_btn = tk.Button(bar, text="✕", bg=COLORS["danger"], fg="#ffffff", font=("微软雅黑", 8),
                                bd=0, padx=4, pady=1, cursor="hand2", command=lambda b=bar: self._remove_watch_room_bar(b))
            del_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.watch_room_bars.append((bar, combo, del_btn))
        self._refresh_room_combo_values()

    def _remove_watch_room_bar(self, bar):
        """删除一个直播间选择栏"""
        if len(self.watch_room_bars) <= 1:
            return
        for i, (b, c, d) in enumerate(self.watch_room_bars):
            if b == bar:
                b.destroy()
                self.watch_room_bars.pop(i)
                break
        # 第一个栏没有删除按钮，后面的栏保持正常状态
        for idx, (b, c, d) in enumerate(self.watch_room_bars):
            if d is not None and idx > 0:
                d.config(state=tk.NORMAL)

    def _get_watch_room_ids(self):
        """获取所有选中的直播间号"""
        room_ids = []
        for bar, combo, del_btn in self.watch_room_bars:
            selected = combo.get().strip()
            if selected:
                for room in self.room_mgr.rooms:
                    if room["name"] == selected:
                        room_ids.append(room["id"])
                        break
        return room_ids

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

    def get_battery_balance(self, account):
        """查询账户电池余额（gold字段，后两位为小数，100=1电池）"""
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                wallet = data.get("data", {})
                # gold字段是电池数，后两位为小数，如100=1电池
                gold_raw = wallet.get("gold", 0)
                battery = gold_raw / 100.0 if gold_raw else 0
                return battery
            return None
        except Exception:
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

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(settings_card, text="看播设置", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        # 直播间多栏选择容器
        self.watch_room_bars = []
        self.watch_room_container = tk.Frame(row1, bg=COLORS["bg_card"])
        self.watch_room_container.pack(side=tk.LEFT, padx=(8, 0))
        self._add_watch_room_bar()
        # 添加直播间栏按钮
        self.add_room_bar_btn = tk.Button(row1, text="+ 添加", bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 9),
                                           bd=0, padx=8, pady=2, cursor="hand2", command=self._add_watch_room_bar)
        self.add_room_bar_btn.pack(side=tk.LEFT, padx=(8, 20))
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
        self.history_btn = DarkButton(row2, "📋 历史记录", command=self.show_watch_history, width=160, height=40, bg_color=COLORS["accent"], text_color="#000000")
        self.history_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 送礼设置卡片
        gift_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        gift_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(gift_card, text="送礼设置（牛蛙牛蛙）", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        gift_inner = tk.Frame(gift_card, bg=COLORS["bg_card"])
        gift_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 送礼账户选择（下拉单选）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_account_combo = ttk.Combobox(gift_acc_row, width=25, values=[], state="readonly")
        self.gift_account_combo.pack(side=tk.LEFT, padx=(8, 10))
        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        # 查询电池按钮
        self.gift_query_battery_btn = tk.Button(gift_acc_row, text="查询电池", bg=COLORS["accent"], fg="white", font=("微软雅黑", 10), bd=0, padx=12, pady=3, cursor="hand2", command=self._query_gift_battery)
        self.gift_query_battery_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.gift_battery_label = tk.Label(gift_acc_row, text="", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.gift_battery_label.pack(side=tk.LEFT)

        gift_row1 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=3)
        tk.Label(gift_row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_combo = ttk.Combobox(gift_row1, width=24, values=[], state="readonly")
        self.gift_room_combo.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row1, text="礼物:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        tk.Label(gift_row1, text="牛蛙牛蛙", bg=COLORS["bg_input"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), padx=10, pady=2).pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row1, text="数量:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_num_var = tk.IntVar(value=1)
        self.gift_num_combo = ttk.Combobox(gift_row1, textvariable=self.gift_num_var, width=6, values=[1, 10], state="readonly")
        self.gift_num_combo.pack(side=tk.LEFT, padx=(8, 0))

        gift_row2 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row2.pack(fill=tk.X, pady=3)
        tk.Label(gift_row2, text="送礼间隔(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_interval_var = tk.IntVar(value=10)
        self.gift_interval_entry = tk.Entry(gift_row2, width=8, textvariable=self.gift_interval_var, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_interval_entry.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row2, text="送礼次数:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_count_var = tk.IntVar(value=0)
        self.gift_count_entry = tk.Entry(gift_row2, width=8, textvariable=self.gift_count_var, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_count_entry.pack(side=tk.LEFT, padx=(8, 20))
        self.gift_start_btn = DarkButton(gift_row2, "▶ 开始送礼", command=self.start_gift, width=140, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.gift_start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.gift_stop_btn = DarkButton(gift_row2, "■ 停止送礼", command=self.stop_gift, width=140, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.gift_stop_btn.pack(side=tk.LEFT)
        self.gift_stop_btn.config(state=tk.DISABLED)

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
        # 同时刷新送礼账户下拉框
        self._refresh_gift_account_combo()

    def _refresh_gift_account_combo(self):
        """刷新送礼账户下拉框，只显示账户名"""
        if not hasattr(self, 'gift_account_combo'):
            return
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(name)
        # 保存当前选择
        current = self.gift_account_combo.get()
        self.gift_account_combo["values"] = values
        # 恢复选择
        if current and current in values:
            self.gift_account_combo.set(current)
        elif values:
            self.gift_account_combo.set(values[0])

    def _query_gift_battery(self):
        """查询当前选中送礼账户的电池余额"""
        selected_name = self.gift_account_combo.get()
        if not selected_name:
            self.gift_battery_label.config(text="请先选择账户")
            return
        self.gift_battery_label.config(text="查询中...")
        self.gift_query_battery_btn.config(state=tk.DISABLED)
        # 异步查询
        def query():
            battery = None
            for acc in self.account_mgr.accounts:
                if acc.get("name") == selected_name:
                    battery = self.get_battery_balance(acc)
                    break
            # 在UI线程更新
            def update():
                if battery is not None:
                    self.gift_battery_label.config(text=f"电池余额: {battery}")
                else:
                    self.gift_battery_label.config(text="查询失败")
                self.gift_query_battery_btn.config(state=tk.NORMAL)
            self.after(0, update)
        threading.Thread(target=query, daemon=True).start()

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
        """线程安全的日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, log_msg)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except Exception:
                pass
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, _update)
            elif hasattr(self, 'app') and hasattr(self.app, 'root') and self.app.root:
                self.app.root.after(0, _update)
            else:
                _update()
        except Exception:
            _update()

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
                    if client["running"]:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            self.log(f"  [{name}] {delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
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
                    if client["running"]:
                        err_str = str(error)
                        # 连接成功后过滤ping/pong等无关错误，初始连接失败时全部输出
                        if client["connected"]:
                            if "ping/pong" not in err_str and "Connection to remote host was lost" not in err_str:
                                self.log(f"  [{name}] 弹幕连接错误: {error}")
                        else:
                            self.log(f"  [{name}] 弹幕初始连接错误: {error}")

                def on_close(ws, *args):
                    was_connected = client["connected"]
                    client["connected"] = False
                    if name in self.account_stats:
                        self.account_stats[name]["ws_connected"] = False
                    # 自动重连（包括初始连接失败的情况）
                    if client["running"]:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            reason = "断开" if was_connected else "初始连接失败"
                            self.log(f"  [{name}] 弹幕连接{reason}，{delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
                        else:
                            self.log(f"  [{name}] 弹幕重连次数过多(15次)，停止重连")

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
                # 异常时也安排重连
                if client["running"]:
                    client["reconnect_count"] += 1
                    if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            self.log(f"  [{name}] {delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
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
                # P1-E: 取消待触发的重连定时器，防止关闭后继续重连
                try:
                    if client.get("reconnect_timer"):
                        client["reconnect_timer"].cancel()
                except Exception:
                    pass
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

    def x25kn_thread_func(self, account, room_id, area_id, parent_id, up_id, name, deadline=None):
        """X25Kn观看心跳线程：E接口进入后，按心跳间隔循环X接口"""
        # P1-F: deadline检查，超过目标时长自动停止
        if deadline and time.time() > deadline:
            self.log(f"  [{name}] X25Kn已超过deadline，不启动")
            return
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
            # P1-F: deadline检查，超过目标时长自动停止
            if deadline and time.time() > deadline:
                self.log(f"  [{name}] X25Kn已超过deadline，停止心跳")
                break
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
        consecutive_404 = 0  # 连续视频流404计数
        stream_paused = False  # 播放流是否已暂停（连续404过多时暂停，心跳继续）
        self.log(f"  [{name}] 播放线程已启动")
        
        while not self.stop_flag["stop"] and self.running:
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
                            # 连续404检测：直播间可能已关播
                            if resp.status_code == 404:
                                consecutive_404 += 1
                                # 第1次404就记录异常（避免用户看不到异常）
                                if consecutive_404 == 1:
                                    self.add_watch_anomaly("视频流404", f"视频流HTTP 404（第{consecutive_404}次），直播间{room_id}可能已关播或波动", account_name=name, room_id=str(room_id))
                                elif consecutive_404 == 3:
                                    self.add_watch_anomaly("直播间关播", f"视频流连续3次HTTP 404，直播间{room_id}可能已关播", account_name=name, room_id=str(room_id))
                                    self.log(f"  [{name}] ⚠ 连续3次404，判定直播间可能关播，已记录异常，加大重试间隔")
                                if consecutive_404 >= 10 and not stream_paused:
                                    stream_paused = True
                                    self.add_watch_anomaly("播放暂停", f"视频流连续{consecutive_404}次404，暂停播放线程（心跳继续）", account_name=name, room_id=str(room_id))
                                    self.log(f"  [{name}] ⚠ 连续{consecutive_404}次404，暂停播放线程（心跳继续保持）")
                            else:
                                consecutive_404 = 0
                            # 连续404时加大重试间隔：3次后30秒，暂停后60秒
                            wait_time = 5
                            if consecutive_404 >= 3:
                                wait_time = 30
                            if stream_paused:
                                wait_time = 60
                            time.sleep(wait_time)
                            continue
                        consecutive_404 = 0
                        if stream_paused:
                            stream_paused = False
                            self.log(f"  [{name}] ✓ 视频流恢复，解除暂停")
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
        try:
            if self.running:
                self.log("⚠ 看播任务已在运行中，请勿重复点击")
                return
            room_ids = self._get_watch_room_ids()
            if not room_ids:
                messagebox.showwarning("提示", "请至少选择一个直播间（可在账户管理页面添加）")
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
            self.stop_flag["stop"] = False  # P1-A: 不换对象，只改key，防止旧线程复活
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            for bar, combo, del_btn in self.watch_room_bars:
                combo.config(state=tk.DISABLED)
                if del_btn is not None:
                    del_btn.config(state=tk.DISABLED)
            self.add_room_bar_btn.config(state=tk.DISABLED)
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
            # 开始历史记录
            self.start_watch_record(room_ids, selected_accounts)
            # 启动快照定时器（5分钟后第一次）
            self.watch_snapshot_timer = self.after(300000, self.save_watch_snapshot)
            self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
            self.watch_thread.start()
        except Exception as e:
            import traceback
            self.log(f"[错误] start_watch异常: {e}")
            self.log(traceback.format_exc())
            # P0-B: 完整回滚UI状态
            self.running = False
            self.stop_flag["stop"] = True
            # 取消快照定时器
            try:
                if hasattr(self, 'watch_snapshot_timer') and self.watch_snapshot_timer:
                    self.after_cancel(self.watch_snapshot_timer)
            except Exception:
                pass
            # 结束记录（标记为启动失败）
            try:
                if self.current_watch_record:
                    self.finish_watch_record(status="启动失败")
                    self.current_watch_record = None
            except Exception:
                pass
            self._reset_watch_ui()
            messagebox.showerror("错误", f"启动看播失败: {e}")

    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        for bar, combo, del_btn in self.watch_room_bars:
            combo.config(state="readonly")
            if del_btn is not None:
                del_btn.config(state=tk.NORMAL)
        self.add_room_bar_btn.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        # 停止所有x25kn心跳线程
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()
        # 停止播放线程（stop_flag已设置，线程会自动退出）
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")
        # 结束历史记录
        if self.current_watch_record:
            self.finish_watch_record(status="已停止")

    def _watch_loop(self, room_ids, selected_accounts):
        import random
        base_interval = self.interval_var.get()
        target_seconds = self.duration_var.get() * 60
        # P1-5: 用monotonic记录开始时间，替代sleep累加计时
        watch_start_time = time.monotonic()
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
                    self.add_watch_anomaly("进入直播间失败", msg, account_name=name, room_id=rid)
                time.sleep(random.uniform(0.5, 1.5))
            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
                self.account_stats[name]["ws_connected"] = False
                # 获取房间信息（浏览器加载页面时会调用）
                try:
                    self.get_room_info(room_ids[0], acc)
                except Exception as e:
                    self.log(f"  [{name}] 获取房间信息异常: {e}")
                # 建立WebSocket弹幕连接（对第一个直播间建立连接，让账户出现在在线观众列表）
                if WEBSOCKET_AVAILABLE and room_ids:
                    self.log(f"  [{name}] 正在建立弹幕连接...")
                    try:
                        ws_client = self.connect_ws_danmaku(acc, room_ids[0])
                        if ws_client:
                            self.ws_clients[name] = ws_client
                            self.log(f"  [{name}] ✓ 弹幕连接线程已启动")
                        else:
                            self.log(f"  [{name}] ✗ 弹幕连接建立失败（返回None）")
                    except Exception as e:
                        self.log(f"  [{name}] ✗ 弹幕连接异常: {e}")
                elif not WEBSOCKET_AVAILABLE:
                    self.log(f"  [{name}] ⚠ websocket-client不可用，跳过弹幕连接")
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
            # P1-F: 传入deadline，超过目标时长+60秒缓冲后自动停止
            x25kn_deadline = time.time() + target_seconds + 60
            t = threading.Thread(target=self.x25kn_thread_func,
                                 args=(acc, room_ids[0], area_id, parent_id, up_id, name, x25kn_deadline),
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
                        # P1-5: 用monotonic差值计算真实观看时长，替代sleep累加
                        stats["watch_seconds"] = int(time.monotonic() - watch_start_time)
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
                        self.add_watch_anomaly("心跳失败", msg, account_name=name, room_id=rid)
                    time.sleep(random.uniform(0.3, 0.8))
                # 播放模拟在独立线程中持续执行
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    watch_min = stats["watch_seconds"] // 60
                    self.log(f"  [{name}] 心跳累计 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)

    def _reset_watch_ui(self):
        """P0-B: 统一的UI复位逻辑，供正常结束和异常回滚共用"""
        try:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        except Exception:
            pass
        try:
            for bar, combo, del_btn in self.watch_room_bars:
                combo.config(state="readonly")
                if del_btn is not None:
                    del_btn.config(state=tk.NORMAL)
        except Exception:
            pass
        try:
            self.add_room_bar_btn.config(state=tk.NORMAL)
            self.duration_combo.config(state="readonly")
            self.interval_combo.config(state="readonly")
        except Exception:
            pass
        try:
            for cb in self.account_checkbuttons:
                cb.config(state=tk.NORMAL)
            self.select_all_btn.config(state=tk.NORMAL)
            self.deselect_all_btn.config(state=tk.NORMAL)
        except Exception:
            pass

    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        # 结束历史记录（已完成状态）
        if self.current_watch_record:
            self.finish_watch_record(status="已完成")
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        self.close_all_ws()
        self._reset_watch_ui()

    # ========== 送礼功能 ==========
    def get_gift_id(self, account):
        """查询牛哇牛哇的gift_id（优先选bag_gift=0可直接用电池送的）"""
        if self.gift_id_cache:
            return self.gift_id_cache
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            # 获取礼物列表
            url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                gift_list = data.get("data", {}).get("list", [])
                # 优先找bag_gift=0（可直接用电池送）的牛哇牛哇
                for gift in gift_list:
                    name = gift.get("name", "")
                    bag_gift = gift.get("bag_gift", 0)
                    if ("牛哇" in name or "牛蛙" in name) and bag_gift == 0:
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {name} (id={gift['id']}, 价格={gift.get('price', 0)}, 可直接电池送)")
                        return gift["id"]
                # 找不到bag_gift=0的，找任意牛哇牛哇
                for gift in gift_list:
                    name = gift.get("name", "")
                    if "牛哇" in name or "牛蛙" in name:
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {name} (id={gift['id']}, 价格={gift.get('price', 0)})")
                        return gift["id"]
            self.log("  ⚠ 未找到牛哇牛哇礼物，使用默认id=31039")
            self.gift_id_cache = 31039
            return 31039
        except Exception as e:
            self.log(f"  ⚠ 查询礼物ID失败: {e}，使用默认id=31039")
            self.gift_id_cache = 31039
            return 31039

    def get_room_info(self, room_id, account):
        """获取直播间信息（ruid等）"""
        try:
            sessdata = account.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
            return {}
        except Exception:
            return {}

    def send_gift(self, account, room_id, gift_id, gift_num):
        """发送礼物（直接用电池购买送出）"""
        try:
            name = account.get("name", "未知")
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "") or account.get("DedeUserID", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            # 获取直播间ruid
            room_info = self.get_room_info(room_id, account)
            ruid = room_info.get("uid", "")
            # 送礼接口（直接用电池送，不是背包送礼）
            url = "https://api.live.bilibili.com/gift/v2/live/send"
            data = {
                "uid": uid,
                "gift_id": gift_id,
                "ruid": ruid,
                "gift_num": gift_num,
                "platform": "pc",
                "biz_code": "live",
                "biz_id": room_id,
                "rnd": int(time.time()),
                "storm_beat_id": "0",
                "metadata": "",
                "price": "100",
                "coin_type": "gold",
                "csrf_token": bili_jct,
                "csrf": bili_jct,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
            }
            resp = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
            result = resp.json()
            code = result.get("code", -1)
            msg = result.get("message", "") or result.get("msg", "")
            # 错误码中文说明
            error_map = {
                200007: "该房间不支持投喂该礼物",
                200010: "该礼物仅限从包裹中送出",
                200013: "余额不足（电池不够）",
                200014: "参数错误",
                200036: "该道具不能在这个房间投喂",
                75255: "库存已经使用完",
                -401: "请先登录（cookies失效）",
            }
            if code == 0:
                return True, "送礼成功"
            else:
                detail = error_map.get(code, msg)
                return False, f"[{code}] {detail}"
        except Exception as e:
            return False, f"网络异常: {e}"

    def start_gift(self):
        """开始送礼"""
        # 防重复调用
        if self.gift_running:
            self.log("⚠ 送礼任务已在运行中，请勿重复点击")
            return
        room_id = self._get_gift_room_id()
        if not room_id:
            self.log("✗ 请先选择直播间（可在账户管理页面添加直播间）")
            return
        # 获取选中的送礼账户
        selected_name = self.gift_account_combo.get()
        selected_accounts = []
        for acc in self.account_mgr.accounts:
            if acc.get("name") == selected_name:
                selected_accounts.append(acc)
                break
        if not selected_accounts:
            self.log("✗ 请先选择送礼账户")
            return
        gift_num = self.gift_num_var.get()
        interval = self.gift_interval_var.get()
        max_count = self.gift_count_var.get()
        # 检查次数
        if max_count <= 0:
            self.log("✗ 送礼次数必须大于0，请先设置送礼次数")
            return
        # 计算总消耗电池数（牛蛙牛蛙1电池/个）
        total_battery = len(selected_accounts) * max_count * gift_num
        # 确认弹窗，防止误触
        confirm = messagebox.askyesno("送礼确认",
            f"当前操作共计消耗 {total_battery} 电池\n\n"
            f"账户数: {len(selected_accounts)} 个\n"
            f"送礼次数: {max_count} 次\n"
            f"每次数量: 牛蛙牛蛙x{gift_num}\n"
            f"单个价格: 1电池/个\n\n"
            f"是否继续？",
            icon="warning")
        if not confirm:
            self.log("⏹ 已取消送礼操作")
            return
        self.save_gift_config()
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{max_count}")
        self.log(f"  共 {len(selected_accounts)} 个账户参与送礼")
        # 为每个账户启动独立线程
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.gift_stop[name] = False
            t = threading.Thread(target=self._gift_worker, args=(acc, room_id, gift_num, interval, max_count), daemon=True)
            self.gift_threads[name] = t
            t.start()
            time.sleep(0.5)  # 错开启动

    def _gift_worker(self, account, room_id, gift_num, interval, max_count):
        """送礼工作线程"""
        name = account.get("name", "未知")
        count = 0
        try:
            # 先查询gift_id
            gift_id = self.get_gift_id(account)
            while not self.gift_stop.get(name, True) and self.gift_running:
                if count >= max_count:
                    self.log(f"  [{name}] ✓ 已达到最大送礼次数 ({max_count}次)")
                    break
                success, msg = self.send_gift(account, room_id, gift_id, gift_num)
                count += 1
                if success:
                    self.log(f"  [{name}] 第{count}次: ✓ {msg} (牛蛙牛蛙x{gift_num})")
                else:
                    self.log(f"  [{name}] 第{count}次: ✗ {msg}")
                    # P1-D/P1-10: 余额不足时立即停止该账户送礼，避免无效重试
                    if "余额不足" in msg or "200013" in msg or "电池不够" in msg:
                        self.log(f"  [{name}] ⚠ 电池余额不足，停止该账户送礼")
                        break
                # 等待间隔
                for _ in range(int(interval * 10)):
                    if self.gift_stop.get(name, True) or not self.gift_running:
                        break
                    time.sleep(0.1)
        except Exception as e:
            self.log(f"  [{name}] 送礼线程异常: {e}")
        finally:
            self.log(f"  [{name}] 送礼结束，共尝试 {count} 次")
            self.gift_threads.pop(name, None)
            # 检查是否所有线程都结束了
            if not self.gift_threads:
                self.after(100, self._on_gift_finished)

    def _on_gift_finished(self):
        """送礼全部结束"""
        self.gift_running = False
        self.gift_start_btn.config(state=tk.NORMAL)
        self.gift_stop_btn.config(state=tk.DISABLED)
        self.log("✓ 所有账户送礼已结束")

    def stop_gift(self):
        """停止送礼"""
        self.gift_running = False
        for name in self.gift_stop:
            self.gift_stop[name] = True
        self.log("⏹ 正在停止所有送礼线程...")
        self.gift_start_btn.config(state=tk.NORMAL)
        self.gift_stop_btn.config(state=tk.DISABLED)
        self.refresh_status_tree()
        self.log("送礼任务结束")


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
        """线程安全的日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.schedule_log_text.config(state=tk.NORMAL)
                self.schedule_log_text.insert(tk.END, line)
                self.schedule_log_text.see(tk.END)
                self.schedule_log_text.config(state=tk.DISABLED)
            except Exception:
                pass
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, _update)
            elif hasattr(self, 'app') and hasattr(self.app, 'root') and self.app.root:
                self.app.root.after(0, _update)
            else:
                _update()
        except Exception:
            _update()

    def sync_log_to_modules(self, msg):
        """将日志同步到所有相关模块页面"""
        try:
            # 同步到抢码页面
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)
        except Exception:
            pass
        try:
            # 同步到看播页面
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)
        except Exception:
            pass
        try:
            # 同步到弹幕页面（主页面日志）
            if hasattr(self.app, 'log'):
                self.app.log(msg)
        except Exception:
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
                except Exception:
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
        # P1-I: 同类任务禁止并发（抢码/看播/弹幕同一时间只能有一个在执行）
        if task["type"] in ["watch", "danmaku", "rush"]:
            for t in self.schedule_tasks:
                if t["id"] != task["id"] and t["type"] == task["type"] and t.get("status") == "执行中":
                    msg = f"⏭ [日程] 跳过任务「{task['name']}」：同类型任务「{t['name']}」正在执行中"
                    self.log(msg)
                    self.sync_log_to_modules(msg)
                    task["status"] = "已跳过"
                    self.refresh_task_list()
                    return
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
        """标记任务完成并写日志，状态重置为等待中（次日继续执行）"""
        task["status"] = "等待中"
        self.log(msg)
        self.sync_log_to_modules(msg)
        self.refresh_task_list()
        self.save_schedule()

    def _mark_task_done(self, task):
        task["status"] = "等待中"
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
        last_check_time = time.time()  # P1-14: 用于检测休眠唤醒后的时间跳跃
        warned_tasks = set()  # 已提前1分钟写过日志的任务ID
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute
                current_time = time.time()

                # P1-14: 检测休眠唤醒——如果时间跳跃超过5分钟，说明电脑休眠过
                time_jump = current_time - last_check_time
                if time_jump > 300:
                    self.log(f"⏰ 检测到系统休眠唤醒（跳过{time_jump:.0f}秒），立即检查待执行任务")
                    last_minute = -1  # 强制重新检查所有任务
                last_check_time = current_time

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    # 新的一分钟，清空已警告集合（用于第二天重复）
                    warned_tasks.clear()

                    # P1-H/P1-K: 用list快照遍历，避免execute_task修改列表导致迭代器异常
                    for task in list(self.schedule_tasks):
                        # 逐任务重校验：任务可能在遍历期间被删除/禁用
                        if task not in self.schedule_tasks:
                            continue
                        if not task.get("enabled", False):
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
            atomic_write_json(config_file, save_data)
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
            atomic_write_json(preset_file, self.schedule_presets)
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
            atomic_write_json(config_file, settings)
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
        self.card_text = get_card_remaining_text()
        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务{self.card_text}")
        self.root.geometry("1800x1400")
        self.root.minsize(1500, 1100)
        self.root.configure(bg=COLORS["bg_dark"])

        self.account_mgr = AccountManager()
        self.room_mgr = RoomManager()
        self.danmaku_list = self.load_danmaku()
        self._config_save_timer = None  # 配置保存防抖定时器
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
        # 启动时后台验证所有账号登录状态
        self._startup_check_accounts()

    def _startup_check_accounts(self):
        """启动时在后台线程验证所有账号登录状态，失效则弹窗报错"""
        import threading
        def _check():
            try:
                import requests
                time.sleep(2)  # 等UI完全加载
                failed = []
                for acc in self.account_mgr.accounts:
                    name = acc.get("name", "未知")
                    try:
                        cookies = cookies_from_account(acc)
                        resp = requests.get("https://api.bilibili.com/x/web-interface/nav",
                                            headers=HEADERS, cookies=cookies, timeout=8)
                        data = resp.json()
                        if data.get("code") != 0:
                            failed.append(f"{name}（{data.get('message', '未知错误')}）")
                    except Exception as e:
                        failed.append(f"{name}（验证异常: {str(e)[:30]}）")
                if failed:
                    msg = "以下 " + str(len(failed)) + " 个账号登录已失效，请重新登录：\n\n" + "\n".join(failed)
                    self.root.after(0, lambda: self._show_account_login_error(msg))
                else:
                    self.log(f"✓ 启动账号验证: 全部 {len(self.account_mgr.accounts)} 个账号登录有效")
            except Exception as e:
                self.log(f"⚠ 启动账号验证异常: {e}")
        threading.Thread(target=_check, daemon=True).start()

    def _show_account_login_error(self, msg):
        """在主线程弹出账号登录失效错误"""
        from tkinter import messagebox
        self.log(f"⚠ {msg}")
        messagebox.showerror("账号登录失效", msg)

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
        """窗口关闭时：先停止所有线程 → 等待结束 → 保存配置 → 销毁窗口"""
        close_errors = []
        try:
            # 1. 停止所有运行中的模块
            if hasattr(self, 'rush_page'):
                try:
                    if hasattr(self.rush_page, 'running'):
                        self.rush_page.running = False
                    if hasattr(self.rush_page, 'nm_stop_all'):
                        self.rush_page.nm_stop_all()
                    elif hasattr(self.rush_page, 'stop_rush'):
                        self.rush_page.stop_rush()
                except Exception as e:
                    close_errors.append(f"停止抢码: {e}")
            if hasattr(self, 'watch_page'):
                try:
                    if hasattr(self.watch_page, 'running'):
                        self.watch_page.running = False
                    if hasattr(self.watch_page, 'stop_flag'):
                        self.watch_page.stop_flag["stop"] = True
                    if hasattr(self.watch_page, 'gift_running'):
                        self.watch_page.gift_running = False
                    if hasattr(self.watch_page, 'gift_stop'):
                        for name in self.watch_page.gift_stop:
                            self.watch_page.gift_stop[name] = True
                except Exception as e:
                    close_errors.append(f"停止看播: {e}")
            # 停止弹幕发送
            try:
                self.running = False
            except Exception:
                pass
            # 停止调度器
            if hasattr(self, 'schedule_page'):
                try:
                    if hasattr(self.schedule_page, 'stop_scheduler'):
                        self.schedule_page.stop_scheduler()
                except Exception as e:
                    close_errors.append(f"停止调度器: {e}")
            # 取消定时关机
            try:
                self.cancel_shutdown()
            except Exception as e:
                close_errors.append(f"取消关机: {e}")

            # 2. 等待线程结束（最多2秒）
            time.sleep(0.5)

            # 3. 保存所有配置
            try:
                self.save_config()
            except Exception as e:
                close_errors.append(f"保存配置: {e}")
            try:
                self.save_danmaku_silent()
            except Exception as e:
                close_errors.append(f"保存弹幕: {e}")
            if hasattr(self, 'rush_page'):
                try:
                    self.rush_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存抢码: {e}")
            if hasattr(self, 'watch_page'):
                try:
                    self.watch_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存看播: {e}")
            if hasattr(self, 'schedule_page'):
                try:
                    self.schedule_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存日程: {e}")
            try:
                self.save_shutdown_config()
            except Exception as e:
                close_errors.append(f"保存关机配置: {e}")

            if close_errors:
                print(f"⚠ 关闭时出现 {len(close_errors)} 个错误:")
                for err in close_errors:
                    print(f"  - {err}")
        except Exception as e:
            print(f"✗ on_closing严重异常: {e}")
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

        self.tab_code_export = tk.Label(tab_bar, text="🎁 兑换码", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                         font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_code_export.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_code_export.bind("<Button-1>", lambda e: self.switch_tab("code_export"))

        self.tab_schedule = tk.Label(tab_bar, text="📅 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))

        self.tab_account = tk.Label(tab_bar, text="👤 账户管理", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_account.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_account.bind("<Button-1>", lambda e: self.switch_tab("account"))

        # 任务说明标签
        self.tab_guide = tk.Label(tab_bar, text="📖 使用说明", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                  font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_guide.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_guide.bind("<Button-1>", lambda e: self.switch_tab("guide"))

        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        # 左侧：版本号 + 卡密信息
        left_info = tk.Frame(footer, bg=COLORS["bg_card"])
        left_info.pack(side=tk.LEFT, padx=20)
        tk.Label(left_info, text=f"{APP_VERSION}", 
                bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 15))
        self.footer_card_label = tk.Label(left_info, text=self.card_text, 
                bg=COLORS["bg_card"], fg=COLORS["success"],
                font=("微软雅黑", 10))
        self.footer_card_label.pack(side=tk.LEFT)
        
        # 右侧：设备码 + 复制按钮
        right_info = tk.Frame(footer, bg=COLORS["bg_card"])
        right_info.pack(side=tk.RIGHT, padx=20)
        machine_code = get_machine_code()
        tk.Label(right_info, text="设备码:", 
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 8))
        self.footer_machine_label = tk.Label(right_info, 
                text=f"{machine_code[:8]}...{machine_code[-8:]}", 
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                font=("Consolas", 10))
        self.footer_machine_label.pack(side=tk.LEFT, padx=(0, 8))
        copy_machine_btn = tk.Button(right_info, text="📋 复制", 
                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                font=("微软雅黑", 9), relief=tk.FLAT, cursor="hand2",
                command=lambda: self._copy_machine_code())
        copy_machine_btn.pack(side=tk.LEFT, ipadx=8, ipady=2)

        # 主内容区（标签页容器）
        self.tab_container = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.tab_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 弹幕工具页面
        self.danmaku_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.danmaku_page.pack(fill=tk.BOTH, expand=True)
        self.danmaku_page.pack_forget()

        # 抢码工具页面
        self.rush_page = RushRewardFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.rush_page.pack(fill=tk.BOTH, expand=True)

        # 定时关机页面
        self.shutdown_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.shutdown_page.pack(fill=tk.BOTH, expand=True)
        self.shutdown_page.pack_forget()
        self.build_shutdown_page()

        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        # 兑换码导出页面
        self.code_export_page = CodeExportFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.code_export_page.pack(fill=tk.BOTH, expand=True)
        self.code_export_page.pack_forget()

        # 日程任务页面
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

        # 账户管理页面
        self.account_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.account_page.pack(fill=tk.BOTH, expand=True)
        self.account_page.pack_forget()

        # 任务说明页面
        self.guide_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.guide_page.pack(fill=tk.BOTH, expand=True)
        self.guide_page.pack_forget()
        self._build_guide_page()
        self.build_account_page()
        # 初始化弹幕工具页面的账户多选
        self._refresh_danmaku_account_checkboxes()

        self.current_tab = "rush"

        # 左侧：选择发送账户（复选框多选，参考看播布局）
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)

        tk.Label(left_card, text="选择发送账户", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))

        # 全选/取消全选按钮
        danmaku_btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        danmaku_btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.danmaku_select_all_btn = tk.Button(danmaku_btn_frame, text="全选", bg=COLORS["bg_input"],
                                                  fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0,
                                                  padx=8, pady=2, cursor="hand2", command=self._danmaku_select_all)
        self.danmaku_select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.danmaku_deselect_all_btn = tk.Button(danmaku_btn_frame, text="取消全选", bg=COLORS["bg_input"],
                                                     fg=COLORS["text_secondary"], font=("微软雅黑", 8), bd=0,
                                                     padx=8, pady=2, cursor="hand2", command=self._danmaku_deselect_all)
        self.danmaku_deselect_all_btn.pack(side=tk.LEFT)

        # 复选框区域
        self.danmaku_account_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        self.danmaku_account_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.danmaku_account_vars = {}  # 账户名 -> BooleanVar
        self.danmaku_account_checkbuttons = []

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

        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[], state="readonly")
        self.room_combo.pack(side=tk.LEFT, padx=(8, 20))

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
        # 刷新弹幕工具页面的账户多选复选框（确保UI构建完成后填充账户列表）
        self._refresh_danmaku_account_checkboxes()

    # ---------- 账户管理 ----------
    def refresh_account_list(self):
        # 兼容旧的account_listbox（如果存在）
        if hasattr(self, 'account_listbox') and self.account_listbox.winfo_exists():
            self.account_listbox.delete(0, tk.END)
            for acc in self.account_mgr.accounts:
                display = f"  {acc['name']}"
                self.account_listbox.insert(tk.END, display)

    def build_account_page(self):
        """构建账户管理页面（独立标签页）"""
        main = tk.Frame(self.account_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 左侧：账户列表
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_card.pack_propagate(False)
        left_card.configure(width=300)

        tk.Label(left_card, text="账户列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        # 账户列表（Listbox）
        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        self.manager_account_listbox = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                                    selectbackground=COLORS["accent"], selectforeground="#000000",
                                                    font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                                    activestyle="none", exportselection=False)
        self.manager_account_listbox.pack(fill=tk.BOTH, expand=True)
        self.manager_account_listbox.bind("<<ListboxSelect>>", self._on_manager_account_select)

        # 按钮区
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(10, 12))
        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=270, height=38).pack(pady=(0, 6))
        DarkButton(btn_frame, "编辑账户", command=self._manager_edit_account,
                   width=270, height=38, bg_color="#27ae60", text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "删除账户", command=self._manager_delete_account,
                   width=270, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "验证登录", command=self._manager_verify_account,
                   width=270, height=38, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "刷新信息", command=self._manager_refresh_info,
                   width=270, height=38, bg_color="#2980b9", text_color="#ffffff").pack()

        # 右侧：账户详细信息
        right_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        right_card.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 8))
        right_card.pack_propagate(False)
        right_card.configure(width=400)

        tk.Label(right_card, text="账户详细信息", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        info_frame = tk.Frame(right_card, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 信息展示区
        self.manager_info_text = tk.Text(info_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                          font=("Consolas", 10), bd=0, highlightthickness=0, wrap=tk.WORD,
                                          padx=12, pady=12)
        self.manager_info_text.pack(fill=tk.BOTH, expand=True)
        self.manager_info_text.config(state=tk.DISABLED)
        self._manager_show_info(None)

        # 复制按钮区
        copy_frame = tk.Frame(info_frame, bg=COLORS["bg_card"])
        copy_frame.pack(fill=tk.X, pady=(8, 0))
        DarkButton(copy_frame, "📋 复制 SESSDATA", command=self._manager_copy_sessdata,
                   width=180, height=32, bg_color="#8e44ad", text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(copy_frame, "📋 复制 bili_jct", command=self._manager_copy_bili_jct,
                   width=180, height=32, bg_color="#16a085", text_color="#ffffff").pack(side=tk.LEFT)

        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))

        tk.Label(room_card, text="直播间管理", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        room_inner = tk.Frame(room_card, bg=COLORS["bg_card"])
        room_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 左侧：直播间列表
        room_left = tk.Frame(room_inner, bg=COLORS["bg_card"])
        room_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.manager_room_listbox = tk.Listbox(room_left, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                                  selectbackground=COLORS["accent"], selectforeground="#000000",
                                                  font=("微软雅黑", 10), bd=0, highlightthickness=0,
                                                  activestyle="none", exportselection=False)
        self.manager_room_listbox.pack(fill=tk.BOTH, expand=True)
        self.manager_room_listbox.bind("<<ListboxSelect>>", self._on_manager_room_select)

        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=340)
        room_right.pack(side=tk.LEFT, fill=tk.Y)
        room_right.pack_propagate(False)

        tk.Label(room_right, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_id_entry = DarkEntry(room_right, width=28)
        self.room_id_entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(room_right, text="显示名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_name_entry = DarkEntry(room_right, width=28)
        self.room_name_entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(room_right, text="备注:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W)
        self.room_remark_entry = DarkEntry(room_right, width=28)
        self.room_remark_entry.pack(fill=tk.X, pady=(2, 10))

        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=320, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=320, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=320, height=34, bg_color="#2980b9", text_color="#ffffff").pack()

        self._refresh_manager_room_list()

    def _build_guide_page(self):
        """构建任务说明页面"""
        main = tk.Frame(self.guide_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 标题
        tk.Label(main, text="📖 使用说明", bg=COLORS["bg_dark"], fg=COLORS["accent"],
                 font=("微软雅黑", 16, "bold")).pack(anchor=tk.W, padx=8, pady=(0, 10))

        # 内容卡片
        card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scroll = tk.Scrollbar(card)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 文本区域
        text = tk.Text(card, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                        font=("微软雅黑", 10), bd=0, highlightthickness=0, wrap=tk.WORD,
                        padx=20, pady=20, yscrollcommand=scroll.set)
        text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=text.yview)

        # 插入任务说明内容
        text.insert(tk.END, TASK_GUIDE_TEXT)
        text.config(state=tk.DISABLED)

    def _refresh_manager_room_list(self):
        """刷新直播间管理列表"""
        if not hasattr(self, 'manager_room_listbox') or not self.manager_room_listbox.winfo_exists():
            return
        self.manager_room_listbox.delete(0, tk.END)
        for room in self.room_mgr.rooms:
            display = f"  {room['name']}"
            if room.get('remark'):
                display += f"  [{room['remark']}]"
            self.manager_room_listbox.insert(tk.END, display)

    def _on_manager_room_select(self, event):
        """选择直播间时填充表单"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            return
        room = self.room_mgr.rooms[selection[0]]
        self.room_id_entry.delete(0, tk.END)
        self.room_id_entry.insert(0, room["id"])
        self.room_name_entry.delete(0, tk.END)
        self.room_name_entry.insert(0, room["name"])
        self.room_remark_entry.delete(0, tk.END)
        self.room_remark_entry.insert(0, room.get("remark", ""))

    def _manager_add_room(self):
        """添加直播间"""
        room_id = self.room_id_entry.get().strip()
        name = self.room_name_entry.get().strip()
        remark = self.room_remark_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）")
            return
        if not name:
            name = f"直播间{room_id}"
        ok, msg = self.room_mgr.add_room(room_id, name, remark)
        if ok:
            self._refresh_manager_room_list()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已添加直播间: {name}（{room_id}）")
        else:
            messagebox.showwarning("提示", msg)

    def _manager_delete_room(self):
        """删除直播间"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的直播间")
            return
        room = self.room_mgr.rooms[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除直播间「{room['name']}」吗？"):
            self.room_mgr.delete_room(room["id"])
            self._refresh_manager_room_list()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已删除直播间: {room['name']}（{room['id']}）")

    def _manager_import_rooms_from_accounts(self):
        """从账户导入直播间"""
        count = self.room_mgr.import_from_accounts(self.account_mgr, self.log)
        self._refresh_manager_room_list()
        messagebox.showinfo("提示", f"从账户导入完成，共新增 {count} 个直播间")

    def refresh_account_manager_list(self):
        """刷新账户管理页面的账户列表"""
        if not hasattr(self, 'manager_account_listbox') or not self.manager_account_listbox.winfo_exists():
            return
        self.manager_account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"  {acc['name']}"
            self.manager_account_listbox.insert(tk.END, display)
        # 刷新弹幕工具页面的账户多选
        self._refresh_danmaku_account_checkboxes()

    def _on_manager_account_select(self, event):
        """账户管理页面选择账户时显示详细信息"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            self._manager_show_info(None)
            return
        acc = self.account_mgr.accounts[selection[0]]
        self._manager_show_info(acc)

    def _manager_show_info(self, acc):
        """显示账户详细信息"""
        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        if not acc:
            self.manager_info_text.insert(tk.END, "请从左侧列表选择一个账户查看详细信息")
            self.manager_info_text.config(state=tk.DISABLED)
            return

        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", "未设置"))
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: 查询中...
直播状态: 查询中...

--- 电池余额 ---
电池数量: 查询中...

提示: 点击「刷新信息」按钮获取最新的直播间号和电池余额
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)

    def _manager_copy_sessdata(self):
        """复制当前账户的SESSDATA到剪贴板"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        sessdata = acc.get("SESSDATA", "")
        if not sessdata:
            messagebox.showwarning("提示", "该账户没有SESSDATA")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(sessdata)
            self.root.update()
            self.log(f"已复制账户「{acc.get('name', '未知')}」的SESSDATA到剪贴板")
            messagebox.showinfo("成功", "SESSDATA已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")

    def _manager_copy_bili_jct(self):
        """复制当前账户的bili_jct到剪贴板"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        bili_jct = acc.get("bili_jct", "")
        if not bili_jct:
            messagebox.showwarning("提示", "该账户没有bili_jct")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(bili_jct)
            self.root.update()
            self.log(f"已复制账户「{acc.get('name', '未知')}」的bili_jct到剪贴板")
            messagebox.showinfo("成功", "bili_jct已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")

    def _manager_refresh_info(self):
        """刷新选中账户的详细信息（直播间号、电池余额）"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", ""))

        # 获取直播间号
        room_id = "未开播"
        room_status = "未开播"
        if uid:
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={uid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid", "未开播")
                    if data["data"].get("roomStatus") == 1:
                        room_status = "直播中"
                    else:
                        room_status = "未开播"
            except Exception:
                room_id = "查询失败"
                room_status = "查询失败"

        # 获取电池余额
        battery = "查询失败"
        try:
            sessdata = acc.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get("https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1",
                                cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                gold = data["data"].get("gold", 0)
                battery = f"{gold / 100:.1f} 电池"
        except Exception:
            battery = "查询失败"

        # 更新显示
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: {room_id}
直播状态: {room_status}

--- 电池余额 ---
电池数量: {battery}
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)
        self.log(f"已刷新账户「{name}」的详细信息")

    def _manager_edit_account(self):
        """账户管理页面编辑账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        dialog = EditAccountDialog(self.root, acc, on_update=self.account_mgr.update_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()
        # 刷新看播页面账户列表
        if hasattr(self, 'watch_page'):
            self.watch_page.refresh_account_list()
        self.log(f"已编辑账户: {acc['name']}")

    def _manager_delete_account(self):
        """账户管理页面删除账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        # 检查是否有任务正在运行
        running_tasks = []
        if getattr(self, 'running', False):
            running_tasks.append('弹幕发送')
        if getattr(self, 'watch_page', None) and getattr(self.watch_page, 'running', False):
            running_tasks.append('看播')
        if getattr(self, 'watch_page', None) and getattr(self.watch_page, 'gift_running', False):
            running_tasks.append('送礼')
        if getattr(self, 'rush_page', None) and getattr(self.rush_page, 'running', False):
            running_tasks.append('抢码')
        if running_tasks:
            messagebox.showwarning("提示", f"以下任务正在运行，请先停止后再删除账户：\n{'、'.join(running_tasks)}")
            return
        if custom_askyesno(self.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_manager_list()
            self._manager_show_info(None)
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新所有直播间下拉框选项（用户列表变了）
            if hasattr(self, '_refresh_danmaku_room_combo_values'):
                self._refresh_danmaku_room_combo_values()
            if hasattr(self, 'watch_frame') and hasattr(self.watch_frame, '_refresh_room_combo_values'):
                self.watch_frame._refresh_room_combo_values()
            self.log(f"已删除账户: {acc['name']}")

    def _manager_verify_account(self):
        """账户管理页面验证登录"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择账户")
            return
        acc = self.account_mgr.accounts[selection[0]]
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        ok, msg = verify_login(cookie_str)
        if ok:
            messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}")
            self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
        else:
            messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}")
            self.log(f"账户「{acc['name']}」验证失败: {msg}")

    # ========== 弹幕工具页面账户多选 ==========
    def _refresh_danmaku_account_checkboxes(self):
        """刷新弹幕工具页面的账户多选复选框"""
        if not hasattr(self, 'danmaku_account_frame') or not self.danmaku_account_frame.winfo_exists():
            return
        for widget in self.danmaku_account_frame.winfo_children():
            widget.destroy()
        self.danmaku_account_vars.clear()
        self.danmaku_account_checkbuttons.clear()
        # 从配置加载选中的账户列表
        saved_selected = self.config.get("danmaku_selected_accounts", [])
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            # 如果有保存的选择，按保存的来；否则默认全选
            is_selected = name in saved_selected if saved_selected else True
            var = tk.BooleanVar(value=is_selected)
            self.danmaku_account_vars[name] = var
            cb = tk.Checkbutton(self.danmaku_account_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w", padx=8, pady=4,
                                command=self._on_danmaku_account_changed)
            cb.pack(fill=tk.X, anchor="w")
            self.danmaku_account_checkbuttons.append(cb)

    def _on_danmaku_account_changed(self):
        """弹幕账户选择改变时：保存配置"""
        self.save_config()

    def _danmaku_select_all(self):
        """弹幕账户全选"""
        for var in self.danmaku_account_vars.values():
            var.set(True)
        self.save_config()

    def _danmaku_deselect_all(self):
        """弹幕账户取消全选"""
        for var in self.danmaku_account_vars.values():
            var.set(False)
        self.save_config()

    def _refresh_danmaku_room_combo_values(self):
        """刷新弹幕直播间下拉框选项：只显示直播间名称，不显示数字ID"""
        if not hasattr(self, 'room_combo'):
            return
        values = [room["name"] for room in self.room_mgr.rooms]
        self.room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.room_combo.get() not in values:
            self.room_combo.set("")

    def _get_danmaku_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None

    def _on_danmaku_room_selected(self, event=None):
        """选择弹幕直播间下拉框时：保存配置"""
        self.save_config()

    def _get_danmaku_selected_accounts(self):
        """获取弹幕工具页面选中的账户列表"""
        selected = []
        for name, var in self.danmaku_account_vars.items():
            if var.get():
                for acc in self.account_mgr.accounts:
                    if acc.get("name") == name:
                        selected.append(acc)
                        break
        return selected

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
        MAX_ACCOUNTS = 8
        if len(self.account_mgr.accounts) >= MAX_ACCOUNTS:
            messagebox.showwarning("提示", f"最多只能添加 {MAX_ACCOUNTS} 个账户\n当前已有 {len(self.account_mgr.accounts)} 个，请先删除不需要的账户")
            return
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()
        # 刷新看播页面账户列表
        if hasattr(self, 'watch_page'):
            self.watch_page.refresh_account_list()

    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        # 检查是否有任务正在运行
        running_tasks = []
        if getattr(self, 'running', False):
            running_tasks.append('弹幕发送')
        if hasattr(self, 'watch_frame') and getattr(self.watch_frame, 'running', False):
            running_tasks.append('看播')
        if hasattr(self, 'gift_frame') and getattr(self.gift_frame, 'gift_running', False):
            running_tasks.append('送礼')
        if hasattr(self, 'rush_frame') and getattr(self.rush_frame, 'running', False):
            running_tasks.append('抢码')
        if running_tasks:
            messagebox.showwarning("提示", f"以下任务正在运行，请先停止后再删除账户：\n{'、'.join(running_tasks)}")
            return
        if custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新看播页面账户列表
            if hasattr(self, 'watch_page'):
                self.watch_page.refresh_account_list()
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

    def _copy_machine_code(self):
        """复制设备码到剪贴板"""
        try:
            machine_code = get_machine_code()
            self.root.clipboard_clear()
            self.root.clipboard_append(machine_code)
            self.root.update()
            # 临时显示复制成功
            old_text = self.footer_machine_label.cget("text")
            self.footer_machine_label.config(text="✓ 已复制", fg=COLORS["success"])
            self.root.after(1500, lambda: self.footer_machine_label.config(text=old_text, fg=COLORS["accent"]))
        except Exception as e:
            pass
    
    def switch_tab(self, tab_name):
        """切换标签页"""
        if tab_name == self.current_tab:
            return

        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.code_export_page.pack_forget()
        self.schedule_page.pack_forget()
        self.account_page.pack_forget()
        self.guide_page.pack_forget()

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_code_export.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_account.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_guide.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 12))

        if tab_name == "danmaku":
            self.danmaku_page.pack(fill=tk.BOTH, expand=True)
            self.tab_danmaku.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "danmaku"
            # 切换到弹幕工具时刷新账户列表
            self._refresh_danmaku_account_checkboxes()
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
        elif tab_name == "code_export":
            self.code_export_page.pack(fill=tk.BOTH, expand=True)
            self.tab_code_export.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "code_export"
            # 切换到兑换码页面时刷新列表
            self.code_export_page.refresh_list()
        elif tab_name == "schedule":
            self.schedule_page.pack(fill=tk.BOTH, expand=True)
            self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "schedule"
        elif tab_name == "account":
            self.account_page.pack(fill=tk.BOTH, expand=True)
            self.tab_account.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
            self.current_tab = "account"
            # 切换到账户管理页面时刷新列表
            self.refresh_account_manager_list()
        elif tab_name == "guide":
            self.guide_page.pack(fill=tk.BOTH, expand=True)
            self.tab_guide.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 12, "bold"))
            self.current_tab = "guide"
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
                        self.log(f"✗ 关机确认弹窗异常，已取消关机: {e}")
                        confirm_result["confirmed"] = False
                        confirm_result["done"] = True

                self.root.after(0, show_confirm_dialog)

                # 等待确认结果（最多等90秒）
                wait_count = 0
                while not confirm_result["done"] and wait_count < 90:
                    if task["stop_flag"]["stop"]:
                        break
                    time.sleep(1)
                    wait_count += 1

                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
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
            # P1-J: 纳入"待确认"状态，避免确认弹窗未处理时任务继续运行
            if task["status"] in ["等待中", "倒计时中", "待确认"]:
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
            atomic_write_json(shutdown_config_file, config)
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
                # P1-G: 所有字段恢复后再触发mode change，避免默认值覆盖配置
                if config.get("shutdown_mode"):
                    self.on_shutdown_mode_change()
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
            "danmaku_selected_accounts": [],
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default_config.update(cfg)
            except Exception:
                pass
        return default_config

    def _schedule_save_config(self):
        """调度配置保存（防抖：500ms内连续触发只保存一次）"""
        if self._config_save_timer:
            self.root.after_cancel(self._config_save_timer)
        self._config_save_timer = self.root.after(500, self.save_config)

    def save_config(self):
        try:
            self.config["room_name"] = self.room_combo.get().strip()  # 保存直播间名称
            self.config["interval_min"] = self.interval_min.get().strip()
            self.config["interval_max"] = self.interval_max.get().strip()
            self.config["send_mode"] = self.mode_var.get()
            self.config["account_mode"] = self.account_mode_var.get()
            self.config["send_limit"] = self.max_send_entry.get().strip()
            self.config["current_tab"] = self.current_tab
            self.config["window_geometry"] = self.root.geometry()
            # 保存弹幕工具选中的账户列表
            try:
                if hasattr(self, 'danmaku_account_vars'):
                    selected = [name for name, var in self.danmaku_account_vars.items() if var.get()]
                    self.config["danmaku_selected_accounts"] = selected
            except Exception:
                pass
            # 保存当前选中的账户
            try:
                selection = self.account_listbox.curselection()
                if selection:
                    idx = selection[0]
                    if idx < len(self.account_mgr.accounts):
                        self.config["selected_account"] = self.account_mgr.accounts[idx].get("name", "")
            except Exception:
                pass
            atomic_write_json(CONFIG_FILE, self.config)
        except Exception:
            pass

    def apply_config(self):
        # 初始化直播间下拉框选项
        self._refresh_danmaku_room_combo_values()
        if self.config.get("room_name"):
            self.room_combo.set(self.config["room_name"])
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
        # 恢复窗口大小和位置（如果保存的宽度小于1500则用默认值）
        if self.config.get("window_geometry"):
            try:
                geom = self.config["window_geometry"]
                width_str = geom.split("x")[0]
                if width_str.isdigit() and int(width_str) >= 1500:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1000")
            except Exception:
                self.root.geometry("1600x1000")
        # 绑定自动保存
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)
        self.interval_min.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_max.bind("<FocusOut>", lambda e: self.save_config())
        self.max_send_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.mode_var.trace_add("write", lambda *a: self.save_config())
        self.account_mode_var.trace_add("write", lambda *a: self.save_config())
        # 窗口大小变化时保存
        self.root.bind("<Configure>", lambda e: self._schedule_save_config() if e.widget == self.root else None)

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
        """线程安全的日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except Exception:
                pass
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, _update)
            elif hasattr(self, 'app') and hasattr(self.app, 'root') and self.app.root:
                self.app.root.after(0, _update)
            else:
                _update()
        except Exception:
            _update()

    # ---------- 发送控制 ----------
    def start_sending(self):
        # P1-Q: 运行中守卫，防止并发启动双倍发送
        if self.running or (hasattr(self, 'send_thread') and self.send_thread and self.send_thread.is_alive()):
            messagebox.showwarning("提示", "弹幕发送正在运行中，请先停止当前任务")
            return
        # 从弹幕工具页面的账户多选复选框获取选中的账户
        accounts = self._get_danmaku_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先勾选至少一个发送账户")
            return
        # P1-R: 从界面单选按钮读取account_mode，而不是根据账户数量推断
        try:
            account_mode = self.account_mode_var.get()
            if account_mode not in ("single", "multi", "rotate"):
                account_mode = "multi" if len(accounts) > 1 else "single"
        except Exception:
            account_mode = "multi" if len(accounts) > 1 else "single"

        room_id = self._get_danmaku_room_id()
        if not room_id:
            messagebox.showwarning("提示", "请先选择直播间（可在账户管理页面添加）")
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
                self.running = False
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
            # P1-8: 空列表保护，防止运行中弹幕被清空导致崩溃
            if not self.danmaku_list:
                self.log("⚠ 弹幕列表为空，等待10秒后重试...")
                time.sleep(10)
                continue
            if mode == "random":
                msg = random.choice(self.danmaku_list)
            else:
                msg = self.danmaku_list[index % len(self.danmaku_list)]
                index += 1

            success = False
            result = ""  # P1-7: 初始化result，防止循环提前break时NameError
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
                    # P1-T: 区分瞬时错误和永久错误，永久错误不重试
                    permanent_errors = ["-101", "账号未登录", "cookie", "房间不存在", "内容违规", "禁言", "黑名单"]
                    is_permanent = any(err in result for err in permanent_errors)
                    if is_permanent:
                        self.log(f"  ✗ 永久错误({account['name']}): {result}，不重试")
                        break
                    if retry < 2:
                        self.log(f"  重试{retry+1} ({account['name']}): {result}")
                        time.sleep(random.uniform(2, 4))

            if not success:
                fail_count += 1
                self.log(f"✗ 失败({fail_count}) [{account['name']}]: {msg} - {result}")
                if fail_count >= 5:
                    self.log("连续失败5次，自动停止")
                    self.running = False
                    self.root.after(0, self.stop_sending)
                    break

            wait_time = random.uniform(interval_min, interval_max)
            waited = 0
            while waited < wait_time and self.running:
                time.sleep(0.5)
                waited += 0.5

        self.log(f"本次结束，共成功发送 {send_count} 条")




# 卡密验证核心函数已移至 card_verify.py（PyArmor加密保护）
# 从加密模块导入所有核心函数
from card_verify import (
    get_machine_code, verify_card_online, load_saved_card,
    is_card_expired, save_card_info, clear_saved_card,
    get_card_remaining_text, CARD_FILE, CARD_API_BASE, CARD_VERIFY_URL
)


class CardAuthFrame:
    """卡密验证界面（直接在主窗口显示，不用Toplevel）"""
    
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.result = False
        self.card_info = None
        self._verifying = False
        
        # 清空主窗口
        for widget in root.winfo_children():
            widget.destroy()
        
        # 设置窗口
        root.title("卡密验证 - B站工具箱")
        root.geometry("480x380")
        root.resizable(True, True)
        root.minsize(420, 340)
        root.configure(bg=COLORS["bg_dark"])
        
        # 居中
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 480) // 2
        y = (root.winfo_screenheight() - 380) // 2
        root.geometry(f"480x380+{x}+{y}")
        
        self._build_ui()
        
        # 检查是否有保存的卡密
        saved = load_saved_card()
        if saved and saved.get("card_code"):
            # 先检查本地是否过期
            if is_card_expired(saved):
                # 已过期，删除保存的卡密，显示验证界面
                try:
                    CARD_FILE.unlink()
                except Exception:
                    pass
                self.status_label.config(text="⚠ 卡密已过期，请重新输入", fg=COLORS["warning"])
            else:
                # 未过期，先在线验证卡密状态（检查是否被封禁）
                self.status_label.config(text="⏳ 正在验证卡密状态...", fg=COLORS["text_secondary"])
                self._verify_saved_card(saved)
                return
    
    def _build_ui(self):
        """构建UI"""
        # 标题
        title_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        title_frame.pack(fill=tk.X, pady=(30, 10))
        
        tk.Label(title_frame, text="🔐 卡密验证", 
                bg=COLORS["bg_dark"], fg=COLORS["accent"],
                font=("微软雅黑", 18, "bold")).pack()
        
        tk.Label(title_frame, text="请输入您的卡密以激活软件", 
                bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
                font=("微软雅黑", 10)).pack(pady=(5, 0))
        
        # 卡密输入
        input_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        input_frame.pack(fill=tk.X, padx=40, pady=(20, 10))
        
        tk.Label(input_frame, text="卡密:", 
                bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                font=("微软雅黑", 11)).pack(anchor=tk.W)
        
        self.card_entry = tk.Entry(input_frame, 
                                   bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                   insertbackground=COLORS["accent"],
                                   font=("微软雅黑", 12),
                                   relief=tk.FLAT, justify=tk.CENTER)
        self.card_entry.pack(fill=tk.X, pady=(5, 0), ipady=8)
        self.card_entry.bind('<Return>', lambda e: self._verify())
        
        # 状态标签
        self.status_label = tk.Label(self.root, text="", 
                                    bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                                    font=("微软雅黑", 9))
        self.status_label.pack(pady=(5, 0))
        
        # 按钮
        btn_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=40, pady=(20, 0))
        
        self.verify_btn = DarkButton(btn_frame, text="验证激活",
                              width=160, height=44,
                              bg_color=COLORS["accent"], text_color="#000000",
                              command=self._verify)
        self.verify_btn.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        
        cancel_btn = DarkButton(btn_frame, text="退出",
                             width=160, height=44,
                             bg_color=COLORS["danger"], text_color="#ffffff",
                             command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=0)
        
        # 机器码显示
        machine_code = get_machine_code()
        tk.Label(self.root, text=f"设备码: {machine_code[:8]}...{machine_code[-8:]}", 
                bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                font=("微软雅黑", 8)).pack(side=tk.BOTTOM, pady=(0, 15))
    
    def _verify(self):
        """验证卡密（后台线程）"""
        card_code = self.card_entry.get().strip().upper()
        if not card_code:
            self.status_label.config(text="⚠ 请输入卡密", fg=COLORS["warning"])
            return
        
        if self._verifying:
            return
        
        self._verifying = True
        self.verify_btn.config(state=tk.DISABLED, text="验证中...")
        self.status_label.config(text="⏳ 正在验证...", fg=COLORS["text_secondary"])
        
        def verify_thread():
            try:
                machine_code = get_machine_code()
                success, result = verify_card_online(card_code, machine_code)
            except Exception as e:
                success = False
                result = {"code": -99, "msg": f"验证异常: {str(e)}"}
            
            self.root.after(0, lambda: self._verify_result(card_code, success, result))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def _verify_result(self, card_code, success, result):
        """验证结果回调"""
        self._verifying = False
        self.verify_btn.config(state=tk.NORMAL, text="验证激活")
        
        if success:
            self.status_label.config(text=f"✓ {result.get('msg', '验证成功')}", fg=COLORS["success"])
            self.result = True
            self.card_info = result
            save_card_info(card_code, result)
            self.root.after(1000, lambda: self.on_success(self.card_info))
        else:
            code = result.get("code", -99)
            msg = result.get("msg", "验证失败")
            self.status_label.config(text=f"✗ {msg}", fg=COLORS["danger"])
            
            # 网络错误时尝试离线验证
            if code == -99:
                saved = load_saved_card()
                if saved and saved.get("card_code") == card_code:
                    try:
                        last_verify = datetime.strptime(saved.get("last_verify", ""), "%Y-%m-%dT%H:%M:%S")
                        days_diff = (datetime.now() - last_verify).days
                        if days_diff <= 1:
                            self.status_label.config(text=f"⚠ 网络错误，离线验证（剩余{1-days_diff}天）", fg=COLORS["warning"])
                            self.result = True
                            self.card_info = saved
                            # 更新本地缓存的last_verify时间，使离线宽限持续有效
                            save_card_info(card_code, saved)
                            self.root.after(1500, lambda: self.on_success(self.card_info))
                            return
                    except Exception:
                        pass
                    # 有保存的卡密但离线验证失败（超过1天或解析异常），清除缓存并提示
                    self.status_label.config(text="⚠ 网络错误且离线验证已过期，请重新输入", fg=COLORS["danger"])
                    clear_saved_card()
                else:
                    # 没有保存的卡密或卡密不匹配，只提示网络错误，不清除缓存
                    self.status_label.config(text="⚠ 网络错误，请检查网络后重试", fg=COLORS["warning"])
    
    def _verify_saved_card(self, saved):
        """在线验证保存的卡密状态（检查是否被封禁）"""
        card_code = saved.get("card_code")
        
        def verify_thread():
            try:
                machine_code = get_machine_code()
                success, result = verify_card_online(card_code, machine_code)
            except Exception as e:
                success = False
                result = {"code": -99, "msg": f"验证异常: {str(e)}"}
            
            self.root.after(0, lambda: self._verify_saved_card_result(saved, success, result))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def _verify_saved_card_result(self, saved, success, result):
        """保存卡密的在线验证结果"""
        card_code = saved.get("card_code")
        
        if success:
            # 在线验证通过，更新本地缓存并登录
            self.status_label.config(text="✓ 卡密有效，正在进入...", fg=COLORS["success"])
            self.result = True
            self.card_info = result
            save_card_info(card_code, result)
            self.root.after(1000, lambda: self.on_success(self.card_info))
        else:
            code = result.get("code", -99)
            msg = result.get("msg", "验证失败")
            
            if code == -99:
                # 网络错误，尝试离线登录（1天宽限期）
                try:
                    last_verify = datetime.strptime(saved.get("last_verify", ""), "%Y-%m-%dT%H:%M:%S")
                    days_diff = (datetime.now() - last_verify).days
                    if days_diff <= 1:
                        self.status_label.config(text=f"⚠ 网络错误，离线验证（剩余{1-days_diff}天）", fg=COLORS["warning"])
                        self.result = True
                        self.card_info = saved
                        # 更新本地缓存的last_verify时间，使离线宽限持续有效
                        save_card_info(card_code, saved)
                        self.root.after(1500, lambda: self.on_success(self.card_info))
                        return
                except Exception:
                    pass
                
                # 超过1天或解析失败，清除本地缓存，要求重新输入
                self.status_label.config(text="⚠ 网络错误且离线验证已过期，请重新输入", fg=COLORS["danger"])
                clear_saved_card()
            else:
                # 卡密被封禁/过期/绑定其他设备，清除本地缓存，要求重新输入
                self.status_label.config(text=f"✗ {msg}，请重新输入", fg=COLORS["danger"])
                clear_saved_card()
    
    def _cancel(self):
        """取消"""
        self.result = False
        self.root.destroy()


def show_card_auth(root):
    """显示卡密验证界面，阻塞直到验证通过或退出"""
    result = {"success": False, "card_info": None}
    
    def on_success(card_info):
        result["success"] = True
        result["card_info"] = card_info
        root.quit()
    
    frame = CardAuthFrame(root, on_success)
    
    # 进入事件循环，直到验证通过或窗口关闭
    root.mainloop()
    
    return result["success"], result["card_info"]


def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    
    # 卡密验证（直接在主窗口显示，验证通过后on_success会调用root.quit()）
    auth_success, card_info = show_card_auth(root)
    
    if not auth_success:
        try:
            root.destroy()
        except Exception:
            pass
        return
    
    # 验证通过，重新创建主窗口进入主程序
    try:
        root.destroy()
    except Exception:
        pass
    
    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


























