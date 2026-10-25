# -*- coding: utf-8 -*-
"""抢码工具页面：旧版监控 + 新版精准抢码（并存，需互斥）。"""

import json, os, random, threading, time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

import requests

from config import (COLORS, BASE_DIR, APP_VERSION, LOG_DIR,
                    HEADERS, MIXIN_KEY_ENC_TAB, _GLOBAL_LOCK)
from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID, get_manual_task
from storage import atomic_write_json, safe_load_json
from bili_api import (check_all_tasks_finished, cookies_from_account, get_mission_info,
                      parse_stock_info, receive_reward, verify_login)
from widgets import DarkButton, DarkEntry, ToolTip
import rush_stats
from .new_mode import NewModeMixin
from .scheduled import ScheduledMixin
from .manual_task import ManualTaskMixin, task_label, available_versions


# ========== 组内任务列表列宽（表头与数据行共用，保证严格对齐）==========
# 单位：像素。之前用 tk.Label(width=字符数) 会因表头是粗体、数据行是常规体
# 导致同 width 的实际像素宽度不同，逐列累积错位，最终操作列偏了 45px。
NM_TASK_COLUMNS = [
    ("状态", 74),
    ("优先级", 74),
    ("任务名称", 326),
    ("奖励", 158),
    ("窗口期", 74),
    ("账户", 142),
    ("操作(↑↓✎🔍×)", 184),
]
NM_TASK_CELL_PAD = 8   # 留白已包含在列宽中，不再用 grid padx（会撑宽列）


