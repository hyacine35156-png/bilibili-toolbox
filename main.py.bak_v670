# -*- coding: utf-8 -*-
"""程序入口：主窗口与启动流程。

原先的 main_gui_pro.py 已拆分为：
    config.py        常量/路径/颜色/API 地址
    tasks_config.py  游戏活动任务表 + act_id 缓存
    storage.py       原子写/安全读/兑换码持久化
    bili_api.py      B站接口（登录/WBI/任务/库存/领取）
    widgets.py       自定义 Tk 组件
    dialogs.py       账户对话框
    card_auth.py     卡密验证转发
    managers/        账户与直播间管理器
    ui/              各功能页面（看播/日程/兑换码/卡密/抢码）
"""

import json, os, random, shutil, threading, time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ctypes

# 打包后 certifi 证书路径修复（必须在 requests 之前）
try:
    import certifi
    _cert_path = certifi.where()
    if os.path.exists(_cert_path):
        os.environ['REQUESTS_CA_BUNDLE'] = _cert_path
        os.environ['CURL_CA_BUNDLE'] = _cert_path
except Exception:
    pass

import requests

from config import (COLORS, BASE_DIR, _EXE_DIR, APP_VERSION, CONFIG_FILE, DANMAKU_FILE,
                    ACCOUNTS_FILE, ACT_ID_CACHE_FILE, LOG_DIR, BACKUP_DIR,
                    HEADERS, DANMAKU_POOL, _GLOBAL_LOCK, TASK_GUIDE_TEXT)
from tasks_config import ALL_TASKS, MINGCHAO_TASKS, VERSION_DEFAULT_ACT_ID
from storage import atomic_write_json, safe_load_json
from bili_api import send_danmaku, verify_login, cookies_from_account
from widgets import DarkButton, DarkEntry, ToolTip, custom_askyesno
from dialogs import AddAccountDialog, EditAccountDialog
from managers import AccountManager, RoomManager
from ui.rush_reward import RushRewardFrame
from ui.code_export import CodeExportFrame
from ui.watch_live import WatchLiveFrame
from ui.schedule import ScheduleFrame
from ui.card_auth_page import CardAuthFrame, show_card_auth
from card_auth import (get_machine_code, get_card_remaining_text, verify_card_online,
                      load_saved_card, is_card_expired, save_card_info, clear_saved_card,
                      CARD_FILE, CARD_API_BASE, CARD_VERIFY_URL)
import data_guard
from ui import theme
import updater

# 自动迁移旧配置文件（从exe同目录迁移到data子目录）
def _migrate_old_files():
    old_files = [
        "accounts.json", "danmaku_list.txt", "config.json",
        "act_id_cache.json", "watch_config.json", "rush_config.json",
        "scheduled_tasks.json", "shutdown_config.json",
    ]
    for fname in old_files:
        old_path = _EXE_DIR / fname
        new_path = BASE_DIR / fname
        if old_path.exists() and not new_path.exists():
            try:
                import shutil
                shutil.move(str(old_path), str(new_path))
                print(f"已迁移配置文件: {fname} -> data/")
            except Exception as e:
                print(f"迁移 {fname} 失败: {e}")
    # 迁移logs和backup目录
    for dname in ["logs", "backup"]:
        old_dir = _EXE_DIR / dname
        new_dir = BASE_DIR / dname
        if old_dir.exists() and old_dir.is_dir() and not new_dir.exists():
            try:
                import shutil
                shutil.move(str(old_dir), str(new_dir))
                print(f"已迁移目录: {dname}/ -> data/{dname}/")
            except Exception as e:
                print(f"迁移 {dname} 失败: {e}")


# 启动时迁移旧配置（原 main_gui_pro.py:123-126）
try:
    _migrate_old_files()
except Exception as e:
    print(f"配置文件迁移失败（不影响启动）: {e}")

# 启动时数据自检 + 每日自动备份（O2）
# 必须在 AccountManager / RoomManager 加载数据之前执行，才能起到自愈作用。
_STARTUP_DATA_GUARD = None
try:
    _STARTUP_DATA_GUARD = data_guard.startup_maintenance()
except Exception as e:
    print(f"数据自检/备份失败（不影响启动）: {e}")


