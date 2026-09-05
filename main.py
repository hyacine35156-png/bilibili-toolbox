#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站直播间自动发弹幕工具 - 模板版本
功能：读取配置，循环向指定直播间发送弹幕
使用前请先配置 config.json 中的 cookie 和 room_id
"""

import json
import time
import random
import logging
import sys
from pathlib import Path

import requests

# ========== 常量配置 ==========
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
DANMAKU_PATH = BASE_DIR / "danmaku_list.txt"

SEND_API = "https://api.live.bilibili.com/msg/send"
USER_INFO_API = "https://api.bilibili.com/x/web-interface/nav"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "danmaku_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ========== 配置加载 ==========
def load_config() -> dict:
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        logger.error(f"配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 校验必填项
    cookie = config.get("cookie", {})
    if not cookie.get("SESSDATA") or not cookie.get("bili_jct"):
        logger.error("请在 config.json 中填写 SESSDATA 和 bili_jct")
        sys.exit(1)

    if not config.get("room_id"):
        logger.error("请在 config.json 中填写 room_id（直播间号）")
        sys.exit(1)

    return config


def load_danmaku_list() -> list:
    """加载弹幕内容列表"""
    if not DANMAKU_PATH.exists():
        logger.error(f"弹幕列表文件不存在: {DANMAKU_PATH}")
        sys.exit(1)

    with open(DANMAKU_PATH, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        logger.error("弹幕列表为空，请在 danmaku_list.txt 中添加弹幕内容")
        sys.exit(1)

    logger.info(f"已加载 {len(lines)} 条弹幕")
    return lines


# ========== B站API交互 ==========
def build_cookie_string(cookie: dict) -> str:
    """构造cookie字符串"""
    parts = []
    for key, value in cookie.items():
        if value:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


def verify_login(cookie_str: str) -> bool:
    """验证登录状态"""
    headers = {**HEADERS, "Cookie": cookie_str}
    try:
        resp = requests.get(USER_INFO_API, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            uname = data["data"].get("uname", "未知用户")
            logger.info(f"登录验证成功，当前用户: {uname}")
            return True
        else:
            logger.error(f"登录验证失败: {data.get('message', '未知错误')}")
            return False
    except Exception as e:
        logger.error(f"登录验证请求异常: {e}")
        return False


def send_danmaku(cookie_str: str, csrf: str, room_id: int, msg: str) -> bool:
    """
    发送一条弹幕
    :param cookie_str: cookie字符串
    :param csrf: bili_jct 的值（csrf token）
    :param room_id: 直播间房间号
    :param msg: 弹幕内容
    :return: 是否发送成功
    """
    headers = {**HEADERS, "Cookie": cookie_str}
    payload = {
        "csrf": csrf,
        "roomid": room_id,
        "msg": msg,
        "rnd": int(time.time()),
        "color": 16777215,  # 白色
        "fontsize": 25,
        "mode": 1,  # 滚动弹幕
        "bubble": 0,
    }

    try:
        resp = requests.post(SEND_API, data=payload, headers=headers, timeout=10)
        data = resp.json()

        if data.get("code") == 0:
            logger.info(f"弹幕发送成功: {msg}")
            return True
        else:
            logger.warning(f"弹幕发送失败 [{data.get('code')}]: {data.get('message', '未知错误')} - 内容: {msg}")
            return False

    except Exception as e:
        logger.error(f"发送请求异常: {e}")
        return False


# ========== 主循环 ==========
def run_bot():
    """主运行循环"""
    logger.info("=" * 50)
    logger.info("B站自动发弹幕工具启动")
    logger.info("=" * 50)

    # 加载配置
    config = load_config()
    danmaku_list = load_danmaku_list()

    cookie = config["cookie"]
    cookie_str = build_cookie_string(cookie)
    csrf = cookie["bili_jct"]
    room_id = config["room_id"]
    interval_min = config.get("send_interval_min", 5)
    interval_max = config.get("send_interval_max", 10)
    send_mode = config.get("send_mode", "random")
    max_retry = config.get("max_retry", 3)

    logger.info(f"目标直播间: {room_id}")
    logger.info(f"发送模式: {send_mode}")
    logger.info(f"发送间隔: {interval_min}-{interval_max} 秒")

    # 验证登录
    if not verify_login(cookie_str):
        logger.error("登录验证未通过，请检查 cookie 是否正确或已过期")
        sys.exit(1)

    # 发送循环
    send_count = 0
    fail_count = 0
    index = 0

    logger.info("开始发送弹幕，按 Ctrl+C 停止")
    logger.info("-" * 50)

    try:
        while True:
            # 选取弹幕内容
            if send_mode == "random":
                msg = random.choice(danmaku_list)
            else:  # 顺序模式
                msg = danmaku_list[index % len(danmaku_list)]
                index += 1

            # 发送弹幕（带重试）
            success = False
            for retry in range(max_retry):
                if send_danmaku(cookie_str, csrf, room_id, msg):
                    success = True
                    send_count += 1
                    fail_count = 0
                    break
                else:
                    if retry < max_retry - 1:
                        wait = random.uniform(2, 5)
                        logger.info(f"第 {retry + 1} 次重试，等待 {wait:.1f} 秒...")
                        time.sleep(wait)

            if not success:
                fail_count += 1
                logger.warning(f"连续失败 {fail_count} 次")
                if fail_count >= 5:
                    logger.error("连续失败5次，程序停止，请检查账号状态或网络")
                    break

            # 随机间隔等待
            wait_time = random.uniform(interval_min, interval_max)
            logger.info(f"下一条弹幕将在 {wait_time:.1f} 秒后发送 (已发送 {send_count} 条)")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        logger.info("-" * 50)
        logger.info(f"用户手动停止，本次共发送 {send_count} 条弹幕")
        logger.info("程序退出")
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)


if __name__ == "__main__":
    run_bot()
