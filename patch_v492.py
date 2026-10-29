#!/usr/bin/env python3
"""v4.9.2: 送礼次数0=0次(非无限)，无电池账户禁用"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. UI标签：去掉"0=无限"
# ============================================================
old_label = '''        tk.Label(gift_row2, text="送礼次数(0=无限):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

new_label = '''        tk.Label(gift_row2, text="送礼次数:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)'''

if old_label in content:
    content = content.replace(old_label, new_label)
    print("1. UI标签已去掉'0=无限'")
else:
    print("1. 未找到UI标签")

# ============================================================
# 2. start_gift：检查次数为0时提示，检查电池余额
# ============================================================
old_start_check = '''        gift_num = self.gift_num_var.get()
        interval = self.gift_interval_var.get()
        max_count = self.gift_count_var.get()
        self.save_gift_config()
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{'无限' if max_count == 0 else max_count}")
        self.log(f"  共 {len(selected_accounts)} 个账户参与送礼")'''

new_start_check = '''        gift_num = self.gift_num_var.get()
        interval = self.gift_interval_var.get()
        max_count = self.gift_count_var.get()
        # 检查次数
        if max_count <= 0:
            self.log("✗ 送礼次数必须大于0，请先设置送礼次数")
            return
        self.save_gift_config()
        # 检查每个账户的电池余额
        valid_accounts = []
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            battery = self.get_battery_balance(acc)
            if battery is not None and battery <= 0:
                self.log(f"  ⚠ [{name}] 电池余额为0，跳过该账户")
                continue
            if battery is not None:
                self.log(f"  [{name}] 电池余额: {battery}")
            valid_accounts.append(acc)
        if not valid_accounts:
            self.log("✗ 没有可用的账户（所有选中账户电池余额均为0）")
            return
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{max_count}")
        self.log(f"  共 {len(valid_accounts)} 个账户参与送礼")
        selected_accounts = valid_accounts'''

if old_start_check in content:
    content = content.replace(old_start_check, new_start_check)
    print("2. start_gift已添加次数检查和电池余额检查")
else:
    print("2. 未找到start_gift检查点")

# ============================================================
# 3. _gift_worker：移除无限逻辑
# ============================================================
old_worker_loop = '''        while not self.gift_stop.get(name, True) and self.gift_running:
                if max_count > 0 and count >= max_count:
                    self.log(f"  [{name}] ✓ 已达到最大送礼次数 ({max_count}次)")
                    break'''

new_worker_loop = '''        while not self.gift_stop.get(name, True) and self.gift_running:
                if count >= max_count:
                    self.log(f"  [{name}] ✓ 已达到最大送礼次数 ({max_count}次)")
                    break'''

if old_worker_loop in content:
    content = content.replace(old_worker_loop, new_worker_loop)
    print("3. _gift_worker已移除无限逻辑")
else:
    print("3. 未找到_gift_worker循环")

# ============================================================
# 4. 添加查询电池余额的方法（在get_user_room_id之后）
# ============================================================
old_get_room_end = '''    def get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                room_id = data.get("data", {}).get("roomid", 0)
                if room_id:
                    return str(room_id)
            return None
        except Exception:
            return None'''

new_get_room_end = '''    def get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                room_id = data.get("data", {}).get("roomid", 0)
                if room_id:
                    return str(room_id)
            return None
        except Exception:
            return None

    def get_battery_balance(self, account):
        """查询账户电池余额"""
        try:
            sessdata = account.get("sessdata", "")
            cookies = {"SESSDATA": sessdata}
            url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
            resp = requests.get(url, cookies=cookies, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                wallet = data.get("data", {})
                # 电池余额字段可能是bp或battery
                battery = wallet.get("bp", wallet.get("battery", 0))
                return battery
            return None
        except Exception:
            return None'''

if old_get_room_end in content:
    content = content.replace(old_get_room_end, new_get_room_end)
    print("4. 已添加get_battery_balance方法")
else:
    print("4. 未找到get_user_room_id结尾")

# ============================================================
# 5. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.9.1"', 'APP_VERSION = "v4.9.2"')
print("5. 版本号: v4.9.1 -> v4.9.2")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
