#!/usr/bin/env python3
"""v5.0.1: 修复送礼功能 - 礼物名(牛哇)、uid字段(DedeUserID)、默认gift_id、headers"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. get_gift_id: 搜索"牛哇"、加headers、默认id=31225
# ============================================================
old_get_gift = '''    def get_gift_id(self, account):
        """查询牛蛙牛蛙的gift_id"""
        if self.gift_id_cache:
            return self.gift_id_cache
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            # 获取礼物列表
            url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc"
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                gift_list = data.get("data", {}).get("list", [])
                for gift in gift_list:
                    if "牛蛙" in gift.get("name", "") or "牛哇" in gift.get("name", ""):
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {gift['name']} (id={gift['id']}, 价格={gift.get('price', 0)})")
                        return gift["id"]
            self.log("  ⚠ 未找到牛蛙牛蛙礼物，使用默认id=30029")
            self.gift_id_cache = 30029
            return 30029
        except Exception as e:
            self.log(f"  ⚠ 查询礼物ID失败: {e}，使用默认id=30029")
            self.gift_id_cache = 30029
            return 30029'''

new_get_gift = '''    def get_gift_id(self, account):
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

if old_get_gift in content:
    content = content.replace(old_get_gift, new_get_gift)
    print("1. get_gift_id已修复（牛哇、headers、默认id=31225）")
else:
    print("1. 未找到get_gift_id")

# ============================================================
# 2. get_room_info: 加headers
# ============================================================
old_get_room = '''    def get_room_info(self, room_id, account):
        """获取直播间信息（ruid等）"""
        try:
            sessdata = account.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
            return {}
        except Exception:
            return {}'''

new_get_room = '''    def get_room_info(self, room_id, account):
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
            return {}'''

if old_get_room in content:
    content = content.replace(old_get_room, new_get_room)
    print("2. get_room_info已加headers")
else:
    print("2. 未找到get_room_info")

# ============================================================
# 3. send_gift: uid从DedeUserID获取
# ============================================================
old_send_uid = '''            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}'''

new_send_uid = '''            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "") or account.get("DedeUserID", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}'''

if old_send_uid in content:
    content = content.replace(old_send_uid, new_send_uid)
    print("3. send_gift uid已修复（DedeUserID）")
else:
    print("3. 未找到send_gift uid")

# ============================================================
# 4. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v5.0.0"', 'APP_VERSION = "v5.0.1"')
print("4. 版本号: v5.0.0 -> v5.0.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
