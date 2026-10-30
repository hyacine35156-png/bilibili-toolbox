# -*- coding: utf-8 -*-
"""抢码工具页面：旧版监控 + 新版精准抢码（并存，需互斥）。"""

import json, random, threading, time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

from config import (COLORS, BASE_DIR, LOG_DIR,
                    HEADERS, MIXIN_KEY_ENC_TAB, _GLOBAL_LOCK)
from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID, get_manual_task
from storage import atomic_write_json
from bili_api import (check_all_tasks_finished, cookies_from_account, get_mission_info,
                      parse_stock_info, receive_reward, verify_login)
from widgets import (DarkButton, DarkEntry, ToolTip, RoundEntry,
                     RoundCombobox)
import rush_stats
import rush_presets
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

        # v6.7.4: 按「⚙ 设置 -> 全局设置」里的开关决定默认显示哪个模式。
        # 默认 old（旧模式在第一页）；开启后 new（新模式在第一页）。
        # 注意：新模式 UI 是延迟构建的（实测耗时 1.2~1.8 秒），
        #      所以用 after(250) 延后执行，先把主界面显示出来。
        try:
            import app_settings as _appset
            if _appset.rush_new_mode_first():
                try:
                    self.after(250, self._apply_default_rush_mode)
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_default_rush_mode(self):
        """按全局设置切换到默认抢码模式（v6.7.4 新增）。"""
        try:
            import app_settings as _appset
            if not _appset.rush_new_mode_first():
                return
            # 只有当用户还没手动切换过时才应用
            try:
                cur = self.new_mode_mode_var.get() if self.new_mode_mode_var else "old"
            except Exception:
                cur = "old"
            if cur == "new":
                return
            self.switch_rush_mode("new")
            try:
                self.log("⚙ 已按全局设置默认显示「✨ 新模式·精准抢码」")
            except Exception:
                pass
        except Exception as e:
            try:
                self.log("应用默认抢码模式失败: %s" % e)
            except Exception:
                pass

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
        tk.Label(header, text="◈ 自动抢码工具", bg=COLORS["bg_card"],
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
        # v6.2.0 性能优化：延迟构建。
        # build_new_mode_ui 实测耗时约 1.2-1.8 秒，主要开销是首次渲染 emoji
        # 时 Windows 加载 emoji 字体（单个含 emoji 的控件可达 900ms）。
        # 而程序默认显示旧模式，新模式往往整场都不用 —— 没必要在启动时付这个代价。
        # 改为首次切换到新模式时才构建，启动时间直接省下 1.2 秒以上。
        self.new_mode_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self._new_mode_ui_built = False

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
                                     height=32, bg_color="#8e44ad", text_color="#ffffff", tip="手动输入 task_id 或活动网址来添加任务（官方任务表里没有的活动也能加）")
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
        # v6.4.5: 快捷选中可抢任务（用户需求）
        # 读取持久化的查询结果，把「已完成且可抢」的任务一键加入当前任务组。
        # v6.4.6: 改为打开独立窗口（跟仪表盘一样的界面）
        self.query_center_btn = DarkButton(
            right_frame, "🔍 任务查询中心",
            command=self.open_task_center,
            width=170, height=44, bg_color="#8e44ad", text_color="#ffffff")
        self.query_center_btn.pack(side=tk.RIGHT, padx=(0, 8))

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
                  height=26, width=70, bg_color=COLORS["bg_input"], tip="刷新抢码统计面板数据",
                  text_color=COLORS["text_primary"]).pack(side=tk.RIGHT, padx=(6, 0))
        DarkButton(stats_head, text="📈 详细仪表盘", command=self.open_stats_dashboard,
                  height=26, width=120, bg_color="#8e44ad", tip="打开详细统计仪表盘（18项指标、库存窗口等）",
                  text_color="#ffffff").pack(side=tk.RIGHT)
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

    def _current_ui_settings_snapshot(self):
        """抓取当前 UI 设置快照，用于存进预案。"""
        try:
            return {
                "version": self.nm_version_var.get(),
                "period": self.nm_period_var.get(),
                "type": self.nm_type_var.get(),
                "task": self.nm_task_var.get(),
                "account": self.nm_account_var.get(),
                "window": self.nm_window_entry.get(),
                "base_interval": self.nm_base_interval_entry.get(),
                "group": self.nm_group_var.get(),
                "target_hour": self.nm_hour_var.get(),
                "target_minute": self.nm_minute_var.get(),
                "target_second": self.nm_second_var.get(),
                "target_ms": self.nm_ms_entry.get(),
            }
        except Exception:
            return {}

    def open_preset_manager(self):
        """抢码预案管理器（v6.2.0 新增）。

        预案 = 整套任务组配置的快照。用于不同活动之间快速切换，
        避免每次都手动改目标时间/窗口期/间隔。
        """
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("抢码预案管理")
        dlg.configure(bg=COLORS["bg_dark"])
        dlg.geometry("820x600")
        try:
            dlg.transient(self.winfo_toplevel())
        except Exception:
            pass

        # ---- 顶部说明 ----
        head = tk.Frame(dlg, bg=COLORS["bg_card"])
        head.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(head, text="📦 抢码预案", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=14, pady=(10, 2))
        tk.Label(head, text="把当前整套任务组配置存成预案，下次一键切换，不用再手改时间/间隔",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(anchor=tk.W, padx=14, pady=(0, 10))

        # ---- 保存新预案 ----
        save_row = tk.Frame(dlg, bg=COLORS["bg_dark"])
        save_row.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(save_row, text="预案名称:", bg=COLORS["bg_dark"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        name_entry = tk.Entry(save_row, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                              insertbackground=COLORS["accent"], relief=tk.FLAT,
                              font=("微软雅黑", 10), width=28)
        name_entry.pack(side=tk.LEFT, padx=(6, 10), ipady=4)
        tk.Label(save_row, text="备注:", bg=COLORS["bg_dark"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        note_entry = tk.Entry(save_row, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                              insertbackground=COLORS["accent"], relief=tk.FLAT,
                              font=("微软雅黑", 10), width=18)
        note_entry.pack(side=tk.LEFT, padx=(6, 0), ipady=4)

        # ---- 预案列表 ----
        list_card = tk.Frame(dlg, bg=COLORS["bg_card"])
        list_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        tk.Label(list_card, text="已有预案（双击直接加载）", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 10, "bold")
                 ).pack(anchor=tk.W, padx=12, pady=(8, 4))
        lf = tk.Frame(list_card, bg=COLORS["bg_card"])
        lf.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        sb = tk.Scrollbar(lf, orient=tk.VERTICAL)
        lb = tk.Listbox(lf, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                        font=("Consolas", 9), bd=0, highlightthickness=0,
                        selectbackground=COLORS["accent"], selectforeground="#000000",
                        yscrollcommand=sb.set)
        sb.config(command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        presets = {"data": rush_presets.load_presets()}

        def refresh_list():
            lb.delete(0, tk.END)
            for p in presets["data"]:
                lb.insert(tk.END, rush_presets.summarize(p))
            if not presets["data"]:
                lb.insert(tk.END, "（暂无预案，填写名称后点「保存当前配置为预案」）")

        def do_save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "请先填写预案名称", parent=dlg)
                return
            if not self.rush_groups:
                messagebox.showwarning("提示", "当前没有任何任务组，无法保存预案", parent=dlg)
                return
            preset = rush_presets.make_preset(
                name, self.rush_groups,
                ui_settings=self._current_ui_settings_snapshot(),
                note=note_entry.get().strip())
            presets["data"], replaced = rush_presets.upsert_preset(presets["data"], preset)
            ok = rush_presets.save_presets(presets["data"])
            if ok:
                self.nm_log(f"📦 预案已{'覆盖' if replaced else '保存'}: {name}"
                            f"（{len(preset['groups'])} 组 / "
                            f"{sum(len(g.get('tasks', [])) for g in preset['groups'])} 任务）")
                refresh_list()
            else:
                messagebox.showerror("失败", "预案写入文件失败", parent=dlg)

        def do_load():
            sel = lb.curselection()
            if not sel or not presets["data"]:
                messagebox.showwarning("提示", "请先在列表中选择一个预案", parent=dlg)
                return
            idx = sel[0]
            if idx >= len(presets["data"]):
                return
            p = presets["data"][idx]
            n_groups = len(p.get("groups", []))
            n_tasks = sum(len(g.get("tasks", [])) for g in p.get("groups", []))
            if not messagebox.askyesno(
                    "加载预案",
                    f"确定加载预案「{p.get('name','')}」吗？\n\n"
                    f"会用该预案的 {n_groups} 个任务组 / {n_tasks} 个任务\n"
                    f"替换当前全部任务组配置。\n\n"
                    f"（当前配置不会自动备份，如需保留请先另存为新预案）",
                    parent=dlg):
                return
            # 深拷贝，避免预案数据和运行时互相污染
            self.rush_groups = rush_presets.deep_copy_groups(p.get("groups", []))
            if self.rush_groups:
                self.current_group_id = self.rush_groups[0].get("group_id")
            else:
                self.current_group_id = None
            self.save_rush_groups()

            # 恢复 UI 设置
            ui = p.get("ui_settings") or {}
            try:
                if ui.get("window"):
                    self.nm_window_entry.delete(0, tk.END)
                    self.nm_window_entry.insert(0, ui["window"])
                if ui.get("base_interval"):
                    self.nm_base_interval_entry.delete(0, tk.END)
                    self.nm_base_interval_entry.insert(0, ui["base_interval"])
                for key, var in (("target_hour", self.nm_hour_var),
                                 ("target_minute", self.nm_minute_var),
                                 ("target_second", self.nm_second_var)):
                    if ui.get(key):
                        var.set(ui[key])
                if ui.get("target_ms"):
                    self.nm_ms_entry.delete(0, tk.END)
                    self.nm_ms_entry.insert(0, ui["target_ms"])
            except Exception:
                pass

            # 刷新界面
            try:
                self.refresh_new_mode_group_list()
                self.refresh_new_mode_task_list()
                if hasattr(self, "nm_update_scheduler"):
                    self.nm_update_scheduler()
                self.nm_save_ui_settings()
            except Exception:
                pass

            self.nm_log(f"📦 已加载预案「{p.get('name','')}」：{n_groups} 组 / {n_tasks} 任务")
            messagebox.showinfo("已加载", f"预案「{p.get('name','')}」已加载。\n\n"
                                          f"{n_groups} 个任务组 / {n_tasks} 个任务",
                                parent=dlg)
            dlg.destroy()

        def do_delete():
            sel = lb.curselection()
            if not sel or not presets["data"]:
                messagebox.showwarning("提示", "请先选择要删除的预案", parent=dlg)
                return
            idx = sel[0]
            if idx >= len(presets["data"]):
                return
            p = presets["data"][idx]
            if not messagebox.askyesno("确认删除",
                                       f"确定删除预案「{p.get('name','')}」吗？",
                                       parent=dlg):
                return
            presets["data"] = rush_presets.delete_preset(presets["data"], p.get("name", ""))
            rush_presets.save_presets(presets["data"])
            self.nm_log(f"📦 已删除预案: {p.get('name','')}")
            refresh_list()

        def do_export():
            """导出预案到指定文件（方便备份/分享）"""
            sel = lb.curselection()
            if not sel or not presets["data"]:
                messagebox.showwarning("提示", "请先选择要导出的预案", parent=dlg)
                return
            idx = sel[0]
            if idx >= len(presets["data"]):
                return
            p = presets["data"][idx]
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                parent=dlg, title="导出预案",
                defaultextension=".json",
                initialfile=f"预案_{p.get('name','preset')}.json",
                filetypes=[("JSON 文件", "*.json")])
            if not path:
                return
            try:
                import json as _json
                with open(path, "w", encoding="utf-8") as f:
                    _json.dump(p, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("导出成功", f"已导出到:\n{path}", parent=dlg)
            except Exception as e:
                messagebox.showerror("导出失败", str(e), parent=dlg)

        # ---- 按钮区 ----
        btn_row = tk.Frame(dlg, bg=COLORS["bg_dark"])
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        DarkButton(btn_row, text="💾 保存当前配置为预案", command=do_save,
                   height=32, bg_color=COLORS["accent"], text_color="#000000"
                   ).pack(side=tk.LEFT)
        DarkButton(btn_row, text="▶ 加载选中预案", command=do_load,
                   height=32, bg_color=COLORS["success"], text_color="#000000"
                   ).pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(btn_row, text="📤 导出", command=do_export,
                   height=32, bg_color="#2980b9", text_color="#ffffff"
                   ).pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(btn_row, text="🗑 删除", command=do_delete,
                   height=32, bg_color="#c0392b", text_color="#ffffff"
                   ).pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(btn_row, text="关闭", command=dlg.destroy,
                   height=32, bg_color="#7f8c8d", text_color="#ffffff"
                   ).pack(side=tk.RIGHT)

        lb.bind("<Double-Button-1>", lambda e: do_load())
        refresh_list()

    def open_stats_dashboard(self):
        """抢码成功率仪表盘（v6.3.0 重写，v6.3.1 修复配色可读性）。

        v6.3.0 增强：
          - 窗口加大到 1400x900（原 1000x680 显示不全）
          - 左右分栏：左侧三个分析报表（标签页切换），右侧明细记录
          - 新增「仅看稀有奖励」过滤（四个游戏的稀有货币/抽卡券）
          - 新增明细记录列表，可逐条手动剔除/恢复，剔除持久化

        展示三个核心分析：
          1) 各任务历史成功率 —— 哪些任务值得优先抢
          2) 各提前量区间成功率 —— 哪个提前量命中率最高（数据驱动调参）
          3) 风控高发时段 —— 避开高风险时段
        """
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("抢码成功率仪表盘")
        dlg.configure(bg=COLORS["bg_dark"])
        # v6.3.0: 加大窗口，并居中显示
        try:
            # v6.4.2: 窗口尺寸按 DPI 缩放修正
            # 本机屏幕 2560x1600，DPI scale 1.4985，
            # 请求 2040 逻辑像素时实际只有 ~1375 物理像素，
            # 导致内容被挤出。这里按可用物理像素反算安全尺寸。
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            try:
                scale = dlg.winfo_fpixels("1i") / 96.0
            except Exception:
                scale = 1.0
            if scale < 0.5 or scale > 4:
                scale = 1.0
            # v6.4.4: 窗口加大到屏幕 88% 宽、92% 高
            # 原因：底部按钮（剔除所选/恢复所选/清空全部剔除/刷新）被裁掉，
            # 用户要求「仪表盘下方的按钮现在是遮住的，你还要调大窗口」。
            w = int(sw * 0.88)
            h = int(sh * 0.92)
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2 - 10)
            dlg.geometry(f"{w}x{h}+{x}+{y}")
            # 最小尺寸：保证 5 列指标 + 6 列明细 + 底部按钮都放得下
            dlg.minsize(1360, 860)
        except Exception:
            dlg.geometry("1700x900")
        # v6.4.5: 去掉了 transient —— Tk 禁止附属窗口最小化
        # （实测报错 "can't iconify: it is a transient"），
        # 这也是用户反馈「最小化点击无效」的根因。
        # 改为独立顶层窗口后，系统原生最小化/最大化/关闭按钮全部可用。

        # ---- v6.3.1 高对比度配色（解决深色背景下文字看不清）----
        # 原配色问题：Treeview 未设默认前景色，用了系统深色 -> 几乎不可见；
        # 表格里的 warning(#ffa502)/danger(#ff4757) 在深色底上偏暗。
        # 新配色全部经对比度计算，均 ≥5.3（WCAG AA 要求 4.5）。
        D = {
            "row1": "#1c2847",       # 奇数行底色
            "row2": "#16213e",       # 偶数行底色
            "text": "#ffffff",       # 主文字（对比度 15.9）
            "text2": "#c8c8e0",      # 次要文字（9.7）
            "muted": "#9d9db8",      # 弱化文字（6.0，原 3.14 太暗）
            "ok": "#39ff88",         # 成功/高成功率（12.0）
            "mid": "#ffd93d",        # 中等/警告（11.5，原橙色偏暗）
            "bad": "#ff6b81",        # 失败/低成功率（5.8，原红色偏暗）
            "rare": "#ffd700",       # 稀有标记（11.3）
            "normal": "#adb5bd",     # 普通标记（7.7）
            "excluded": "#8a8aa0",   # 已剔除（灰色但可辨认）
            # v6.3.4: 选中高亮色（解决"选中看不出来"的问题）
            # 原选中色 #0f3460 与普通行背景 #16213e 对比度仅 1.27，几乎不可见。
            # 新色 #0d7a9e 对比度 3.25，配合白色文字（4.89）清晰可辨。
            "sel": "#0d7a9e",        # 选中行背景（亮青）
            "sel_text": "#ffffff",   # 选中行文字（纯白）
        }

        # ---- 过滤状态（v6.4.5: 从配置文件读取，切换后自动保存）----
        # 用户需求：
        #   1. 过滤信息要保存（下次打开还是上次的选择）
        #   2. 默认仅查看稀有奖励
        #   3. 默认不显示已剔除的任务
        _saved_filters = rush_stats.load_dash_filters()
        state = {
            "rare_only": tk.BooleanVar(value=_saved_filters.get("rare_only", True)),
            "show_excluded": tk.BooleanVar(
                value=_saved_filters.get("show_excluded", False)),
            # v6.5.1: 时间范围（用户需求4种：全部/昨天/近3天/自定义）
            "date_range": tk.StringVar(
                value=_saved_filters.get("date_range", rush_stats.RANGE_ALL)),
            "custom_from": tk.StringVar(
                value=_saved_filters.get("custom_from", "")),
            "custom_to": tk.StringVar(
                value=_saved_filters.get("custom_to", "")),
        }
        render_holder = {"fn": None}

        def _persist_filters():
            """把当前过滤状态写盘（勾选变化时调用）。"""
            try:
                rush_stats.save_dash_filters({
                    "rare_only": bool(state["rare_only"].get()),
                    "show_excluded": bool(state["show_excluded"].get()),
                    # v6.5.1: 时间范围也要记住
                    "date_range": str(state["date_range"].get() or "all"),
                    "custom_from": str(state["custom_from"].get() or ""),
                    "custom_to": str(state["custom_to"].get() or ""),
                })
            except Exception:
                pass

        # ============ 顶部标题栏 ============
        head = tk.Frame(dlg, bg=COLORS["bg_card"])
        head.pack(fill=tk.X, padx=14, pady=(14, 8))

        title_row = tk.Frame(head, bg=COLORS["bg_card"])
        title_row.pack(fill=tk.X, padx=18, pady=(14, 8))
        tk.Label(title_row, text="📈 抢码成功率仪表盘", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold")
                 ).pack(side=tk.LEFT)

        # 过滤控制条
        ctrl = tk.Frame(head, bg=COLORS["bg_card"])
        ctrl.pack(fill=tk.X, padx=18, pady=(0, 10))
        tk.Label(ctrl, text="过滤：", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)

        try:
            def _on_filter_change():
                """勾选变化：先保存过滤条件，再重新渲染。"""
                _persist_filters()
                try:
                    if render_holder.get("fn"):
                        render_holder["fn"]()
                except Exception:
                    pass

            rare_cb = ttk.Checkbutton(ctrl,
                                      text="仅看稀有奖励（原石/星琼/星轨通票/菲林/原装母带/星声/唤声涡纹）",
                                      variable=state["rare_only"],
                                      command=_on_filter_change)
            rare_cb.pack(side=tk.LEFT, padx=(6, 20))
            exc_cb = ttk.Checkbutton(ctrl, text="显示已剔除记录",
                                     variable=state["show_excluded"],
                                     command=_on_filter_change)
            exc_cb.pack(side=tk.LEFT, padx=(0, 20))
        except Exception:
            pass

        # ===== v6.5.1: 时间范围选择（用户需求）=====
        range_row = tk.Frame(head, bg=COLORS["bg_card"])
        range_row.pack(fill=tk.X, padx=18, pady=(0, 8))
        tk.Label(range_row, text="时间范围：", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)
                 ).pack(side=tk.LEFT)

        _RANGE_CHOICES = [
            ("全部数据", rush_stats.RANGE_ALL),
            ("昨天", rush_stats.RANGE_YESTERDAY),
            ("近3天", rush_stats.RANGE_3DAYS),
            ("自定义", rush_stats.RANGE_CUSTOM),
        ]
        _label_to_key = {lab: key for lab, key in _RANGE_CHOICES}
        _key_to_label = {key: lab for lab, key in _RANGE_CHOICES}

        _cur_range = str(state["date_range"].get() or rush_stats.RANGE_ALL)
        if _cur_range not in _key_to_label:
            _cur_range = rush_stats.RANGE_ALL
        range_var = tk.StringVar(value=_key_to_label[_cur_range])

        from_lbl = tk.Label(range_row, text="从", bg=COLORS["bg_card"],
                            fg=COLORS["text_muted"], font=("微软雅黑", 9))
        from_ent = RoundEntry(range_row, width=12, font=("Consolas", 10))
        to_lbl = tk.Label(range_row, text="到", bg=COLORS["bg_card"],
                          fg=COLORS["text_muted"], font=("微软雅黑", 9))
        to_ent = RoundEntry(range_row, width=12, font=("Consolas", 10))

        def _sync_custom_visibility(*_a):
            key = _label_to_key.get(range_var.get(), rush_stats.RANGE_ALL)
            state["date_range"].set(key)
            _persist_filters()
            if key == rush_stats.RANGE_CUSTOM:
                from_lbl.pack(side=tk.LEFT, padx=(12, 2))
                from_ent.pack(side=tk.LEFT)
                to_lbl.pack(side=tk.LEFT, padx=(8, 2))
                to_ent.pack(side=tk.LEFT)
            else:
                for w in (from_lbl, from_ent, to_lbl, to_ent):
                    try:
                        w.pack_forget()
                    except Exception:
                        pass
            try:
                if render_holder.get("fn"):
                    render_holder["fn"]()
            except Exception:
                pass

        range_combo = RoundCombobox(
            range_row, textvariable=range_var,
            values=[lab for lab, _ in _RANGE_CHOICES],
            width=12, font=("微软雅黑", 10), state="readonly")
        range_combo.pack(side=tk.LEFT, padx=(4, 0))
        range_combo.bind("<<ComboboxSelected>>",
                         lambda e: _sync_custom_visibility())

        # 预填自定义日期（默认今天、昨天）
        try:
            import datetime as _dtm
            _today = _dtm.date.today()
            _cf = str(state["custom_from"].get() or "")
            _ct = str(state["custom_to"].get() or "")
            from_ent.insert(0, _cf or (_today - _dtm.timedelta(days=1)).strftime("%Y-%m-%d"))
            to_ent.insert(0, _ct or _today.strftime("%Y-%m-%d"))
        except Exception:
            pass

        def _on_custom_date_change(*_a):
            try:
                state["custom_from"].set(from_ent.get().strip())
                state["custom_to"].set(to_ent.get().strip())
            except Exception:
                pass
            _persist_filters()
            try:
                if render_holder.get("fn"):
                    render_holder["fn"]()
            except Exception:
                pass

        from_ent.bind("<FocusOut>", _on_custom_date_change)
        from_ent.bind("<Return>", _on_custom_date_change)
        to_ent.bind("<FocusOut>", _on_custom_date_change)
        to_ent.bind("<Return>", _on_custom_date_change)

        tk.Label(range_row,
                 text="（近3天含今天；自定义格式 YYYY-MM-DD）",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        # 统计摘要行
        summary_lbl = tk.Label(head, text="", bg=COLORS["bg_card"],
                               fg=COLORS["text_primary"], font=("微软雅黑", 11),
                               anchor=tk.W, justify=tk.LEFT)
        summary_lbl.pack(fill=tk.X, padx=18, pady=(0, 12))

        # ============ 主体：左右分栏 ============
        body = tk.PanedWindow(dlg, orient=tk.HORIZONTAL, bg=COLORS["bg_dark"],
                              sashrelief=tk.FLAT, sashwidth=6, bd=0)

        # v6.4.4: 先创建并 pack 底部按钮区，再 pack 主体。
        # Tk 的 pack 规则是"先 pack 的优先占用空间"，
        # 原代码 body 先 pack(fill=BOTH, expand=True) 会吃光空间，
        # 导致后面 pack 的 foot（剔除/恢复/刷新按钮）被挤出窗口外。
        foot = tk.Frame(dlg, bg=COLORS["bg_dark"])
        foot.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 12))
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        # ---- 左侧：三个分析报表（用 Notebook 节省纵向空间）----
        left = tk.Frame(body, bg=COLORS["bg_dark"])
        body.add(left, minsize=620, width=760)

        try:
            nb = ttk.Notebook(left)
            nb.pack(fill=tk.BOTH, expand=True)
        except Exception:
            nb = None

        def make_table(parent, headers, rows, col_w, colorize_rate_col=None,
                       row_tags=None, on_row_click=None, selected_rows=None,
                       rows_widget_store=None):
            """在 parent 里生成一个表格，返回外层 Frame。

            v6.3.2 重构：用 grid + weight 自适应容器宽度。
            原来用 pack(side=LEFT) + 固定 width，当总宽度超过容器时
            后面的列会被直接挤掉（用户反馈"方框内有内容没显示完全"）。
            现在改为 grid，列宽按权重分配，最小宽度保证不被压缩。

            row_tags              每行状态标签（"excluded"= 已剔除，整行灰显）
            selected_rows         已选中的行号集合（用于高亮）
            rows_widget_store     可选 dict，用于回存每行的控件（供外部刷新高亮）
            on_row_click          单击某行的回调，参数是 (行号, 是否Ctrl多选)
            """
            card = tk.Frame(parent, bg=COLORS["bg_card"])
            card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            inner = tk.Frame(card, bg=COLORS["bg_card"])
            inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=(12, 4))

            # 列宽按字符数转成相对权重；第一列（任务名）占大头
            weights = list(col_w)
            ncol = len(headers)

            # 每列最小像素宽（按字符数 * 估算字符宽 9px，再加内边距）
            min_px = [max(60, int(w * 9) + 20) for w in col_w]

            # ==== 表头 ====
            hdr = tk.Frame(inner, bg=COLORS["bg_input"])
            hdr.pack(fill=tk.X)
            hdr.columnconfigure(tuple(range(ncol)), weight=0)  # 先占位，下面重设
            for i, h in enumerate(headers):
                hdr.grid_columnconfigure(i, weight=weights[i], minsize=min_px[i])
                lb = tk.Label(hdr, text=h, bg=COLORS["bg_input"],
                              fg=COLORS["text_secondary"],
                              font=("微软雅黑", 11, "bold"), anchor=tk.W)
                lb.grid(row=0, column=i, sticky="w", padx=(6, 10), pady=7)

            # ==== 数据行 ====
            if not rows:
                r = tk.Frame(inner, bg=COLORS["bg_card"])
                r.pack(fill=tk.X)
                tk.Label(r, text="（暂无数据）", bg=COLORS["bg_card"],
                         fg=D["muted"], font=("微软雅黑", 10),
                         anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=10)
                return card

            body = tk.Frame(inner, bg=COLORS["bg_card"])
            body.pack(fill=tk.BOTH, expand=True)
            for i in range(ncol):
                body.grid_columnconfigure(i, weight=weights[i], minsize=min_px[i])

            for ridx, row in enumerate(rows):
                # v6.3.2/3.3: 已剔除灰显 + 选中高亮
                row_excluded = bool(row_tags and ridx < len(row_tags)
                                    and "excluded" in row_tags[ridx])
                row_selected = bool(selected_rows and ridx in selected_rows)
                if row_selected:
                    row_bg = D["sel"]                # v6.3.4: 亮青高亮（对比度3.25）
                elif row_excluded:
                    row_bg = D["row2"]               # 已剔除：暗底
                else:
                    row_bg = COLORS["bg_card"]
                row_widgets = []
                for i, v in enumerate(row):
                    if row_selected:
                        fg_c = D["sel_text"]         # v6.3.4: 选中行纯白文字
                    elif row_excluded:
                        fg_c = D["excluded"]
                    else:
                        fg_c = D["text"]
                    txt = str(v)
                    # v6.3.4: 选中行首列加 ● 标记，即使色弱也能分辨
                    if row_selected and i == 0:
                        txt = "● " + txt
                    elif row_excluded and i == 0:
                        txt = "○ " + txt
                    if (not row_excluded and not row_selected
                            and colorize_rate_col is not None
                            and i == colorize_rate_col and "%" in txt):
                        try:
                            pct = float(txt.replace("%", ""))
                            fg_c = (D["ok"] if pct >= 50 else
                                    D["mid"] if pct >= 20 else D["bad"])
                        except Exception:
                            pass
                    # v6.3.4: 选中行用粗体，进一步强化区分
                    _font = ("Consolas", 11, "bold") if row_selected else ("Consolas", 11)
                    lb = tk.Label(body, text=txt, bg=row_bg, fg=fg_c,
                                  font=_font, anchor=tk.W)
                    lb.grid(row=ridx, column=i, sticky="w", padx=(6, 10), pady=4)
                    row_widgets.append(lb)
                if rows_widget_store is not None:
                    rows_widget_store[ridx] = row_widgets
                # v6.3.3: 行选中机制（单击选中/取消，Ctrl 多选）
                # 不再双击直接剔除，改为选中后点底部按钮确认
                if on_row_click is not None:
                    def _mk(ridx=ridx, widgets=row_widgets):
                        def _handler(event=None):
                            try:
                                ctrl = False
                                try:
                                    ctrl = bool(event and (event.state & 0x0004))
                                except Exception:
                                    ctrl = False
                                on_row_click(ridx, ctrl)
                            except Exception:
                                pass
                        return _handler
                    _handler = _mk()
                    for _wdg in row_widgets:
                        _wdg.bind("<Button-1>", _handler)
                        _wdg.bind("<Enter>", lambda e, wl=row_widgets: [
                            x.config(cursor="hand2") for x in wl])

            return card


            for row in rows:
                r = tk.Frame(inner, bg=COLORS["bg_card"])
                r.pack(fill=tk.X)
                for i, (v, w) in enumerate(zip(row, col_w)):
                    fg_c = COLORS["text_primary"]
                    txt = str(v)
                    if colorize_rate_col is not None and i == colorize_rate_col and "%" in txt:
                        try:
                            pct = float(txt.replace("%", ""))
                            # v6.3.1: 用高对比度配色（原 success/warning/danger 偏暗）
                            fg_c = (D["ok"] if pct >= 50 else
                                    D["mid"] if pct >= 20 else
                                    D["bad"])
                        except Exception:
                            pass
                    tk.Label(r, text=txt, bg=COLORS["bg_card"], fg=fg_c,
                             font=("Consolas", 11), width=w, anchor=tk.W
                             ).pack(side=tk.LEFT, padx=6, pady=5)
            return card

        # v6.4.2: 记住当前选中的标签页索引，重建后恢复（解决"剔除后跳回第一个"）
        _tab_state = {"index": 0}

        def build_tables(data):
            """按当前数据重建左侧报表（清空后重建，保持当前标签页）。"""
            # 重建前先记下当前选中的标签页
            try:
                _old_nb = None
                for _c in left.winfo_children():
                    if type(_c).__name__ == "Notebook":
                        _old_nb = _c
                        break
                if _old_nb is not None:
                    _sel = _old_nb.select()
                    if _sel:
                        _idx = _old_nb.index(_sel)
                        _tab_state["index"] = _idx
            except Exception:
                pass

            for w in list(left.winfo_children()):
                w.destroy()
            try:
                nb2 = ttk.Notebook(left)
                nb2.pack(fill=tk.BOTH, expand=True)
            except Exception:
                nb2 = None

            def add_tab(frame, text):
                if nb2 is not None:
                    nb2.add(frame, text=text)
                else:
                    frame.pack(fill=tk.BOTH, expand=True)

            # --- ① 抢码状态（v6.4.1: 完整 18 项指标分组展示）---
            fS = tk.Frame(left, bg=COLORS["bg_card"])
            snap = rush_stats.score_snapshot(data)
            metrics = rush_stats.metrics_all(data)

            # ===== 顶部：程序健康分（区分"程序对不对"和"运气好不好"）=====
            # v6.4.2: 改用 grid + anchor=S 实现【基线对齐】
            # 原实现用 pack(side=LEFT) 配合不同 pady(0/6/7) 手工凑高度，
            # 导致图标、大数字、小字、说明文字的基线参差不齐（看起来歪）。
            # 现在统一 bottom 对齐，各元素底部齐平。
            score_head = tk.Frame(fS, bg=COLORS["bg_card"])
            score_head.pack(fill=tk.X, padx=14, pady=(10, 2))
            score_head.grid_columnconfigure(4, weight=1)   # 右侧弹性占位

            _pc = {"ok": D["ok"], "mid": D["mid"], "bad": D["bad"],
                   "muted": D["muted"]}.get(snap.get("program_color"), D["text"])
            _ps = snap.get("program_score")

            tk.Label(score_head, text="程序健康分", bg=COLORS["bg_card"],
                     fg=D["text2"], font=("微软雅黑", 10)
                     ).grid(row=0, column=0, sticky="sw", pady=(0, 3))
            tk.Label(score_head, text=str(_ps if _ps is not None else "--"),
                     bg=COLORS["bg_card"], fg=_pc,
                     font=("Consolas", 22, "bold")
                     ).grid(row=0, column=1, sticky="sw", padx=(6, 0))
            tk.Label(score_head,
                     text="/100 " + str(snap.get("program_level", "")),
                     bg=COLORS["bg_card"], fg=_pc,
                     font=("微软雅黑", 10, "bold")
                     ).grid(row=0, column=2, sticky="sw", padx=(4, 0), pady=(0, 3))
            _rs = snap.get("result_score")
            _rtxt = "未采集" if _rs is None else "%d%%" % _rs
            tk.Label(score_head,
                     text="结果参考 " + str(_rtxt) + "（随机，仅参考）",
                     bg=COLORS["bg_card"], fg=D["muted"],
                     font=("微软雅黑", 9)
                     ).grid(row=0, column=3, sticky="sw", padx=(18, 0), pady=(0, 4))

            tk.Label(fS,
                     text="说明：抢码成功有随机性（库存/竞争）。健康分只评估程序是否做对，抢不到不等于程序差。",
                     bg=COLORS["bg_card"], fg=D["muted"],
                     font=("微软雅黑", 9), anchor=tk.W
                     ).pack(fill=tk.X, padx=14, pady=(0, 4))

            # ===== 指标列表（可滚动，按 A/B/C/D/E 分组）=====
            list_wrap = tk.Frame(fS, bg=COLORS["bg_card"])
            list_wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

            # v6.4.2: 去掉 Canvas 滚动 —— 左面板高度足够容纳全部指标，直接放 Frame
            # 原因：Canvas + create_window 在 Tk 下宽度上报为 1px，导致布局异常。
            # 实测左面板高 1123px，18项指标+5分组+表头约需 820px，完全放得下。
            inner_m = tk.Frame(list_wrap, bg=COLORS["bg_card"])
            inner_m.pack(fill=tk.BOTH, expand=True)

            # 表头 + 数据行共用同一个 Grid 容器（v6.4.5 修复列不对齐）
            # 根因：原代码表头和数据行各自是独立 Frame + 各自 grid_columnconfigure，
            #       两边列宽分配互相独立，实测列起点偏移 +24/+17/+7px。
            # 修复：所有行（含表头）放在同一个 Frame 里，列配置只设一次，自然对齐。
            COL_WEIGHTS = (3, 1, 3, 2)
            COL_MINS = (140, 46, 100, 70)

            grid_m = tk.Frame(inner_m, bg=COLORS["bg_card"])
            grid_m.pack(fill=tk.X)
            for _ci in range(4):
                grid_m.grid_columnconfigure(_ci,
                                           weight=COL_WEIGHTS[_ci],
                                           minsize=COL_MINS[_ci],
                                           uniform="col")

            _gr = {"row": 0}

            def _add_grid_row(values, colors, bold=False, is_header=False,
                              span_full=False, bgkey="bg_card"):
                """往共享 Grid 里加一行。span_full=True 时整行跨 4 列合并。"""
                _r = _gr["row"]
                _gr["row"] += 1
                _bg = COLORS[bgkey]
                if span_full:
                    tk.Label(grid_m, text=str(values[0]), bg=_bg,
                             fg=colors[0],
                             font=("微软雅黑", 10,
                                   "bold" if bold else "normal"),
                             anchor=tk.W
                             ).grid(row=_r, column=0, columnspan=4,
                                    sticky="w", padx=6, pady=3)
                    return
                for _i, (_v, _c) in enumerate(zip(values, colors)):
                    tk.Label(grid_m, text=str(_v), bg=_bg, fg=_c,
                             font=("Consolas", 10 if not is_header else 10,
                                   "bold" if (bold or is_header) else "normal"),
                             anchor=tk.W
                             ).grid(row=_r, column=_i, sticky="w",
                                    padx=6, pady=(5 if is_header else 2))

            # ---- 表头行 ----
            _add_grid_row(("指标", "得分", "当前值", "状态"),
                          (D["text2"], D["text2"], D["text2"], D["text2"]),
                          is_header=True, bgkey="bg_input")

            # ---- 数据行（按 A/B/C/D/E 分组）----
            _cur_group = None
            for m in metrics:
                if m["group"] != _cur_group:
                    _cur_group = m["group"]
                    _add_grid_row((_cur_group,), (COLORS["accent"],),
                                  bold=True, span_full=True,
                                  bgkey="bg_input")
                _c = {"ok": D["ok"], "mid": D["mid"], "bad": D["bad"],
                      "muted": D["muted"]}.get(m.get("color"), D["text"])
                _sc_txt = "—" if m["score"] is None else str(m["score"])
                _add_grid_row((m["name"], _sc_txt, m["value"], m["grade"]),
                              (D["text"], _c, _c, _c))
            add_tab(fS, " ① 抢码状态 ")
            # --- ② 各任务成功率（v6.3.3: 单击选中 -> 点按钮确认剔除）---
            f1 = tk.Frame(left, bg=COLORS["bg_card"])
            task_rows = []
            task_names = []
            task_tags = []
            # 建立 任务名 -> 该任务的全部记录 的映射（用于批量剔除）
            by_task_recs = {}
            for r in data.get("records", []):
                by_task_recs.setdefault(r.get("task_name", ""), []).append(r)
            for t in data.get("by_task", [])[:20]:
                nm = t["task"]
                task_names.append(nm)
                recs = by_task_recs.get(nm, [])
                all_excl = bool(recs) and all(x.get("excluded") for x in recs)
                task_tags.append(["excluded"] if all_excl else [])
                task_rows.append([
                    nm[:30],
                    str(t["total"]),
                    str(t["success"]),
                    f"{t['rate']}%",
                    str(t["risk"]),
                ])

            # 左侧任务的选中集合（行号 -> 任务名），支持 Ctrl 多选
            left_sel = {"rows": set()}

            def _on_task_click(ridx, ctrl, _names=task_names):
                """单击任务行：选中/取消（Ctrl 切换多选，非 Ctrl 单选）。"""
                if ridx < 0 or ridx >= len(_names):
                    return
                if ctrl:
                    if ridx in left_sel["rows"]:
                        left_sel["rows"].discard(ridx)
                    else:
                        left_sel["rows"].add(ridx)
                else:
                    if left_sel["rows"] == {ridx}:
                        left_sel["rows"].clear()
                    else:
                        left_sel["rows"] = {ridx}
                _refresh_left_buttons()
                render_marks()

            def _confirmed_exclude_tasks():
                """确认后剔除【选中任务】的全部记录。"""
                if not left_sel["rows"]:
                    messagebox.showwarning("未选择",
                                           "请先选中要剔除的任务行\n\n"
                                           "（按住 Ctrl 可多选任务）",
                                           parent=dlg)
                    return
                sel_names = [_names for _i, _names in
                             ((i, task_names[i]) for i in sorted(left_sel["rows"])
                              if 0 <= i < len(task_names))]
                # 收集这些任务的全部记录
                all_recs = []
                for nm in sel_names:
                    all_recs.extend(by_task_recs.get(nm, []))
                if not all_recs:
                    messagebox.showinfo("提示", "选中的任务没有可剔除的记录", parent=dlg)
                    return
                lines = []
                for nm in sel_names[:6]:
                    cnt = len(by_task_recs.get(nm, []))
                    lines.append("  · " + str(nm)[:26] + "  (" + str(cnt) + " 条)")
                if len(sel_names) > 6:
                    lines.append("  · ... 共 " + str(len(sel_names)) + " 个任务")
                ok = messagebox.askyesno(
                    "确认剔除",
                    "确定要剔除以下任务的【全部记录】吗？\n\n"
                    + "\n".join(lines)
                    + "\n\n合计 " + str(len(all_recs)) + " 条记录。\n"
                    "剔除后不参与统计，可随时恢复。",
                    parent=dlg)
                if not ok:
                    return
                excl = rush_stats.load_excluded()
                new_set = set(excl)
                for r in all_recs:
                    new_set.add(rush_stats.make_record_key(r))
                rush_stats.save_excluded(new_set)
                self.nm_log("剔除 " + str(len(sel_names)) + " 个任务的 "
                            + str(len(all_recs)) + " 条记录")
                left_sel["rows"].clear()
                render()

            def _confirmed_restore_tasks():
                """确认后恢复【选中任务】的全部记录。"""
                if not left_sel["rows"]:
                    messagebox.showwarning("未选择", "请先选中要恢复的任务行", parent=dlg)
                    return
                sel_names = [task_names[i] for i in sorted(left_sel["rows"])
                             if 0 <= i < len(task_names)]
                all_recs = []
                for nm in sel_names:
                    all_recs.extend(by_task_recs.get(nm, []))
                if not all_recs:
                    return
                excl = rush_stats.load_excluded()
                removable = [r for r in all_recs if rush_stats.make_record_key(r) in excl]
                if not removable:
                    messagebox.showinfo("提示", "选中的任务没有被剔除的记录，无需恢复",
                                        parent=dlg)
                    return
                if not messagebox.askyesno(
                        "确认恢复",
                        "确定要恢复以下任务的记录吗？\n\n"
                        "  " + "\n  ".join(str(n)[:26] for n in sel_names[:6])
                        + "\n\n合计 " + str(len(removable)) + " 条记录。",
                        parent=dlg):
                    return
                new_set = set(excl)
                for r in removable:
                    new_set.discard(rush_stats.make_record_key(r))
                rush_stats.save_excluded(new_set)
                self.nm_log("恢复 " + str(len(removable)) + " 条记录")
                left_sel["rows"].clear()
                render()

            task_widgets = {}
            tkf = make_table(f1, ["任务名称", "请求", "成功", "成功率", "风控"],
                             task_rows, (34, 8, 8, 9, 8), colorize_rate_col=3,
                             row_tags=task_tags, on_row_click=_on_task_click,
                             selected_rows=left_sel["rows"],
                             rows_widget_store=task_widgets)

            def render_marks():
                """刷新任务表的选中高亮（不重建控件，性能好）。

                v6.3.4: 除了背景色，还要同步更新文字色、粗体、以及首列 ● 标记，
                否则只改背景时视觉区分度仍然不够。
                """
                try:
                    f_normal = ("Consolas", 11)
                    f_bold = ("Consolas", 11, "bold")
                    for ridx, widgets in task_widgets.items():
                        sel = ridx in left_sel["rows"]
                        excl = bool(task_tags and ridx < len(task_tags)
                                    and "excluded" in task_tags[ridx])
                        # 背景 / 文字色
                        if sel:
                            bg = D["sel"]             # 亮青高亮（对比度3.25）
                            fg = D["sel_text"]
                        elif excl:
                            bg = D["row2"]
                            fg = D["excluded"]
                        else:
                            bg = COLORS["bg_card"]
                            fg = D["text"]
                        for i, w in enumerate(widgets):
                            w.config(bg=bg)
                            # v6.3.4: 选中行粗体 + 白字，普通行恢复常规字体
                            w.config(font=(f_bold if sel else f_normal))
                            if sel or excl:
                                w.config(fg=fg)
                            elif i == 3 and "%" in str(task_rows[ridx][i]):
                                try:
                                    pct = float(str(task_rows[ridx][i]).replace("%", ""))
                                    w.config(fg=(D["ok"] if pct >= 50 else
                                                 D["mid"] if pct >= 20 else D["bad"]))
                                except Exception:
                                    w.config(fg=D["text"])
                            else:
                                w.config(fg=D["text"])
                        # v6.3.4: 首列加 ● / ○ 标记（色弱也能分辨选中状态）
                        if widgets:
                            base = str(task_rows[ridx][0])
                            if sel:
                                widgets[0].config(text="● " + base)
                            elif excl:
                                widgets[0].config(text="○ " + base)
                            else:
                                widgets[0].config(text=base)
                except Exception:
                    pass

            # 选中状态标签 + 确认按钮（放在任务表下方）
            left_btn_row = tk.Frame(f1, bg=COLORS["bg_card"])
            left_btn_row.pack(fill=tk.X, padx=14, pady=(6, 10))
            left_sel_lbl = tk.Label(left_btn_row, text="未选中任务",
                                    bg=COLORS["bg_card"], fg=D["muted"],
                                    font=("微软雅黑", 10, "bold"))
            left_sel_lbl.pack(side=tk.LEFT)

            # 右侧按钮（从右往左排）
            DarkButton(left_btn_row, text="恢复所选任务",
                       command=_confirmed_restore_tasks,
                       height=28, width=124, bg_color="#8e44ad").pack(side=tk.RIGHT, padx=(6, 0))
            DarkButton(left_btn_row, text="剔除所选任务",
                       command=_confirmed_exclude_tasks,
                       height=28, width=124, bg_color="#e67e22").pack(side=tk.RIGHT)

            def _refresh_left_buttons():
                try:
                    n = len(left_sel["rows"])
                    if n == 0:
                        left_sel_lbl.config(text="未选中任务（单击行选中，Ctrl 多选）",
                                            fg=D["muted"])
                    else:
                        left_sel_lbl.config(text="已选中 " + str(n) + " 个任务",
                                            fg=D["mid"])
                except Exception:
                    pass


            # ===== v6.4.2: 按条件批量剔除（任务名 + 日期 + 时间区间）=====
            cond_wrap = tk.LabelFrame(
                f1, text=" 按条件批量剔除 " , bg=COLORS["bg_card"],
                fg=D["text2"], font=("微软雅黑", 9), bd=1, relief=tk.GROOVE,
                labelanchor="nw")
            cond_wrap.pack(fill=tk.X, padx=14, pady=(0, 8))

            cond_inner = tk.Frame(cond_wrap, bg=COLORS["bg_card"])
            cond_inner.pack(fill=tk.X, padx=8, pady=6)

            def _mk_field(parent, label, width, default=""):
                box = tk.Frame(parent, bg=COLORS["bg_card"])
                box.pack(side=tk.LEFT, padx=(0, 10))
                tk.Label(box, text=label, bg=COLORS["bg_card"],
                         fg=D["muted"], font=("微软雅黑", 9)
                         ).pack(side=tk.LEFT, padx=(0, 4))
                ent = RoundEntry(box, width=width, font=("Consolas", 10))
                ent.pack(side=tk.LEFT)
                try:
                    ent.insert(0, default)
                except Exception:
                    pass
                return ent

            _e_task = _mk_field(cond_inner, "任务名", 18)
            _e_date = _mk_field(cond_inner, "日期", 11, "")
            _e_from = _mk_field(cond_inner, "从", 7, "")
            _e_to = _mk_field(cond_inner, "到", 7, "")

            def _get_ent(ent):
                try:
                    return ent.get().strip()
                except Exception:
                    return ""

            cond_msg = tk.Label(cond_wrap, text="", bg=COLORS["bg_card"],
                                fg=D["mid"], font=("微软雅黑", 9),
                                anchor=tk.W, justify=tk.LEFT)
            cond_msg.pack(fill=tk.X, padx=10, pady=(0, 4))

            def _do_batch_exclude():
                spec = rush_stats.parse_filter_spec(
                    task_name=_get_ent(_e_task),
                    date_str=_get_ent(_e_date),
                    time_from=_get_ent(_e_from),
                    time_to=_get_ent(_e_to))
                if not spec.get("valid"):
                    cond_msg.config(text="✗ " + spec.get("msg", "条件无效"),
                                    fg=D["bad"])
                    return
                recs_all = data.get("records", [])
                cur = rush_stats.load_excluded()
                new_set, n, _hits = rush_stats.batch_exclude(
                    recs_all, spec, cur)
                if n == 0:
                    cond_msg.config(text="没有记录匹配该条件", fg=D["muted"])
                    return
                if not messagebox.askyesno(
                        "确认批量剔除",
                        "将剔除 %d 条记录。\n\n任务名: %s\n日期: %s\n时间: %s ~ %s\n\n"
                        "确定继续？" % (
                            n,
                            spec.get("task_name") or "（不限）",
                            spec.get("date_str") or "（不限）",
                            _get_ent(_e_from) or "（不限）",
                            _get_ent(_e_to) or "（不限）"),
                        parent=dlg):
                    return
                rush_stats.save_excluded(new_set)
                cond_msg.config(text="✓ 已剔除 %d 条记录" % n, fg=D["ok"])
                refresh_all()

            def _do_batch_restore():
                spec = rush_stats.parse_filter_spec(
                    task_name=_get_ent(_e_task),
                    date_str=_get_ent(_e_date),
                    time_from=_get_ent(_e_from),
                    time_to=_get_ent(_e_to))
                if not spec.get("valid"):
                    cond_msg.config(text="✗ " + spec.get("msg", "条件无效"),
                                    fg=D["bad"])
                    return
                recs_all = data.get("records", [])
                cur = rush_stats.load_excluded()
                new_set, n, _hits = rush_stats.batch_restore(
                    recs_all, spec, cur)
                if n == 0:
                    cond_msg.config(text="没有记录匹配该条件", fg=D["muted"])
                    return
                rush_stats.save_excluded(new_set)
                cond_msg.config(text="✓ 已恢复 %d 条记录" % n, fg=D["ok"])
                refresh_all()

            cond_btn = tk.Frame(cond_wrap, bg=COLORS["bg_card"])
            cond_btn.pack(fill=tk.X, padx=8, pady=(0, 8))
            DarkButton(cond_btn, text="按条件剔除",
                       command=_do_batch_exclude, height=26, width=110,
                       bg_color="#e67e22").pack(side=tk.LEFT)
            DarkButton(cond_btn, text="按条件恢复",
                       command=_do_batch_restore, height=26, width=110,
                       bg_color="#8e44ad").pack(side=tk.LEFT, padx=(8, 0))
            tk.Label(cond_btn,
                     text="日期格式 YYYY-MM-DD，时间格式 HH:MM；留空表示不限",
                     bg=COLORS["bg_card"], fg=D["muted"],
                     font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(12, 0))
            _refresh_left_buttons()

            add_tab(f1, " ② 各任务成功率 ")
            # --- ③ 提前量区间 ---
            f2 = tk.Frame(left, bg=COLORS["bg_card"])
            adv_rows = []
            best = rush_stats.best_advance(data)
            for a in data.get("by_advance", []):
                mark = " ★" if best and a["advance"] == best["advance"] else ""
                note = "" if a.get("reliable") else "(样本少)"
                adv_rows.append([
                    f"{a['advance']}-{a['advance']+20}ms{mark}{note}",
                    str(a["total"]),
                    str(a["success"]),
                    f"{a['rate']}%",
                ])
            make_table(f2, ["提前量区间", "请求", "成功", "成功率"],
                       adv_rows, (30, 8, 8, 9), colorize_rate_col=3)
            add_tab(f2, " ③ 提前量成功率 ")
            # --- ④ 风控时段（v6.4.1: 按"抢码场次"分组，不再按自然小时）---
            f3 = tk.Frame(left, bg=COLORS["bg_card"])
            hour_rows = []
            for h in rush_stats.risk_hours(data)[:24]:
                _lab = h.get("label") or h.get("hour", "?")
                hour_rows.append([
                    str(_lab),
                    str(h["total"]),
                    str(h["risk"]),
                    f"{h['success_rate']}%",
                ])
            make_table(f3, ["抢码场次", "请求", "风控", "成功率"],
                       hour_rows, (24, 8, 8, 9), colorize_rate_col=3)
            tk.Label(f3,
                     text="固定 4 个场次（窗口=目标前后各20分钟）：\n"
                          "  00点场 23:40~00:20    01点场 00:40~01:20\n"
                          "  02点场 01:40~02:20    18点场 17:40~18:20\n"
                          "其余时间全部归「其他时段」",
                     bg=COLORS["bg_card"], fg=D["muted"],
                     font=("微软雅黑", 9), anchor=tk.W, justify=tk.LEFT,
                     wraplength=660).pack(fill=tk.X, padx=14, pady=(6, 10))
            add_tab(f3, " ④ 风控高发时段 ")

            # --- ⑤ 库存窗口（v6.4.4：明细为主体，汇总精简为一行）---
            # 用户反馈："明细样本中的数据才是需要观察的，把它移到上面去"
            # 设计：任务行 + 缩进的每场明细行，合成一张表。
            # 汇总只保留「典型告罄」（跨场中位数，抗单次异常）。
            f5 = tk.Frame(left, bg=COLORS["bg_card"])
            wins = []
            try:
                wins = rush_stats.stock_windows(data)
            except Exception:
                wins = []

            if wins:
                _n_fast = sum(1 for w in wins
                              if w.get("first_med") is not None
                              and w["first_med"] <= 10)
                _n_sess_total = sum(int(w.get("sessions") or 0) for w in wins)
                _top = tk.Frame(f5, bg=COLORS["bg_card"])
                _top.pack(fill=tk.X, padx=14, pady=(10, 4))
                tk.Label(_top, text="库存窗口分析", bg=COLORS["bg_card"],
                         fg=D["text2"], font=("微软雅黑", 11, "bold")
                         ).pack(side=tk.LEFT)
                tk.Label(_top,
                         text="  %d 个任务 / %d 场观测，%d 个任务在10秒内告罄"
                              % (len(wins), _n_sess_total, _n_fast),
                         bg=COLORS["bg_card"], fg=D["muted"],
                         font=("微软雅黑", 9)).pack(side=tk.LEFT, pady=(3, 0))

                # 表头
                _W5 = (4, 1, 1, 1, 2)
                _M5 = (230, 62, 62, 62, 120)
                _hd = tk.Frame(f5, bg=COLORS["bg_input"])
                _hd.pack(fill=tk.X, padx=14)
                for _i, _t in enumerate(("任务 / 每场明细", "中位数", "平均数", "最小值", "结论")):
                    _hd.grid_columnconfigure(_i, weight=_W5[_i], minsize=_M5[_i])
                    tk.Label(_hd, text=_t, bg=COLORS["bg_input"], fg=D["text2"],
                             font=("微软雅黑", 9, "bold"), anchor=tk.W
                             ).grid(row=0, column=_i, sticky="w", padx=4, pady=5)

                def _color_of(v):
                    if v is None:
                        return D["muted"]
                    if v <= 10:
                        return D["bad"]
                    if v <= 60:
                        return D["mid"]
                    return D["ok"]

                for w in wins:
                    _fm = w.get("first_med")
                    _wc = _color_of(_fm)
                    # ---- 任务行 ----
                    _rw = tk.Frame(f5, bg=COLORS["bg_card"])
                    _rw.pack(fill=tk.X, padx=14, pady=(6, 0))
                    _fa = w.get("first_avg")
                    _fn = w.get("first_min")
                    _vals = (
                        ("● " + w["task"][:26], D["text"]),
                        (("—" if _fm is None else "%.1f秒" % _fm), _wc),
                        (("—" if _fa is None else "%.1f秒" % _fa), _color_of(_fa)),
                        (("—" if _fn is None else "%.1f秒" % _fn), _color_of(_fn)),
                        (w.get("verdict", ""), _wc),
                    )
                    for _i, (_v, _c) in enumerate(_vals):
                        _rw.grid_columnconfigure(_i, weight=_W5[_i], minsize=_M5[_i])
                        tk.Label(_rw, text=str(_v), bg=COLORS["bg_card"], fg=_c,
                                 font=("微软雅黑", 10, "bold"), anchor=tk.W
                                 ).grid(row=0, column=_i, sticky="w", padx=4, pady=2)
                    # ---- 每场明细行（缩进，等宽字体保证对齐）----
                    for _s in (w.get("per_session") or [])[:8]:
                        _seg = "    %s  %-8s  首次%+5.1fs" % (
                            _s["date"][5:], _s["label"], _s["first"])
                        if _s["n"] >= 2:
                            _seg += "  末次%+5.1fs" % _s["last"]
                        _seg += "  (%d次)" % _s["n"]
                        tk.Label(f5, text=_seg, bg=COLORS["bg_card"],
                                 fg=D["muted"], font=("Consolas", 9),
                                 anchor=tk.W
                                 ).pack(fill=tk.X, padx=14, pady=0)
                    _nf = len(w.get("per_session") or [])
                    if _nf > 8:
                        tk.Label(f5, text="    ...另有 %d 场未显示" % (_nf - 8),
                                 bg=COLORS["bg_card"], fg=D["muted"],
                                 font=("Consolas", 9), anchor=tk.W
                                 ).pack(fill=tk.X, padx=14)

                _note5 = ("说明：中位数/平均数/最小值 都是统计该任务各场次"
                          "「首次出现 75255 库存已经使用完」的偏移。",
                          "0秒 = 开抢瞬间即空；数值越大说明库存越耐用。",
                          "明细行格式：日期 场次 首次偏移 [末次偏移] (该场观测次数)。",
                          "中位数抗单次异常，最小值代表最坏情况（最快被抢空）。")
                tk.Label(f5, text=_note5,
                         bg=COLORS["bg_card"], fg=D["muted"],
                         font=("微软雅黑", 9), anchor=tk.W, justify=tk.LEFT,
                         wraplength=690).pack(fill=tk.X, padx=14, pady=(10, 8))
            else:
                tk.Label(f5, text="暂无库存耗尽记录（75255）",
                         bg=COLORS["bg_card"], fg=D["muted"],
                         font=("微软雅黑", 10), anchor=tk.W
                         ).pack(fill=tk.X, padx=14, pady=20)
                _note5b = ("当某个任务返回「库存已经使用完」时，"
                           "这里会出现该任务的库存窗口统计。")
                tk.Label(f5, text=_note5b,
                         bg=COLORS["bg_card"], fg=D["muted"],
                         font=("微软雅黑", 9), anchor=tk.W, justify=tk.LEFT,
                         wraplength=690).pack(fill=tk.X, padx=14)
            add_tab(f5, " ⑤ 库存窗口 ")

            # v6.4.2: 恢复重建前的标签页（避免剔除操作后跳回第一个）
            try:
                if nb2 is not None and len(nb2.tabs()) > 0:
                    _restore = min(_tab_state.get("index", 0), len(nb2.tabs()) - 1)
                    if _restore > 0:
                        nb2.select(nb2.tabs()[_restore])
            except Exception:
                pass

            return nb2

        # ---- 右侧：明细记录（可手动剔除）----
        right = tk.Frame(body, bg=COLORS["bg_card"], highlightthickness=1,
                         highlightbackground=COLORS["border"])
        body.add(right, minsize=560, width=900)

        right_head = tk.Frame(right, bg=COLORS["bg_card"])
        right_head.pack(fill=tk.X, padx=14, pady=(12, 6))
        tk.Label(right_head, text="📋 明细记录", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 10, "bold")
                 ).pack(side=tk.LEFT)
        detail_count_lbl = tk.Label(right_head, text="", bg=COLORS["bg_card"],
                                    fg=D["muted"], font=("微软雅黑", 11))
        detail_count_lbl.pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(right, text="选中记录（Ctrl 多选 / Shift 连选），再点底部「剔除所选」；勾选「显示已剔除记录」可恢复",
                 bg=COLORS["bg_card"], fg=D["muted"],
                 font=("微软雅黑", 9), anchor=tk.W
                 ).pack(fill=tk.X, padx=10, pady=(0, 4))

        # 明细列表（Treeview 更省空间、支持滚动）
        detail_frame = tk.Frame(right, bg=COLORS["bg_card"])
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        try:
            cols = ("ts", "task", "award", "result", "rare", "state")
            tree = ttk.Treeview(detail_frame, columns=cols, show="headings",
                                height=20, selectmode="extended")
            # v6.4.2: 列宽改为自适应（stretch=True），不再固定
            # 原因：DPI 缩放 1.4985 下，窗口实际物理宽度比请求值小，
            # 固定列宽会导致后面的列被挤出可视区。
            # 现在设 minwidth 保证最小可读，stretch 让列填满可用宽度。
            # v6.4.2: 列宽按实测可用空间(约1150px)重新配比，保证 6 列全可见
            headings = [
                ("ts", "时间", 155, 130), ("task", "任务名称", 285, 180),
                ("award", "奖励", 170, 110), ("result", "结果", 78, 62),
                ("rare", "稀有", 90, 66), ("state", "状态", 90, 66),
            ]
            for cid, txt, wpx, minw in headings:
                tree.heading(cid, text=txt)
                tree.column(cid, width=wpx, minwidth=minw, anchor=tk.W,
                            stretch=True)
            vsb = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            # v6.3.1 关键修复：Treeview 必须显式设置默认前景色，
            # 否则 Windows 用系统深色文字，在深色背景上几乎看不见。
            try:
                style = ttk.Style()
                style.configure("Dash.Treeview",
                                background=D["row2"],
                                fieldbackground=D["row2"],
                                foreground=D["text"],
                                rowheight=34,
                                font=("微软雅黑", 11))
                style.configure("Dash.Treeview.Heading",
                                background=COLORS["bg_input"],
                                foreground=D["text2"],
                                font=("微软雅黑", 11, "bold"))
                # v6.3.4: 选中行用亮青高亮（原来 #0f3460 对比度仅1.27 看不出）
                style.map("Dash.Treeview",
                          background=[("selected", D["sel"])],
                          foreground=[("selected", D["sel_text"])])
                tree.configure(style="Dash.Treeview")
            except Exception:
                pass
            # 交替行底色（两行都显式给前景色，保证可读）
            tree.tag_configure("odd", background=D["row1"], foreground=D["text"])
            tree.tag_configure("even", background=D["row2"], foreground=D["text"])
            tree.tag_configure("excluded", background=D["row2"], foreground=D["excluded"])
            tree.tag_configure("succ", background=D["row1"], foreground=D["ok"])
        except Exception:
            tree = None

        # ---- 渲染主函数 ----
        def render():
            """按当前过滤条件重算数据并刷新界面。"""
            try:
                rare_only = bool(state["rare_only"].get())
                show_excl = bool(state["show_excluded"].get())
            except Exception:
                rare_only, show_excl = False, False

            # v6.5.1: 传入时间范围（全部/昨天/近3天/自定义）
            _rt = str(state["date_range"].get() or rush_stats.RANGE_ALL)
            _cf = str(state["custom_from"].get() or "").strip()
            _ct = str(state["custom_to"].get() or "").strip()
            data = rush_stats.dashboard(rare_only=rare_only,
                                       include_excluded=show_excl,
                                       date_range=_rt,
                                       custom_from=_cf,
                                       custom_to=_ct)

            f = data.get("filters") or {}
            ov = data.get("overview") or {}

            if not f.get("raw_total"):
                summary_lbl.config(
                    text="暂无抢码记录。抢码后这里会自动生成统计数据。",
                    fg=D["muted"])
            else:
                rate = ov.get("success_rate", 0)
                # v6.3.1: 高对比度
                rate_color = D["ok"] if rate >= 50 else (
                    D["mid"] if rate >= 20 else D["bad"])
                parts = [
                    f"总记录 {f.get('raw_total', 0)}",
                    f"纳入统计 {data.get('total', 0)}",
                ]
                if f.get("excluded"):
                    parts.append(f"手动剔除 {f['excluded']}")
                if f.get("non_rare"):
                    parts.append(f"非稀有剔除 {f['non_rare']}")
                if rare_only:
                    parts.append("【仅稀有模式】")
                # v6.4.0: 综合抢码状态评分
                try:
                    _snap = rush_stats.score_snapshot(data)
                    _lv = {"ok": "优秀", "mid": "良好", "bad": "偏低",
                           "muted": "未知"}.get(_snap.get("level_color"), "未知")
                    _score_text = (f"　|　抢码状态 {_snap.get('total_score', 0)}分"
                                   f"（{_snap.get('level', '')}）")
                except Exception:
                    _score_text = ""
                # v6.4.0: 精简摘要，避免过长被截断（原文字超过窗口宽度）
                _sum_parts = [
                    f"总 {f.get('raw_total', 0)} 条",
                    f"纳入 {data.get('total', 0)}",
                ]
                if f.get("excluded"):
                    _sum_parts.append(f"剔除 {f['excluded']}")
                if f.get("non_rare"):
                    _sum_parts.append(f"非稀有 {f['non_rare']}")
                _sum_parts.append(f"成功 {ov.get('success', 0)}")
                _sum_parts.append(f"成功率 {rate}%")
                _sum_parts.append(f"风控 {ov.get('risk_count', 0)}次")
                _score_s = ""
                try:
                    _snap2 = rush_stats.score_snapshot(data)
                    _score_s = f"抢码状态 {_snap2['total_score']}分({_snap2['level']})"
                except Exception:
                    pass
                if _score_s:
                    _sum_parts.append(_score_s)
                summary_lbl.config(text="　|　".join(_sum_parts), fg=rate_color)

            build_tables(data)

            # 刷新明细列表
            if tree is not None:
                for item in tree.get_children():
                    tree.delete(item)
                recs = data.get("records", [])
                detail_count_lbl.config(text=f"共 {len(recs)} 条")
                for idx, r in enumerate(recs):
                    rare_txt = {True: "稀有", False: "非稀有", None: "?"}.get(r.get("rare"), "?")
                    res = r.get("result", "")
                    res_txt = {"success": "成功", "already": "已领", "failed": "失败",
                               "skipped": "跳过"}.get(res, res)
                    tags = ["odd" if idx % 2 else "even"]
                    if r.get("excluded"):
                        tags.append("excluded")
                    elif res in ("success", "already"):
                        tags.append("succ")
                    ts_short = r.get("ts", "")[5:]   # 去掉年份
                    tree.insert("", tk.END, iid=str(idx), tags=tuple(tags),
                                values=(ts_short, r.get("task_name", "")[:30],
                                        r.get("award", "")[:16], res_txt,
                                        rare_txt,
                                        "已剔除" if r.get("excluded") else "正常"))

        # ---- v6.3.3: 选中 + 确认后才剔除（不再双击直接生效）----

        # v6.5.1: 关键修复 —— render_holder["fn"] 之前从未赋值（一直是 None），
        # 导致切换时间范围/勾选过滤时 render_holder["fn"]() 永远不会执行。
        render_holder["fn"] = render
        def _selected_indices():
            """取当前明细列表选中的行号列表（支持多选）。"""
            if tree is None:
                return []
            out = []
            for iid in tree.selection():
                try:
                    out.append(int(iid))
                except Exception:
                    pass
            return out

        def _current_records():
            """按当前过滤条件取明细记录列表。"""
            d = rush_stats.dashboard(rare_only=bool(state["rare_only"].get()),
                                    include_excluded=bool(state["show_excluded"].get()),
                                    date_range=str(state["date_range"].get()
                                                   or rush_stats.RANGE_ALL),
                                    custom_from=str(state["custom_from"].get() or ""),
                                    custom_to=str(state["custom_to"].get() or ""))
            return d.get("records", [])

        def exclude_selected():
            """剔除【选中的】记录（多选支持，需二次确认）。"""
            idxs = _selected_indices()
            if not idxs:
                messagebox.showwarning("未选择",
                                       "请先在明细列表中选中要剔除的记录\\n\\n"
                                       "（按住 Ctrl 可多选，Shift 可连选）",
                                       parent=dlg)
                return
            recs = _current_records()
            targets = [recs[i] for i in idxs if 0 <= i < len(recs)]
            if not targets:
                messagebox.showwarning("提示", "选中的记录已失效，请刷新后重试", parent=dlg)
                return
            lines = []
            for r in targets[:6]:
                lines.append("  · " + str(r.get("ts", "")) + " " + str(r.get("task_name", ""))[:24])
            preview = "\n".join(lines)
            if len(targets) > 6:
                preview += "\n  · ... 共 " + str(len(targets)) + " 条"
            ok = messagebox.askyesno(
                "确认剔除",
                "确定要剔除以下 " + str(len(targets)) + " 条记录吗？\n\n"
                + preview
                + "\n\n剔除后不参与统计，可随时恢复。",
                parent=dlg)
            if not ok:
                return
            excl = rush_stats.load_excluded()
            new_set = set(excl)
            for r in targets:
                new_set.add(rush_stats.make_record_key(r))
            rush_stats.save_excluded(new_set)
            self.nm_log("剔除 " + str(len(targets)) + " 条记录（手动选择）")
            render()

        def restore_selected():
            """恢复【选中的】已剔除记录（多选，需二次确认）。"""
            idxs = _selected_indices()
            if not idxs:
                messagebox.showwarning("未选择",
                                       "请先选中要恢复的记录\n\n"
                                       "（需勾选「显示已剔除记录」才能看到被剔除的条目）",
                                       parent=dlg)
                return
            recs = _current_records()
            targets = [recs[i] for i in idxs if 0 <= i < len(recs)]
            excl = rush_stats.load_excluded()
            removable = [r for r in targets if rush_stats.make_record_key(r) in excl]
            if not removable:
                messagebox.showinfo("提示", "选中的记录都没有被剔除，无需恢复", parent=dlg)
                return
            lines = []
            for r in removable[:6]:
                lines.append("  · " + str(r.get("ts", "")) + " " + str(r.get("task_name", ""))[:24])
            preview = "\n".join(lines)
            if len(removable) > 6:
                preview += "\n  · ... 共 " + str(len(removable)) + " 条"
            ok = messagebox.askyesno(
                "确认恢复",
                "确定要恢复以下 " + str(len(removable)) + " 条记录吗？\n\n" + preview,
                parent=dlg)
            if not ok:
                return
            new_set = set(excl)
            for r in removable:
                new_set.discard(rush_stats.make_record_key(r))
            rush_stats.save_excluded(new_set)
            self.nm_log("恢复 " + str(len(removable)) + " 条记录")
            render()

        def on_selection_change(_e=None):
            """选中变化时更新底部计数与按钮状态。"""
            try:
                n = len(_selected_indices())
                if n == 0:
                    sel_lbl.config(text="未选中记录", fg=D["muted"])
                else:
                    sel_lbl.config(text="已选中 " + str(n) + " 条", fg=D["mid"])
            except Exception:
                pass

        if tree is not None:
            tree.bind("<<TreeviewSelect>>", on_selection_change)


        # 复选框变化时重渲染
        try:
            state["rare_only"].trace_add("write", lambda *a: render())
            state["show_excluded"].trace_add("write", lambda *a: render())
        except Exception:
            pass

        # ---- 底部按钮（v6.3.3: 选中+确认模式）----

        tip_text = ("提示：在明细列表中选中记录（Ctrl 多选 / Shift 连选），"
                    "再点「剔除所选」；需勾选「显示已剔除记录」才能恢复")
        tk.Label(foot, text=tip_text, bg=COLORS["bg_dark"], fg=D["muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        # 选中状态提示（随选择实时更新）
        sel_lbl = tk.Label(foot, text="未选中记录", bg=COLORS["bg_dark"],
                           fg=D["muted"], font=("微软雅黑", 11, "bold"))
        sel_lbl.pack(side=tk.LEFT, padx=(16, 0))

        def clear_all_excluded():
            """一键清空所有手动剔除。"""
            n = len(rush_stats.load_excluded())
            if not n:
                messagebox.showinfo("提示", "当前没有手动剔除的记录", parent=dlg)
                return
            if not messagebox.askyesno(
                    "确认清空",
                    "确定要清空全部 " + str(n) + " 条手动剔除记录吗？\n\n"
                    "清空后这些记录会重新参与统计。",
                    parent=dlg):
                return
            rush_stats.save_excluded(set())
            self.nm_log("已清空全部手动剔除记录（" + str(n) + " 条）")
            render()

        # 右侧按钮：从右往左排
        DarkButton(foot, text="刷新", command=render, tip="刷新抢码统计面板数据",
                   height=30, width=76, bg_color="#2980b9").pack(side=tk.RIGHT, padx=(6, 0))
        DarkButton(foot, text="清空全部剔除", command=clear_all_excluded,
                   height=30, width=124, bg_color="#c0392b").pack(side=tk.RIGHT, padx=(6, 0))
        DarkButton(foot, text="恢复所选", command=restore_selected,
                   height=30, width=100, bg_color="#8e44ad").pack(side=tk.RIGHT, padx=(6, 0))
        DarkButton(foot, text="剔除所选", command=exclude_selected,
                   height=30, width=100, bg_color="#e67e22").pack(side=tk.RIGHT)

        render()



        render()

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
            messagebox.showwarning("提示", "请先选择关机模式（定时关机或延时关机）", parent=self.winfo_toplevel())
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
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）", parent=self.winfo_toplevel())
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
                messagebox.showwarning("提示", "请输入有效的延时分钟数（大于0）", parent=self.winfo_toplevel())
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
            # v6.2.0 延迟构建：首次进入新模式时才真正创建 UI（省约1.2秒启动时间）
            if not getattr(self, "_new_mode_ui_built", False):
                try:
                    self.build_new_mode_ui()
                    self._new_mode_ui_built = True
                    # 构建后应用保存的 UI 设置
                    try:
                        self.nm_load_ui_settings()
                    except Exception:
                        pass
                except Exception as e:
                    self.log(f"构建精准抢码界面失败: {e}")
                    import traceback
                    self.log(traceback.format_exc())
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
                                           height=32, bg_color=COLORS["accent"], text_color="#000000", tip="创建一个新的任务组（一组任务共享同一首发时间）")
        self.nm_new_group_btn.pack(side=tk.LEFT, padx=5)
        # v6.2.1: 任务组改名
        self.nm_rename_group_btn = DarkButton(grow1, text="✎ 改名", command=self.nm_rename_group,
                                              height=32, bg_color="#2980b9", text_color="#ffffff", tip="修改当前任务组的名称")
        self.nm_rename_group_btn.pack(side=tk.LEFT, padx=5)
        self.nm_del_group_btn = DarkButton(grow1, text="删除当前组", command=self.nm_del_group,
                                           height=32, bg_color="#c0392b", text_color="#ffffff", tip="删除当前选中的任务组（含组内所有任务）")
        self.nm_del_group_btn.pack(side=tk.LEFT, padx=5)

        # v6.2.0: 抢码预案（一键切换整套配置）
        self.nm_preset_btn = DarkButton(grow1, text="📦 预案", command=self.open_preset_manager,
                                        height=32, bg_color="#8e44ad", text_color="#ffffff", tip="打开预案管理：保存/载入整套抢码配置")
        self.nm_preset_btn.pack(side=tk.LEFT, padx=(15, 0))

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
                                        height=32, bg_color="#8e44ad", text_color="#ffffff", tip="手动输入 task_id 或活动网址来添加任务（官方任务表里没有的活动也能加）")
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
                                          text_color="#000000", tip="把上方选好的任务加入当前任务组")
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
                                           text_color="#ffffff", tip="批量查询组内所有任务的库存与领取状态（圆点颜色随之变化）")
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
                                      height=44, bg_color=COLORS["accent"], text_color="#000000", tip="启动当前任务组：按目标时间精准首发，失败后按间隔重试")
        self.nm_start_btn.pack(side=tk.LEFT, padx=6)
        self.nm_stop_btn = DarkButton(ctrl_inner, text="⏹ 停止", command=self.nm_stop_rush,
                                     height=44, bg_color="#c0392b", text_color="#ffffff", tip="停止当前任务组的抢码")
        self.nm_stop_btn.pack(side=tk.LEFT, padx=6)
        self.nm_stop_btn.set_state("disabled")
        self.nm_sync_time_btn = DarkButton(ctrl_inner, text="🕐 同步系统时间", command=self.nm_sync_system_time,
                                           height=44, bg_color=COLORS["accent_hover"], text_color="#000000", tip="校准系统时钟（用 Set-Date 精确设置，偏差可降到 ±5ms）")
        self.nm_sync_time_btn.pack(side=tk.LEFT, padx=6)
        self.nm_query_time_btn = DarkButton(ctrl_inner, text="📊 查询时间状态", command=self.nm_query_time_status,
                                            height=44, bg_color="#2d3436", text_color=COLORS["text_primary"], tip="查看 NTP 偏差、根分散、自动校正能力判定")
        self.nm_query_time_btn.pack(side=tk.LEFT, padx=6)
        self.nm_fix_time_btn = DarkButton(ctrl_inner, text="🔧 修复时间服务", command=self.nm_fix_time_service,
                                          height=44, bg_color="#e67e22", text_color="#ffffff", tip="重建 Windows 时间服务（恢复自动同步能力，需管理员权限）")
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
        DarkButton(scheduler_btn_frame, text="▶ 启动选中组", command=self.nm_scheduler_start_selected, tip="在调度器表格里启动勾选的多个任务组",
                  height=44, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="⏹ 停止选中组", command=self.nm_scheduler_stop_selected, tip="停止调度器表格里勾选的任务组",
                  height=44, bg_color="#c0392b", text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="⏹ 停止全部", command=self.nm_stop_rush, tip="停止调度器里的所有任务组",
                  height=44, bg_color="#e74c3c", text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        DarkButton(scheduler_btn_frame, text="🔄 刷新", command=self.nm_update_scheduler, tip="刷新调度器表格（更新剩余时间与进度）",
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

    def nm_manual_rush_once(self, task):
        """手动抢领一次（v6.6.0 新增，点击组内任务的状态圆点触发）。

        与定时抢码的区别：
          - 不做预热等待、不计算提前量，立即发一次领取请求
          - 用任务自带的 account_name 找账户，不强依赖预选
          - 全程后台线程，界面不卡
        适合：补抢、验证任务能否领取、临时手动尝试。
        """
        import threading

        def _log(msg):
            try:
                self.nm_log(msg)
            except Exception:
                pass

        try:
            tid = task.get("task_id", "")
            tname = task.get("name", "")
        except Exception:
            return

        _log("=" * 52)
        _log("[手动抢领] 任务: %s" % tname)
        _log("[手动抢领] task_id: %s" % tid)
        _log("=" * 52)

        def _worker():
            try:
                self._manual_rush_once_worker(task, _log)
            except Exception as e:
                import traceback
                _log("  [X] 手动抢领异常: %s" % e)
                try:
                    _log(traceback.format_exc()[:500])
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _manual_rush_once_worker(self, task, _log):
        """手动抢领的实际工作（后台线程）。"""
        tid = task.get("task_id", "")
        tname = task.get("name", "")
        acc_name = task.get("account_name", "")

        # ---- 1) 找账户 ----
        _log("[1/4] 查找账户...")
        account = None
        try:
            if acc_name:
                account = self.account_mgr.get_account(acc_name)
            if not account:
                accs = getattr(self.account_mgr, "accounts", []) or []
                if accs:
                    account = accs[0]
                    _log("  任务未指定账户，改用第一个: %s"
                         % account.get("name", ""))
        except Exception as e:
            _log("  查找账户异常: %s" % e)

        if not account:
            _log("  [X] 没有可用账户，无法抢领")
            _log("=" * 52)
            self.winfo_toplevel().after(0, lambda: messagebox.showwarning(
                "无法抢领", "没有可用账户。\n\n请先到「账户管理」添加账户。",
                parent=self.winfo_toplevel()))
            return
        _log("  账户: %s" % account.get("name", ""))

        # ---- 2) 查任务信息拿 act_id ----
        _log("[2/4] 查询任务信息（act_id）...")
        cookies = cookies_from_account(account)
        csrf = account.get("bili_jct", "")
        info = None
        try:
            info, msg = get_mission_info(tid, cookies)
            if info:
                _log("  act_id: %s" % info.get("act_id", ""))
            else:
                _log("  查询失败: %s，用备用 act_id" % msg)
        except Exception as e:
            _log("  查询异常: %s" % e)

        if not info:
            version = task.get("version", "")
            backup = VERSION_DEFAULT_ACT_ID.get(version, "")
            info = {
                "act_id": backup,
                "act_name": tname,
                "task_name": tname,
                "reward_info": {"award_name": task.get("award", "")},
            }
            _log("  使用备用 act_id: %s" % backup)

        # ---- 3) 发领取请求 ----
        _log("[3/4] 发送领取请求...")
        t0 = time.time()
        try:
            status, result, data = receive_reward(tid, info, cookies, csrf)
        except Exception as e:
            _log("  [X] 请求异常: %s" % e)
            _log("=" * 52)
            return
        latency = (time.time() - t0) * 1000

        _log("  结果: %s   耗时: %.0fms" % (status, latency))
        _log("  响应: %s" % str(result)[:120])

        # ---- 4) 记录统计 ----
        try:
            _code = ""
            _msg = str(result or "")
            if _msg.startswith("[") and "]" in _msg:
                _code = _msg[1:_msg.index("]")]
            rush_stats.record(
                task_id=tid,
                task_name=tname,
                account=account.get("name", ""),
                act_id=(info or {}).get("act_id", ""),
                result=status,
                code=_code,
                message=_msg,
                latency_ms=latency,
                award=task.get("award", ""),
                version=task.get("version", ""),
                window_seconds=int(task.get("window_seconds", 0) or 0),
                priority=int(task.get("priority", 0) or 0),
            )
        except Exception:
            pass

        # ---- 5) 结果反馈 ----
        _log("[4/4] 完成")
        ok = status in ("success", "already")
        if ok:
            _log("  [OK] 抢领成功！")
        else:
            _log("  [X] 抢领未成功（%s）" % status)
        _log("=" * 52)

        def _popup():
            try:
                if ok:
                    messagebox.showinfo(
                        "抢领成功",
                        "任务「%s」抢领成功！\n\n%s\n耗时 %.0fms"
                        % (tname, str(result)[:80], latency),
                        parent=self.winfo_toplevel())
                else:
                    messagebox.showwarning(
                        "抢领未成功",
                        "任务「%s」抢领未成功。\n\n%s\n耗时 %.0fms"
                        % (tname, str(result)[:80], latency),
                        parent=self.winfo_toplevel())
            except Exception:
                pass
        self.winfo_toplevel().after(0, _popup)


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
            # v6.6.0: 点击圆点 = 立即手动抢领一次
            try:
                status_lbl.configure(cursor="hand2")
                status_lbl.bind("<Button-1>",
                                lambda e, t=task: self.nm_manual_rush_once(t))
            except Exception:
                pass
            # 给状态圆点添加tooltip
            try:
                ToolTip(status_lbl, status_text + "（点击可立即抢领一次）")
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
                       height=24, width=30, bg_color=COLORS["bg_input"], tip="上移：提高该任务在组内的执行优先级",
                       text_color=COLORS["text_primary"], compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="↓", command=lambda tid=task["task_id"]: self.nm_move_task(tid, 1),
                       height=24, width=30, bg_color=COLORS["bg_input"], tip="下移：降低该任务在组内的执行优先级",
                       text_color=COLORS["text_primary"], compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="✎", command=lambda t=task: self.nm_edit_task(t),
                       height=24, width=30, bg_color="#3498db", tip="编辑该任务的窗口期、账户等参数",
                       text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="🔍", command=lambda t=task: self.nm_query_single_task(t),
                       height=24, width=34, bg_color="#f39c12", tip="查询该任务当前的库存与领取状态",
                       text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=1)
            DarkButton(btn_frame, text="×", command=lambda tid=task["task_id"]: self.nm_remove_task(tid),
                       height=24, width=30, bg_color="#c0392b", tip="从当前任务组中移除该任务",
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
        """更新任务状态并刷新UI（在主线程中调用）

        v6.4.5: 同时把查询结果写盘持久化（rush_stats.update_task_status），
        这样重启程序后仍能看到上次查询结果，抢码界面也能据此快捷勾选。
        """
        # ---- 持久化（无论是否当前分组都存，供仪表盘/快捷选中使用）----
        try:
            import rush_stats as _rs
            _res = dict(result or {})
            _res["task_name"] = str(task.get("name", "") or "")
            _res["act_id"] = str(task.get("act_id", "") or "")
            _res["version"] = str(task.get("version", "") or "")
            _rs.update_task_status(
                task.get("task_id", ""),
                task.get("account_name", ""),
                _res)
        except Exception:
            pass

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

    def refresh_version_combo(self):
        """刷新旧模式的版本下拉框（v6.4.9）。

        问题：旧模式 version_combo 在 UI 构建时只读一次 ALL_TASKS（第385行），
        之后在查询中心新建的版本集合不会出现在这里。
        （新模式有 nm_refresh_version_combo，旧模式一直没有）

        修复：提供主动刷新，并尽量保持当前选择。
        """
        try:
            import tasks_config as _tc
            try:
                names = _tc.all_version_names()
            except Exception:
                names = sorted(set(t["version"] for t in ALL_TASKS))
            if not names:
                return
            cur = ""
            try:
                cur = str(self.version_var.get() or "")
            except Exception:
                pass
            self.version_combo.config(values=names)
            # 保持原选择；原值失效则选第一个
            if cur and cur in names:
                self.version_var.set(cur)
            else:
                self.version_var.set(names[0])
            # 联动刷新期数/类型/任务
            self.on_version_change()
        except Exception:
            pass

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
            messagebox.showwarning("提示", "请先选择任务", parent=self.winfo_toplevel())
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户", parent=self.winfo_toplevel())
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
                # v6.3.0: 记录奖励与版本，供"稀有奖励"筛选统计
                award=task.get("award", ""),
                version=task.get("version", ""),
            )
        except Exception:
            pass

        if status in ("success", "already"):
            return True, result, data
        return False, result, None


    # ============================================================
    # v6.4.6：查询结果独立窗口（用户需求：做成跟仪表盘一样的界面）
    # ============================================================

    # ============================================================
    # v6.4.7：任务查询中心（整合两个查询窗口，用户需求）
    #
    # 用户：「我需要把这两个按钮整合进一个界面，
    #       查询任务可以手动控制开始和结束，在界面里面」
    #
    # 一个窗口包含：
    #   - 顶部：账户选择 + 【开始查询】【停止查询】按钮 + 进度
    #   - 中部：实时查询日志（滚动）
    #   - 下部：任务状态表格（可抢高亮）+ 完成情况统计
    #   - 底部：全部加入任务组 / 刷新 / 关闭
    # ============================================================


    def open_task_center(self):
        """任务查询中心 v6.4.8。

        需求确认（用户澄清）：
          · 「任务组」= ALL_TASKS 里的 version 这一层（如「鸣潮3.7」全部任务集合）
          · 手动创建 = 创建一个新的版本集合（可自定义名称，默认「已完成任务」）
          · 期数固定「已完成」、类型固定「已完成任务」
          · 查询到的任务加入【版本集合】，不是新模式抢码组
          · 默认只显示可抢任务
          · 记忆功能：账户/版本集合/过滤状态要保留
        """
        try:
            import rush_stats as _rs
            import tasks_config as _tc
        except Exception:
            return

        cfg = {}
        try:
            cfg = _rs.load_center_settings()
        except Exception:
            cfg = {"only_claimable": True, "account": "",
                   "version": _tc.DONE_VERSION if hasattr(_tc, "DONE_VERSION") else ""}

        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("🔍 任务查询中心")
        dlg.configure(bg=COLORS["bg_dark"])
        try:
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            w = int(sw * 0.68)
            h = int(sh * 0.84)
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2 - 10)
            dlg.geometry(f"{w}x{h}+{x}+{y}")
            dlg.minsize(1020, 660)
        except Exception:
            dlg.geometry("1240x860")

        foot = tk.Frame(dlg, bg=COLORS["bg_dark"])
        foot.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 10))

        head = tk.Frame(dlg, bg=COLORS["bg_card"])
        head.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(12, 6))
        tr = tk.Frame(head, bg=COLORS["bg_card"])
        tr.pack(fill=tk.X, padx=14, pady=(10, 2))
        tk.Label(tr, text="🔍 任务查询中心", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold")
                 ).pack(side=tk.LEFT)
        tk.Label(tr,
                 text="  查询所有活动任务 -> 加入版本集合"
                      "（版本集合=图二「版本」下拉框那一层）",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, pady=(4, 0))

        # ===== 第一行：账户 + 版本集合 + 新建/删除 =====
        row1 = tk.Frame(head, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, padx=14, pady=(4, 6))

        tk.Label(row1, text="查询账户：", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)
                 ).pack(side=tk.LEFT)
        acc_var = tk.StringVar()
        acc_names = []
        try:
            acc_names = [a["name"] for a in self.account_mgr.accounts]
        except Exception:
            pass
        _sa = str(cfg.get("account") or "")
        acc_var.set(_sa if (_sa and _sa in acc_names)
                    else (acc_names[0] if acc_names else ""))
        RoundCombobox(row1, textvariable=acc_var, values=acc_names,
                      width=15, font=("微软雅黑", 10), state="readonly"
                      ).pack(side=tk.LEFT, padx=(4, 16))

        tk.Label(row1, text="目标版本集合：", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)
                 ).pack(side=tk.LEFT)
        ver_var = tk.StringVar()
        state = {"running": False, "stop": False, "done": 0, "total": 0}

        def _ver_names():
            try:
                return _tc.all_version_names()
            except Exception:
                return []

        ver_combo = RoundCombobox(row1, textvariable=ver_var,
                                  values=_ver_names(), width=18,
                                  font=("微软雅黑", 10), state="readonly")
        ver_combo.pack(side=tk.LEFT, padx=(4, 8))

        def _save_cfg():
            try:
                _rs.save_center_settings({
                    "only_claimable": bool(only_claimable.get()),
                    "account": acc_var.get().strip(),
                    "version": ver_var.get().strip(),
                })
            except Exception:
                pass

        def _create_collection():
            """手动创建版本集合（默认名「已完成任务」）。"""
            from tkinter import simpledialog
            base = _tc.DONE_VERSION
            exist = set(_ver_names())
            nm = base
            i = 2
            while nm in exist:
                nm = "%s%d" % (base, i)
                i += 1
            name = simpledialog.askstring(
                "新建版本集合",
                "输入版本集合名称（将出现在「版本」下拉框）：\n"
                "期数固定「已完成」、类型固定「已完成任务」",
                initialvalue=nm, parent=dlg)
            if not name:
                return
            ok, msg = _tc.create_custom_version(name.strip())
            if not ok:
                messagebox.showwarning("创建失败", msg, parent=dlg)
                return
            ver_combo.config(values=_ver_names())
            ver_var.set(name.strip())
            _save_cfg()
            _log("✓ 已创建版本集合：%s" % name.strip())
            try:
                # v6.4.9: 两个模式的下拉框都要刷新
                self.refresh_version_combo()        # 旧模式
                self.nm_refresh_version_combo()     # 新模式
                self.nm_update_task_list()
                self.nm_on_version_change()
            except Exception:
                pass

        def _delete_collection():
            """删除当前选中的自定义版本集合。"""
            name = ver_var.get().strip()
            if not name:
                return
            if not messagebox.askyesno(
                    "确认删除",
                    "删除版本集合「%s」？\n"
                    "该集合下的任务会一并移除（官方版本不可删）。" % name,
                    parent=dlg):
                return
            ok, msg = _tc.delete_custom_version(name)
            if not ok:
                messagebox.showwarning("无法删除", msg, parent=dlg)
                return
            ver_combo.config(values=_ver_names())
            new_names = _ver_names()
            if new_names:
                ver_var.set(new_names[0])
            _save_cfg()
            _log("✓ 已删除版本集合：%s" % name)
            try:
                # v6.4.9: 两个模式的下拉框都要刷新
                self.refresh_version_combo()        # 旧模式
                self.nm_refresh_version_combo()     # 新模式
                self.nm_update_task_list()
                self.nm_on_version_change()
            except Exception:
                pass

        DarkButton(row1, text="＋ 新建集合", command=_create_collection,
                   height=30, width=110, bg_color=COLORS["accent"],
                   text_color="#000000", compact=True
                   ).pack(side=tk.LEFT, padx=(2, 4))
        DarkButton(row1, text="－ 删除集合", command=_delete_collection,
                   height=30, width=110, bg_color="#c0392b",
                   text_color="#ffffff", compact=True
                   ).pack(side=tk.LEFT)

        # ===== 第二行：开始/停止 + 进度 =====
        row2 = tk.Frame(head, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, padx=14, pady=(0, 8))
        prog_lbl = tk.Label(row2, text="未开始", bg=COLORS["bg_card"],
                            fg=COLORS["text_muted"], font=("微软雅黑", 10))
        prog_cv = tk.Canvas(row2, width=280, height=16,
                            bg=COLORS["bg_input"], highlightthickness=0)
        prog_cv.create_rectangle(0, 0, 0, 16, fill=COLORS["success"],
                                 width=0, tags="bar")

        def _update_prog():
            try:
                t = max(1, state["total"])
                pct = min(1.0, state["done"] / t)
                prog_cv.coords("bar", 0, 0, int(280 * pct), 16)
                prog_lbl.config(
                    text="%d/%d" % (state["done"], state["total"]),
                    fg=COLORS["success"] if pct >= 1 else COLORS["accent"])
            except Exception:
                pass

        # ===== 主体 =====
        body = tk.Frame(dlg, bg=COLORS["bg_dark"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        log_card = tk.Frame(body, bg=COLORS["bg_card"],
                            highlightthickness=1,
                            highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(log_card, text="查询日志", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 10, "bold"),
                 anchor=tk.W).pack(fill=tk.X, padx=10, pady=(6, 2))
        log_txt = tk.Text(log_card, height=6, bg=COLORS["bg_input"],
                          fg=COLORS["text_primary"], font=("Consolas", 9),
                          bd=0, highlightthickness=0, wrap=tk.WORD)
        log_sb = tk.Scrollbar(log_card, orient=tk.VERTICAL,
                              command=log_txt.yview)
        log_txt.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=(0, 6))
        log_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                     padx=10, pady=(0, 6))

        def _log(msg):
            try:
                log_txt.insert(tk.END, msg + "\n")
                log_txt.see(tk.END)
            except Exception:
                pass

        tbl_card = tk.Frame(body, bg=COLORS["bg_card"],
                            highlightthickness=1,
                            highlightbackground=COLORS["border"])
        tbl_card.pack(fill=tk.BOTH, expand=True)
        tbl_head = tk.Frame(tbl_card, bg=COLORS["bg_card"])
        tbl_head.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(tbl_head, text="任务状态", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 10, "bold")
                 ).pack(side=tk.LEFT)
        cnt_lbl = tk.Label(tbl_head, text="0 条", bg=COLORS["bg_card"],
                           fg=COLORS["text_muted"], font=("微软雅黑", 9))
        cnt_lbl.pack(side=tk.LEFT, padx=(8, 0))

        # 默认只看可抢（按用户要求）+ 记忆
        only_claimable = tk.BooleanVar(
            value=bool(cfg.get("only_claimable", True)))

        tbl_wrap = tk.Frame(tbl_card, bg=COLORS["bg_card"])
        tbl_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        def _render_table():
            for w in tbl_wrap.winfo_children():
                w.destroy()
            try:
                cache = _rs.load_task_status_cache()
            except Exception:
                cache = {}
            rows = [v for v in (cache or {}).values() if isinstance(v, dict)]
            if only_claimable.get():
                rows = [r for r in rows if (
                    r.get("task_finished") and r.get("stock_available")
                    and r.get("status") not in (6, 7))]
            rows.sort(key=lambda r: str(r.get("queried_at", "")),
                      reverse=True)
            cnt_lbl.config(text="%d 条%s" % (
                len(rows), "（只看可抢）" if only_claimable.get() else ""))

            if not rows:
                tip = ("暂无【可抢】任务：\n"
                       "  1. 没查过 -> 点「▶ 开始查询」\n"
                       "  2. 查过但无可抢 -> 取消勾选「只看可抢」查看全部\n"
                       "  3. 可抢条件：已完成 + 库存充足 + 非已领取/无资格")
                tk.Label(tbl_wrap, text=tip, bg=COLORS["bg_card"],
                         fg=COLORS["text_muted"], font=("微软雅黑", 10),
                         anchor=tk.W, justify=tk.LEFT
                         ).pack(fill=tk.X, padx=6, pady=20)
                return

            cv = tk.Canvas(tbl_wrap, bg=COLORS["bg_card"],
                           highlightthickness=0, bd=0)
            sb = tk.Scrollbar(tbl_wrap, orient=tk.VERTICAL, command=cv.yview)
            inner = tk.Frame(cv, bg=COLORS["bg_card"])
            win = cv.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>",
                       lambda e: cv.configure(scrollregion=cv.bbox("all")))
            cv.bind("<Configure>",
                    lambda e: cv.itemconfig(win, width=max(e.width, 100)))
            cv.configure(yscrollcommand=sb.set)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            gm = tk.Frame(inner, bg=COLORS["bg_card"])
            gm.pack(fill=tk.X)
            W = (4, 2, 1, 2, 2)
            M = (200, 100, 55, 110, 110)
            for ci in range(5):
                gm.grid_columnconfigure(ci, weight=W[ci], minsize=M[ci],
                                        uniform="c")
            HR = {"r": 0}

            def addrow(vals, colors, header=False):
                r = HR["r"]
                HR["r"] += 1
                bg = COLORS["bg_input"] if header else COLORS["bg_card"]
                for i, (v, c) in enumerate(zip(vals, colors)):
                    tk.Label(gm, text=str(v), bg=bg, fg=c,
                             font=("微软雅黑", 9,
                                   "bold" if header else "normal"),
                             anchor=tk.W
                             ).grid(row=r, column=i, sticky="w",
                                    padx=5, pady=(5 if header else 2))

            addrow(("任务名称", "账户", "状态码", "状态", "查询时间"),
                   tuple([COLORS["text_secondary"]] * 5), header=True)
            for it in rows[:300]:
                ok = (it.get("task_finished") and it.get("stock_available")
                      and it.get("status") not in (6, 7))
                col = COLORS["success"] if ok else COLORS["text_muted"]
                addrow((
                    str(it.get("task_name", ""))[:26] or "-",
                    str(it.get("account", ""))[:12] or "-",
                    str(it.get("status", "-")),
                    str(it.get("status_text", ""))[:14] or "-",
                    str(it.get("queried_at", ""))[5:16],
                ), (col, COLORS["text_primary"], COLORS["text_primary"],
                    col, COLORS["text_muted"]))

        # ===== 查询执行 =====
        btn_start = [None]
        btn_stop = [None]

        def _set_running(running):
            state["running"] = running
            try:
                btn_start[0].config(state="disabled" if running else "normal")
                btn_stop[0].config(state="normal" if running else "disabled")
            except Exception:
                pass

        def _worker():
            import threading as _th
            import time as _t

            acc_name = acc_var.get().strip()
            account = None
            try:
                account = self.account_mgr.get_account(acc_name)
            except Exception:
                pass
            if not account:
                dlg.after(0, lambda: _log("✗ 账户不存在：%s" % acc_name))
                dlg.after(0, lambda: _set_running(False))
                return
            cookies = {"SESSDATA": account.get("SESSDATA", ""),
                       "bili_jct": account.get("bili_jct", "")}

            combos = set()
            for t in ALL_TASKS:
                if t.get("version") in (_tc.DONE_VERSION, "手动任务"):
                    continue
                if t.get("is_custom"):
                    continue
                combos.add((t["version"], t["period"], t["type"]))
            combos = sorted(combos)
            state["total"] = len(combos)
            state["done"] = 0
            state["stop"] = False
            dlg.after(0, _update_prog)
            dlg.after(0, lambda: _log("开始查询：账户 %s，共 %d 个活动分类"
                                      % (acc_name, len(combos))))

            from bili_api import check_all_tasks_finished
            total_saved = 0
            for idx, (ver, per, typ) in enumerate(combos):
                if state["stop"]:
                    dlg.after(0, lambda: _log("⏹ 已被用户停止"))
                    break
                dlg.after(0, lambda v=ver, p=per, tt=typ, i=idx:
                          _log("[%d/%d] %s · %s · %s"
                               % (i + 1, len(combos), v, p, tt)))
                try:
                    _af, details = check_all_tasks_finished(
                        ver, per, typ, cookies)
                except Exception as e:
                    dlg.after(0, lambda e=e: _log("  ✗ 异常: %s" % str(e)[:60]))
                    details = []
                saved = 0
                for d in (details or []):
                    tid = str(d.get("task_id", "") or "")
                    if not tid:
                        continue
                    _fin = d.get("finished")
                    if _fin is None:
                        _fin = d.get("task_finished")
                    _ts = d.get("total_stock", 0) or 0
                    try:
                        _rs.update_task_status(tid, acc_name, {
                            "task_finished": bool(_fin),
                            "stock_available": bool(_ts > 0),
                            "status": d.get("status", -1),
                            "status_text": str(d.get("message", "") or ""),
                            "total_stock": _ts,
                            "day_stock": d.get("day_stock", 0) or 0,
                            "task_name": str(d.get("name", "") or ""),
                            "award": str(d.get("award", "") or ""),
                            "version": str(ver or ""),
                        })
                        saved += 1
                    except Exception:
                        pass
                total_saved += saved
                state["done"] = idx + 1
                dlg.after(0, _update_prog)
                dlg.after(0, lambda s=saved: _log("  ✓ 保存 %d 条" % s))
                if idx < len(combos) - 1:
                    for _ in range(10):
                        if state["stop"]:
                            break
                        _t.sleep(0.1)

            dlg.after(0, lambda: _log("查询完成：共保存 %d 条" % total_saved))
            dlg.after(0, lambda: _set_running(False))
            dlg.after(0, _render_table)

        def _start():
            if state["running"]:
                return
            if not acc_var.get().strip():
                messagebox.showwarning("提示", "请先选择查询账户。", parent=dlg)
                return
            _save_cfg()
            state["stop"] = False
            _set_running(True)
            _log("-" * 60)
            import threading as _th
            _th.Thread(target=_worker, daemon=True).start()

        def _stop():
            state["stop"] = True
            _log("正在停止...（当前分类查完就停）")

        DarkButton(row2, text="▶ 开始查询", command=_start,
                   height=32, width=120, bg_color=COLORS["success"],
                   text_color="#ffffff").pack(side=tk.LEFT)
        btn_start[0] = row2.winfo_children()[-1]
        b2 = DarkButton(row2, text="⏹ 停止查询", command=_stop,
                        height=32, width=120, bg_color="#c0392b",
                        text_color="#ffffff")
        b2.pack(side=tk.LEFT, padx=(8, 0))
        btn_stop[0] = b2
        try:
            b2.config(state="disabled")
        except Exception:
            pass
        prog_lbl.pack(side=tk.LEFT, padx=(16, 4))
        prog_cv.pack(side=tk.LEFT)

        # ===== 底部：加入版本集合 =====
        def _add_to_collection():
            target = ver_var.get().strip()
            if not target:
                if not messagebox.askyesno(
                        "未选版本集合",
                        "还没选目标版本集合。\n"
                        "是否自动创建「%s」并加入？" % _tc.DONE_VERSION,
                        parent=dlg):
                    return
                ok, msg = _tc.create_custom_version(_tc.DONE_VERSION)
                if not ok:
                    messagebox.showwarning("创建失败", msg, parent=dlg)
                    return
                ver_combo.config(values=_ver_names())
                ver_var.set(_tc.DONE_VERSION)
                target = _tc.DONE_VERSION

            try:
                cache = _rs.load_task_status_cache()
            except Exception:
                cache = {}
            rows = [v for v in (cache or {}).values() if isinstance(v, dict)
                    and v.get("task_finished") and v.get("stock_available")
                    and v.get("status") not in (6, 7)]
            if not rows:
                messagebox.showinfo("提示", "当前没有可抢任务。", parent=dlg)
                return
            if not messagebox.askyesno(
                    "确认加入",
                    "把 %d 个可抢任务加入版本集合「%s」？\n\n"
                    "加入后它们会出现在「版本」下拉框的「%s」下\n"
                    "（期数=已完成，类型=已完成任务）。\n\n"
                    "已存在的任务会跳过。" % (len(rows), target, target),
                    parent=dlg):
                return
            n = _tc.add_tasks_to_version(target, rows)
            if n == 0:
                messagebox.showinfo("无需加入",
                                    "这些任务都已在「%s」中。" % target,
                                    parent=dlg)
            else:
                messagebox.showinfo(
                    "已加入",
                    "成功加入 %d 个任务到版本集合「%s」。\n\n"
                    "现在可以在抢码界面的「版本」下拉框选到它。"
                    % (n, target), parent=dlg)
            _log("✓ 加入 %d 个任务到「%s」" % (n, target))
            _save_cfg()
            try:
                # v6.4.9: 两个模式的下拉框都要刷新
                self.refresh_version_combo()        # 旧模式
                self.nm_refresh_version_combo()     # 新模式
                self.nm_update_task_list()
                self.nm_on_version_change()
            except Exception:
                pass

        DarkButton(foot, text="＋ 加入版本集合", command=_add_to_collection,
                   height=32, width=170, bg_color="#8e44ad"
                   ).pack(side=tk.RIGHT, padx=(8, 0))
        DarkButton(foot, text="关闭",
                   command=lambda: (_save_cfg(), dlg.destroy()),
                   height=32, width=90, bg_color="#7f8c8d"
                   ).pack(side=tk.RIGHT)

        def _toggle_claimable():
            _render_table()
            _save_cfg()

        ttk.Checkbutton(foot, text="只看可抢", variable=only_claimable,
                        command=_toggle_claimable).pack(side=tk.LEFT)
        DarkButton(foot, text="刷新表格", command=_render_table,
                   height=32, width=100, bg_color="#2980b9"
                   ).pack(side=tk.LEFT, padx=(16, 0))

        # ===== 初始化：恢复记忆的版本集合 =====
        def _init_ver():
            names = _ver_names()
            ver_combo.config(values=names)
            saved = str(cfg.get("version") or "")
            if saved and saved in names:
                ver_var.set(saved)
            elif _tc.DONE_VERSION in names:
                ver_var.set(_tc.DONE_VERSION)
            elif names:
                ver_var.set(names[0])

        _init_ver()
        _render_table()
        dlg.protocol("WM_DELETE_WINDOW",
                     lambda: (_save_cfg(), dlg.destroy()))


    def _create_query_window(self, title, subtitle):
        """创建一个跟仪表盘风格一致的独立窗口，返回 (dlg, body_frame, foot_frame)。"""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title(title)
        dlg.configure(bg=COLORS["bg_dark"])
        try:
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            w = int(sw * 0.62)
            h = int(sh * 0.72)
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2 - 20)
            dlg.geometry(f"{w}x{h}+{x}+{y}")
            dlg.minsize(900, 560)
        except Exception:
            dlg.geometry("1100x760")

        # 底部按钮区【先 pack】，否则会被 body 挤出窗口（v6.4.4 踩过的坑）
        foot = tk.Frame(dlg, bg=COLORS["bg_dark"])
        foot.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 12))

        head = tk.Frame(dlg, bg=COLORS["bg_card"])
        head.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(14, 8))
        title_row = tk.Frame(head, bg=COLORS["bg_card"])
        title_row.pack(fill=tk.X, padx=16, pady=(12, 4))
        tk.Label(title_row, text=title, bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold")
                 ).pack(side=tk.LEFT)
        tk.Label(head, text=subtitle, bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9),
                 anchor=tk.W, justify=tk.LEFT
                 ).pack(fill=tk.X, padx=16, pady=(0, 8))

        body = tk.Frame(dlg, bg=COLORS["bg_dark"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))
        return dlg, body, foot

    def open_claimable_window(self):
        """「查询可领取」独立窗口。

        展示所有已查询任务的完整状态（持久化数据），
        并支持把「已完成且可抢」的任务一键加到当前任务组。
        v6.4.6: 用户要求做成跟仪表盘一样的可打开界面。
        """
        try:
            import rush_stats as _rs
            import tasks_config as _tc
        except Exception:
            return

        dlg, body, foot = self._create_query_window(
            "📋 查询可领取",
            "数据来源：任务状态查询缓存（重启后仍保留）。"
            "「可抢」= 任务已完成 + 库存充足 + 非已领取/无资格。")

        # 顶部过滤条
        ctrl = tk.Frame(body, bg=COLORS["bg_dark"])
        ctrl.pack(fill=tk.X, pady=(0, 6))
        only_claimable = tk.BooleanVar(value=True)

        state_box = {"data": []}

        # 内容容器
        wrap = tk.Frame(body, bg=COLORS["bg_card"])
        wrap.pack(fill=tk.BOTH, expand=True)

        def _render():
            for w in wrap.winfo_children():
                w.destroy()
            try:
                cache = _rs.load_task_status_cache()
            except Exception:
                cache = {}
            rows = []
            for k, v in (cache or {}).items():
                if not isinstance(v, dict):
                    continue
                rows.append(v)

            if only_claimable.get():
                rows = [r for r in rows if (
                    r.get("task_finished") and r.get("stock_available")
                    and r.get("status") not in (6, 7))]
            rows.sort(key=lambda r: str(r.get("queried_at", "")), reverse=True)
            state_box["data"] = rows

            if not rows:
                tk.Label(wrap,
                         text="暂无数据。请先点「查询可领取」或「查询全部完成」发起一次查询。",
                         bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                         font=("微软雅黑", 11), anchor=tk.W
                         ).pack(fill=tk.X, padx=16, pady=30)
                return

            # 表头 + 数据行放进同一个 Grid（v6.4.5 对齐方案）
            gm = tk.Frame(wrap, bg=COLORS["bg_card"])
            gm.pack(fill=tk.BOTH, expand=True)
            W = (3, 2, 1, 2, 2)
            M = (170, 110, 60, 100, 110)
            for ci in range(5):
                gm.grid_columnconfigure(ci, weight=W[ci], minsize=M[ci],
                                        uniform="c")
            HR = {"r": 0}

            def addrow(vals, colors, bold=False, header=False):
                r = HR["r"]
                HR["r"] += 1
                bg = COLORS["bg_input"] if header else COLORS["bg_card"]
                for i, (v, c) in enumerate(zip(vals, colors)):
                    tk.Label(gm, text=str(v), bg=bg, fg=c,
                             font=("微软雅黑", 10,
                                   "bold" if (bold or header) else "normal"),
                             anchor=tk.W
                             ).grid(row=r, column=i, sticky="w",
                                    padx=6, pady=(5 if header else 2))

            addrow(("任务名称", "账户", "状态码", "状态", "查询时间"),
                   tuple([COLORS["text_secondary"]] * 5), header=True)

            for it in rows[:200]:
                ok = (it.get("task_finished") and it.get("stock_available")
                      and it.get("status") not in (6, 7))
                col = COLORS["success"] if ok else COLORS["text_muted"]
                addrow((
                    str(it.get("task_name", ""))[:26] or "-",
                    str(it.get("account", ""))[:12] or "-",
                    str(it.get("status", "-")),
                    str(it.get("status_text", ""))[:14] or "-",
                    str(it.get("queried_at", ""))[5:16],
                ), (col, COLORS["text_primary"], COLORS["text_primary"],
                    col, COLORS["text_muted"]))

        # 底部按钮
        def _add_all_claimable():
            rows = [r for r in state_box["data"] if (
                r.get("task_finished") and r.get("stock_available")
                and r.get("status") not in (6, 7))]
            if not rows:
                messagebox.showinfo("提示", "当前没有可抢任务。",
                                    parent=dlg)
                return
            if not messagebox.askyesno(
                    "确认添加",
                    "把 %d 个可抢任务加入当前任务组？\n"
                    "（已存在的会跳过）" % len(rows), parent=dlg):
                return
            n = self._add_done_to_group(rows)
            messagebox.showinfo("完成", "已加入 %d 个任务。" % n, parent=dlg)
            try:
                self.refresh_new_mode_task_list()
                self.nm_update_scheduler()
            except Exception:
                pass

        DarkButton(foot, text="＋ 全部加入任务组",
                   command=_add_all_claimable, height=32, width=180,
                   bg_color="#8e44ad").pack(side=tk.RIGHT, padx=(8, 0))
        DarkButton(foot, text="刷新", command=_render, height=32, width=90, tip="刷新抢码统计面板数据",
                   bg_color="#2980b9").pack(side=tk.RIGHT, padx=(8, 0))

        def _toggle():
            _render()
            try:
                self.save_ui_settings()
            except Exception:
                pass

        ttk.Checkbutton(ctrl, text="只看可抢（已完成+库存足+未领过）",
                        variable=only_claimable,
                        command=_render).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(ctrl, text="", bg=COLORS["bg_dark"]).pack(side=tk.LEFT)

        count_lbl = tk.Label(foot, text="", bg=COLORS["bg_dark"],
                             fg=COLORS["text_secondary"],
                             font=("微软雅黑", 10))
        count_lbl.pack(side=tk.LEFT)

        _render()
        count_lbl.config(text="共 %d 条" % len(state_box["data"]))

    def _add_done_to_group(self, rows):
        """把查询结果任务加入当前任务组。返回加入数量。"""
        if not self.current_group_id:
            messagebox.showwarning("提示", "请先选择一个任务组",
                                   parent=self.winfo_toplevel())
            return 0
        group = next((g for g in self.rush_groups
                      if g["group_id"] == self.current_group_id), None)
        if not group:
            return 0
        existing = {(t.get("task_id"), t.get("account_name"))
                    for t in group.get("tasks", [])}
        added = 0
        for r in rows:
            tid = str(r.get("task_id", "") or "")
            acc = str(r.get("account", "") or "")
            if not tid or (tid, acc) in existing:
                continue
            group.setdefault("tasks", []).append({
                "task_id": tid,
                "name": str(r.get("task_name", "") or ""),
                "award": "",
                "window_seconds": 120,
                "priority": len(group.get("tasks", [])) + 1,
                "account_name": acc,
                "act_id": str(r.get("act_id", "") or ""),
                "version": str(r.get("version", "") or "已完成任务"),
                "status_color": "green",
                "status_text": "✓ 可抢（来自查询结果）",
                "task_finished": True,
                "stock_available": True,
            })
            existing.add((tid, acc))
            added += 1
        if added:
            try:
                self.save_rush_groups()
            except Exception:
                pass
            self.nm_log("[查询窗口] 已加入 %d 个任务到「%s」"
                        % (added, group.get("group_name", "?")))
        return added

    def open_check_all_window(self):
        """「查询全部完成」独立窗口：统计各活动分类的完成情况。"""
        dlg, body, foot = self._create_query_window(
            "✅ 完成情况统计",
            "按 版本/期数/类型 汇总任务完成情况。数据来自任务状态查询缓存。")

        wrap = tk.Frame(body, bg=COLORS["bg_card"])
        wrap.pack(fill=tk.BOTH, expand=True)

        try:
            import rush_stats as _rs
            cache = _rs.load_task_status_cache()
        except Exception:
            cache = {}

        # 按 version 分组统计
        groups = {}
        for k, v in (cache or {}).items():
            if not isinstance(v, dict):
                continue
            ver = str(v.get("version", "") or "未标注")
            g = groups.setdefault(ver, {"total": 0, "done": 0,
                                        "claimable": 0})
            g["total"] += 1
            if v.get("task_finished"):
                g["done"] += 1
            if (v.get("task_finished") and v.get("stock_available")
                    and v.get("status") not in (6, 7)):
                g["claimable"] += 1

        if not groups:
            tk.Label(wrap, text="暂无数据。请先发起一次任务状态查询。",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 11), anchor=tk.W
                     ).pack(fill=tk.X, padx=16, pady=30)
        else:
            gm = tk.Frame(wrap, bg=COLORS["bg_card"])
            gm.pack(fill=tk.BOTH, expand=True)
            W = (4, 1, 1, 1)
            M = (220, 70, 70, 90)
            for ci in range(4):
                gm.grid_columnconfigure(ci, weight=W[ci], minsize=M[ci],
                                        uniform="c")
            HR = {"r": 0}

            def addrow(vals, colors, bold=False, header=False):
                r = HR["r"]
                HR["r"] += 1
                bg = COLORS["bg_input"] if header else COLORS["bg_card"]
                for i, (v, c) in enumerate(zip(vals, colors)):
                    tk.Label(gm, text=str(v), bg=bg, fg=c,
                             font=("微软雅黑", 10,
                                   "bold" if (bold or header) else "normal"),
                             anchor=tk.W
                             ).grid(row=r, column=i, sticky="w",
                                    padx=6, pady=(5 if header else 2))

            addrow(("版本 / 活动", "任务数", "已完成", "可抢"),
                   tuple([COLORS["text_secondary"]] * 4), header=True)
            for ver in sorted(groups, key=lambda x: -groups[x]["total"]):
                g = groups[ver]
                c = (COLORS["success"] if g["claimable"] > 0
                     else COLORS["text_primary"])
                addrow((ver[:26], str(g["total"]), str(g["done"]),
                        str(g["claimable"])),
                       (c, COLORS["text_primary"], COLORS["text_primary"], c))

        DarkButton(foot, text="关闭", command=dlg.destroy,
                   height=32, width=90, bg_color="#7f8c8d").pack(side=tk.RIGHT)

    def _safe_btn_state(self, attr, state, text=None):
        """安全设置按钮状态（v6.4.7）。

        为什么需要：v6.4.7 把「查询可领取」「查询全部完成」两个按钮
        合并成了「任务查询中心」，但旧代码里还有对已删除按钮的
        .config() 调用，会抛 AttributeError。这里统一做存在性检查。
        """
        try:
            btn = getattr(self, attr, None)
            if btn is None:
                return
            kwargs = {"state": state}
            if text is not None:
                kwargs["text"] = text
            btn.config(**kwargs)
        except Exception:
            pass

    def check_claimable_tasks(self):
        """查询所有活动中已完成但未领取的任务，输出到日志"""
        try:
            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户", parent=self.winfo_toplevel())
                return

            account = selected_accounts[0]
            cookies = {"SESSDATA": account.get("SESSDATA", ""), "bili_jct": account.get("bili_jct", "")}

            self.log(f"查询全部可领取任务（所有活动）")
            self.log(f"账户: {account['name']}")
            self._safe_btn_state("quick_pick_btn", "disabled", "🔍 查询中...")

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
            messagebox.showerror("错误", f"查询失败: {str(e)}", parent=self.winfo_toplevel())
            self._safe_btn_state("quick_pick_btn", "normal", "🔍 任务查询中心")

    def _on_check_claimable_all(self, details):
        """查询全部可领取任务的回调（所有活动）

        v6.4.6: 查询完成后做两件事：
          1. 把每个任务的状态写盘持久化（rush_stats.update_task_status）
          2. 重建「已完成任务」虚拟分类（tasks_config.refresh_done_tasks），
             使其出现在版本/期数/类型下拉框中
        """
        self._safe_btn_state("quick_pick_btn", "normal", "🔍 任务查询中心")

        # ---- 1) 持久化每个任务状态 ----
        try:
            import rush_stats as _rs
            _acc = ""
            try:
                _sel = self.get_selected_accounts()
                if _sel:
                    _acc = str(_sel[0].get("name", "") or "")
            except Exception:
                pass
            for _d in (details or []):
                if not isinstance(_d, dict):
                    continue
                _tid = str(_d.get("task_id", "") or "")
                if not _tid:
                    continue
                # v6.4.7 修复字段名 bug：
                # bili_api.check_all_tasks_finished() 返回的字段是
                #   {"task_id","name","finished","status","message",
                #    "award","total_stock","day_stock","from_cache"}
                # 原代码读 task_finished / stock_available（都不存在）
                # -> 全部判为 False -> 缓存里没有可抢任务 -> 界面显示空。
                _fin = _d.get("finished")
                if _fin is None:
                    _fin = _d.get("task_finished")
                _tstock = _d.get("total_stock", 0) or 0
                _dstock = _d.get("day_stock", 0) or 0
                # 有剩余总库存才算可抢（total_stock 是剩余百分比）
                _stk_ok = bool(_tstock > 0)
                _rs.update_task_status(_tid, _acc, {
                    "task_finished": bool(_fin),
                    "stock_available": _stk_ok,
                    "status": _d.get("status", -1),
                    "status_text": str(_d.get("message", "")
                                        or _d.get("status_text", "")),
                    "total_stock": _tstock,
                    "day_stock": _dstock,
                    "task_name": str(_d.get("name", "")
                                     or _d.get("task_name", "")),
                    "act_id": str(_d.get("act_id", "") or ""),
                    "version": str(_d.get("version", "") or ""),
                })
        except Exception:
            pass

        # ---- 2) 重建「已完成任务」虚拟分类 ----
        try:
            import tasks_config as _tc
            _tc.refresh_done_tasks()
            self.log("已刷新「已完成任务」分类（%d 个可抢任务）"
                     % len(getattr(_tc, "DONE_TASKS", [])))
        except Exception:
            pass

        # ---- 3) 刷新版本/期数/类型下拉框（若已完成任务有数据）----
        try:
            import tasks_config as _tc
            if getattr(_tc, "DONE_TASKS", []):
                self.nm_update_task_list()
        except Exception:
            pass

        if not details:
            self.log("查询结果: 无匹配的任务")
            messagebox.showinfo("查询结果", "无匹配的任务", parent=self.winfo_toplevel())
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
        messagebox.showinfo("可领取任务查询结果", result_text, parent=self.winfo_toplevel())

    def check_all_finished(self):
        """查询当前选择类型的所有任务是否全部完成"""
        try:
            version = self.version_var.get()
            period = self.period_var.get()
            task_type = self.task_type_var.get()

            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户", parent=self.winfo_toplevel())
                return

            account = selected_accounts[0]
            cookies = {"SESSDATA": account.get("SESSDATA", ""), "bili_jct": account.get("bili_jct", "")}

            print(f"[DEBUG] check_all_finished called: version={version}, period={period}, type={task_type}")
            print(f"[DEBUG] account: {account.get('name', 'unknown')}")

            self.log(f"查询全部完成: [{version}][{period}][{task_type}]")
            self.log(f"账户: {account['name']}")
            self._safe_btn_state("quick_pick_btn", "disabled", "🔍 查询中...")

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
            messagebox.showerror("错误", f"查询失败: {str(e)}", parent=self.winfo_toplevel())

    def _on_check_all_finished(self, all_finished, details):
        """查询全部完成的回调"""
        self._safe_btn_state("quick_pick_btn", "normal", "🔍 任务查询中心")

        if not details:
            self.log("查询结果: 无匹配的任务")
            messagebox.showinfo("查询结果", "无匹配的任务", parent=self.winfo_toplevel())
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
        messagebox.showinfo("任务完成情况", result_text, parent=self.winfo_toplevel())

    def claim_all_finished(self):
        """一键领取当前类型下所有已完成的任务"""
        try:
            version = self.version_var.get()
            period = self.period_var.get()
            task_type = self.task_type_var.get()

            # 获取选中的账户
            selected_accounts = self.get_selected_accounts()
            if not selected_accounts:
                messagebox.showwarning("提示", "请先选择一个账户", parent=self.winfo_toplevel())
                return

            account = selected_accounts[0]

            # 确认对话框
            confirm_msg = f"确定要一键领取 [{version}][{period}][{task_type}] 下所有已完成的任务吗？\n\n账户：{account['name']}"
            if not messagebox.askyesno("确认", confirm_msg, parent=self.winfo_toplevel()):
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
            messagebox.showerror("错误", f"一键领取失败: {str(e)}", parent=self.winfo_toplevel())
            self.claim_all_btn.config(state="normal", text="🎁 一键全部领取")

    def _on_claim_all_finished(self, results, success_count, fail_count, skip_count, error):
        """一键全部领取的回调"""
        self.claim_all_btn.config(state="normal", text="🎁 一键全部领取")

        if error:
            self.log(f"一键全部领取失败: {error}")
            messagebox.showerror("错误", error, parent=self.winfo_toplevel())
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
        messagebox.showinfo("一键全部领取结果", result_text, parent=self.winfo_toplevel())

    def manual_receive(self):
        """手动领取：立即尝试领取一次"""
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务", parent=self.winfo_toplevel())
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户", parent=self.winfo_toplevel())
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
            messagebox.showwarning("提示", "请先选择任务", parent=self.winfo_toplevel())
            return
        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择至少一个账户", parent=self.winfo_toplevel())
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
            messagebox.showwarning("提示", "请输入有效的领取时长（秒）和间隔（毫秒）", parent=self.winfo_toplevel())
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
            messagebox.showerror("登录失效", "所有账户登录验证都失败了", parent=self.winfo_toplevel())
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

    def do_receive_fast(self, task, task_info, account, session=None, advance_ms=0,
                        stop_flag=None):
        """快速领取：直接尝试领取（session可选，复用预热连接）

        advance_ms: 本次使用的提前量（v6.2.0）
        stop_flag:  任务组共享状态，含本场次的运行指标（v6.4.0）
        """
        cookies = cookies_from_account(account)
        csrf = account["bili_jct"]
        _t0 = time.time()
        status, result, data = receive_reward(task["task_id"], task_info, cookies, csrf, session)
        _latency_ms = (time.time() - _t0) * 1000

        # O4: 结构化记录每次领取结果，供后续统计成功率/失败码分布
        try:
            # v6.4.0: 取本场次运行指标，并判断是否首发
            _sf = stop_flag if isinstance(stop_flag, dict) else None
            _is_first = bool(_sf is not None
                             and not _sf.get("_first_shot_done", True))
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
                advance_ms=advance_ms,
                # v6.3.0: 记录奖励与版本，供"稀有奖励"筛选统计
                award=task.get("award", ""),
                version=task.get("version", ""),
                # v6.4.0: 本场次程序运行指标
                session_id=(_sf.get("_session_id", "") if _sf else ""),
                ntp_offset_ms=(_sf.get("_ntp_offset_ms", 0) if _sf else 0),
                target_ts=(_sf.get("_target_ts", 0) if _sf else 0),
                fire_ts=(_sf.get("_fire_ts", 0) if _sf else 0),
                one_way_ms=(_sf.get("_one_way_ms", 0) if _sf else 0),
                probe_rtt_med=(_sf.get("_probe_rtt_med", 0) if _sf else 0),
                probe_valid=(_sf.get("_probe_valid", 0) if _sf else 0),
                probe_total=(_sf.get("_probe_total", 0) if _sf else 0),
                spin_error_ms=(_sf.get("_spin_error_ms", 0) if _sf else 0),
                is_first_shot=_is_first,
                arrive_dev_ms=(_sf.get("_arrive_dev_ms") if (_sf and _is_first) else None),
                # v6.5.6: 补齐此前从未写入的字段（导致 RTT抖动/窗口期利用率 一直空）
                probe_samples=(_sf.get("_probe_samples", "") if _sf else ""),
                window_seconds=int(task.get("window_seconds", 0) or 0),
                priority=int(task.get("priority", 0) or 0),
            )
            # 标记首发已消费
            if _is_first and _sf is not None:
                _sf["_first_shot_done"] = True
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
            messagebox.showwarning("提示", "精准抢码正在运行中，请先停止后再启动监控抢码", parent=self.winfo_toplevel())
            return
        task = self.get_current_task()
        if not task:
            messagebox.showwarning("提示", "请先选择任务", parent=self.winfo_toplevel())
            return

        accounts = self.get_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先选择一个账户", parent=self.winfo_toplevel())
            return
        rush_accounts = [accounts[0]]

        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的查询间隔（秒）", parent=self.winfo_toplevel())
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
            messagebox.showerror("登录失效", "所有账户登录验证都失败了", parent=self.winfo_toplevel())
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
            # v6.4.0: 取本场次的运行指标，并判断是否首发
            _sf = stop_flag if isinstance(stop_flag, dict) else None
            _is_first = bool(_sf is not None
                             and not _sf.get("_first_shot_done", True))
