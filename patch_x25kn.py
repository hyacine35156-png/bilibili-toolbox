#!/usr/bin/env python3
"""v4.0.0补丁：集成X25Kn E/X观看心跳上报协议"""
import re

with open('main_gui_pro.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在__init__中添加X25Kn变量
old_init = '''        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.watch_config = self.load_watch_config()'''
new_init = '''        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.x25kn_threads = {}  # X25Kn观看心跳线程 {账户名: thread}
        self.x25kn_stop = {}  # X25Kn停止标志 {账户名: bool}
        self.x25kn_state = {}  # X25Kn协议状态 {账户名: dict}
        self.watch_config = self.load_watch_config()'''
content = content.replace(old_init, new_init)

# 2. 在get_room_info方法后添加X25Kn相关方法
old_room_info_end = '''        except Exception:
            return False

    def play_thread(self, account, room_id):'''
new_room_info_end = '''        except Exception:
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
                "id": json.dumps([parent_id, area_id, 0, room_id], separators=(",", ":")),
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
            return None
        except Exception:
            return None

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
                "room_id": room_id,
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
                "id": json.dumps([parent_id, area_id, seq, room_id], separators=(",", ":")),
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
            return None
        except Exception:
            return None

    def x25kn_thread_func(self, account, room_id, area_id, parent_id, up_id, name):
        """X25Kn观看心跳线程：E接口进入后，按心跳间隔循环X接口"""
        import uuid as uuid_lib
        buvid = self.x25kn_get_buvid(account)
        uuid_str = str(uuid_lib.uuid4())
        self.log(f"  [{name}] X25Kn获取LIVE_BUVID: {buvid[:20]}...")

        # E接口
        e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
        if not e_data:
            self.log(f"  [{name}] ✗ X25Kn E接口失败，观看心跳未启动")
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
            if result:
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
                self.log(f"  [{name}] X25Kn心跳失败（连续{consecutive_fail}次），重新E接口...")
                if consecutive_fail >= 3:
                    # 重新E接口
                    e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
                    if e_data:
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

    def play_thread(self, account, room_id):'''
content = content.replace(old_room_info_end, new_room_info_end)

# 3. 在_watch_loop中，每个账户进入直播间后启动X25Kn线程
old_watch_play = '''        # 启动持续播放线程（模拟真实浏览器播放）
        self.log("启动持续播放线程...")
        self.start_play_threads(selected_accounts, room_ids)'''
new_watch_play = '''        # 启动X25Kn观看心跳上报线程（v4.0.0核心功能：让B站统计系统认为在"观看"）
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
        self.start_play_threads(selected_accounts, room_ids)'''
content = content.replace(old_watch_play, new_watch_play)

# 4. 在stop_watch中停止X25Kn线程
old_stop = '''    def stop_watch(self):
        self.stop_flag["stop"] = True
        self.log("正在停止看播任务...")'''
new_stop = '''    def stop_watch(self):
        self.stop_flag["stop"] = True
        # 停止所有X25Kn心跳线程
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.log("正在停止看播任务（含X25Kn心跳）...")'''
content = content.replace(old_stop, new_stop)

# 5. 在_on_watch_finished中清理X25Kn
old_finish = '''    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        self.close_all_ws()'''
new_finish = '''    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        self.close_all_ws()'''
content = content.replace(old_finish, new_finish)

# 6. 更新窗口标题
old_title = '''self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务(WebSocket在线)")'''
new_title = '''self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务(X25Kn观看心跳)")'''
content = content.replace(old_title, new_title)

with open('main_gui_pro.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("v4.0.0补丁应用完成！")
print("新增功能：X25Kn E/X观看心跳上报协议（纯Python HMAC签名，无需wasm）")
