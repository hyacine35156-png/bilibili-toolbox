# -*- coding: utf-8 -*-
"""日程任务页面：定时执行抢码/看播/弹幕/关机。"""

import json, threading, time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from config import COLORS, BASE_DIR
from storage import atomic_write_json
from widgets import DarkButton, DarkEntry, custom_askyesno

# ---------- O5: 统一日志（模块级缓存，避免重复创建 logger）----------
def _get_logger_cached(owner, name):
    """按实例缓存 logger，避免每次 log 都重建。"""
    try:
        cache = getattr(owner, "_o5_loggger_cache", None)
        if cache is None:
            cache = {}
            setattr(owner, "_o5_loggger_cache", cache)
        lg = cache.get(name)
        if lg is None:
            import logging_util
            lg = logging_util.get_logger(name)
            cache[name] = lg
        return lg
    except Exception:
        return None

# ========== 日程任务 ==========
class ScheduleFrame(tk.Frame):
    """日程任务：定时执行抢码/看播/发弹幕"""
    def __init__(self, parent, account_mgr, app):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.app = app  # DanmakuApp实例，用于访问其他页面
        self.account_mgr = account_mgr
        self.schedule_tasks = []
        self.scheduler_running = False
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = None
        self.selected_ids = set()  # 多选的任务ID集合
        self.schedule_presets = self.load_schedule_presets()  # 日程方案列表
        self.build_ui()
        self.load_schedule()
        self._load_form_settings()
        self.start_scheduler()

    def build_ui(self):
        # 顶部：添加任务卡片
        add_card = tk.Frame(self, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        add_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(add_card, text="➕ 添加日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))

        add_inner = tk.Frame(add_card, bg=COLORS["bg_card"])
        add_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 第一行：任务名称 + 类型
        row1 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)

        tk.Label(row1, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_name_entry = DarkEntry(row1, width=20)
        self.task_name_entry.pack(side=tk.LEFT, padx=(8, 20))

        tk.Label(row1, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.task_type_var = tk.StringVar(value="rush")
        ttk.Radiobutton(row1, text="⚡ 抢码", variable=self.task_type_var, value="rush",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(8, 8))
        ttk.Radiobutton(row1, text="📺 看播", variable=self.task_type_var, value="watch",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="💬 弹幕", variable=self.task_type_var, value="danmaku",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(row1, text="⏻ 关机", variable=self.task_type_var, value="shutdown",
                        style="Dark.TRadiobutton").pack(side=tk.LEFT)

        # 类型切换时自动填名称+控制时间输入框
        self.task_type_var.trace_add("write", self._on_type_changed)

        # 第二行：执行时间
        row2 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)

        tk.Label(row2, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.schedule_hour = DarkEntry(row2, width=5)
        self.schedule_hour.insert(0, "20")
        self.schedule_hour.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row2, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        self.schedule_minute = DarkEntry(row2, width=5)
        self.schedule_minute.insert(0, "00")
        self.schedule_minute.pack(side=tk.LEFT, padx=(2, 10))
        self.time_hint_label = tk.Label(row2, text="（每天自动执行，使用各页面当前已设置的参数）", bg=COLORS["bg_card"],
                                         fg=COLORS["text_muted"], font=("微软雅黑", 8))
        self.time_hint_label.pack(side=tk.LEFT)

        # 第三行：添加按钮
        row3 = tk.Frame(add_inner, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=(8, 0))

        DarkButton(row3, "+ 添加任务", command=self.add_schedule_task,
                   width=160, height=40, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.LEFT)
        DarkButton(row3, "✏ 编辑", command=self.edit_selected_task,
                   width=150, height=38, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "▶ 执行", command=self.run_selected_task,
                   width=150, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "☑ 全选", command=self.toggle_select_all,
                   width=150, height=38, bg_color="#9b59b6", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "🗑 批量删除", command=self.delete_selected_tasks,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(row3, "⚡ 全部启用", command=self.enable_all_tasks,
                   width=140, height=38, bg_color="#e67e22", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        # 调度器状态
        self.scheduler_status_label = tk.Label(row3, text="● 调度器运行中", bg=COLORS["bg_card"],
                                                fg=COLORS["success"], font=("微软雅黑", 10, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        # 方案管理行
        preset_row = tk.Frame(add_inner, bg=COLORS["bg_card"])
        preset_row.pack(fill=tk.X, pady=(8, 0))

        tk.Label(preset_row, text="📦 方案管理:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)

        tk.Label(preset_row, text="方案名:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.preset_name_entry = DarkEntry(preset_row, width=15)
        self.preset_name_entry.pack(side=tk.LEFT)

        DarkButton(preset_row, "💾 保存方案", command=self.save_schedule_preset,
                   width=140, height=38, bg_color="#27ae60", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(preset_row, text="选择方案:", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(15, 2))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var,
                                           values=[], state="readonly", width=15, font=("微软雅黑", 9))
        self.preset_combo.pack(side=tk.LEFT)

        DarkButton(preset_row, "📂 加载方案", command=self.load_schedule_preset,
                   width=140, height=38, bg_color="#3498db", text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))
        DarkButton(preset_row, "🗑 删除方案", command=self.delete_schedule_preset,
                   width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(8, 0))

        self._refresh_preset_combo()

        # 底部：任务列表 + 日志
        bottom = tk.Frame(self, bg=COLORS["bg_dark"])
        bottom.pack(fill=tk.BOTH, expand=True)

        # 左侧：任务列表
        list_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        list_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        list_header = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_header.pack(fill=tk.X, padx=15, pady=(10, 6))
        tk.Label(list_header, text="📋 日程任务列表", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(list_header, text="（勾选「选」可批量删除；点「启动/取消」控制是否执行；双击编辑）", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=(10, 0))

        self.task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.task_list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        # 右侧：日志
        log_card = tk.Frame(bottom, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(log_card, text="📝 执行日志", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 6))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))

        self.schedule_log_text = tk.Text(log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
                                          insertbackground=COLORS["accent"], font=("Consolas", 9),
                                          bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(fill=tk.BOTH, expand=True)

        self.selected_task_id = None

    def log(self, msg):
        """线程安全的日志输出（O5: 同时写文件，便于排障）"""
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.schedule_log_text.config(state=tk.NORMAL)
                self.schedule_log_text.insert(tk.END, line)
                self.schedule_log_text.see(tk.END)
                self.schedule_log_text.config(state=tk.DISABLED)
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
        # O5: 落文件（原实现只写 UI，重启即丢）
        try:
            _get_logger_cached(self, "schedule").log(msg)
        except Exception:
            pass

    def sync_log_to_modules(self, msg):
        """将日志同步到所有相关模块页面"""
        try:
            # 同步到抢码页面
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)
        except Exception:
            pass
        try:
            # 同步到看播页面
            if hasattr(self.app, 'watch_page') and hasattr(self.app.watch_page, 'log'):
                self.app.watch_page.log(msg)
        except Exception:
            pass
        try:
            # 同步到弹幕页面（主页面日志）
            if hasattr(self.app, 'log'):
                self.app.log(msg)
        except Exception:
            pass

    def _on_type_changed(self, *args):
        """类型切换时：自动填名称 + 控制时间输入框"""
        task_type = self.task_type_var.get()
        self._auto_fill_name(task_type)

        if task_type == "rush":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        elif task_type == "shutdown":
            self.schedule_hour.config(state=tk.DISABLED)
            self.schedule_minute.config(state=tk.DISABLED)
            self.time_hint_label.config(text="（关机时间在「定时关机」页面设置，此处无需填写）",
                                         fg=COLORS["warning"])
        else:
            self.schedule_hour.config(state=tk.NORMAL)
            self.schedule_minute.config(state=tk.NORMAL)
            self.time_hint_label.config(text="（每天自动执行，使用各页面当前已设置的参数）",
                                         fg=COLORS["text_muted"])

    def _auto_fill_name(self, task_type):
        """根据类型自动填写任务名称（看播1、看播2...）"""
        type_prefix = {
            "watch": "看播",
            "danmaku": "弹幕",
            "rush": "抢码",
            "shutdown": "关机",
        }
        prefix = type_prefix.get(task_type, "任务")
        count = sum(1 for t in self.schedule_tasks if t["type"] == task_type)
        auto_name = f"{prefix}{count + 1}"
        # 切换类型时强制更新名称（不管当前是什么）
        self.task_name_entry.delete(0, tk.END)
        self.task_name_entry.insert(0, auto_name)

    def add_schedule_task(self):
        name = self.task_name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入任务名称", parent=self.winfo_toplevel())
            return

        task_type = self.task_type_var.get()
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}

        if task_type == "rush":
            # 抢码不需要时间，添加后立即执行
            hour = -1
            minute = -1
            time_str = "立即执行"
        elif task_type == "shutdown":
            # 关机任务时间从关机页面读取，不在日程页面设置
            hour = -2
            minute = -2
            time_str = "关机页面设置"
        else:
            try:
                hour = int(self.schedule_hour.get().strip())
                minute = int(self.schedule_minute.get().strip())
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                messagebox.showwarning("提示", "请输入有效的时间（时: 0-23，分: 0-59）", parent=self.winfo_toplevel())
                return
            time_str = f"{hour:02d}:{minute:02d}"

        task = {
            "id": f"schedule_{int(time.time()*1000)}",
            "name": name,
            "type": task_type,
            "type_name": type_names[task_type],
            "hour": hour,
            "minute": minute,
            "time_str": time_str,
            "enabled": True,
            "last_run": "",
            "status": "等待中",
        }
        self.schedule_tasks.append(task)
        self.refresh_task_list()
        self.save_schedule()
        # 保存表单设置
        self._save_form_settings()

        if task_type == "rush":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，立即执行")
            # 抢码任务添加后立即执行
            self.after(100, lambda t=task: self.execute_task(t))
        elif task_type == "shutdown":
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天按关机页面设置的时间执行")
        else:
            self.log(f"➕ 已添加任务「{name}」({type_names[task_type]})，每天 {time_str} 执行")

        # 添加后自动填下一个名称
        self._auto_fill_name(task_type)

    def refresh_task_list(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        if not self.schedule_tasks:
            tk.Label(self.task_list_frame, text="暂无日程任务，设置好参数后点击「+ 添加任务」",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(pady=30)
            return

        for idx, task in enumerate(self.schedule_tasks):
            is_selected = (task["id"] == self.selected_task_id)
            is_checked = (task["id"] in self.selected_ids)
            bg_color = COLORS["accent"] if is_selected else (COLORS["bg_input"] if idx % 2 == 0 else COLORS["bg_card"])
            text_color = "#000000" if is_selected else COLORS["text_primary"]

            row_frame = tk.Frame(self.task_list_frame, bg=bg_color)
            row_frame.pack(fill=tk.X, pady=3)
            row_frame.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 选择复选框（多选）
            check_var = tk.BooleanVar(value=is_checked)
            def toggle_check(var=check_var, tid=task["id"]):
                if var.get():
                    self.selected_ids.add(tid)
                else:
                    self.selected_ids.discard(tid)
            check_chk = tk.Checkbutton(row_frame, variable=check_var, command=toggle_check,
                                        bg=bg_color, activebackground=bg_color, selectcolor=COLORS["bg_input"],
                                        fg=text_color, font=("微软雅黑", 8))
            check_chk.pack(side=tk.LEFT, padx=(4, 0), pady=8)


            # 任务名称（双击编辑）
            name_label = tk.Label(row_frame, text=task["name"], bg=bg_color, fg=text_color,
                                  font=("微软雅黑", 10, "bold"), width=8, anchor=tk.W)
            name_label.pack(side=tk.LEFT, padx=(4, 0), pady=8)
            name_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))
            name_label.bind("<Double-Button-1>", lambda e, tid=task["id"]: self._edit_task_by_id(tid))

            # 类型
            type_label = tk.Label(row_frame, text=task["type_name"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 9), width=6, anchor=tk.W)
            type_label.pack(side=tk.LEFT, padx=(4, 0))
            type_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 时间
            time_label = tk.Label(row_frame, text=task["time_str"], bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 10, "bold"), width=10, anchor=tk.W)
            time_label.pack(side=tk.LEFT, padx=(4, 0))
            time_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 状态
            if not task["enabled"]:
                status_text = "已取消"
                status_fg = COLORS["text_muted"]
            else:
                status_text = task.get("status", "等待中")
                if status_text == "执行中":
                    status_fg = COLORS["danger"]
                elif status_text in ["已完成", "已结束"]:
                    status_fg = COLORS["success"]
                elif "已结束" in status_text:
                    status_fg = COLORS["success"]
                elif status_text == "失败":
                    status_fg = COLORS["warning"]
                else:
                    status_fg = COLORS["text_muted"]
            status_label = tk.Label(row_frame, text=f"● {status_text}", bg=bg_color,
                                    fg=status_fg if not is_selected else "#000000",
                                    font=("微软雅黑", 9), width=7, anchor=tk.W)
            status_label.pack(side=tk.LEFT, padx=(4, 0))
            status_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))

            # 上次执行
            last_run = task.get("last_run", "-")
            if last_run and last_run != "-":
                try:
                    from datetime import datetime as _dt
                    _parsed = _dt.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    last_run = _parsed.strftime("%m-%d %H:%M")
                except Exception:
                    pass
            last_label = tk.Label(row_frame, text=last_run, bg=bg_color,
                                  fg=text_color if not is_selected else "#000000",
                                  font=("微软雅黑", 8), width=12, anchor=tk.W)
            last_label.pack(side=tk.LEFT, padx=(4, 0))
            last_label.bind("<Button-1>", lambda e, tid=task["id"]: self.select_task(tid))
            # 启用/取消按钮
            if task["enabled"]:
                btn_text = "取消"
                btn_bg = COLORS["warning"]
                def toggle_task(t=task):
                    t["enabled"] = False
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"⏸ 已取消日程「{t['name']}」")
            else:
                btn_text = "启用"
                btn_bg = COLORS["success"]
                def toggle_task(t=task):
                    t["enabled"] = True
                    self.save_schedule()
                    self.refresh_task_list()
                    self.log(f"✅ 已启用日程「{t['name']}」")
            toggle_btn = DarkButton(row_frame, btn_text, command=toggle_task,
                                     width=90, height=34, bg_color=btn_bg, text_color="#ffffff")
            toggle_btn.pack(side=tk.RIGHT, padx=(4, 4), pady=6)

    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def toggle_select_all(self):
        """全选/取消全选"""
        if len(self.selected_ids) == len(self.schedule_tasks):
            # 已全选，取消全选
            self.selected_ids.clear()
            self.log("☐ 已取消全选")
        else:
            # 全选
            self.selected_ids = {t["id"] for t in self.schedule_tasks}
            self.log(f"☑ 已全选 {len(self.schedule_tasks)} 个任务")
        self.refresh_task_list()

    def delete_selected_tasks(self):
        """批量删除勾选的任务"""
        if not self.selected_ids:
            messagebox.showwarning("提示", "请先勾选要删除的任务（每行左侧复选框）", parent=self.winfo_toplevel())
            return
        count = len(self.selected_ids)
        if custom_askyesno(self.app.root, "确认", f"确定删除选中的 {count} 个任务吗？"):
            names = [t["name"] for t in self.schedule_tasks if t["id"] in self.selected_ids]
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] not in self.selected_ids]
            if self.selected_task_id in self.selected_ids:
                self.selected_task_id = None
            self.selected_ids.clear()
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已批量删除 {count} 个任务: {', '.join(names)}")

    def delete_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要删除的任务", parent=self.winfo_toplevel())
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task and custom_askyesno(self.app.root, "确认", f"确定删除任务「{task['name']}」吗？"):
            self.schedule_tasks = [t for t in self.schedule_tasks if t["id"] != self.selected_task_id]
            self.selected_task_id = None
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"🗑 已删除任务「{task['name']}」")

    def edit_selected_task(self):
        """编辑选中的日程任务"""
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要编辑的任务", parent=self.winfo_toplevel())
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if not task:
            return

        # 创建编辑窗口
        edit_win = tk.Toplevel(self.app.root)
        edit_win.title(f"编辑任务 - {task['name']}")
        edit_win.geometry("380x280")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.resizable(False, False)
        edit_win.attributes("-topmost", True)
        edit_win.grab_set()
        edit_win.update_idletasks()
        x = (edit_win.winfo_screenwidth() // 2) - 190
        y = (edit_win.winfo_screenheight() // 2) - 140
        edit_win.geometry(f"380x280+{x}+{y}")

        tk.Label(edit_win, text="✏ 编辑日程任务", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 14, "bold")).pack(pady=(15, 10))

        # 任务名称
        name_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        name_entry = DarkEntry(name_frame, width=22)
        name_entry.insert(0, task["name"])
        name_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 任务类型
        type_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        type_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(type_frame, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        edit_type_var = tk.StringVar(value=task["type"])
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}
        for val, label in type_names.items():
            ttk.Radiobutton(type_frame, text=label, variable=edit_type_var, value=val,
                            style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(6, 0))

        # 执行时间
        time_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        time_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(time_frame, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT)
        hour_entry = DarkEntry(time_frame, width=5)
        hour_entry.insert(0, f"{task.get('hour', 20):02d}" if task.get("hour", -1) >= 0 else "20")
        hour_entry.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(time_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        minute_entry = DarkEntry(time_frame, width=5)
        minute_entry.insert(0, f"{task.get('minute', 0):02d}" if task.get("minute", -1) >= 0 else "00")
        minute_entry.pack(side=tk.LEFT, padx=(0, 0))
        time_hint = tk.Label(time_frame, text="", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                             font=("微软雅黑", 8))
        time_hint.pack(side=tk.LEFT, padx=(10, 0))

        def on_type_change(*args):
            if edit_type_var.get() == "rush":
                hour_entry.config(state=tk.DISABLED)
                minute_entry.config(state=tk.DISABLED)
                time_hint.config(text="（立即执行）", fg=COLORS["warning"])
            else:
                hour_entry.config(state=tk.NORMAL)
                minute_entry.config(state=tk.NORMAL)
                time_hint.config(text="")
        edit_type_var.trace_add("write", on_type_change)
        on_type_change()

        # 按钮
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(pady=(15, 10))

        def save_edit():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("提示", "请输入任务名称", parent=edit_win)
                return
            new_type = edit_type_var.get()
            if new_type == "rush":
                new_hour = -1
                new_minute = -1
                new_time_str = "立即执行"
            else:
                try:
                    new_hour = int(hour_entry.get().strip())
                    new_minute = int(minute_entry.get().strip())
                    if not (0 <= new_hour <= 23 and 0 <= new_minute <= 59):
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("提示", "请输入有效的时间", parent=edit_win)
                    return
                new_time_str = f"{new_hour:02d}:{new_minute:02d}"

            task["name"] = new_name
            task["type"] = new_type
            task["type_name"] = type_names[new_type]
            task["hour"] = new_hour
            task["minute"] = new_minute
            task["time_str"] = new_time_str
            self.refresh_task_list()
            self.save_schedule()
            self.log(f"✏ 已修改任务「{new_name}」({type_names[new_type]})，{new_time_str}")
            edit_win.destroy()

        DarkButton(btn_frame, "保存", command=save_edit,
                   width=150, height=34, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
        DarkButton(btn_frame, "取消", command=edit_win.destroy,
                   width=150, height=34, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    def _edit_task_by_id(self, task_id):
        """根据ID编辑任务（双击调用）"""
        self.selected_task_id = task_id
        self.refresh_task_list()
        self.edit_selected_task()

    def run_selected_task(self):
        if not self.selected_task_id:
            messagebox.showwarning("提示", "请先选中要执行的任务", parent=self.winfo_toplevel())
            return
        task = next((t for t in self.schedule_tasks if t["id"] == self.selected_task_id), None)
        if task:
            self.execute_task(task, manual=True)

    def enable_all_tasks(self):
        """全部启用：让所有任务按设定时间执行（不立即执行）"""
        disabled_tasks = [t for t in self.schedule_tasks if not t["enabled"]]
        if not disabled_tasks:
            messagebox.showinfo("提示", "所有日程任务都已启用", parent=self.winfo_toplevel())
            return
        if not custom_askyesno(self.app.root, "确认", f"确定启用全部 {len(disabled_tasks)} 个已取消的日程任务吗？\n启用后任务将按设定时间自动执行"):
            return
        for task in disabled_tasks:
            task["enabled"] = True
        self.save_schedule()
        self.refresh_task_list()
        self.log(f"⚡ 已全部启用 {len(disabled_tasks)} 个日程任务，将按设定时间执行")

    def execute_task(self, task, manual=False):
        """执行指定任务"""
        # P1-I: 同类任务禁止并发（抢码/看播/弹幕同一时间只能有一个在执行）
        if task["type"] in ["watch", "danmaku", "rush"]:
            for t in self.schedule_tasks:
                if t["id"] != task["id"] and t["type"] == task["type"] and t.get("status") == "执行中":
                    msg = f"⏭ [日程] 跳过任务「{task['name']}」：同类型任务「{t['name']}」正在执行中"
                    self.log(msg)
                    self.sync_log_to_modules(msg)
                    task["status"] = "已跳过"
                    self.refresh_task_list()
                    return
        task["status"] = "执行中"
        task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.refresh_task_list()

        prefix = "手动执行" if manual else "定时触发"
        msg = f"{'⚡' if manual else '⏰'} [日程] {prefix}任务「{task['name']}」({task['type_name']})"
        self.log(msg)
        # 同步到所有相关模块页面
        self.sync_log_to_modules(msg)

        try:
            if task["type"] == "watch":
                # v6.6.0: 懒加载页面必须先构建，否则 watch_page=None 导致启动直接失败
                self.app._ensure_page_built("watch")
                # 不跳转，直接后台启动看播
                self.app.root.after(100, lambda: self._start_watch_safe(task))
            elif task["type"] == "danmaku":
                # 弹幕页常驻，无需构建
                # 不跳转，直接后台启动弹幕
                self.app.root.after(100, lambda: self._start_danmaku_safe(task))
            elif task["type"] == "rush":
                # 抢码任务不跳转，直接后台执行，等所有子任务结束才标记完成
                self.app.root.after(100, lambda: self._start_rush_safe(task))
                self.app.root.after(3000, lambda: self._monitor_rush_completion(task))
            elif task["type"] == "shutdown":
                # 执行关机（带确认）
                self.app.root.after(0, lambda: self._execute_shutdown_safe(task))

            # 标记完成：
            # - 抢码任务由监控线程处理
            # - 关机任务立即标记
            # - 弹幕和看播任务启动监控线程，等任务实际停止后标记
            if task["type"] == "shutdown":
                self.app.root.after(2000, lambda: self._mark_task_done(task))
            elif task["type"] in ["danmaku", "watch"]:
                self.app.root.after(3000, lambda: self._monitor_long_task(task))

        except Exception as e:
            task["status"] = "失败"
            self.refresh_task_list()
            self.log(f"✗ 任务「{task['name']}」执行失败: {e}")

    def _start_watch_safe(self, task):
        """启动看播（v6.6.0 修复：页面懒加载 + 校验是否真的启动成功）。"""
        try:
            # 懒加载：确保页面已构建
            self.app._ensure_page_built("watch")
            wp = getattr(self.app, 'watch_page', None)
            if wp is None:
                msg = ("✗ [日程] 看播页未构建，无法启动「%s」。"
                       "请先手动打开一次「看播任务」标签页。" % task['name'])
                self.log(msg)
                self.sync_log_to_modules(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
                return

            if not hasattr(wp, 'start_watch'):
                msg = f"✗ [日程] 看播页缺少 start_watch 方法"
                self.log(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
                return

            wp.start_watch()

            # 关键：校验是否真的启动成功（running 会变 True）
            if getattr(wp, 'running', False):
                msg = f"✓ [日程] 看播任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(wp, 'log'):
                    wp.log(msg)
            else:
                # 没启动成功（通常是缺少直播间/账户配置，start_watch 弹框后 return）
                msg = (f"✗ [日程] 看播任务「{task['name']}」启动失败："
                       "请检查看播页是否已选好直播间和账户")
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(wp, 'log'):
                    wp.log(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
        except Exception as e:
            msg = f"✗ [日程] 启动看播失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            task["status"] = "启动失败"
            try:
                self.refresh_task_list()
            except Exception:
                pass

    def _start_danmaku_safe(self, task):
        try:
            if hasattr(self.app, 'start_sending'):
                self.app.start_sending()
                msg = f"✓ [日程] 弹幕任务「{task['name']}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                # 同时写主页面日志（弹幕工具的日志）
                if hasattr(self.app, 'log'):
                    self.app.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动弹幕失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            if hasattr(self.app, 'log'):
                self.app.log(msg)

    def _start_rush_safe(self, task):
        try:
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_all_scheduled_tasks'):
                self.app.rush_page.start_all_scheduled_tasks()
                msg = f"✓ [日程] 抢码任务「{task['name']}」已全部启动"
                self.log(msg)
                # 同时写抢码页面日志
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
            elif hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'start_rush'):
                self.app.rush_page.start_rush()
                msg = f"✓ [日程] 抢码监控「{task['name']}」已启动"
                self.log(msg)
                if hasattr(self.app.rush_page, 'log'):
                    self.app.rush_page.log(msg)
        except Exception as e:
            msg = f"✗ [日程] 启动抢码失败: {e}"
            self.log(msg)
            if hasattr(self.app, 'rush_page') and hasattr(self.app.rush_page, 'log'):
                self.app.rush_page.log(msg)

    def _execute_shutdown_safe(self, task):
        """执行关机任务（带确认弹窗，超时60秒自动关机）"""
        try:
            self.log(f"⏻ 关机任务「{task['name']}」已触发，弹出确认窗口...")
            # 创建确认对话框
            confirm_win = tk.Toplevel(self.app.root)
            confirm_win.title("关机确认")
            confirm_win.geometry("360x200")
            confirm_win.configure(bg=COLORS["bg_card"])
            confirm_win.resizable(False, False)
            # 置顶
            confirm_win.attributes("-topmost", True)
            confirm_win.grab_set()

            # 居中
            confirm_win.update_idletasks()
            x = (confirm_win.winfo_screenwidth() // 2) - 180
            y = (confirm_win.winfo_screenheight() // 2) - 100
            confirm_win.geometry(f"360x200+{x}+{y}")

            tk.Label(confirm_win, text="⏻ 定时关机", bg=COLORS["bg_card"], fg=COLORS["accent"],
                     font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
            tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
            countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                       fg=COLORS["warning"], font=("微软雅黑", 12, "bold"))
            countdown_label.pack(pady=(8, 15))

            result = {"confirmed": False, "window": confirm_win}

            def confirm_shutdown():
                result["confirmed"] = True
                confirm_win.destroy()

            def cancel_shutdown():
                result["confirmed"] = False
                confirm_win.destroy()

            # P0-F修复: 窗口X按钮关闭也视为取消
            confirm_win.protocol("WM_DELETE_WINDOW", cancel_shutdown)

            btn_frame = tk.Frame(confirm_win, bg=COLORS["bg_card"])
            btn_frame.pack()
            DarkButton(btn_frame, "确认关机", command=confirm_shutdown,
                       width=140, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
            DarkButton(btn_frame, "取消", command=cancel_shutdown,
                       width=140, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

            # 倒计时
            remaining = [60]
            def update_countdown():
                if remaining[0] > 0 and confirm_win.winfo_exists():
                    remaining[0] -= 1
                    countdown_label.config(text=f"{remaining[0]}秒后自动取消...")
                    confirm_win.after(1000, update_countdown)
                elif confirm_win.winfo_exists():
                    # 超时自动取消（避免用户不在时误关机）
                    result["confirmed"] = False
                    confirm_win.destroy()
            confirm_win.after(1000, update_countdown)

            # 等待对话框关闭
            self.app.root.wait_window(confirm_win)

            if result["confirmed"]:
                self.log(f"⏻ 确认关机，正在执行关机命令...")
                import subprocess
                subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True)
            else:
                self.log(f"■ 关机任务「{task['name']}」已取消")
        except Exception as e:
            self.log(f"✗ 关机任务执行失败: {e}")

    def _monitor_rush_completion(self, task):
        """监控抢码子任务，等所有子任务结束后标记日程任务完成"""
        def monitor_loop():
            max_wait = 7200  # 最多等2小时
            waited = 0
            check_interval = 5  # 每5秒检查一次
            last_running_count = -1  # 记录上次的运行中数量，只在变化时写日志
            while waited < max_wait:
                try:
                    if not hasattr(self.app, 'rush_page') or not hasattr(self.app.rush_page, 'scheduled_tasks'):
                        break
                    rush_tasks = self.app.rush_page.scheduled_tasks
                    if not rush_tasks:
                        break
                    # 检查是否还有运行中或等待中的子任务
                    running = [t for t in rush_tasks if t.get("status") in ["运行中", "等待中"]]
                    if not running:
                        # 所有子任务都结束了
                        self.app.root.after(0, lambda: self._mark_rush_done(task))
                        return
                    # 只有在数量变化时才写日志，避免刷屏
                    if len(running) != last_running_count:
                        running_names = [t.get("task_name", "?") for t in running]
                        self.log(f"⏳ 抢码任务「{task['name']}」等待中，还有 {len(running)} 个子任务运行中: {', '.join(running_names[:3])}")
                        last_running_count = len(running)
                except Exception as e:
                    self.log(f"⚠ 抢码监控异常: {e}")
                time.sleep(check_interval)
                waited += check_interval
            # 超时，标记完成
            self.app.root.after(0, lambda: self._mark_rush_done(task, timeout=True))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _mark_rush_done(self, task, timeout=False):
        """标记抢码任务完成（修复P0-3回归：状态重置为等待中，避免永久显示已结束）"""
        if timeout:
            task["status"] = "等待中"
            self.log(f"⏰ 抢码任务「{task['name']}」监控超时(2小时)，重置为等待中")
        else:
            task["status"] = "等待中"
            self.log(f"✓ 抢码任务「{task['name']}」所有子任务已完成，重置为等待中")
        self.refresh_task_list()
        self.save_schedule()

    def _monitor_long_task(self, task):
        """监控弹幕/看播任务，等真正停止后才标记完成（v6.6.0 修复）。

        【原 bug】原实现在任务没启动成功时也会立刻标记"已完成"：
          1. watch_page 懒加载，用户没点过就是 None
             -> hasattr(None, "running") 为 False -> is_running=False
             -> 3秒后误报"已完成"
          2. start_watch 因缺配置弹框 return，running 仍是 False
             -> 同样误报"已完成"

        【修复】
          · 先校验页面是否存在
          · 加"启动宽限期"：前 15 秒内不判定完成（给启动留时间）
          · 若宽限期内仍未 running，标记为"启动失败"而不是"已完成"
          · 真正跑起来后，等 running=False 才标记完成
        """
        def monitor_loop():
            max_wait = 86400
            waited = 0
            check_interval = 5
            task_type = task["type"]
            # v6.6.0: 启动宽限期，避免刚启动就被判定完成
            grace_period = 15
            seen_running = False

            while waited < max_wait:
                try:
                    is_running = False
                    page_missing = False

                    if task_type == "danmaku":
                        if hasattr(self.app, 'running'):
                            is_running = bool(self.app.running)
                    elif task_type == "watch":
                        wp = getattr(self.app, 'watch_page', None)
                        if wp is None:
                            page_missing = True
                        else:
                            is_running = bool(getattr(wp, 'running', False))

                    # 页面不存在 -> 明确报启动失败，不谎报完成
                    if page_missing:
                        msg = (f"✗ [日程] {task['type_name']}任务「{task['name']}」"
                               "未能启动：看播页未构建")
                        self.app.root.after(0, lambda m=msg, t=task:
                                            self._mark_task_failed(t, m))
                        return

                    if is_running:
                        seen_running = True

                    # 宽限期内：只观察，不判定
                    if waited < grace_period:
                        pass
                    elif seen_running and not is_running:
                        # 真正跑过然后停了 -> 正常完成
                        msg = (f"✓ [日程] {task['type_name']}任务"
                               f"「{task['name']}」已完成")
                        self.app.root.after(0, lambda m=msg, t=task:
                                            self._mark_task_done_with_log(t, m))
                        return
                    elif not seen_running and not is_running:
                        # 宽限期内一直没启动 -> 启动失败
                        msg = (f"✗ [日程] {task['type_name']}任务「{task['name']}」"
                               "启动失败：未检测到运行状态\n"
                               "  请检查对应页面是否已选好账户/房间")
                        self.app.root.after(0, lambda m=msg, t=task:
                                            self._mark_task_failed(t, m))
                        try:
                            self.sync_log_to_modules(msg)
                        except Exception:
                            pass
                        return

                except Exception:
                    pass  # 监控异常不影响任务

                time.sleep(check_interval)
                waited += check_interval

            # 超时
            self.app.root.after(0, lambda: self._mark_task_done(task))

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def _mark_task_failed(self, task, msg):
        """标记任务启动失败（v6.6.0 新增，区别于误报"已完成"）。"""
        task["status"] = "启动失败"
        self.log(msg)
        try:
            self.sync_log_to_modules(msg)
        except Exception:
            pass
        self.refresh_task_list()
        self.save_schedule()


    def _mark_task_done_with_log(self, task, msg):
        """标记任务完成并写日志，状态重置为等待中（次日继续执行）"""
        task["status"] = "等待中"
        self.log(msg)
        self.sync_log_to_modules(msg)
        self.refresh_task_list()
        self.save_schedule()

    def _mark_task_done(self, task):
        task["status"] = "等待中"
        self.refresh_task_list()
        self.save_schedule()

    def start_scheduler(self):
        """启动调度器"""
        if self.scheduler_running:
            return
        self.scheduler_running = True
        self.scheduler_stop = {"stop": False}
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.scheduler_status_label.config(text="● 调度器运行中", fg=COLORS["success"])
        self.log("⏰ 日程调度器已启动")

    def _scheduler_loop(self):
        """调度器主循环：每秒检查一次，到点执行任务"""
        last_minute = -1
        last_check_time = time.time()  # P1-14: 用于检测休眠唤醒后的时间跳跃
        warned_tasks = set()  # 已提前1分钟写过日志的任务ID
        while not self.scheduler_stop["stop"]:
            try:
                now = datetime.now()
                current_minute = now.hour * 60 + now.minute
                current_time = time.time()

                # P1-14: 检测休眠唤醒——如果时间跳跃超过5分钟，说明电脑休眠过
                time_jump = current_time - last_check_time
                if time_jump > 300:
                    self.log(f"⏰ 检测到系统休眠唤醒（跳过{time_jump:.0f}秒），立即检查待执行任务")
                    last_minute = -1  # 强制重新检查所有任务
                last_check_time = current_time

                # 只在分钟变化时检查（避免同一分钟重复执行）
                if current_minute != last_minute:
                    last_minute = current_minute
                    # 新的一分钟，清空已警告集合（用于第二天重复）
                    warned_tasks.clear()

                    # P1-H/P1-K: 用list快照遍历，避免execute_task修改列表导致迭代器异常
                    for task in list(self.schedule_tasks):
                        # 逐任务重校验：任务可能在遍历期间被删除/禁用
                        if task not in self.schedule_tasks:
                            continue
                        if not task.get("enabled", False):
                            continue
                        # 抢码任务是立即执行的，不参与定时检查
                        if task["type"] == "rush" or task.get("hour", -1) == -1:
                            continue
                        # 关机任务：动态从关机页面读取时间
                        if task["type"] == "shutdown" and task.get("hour", -1) == -2:
                            try:
                                if hasattr(self.app, 'shutdown_page') and self.app.shutdown_page:
                                    shutdown_hour = int(self.app.shutdown_page.shutdown_hour.get().strip())
                                    shutdown_minute = int(self.app.shutdown_page.shutdown_minute.get().strip())
                                    task_minute = shutdown_hour * 60 + shutdown_minute
                                else:
                                    continue
                            except (ValueError, AttributeError):
                                continue
                        else:
                            task_minute = task["hour"] * 60 + task["minute"]

                        # 抢码任务：提前1分钟写日志（如果不足1分钟则立即写）
                        if task["type"] == "rush":
                            time_diff = task_minute - current_minute
                            if time_diff <= 1 and task["id"] not in warned_tasks:
                                warned_tasks.add(task["id"])
                                warn_msg = f"⏳ [日程] 抢码任务「{task['name']}」将在 {task['time_str']} 执行，准备中..."
                                self.log(warn_msg)
                                self.sync_log_to_modules(warn_msg)

                        if task_minute == current_minute:
                            # 到点执行
                            self.app.root.after(0, lambda t=task: self.execute_task(t))

            except Exception as e:
                self.log(f"调度器异常: {e}")

            time.sleep(1)

    def _reset_task_status(self, task):
        """重置任务状态为等待中（用于每天重复执行）"""
        if "已结束" in task.get("status", ""):
            task["status"] = "等待中"
            self.refresh_task_list()

    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_stop["stop"] = True
        self.scheduler_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=2)
        self.scheduler_status_label.config(text="● 调度器已停止", fg=COLORS["text_muted"])
        self.log("⏰ 日程调度器已停止")

    def save_schedule(self):
        """保存日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            # 只保存可序列化的字段
            save_data = []
            for task in self.schedule_tasks:
                save_data.append({
                    "id": task["id"],
                    "name": task["name"],
                    "type": task["type"],
                    "type_name": task["type_name"],
                    "hour": task["hour"],
                    "minute": task["minute"],
                    "time_str": task["time_str"],
                    "enabled": task["enabled"],
                    "last_run": task.get("last_run", ""),
                })
            atomic_write_json(config_file, save_data)
        except Exception:
            pass

    def load_schedule_presets(self):
        """加载日程方案列表"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            if preset_file.exists():
                with open(preset_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载日程方案失败: {e}")
        return {}

    def save_schedule_presets_to_file(self):
        """保存日程方案列表到文件"""
        try:
            preset_file = BASE_DIR / "schedule_presets.json"
            atomic_write_json(preset_file, self.schedule_presets)
        except Exception as e:
            self.log(f"✗ 保存日程方案失败: {e}")

    def _refresh_preset_combo(self):
        """刷新方案下拉列表"""
        try:
            preset_names = list(self.schedule_presets.keys())
            self.preset_combo.config(values=preset_names)
            if preset_names and not self.preset_var.get():
                self.preset_var.set(preset_names[0])
        except Exception:
            pass

    def save_schedule_preset(self):
        """保存当前日程为方案（v6.2.0: 补异常保护）"""
        try:
            preset_name = self.preset_name_entry.get().strip()
            if not preset_name:
                messagebox.showwarning("提示", "请输入方案名称", parent=self.winfo_toplevel())
                return

            # 深拷贝当前日程任务，避免后续修改影响方案
            import copy
            preset_data = {
                "name": preset_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tasks": copy.deepcopy(self.schedule_tasks)
            }

            self.schedule_presets[preset_name] = preset_data
            self.save_schedule_presets_to_file()
            self._refresh_preset_combo()
            self.log(f"💾 已保存方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存方案时出错：\n{e}",
                                 parent=self.winfo_toplevel())

    def load_schedule_preset(self):
        """加载方案到当前日程"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要加载的方案", parent=self.winfo_toplevel())
            return

        # 确认是否覆盖当前日程
        if self.schedule_tasks:
            result = custom_askyesno(self.app.root, "确认", f"当前有 {len(self.schedule_tasks)} 个日程任务，加载方案将覆盖当前日程，是否继续？")
            if not result:
                return

        import copy
        preset_data = self.schedule_presets[preset_name]
        self.schedule_tasks = copy.deepcopy(preset_data["tasks"])

        # 重置任务状态
        for task in self.schedule_tasks:
            task["status"] = "等待中"
            task["last_run"] = ""
            task["enabled"] = task.get("enabled", True)

        self.save_schedule()
        self.refresh_task_list()
        self.log(f"📂 已加载方案「{preset_name}」（包含 {len(self.schedule_tasks)} 个任务）")

    def delete_schedule_preset(self):
        """删除选中的方案"""
        preset_name = self.preset_var.get()
        if not preset_name or preset_name not in self.schedule_presets:
            messagebox.showwarning("提示", "请选择要删除的方案", parent=self.winfo_toplevel())
            return

        result = custom_askyesno(self.app.root, "确认", f"确定要删除方案「{preset_name}」吗？")
        if not result:
            return

        del self.schedule_presets[preset_name]
        self.save_schedule_presets_to_file()
        self._refresh_preset_combo()
        self.preset_name_entry.delete(0, tk.END)
        self.log(f"🗑 已删除方案「{preset_name}」")

    def _save_form_settings(self):
        """保存表单设置（类型、时间）"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            settings = {
                "task_type": self.task_type_var.get(),
                "hour": self.schedule_hour.get(),
                "minute": self.schedule_minute.get(),
            }
            atomic_write_json(config_file, settings)
        except Exception:
            pass

    def _load_form_settings(self):
        """加载表单设置"""
        try:
            config_file = BASE_DIR / "schedule_form_settings.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.task_type_var.set(settings.get("task_type", "watch"))
                h = settings.get("hour", "20")
                m = settings.get("minute", "00")
                self.schedule_hour.delete(0, tk.END)
                self.schedule_hour.insert(0, h)
                self.schedule_minute.delete(0, tk.END)
                self.schedule_minute.insert(0, m)
                # 触发类型切换回调
                self._on_type_changed()
        except Exception:
            pass

    def load_schedule(self):
        """加载日程配置"""
        try:
            config_file = BASE_DIR / "schedule_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    saved_tasks = json.load(f)
                for task in saved_tasks:
                    task["status"] = "等待中"
                    self.schedule_tasks.append(task)
                self.refresh_task_list()
                self.log(f"已加载 {len(saved_tasks)} 个日程任务")
        except Exception as e:
            self.log(f"加载日程配置失败: {e}")

    def on_close(self):
        """关闭时保存配置并停止调度器"""
        self.save_schedule()
        self._save_form_settings()
        self.stop_scheduler()
