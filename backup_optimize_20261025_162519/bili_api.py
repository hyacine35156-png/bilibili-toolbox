# -*- coding: utf-8 -*-
"""B 站接口：登录校验、发弹幕、WBI 签名、任务查询、库存解析、领取。"""

import hashlib, json, re, struct, time
import urllib.parse
from datetime import datetime, timedelta

import requests

from config import (
    HEADERS, SEND_API, USER_INFO_API, MISSION_INFO_API, MISSION_RECEIVE_API, MISSION_MYLIST_API,
    MIXIN_KEY_ENC_TAB,
    _WBI_KEY_CACHE, _WBI_CACHE_TTL, _mission_info_cache, _MISSION_CACHE_TTL,
    _last_claim_data_global, _last_claim_result_global,
)
from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID


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

# ---------- WBI 签名 ----------

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

# ---------- 任务/库存 ----------

def get_mission_info(task_id, cookies_dict):
    """获取任务信息（库存、资格等）"""
    img_key, sub_key = get_wbi_keys(cookies_dict)
    if not img_key:
        return None, "获取WBI密钥失败"

    headers = {
        **HEADERS,
        "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task_id}",
        "Origin": "https://www.bilibili.com",  # P2-R: Origin与Referer域匹配
    }
    params = {
        "task_id": task_id,
        "web_location": "888.126558",
    }

    try:
        # P2-Q: wbi_sign移到try内，避免签名异常导致函数崩溃
        signed_params = wbi_sign(params, img_key, sub_key)
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
            # P2-S: 重试机制改为最多3次（首次+2次重试），超时/5xx也退避
            for retry in range(3):
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
                        # P2-S: 频率过高、超时、5xx都退避后重试
                        if "-702" in msg or "频率" in msg or "超时" in msg or "500" in msg or "502" in msg or "503" in msg:
                            if retry < 2:
                                time.sleep(1.0 * (retry + 1))
                                continue
                        break
                except Exception as e:
                    message = f"异常: {str(e)}"
                    if retry < 2:
                        time.sleep(0.5 * (retry + 1))
                        continue
                    break

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

def get_award_record(activity_id, cookies_dict, page=1, page_size=50):
    """获取领取记录（含兑换码）P2-U: 支持分页"""
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
        "page": page,
        "page_size": page_size,
    }

    try:
        # P2-Q: wbi_sign移到try内，避免签名异常导致函数崩溃
        signed_params = wbi_sign(params, img_key, sub_key)
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

    # 尝试6: 查找包含stock/remain/left/available的任意字段
    # P2-J: 排除明显非库存字段（价格、比率、百分比等）
    _stock_blacklist = ["price", "cost", "rate", "ratio", "percent", "discount", "value", "score", "level", "exp", "coin", "money", "amount"]
    for key, val in task_info.items():
        key_lower = key.lower()
        if any(kw in key_lower for kw in ["stock", "remain", "left", "available"]) and isinstance(val, (int, float)) and val > 0:
            # 排除黑名单字段
            if any(bl in key_lower for bl in _stock_blacklist):
                continue
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

# ---------- cookies ----------

def cookies_from_account(acc):
    """从账户数据生成cookies字典"""
    cookies = {
        "SESSDATA": acc["SESSDATA"],
        "bili_jct": acc["bili_jct"],
    }
    if acc.get("DedeUserID"):
        cookies["DedeUserID"] = acc["DedeUserID"]
    return cookies
