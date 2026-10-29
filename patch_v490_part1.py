#!/usr/bin/env python3
"""v4.9.0: 新增送礼功能（牛蛙牛蛙），加入看播任务页"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在__init__中添加送礼相关变量
# ============================================================
old_init = '''        self.watch_config = self.load_watch_config()
        self.build_ui()'''

new_init = '''        self.watch_config = self.load_watch_config()
        # 送礼功能变量
        self.gift_running = False
        self.gift_threads = {}
        self.gift_stop = {}
        self.gift_config = self.load_gift_config()
        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.build_ui()'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("1. __init__中已添加送礼变量")
else:
    print("1. 未找到__init__插入点")

# ============================================================
# 2. 添加送礼配置加载和保存方法（在save_watch_config之后）
# ============================================================
old_save_end = '''        except Exception:
            pass

    def refresh_account_list(self):'''

new_save_end = '''        except Exception:
            pass

    def load_gift_config(self):
        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,  # 0=无限
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
            # 恢复选中账户
            selected = cfg.get("selected_accounts", [])
            for name, var in self.account_vars.items():
                var.set(name in selected)
        except Exception:
            pass

    def refresh_account_list(self):'''

if old_save_end in content:
    content = content.replace(old_save_end, new_save_end)
    print("2. 已添加送礼配置加载/保存/恢复方法")
else:
    print("2. 未找到配置方法插入点")

# ============================================================
# 3. 在build_ui中添加送礼UI区域（在看播设置卡片之后）
# ============================================================
old_status_card = '''        # 状态卡片
        status_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        status_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(status_card, text="观看状态", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))'''

new_status_card = '''        # 送礼设置卡片
        gift_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        gift_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(gift_card, text="送礼设置（牛蛙牛蛙）", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        gift_inner = tk.Frame(gift_card, bg=COLORS["bg_card"])
        gift_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        gift_row1 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=3)
        tk.Label(gift_row1, text="直播间号:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_entry = tk.Entry(gift_row1, width=20, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_room_entry.pack(side=tk.LEFT, padx=(8, 20))
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
        tk.Label(gift_row2, text="送礼次数(0=无限):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
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
        tk.Label(status_card, text="观看状态", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))'''

if old_status_card in content:
    content = content.replace(old_status_card, new_status_card)
    print("3. 已添加送礼UI区域")
else:
    print("3. 未找到UI插入点")

# ============================================================
# 4. 在__init__末尾调用apply_gift_config
# ============================================================
old_apply = '''        self.apply_watch_config()
        self.bind_auto_save()'''

new_apply = '''        self.apply_watch_config()
        self.apply_gift_config()
        self.bind_auto_save()'''

if old_apply in content:
    content = content.replace(old_apply, new_apply)
    print("4. 已添加apply_gift_config调用")
else:
    print("4. 未找到apply插入点")

# ============================================================
# 5. 版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.8.1"', 'APP_VERSION = "v4.9.0"')
print("5. 版本号: v4.8.1 -> v4.9.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