class RushRewardFrame(NewModeMixin, ScheduledMixin, ManualTaskMixin, tk.Frame):
    """抢码页面。逻辑分布在：
      - 本文件：初始化、UI 构建、旧版监控、查询/领取、关机
      - new_mode.py：精准抢码（39 个方法）
      - scheduled.py：旧版定时任务（12 个方法）
    """

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

        # 初始化日志文件（P1-13: 常开句柄+锁）
        self.log_file = None
        self._log_file_handle = None
        self._log_lock = threading.Lock()
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
        # P1-13: 关闭日志文件句柄
        if self._log_file_handle:
            try:
                self._log_file_handle.close()
            except Exception:
                pass
            self._log_file_handle = None

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
            # 1. 设置版本（保存的版本已不存在时回退到第一个可用版本，避免空列表）
            _versions = available_versions()
            _saved_version = self.rush_config.get("version") or ""
            if _saved_version in _versions:
                self.version_var.set(_saved_version)
            elif _versions:
                self.version_var.set(_versions[0])

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
        _versions = sorted(set(t["version"] for t in ALL_TASKS), key=lambda v: [t["version"] for t in ALL_TASKS].index(v))
        self.version_combo = ttk.Combobox(row1, textvariable=self.version_var,
                                           values=_versions, state="readonly",
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

        # 手动添加任务（task_id / 活动网址）
        self.mt_add_btn = DarkButton(row1b, text="＋ 手动添加", command=self.mt_open_add_dialog,
                                     height=32, bg_color="#8e44ad", text_color="#ffffff")
        self.mt_add_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.on_version_change()  # 初始化期数、类型下拉框选项和任务列表
        self.mt_refresh_task_combos()  # 把手动任务版本并入版本下拉框

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

        # 统计卡片（O4：抢码结果结构化统计）
        stats_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1,
                              highlightbackground=COLORS["border"])
        stats_card.pack(fill=tk.X, pady=(8, 4))
        stats_head = tk.Frame(stats_card, bg=COLORS["bg_card"])
        stats_head.pack(fill=tk.X, padx=15, pady=(8, 2))
        tk.Label(stats_head, text="📊 抢码统计（今日）", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        DarkButton(stats_head, text="刷新", command=self.refresh_stats_panel,
                  height=26, width=70, bg_color=COLORS["bg_input"],
                  text_color=COLORS["text_primary"]).pack(side=tk.RIGHT)
        self.stats_label = tk.Label(stats_card, text="暂无数据（抢码后自动统计）",
                                    bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                                    font=("微软雅黑", 10), justify=tk.LEFT, anchor=tk.W,
                                    wraplength=1200)
        self.stats_label.pack(fill=tk.X, padx=15, pady=(0, 8))

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

    def refresh_stats_panel(self):
        """刷新抢码统计面板（O4）。"""
        try:
            s = rush_stats.summary(today_only=True)
            if not s or s.get("total", 0) == 0:
                self.stats_label.config(text="暂无数据（抢码后自动统计）",
                                        fg=COLORS["text_muted"])
                return
            parts = [
                f"总尝试 {s['total']}",
                f"成功 {s['success']}",
                f"已领 {s['already']}",
                f"失败 {s['failed']}",
                f"成功率 {s['success_rate']}%",
                f"平均延迟 {s['avg_latency_ms']}ms",
            ]
            line1 = " | ".join(parts)

            extra = []
            if s.get("top_codes"):
                codes = ", ".join(f"{c['code'] or '未知'}×{c['count']}"
                                  for c in s["top_codes"][:3])
                extra.append(f"失败码 Top3: {codes}")
            if s.get("by_task"):
                top_task = s["by_task"][0]
                extra.append(f"最活跃任务: {top_task['task'][:20]} ({top_task['total']}次)")
            if s.get("by_hour"):
                busy = max(s["by_hour"], key=lambda x: x["total"])
                extra.append(f"高峰时段: {busy['hour']}点 ({busy['total']}次)")

            text = line1 + "\n" + " | ".join(extra) if extra else line1
            color = COLORS["success"] if s["success_rate"] >= 50 else COLORS["warning"]
            self.stats_label.config(text=text, fg=color)
        except Exception as e:
            try:
                self.stats_label.config(text=f"统计读取失败: {e}", fg=COLORS["danger"])
            except Exception:
                pass

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

        # 用 DarkButton（自带 8px 圆角），替代原生 tk.Button 的直角外观
        self.nm_new_group_btn = DarkButton(grow1, text="+ 新建组", command=self.nm_new_group,
                                           height=32, bg_color=COLORS["accent"], text_color="#000000")
        self.nm_new_group_btn.pack(side=tk.LEFT, padx=5)
        self.nm_del_group_btn = DarkButton(grow1, text="删除当前组", command=self.nm_del_group,
                                           height=32, bg_color="#c0392b", text_color="#ffffff")
        self.nm_del_group_btn.pack(side=tk.LEFT, padx=5)

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
        _nm_versions = sorted(set(t["version"] for t in ALL_TASKS), key=lambda v: [t["version"] for t in ALL_TASKS].index(v))
        self.nm_version_combo = ttk.Combobox(row1, textvariable=self.nm_version_var,
                                             values=_nm_versions,
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
        self.nm_account_combo.pack(side=tk.LEFT, padx=(8, 8))

        # 手动添加任务（task_id / 活动网址）
        self.nm_mt_add_btn = DarkButton(row2, text="＋ 手动添加", command=self.mt_open_add_dialog,
                                        height=32, bg_color="#8e44ad", text_color="#ffffff")
        self.nm_mt_add_btn.pack(side=tk.LEFT, padx=(0, 15))

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

        self.nm_add_task_btn = DarkButton(row3, text="+ 添加到当前组", command=self.nm_add_task,
                                          height=36, width=180, bg_color=COLORS["accent"],
                                          text_color="#000000")
        self.nm_add_task_btn.pack(side=tk.RIGHT, padx=10)


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
        self.nm_query_all_btn = DarkButton(list_title_frame, text="🔍 批量查询状态",
                                           command=self.nm_query_all_tasks,
                                           height=28, width=150, bg_color="#f39c12",
                                           text_color="#ffffff")
        self.nm_query_all_btn.pack(side=tk.RIGHT)
        tk.Label(list_title_frame, text="●=可抢  ●=已领取  ●=不可抢  ●=未查询", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(side=tk.RIGHT, padx=10)

        # 表头（用 grid + 固定像素宽度，与数据行严格共用同一套列宽常量）
        list_header = tk.Frame(list_card, bg=COLORS["bg_input"])
        list_header.pack(fill=tk.X, padx=15)
        for col_idx, (text, px) in enumerate(NM_TASK_COLUMNS):
            # 注意：grid 的 padx 会额外撑大列宽，因此这里不加 padx，
            # 统一由 uniform 列宽常量决定位置，保证与数据行逐列对齐。
            list_header.grid_columnconfigure(col_idx, minsize=px, weight=0)
            tk.Label(list_header, text=text, bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                     font=("微软雅黑", 10, "bold"), anchor=tk.W,
                     ).grid(row=0, column=col_idx, sticky="w", pady=5)

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
            # 与表头共用同一套像素列宽，grid 布局保证严格对齐
            for col_idx, (_, px) in enumerate(NM_TASK_COLUMNS):
                row.grid_columnconfigure(col_idx, minsize=px, weight=0)

            status_lbl = tk.Label(row, text="●", bg=COLORS["bg_card"], fg=dot_color,
                                  font=("微软雅黑", 12, "bold"), anchor=tk.W)
            status_lbl.grid(row=0, column=0, sticky="w")
            # 给状态圆点添加tooltip
            try:
                ToolTip(status_lbl, status_text)
            except Exception:
                pass
            tk.Label(row, text=str(task.get("priority", i+1)), bg=COLORS["bg_card"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), anchor=tk.W
                     ).grid(row=0, column=1, sticky="w")
            tk.Label(row, text=task.get("name", "")[:26], bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 10), anchor=tk.W
                     ).grid(row=0, column=2, sticky="w")
            tk.Label(row, text=task.get("award", "")[:12], bg=COLORS["bg_card"],
                     fg=COLORS["success"], font=("微软雅黑", 10), anchor=tk.W
                     ).grid(row=0, column=3, sticky="w")
            tk.Label(row, text=f"{task.get('window_seconds', 15)}秒", bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), anchor=tk.W
                     ).grid(row=0, column=4, sticky="w")
            tk.Label(row, text=task.get("account_name", "")[:10], bg=COLORS["bg_card"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 10), anchor=tk.W
                     ).grid(row=0, column=5, sticky="w")
            # 操作按钮（放进第7列，与表头「操作」列严格对齐）
            btn_frame = tk.Frame(row, bg=COLORS["bg_card"])
            btn_frame.grid(row=0, column=6, sticky="w")
            # 紧凑模式：表格操作列需要小按钮，不能用默认 100px 最小宽度
            DarkButton(btn_frame, text="↑", command=lambda tid=task["task_id"]: self.nm_move_task(tid, -1),
                       height=24, width=30, bg_color=COLORS["bg_input"],
                       text_color=COLORS["text_primary"], compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="↓", command=lambda tid=task["task_id"]: self.nm_move_task(tid, 1),
                       height=24, width=30, bg_color=COLORS["bg_input"],
                       text_color=COLORS["text_primary"], compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="✎", command=lambda t=task: self.nm_edit_task(t),
                       height=24, width=30, bg_color="#3498db",
                       text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="🔍", command=lambda t=task: self.nm_query_single_task(t),
                       height=24, width=34, bg_color="#f39c12",
                       text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="×", command=lambda tid=task["task_id"]: self.nm_remove_task(tid),
                       height=24, width=30, bg_color="#c0392b",
                       text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=1)

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
        task_names = [task_label(t, "paren") for t in filtered]
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
        """初始化日志文件（P1-13: 常开句柄+锁，避免每次log都open/close）"""
        try:
            LOG_DIR.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.log_file = LOG_DIR / f"抢码日志_{timestamp}.txt"
            # P1-13: 打开文件句柄，保持常开，避免高频open/close
            self._log_file_handle = open(self.log_file, "w", encoding="utf-8")
            self._log_file_handle.write(f"===== B站抢码工具日志 =====\n")
            self._log_file_handle.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._log_file_handle.write(f"日志文件: {self.log_file}\n")
            self._log_file_handle.write(f"============================\n\n")
            self._log_file_handle.flush()
        except Exception as e:
            print(f"初始化日志文件失败: {e}")
            self.log_file = None
            self._log_file_handle = None

    def log(self, msg):
        """线程安全的日志输出（P1-13: 常开句柄+锁，避免高频open/close阻塞主线程）"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        # P1-13: 用锁保护写入，使用常开句柄，避免每次open/close
        if self._log_file_handle:
            try:
                with self._log_lock:
                    self._log_file_handle.write(line)
                    self._log_file_handle.flush()
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
        _t0 = time.time()
        status, result, data = receive_reward(task["task_id"], info, cookies, csrf)
        _latency_ms = (time.time() - _t0) * 1000

        # O4: 结构化记录
        try:
            _code = ""
            _msg = str(result or "")
            if _msg.startswith("[") and "]" in _msg:
                _code = _msg[1:_msg.index("]")]
            rush_stats.record(
                task_id=task.get("task_id", ""),
                task_name=task.get("name", ""),
                account=account.get("name", ""),
                act_id=(info or {}).get("act_id", ""),
                result=status,
                code=_code,
                message=_msg,
                latency_ms=_latency_ms,
            )
        except Exception:
            pass

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

    def build_task_info_from_task(self, task):
        """从任务列表数据构造task_info，根据版本设置正确的活动名称和act_id"""
        version = task.get("version", "")
        if version == "原神7.1":
            act_name = "原神7.1版本UP主激励计划"
        elif "原神" in version:
            act_name = "原神7.0版本创作激励计划"
        elif "崩坏" in version or "星穹" in version:
            act_name = "崩坏星穹铁道4.5版本创作激励计划"
        elif "绝区零" in version:
            act_name = "绝区零3.3版本创作激励计划"
        else:
            act_name = "鸣潮3.7版本创作激励计划"
        # 手动任务（即使被归入 鸣潮3.7 这类官方版本）优先用任务自带的 act_id/act_name，
        # 因为它的 act_id 来自接口实查，比版本默认值更准确。
        _is_manual = get_manual_task(task.get("task_id", "")) is not None
        if _is_manual:
            act_id = task.get("act_id") or VERSION_DEFAULT_ACT_ID.get(version, "")
        else:
            act_id = VERSION_DEFAULT_ACT_ID.get(version) or task.get("act_id", "")
        act_name = task.get("act_name") or act_name
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
        _t0 = time.time()
        status, result, data = receive_reward(task["task_id"], task_info, cookies, csrf, session)
        _latency_ms = (time.time() - _t0) * 1000

        # O4: 结构化记录每次领取结果，供后续统计成功率/失败码分布
        try:
            _code = ""
            _msg = str(result or "")
            if _msg.startswith("[") and "]" in _msg:
                _code = _msg[1:_msg.index("]")]
            rush_stats.record(
                task_id=task.get("task_id", ""),
                task_name=task.get("name", ""),
                account=account.get("name", ""),
                act_id=(task_info or {}).get("act_id", ""),
                result=status,
                code=_code,
                message=_msg,
                latency_ms=_latency_ms,
            )
        except Exception:
            pass

        if status in ("success", "already"):
            return True, result
        return False, result

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
