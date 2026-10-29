#!/usr/bin/env python3
"""v4.9.0 part2: 添加送礼配置方法和送礼API核心逻辑"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在apply_watch_config之后添加送礼配置方法
# ============================================================
old_bind = '''    def bind_auto_save(self):
        try:
            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())'''

new_bind = '''    def load_gift_config(self):
        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,
            "selected_accounts": []
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
            self.gift_config["room_id"] = self.gift_room_entry.get().strip()
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.gift_config["selected_accounts"] = selected
            config_file = BASE_DIR / "gift_config.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.gift_config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self.gift_room_entry.delete(0, tk.END)
            self.gift_room_entry.insert(0, cfg.get("room_id", ""))
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            selected = cfg.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected)
        except Exception:
            pass

    def bind_auto_save(self):
        try:
            self.room_combo.bind("<KeyRelease>", lambda e: self.save_watch_config())'''

if old_bind in content:
    content = content.replace(old_bind, new_bind)
    print("1. 已添加送礼配置方法（load/save/apply）")
else:
    print("1. 未找到bind_auto_save插入点")

# ============================================================
# 2. 在类的末尾添加送礼API和多线程逻辑
# ============================================================
# 找到WatchLiveFrame类的最后一个方法，在其后添加送礼方法
# 先搜索_on_watch_finished方法结尾
old_watch_finished_end = '''        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        self.interval_combo.config(state="readonly")'''

new_watch_finished_end = '''        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        self.interval_combo.config(state="readonly")

    # ========== 送礼功能 ==========
    def get_gift_id(self, account):
        """查询牛蛙牛蛙的gift_id"""
        if self.gift_id_cache:
            return self.gift_id_cache
        try:
            sessdata = account.get("sessdata", "")
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
            return 30029

    def get_room_info(self, room_id, account):
        """获取直播间信息（ruid等）"""
        try:
            sessdata = account.get("sessdata", "")
            cookies = {"SESSDATA": sessdata}
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
            return {}
        except Exception:
            return {}

    def send_gift(self, account, room_id, gift_id, gift_num):
        """发送礼物"""
        try:
            sessdata = account.get("sessdata", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "")
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
            return False, f"网络异常: {e}"

    def start_gift(self):
        """开始送礼"""
        room_id = self.gift_room_entry.get().strip()
        if not room_id:
            self.log("✗ 请先输入送礼直播间号")
            return
        if not room_id.isdigit():
            self.log("✗ 直播间号必须是数字")
            return
        selected_accounts = [acc for acc in self.account_mgr.accounts if self.account_vars.get(acc.get("name", ""), tk.BooleanVar()).get()]
        if not selected_accounts:
            self.log("✗ 请先选择送礼账户")
            return
        gift_num = self.gift_num_var.get()
        interval = self.gift_interval_var.get()
        max_count = self.gift_count_var.get()
        self.save_gift_config()
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{'无限' if max_count == 0 else max_count}")
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
                if max_count > 0 and count >= max_count:
                    self.log(f"  [{name}] ✓ 已达到最大送礼次数 ({max_count}次)")
                    break
                success, msg = self.send_gift(account, room_id, gift_id, gift_num)
                count += 1
                if success:
                    self.log(f"  [{name}] 第{count}次: ✓ {msg} (牛蛙牛蛙x{gift_num})")
                else:
                    self.log(f"  [{name}] 第{count}次: ✗ {msg}")
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
        self.gift_stop_btn.config(state=tk.DISABLED)'''

if old_watch_finished_end in content:
    content = content.replace(old_watch_finished_end, new_watch_finished_end)
    print("2. 已添加送礼API和多线程逻辑")
else:
    print("2. 未找到类末尾插入点")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