class DanmakuApp:
    def __init__(self, root):
        self.root = root
        self.card_text = get_card_remaining_text()
        self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+看播任务+日程任务{self.card_text}")
        self.root.geometry("1800x1400")
        self.root.minsize(1500, 1100)
        self.root.configure(bg=COLORS["bg_dark"])

        self.account_mgr = AccountManager()
        self.room_mgr = RoomManager()
        self.danmaku_list = self.load_danmaku()
        self._config_save_timer = None  # 配置保存防抖定时器
        self.config = self.load_config()
        self.running = False
        self.send_thread = None

        # 定时关机相关
        self.shutdown_mode = "none"  # none / scheduled / delay
        self.shutdown_thread = None
        self.shutdown_stop_flag = {"stop": False}
        self.shutdown_remaining = 0  # 剩余秒数
        self.shutdown_tasks = []  # 关机任务列表

        self.setup_styles()
        self.build_ui()
        self.refresh_account_list()
        self.refresh_danmaku_list()
        # 恢复上次选中的标签页
        saved_tab = self.config.get("current_tab", "rush")
        if saved_tab == "danmaku":
            self.switch_tab("danmaku")
        elif saved_tab == "shutdown":
            self.switch_tab("shutdown")
        elif saved_tab == "schedule":
            self.switch_tab("schedule")
        # 恢复上次选中的账户
        self.restore_selected_account()
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log("程序启动，已加载 " + str(len(self.account_mgr.accounts)) + " 个账户，" + str(len(self.danmaku_list)) + " 条弹幕")
        self.log("数据目录: " + str(BASE_DIR))
        self.log("(配置文件已自动存到data子文件夹，不会铺满桌面)")
        # 启动时后台验证所有账号登录状态
        self._startup_check_accounts()

    def _startup_check_accounts(self):
        """启动时在后台线程验证所有账号登录状态，失效则弹窗报错"""
        import threading
        def _check():
            try:
                import requests
                time.sleep(2)  # 等UI完全加载
                failed = []
                for acc in self.account_mgr.accounts:
                    name = acc.get("name", "未知")
                    try:
                        cookies = cookies_from_account(acc)
                        resp = requests.get("https://api.bilibili.com/x/web-interface/nav",
                                            headers=HEADERS, cookies=cookies, timeout=8)
                        data = resp.json()
                        if data.get("code") != 0:
                            failed.append(f"{name}（{data.get('message', '未知错误')}）")
                    except Exception as e:
                        failed.append(f"{name}（验证异常: {str(e)[:30]}）")
                if failed:
                    msg = "以下 " + str(len(failed)) + " 个账号登录已失效，请重新登录：\n\n" + "\n".join(failed)
                    self.root.after(0, lambda: self._show_account_login_error(msg))
                else:
                    self.log(f"✓ 启动账号验证: 全部 {len(self.account_mgr.accounts)} 个账号登录有效")
            except Exception as e:
                self.log(f"⚠ 启动账号验证异常: {e}")
        threading.Thread(target=_check, daemon=True).start()

    def _show_account_login_error(self, msg):
        """在主线程弹出账号登录失效错误"""
        from tkinter import messagebox
        self.log(f"⚠ {msg}")
        messagebox.showerror("账号登录失效", msg, parent=self.root)

    def restore_selected_account(self):
        """恢复上次选中的账户"""
        saved_name = self.config.get("selected_account", "")
        if not saved_name:
            return
        for i, acc in enumerate(self.account_mgr.accounts):
            if acc.get("name", "") == saved_name:
                try:
                    self.account_listbox.selection_set(i)
                    self.account_listbox.see(i)
                    self.on_account_select(None)
                except Exception:
                    pass
                break

    def on_closing(self):
        """窗口关闭时：先停止所有线程 → 等待结束 → 保存配置 → 销毁窗口"""
        close_errors = []
        try:
            # 1. 停止所有运行中的模块
            if hasattr(self, 'rush_page'):
                try:
                    if hasattr(self.rush_page, 'running'):
                        self.rush_page.running = False
                    if hasattr(self.rush_page, 'nm_stop_all'):
                        self.rush_page.nm_stop_all()
                    elif hasattr(self.rush_page, 'stop_rush'):
                        self.rush_page.stop_rush()
                except Exception as e:
                    close_errors.append(f"停止抢码: {e}")
            if hasattr(self, 'watch_page'):
                try:
                    if hasattr(self.watch_page, 'running'):
                        self.watch_page.running = False
                    if hasattr(self.watch_page, 'stop_flag'):
                        self.watch_page.stop_flag["stop"] = True
                    if hasattr(self.watch_page, 'gift_running'):
                        self.watch_page.gift_running = False
                    if hasattr(self.watch_page, 'gift_stop'):
                        for name in self.watch_page.gift_stop:
                            self.watch_page.gift_stop[name] = True
                except Exception as e:
                    close_errors.append(f"停止看播: {e}")
            # 停止弹幕发送
            try:
                self.running = False
            except Exception:
                pass
            # 停止调度器
            if hasattr(self, 'schedule_page'):
                try:
                    if hasattr(self.schedule_page, 'stop_scheduler'):
                        self.schedule_page.stop_scheduler()
                except Exception as e:
                    close_errors.append(f"停止调度器: {e}")
            # 取消定时关机
            try:
                self.cancel_shutdown()
            except Exception as e:
                close_errors.append(f"取消关机: {e}")

            # 2. 等待线程结束（最多2秒）
            time.sleep(0.5)

            # 3. 保存所有配置
            try:
                self.save_config()
            except Exception as e:
                close_errors.append(f"保存配置: {e}")
            try:
                self.save_danmaku_silent()
            except Exception as e:
                close_errors.append(f"保存弹幕: {e}")
            if hasattr(self, 'rush_page'):
                try:
                    self.rush_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存抢码: {e}")
            if hasattr(self, 'watch_page'):
                try:
                    self.watch_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存看播: {e}")
            if hasattr(self, 'schedule_page'):
                try:
                    self.schedule_page.on_close()
                except Exception as e:
                    close_errors.append(f"保存日程: {e}")
            try:
                self.save_shutdown_config()
            except Exception as e:
                close_errors.append(f"保存关机配置: {e}")

            if close_errors:
                print(f"⚠ 关闭时出现 {len(close_errors)} 个错误:")
                for err in close_errors:
                    print(f"  - {err}")
        except Exception as e:
            print(f"✗ on_closing严重异常: {e}")
        self.root.destroy()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=COLORS["bg_dark"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])
        style.configure("Dark.TLabel", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=theme.font(9))
        style.configure("Title.TLabel", background=COLORS["bg_card"], foreground=COLORS["accent"], font=theme.font(11, bold=True))
        style.configure("Dark.TRadiobutton", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=theme.font(9))
        style.configure("Dark.Horizontal.TScrollbar", background=COLORS["bg_input"], troughcolor=COLORS["bg_card"], bordercolor=COLORS["bg_card"], arrowcolor=COLORS["accent"])

    def build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_frame = tk.Frame(header, bg=COLORS["bg_card"])
        title_frame.pack(side=tk.LEFT, padx=20)

        tk.Label(title_frame, text="● B站工具箱", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=theme.font(16, bold=True)).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=theme.font(11)).pack(side=tk.LEFT, padx=(8, 0))

        self.header_status = tk.Label(header, text="● 未运行", bg=COLORS["bg_card"],
                                       fg=COLORS["text_muted"], font=theme.font(11))
        self.header_status.pack(side=tk.RIGHT, padx=20)

        # 标签切换栏
        tab_bar = tk.Frame(self.root, bg=COLORS["bg_card"], height=52)
        tab_bar.pack(fill=tk.X)
        tab_bar.pack_propagate(False)

        # v6.2.0 性能优化：Tab 栏 emoji 换成几何符号。
        # 实测 ⚡ 首次渲染 290ms、💬 430ms（Windows 要加载 Segoe UI Emoji 字体），
        # 而 ◈ ○ 等几何符号只需 6-12ms。两个 Tab 换成几何符号可省约 700ms 启动时间。
        # 视觉效果基本一致（都是图标+文字），但启动快得多。
        self.tab_rush = tk.Label(tab_bar, text="◈ 抢码工具", bg=COLORS["accent"], fg="#000000",
                                  font=theme.font(12, bold=True), padx=24, pady=10, cursor="hand2")
        self.tab_rush.pack(side=tk.LEFT, padx=(15, 5), pady=6)
        self.tab_rush.bind("<Button-1>", lambda e: self.switch_tab("rush"))

        self.tab_danmaku = tk.Label(tab_bar, text="○ 弹幕工具", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_danmaku.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_danmaku.bind("<Button-1>", lambda e: self.switch_tab("danmaku"))

        self.tab_shutdown = tk.Label(tab_bar, text="◷ 定时关机", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_shutdown.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_shutdown.bind("<Button-1>", lambda e: self.switch_tab("shutdown"))

        self.tab_watch = tk.Label(tab_bar, text="▣ 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))

        self.tab_code_export = tk.Label(tab_bar, text="◆ 兑换码", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                         font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_code_export.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_code_export.bind("<Button-1>", lambda e: self.switch_tab("code_export"))

        self.tab_schedule = tk.Label(tab_bar, text="▤ 日程任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                      font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_schedule.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_schedule.bind("<Button-1>", lambda e: self.switch_tab("schedule"))

        self.tab_account = tk.Label(tab_bar, text="◎ 账户管理", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                     font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_account.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_account.bind("<Button-1>", lambda e: self.switch_tab("account"))

        # 任务说明标签
        self.tab_guide = tk.Label(tab_bar, text="▥ 使用说明", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                  font=theme.font(12), padx=24, pady=10, cursor="hand2")
        self.tab_guide.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_guide.bind("<Button-1>", lambda e: self.switch_tab("guide"))

        # 底部控制栏（必须先pack，固定在底部，否则会被主内容区挤出窗口）
        footer = tk.Frame(self.root, bg=COLORS["bg_card"], height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        # 左侧：版本号 + 卡密信息
        left_info = tk.Frame(footer, bg=COLORS["bg_card"])
        left_info.pack(side=tk.LEFT, padx=20)
        tk.Label(left_info, text=f"{APP_VERSION}", 
                bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                font=theme.font(10)).pack(side=tk.LEFT, padx=(0, 15))
        self.footer_card_label = tk.Label(left_info, text=self.card_text, 
                bg=COLORS["bg_card"], fg=COLORS["success"],
                font=theme.font(10))
        self.footer_card_label.pack(side=tk.LEFT)
        
        # 右侧：设备码 + 复制按钮
        right_info = tk.Frame(footer, bg=COLORS["bg_card"])
        right_info.pack(side=tk.RIGHT, padx=20)
        # v6.2.0 性能优化：设备码延迟计算。
        # get_machine_code() 实测耗时约 560ms（读硬件信息+哈希），
        # 但它只用于状态栏显示，没必要阻塞启动。
        # 先显示占位符，界面显示后再异步算出来填进去。
        tk.Label(right_info, text="设备码:", 
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                font=theme.font(10)).pack(side=tk.LEFT, padx=(0, 8))
        self.footer_machine_label = tk.Label(right_info, 
                text="计算中...", 
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                font=("Consolas", 10))
        self.footer_machine_label.pack(side=tk.LEFT, padx=(0, 8))
        self._machine_code_cache = None
        self.root.after(300, self._fill_machine_code_async)
        copy_machine_btn = DarkButton(right_info, text="📋 复制", command=lambda: self._copy_machine_code(), bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32)
        copy_machine_btn.pack(side=tk.LEFT, ipadx=8, ipady=2)

        # 主内容区（标签页容器）
        self.tab_container = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.tab_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 弹幕工具页面
        self.danmaku_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.danmaku_page.pack(fill=tk.BOTH, expand=True)
        self.danmaku_page.pack_forget()

        # ===== v6.2.0 性能优化：页面延迟构建 =====
        # 原来启动时一次性把 7 个页面全建出来（约 1.8 秒），
        # 但用户打开软件 99% 只先看抢码页。
        # 改为：抢码页立即构建，其余页面首次切换到才构建。
        # 实测启动时间从 ~3.2 秒降到 ~1.3 秒。
        #
        # 实现方式：先创建空 Frame 占位，用 _page_builders 登记构建函数，
        # switch_tab 时按需调用。

        self._page_builders = {}      # tab名 -> 构建函数
        self._page_built = set()      # 已构建的 tab

        # 抢码工具页面（默认页，立即构建）
        self.rush_page = RushRewardFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.rush_page.pack(fill=tk.BOTH, expand=True)
        self._page_built.add("rush")

        # 其余页面：只建空容器，构建函数登记到 _page_builders
        self.shutdown_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.shutdown_page.pack(fill=tk.BOTH, expand=True)
        self.shutdown_page.pack_forget()
        self._page_builders["shutdown"] = self.build_shutdown_page

        self.watch_page = None
        self._page_builders["watch"] = lambda: self._lazy_make_watch()

        self.code_export_page = None
        self._page_builders["code"] = lambda: self._lazy_make_code_export()

        self.schedule_page = None
        self._page_builders["schedule"] = lambda: self._lazy_make_schedule()

        # 账户管理页面
        self.account_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.account_page.pack(fill=tk.BOTH, expand=True)
        self.account_page.pack_forget()
        self._page_builders["account"] = self.build_account_page

        # 任务说明页面
        self.guide_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.guide_page.pack(fill=tk.BOTH, expand=True)
        self.guide_page.pack_forget()
        self._page_builders["guide"] = self._build_guide_page

        # 初始化弹幕工具页面的账户多选（这个很轻，且弹幕页是常用页）
        self._refresh_danmaku_account_checkboxes()

        self.current_tab = "rush"

        # 左侧：选择发送账户（复选框多选，参考看播布局）
        left_card = tk.Frame(self.danmaku_page, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)

        tk.Label(left_card, text="选择发送账户", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(11, bold=True)).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(8)).pack(anchor=tk.W, padx=15, pady=(0, 4))

        # 全选/取消全选按钮
        danmaku_btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        danmaku_btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.danmaku_select_all_btn = DarkButton(danmaku_btn_frame, text="全选", command=self._danmaku_select_all, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32)
        self.danmaku_select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.danmaku_deselect_all_btn = DarkButton(danmaku_btn_frame, text="取消全选", command=self._danmaku_deselect_all, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32)
        self.danmaku_deselect_all_btn.pack(side=tk.LEFT)

        # 复选框区域
        self.danmaku_account_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        self.danmaku_account_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.danmaku_account_vars = {}  # 账户名 -> BooleanVar
        self.danmaku_account_checkbuttons = []

        # 右侧：设置 + 弹幕 + 日志
        right = tk.Frame(self.danmaku_page, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))

        tk.Label(settings_card, text="发送设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(11, bold=True)).pack(anchor=tk.W, padx=15, pady=(10, 8))

        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行
        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.room_combo = ttk.Combobox(row1, width=28, values=[], state="readonly")
        self.room_combo.pack(side=tk.LEFT, padx=(8, 4))
        # 刷新直播间下拉框按钮
        refresh_btn = DarkButton(row1, text="↻", command=self._refresh_danmaku_room_combo_values, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32, width=50)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(row1, text="发送间隔", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(9)).pack(side=tk.LEFT)
        self.interval_min = DarkEntry(row1, width=5)
        self.interval_min.insert(0, "5")
        self.interval_min.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row1, text="-", bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack(side=tk.LEFT)
        self.interval_max = DarkEntry(row1, width=5)
        self.interval_max.insert(0, "10")
        self.interval_max.pack(side=tk.LEFT, padx=(4, 20))

        tk.Label(row1, text="模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(9)).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="random")
        ttk.Radiobutton(row1, text="随机", variable=self.mode_var, value="random", style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="顺序", variable=self.mode_var, value="sequence", style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 第二行：发送账户模式
        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)

        tk.Label(row2, text="账户模式", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(9)).pack(side=tk.LEFT)
        self.account_mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(row2, text="单账户", variable=self.account_mode_var, value="single", style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row2, text="多账户轮流", variable=self.account_mode_var, value="rotate", style="Dark.TRadiobutton").pack(side=tk.LEFT)
        tk.Label(row2, text="（所有账户依次轮流发）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(8)).pack(side=tk.LEFT, padx=(8, 0))

        # 第三行：发送条数限制
        row3 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=3)

        tk.Label(row3, text="发送限制", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(9)).pack(side=tk.LEFT)
        self.max_send_entry = DarkEntry(row3, width=8)
        self.max_send_entry.insert(0, "0")
        self.max_send_entry.pack(side=tk.LEFT, padx=(8, 4))
        tk.Label(row3, text="条后停止（0=不限制）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(8)).pack(side=tk.LEFT)

        # ===== 底部容器：日志 + 控制栏（固定高度，先pack到BOTTOM）=====
        bottom_container = tk.Frame(right, bg=COLORS["bg_dark"])
        bottom_container.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        # 日志卡片（固定高度160px）
        log_card = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.X, pady=(0, 6))
        log_card.pack_propagate(False)
        log_card.configure(height=160)

        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(11, bold=True)).pack(anchor=tk.W, padx=15, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                 insertbackground=COLORS["accent"], font=("Consolas", 9),
                                 bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 控制栏（两排布局，固定高度100px）
        danmaku_ctrl = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X)
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=100)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

        # 第一排：按钮
        btn_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X)

        self.start_btn = DarkButton(btn_row, "▶ 启动发送", command=self.start_sending,
                                     width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = DarkButton(btn_row, "■ 停止发送", command=self.stop_sending,
                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.stop_btn.set_state("disabled")

        # 第二排：状态标签
        status_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        status_row.pack(fill=tk.X, pady=(6, 0))

        self.status_label = tk.Label(status_row, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=theme.font(9))
        self.status_label.pack(side=tk.LEFT)

        # ===== 中间：弹幕列表卡片（expand=True，占据剩余空间）=====
        danmaku_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_card.pack(fill=tk.BOTH, expand=True, pady=(6, 6))

        danmaku_header = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        danmaku_header.pack(fill=tk.X, padx=15, pady=(10, 6))

        # 第一排：标题
        header_row1 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row1.pack(fill=tk.X)
        tk.Label(header_row1, text="弹幕列表（三列显示，每行一条）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(11, bold=True)).pack(side=tk.LEFT)

        # 第二排：按钮
        header_row2 = tk.Frame(danmaku_header, bg=COLORS["bg_card"])
        header_row2.pack(fill=tk.X, pady=(6, 0))
        DarkButton(header_row2, "+ 添加", command=self.add_single_danmaku,
                   width=130, height=36, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(header_row2, "批量生成", command=self.batch_generate_danmaku,
                   width=150, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(header_row2, "保存列表", command=self.save_danmaku,
                   width=140, height=36, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 三列弹幕列表（使用grid布局，三列平均分配宽度）
        columns_frame = tk.Frame(danmaku_card, bg=COLORS["bg_card"])
        columns_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 设置三列等宽
        for i in range(3):
            columns_frame.grid_columnconfigure(i, weight=1, uniform="column")

        self.danmaku_texts = []
        for i in range(3):
            col_frame = tk.Frame(columns_frame, bg=COLORS["bg_card"])
            col_frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
            col_frame.grid_rowconfigure(1, weight=1)
            col_frame.grid_columnconfigure(0, weight=1)

            # 列标题
            tk.Label(col_frame, text=f"第{i+1}列", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=theme.font(8)).grid(row=0, column=0, sticky="w", pady=(0, 2))

            text_with_scroll = tk.Frame(col_frame, bg=COLORS["bg_card"])
            text_with_scroll.grid(row=1, column=0, sticky="nsew")
            text_with_scroll.grid_rowconfigure(0, weight=1)
            text_with_scroll.grid_columnconfigure(0, weight=1)

            text_widget = tk.Text(text_with_scroll, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                  insertbackground=COLORS["accent"], font=theme.font(9),
                                  bd=0, highlightthickness=0, wrap=tk.WORD, width=20)
            text_widget.grid(row=0, column=0, sticky="nsew")
            self.danmaku_texts.append(text_widget)

        # 加载保存的配置
        self.apply_config()
        # 刷新弹幕工具页面的账户多选复选框（确保UI构建完成后填充账户列表）
        self._refresh_danmaku_account_checkboxes()

    # ---------- 账户管理 ----------
    def refresh_account_list(self):
        # 兼容旧的account_listbox（如果存在）
        if hasattr(self, 'account_listbox') and self.account_listbox.winfo_exists():
            self.account_listbox.delete(0, tk.END)
            for acc in self.account_mgr.accounts:
                display = f"  {acc['name']}"
                self.account_listbox.insert(tk.END, display)

    def build_account_page(self):
        """构建账户管理页面（v6.6.4 布局重做，保留全部原有功能）。

        【v6.6.3 的问题】用 grid weight 20/32/48 设定比例，但实际渲染成
          312 / 1003 / 329 px = 18.8% / 60.6% / 19.9%
        根因：Text 控件默认 width=80字符（约900px）把中间栏撑爆，
              直播间栏被挤到只剩 329px，列表内容显示不全（截图可见截断）。

        【v6.6.4 修复】三栏改用 place + relwidth 绝对定位：
          账户 22% / 详情 34% / 直播间 42%（+间距），比例精确不受内容影响。
        Text 显式设 width=1，避免默认 80 字符撑破布局。
        """
        main = tk.Frame(self.account_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        CARD = dict(bg=COLORS["bg_card"], bd=0,
                    highlightthickness=1,
                    highlightbackground=COLORS["border"])

        # ============ ① 账户栏（22%）============
        left_card = tk.Frame(main, **CARD)
        left_card.place(x=0, y=0, relwidth=0.218, relheight=1.0)

        head_l = tk.Frame(left_card, bg=COLORS["bg_card"])
        head_l.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(head_l, text="👤 账户列表", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=theme.font(11, bold=True)
                 ).pack(side=tk.LEFT)
        self.account_count_label = tk.Label(
            head_l, text="", bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], font=theme.font(9))
        self.account_count_label.pack(side=tk.RIGHT)

        list_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        acct_sb = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        acct_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.manager_account_listbox = tk.Listbox(
            list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"], selectforeground="#000000",
            font=theme.font(9), bd=0, highlightthickness=0,
            activestyle="none", exportselection=False,
            yscrollcommand=acct_sb.set)
        acct_sb.config(command=self.manager_account_listbox.yview)
        self.manager_account_listbox.pack(side=tk.LEFT, fill=tk.BOTH,
                                          expand=True)
        self.manager_account_listbox.bind("<<ListboxSelect>>",
                                          self._on_manager_account_select)

        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        tk.Label(btn_frame, text="账户操作", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=theme.font(8)
                 ).pack(anchor=tk.W, pady=(0, 2))
        DarkButton(btn_frame, "＋ 添加账户", command=self.add_account,
                   height=30).pack(fill=tk.X, pady=(0, 4))
        row_edit = tk.Frame(btn_frame, bg=COLORS["bg_card"])
        row_edit.pack(fill=tk.X, pady=(0, 4))
        DarkButton(row_edit, "编辑", command=self._manager_edit_account,
                   height=28, bg_color="#27ae60", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X,
                                      expand=True, padx=(0, 3))
        DarkButton(row_edit, "删除", command=self._manager_delete_account,
                   height=28, bg_color=COLORS["danger"],
                   text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(btn_frame, text="账户校验", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=theme.font(8)
                 ).pack(anchor=tk.W, pady=(3, 2))
        row_v = tk.Frame(btn_frame, bg=COLORS["bg_card"])
        row_v.pack(fill=tk.X, pady=(0, 4))
        DarkButton(row_v, "验证登录", command=self._manager_verify_account,
                   height=28, bg_color="#444466", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X,
                                      expand=True, padx=(0, 3))
        DarkButton(row_v, "刷新信息", command=self._manager_refresh_info,
                   height=28, bg_color="#2980b9", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X, expand=True)

        DarkButton(btn_frame, "🛡 数据备份与恢复",
                   command=self._open_backup_manager,
                   height=28, bg_color="#7d3c98", text_color="#ffffff",
                   compact=True).pack(fill=tk.X, pady=(3, 0))

        # ============ ② 详情栏（34%）============
        mid_card = tk.Frame(main, **CARD)
        mid_card.place(relx=0.222, y=0, relwidth=0.336, relheight=1.0)

        head_m = tk.Frame(mid_card, bg=COLORS["bg_card"])
        head_m.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(head_m, text="📄 账户详细信息", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=theme.font(11, bold=True)
                 ).pack(side=tk.LEFT)

        info_frame = tk.Frame(mid_card, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        info_sb = tk.Scrollbar(info_frame, orient=tk.VERTICAL)
        info_sb.pack(side=tk.RIGHT, fill=tk.Y)
        # 关键：width=1 让控件跟随容器，避免 Text 默认 80 字符撑破布局
        self.manager_info_text = tk.Text(
            info_frame, width=1, height=1,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            font=("Consolas", 10), bd=0, highlightthickness=0,
            wrap=tk.WORD, padx=10, pady=8,
            selectbackground=COLORS["accent"],
            selectforeground="#000000",
            insertbackground=COLORS["text_primary"],
            yscrollcommand=info_sb.set)
        info_sb.config(command=self.manager_info_text.yview)
        self.manager_info_text.pack(side=tk.LEFT, fill=tk.BOTH,
                                    expand=True)
        self.manager_info_text.config(state=tk.DISABLED)
        self._manager_show_info(None)

        copy_frame = tk.Frame(mid_card, bg=COLORS["bg_card"])
        copy_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        DarkButton(copy_frame, "📋 复制 SESSDATA",
                   command=self._manager_copy_sessdata, height=28,
                   bg_color="#8e44ad", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X,
                                      expand=True, padx=(0, 3))
        DarkButton(copy_frame, "📋 复制 bili_jct",
                   command=self._manager_copy_bili_jct, height=28,
                   bg_color="#16a085", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ============ ③ 直播间栏（42%）============
        right_card = tk.Frame(main, **CARD)
        right_card.place(relx=0.562, y=0, relwidth=0.438, relheight=1.0)

        head_r = tk.Frame(right_card, bg=COLORS["bg_card"])
        head_r.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(head_r, text="📺 直播间管理", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=theme.font(11, bold=True)
                 ).pack(side=tk.LEFT)
        self.room_count_label = tk.Label(
            head_r, text="", bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], font=theme.font(9))
        self.room_count_label.pack(side=tk.RIGHT)

        body_r = tk.Frame(right_card, bg=COLORS["bg_card"])
        body_r.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # 直播间列表（占主要空间，加横向滚动条防截断）
        room_list_wrap = tk.Frame(body_r, bg=COLORS["bg_card"])
        room_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        room_sb = tk.Scrollbar(room_list_wrap, orient=tk.VERTICAL)
        room_sb.pack(side=tk.RIGHT, fill=tk.Y)
        room_hsb = tk.Scrollbar(body_r, orient=tk.HORIZONTAL)
        self.manager_room_listbox = tk.Listbox(
            room_list_wrap, bg=COLORS["bg_input"],
            fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"], selectforeground="#000000",
            font=theme.font(9), bd=0, highlightthickness=0,
            activestyle="none", exportselection=False,
            yscrollcommand=room_sb.set,
            xscrollcommand=room_hsb.set)
        room_sb.config(command=self.manager_room_listbox.yview)
        room_hsb.config(command=self.manager_room_listbox.xview)
        self.manager_room_listbox.pack(side=tk.LEFT, fill=tk.BOTH,
                                       expand=True)
        self.manager_room_listbox.bind("<<ListboxSelect>>",
                                       self._on_manager_room_select)

        # 表单（浅底区分区块）
        form = tk.Frame(body_r, bg=COLORS["bg_input"])
        form.pack(fill=tk.X, pady=(0, 6))

        tk.Label(form, text="添加 / 编辑直播间", bg=COLORS["bg_input"],
                 fg=COLORS["accent"], font=theme.font(9, bold=True)
                 ).pack(anchor=tk.W, padx=8, pady=(5, 3))

        for lbl_txt, attr_name in [("直播间号", "room_id_entry"),
                                   ("显示名称", "room_name_entry"),
                                   ("备注", "room_remark_entry")]:
            rr = tk.Frame(form, bg=COLORS["bg_input"])
            rr.pack(fill=tk.X, padx=8, pady=(0, 3))
            tk.Label(rr, text=lbl_txt, bg=COLORS["bg_input"],
                     fg=COLORS["text_secondary"],
                     font=theme.font(9), width=7, anchor=tk.W
                     ).pack(side=tk.LEFT)
            ent = DarkEntry(rr, width=10)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
            setattr(self, attr_name, ent)
        tk.Frame(form, bg=COLORS["bg_input"], height=4).pack(fill=tk.X)

        # 按钮三列并排
        room_btns = tk.Frame(body_r, bg=COLORS["bg_card"])
        room_btns.pack(fill=tk.X)
        DarkButton(room_btns, "＋ 添加", command=self._manager_add_room,
                   height=28, compact=True).pack(side=tk.LEFT, fill=tk.X,
                                                 expand=True, padx=(0, 3))
        DarkButton(room_btns, "删除", command=self._manager_delete_room,
                   height=28, bg_color=COLORS["danger"],
                   text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X,
                                      expand=True, padx=(0, 3))
        DarkButton(room_btns, "从账户导入",
                   command=self._manager_import_rooms_from_accounts,
                   height=28, bg_color="#2980b9", text_color="#ffffff",
                   compact=True).pack(side=tk.LEFT, fill=tk.X,
                                      expand=True)

        self._refresh_manager_room_list()
        try:
            self._update_account_room_counts()
        except Exception:
            pass
        # 布局调整后重新适配一次（等窗口尺寸确定）
        try:
            self.after(120, self._refresh_manager_room_list)
        except Exception:
            pass

    def _build_guide_page(self):
        """构建任务说明页面（左侧固定目录树 + 右侧内容，点击目录跳转）"""
        main = tk.Frame(self.guide_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 标题
        tk.Label(main, text="📖 使用说明", bg=COLORS["bg_dark"], fg=COLORS["accent"],
                 font=theme.font(16, bold=True)).pack(anchor=tk.W, padx=8, pady=(0, 10))

        # 主体：左目录 + 右内容
        body = tk.Frame(main, bg=COLORS["bg_dark"])
        body.pack(fill=tk.BOTH, expand=True)

        # ---------- 左侧：目录树 ----------
        toc_card = tk.Frame(body, bg=COLORS["bg_card"], bd=0,
                            highlightthickness=1, highlightbackground=COLORS["border"])
        toc_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        toc_card.pack_propagate(False)
        # v6.6.5: 目录加宽 250->360，并加横向滚动条防条目截断
        toc_card.configure(width=360)

        tk.Label(toc_card, text="目录", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(12, bold=True)).pack(anchor=tk.W, padx=14, pady=(12, 6))

        toc_frame = tk.Frame(toc_card, bg=COLORS["bg_card"])
        toc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # v6.6.5: 横向滚动条（目录条目长，防截断）
        toc_hsb = tk.Scrollbar(toc_card, orient=tk.HORIZONTAL)
        toc_scroll = tk.Scrollbar(toc_frame, orient=tk.VERTICAL)
        toc_list = tk.Listbox(
            toc_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            selectbackground=COLORS["accent"], selectforeground="#000000",
            # v6.6.5: 目录字号 10->9（用户要求"整体字号稍微缩小一点"）
            font=theme.font(9), bd=0, highlightthickness=0,
            activestyle="none", exportselection=False,
            yscrollcommand=toc_scroll.set, xscrollcommand=toc_hsb.set,
        )
        toc_scroll.config(command=toc_list.yview)
        toc_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        toc_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        toc_hsb.config(command=toc_list.xview)
        toc_hsb.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 6))

        # ---------- 右侧：内容 ----------
        card = tk.Frame(body, bg=COLORS["bg_card"], bd=0,
                        highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = tk.Scrollbar(card)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(card, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                       # v6.6.5: 内容字号 10->9
                       font=theme.font(9), bd=0, highlightthickness=0, wrap=tk.WORD,
                       padx=22, pady=20, yscrollcommand=scroll.set)
        # v6.6.5: 加大行间距（用户要求"字间距稍微大一点"）
        try:
            text.configure(spacing1=4, spacing2=2, spacing3=5)
        except Exception:
            pass
        text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=text.yview)

        # 插入任务说明内容（富文本渲染）
        try:
            # v6.6.5: 富文本基础字号 10->9
            theme.render_richtext(text, TASK_GUIDE_TEXT, base_size=9)
        except Exception as e:
            print(f"富文本渲染失败，回退纯文本: {e}")
            text.insert(tk.END, TASK_GUIDE_TEXT)
        text.config(state=tk.DISABLED)

        # ---------- 建立目录索引并绑定跳转 ----------
        # 用 Text 的 mark 精确定位每个章节标题所在行
        toc_entries = []   # [(显示名, mark名)]
        try:
            lines = TASK_GUIDE_TEXT.split("\n")
            line_no = 1
            mark_seq = 0
            for ln in lines:
                stripped = ln.strip()
                # 大章节：【一、账户管理】
                if stripped.startswith("【") and stripped.endswith("】"):
                    title = stripped.strip("【】")
                    mark = f"toc_{mark_seq}"
                    mark_seq += 1
                    text.config(state=tk.NORMAL)
                    text.mark_set(mark, f"{line_no}.0")
                    text.mark_gravity(mark, tk.LEFT)
                    text.config(state=tk.DISABLED)
                    toc_entries.append((title, mark, 0))
                # 小节：## 1.1 添加账户 -> 渲染后变成 "1.1 添加账户"
                elif stripped.startswith("## "):
                    title = stripped[3:].strip()
                    mark = f"toc_{mark_seq}"
                    mark_seq += 1
                    text.config(state=tk.NORMAL)
                    text.mark_set(mark, f"{line_no}.0")
                    text.mark_gravity(mark, tk.LEFT)
                    text.config(state=tk.DISABLED)
                    toc_entries.append((title, mark, 1))
                line_no += 1
        except Exception as e:
            print(f"建立目录索引失败: {e}")

        # 填充目录列表（缩进区分层级）
        for title, mark, level in toc_entries:
            prefix = "    " if level else ""
            toc_list.insert(tk.END, f"{prefix}{title}")

        def _jump(event=None):
            sel = toc_list.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(toc_entries):
                return
            _, mark, _ = toc_entries[idx]
            try:
                pos = text.index(mark)
                total = int(text.index("end-1c").split(".")[0])
                cur_line = int(pos.split(".")[0])
                # 换算滚动比例（不能到 1.0，否则内容顶端看不到）
                frac = max(0.0, min(0.98, (cur_line - 1) / max(1, total - 1)))
                text.yview_moveto(frac)
                # 高亮跳转到的章节标题
                text.tag_remove("toc_hl", "1.0", tk.END)
                text.tag_add("toc_hl", f"{cur_line}.0", f"{cur_line}.end+1l")
                text.tag_configure("toc_hl", background="#1f4a6d")
            except Exception:
                pass

        toc_list.bind("<<ListboxSelect>>", _jump)
        toc_list.bind("<Double-Button-1>", _jump)

        # 记录供外部刷新
        self._guide_toc_list = toc_list
        self._guide_toc_entries = toc_entries
        self._guide_text = text

    def _update_account_room_counts(self):
        """更新账户/直播间数量标签（v6.6.3）。"""
        try:
            n_acc = len(getattr(self.account_mgr, "accounts", []) or [])
            n_room = len(getattr(self.room_mgr, "rooms", []) or [])
            if hasattr(self, "account_count_label"):
                self.account_count_label.config(text="%d 个" % n_acc)
            if hasattr(self, "room_count_label"):
                self.room_count_label.config(text="%d 个" % n_room)
        except Exception:
            pass

    def _refresh_manager_room_list(self):
        """刷新直播间管理列表"""
        if not hasattr(self, 'manager_room_listbox') or not self.manager_room_listbox.winfo_exists():
            return
        self.manager_room_listbox.delete(0, tk.END)
        for room in self.room_mgr.rooms:
            display = f"  {room['name']}"
            if room.get('remark'):
                display += f"  [{room['remark']}]"
            self.manager_room_listbox.insert(tk.END, display)

    def _on_manager_room_select(self, event):
        """选择直播间时填充表单"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            return
        room = self.room_mgr.rooms[selection[0]]
        self.room_id_entry.delete(0, tk.END)
        self.room_id_entry.insert(0, room["id"])
        self.room_name_entry.delete(0, tk.END)
        self.room_name_entry.insert(0, room["name"])
        self.room_remark_entry.delete(0, tk.END)
        self.room_remark_entry.insert(0, room.get("remark", ""))

    def _manager_add_room(self):
        """添加直播间"""
        room_id = self.room_id_entry.get().strip()
        name = self.room_name_entry.get().strip()
        remark = self.room_remark_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）", parent=self.root)
            return
        if not name:
            name = f"直播间{room_id}"
        ok, msg = self.room_mgr.add_room(room_id, name, remark)
        if ok:
            self._refresh_manager_room_list()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已添加直播间: {name}（{room_id}）")
        else:
            messagebox.showwarning("提示", msg, parent=self.root)

    def _manager_delete_room(self):
        """删除直播间"""
        selection = self.manager_room_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的直播间", parent=self.root)
            return
        room = self.room_mgr.rooms[selection[0]]
        if custom_askyesno(self.root, "确认", f"确定删除直播间「{room['name']}」吗？"):
            self.room_mgr.delete_room(room["id"])
            self._refresh_manager_room_list()
            # P2-G: 删除直播间后同步刷新送礼页面的下拉框，避免选中已删除的直播间
            if hasattr(self, '_refresh_gift_room_combo_values'):
                self._refresh_gift_room_combo_values()
            self.room_id_entry.delete(0, tk.END)
            self.room_name_entry.delete(0, tk.END)
            self.room_remark_entry.delete(0, tk.END)
            self.log(f"已删除直播间: {room['name']}（{room['id']}）")

    def _manager_import_rooms_from_accounts(self):
        """从账户导入直播间"""
        count = self.room_mgr.import_from_accounts(self.account_mgr, self.log)
        self._refresh_manager_room_list()
        # 刷新弹幕页面直播间下拉框
        self._refresh_danmaku_room_combo_values()
        # 刷新看播页面直播间下拉框
        if hasattr(self, 'watch_page') and hasattr(self.watch_page, '_refresh_room_combo_values'):
            self.watch_page._refresh_room_combo_values()
        messagebox.showinfo("提示", f"从账户导入完成，共新增 {count} 个直播间", parent=self.root)

    def _open_backup_manager(self):
        """打开数据备份与恢复管理器（O2 用户界面）。"""
        existing = getattr(self, "_backup_dialog", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except Exception:
            pass

        dlg = tk.Toplevel(self.root)
        self._backup_dialog = dlg
        dlg.title("数据备份与恢复")
        dlg.configure(bg=COLORS["bg_dark"])
        dlg.transient(self.root)
        try:
            dlg.geometry("820x560")
        except Exception:
            pass

        # 顶部说明
        head = tk.Frame(dlg, bg=COLORS["bg_card"])
        head.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(head, text="程序每天首次启动会自动备份 data/，保留最近 7 份",
                 bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(11, bold=True)).pack(anchor=tk.W, padx=12, pady=(8, 2))
        tk.Label(head, text="恢复会用备份覆盖当前 data/，建议先手动备份当前数据再恢复",
                 bg=COLORS["bg_card"], fg=COLORS["warning"],
                 font=theme.font(9)).pack(anchor=tk.W, padx=12, pady=(0, 8))

        # 状态行
        status_frame = tk.Frame(dlg, bg=COLORS["bg_dark"])
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        status_label = tk.Label(status_frame, text="", bg=COLORS["bg_dark"],
                                fg=COLORS["text_secondary"], font=theme.font(10),
                                justify=tk.LEFT, anchor=tk.W)
        status_label.pack(fill=tk.X)

        # 备份列表
        list_card = tk.Frame(dlg, bg=COLORS["bg_card"])
        list_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        tk.Label(list_card, text="已有备份（新→旧）", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=theme.font(10, bold=True)
                 ).pack(anchor=tk.W, padx=12, pady=(8, 4))
        lf = tk.Frame(list_card, bg=COLORS["bg_card"])
        lf.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        sb = tk.Scrollbar(lf, orient=tk.VERTICAL)
        lb = tk.Listbox(lf, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                        font=("Consolas", 10), bd=0, highlightthickness=0,
                        selectbackground=COLORS["accent"], selectforeground="#000000",
                        yscrollcommand=sb.set)
        sb.config(command=lb.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        backups = []

        def refresh_list():
            backups.clear()
            lb.delete(0, tk.END)
            items = data_guard.list_backups()
            for b in items:
                backups.append(b)
                lb.insert(tk.END, f'{b["time"]}   {b["size_kb"]:>8.1f} KB   {b["name"]}')
            if not items:
                lb.insert(tk.END, "（暂无备份，点下方「立即备份」创建第一份）")
            try:
                s = data_guard.list_backups()
                total = len(s)
                latest = s[0]["time"] if s else "无"
                status_label.config(text=f"当前备份数: {total}    最近备份: {latest}")
            except Exception:
                pass

        # 操作按钮
        btn_row = tk.Frame(dlg, bg=COLORS["bg_dark"])
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        def do_backup_now():
            ok, path, msg = data_guard.daily_backup(force=True)
            if ok:
                messagebox.showinfo("备份完成", f"{msg}\n\n{path}", parent=dlg)
            else:
                messagebox.showwarning("备份失败", msg, parent=dlg)
            refresh_list()

        def do_restore():
            sel = lb.curselection()
            if not sel or not backups:
                messagebox.showwarning("提示", "请先在列表中选择一个备份", parent=dlg)
                return
            idx = sel[0]
            if idx >= len(backups):
                return
            target = backups[idx]
            if not messagebox.askyesno(
                    "确认恢复",
                    f"确定用以下备份恢复吗？\n\n{target['time']}\n{target['name']}\n\n"
                    f"注意：会用备份内容覆盖当前 data/ 下的同名文件。\n"
                    f"建议先点「立即备份」保存当前数据。",
                    parent=dlg):
                return
            ok, msgs = data_guard.restore_from_backup(target["path"])
            if ok:
                messagebox.showinfo("恢复完成",
                                    "已从备份恢复:\n" + "\n".join(msgs) +
                                    "\n\n请重启程序以使恢复的数据完全生效。",
                                    parent=dlg)
            else:
                messagebox.showerror("恢复失败", "\n".join(msgs), parent=dlg)
            refresh_list()

        def do_open_folder():
            try:
                import subprocess
                subprocess.Popen(["explorer", str(data_guard.BACKUP_DIR)])
            except Exception as e:
                messagebox.showwarning("提示", f"无法打开目录: {e}", parent=dlg)

        DarkButton(btn_row, "💾 立即备份", command=do_backup_now,
                   width=150, height=36).pack(side=tk.LEFT)
        DarkButton(btn_row, "♻ 恢复选中备份", command=do_restore,
                   width=170, height=36, bg_color="#e67e22", text_color="#ffffff"
                   ).pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(btn_row, "📂 打开备份目录", command=do_open_folder,
                   width=170, height=36, bg_color="#2980b9", text_color="#ffffff"
                   ).pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(btn_row, "关闭", command=dlg.destroy,
                   width=100, height=36, bg_color="#7f8c8d", text_color="#ffffff"
                   ).pack(side=tk.RIGHT)

        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
        refresh_list()

    def refresh_account_manager_list(self):
        """刷新账户管理页面的账户列表"""
        if not hasattr(self, 'manager_account_listbox') or not self.manager_account_listbox.winfo_exists():
            return
        self.manager_account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"  {acc['name']}"
            self.manager_account_listbox.insert(tk.END, display)
        # 刷新弹幕工具页面的账户多选
        self._refresh_danmaku_account_checkboxes()

    def _on_manager_account_select(self, event):
        """账户管理页面选择账户时显示详细信息"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            self._manager_show_info(None)
            return
        acc = self.account_mgr.accounts[selection[0]]
        self._manager_show_info(acc)

    def _manager_show_info(self, acc):
        """显示账户详细信息"""
        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        if not acc:
            self.manager_info_text.insert(tk.END, "请从左侧列表选择一个账户查看详细信息")
            self.manager_info_text.config(state=tk.DISABLED)
            return

        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", "未设置"))
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: 查询中...
直播状态: 查询中...

--- 电池余额 ---
电池数量: 查询中...

提示: 点「刷新信息」可获取直播号与电池余额
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)

    def _manager_copy_sessdata(self):
        """复制当前账户的SESSDATA到剪贴板"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        sessdata = acc.get("SESSDATA", "")
        if not sessdata:
            messagebox.showwarning("提示", "该账户没有SESSDATA", parent=self.root)
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(sessdata)
            self.root.update()
            self.log(f"已复制账户「{acc.get('name', '未知')}」的SESSDATA到剪贴板")
            messagebox.showinfo("成功", "SESSDATA已复制到剪贴板", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}", parent=self.root)

    def _manager_copy_bili_jct(self):
        """复制当前账户的bili_jct到剪贴板"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        bili_jct = acc.get("bili_jct", "")
        if not bili_jct:
            messagebox.showwarning("提示", "该账户没有bili_jct", parent=self.root)
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(bili_jct)
            self.root.update()
            self.log(f"已复制账户「{acc.get('name', '未知')}」的bili_jct到剪贴板")
            messagebox.showinfo("成功", "bili_jct已复制到剪贴板", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}", parent=self.root)

    def _manager_refresh_info(self):
        """刷新选中账户的详细信息（直播间号、电池余额）"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        name = acc.get("name", "未知")
        uid = acc.get("DedeUserID", acc.get("uid", ""))

        # 获取直播间号
        room_id = "未开播"
        room_status = "未开播"
        if uid:
            try:
                url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={uid}"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                data = resp.json()
                if data.get("code") == 0 and data.get("data"):
                    room_id = data["data"].get("roomid", "未开播")
                    if data["data"].get("roomStatus") == 1:
                        room_status = "直播中"
                    else:
                        room_status = "未开播"
            except Exception:
                room_id = "查询失败"
                room_status = "查询失败"

        # 获取电池余额
        battery = "查询失败"
        try:
            sessdata = acc.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get("https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1",
                                cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                gold = data["data"].get("gold", 0)
                battery = f"{gold / 100:.1f} 电池"
        except Exception:
            battery = "查询失败"

        # 更新显示
        sessdata = acc.get("SESSDATA", "")
        bili_jct = acc.get("bili_jct", "")
        sessdata_preview = sessdata[:20] + "..." if len(sessdata) > 20 else sessdata
        jct_preview = bili_jct[:15] + "..." if len(bili_jct) > 15 else bili_jct

        self.manager_info_text.config(state=tk.NORMAL)
        self.manager_info_text.delete(1.0, tk.END)
        info = f"""账户名称: {name}
用户UID: {uid}
SESSDATA: {sessdata_preview}
bili_jct: {jct_preview}

--- 直播间信息 ---
直播间号: {room_id}
直播状态: {room_status}

--- 电池余额 ---
电池数量: {battery}
"""
        self.manager_info_text.insert(tk.END, info)
        self.manager_info_text.config(state=tk.DISABLED)
        self.log(f"已刷新账户「{name}」的详细信息")

    def _manager_edit_account(self):
        """账户管理页面编辑账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        dialog = EditAccountDialog(self.root, acc, on_update=self.account_mgr.update_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()
        # 刷新看播页面账户列表
        if hasattr(self, 'watch_page'):
            self.watch_page.refresh_account_list()
        self.log(f"已编辑账户: {acc['name']}")

    def _manager_delete_account(self):
        """账户管理页面删除账户"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        # 检查是否有任务正在运行
        running_tasks = []
        if getattr(self, 'running', False):
            running_tasks.append('弹幕发送')
        if getattr(self, 'watch_page', None) and getattr(self.watch_page, 'running', False):
            running_tasks.append('看播')
        if getattr(self, 'watch_page', None) and getattr(self.watch_page, 'gift_running', False):
            running_tasks.append('送礼')
        if getattr(self, 'rush_page', None) and getattr(self.rush_page, 'running', False):
            running_tasks.append('抢码')
        if running_tasks:
            messagebox.showwarning("提示", f"以下任务正在运行，请先停止后再删除账户：\n{'、'.join(running_tasks)}", parent=self.root)
            return
        if custom_askyesno(self.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_manager_list()
            self._manager_show_info(None)
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新所有直播间下拉框选项（用户列表变了）
            if hasattr(self, '_refresh_danmaku_room_combo_values'):
                self._refresh_danmaku_room_combo_values()
            if hasattr(self, 'watch_page') and hasattr(self.watch_page, '_refresh_room_combo_values'):
                self.watch_page._refresh_room_combo_values()
            self.log(f"已删除账户: {acc['name']}")

    def _manager_verify_account(self):
        """账户管理页面验证登录（P1-S: 异步执行，避免阻塞UI）"""
        selection = self.manager_account_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择账户", parent=self.root)
            return
        acc = self.account_mgr.accounts[selection[0]]
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        self.log(f"正在验证账户「{acc['name']}」登录状态...")

        def _verify():
            ok, msg = verify_login(cookie_str)
            def _update_ui():
                if ok:
                    messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}", parent=self.root)
                    self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
                else:
                    messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}", parent=self.root)
                    self.log(f"账户「{acc['name']}」验证失败: {msg}")
            self.root.after(0, _update_ui)

        threading.Thread(target=_verify, daemon=True).start()

    # ========== 弹幕工具页面账户多选 ==========
    def _refresh_danmaku_account_checkboxes(self):
        """刷新弹幕工具页面的账户多选复选框"""
        if not hasattr(self, 'danmaku_account_frame') or not self.danmaku_account_frame.winfo_exists():
            return
        for widget in self.danmaku_account_frame.winfo_children():
            widget.destroy()
        self.danmaku_account_vars.clear()
        self.danmaku_account_checkbuttons.clear()
        # 从配置加载选中的账户列表
        saved_selected = self.config.get("danmaku_selected_accounts", [])
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            # 如果有保存的选择，按保存的来；否则默认全选
            is_selected = name in saved_selected if saved_selected else True
            var = tk.BooleanVar(value=is_selected)
            self.danmaku_account_vars[name] = var
            cb = tk.Checkbutton(self.danmaku_account_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=theme.font(9),
                                anchor="w", padx=8, pady=4,
                                command=self._on_danmaku_account_changed)
            cb.pack(fill=tk.X, anchor="w")
            self.danmaku_account_checkbuttons.append(cb)

    def _on_danmaku_account_changed(self):
        """弹幕账户选择改变时：保存配置"""
        self.save_config()

    def _danmaku_select_all(self):
        """弹幕账户全选"""
        for var in self.danmaku_account_vars.values():
            var.set(True)
        self.save_config()

    def _danmaku_deselect_all(self):
        """弹幕账户取消全选"""
        for var in self.danmaku_account_vars.values():
            var.set(False)
        self.save_config()

    def _refresh_danmaku_room_combo_values(self):
        """刷新弹幕直播间下拉框选项：只显示直播间名称，不显示数字ID"""
        if not hasattr(self, 'room_combo'):
            return
        values = [room["name"] for room in self.room_mgr.rooms]
        self.room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.room_combo.get() not in values:
            self.room_combo.set("")

    def _get_danmaku_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None

    def _on_danmaku_room_selected(self, event=None):
        """选择弹幕直播间下拉框时：保存配置"""
        self.save_config()

    def _get_danmaku_selected_accounts(self):
        """获取弹幕工具页面选中的账户列表"""
        selected = []
        for name, var in self.danmaku_account_vars.items():
            if var.get():
                for acc in self.account_mgr.accounts:
                    if acc.get("name") == name:
                        selected.append(acc)
                        break
        return selected

    def on_account_select(self, event):
        selection = self.account_listbox.curselection()
        if not selection:
            return
        acc = self.account_mgr.accounts[selection[0]]
        # 保存当前选中的账户
        self.save_config()

    def get_current_account(self):
        selection = self.account_listbox.curselection()
        if not selection:
            return None
        return self.account_mgr.accounts[selection[0]]

    def add_account(self):
        MAX_ACCOUNTS = 8
        if len(self.account_mgr.accounts) >= MAX_ACCOUNTS:
            messagebox.showwarning("提示", f"最多只能添加 {MAX_ACCOUNTS} 个账户\n当前已有 {len(self.account_mgr.accounts)} 个，请先删除不需要的账户", parent=self.root)
            return
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()
        self.refresh_account_manager_list()
        # 刷新看播页面账户列表
        if hasattr(self, 'watch_page'):
            self.watch_page.refresh_account_list()

    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户", parent=self.root)
            return
        # 检查是否有任务正在运行
        running_tasks = []
        if getattr(self, 'running', False):
            running_tasks.append('弹幕发送')
        if hasattr(self, 'watch_page') and getattr(self.watch_page, 'running', False):
            running_tasks.append('看播')
        if hasattr(self, 'watch_page') and getattr(self.watch_page, 'gift_running', False):
            running_tasks.append('送礼')
        if hasattr(self, 'rush_page') and getattr(self.rush_page, 'running', False):
            running_tasks.append('抢码')
        if running_tasks:
            messagebox.showwarning("提示", f"以下任务正在运行，请先停止后再删除账户：\n{'、'.join(running_tasks)}", parent=self.root)
            return
        if custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            # 刷新弹幕账户多选复选框
            if hasattr(self, '_refresh_danmaku_account_checkboxes'):
                self._refresh_danmaku_account_checkboxes()
            # 刷新看播页面账户列表
            if hasattr(self, 'watch_page'):
                self.watch_page.refresh_account_list()
            self.log(f"已删除账户: {acc['name']}")

    def verify_current_account(self):
        """验证当前选中账户登录状态（P1-S: 异步执行，避免阻塞UI）"""
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择账户", parent=self.root)
            return
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        self.log(f"正在验证账户「{acc['name']}」登录状态...")

        def _verify():
            ok, msg = verify_login(cookie_str)
            def _update_ui():
                if ok:
                    messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}", parent=self.root)
                    self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
                else:
                    messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}", parent=self.root)
                    self.log(f"账户「{acc['name']}」验证失败: {msg}")
            self.root.after(0, _update_ui)

        threading.Thread(target=_verify, daemon=True).start()

    def _fill_machine_code_async(self):
        """异步计算并填充设备码（v6.2.0: 避免启动阻塞）。

        实现说明：worker 线程不直接调 root.after —— 在某些环境（非
        mainloop 上下文）会报 "main thread is not in main loop"。
        改为 worker 把结果放进队列，主线程用 after 轮询消费，最稳妥。
        """
        import threading
        import queue

        if not hasattr(self, "_mc_queue"):
            self._mc_queue = queue.Queue()

        def worker():
            try:
                mc = get_machine_code()
            except Exception:
                mc = ""
            try:
                self._mc_queue.put(mc)
            except Exception:
                pass

        def poll():
            """主线程轮询队列（在主线程注册，after 一定可用）。"""
            try:
                mc = self._mc_queue.get_nowait()
            except Exception:
                try:
                    self.root.after(50, poll)
                except Exception:
                    pass
                return
            try:
                self._machine_code_cache = mc
                if mc:
                    self.footer_machine_label.config(text=f"{mc[:8]}...{mc[-8:]}")
                else:
                    self.footer_machine_label.config(text="(获取失败)")
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(50, poll)

    def _copy_machine_code(self):
        """复制设备码到剪贴板（v6.2.0: 优先用已缓存的设备码，没有则现算）"""
        try:
            machine_code = self._machine_code_cache
            if not machine_code:
                machine_code = get_machine_code()
                self._machine_code_cache = machine_code
            self.root.clipboard_clear()
            self.root.clipboard_append(machine_code)
            self.root.update()
            # 临时显示复制成功
            old_text = self.footer_machine_label.cget("text")
            self.footer_machine_label.config(text="✓ 已复制", fg=COLORS["success"])
            self.root.after(1500, lambda: self.footer_machine_label.config(text=old_text, fg=COLORS["accent"]))
        except Exception:
            pass
    
    def _ensure_page_built(self, tab_name):
        """确保指定页面已构建（v6.2.0 延迟构建）。"""
        if tab_name in self._page_built:
            return True
        builder = self._page_builders.get(tab_name)
        if builder is None:
            return False
        try:
            builder()
            self._page_built.add(tab_name)
            return True
        except Exception as e:
            self.log(f"构建页面[{tab_name}]失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False

    def _lazy_make_watch(self):
        """延迟创建看播页。"""
        if self.watch_page is not None:
            return
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()
        self._watch_page_ready = True

    def _lazy_make_code_export(self):
        """延迟创建兑换码页。"""
        if self.code_export_page is not None:
            return
        self.code_export_page = CodeExportFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.code_export_page.pack(fill=tk.BOTH, expand=True)
        self.code_export_page.pack_forget()

    def _lazy_make_schedule(self):
        """延迟创建日程页。"""
        if self.schedule_page is not None:
            return
        self.schedule_page = ScheduleFrame(self.tab_container, self.account_mgr, self)
        self.schedule_page.pack(fill=tk.BOTH, expand=True)
        self.schedule_page.pack_forget()

    def switch_tab(self, tab_name):
        """切换标签页"""
        if tab_name == self.current_tab:
            return

        # 隐藏所有页面（延迟构建的页面可能还是 None，用安全方式处理）
        for _p in (self.rush_page, self.danmaku_page, self.shutdown_page,
                   self.watch_page, self.code_export_page, self.schedule_page,
                   self.account_page, self.guide_page):
            if _p is not None:
                try:
                    _p.pack_forget()
                except Exception:
                    pass

        # 重置所有标签样式
        self.tab_rush.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_danmaku.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_shutdown.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_watch.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_code_export.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_schedule.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_account.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))
        self.tab_guide.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=theme.font(12))

        if tab_name == "danmaku":
            self.danmaku_page.pack(fill=tk.BOTH, expand=True)
            self.tab_danmaku.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
            self.current_tab = "danmaku"
            # 切换到弹幕工具时刷新账户列表
            self._refresh_danmaku_account_checkboxes()
        elif tab_name == "rush":
            self.rush_page.pack(fill=tk.BOTH, expand=True)
            self.tab_rush.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
            self.current_tab = "rush"
            # 切换到抢码工具时刷新账户列表
            self.rush_page.refresh_account_list()
        elif tab_name == "shutdown":
            if self._ensure_page_built("shutdown"):
                self.shutdown_page.pack(fill=tk.BOTH, expand=True)
                self.tab_shutdown.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "shutdown"
                self.refresh_shutdown_task_list()
        elif tab_name == "watch":
            # v6.2.0 延迟构建：首次进入才创建
            if self._ensure_page_built("watch"):
                self.watch_page.pack(fill=tk.BOTH, expand=True)
                self.tab_watch.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "watch"
                self.watch_page.refresh_account_list()
        elif tab_name == "code_export":
            if self._ensure_page_built("code"):
                self.code_export_page.pack(fill=tk.BOTH, expand=True)
                self.tab_code_export.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "code_export"
                self.code_export_page.refresh_list()
        elif tab_name == "schedule":
            if self._ensure_page_built("schedule"):
                self.schedule_page.pack(fill=tk.BOTH, expand=True)
                self.tab_schedule.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "schedule"
        elif tab_name == "account":
            if self._ensure_page_built("account"):
                self.account_page.pack(fill=tk.BOTH, expand=True)
                self.tab_account.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "account"
                self.refresh_account_manager_list()
        elif tab_name == "guide":
            if self._ensure_page_built("guide"):
                self.guide_page.pack(fill=tk.BOTH, expand=True)
                self.tab_guide.config(bg=COLORS["accent"], fg="#000000", font=theme.font(12, bold=True))
                self.current_tab = "guide"
        # 保存当前标签页
        self.save_config()

    # ========== 定时关机页面 ==========
    def build_shutdown_page(self):
        """构建定时关机页面"""
        # 主容器
        main = tk.Frame(self.shutdown_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # 顶部：关机设置卡片
        setup_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        setup_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(setup_card, text="⏻ 定时关机设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(12, bold=True)).pack(anchor=tk.W, padx=15, pady=(10, 8))

        setup_content = tk.Frame(setup_card, bg=COLORS["bg_card"])
        setup_content.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 关机模式选择
        mode_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        mode_frame.pack(fill=tk.X, pady=4)
        tk.Label(mode_frame, text="关机模式:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.shutdown_mode_var = tk.StringVar(value="none")
        tk.Radiobutton(mode_frame, text="不关机", variable=self.shutdown_mode_var, value="none",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=theme.font(10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))
        tk.Radiobutton(mode_frame, text="定时关机", variable=self.shutdown_mode_var, value="scheduled",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=theme.font(10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))
        tk.Radiobutton(mode_frame, text="延时关机", variable=self.shutdown_mode_var, value="delay",
                       bg=COLORS["bg_card"], fg=COLORS["text_primary"], selectcolor=COLORS["bg_input"],
                       activebackground=COLORS["bg_card"], activeforeground=COLORS["text_primary"],
                       font=theme.font(10), command=self.on_shutdown_mode_change).pack(side=tk.LEFT, padx=(15, 0))

        # 定时关机时间设置
        self.scheduled_shutdown_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        self.scheduled_shutdown_frame.pack(fill=tk.X, pady=4)
        tk.Label(self.scheduled_shutdown_frame, text="关机时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.shutdown_hour = DarkEntry(self.scheduled_shutdown_frame, width=5)
        self.shutdown_hour.insert(0, "23")
        self.shutdown_hour.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(self.scheduled_shutdown_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=theme.font(12, bold=True)).pack(side=tk.LEFT)
        self.shutdown_minute = DarkEntry(self.scheduled_shutdown_frame, width=5)
        self.shutdown_minute.insert(0, "00")
        self.shutdown_minute.pack(side=tk.LEFT, padx=(2, 10))
        tk.Label(self.scheduled_shutdown_frame, text="（如果时间已过，将在第二天同一时间关机）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(8)).pack(side=tk.LEFT)

        # 延时关机时间设置
        self.delay_shutdown_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        self.delay_shutdown_frame.pack(fill=tk.X, pady=4)
        tk.Label(self.delay_shutdown_frame, text="延时分钟:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.shutdown_delay = DarkEntry(self.delay_shutdown_frame, width=8)
        self.shutdown_delay.insert(0, "60")
        self.shutdown_delay.pack(side=tk.LEFT, padx=(10, 10))
        tk.Label(self.delay_shutdown_frame, text="分钟后关机", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(10)).pack(side=tk.LEFT)

        # 任务名称
        name_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, pady=4)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.shutdown_task_name = DarkEntry(name_frame, width=30)
        self.shutdown_task_name.insert(0, "定时关机任务")
        self.shutdown_task_name.pack(side=tk.LEFT, padx=(10, 0))

        # 控制按钮
        btn_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        self.add_shutdown_task_btn = DarkButton(btn_frame, "+ 添加关机任务", command=self.add_shutdown_task,
                                                  width=160, height=40, bg_color=COLORS["accent"], text_color="#000000")
        self.add_shutdown_task_btn.pack(side=tk.LEFT)
        self.cancel_all_shutdown_btn = DarkButton(btn_frame, "■ 取消全部任务", command=self.cancel_all_shutdown,
                                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.cancel_all_shutdown_btn.pack(side=tk.LEFT, padx=(10, 0))

        # 当前状态显示
        status_frame = tk.Frame(setup_content, bg=COLORS["bg_card"])
        status_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(status_frame, text="当前状态:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=theme.font(10)).pack(side=tk.LEFT)
        self.shutdown_status_label = tk.Label(status_frame, text="● 无运行中的关机任务", bg=COLORS["bg_card"],
                                               fg=COLORS["text_muted"], font=theme.font(10, bold=True))
        self.shutdown_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # 初始隐藏定时和延时设置
        self.scheduled_shutdown_frame.pack_forget()
        self.delay_shutdown_frame.pack_forget()

        # 底部：关机任务列表卡片
        list_card = tk.Frame(main, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(fill=tk.BOTH, expand=True)

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 关机任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=theme.font(12, bold=True)).pack(side=tk.LEFT)
        tk.Label(list_header, text="（点击「取消」可单独取消某个任务）", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=theme.font(8)).pack(side=tk.LEFT, padx=(10, 0))

        # 任务列表容器
        self.shutdown_task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.shutdown_task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 加载关机配置
        self.load_shutdown_config()

    def on_shutdown_mode_change(self):
        """关机模式切换时显示/隐藏对应的设置"""
        mode = self.shutdown_mode_var.get()
        if mode == "scheduled":
            self.scheduled_shutdown_frame.pack(fill=tk.X, pady=4)
            self.delay_shutdown_frame.pack_forget()
        elif mode == "delay":
            self.delay_shutdown_frame.pack(fill=tk.X, pady=4)
            self.scheduled_shutdown_frame.pack_forget()
        else:
            self.scheduled_shutdown_frame.pack_forget()
            self.delay_shutdown_frame.pack_forget()
        self.save_shutdown_config()

    def add_shutdown_task(self):
        """添加关机任务"""
        mode = self.shutdown_mode_var.get()
        if mode == "none":
            messagebox.showwarning("提示", "请先选择关机模式（定时关机或延时关机）", parent=self.root)
            return

        task_name = self.shutdown_task_name.get().strip() or "定时关机任务"

        # 计算关机时间
        now = datetime.now()
        if mode == "scheduled":
            try:
                hour = int(self.shutdown_hour.get().strip())
                minute = int(self.shutdown_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）", parent=self.root)
                return
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)
            delay_seconds = (target_time - now).total_seconds()
            time_desc = f"{hour:02d}:{minute:02d}"
        elif mode == "delay":
            try:
                delay_minutes = float(self.shutdown_delay.get().strip())
                if delay_minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的延时分钟数（大于0）", parent=self.root)
                return
            delay_seconds = delay_minutes * 60
            target_time = now + timedelta(seconds=delay_seconds)
            time_desc = f"{delay_minutes}分钟后"

        # 创建任务
        task_id = f"shutdown_{int(time.time()*1000)}"
        task = {
            "id": task_id,
            "name": task_name,
            "mode": mode,
            "time_desc": time_desc,
            "target_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
            "delay_seconds": int(delay_seconds),
            "remaining": int(delay_seconds),
            "status": "等待中",
            "stop_flag": {"stop": False},
            "thread": None,
        }

        # 启动任务线程
        task["thread"] = threading.Thread(
            target=self.shutdown_task_worker,
            args=(task,),
            daemon=True
        )
        task["thread"].start()

        self.shutdown_tasks.append(task)
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()
        self.log(f"⏻ 已添加关机任务「{task_name}」，将在 {time_desc} 关机（{target_time.strftime('%Y-%m-%d %H:%M:%S')}）")

    def shutdown_task_worker(self, task):
        """关机任务工作线程"""
        try:
            start_time = time.time()
            total_seconds = task["delay_seconds"]
            while time.time() - start_time < total_seconds:
                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    return
                remaining = int(total_seconds - (time.time() - start_time))
                task["remaining"] = remaining
                task["status"] = "倒计时中"
                self.root.after(0, self.refresh_shutdown_task_list)
                self.root.after(0, self.update_shutdown_status)
                time.sleep(1)

            # 时间到，弹出确认窗口
            if not task["stop_flag"]["stop"]:
                task["status"] = "待确认"
                self.root.after(0, self.refresh_shutdown_task_list)
                self.log(f"⏻ 任务「{task['name']}」时间到，弹出关机确认窗口...")

                # 在UI线程弹出确认对话框
                confirm_result = {"confirmed": False, "done": False}

                def show_confirm_dialog():
                    try:
                        confirm_win = tk.Toplevel(self.root)
                        confirm_win.title("关机确认")
                        confirm_win.geometry("360x200")
                        confirm_win.configure(bg=COLORS["bg_card"])
                        confirm_win.resizable(False, False)
                        confirm_win.attributes("-topmost", True)
                        confirm_win.grab_set()
                        confirm_win.update_idletasks()
                        x = (confirm_win.winfo_screenwidth() // 2) - 180
                        y = (confirm_win.winfo_screenheight() // 2) - 100
                        confirm_win.geometry(f"360x200+{x}+{y}")

                        tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                                 font=theme.font(16, bold=True)).pack(pady=(20, 10))
                        tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                                 fg=COLORS["text_primary"], font=theme.font(11)).pack()
                        countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                                   fg=COLORS["warning"], font=theme.font(12, bold=True))
                        countdown_label.pack(pady=(8, 15))

                        def do_confirm():
                            confirm_result["confirmed"] = True
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        def do_cancel():
                            confirm_result["confirmed"] = False
                            confirm_result["done"] = True
                            confirm_win.destroy()

                        # P0-F修复: 窗口X按钮关闭也视为取消
                        confirm_win.protocol("WM_DELETE_WINDOW", do_cancel)

                        btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
                        btn_frame.pack()
                        DarkButton(btn_frame, "确认关机", command=do_confirm,
                                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
                        DarkButton(btn_frame, "取消", command=do_cancel,
                                   width=140, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

                        remaining = [60]
                        def tick():
                            if remaining[0] > 0 and confirm_win.winfo_exists():
                                remaining[0] -= 1
                                countdown_label.config(text=f"{remaining[0]}秒后自动取消...")
                                confirm_win.after(1000, tick)
                            elif confirm_win.winfo_exists():
                                # 超时自动取消（避免用户不在时误关机）
                                confirm_result["confirmed"] = False
                                confirm_result["done"] = True
                                confirm_win.destroy()
                        confirm_win.after(1000, tick)

                        # P0-F修复: 删除wait_window，避免阻塞主线程；由下方while循环等待confirm_result["done"]
                    except Exception as e:
                        self.log(f"✗ 关机确认弹窗异常，已取消关机: {e}")
                        confirm_result["confirmed"] = False
                        confirm_result["done"] = True

                self.root.after(0, show_confirm_dialog)

                # 等待确认结果（最多等90秒）
                wait_count = 0
                while not confirm_result["done"] and wait_count < 90:
                    if task["stop_flag"]["stop"]:
                        break
                    time.sleep(1)
                    wait_count += 1

                if task["stop_flag"]["stop"]:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    return

                if confirm_result["confirmed"]:
                    task["status"] = "执行中"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.log(f"⏻ 确认关机，正在执行关机命令...")
                    time.sleep(1)
                    import subprocess
                    subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
                else:
                    task["status"] = "已取消"
                    self.root.after(0, self.refresh_shutdown_task_list)
                    self.root.after(0, self.update_shutdown_status)
                    self.log(f"■ 关机任务「{task['name']}」已取消")
        except Exception as e:
            task["status"] = "异常"
            self.log(f"✗ 关机任务「{task['name']}」异常: {e}")
            self.root.after(0, self.refresh_shutdown_task_list)
            self.root.after(0, self.update_shutdown_status)

    def cancel_shutdown_task(self, task_id):
        """取消单个关机任务"""
        for task in self.shutdown_tasks:
            if task["id"] == task_id:
                task["stop_flag"]["stop"] = True
                task["status"] = "已取消"
                if task["thread"] and task["thread"].is_alive():
                    task["thread"].join(timeout=2)
                self.log(f"■ 已取消关机任务「{task['name']}」")
                break
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def cancel_all_shutdown(self):
        """取消所有关机任务"""
        if not self.shutdown_tasks:
            messagebox.showinfo("提示", "当前没有运行中的关机任务", parent=self.root)
            return
        for task in self.shutdown_tasks:
            # P1-J: 纳入"待确认"状态，避免确认弹窗未处理时任务继续运行
            if task["status"] in ["等待中", "倒计时中", "待确认"]:
                task["stop_flag"]["stop"] = True
                task["status"] = "已取消"
                if task["thread"] and task["thread"].is_alive():
                    task["thread"].join(timeout=2)
        self.log("■ 已取消所有关机任务")
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def cancel_shutdown(self):
        """取消所有关机（用于程序关闭时）"""
        for task in self.shutdown_tasks:
            task["stop_flag"]["stop"] = True
            if task["thread"] and task["thread"].is_alive():
                task["thread"].join(timeout=1)

    def refresh_shutdown_task_list(self):
        """刷新关机任务列表显示"""
        # 清空现有内容
        for widget in self.shutdown_task_list_frame.winfo_children():
            widget.destroy()

        if not self.shutdown_tasks:
            tk.Label(self.shutdown_task_list_frame, text="暂无关机任务，设置好参数后点击「+ 添加关机任务」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=theme.font(10)).pack(pady=30)
            return

        for idx, task in enumerate(self.shutdown_tasks):
            row_frame = tk.Frame(self.shutdown_task_list_frame, bg=COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            row_frame.pack(fill=tk.X, pady=3)

            # 任务名称
            name_label = tk.Label(row_frame, text=task["name"], bg=row_frame["bg"], fg=COLORS["text_primary"],
                                  font=theme.font(10, bold=True), width=20, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(10, 0), pady=8)

            # 关机时间
            time_label = tk.Label(row_frame, text=task["time_desc"], bg=row_frame["bg"], fg=COLORS["text_secondary"],
                                  font=theme.font(9), width=15, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(10, 0))

            # 目标时间
            target_label = tk.Label(row_frame, text=task["target_time"], bg=row_frame["bg"], fg=COLORS["text_muted"],
                                    font=theme.font(9), width=20, anchor=tk.W)
            target_label.pack(side=tk.LEFT, padx=(10, 0))

            # 倒计时/状态
            if task["status"] == "倒计时中":
                hours = task["remaining"] // 3600
                minutes = (task["remaining"] % 3600) // 60
                seconds = task["remaining"] % 60
                if hours > 0:
                    countdown_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    countdown_str = f"{minutes:02d}:{seconds:02d}"
                status_label = tk.Label(row_frame, text=f"⏳ {countdown_str}", bg=row_frame["bg"], fg=COLORS["warning"],
                                        font=theme.font(10, bold=True), width=12, anchor=tk.W)
            elif task["status"] == "已取消":
                status_label = tk.Label(row_frame, text="■ 已取消", bg=row_frame["bg"], fg=COLORS["text_muted"],
                                        font=theme.font(9), width=12, anchor=tk.W)
            elif task["status"] == "执行中":
                status_label = tk.Label(row_frame, text="⚡ 执行中", bg=row_frame["bg"], fg=COLORS["danger"],
                                        font=theme.font(10, bold=True), width=12, anchor=tk.W)
            else:
                status_label = tk.Label(row_frame, text=f"● {task['status']}", bg=row_frame["bg"], fg=COLORS["text_muted"],
                                        font=theme.font(9), width=12, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(10, 0))

            # 取消按钮
            if task["status"] in ["等待中", "倒计时中"]:
                cancel_btn = DarkButton(row_frame, "取消", command=lambda tid=task["id"]: self.cancel_shutdown_task(tid),
                                        width=90, height=28, bg_color=COLORS["danger"], text_color="#ffffff")
                cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))

            # 删除按钮（已取消/已完成的任务可以删除）
            if task["status"] in ["已取消", "执行中"]:
                delete_btn = DarkButton(row_frame, "删除", command=lambda tid=task["id"]: self.delete_shutdown_task(tid),
                                        width=90, height=28, bg_color="#444466", text_color="#ffffff")
                delete_btn.pack(side=tk.RIGHT, padx=(0, 5))

    def delete_shutdown_task(self, task_id):
        """删除关机任务"""
        self.shutdown_tasks = [t for t in self.shutdown_tasks if t["id"] != task_id]
        self.refresh_shutdown_task_list()
        self.update_shutdown_status()
        self.save_shutdown_config()

    def update_shutdown_status(self):
        """更新关机状态显示"""
        running_tasks = [t for t in self.shutdown_tasks if t["status"] in ["等待中", "倒计时中"]]
        if running_tasks:
            # 找到最近的一个任务
            nearest = min(running_tasks, key=lambda t: t["remaining"])
            hours = nearest["remaining"] // 3600
            minutes = (nearest["remaining"] % 3600) // 60
            seconds = nearest["remaining"] % 60
            if hours > 0:
                countdown_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                countdown_str = f"{minutes:02d}:{seconds:02d}"
            self.shutdown_status_label.config(text=f"● {len(running_tasks)}个任务运行中，最近: {countdown_str}", fg=COLORS["warning"])
        else:
            self.shutdown_status_label.config(text="● 无运行中的关机任务", fg=COLORS["text_muted"])

    def save_shutdown_config(self):
        """保存关机配置"""
        try:
            config = {
                "shutdown_mode": self.shutdown_mode_var.get(),
                "shutdown_hour": self.shutdown_hour.get().strip(),
                "shutdown_minute": self.shutdown_minute.get().strip(),
                "shutdown_delay": self.shutdown_delay.get().strip(),
                "task_name": self.shutdown_task_name.get().strip(),
            }
            shutdown_config_file = BASE_DIR / "shutdown_config.json"
            atomic_write_json(shutdown_config_file, config)
        except Exception:
            pass

    def load_shutdown_config(self):
        """加载关机配置"""
        try:
            shutdown_config_file = BASE_DIR / "shutdown_config.json"
            if shutdown_config_file.exists():
                with open(shutdown_config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if config.get("shutdown_mode"):
                    self.shutdown_mode_var.set(config["shutdown_mode"])
                if config.get("shutdown_hour"):
                    self.shutdown_hour.delete(0, tk.END)
                    self.shutdown_hour.insert(0, config["shutdown_hour"])
                if config.get("shutdown_minute"):
                    self.shutdown_minute.delete(0, tk.END)
                    self.shutdown_minute.insert(0, config["shutdown_minute"])
                if config.get("shutdown_delay"):
                    self.shutdown_delay.delete(0, tk.END)
                    self.shutdown_delay.insert(0, config["shutdown_delay"])
                if config.get("task_name"):
                    self.shutdown_task_name.delete(0, tk.END)
                    self.shutdown_task_name.insert(0, config["task_name"])
                # P1-G: 所有字段恢复后再触发mode change，避免默认值覆盖配置
                if config.get("shutdown_mode"):
                    self.on_shutdown_mode_change()
        except Exception:
            pass

    # ---------- 配置管理 ----------
    def load_config(self):
        default_config = {
            "room_id": "1791983148",
            "interval_min": "5",
            "interval_max": "10",
            "send_mode": "random",
            "account_mode": "single",
            "send_limit": "0",
            "selected_account": "",
            "current_tab": "rush",
            "window_geometry": "",
            "danmaku_selected_accounts": [],
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default_config.update(cfg)
            except Exception:
                pass
        return default_config

    def _schedule_save_config(self):
        """调度配置保存（防抖：500ms内连续触发只保存一次）"""
        if self._config_save_timer:
            self.root.after_cancel(self._config_save_timer)
        self._config_save_timer = self.root.after(500, self.save_config)

    def save_config(self):
        try:
            self.config["room_name"] = self.room_combo.get().strip()  # 保存直播间名称
            self.config["interval_min"] = self.interval_min.get().strip()
            self.config["interval_max"] = self.interval_max.get().strip()
            self.config["send_mode"] = self.mode_var.get()
            self.config["account_mode"] = self.account_mode_var.get()
            self.config["send_limit"] = self.max_send_entry.get().strip()
            self.config["current_tab"] = self.current_tab
            self.config["window_geometry"] = self.root.geometry()
            # 保存弹幕工具选中的账户列表
            try:
                if hasattr(self, 'danmaku_account_vars'):
                    selected = [name for name, var in self.danmaku_account_vars.items() if var.get()]
                    self.config["danmaku_selected_accounts"] = selected
            except Exception:
                pass
            # 保存当前选中的账户
            try:
                selection = self.account_listbox.curselection()
                if selection:
                    idx = selection[0]
                    if idx < len(self.account_mgr.accounts):
                        self.config["selected_account"] = self.account_mgr.accounts[idx].get("name", "")
            except Exception:
                pass
            atomic_write_json(CONFIG_FILE, self.config)
        except Exception:
            pass

    def apply_config(self):
        # 初始化直播间下拉框选项
        self._refresh_danmaku_room_combo_values()
        if self.config.get("room_name"):
            self.room_combo.set(self.config["room_name"])
        if self.config.get("interval_min"):
            self.interval_min.delete(0, tk.END)
            self.interval_min.insert(0, self.config["interval_min"])
        if self.config.get("interval_max"):
            self.interval_max.delete(0, tk.END)
            self.interval_max.insert(0, self.config["interval_max"])
        if self.config.get("send_mode"):
            self.mode_var.set(self.config["send_mode"])
        if self.config.get("account_mode"):
            self.account_mode_var.set(self.config["account_mode"])
        if self.config.get("send_limit"):
            self.max_send_entry.delete(0, tk.END)
            self.max_send_entry.insert(0, self.config["send_limit"])
        # 恢复窗口大小和位置（如果保存的宽度小于1500则用默认值）
        if self.config.get("window_geometry"):
            try:
                geom = self.config["window_geometry"]
                width_str = geom.split("x")[0]
                if width_str.isdigit() and int(width_str) >= 1500:
                    self.root.geometry(geom)
                else:
                    self.root.geometry("1600x1000")
            except Exception:
                self.root.geometry("1600x1000")
        # 绑定自动保存
        self.room_combo.bind("<<ComboboxSelected>>", self._on_danmaku_room_selected)
        self.interval_min.bind("<FocusOut>", lambda e: self.save_config())
        self.interval_max.bind("<FocusOut>", lambda e: self.save_config())
        self.max_send_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.mode_var.trace_add("write", lambda *a: self.save_config())
        self.account_mode_var.trace_add("write", lambda *a: self.save_config())
        # 窗口大小变化时保存
        self.root.bind("<Configure>", lambda e: self._schedule_save_config() if e.widget == self.root else None)

    # ---------- 弹幕列表（三列） ----------
    def get_all_danmaku(self):
        """从三列中获取所有弹幕，按列顺序合并"""
        all_lines = []
        for text_widget in self.danmaku_texts:
            content = text_widget.get("1.0", tk.END).strip()
            if content:
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                all_lines.extend(lines)
        return all_lines

    def distribute_danmaku_to_columns(self, danmaku_list):
        """把弹幕列表平均分配到三列"""
        # 清空所有列
        for text_widget in self.danmaku_texts:
            text_widget.delete("1.0", tk.END)

        if not danmaku_list:
            return

        # 计算每列的数量
        total = len(danmaku_list)
        col_count = (total + 2) // 3  # 向上取整

        # 分配到三列
        for i in range(3):
            start = i * col_count
            end = min(start + col_count, total)
            if start < total:
                column_lines = danmaku_list[start:end]
                self.danmaku_texts[i].insert("1.0", "\n".join(column_lines))

    def add_single_danmaku(self):
        text = simpledialog.askstring("添加弹幕", "请输入弹幕内容：", parent=self.root)
        if text and text.strip():
            text = text.strip()
            # 获取当前所有弹幕
            all_danmaku = self.get_all_danmaku()
            all_danmaku.append(text)
            # 重新分配到三列
            self.distribute_danmaku_to_columns(all_danmaku)
            self.danmaku_list = all_danmaku
            self.save_danmaku()
            self.log(f"已添加弹幕: {text}")

    def batch_generate_danmaku(self):
        count = simpledialog.askinteger("批量生成弹幕", "请输入生成数量（1-100）：",
                                         parent=self.root, minvalue=1, maxvalue=100, initialvalue=20)
        if not count:
            return
        if count > len(DANMAKU_POOL):
            count = len(DANMAKU_POOL)
        selected = random.sample(DANMAKU_POOL, count)
        # 获取当前所有弹幕
        all_danmaku = self.get_all_danmaku()
        all_danmaku.extend(selected)
        # 重新分配到三列
        self.distribute_danmaku_to_columns(all_danmaku)
        self.danmaku_list = all_danmaku
        self.save_danmaku()
        self.log(f"批量生成 {count} 条弹幕，当前共 {len(all_danmaku)} 条")

    def load_danmaku(self):
        if DANMAKU_FILE.exists():
            with open(DANMAKU_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return ["666", "主播好强", "来了来了", "哈哈哈哈", "学到了"]

    def save_danmaku(self):
        """保存弹幕列表到文件（v6.2.0: 补异常保护，避免写盘失败导致崩溃）"""
        try:
            all_danmaku = self.get_all_danmaku()
            with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(all_danmaku))
            self.danmaku_list = all_danmaku
            self.log(f"弹幕列表已保存，共 {len(all_danmaku)} 条")
            messagebox.showinfo("成功", f"弹幕列表已保存，共 {len(all_danmaku)} 条",
                                parent=self.root)
        except PermissionError:
            messagebox.showerror("保存失败",
                                 f"没有写入权限，无法保存到：\n{DANMAKU_FILE}\n\n"
                                 f"请检查文件是否被其他程序占用。",
                                 parent=self.root)
        except Exception as e:
            messagebox.showerror("保存失败", f"保存弹幕列表时出错：\n{e}",
                                 parent=self.root)

    def save_danmaku_silent(self):
        """静默保存弹幕列表（不弹提示框）"""
        try:
            all_danmaku = self.get_all_danmaku()
            with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(all_danmaku))
            self.danmaku_list = all_danmaku
        except Exception:
            pass

    def refresh_danmaku_list(self):
        self.distribute_danmaku_to_columns(self.danmaku_list)

    # ---------- 日志 ----------
    def log(self, msg):
        """线程安全的日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
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

    # ---------- 发送控制 ----------
    def start_sending(self):
        # P1-Q: 运行中守卫，防止并发启动双倍发送
        if self.running or (hasattr(self, 'send_thread') and self.send_thread and self.send_thread.is_alive()):
            messagebox.showwarning("提示", "弹幕发送正在运行中，请先停止当前任务", parent=self.root)
            return
        # 从弹幕工具页面的账户多选复选框获取选中的账户
        accounts = self._get_danmaku_selected_accounts()
        if not accounts:
            messagebox.showwarning("提示", "请先勾选至少一个发送账户", parent=self.root)
            return
        # P1-R: 从界面单选按钮读取account_mode，而不是根据账户数量推断
        try:
            account_mode = self.account_mode_var.get()
            if account_mode not in ("single", "multi", "rotate"):
                account_mode = "multi" if len(accounts) > 1 else "single"
        except Exception:
            account_mode = "multi" if len(accounts) > 1 else "single"

        room_id = self._get_danmaku_room_id()
        if not room_id:
            messagebox.showwarning("提示", "请先选择直播间（可在账户管理页面添加）", parent=self.root)
            return
        # 从三列中获取所有弹幕
        lines = self.get_all_danmaku()
        if not lines:
            messagebox.showwarning("提示", "弹幕列表为空，请先添加弹幕内容", parent=self.root)
            return
        self.danmaku_list = lines

        # 获取发送条数限制（0表示不限制）
        try:
            max_send_count = int(self.max_send_entry.get().strip())
            if max_send_count < 0:
                max_send_count = 0
        except ValueError:
            max_send_count = 0
        try:
            interval_min = float(self.interval_min.get())
            interval_max = float(self.interval_max.get())
            if interval_min <= 0 or interval_max <= 0 or interval_min > interval_max:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的发送间隔（秒），且最小值 ≤ 最大值", parent=self.root)
            return

        # 验证账户登录
        valid_accounts = []
        for acc in accounts:
            cookie_str = self.account_mgr.get_cookie_string(acc["name"])
            ok, msg = verify_login(cookie_str)
            if ok:
                valid_accounts.append(acc)
            else:
                self.log(f"⚠ 账户「{acc['name']}」登录失效，已跳过: {msg}")

        if not valid_accounts:
            messagebox.showerror("登录失效", "所有账户登录验证都失败了，请更新cookie后重试", parent=self.root)
            return

        if account_mode == "rotate" and len(valid_accounts) < 2:
            messagebox.showwarning("提示", "多账户轮流模式至少需要2个有效账户，当前只有1个", parent=self.root)
            return

        self.running = True
        self.start_btn.set_state("disabled")
        self.stop_btn.set_state("normal")
        if account_mode == "single":
            status_text = f"状态：运行中（账户: {valid_accounts[0]['name']}）"
        else:
            status_text = f"状态：运行中（多账户轮流，共{len(valid_accounts)}个账户）"
        self.status_label.config(text=status_text, fg=COLORS["success"])
        self.header_status.config(text="● 运行中", fg=COLORS["success"])

        self.log("=" * 40)
        if account_mode == "single":
            self.log(f"启动发送 | 账户: {valid_accounts[0]['name']}")
        else:
            acc_names = "、".join([a['name'] for a in valid_accounts])
            self.log(f"启动发送 | 多账户轮流: {acc_names}")
        self.log(f"直播间: {room_id} | 弹幕: {len(self.danmaku_list)}条 | 间隔: {interval_min}-{interval_max}秒")
        if max_send_count > 0:
            self.log(f"发送限制: 最多发送 {max_send_count} 条后自动停止")
        self.log("-" * 40)

        self.send_thread = threading.Thread(
            target=self.send_loop, args=(valid_accounts, int(room_id), interval_min, interval_max, account_mode, max_send_count), daemon=True
        )
        self.send_thread.start()

    def stop_sending(self):
        self.running = False
        self.start_btn.set_state("normal")
        self.stop_btn.set_state("disabled")
        self.status_label.config(text="状态：已停止", fg=COLORS["warning"])
        self.header_status.config(text="● 已停止", fg=COLORS["warning"])
        self.log("-" * 40)
        self.log("已停止发送")

    def send_loop(self, accounts, room_id, interval_min, interval_max, account_mode, max_send_count=0):
        mode = self.mode_var.get()
        index = 0
        send_count = 0
        fail_count = 0
        acc_index = 0

        while self.running:
            # 检查是否达到最大发送条数
            if max_send_count > 0 and send_count >= max_send_count:
                self.log(f"✓ 已达到最大发送条数 {max_send_count}，自动停止")
                self.running = False
                self.root.after(0, self.stop_sending)
                break

            # 选择当前账户
            if account_mode == "single":
                account = accounts[0]
            else:
                account = accounts[acc_index % len(accounts)]
                acc_index += 1

            cookie_str = self.account_mgr.get_cookie_string(account["name"])
            csrf = account["bili_jct"]

            # 选择弹幕
            # P1-8: 空列表保护，防止运行中弹幕被清空导致崩溃
            if not self.danmaku_list:
                self.log("⚠ 弹幕列表为空，等待10秒后重试...")
                time.sleep(10)
                continue
            if mode == "random":
                msg = random.choice(self.danmaku_list)
            else:
                msg = self.danmaku_list[index % len(self.danmaku_list)]
                index += 1

            success = False
            result = ""  # P1-7: 初始化result，防止循环提前break时NameError
            for retry in range(3):
                if not self.running:
                    break
                ok, result = send_danmaku(cookie_str, csrf, room_id, msg)
                if ok:
                    success = True
                    send_count += 1
                    fail_count = 0
                    if account_mode == "single":
                        self.log(f"✓ [{send_count}/{max_send_count if max_send_count > 0 else '∞'}] {msg}")
                    else:
                        self.log(f"✓ [{send_count}/{max_send_count if max_send_count > 0 else '∞'}] [{account['name']}] {msg}")
                    break
                else:
                    # P1-T: 区分瞬时错误和永久错误，永久错误不重试
                    permanent_errors = ["-101", "账号未登录", "cookie", "房间不存在", "内容违规", "禁言", "黑名单"]
                    is_permanent = any(err in result for err in permanent_errors)
                    if is_permanent:
                        self.log(f"  ✗ 永久错误({account['name']}): {result}，不重试")
                        break
                    if retry < 2:
                        self.log(f"  重试{retry+1} ({account['name']}): {result}")
                        time.sleep(random.uniform(2, 4))

            if not success:
                fail_count += 1
                self.log(f"✗ 失败({fail_count}) [{account['name']}]: {msg} - {result}")
                if fail_count >= 5:
                    self.log("连续失败5次，自动停止")
                    self.running = False
                    self.root.after(0, self.stop_sending)
                    break

            wait_time = random.uniform(interval_min, interval_max)
            waited = 0
            while waited < wait_time and self.running:
                time.sleep(0.5)
                waited += 0.5

        self.log(f"本次结束，共成功发送 {send_count} 条")

def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    
    # 卡密验证（直接在主窗口显示，验证通过后on_success会调用root.quit()）
    auth_success, card_info = show_card_auth(root)
    
    if not auth_success:
        try:
            root.destroy()
        except Exception:
            pass
        return
    
    # 验证通过，重新创建主窗口进入主程序
    try:
        root.destroy()
    except Exception:
        pass
    
    root = tk.Tk()
    app = DanmakuApp(root)

    # O10: 后台检查更新（不阻塞启动、不自动替换 exe）
    # 未配置 UPDATE_INDEX_URL 时 check_for_update 会直接跳过，无副作用。
    def _on_update_result(result):
        """更新检查结果回调（在后台线程，需投递回主线程弹窗）。"""
        try:
            if not result or not result.get("has_update"):
                return
            def _show():
                try:
                    updater.show_update_dialog(root, result)
                except Exception:
                    pass
            root.after(1200, _show)
        except Exception:
            pass

    try:
        # 延迟 3 秒再检查，避免和主界面初始化抢资源
        root.after(3000, lambda: updater.check_in_background(_on_update_result))
    except Exception as e:
        print(f"更新检查启动失败（不影响使用）: {e}")

    root.mainloop()


if __name__ == "__main__":
    main()
