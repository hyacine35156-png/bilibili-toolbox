#!/usr/bin/env python3
"""v5.0.2: 修复送礼 - 正确gift_id(31039)、coin_type、电池检查、错误码说明"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. get_gift_id: 优先选bag_gift=0的，默认id=31039
# ============================================================
old_get_gift = '''    def get_gift_id(self, account):
        """查询牛哇牛哇的gift_id"""
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
                for gift in gift_list:
                    name = gift.get("name", "")
                    if "牛哇" in name or "牛蛙" in name:
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {name} (id={gift['id']}, 价格={gift.get('price', 0)})")
                        return gift["id"]
            self.log("  ⚠ 未找到牛哇牛哇礼物，使用默认id=31225")
            self.gift_id_cache = 31225
            return 31225
        except Exception as e:
            self.log(f"  ⚠ 查询礼物ID失败: {e}，使用默认id=31225")
            self.gift_id_cache = 31225
            return 31225'''

new_get_gift = '''    def get_gift_id(self, account):
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
            return 31039'''

if old_get_gift in content:
    content = content.replace(old_get_gift, new_get_gift)
    print("1. get_gift_id已修复（优先bag_gift=0，默认31039）")
else:
    print("1. 未找到get_gift_id")

# ============================================================
# 2. send_gift: 加coin_type=gold，添加电池检查和错误码说明
# ============================================================
old_send = '''    def send_gift(self, account, room_id, gift_id, gift_num):
        """发送礼物"""
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "") or account.get("DedeUserID", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            # 获取直播间ruid
            room_info = self.get_room_info(room_id, account)
            ruid = room_info.get("uid", "")
            # 送礼接口
            url = "https://api.live.bilibili.com/gift/v2/live/bag_send"
            data = {
                "uid": uid,
                "gift_id": gift_id,
                "ruid": ruid,
                "gift_num": gift_num,
                "bag_id": 0,
                "platform": "pc",
                "biz_code": "live",
                "biz_id": room_id,
                "rnd": int(time.time()),
                "storm_beat_id": "0",
                "metadata": "",
                "price": "0",
                "csrf_token": bili_jct,
                "csrf": bili_jct,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://live.bilibili.com/{room_id}",
            }
            resp = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
            result = resp.json()
            code = result.get("code", -1)
            msg = result.get("message", "")
            if code == 0:
                return True, "送礼成功"
            else:
                return False, f"[{code}] {msg}"
        except Exception as e:
            return False, f"网络异常: {e}"'''

new_send = '''    def send_gift(self, account, room_id, gift_id, gift_num):
        """发送礼物（直接用电池购买送出）"""
        try:
            name = account.get("name", "未知")
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "") or account.get("DedeUserID", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            # 先检查电池余额
            battery = self.get_battery_balance(account)
            if battery is not None and battery <= 0:
                return False, "电池余额为0，无法送礼"
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
            return False, f"网络异常: {e}"'''

if old_send in content:
    content = content.replace(old_send, new_send)
    print("2. send_gift已修复（send接口、coin_type、电池检查、错误码说明）")
else:
    print("2. 未找到send_gift")

# ============================================================
# 3. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v5.0.1"', 'APP_VERSION = "v5.0.2"')
print("3. 版本号: v5.0.1 -> v5.0.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
