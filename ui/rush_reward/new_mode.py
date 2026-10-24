# -*- coding: utf-8 -*-
"""精准抢码（新模式）全部逻辑：任务组、调度器、NTP、首枪、风控退避。

以 Mixin 形式提供，由 RushRewardFrame 继承。所有方法都依赖宿主类提供的
self.rush_groups / self.nm_group_threads / self.account_mgr 等属性。
"""

import ctypes
import json, os, random, struct, subprocess, threading, time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox

import requests

from config import (COLORS, BASE_DIR, HEADERS, LOG_DIR)
from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID
from storage import atomic_write_json, safe_load_json
from bili_api import (check_all_tasks_finished, cookies_from_account, get_mission_info,
                      parse_stock_info, receive_reward, verify_login)
from widgets import DarkButton, DarkEntry, ToolTip, _SHELLEXECUTEINFOW
from .manual_task import task_label, available_versions


class NewModeMixin:
    """精准抢码子系统（39 个方法）。"""


    def nm_save_ui_settings(self):
        """保存新模式UI设置"""
        try:
            settings = {
                "version": self.nm_version_var.get(),
                "period": self.nm_period_var.get(),
                "type": self.nm_type_var.get(),
                "task": self.nm_task_var.get(),
                "account": self.nm_account_var.get(),
                "window": self.nm_window_entry.get(),
                "group": self.nm_group_var.get(),
                "target_hour": self.nm_hour_var.get(),
                "target_minute": self.nm_minute_var.get(),
                "target_second": self.nm_second_var.get(),
                "target_ms": self.nm_ms_entry.get(),
            }
            settings_file = BASE_DIR / "rush_ui_settings.json"
            atomic_write_json(settings_file, settings)
        except Exception:
            pass

    def nm_load_ui_settings(self):
        """加载新模式UI设置"""
        try:
            settings_file = BASE_DIR / "rush_ui_settings.json"
            if not settings_file.exists():
                return
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
            if settings.get("version") and settings["version"] in available_versions():
                self.nm_version_var.set(settings["version"])
                self.nm_on_version_change()
            if settings.get("period"):
                self.nm_period_var.set(settings["period"])
                self.nm_on_period_change()
            if settings.get("type"):
                self.nm_type_var.set(settings["type"])
                self.nm_update_task_list()
            if settings.get("task"):
                self.nm_task_var.set(settings["task"])
            if settings.get("account"):
                self.nm_account_var.set(settings["account"])
            if settings.get("window"):
                self.nm_window_entry.delete(0, tk.END)
                self.nm_window_entry.insert(0, settings["window"])
            if settings.get("group"):
                self.nm_group_var.set(settings["group"])
            if settings.get("group"):
                self.nm_group_var.set(settings["group"])
                self.nm_on_group_change()
            if settings.get("target_hour"):
                self.nm_hour_var.set(settings["target_hour"])
            if settings.get("target_minute"):
                self.nm_minute_var.set(settings["target_minute"])
            if settings.get("target_second"):
                self.nm_second_var.set(settings["target_second"])
            if settings.get("target_ms"):
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, settings["target_ms"])
        except Exception:
            pass

    def nm_log(self, msg):
        """新模式日志输出（毫秒级时间戳）- 线程安全"""
        now = time.time()
        timestamp = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
        line = f"[{timestamp}] {msg}\n"
        # UI操作必须在主线程执行
        def _append_log():
            try:
                self.nm_log_text.insert(tk.END, line)
                self.nm_log_text.see(tk.END)
            except Exception:
                pass
        try:
            self.after(0, _append_log)
        except Exception:
            pass
        # 同时写主日志文件（文件IO是线程安全的）
        try:
            self.log(msg)
        except Exception:
            pass

    def nm_on_version_change(self):
        """版本切换：动态更新期数下拉框"""
        version = self.nm_version_var.get()
        periods = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] not in periods:
                periods.append(t["period"])
        self.nm_period_combo.config(values=periods)
        if periods:
            self.nm_period_var.set(periods[0])
        self.nm_on_period_change()

    def nm_on_period_change(self):
        """期数切换：动态更新类型下拉框"""
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        types = []
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] not in types:
                types.append(t["type"])
        self.nm_type_combo.config(values=types)
        if types:
            self.nm_type_var.set(types[0])
        self.nm_update_task_list()

    def nm_update_task_list(self):
        """更新新模式任务下拉列表"""
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        tasks = [t for t in ALL_TASKS if t["version"] == version and t["period"] == period and t["type"] == task_type]
        task_names = [task_label(t, "arrow") for t in tasks]
        self.nm_task_combo.config(values=task_names)
        if task_names:
            self.nm_task_var.set(task_names[0])
        elif hasattr(self, 'nm_task_var'):
            self.nm_task_var.set('')
        # 更新账户列表
        accounts = self.account_mgr.accounts
        account_names = [a["name"] for a in accounts]
        self.nm_account_combo.config(values=account_names)
        if account_names and not self.nm_account_var.get():
            self.nm_account_var.set(account_names[0])

    def nm_on_group_change(self):
        """任务组切换"""
        group_name = self.nm_group_var.get()
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if group:
            self.current_group_id = group["group_id"]
            target_str = group.get("target_time", "00:00:00.000")
            try:
                parts = target_str.split(":")
                self.nm_hour_var.set(parts[0])
                self.nm_minute_var.set(parts[1])
                sec_parts = parts[2].split(".")
                self.nm_second_var.set(sec_parts[0])
                ms_val = sec_parts[1] if len(sec_parts) > 1 else "000"
                self.nm_ms_var.set(ms_val)
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, ms_val)
            except Exception:
                self.nm_hour_var.set("00")
                self.nm_minute_var.set("00")
                self.nm_second_var.set("00")
                self.nm_ms_var.set("000")
                self.nm_ms_entry.delete(0, tk.END)
                self.nm_ms_entry.insert(0, "000")
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_update_ui_state()
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    def nm_new_group(self):
        """新建任务组"""
        from tkinter import simpledialog
        name = simpledialog.askstring("新建任务组", "请输入任务组名称:", parent=self)
        if not name:
            return
        group_id = f"group_{int(time.time())}"
        new_group = {
            "group_id": group_id,
            "group_name": name,
            "target_time": "00:00:00.000",
            "tasks": []
        }
        self.rush_groups.append(new_group)
        self.current_group_id = group_id
        self.save_rush_groups()
        self.refresh_new_mode_group_list()
        # 更新下拉框选中值
        if hasattr(self, 'nm_group_var'):
            self.nm_group_var.set(name)
        self.refresh_new_mode_task_list()
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()
        self.nm_log(f"新建任务组: {name}")

    def nm_del_group(self):
        """删除当前任务组"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        from tkinter import messagebox
        if not messagebox.askyesno("确认删除", f"确定删除任务组「{group['group_name']}」吗？"):
            return
        deleted_name = group['group_name']
        self.rush_groups = [g for g in self.rush_groups if g["group_id"] != self.current_group_id]
        self.current_group_id = self.rush_groups[0]["group_id"] if self.rush_groups else None
        # 保存后立即验证，确保数据真正写入文件
        self.save_rush_groups()
        try:
            groups_file = BASE_DIR / "rush_groups.json"
            with open(groups_file, "r", encoding="utf-8") as f:
                verify_data = json.load(f)
            if any(g.get("group_name") == deleted_name for g in verify_data):
                self.nm_log(f"⚠ 删除验证失败：文件中仍存在任务组「{deleted_name}」，重试保存...")
                self.save_rush_groups()
        except Exception as e:
            self.nm_log(f"⚠ 删除验证异常: {e}")
        # 如果没有组了，清空下拉框
        if not self.rush_groups:
            self.nm_group_var.set("")
            self.nm_group_combo.config(values=[])
        self.refresh_new_mode_group_list()
        self.refresh_new_mode_task_list()
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()
        self.nm_log(f"删除任务组: {deleted_name}")

    def nm_add_task(self):
        """添加任务到当前组"""
        if not self.current_group_id:
            self.nm_log("请先选择或创建任务组")
            return
        task_text = self.nm_task_var.get()
        if not task_text:
            self.nm_log("请选择任务")
            return
        account_name = self.nm_account_var.get()
        if not account_name:
            self.nm_log("请选择账户")
            return
        # 从ALL_TASKS找到对应任务
        version = self.nm_version_var.get()
        period = self.nm_period_var.get()
        task_type = self.nm_type_var.get()
        task = None
        for t in ALL_TASKS:
            if t["version"] == version and t["period"] == period and t["type"] == task_type and task_label(t, "arrow") == task_text:
                task = t
                break
        if not task:
            self.nm_log("未找到对应任务")
            return
        try:
            window_seconds = int(self.nm_window_entry.get())
        except ValueError:
            window_seconds = 15
        try:
            base_interval = int(self.nm_base_interval_entry.get()) / 1000.0
            if base_interval < 0.3:
                base_interval = 0.3
            if base_interval > 2.0:
                base_interval = 2.0
        except ValueError:
            base_interval = 0.9
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            # 检查是否已存在
            if any(t["task_id"] == task["task_id"] for t in group["tasks"]):
                self.nm_log(f"任务已存在: {task['name']}")
                return
            # 优先级自动分配：当前组内最大优先级+1
            existing_priorities = [t["priority"] for t in group["tasks"]]
            priority = max(existing_priorities) + 1 if existing_priorities else 1
            # 获取act_id并保存（添加任务时一次性获取，抢码时直接使用）
            act_id = task.get("act_id", "")
            try:
                cookies = cookies_from_account(account_name)
                info, msg = get_mission_info(task["task_id"], cookies)
                if info:
                    # 尝试多种字段名和层级
                    for key in ["act_id", "activity_id", "ActivityId", "id"]:
                        if info.get(key):
                            act_id = str(info[key])
                            break
                    if not act_id:
                        for sub_key in ["act_info", "activity_info", "mission_info", "data"]:
                            sub = info.get(sub_key, {})
                            if isinstance(sub, dict):
                                for key in ["act_id", "activity_id", "ActivityId", "id"]:
                                    if sub.get(key):
                                        act_id = str(sub[key])
                                        break
                            if act_id:
                                break
            except Exception:
                pass
            if not act_id:
                act_id = VERSION_DEFAULT_ACT_ID.get(version, "")

            new_task = {
                "task_id": task["task_id"],
                "name": task["name"],
                "award": task["award"],
                "period": task["period"],
                "type": task["type"],
                "version": task["version"],
                "account_name": account_name,
                "priority": priority,
                "window_seconds": window_seconds,
                "base_interval": base_interval,
                "act_id": act_id,
                "status_color": "gray",
                "status_text": "查询中...",
                "task_finished": None,
                "stock_available": None
            }
            group["tasks"].append(new_task)
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.refresh_new_mode_task_list()
            self.nm_log(f"添加任务: {task['name']} (优先级{priority}, 窗口期{window_seconds}秒, 基础间隔{int(base_interval*1000)}ms)")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()
            # 异步查询任务状态
            self.after(100, lambda t=new_task: self.nm_query_task_status_async(t))

    def nm_query_task_status_async(self, task):
        """异步查询任务状态（在后台线程中执行，避免阻塞UI）"""
        import threading
        def query_thread():
            try:
                result = self._do_query_task_status(task)
                # 回到主线程更新UI
                self.after(0, lambda: self._update_task_status(task, result))
            except Exception as e:
                self.after(0, lambda ex=str(e): self._update_task_status(task, {"error": ex}))
        threading.Thread(target=query_thread, daemon=True).start()

    def nm_query_single_task(self, task):
        """手动查询单个任务状态"""
        task["status_color"] = "gray"
        task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        self.nm_log(f"[手动查询] {task.get('name', '')}...")
        self.nm_query_task_status_async(task)

    def nm_query_all_tasks(self):
        """查询当前组内所有任务状态"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            return
        self.nm_log(f"[批量查询] 开始查询 {len(group['tasks'])} 个任务状态...")
        for task in group["tasks"]:
            task["status_color"] = "gray"
            task["status_text"] = "查询中..."
        self.refresh_new_mode_task_list()
        # 逐个查询，间隔1秒避免风控
        import threading
        def query_all_thread():
            for task in group["tasks"]:
                try:
                    result = self._do_query_task_status(task)
                    self.after(0, lambda t=task, r=result: self._update_task_status(t, r))
                except Exception as e:
                    self.after(0, lambda t=task, err=str(e): self._update_task_status(t, {"error": err}))
                time.sleep(1.0)
            self.after(0, lambda: self.nm_log("[批量查询] 全部查询完成"))
        threading.Thread(target=query_all_thread, daemon=True).start()

    def nm_edit_task(self, task):
        """编辑组内任务"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return

        # 创建编辑对话框
        edit_win = tk.Toplevel(self)
        edit_win.title(f"编辑任务 - {task.get('name', '')[:20]}")
        edit_win.geometry("520x420")
        edit_win.configure(bg=COLORS["bg_card"])
        edit_win.transient(self)
        edit_win.grab_set()
        # 居中显示
        edit_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        edit_win.geometry(f"+{x}+{y}")

        # 任务信息显示
        info_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        info_frame.pack(fill=tk.X, padx=15, pady=(15, 10))
        tk.Label(info_frame, text="任务:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)
        tk.Label(info_frame, text=task.get("name", ""), bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 10, "bold"), wraplength=380, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 5))
        tk.Label(info_frame, text=f"奖励: {task.get('award', '')}", bg=COLORS["bg_card"], fg=COLORS["success"],
                 font=("微软雅黑", 10)).pack(anchor=tk.W)

        # 编辑区域
        edit_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        edit_frame.pack(fill=tk.X, padx=15, pady=10)

        # 窗口期
        row1 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=10)
        tk.Label(row1, text="窗口期(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        window_var = tk.StringVar(value=str(task.get("window_seconds", 15)))
        window_entry = tk.Entry(row1, textvariable=window_var, width=12, font=("微软雅黑", 10),
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        window_entry.pack(side=tk.LEFT, padx=5)

        # 账户选择
        row2 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=10)
        tk.Label(row2, text="账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        account_var = tk.StringVar(value=task.get("account_name", ""))
        # 获取所有账户
        account_names = []
        try:
            if hasattr(self, 'account_mgr') and self.account_mgr:
                accounts = self.account_mgr.get_all_accounts()
                account_names = [a.get("name", "") for a in accounts]
        except Exception:
            pass
        if not account_names:
            account_names = [task.get("account_name", "")]
        account_combo = ttk.Combobox(row2, textvariable=account_var, values=account_names,
                                     state="readonly", width=20, font=("微软雅黑", 10))
        account_combo.pack(side=tk.LEFT, padx=5)

        # 基础间隔
        row3 = tk.Frame(edit_frame, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, pady=10)
        tk.Label(row3, text="基础间隔(ms):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 10), width=14, anchor=tk.W).pack(side=tk.LEFT)
        interval_var = tk.StringVar(value=str(int(task.get("base_interval", 0.9) * 1000)))
        interval_entry = tk.Entry(row3, textvariable=interval_var, width=12, font=("微软雅黑", 10),
                                  bg=COLORS["bg_input"], fg=COLORS["text_primary"], insertbackground=COLORS["text_primary"])
        interval_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(row3, text="(风控后自动+1~5ms)", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)

        # 按钮区域
        btn_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        def save_edit():
            """保存修改"""
            try:
                window_val = int(window_var.get())
                interval_ms = int(interval_var.get())
                if interval_ms < 300:
                    interval_ms = 300
                if interval_ms > 2000:
                    interval_ms = 2000
                interval_val = interval_ms / 1000.0
            except ValueError:
                messagebox.showerror("错误", "窗口期和基础间隔必须是数字", parent=edit_win)
                return

            # 找到任务并更新
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["window_seconds"] = window_val
                    t["account_name"] = account_var.get()
                    t["base_interval"] = interval_val
                    # 同时更新account_id（如果能找到）
                    try:
                        if hasattr(self, 'account_mgr') and self.account_mgr:
                            accounts = self.account_mgr.get_all_accounts()
                            for a in accounts:
                                if a.get("name") == account_var.get():
                                    t["account_id"] = a.get("id", a.get("account_id", ""))
                                    break
                    except Exception:
                        pass
                    break

            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"[编辑] 任务「{task.get('name', '')}」已更新: 窗口期={window_val}秒, 账户={account_var.get()}, 间隔={interval_ms}ms")
            edit_win.destroy()
            # 编辑后重新查询状态
            for t in group.get("tasks", []):
                if t.get("task_id") == task.get("task_id"):
                    t["status_color"] = "gray"
                    t["status_text"] = "查询中..."
                    self.refresh_new_mode_task_list()
                    self.nm_query_task_status_async(t)
                    break

        tk.Button(btn_frame, text="保存", bg=COLORS["success"], fg="#ffffff",
                  font=("微软雅黑", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                  command=save_edit).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)
        tk.Button(btn_frame, text="取消", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                  font=("微软雅黑", 10), relief=tk.FLAT, cursor="hand2",
                  command=edit_win.destroy).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)

    def nm_remove_task(self, task_id):
        """从组中删除任务，删除后重新按1,2,3...分配优先级"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            group["tasks"] = [t for t in group["tasks"] if t["task_id"] != task_id]
            # 重新按顺序分配优先级
            tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            for i, t in enumerate(tasks):
                t["priority"] = i + 1
            self.save_rush_groups()
            self.refresh_new_mode_task_list()
            self.nm_log(f"删除任务，优先级已重新分配")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()

    def nm_move_task(self, task_id, direction):
        """调整任务优先级（上移/下移）"""
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
        idx = next((i for i, t in enumerate(tasks) if t["task_id"] == task_id), -1)
        if idx < 0:
            return
        swap_idx = idx + direction
        if swap_idx < 0 or swap_idx >= len(tasks):
            return
        # 交换任务位置后重新按1,2,3...分配优先级
        tasks[idx], tasks[swap_idx] = tasks[swap_idx], tasks[idx]
        for i_task, t in enumerate(tasks):
            t["priority"] = i_task + 1
        self.save_rush_groups()
        self.refresh_new_mode_task_list()
        self.nm_log(f"任务顺序已调整，优先级重新分配")
        # 刷新调度器显示
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()

    def nm_auto_save_group(self):
        """自动保存当前任务组设置（目标时间修改时触发）"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        try:
            hour = self.nm_hour_var.get()
            minute = self.nm_minute_var.get()
            second = self.nm_second_var.get()
            ms = self.nm_ms_entry.get().strip() or "000"
            target_time = f"{hour}:{minute}:{second}.{ms}"
            group["target_time"] = target_time
            self.save_rush_groups()
            self.nm_log(f"[自动保存] 任务组「{group['group_name']}」目标时间已更新为 {target_time}")
            # 同时刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()
        except Exception as e:
            pass

    def nm_save_group_settings(self):
        """保存任务组设置"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if group:
            ms_val = self.nm_ms_entry.get().strip()
            if not ms_val or not ms_val.isdigit():
                ms_val = "000"
            ms_val = ms_val.zfill(3)[:3]
            group["target_time"] = f"{self.nm_hour_var.get()}:{self.nm_minute_var.get()}:{self.nm_second_var.get()}.{ms_val}"
            self.save_rush_groups()
            self.nm_save_ui_settings()
            self.nm_log(f"任务组设置已保存: 目标时间={group['target_time']}")
            # 刷新调度器显示
            if hasattr(self, 'nm_update_scheduler'):
                self.nm_update_scheduler()
    # ========== 新模式·任务组调度器 ==========
    def nm_refresh_scheduler(self):
        """刷新调度器列表（兼容旧调用，实际使用Treeview版本）"""
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()

    def nm_switch_to_group(self, group_id):
        """从调度器切换到指定组"""
        group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
        if group:
            self.nm_group_var.set(group["group_name"])
            self.nm_on_group_change()

    def nm_start_single_group(self, group_id):
        """启动单个任务组（独立线程）"""
        group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
        if not group:
            return
        if not group.get("tasks"):
            self.nm_log(f"[{group['group_name']}] 任务组为空，无法启动")
            return
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            self.nm_log(f"[{group['group_name']}] 已在运行中")
            return
        # 启动时不再从界面读取时间覆盖group
        # 时间修改由自动保存（nm_auto_save_group）负责
        stop_flag = {"stop": False}
        self.nm_group_stop_flags[group_id] = stop_flag
        self.nm_group_status[group_id] = "running"
        thread = threading.Thread(target=self.nm_rush_worker_for_group, args=(group, stop_flag), daemon=True)
        self.nm_group_threads[group_id] = thread
        thread.start()
        self.nm_refresh_scheduler()
        self.nm_log(f"[调度器] 启动任务组: {group['group_name']} (目标: {group['target_time']})")

    def nm_stop_single_group(self, group_id):
        """停止单个任务组"""
        if group_id in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_group_status[group_id] = "stopped"
            self.nm_refresh_scheduler()
            group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
            if group:
                self.nm_log(f"[调度器] 停止任务组: {group['group_name']}")

    def nm_start_all_groups(self):
        """启动所有任务组"""
        count = 0
        for group in self.rush_groups:
            if group.get("tasks"):
                gid = group["group_id"]
                if gid not in self.nm_group_threads or not self.nm_group_threads[gid].is_alive():
                    self.nm_start_single_group(gid)
                    count += 1
        self.nm_log(f"[调度器] 全部开始: 启动了 {count} 个任务组")

    def nm_stop_all_groups(self):
        """停止所有任务组"""
        for group_id in list(self.nm_group_stop_flags.keys()):
            self.nm_stop_single_group(group_id)
        self.nm_log("[调度器] 全部停止")

    def nm_rush_worker_for_group(self, group, stop_flag):
        """单个任务组的抢码线程（调度器版本，使用独立stop_flag）"""
        gid = group["group_id"]
        try:
            self.nm_rush_worker(group)
        finally:
            if stop_flag.get("stop"):
                self.nm_group_status[gid] = "stopped"
            else:
                self.nm_group_status[gid] = "finished"
            # UI更新必须在主线程执行
            try:
                self.after(0, self.nm_refresh_scheduler)
            except Exception:
                pass

    def nm_start_rush(self):
        """启动精准抢码（支持多组同时运行）"""
        # P1-6: 新旧抢码互斥闸门
        if self.running:
            self.nm_log("⚠ 监控抢码正在运行中，请先停止后再启动精准抢码")
            return
        if not self.current_group_id:
            self.nm_log("请先选择任务组")
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group or not group.get("tasks"):
            self.nm_log("任务组为空，请先添加任务")
            return
        
        group_id = group["group_id"]
        group_name = group["group_name"]
        
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            self.nm_log(f"任务组「{group_name}」已在运行中")
            return
        
        # 启动时不再从界面读取时间覆盖group
        # 时间修改由自动保存（nm_auto_save_group）负责，确保组的target_time是最新的
        
        self.nm_group_stop_flags[group_id] = {"stop": False}
        self.nm_group_status[group_id] = "running"
        self.nm_update_ui_state()
        
        self.nm_log("=" * 50)
        self.nm_log(f"启动精准抢码: {group_name}")
        self.nm_log(f"目标时间: {group['target_time']}")
        self.nm_log(f"任务数量: {len(group['tasks'])}")
        running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()]) + 1
        self.nm_log(f"当前运行组数: {running_count}")
        
        thread = threading.Thread(target=self.nm_rush_worker, args=(group, group_id), daemon=True)
        self.nm_group_threads[group_id] = thread
        thread.start()

    def nm_stop_rush(self):
        """停止所有正在运行的精准抢码任务组"""
        running_count = 0
        for group_id, stop_flag in self.nm_group_stop_flags.items():
            if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
                stop_flag["stop"] = True
                running_count += 1
                group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                group_name = group["group_name"] if group else group_id
                self.nm_log(f"发送停止指令: {group_name}")
        
        if running_count == 0:
            self.nm_log("没有正在运行的任务组")
        else:
            self.nm_log(f"已向 {running_count} 个任务组发送停止指令，等待当前请求完成后停止...")

    def nm_sync_system_time(self):
        """同步系统时间（需要管理员权限，显示窗口+等待完成+弹结果）"""
        import subprocess
        try:
            self.nm_log("正在请求管理员权限同步系统时间...")

            # 用ShellExecuteExW获取进程句柄，可等待结束（P2-14: 引用全局定义）
            see = _SHELLEXECUTEINFOW()
            see.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
            see.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
            see.lpVerb = "runas"
            see.lpFile = "cmd.exe"
            see.lpParameters = "/c w32tm /resync /force & echo. & echo 同步完成，按任意键关闭 & pause >nul"
            see.nShow = 1  # SW_SHOWNORMAL，显示黑窗口

            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(see))
            if ok and see.hProcess:
                self.nm_log("✓ UAC已授权，正在同步（黑窗口显示执行过程）...")
                ctypes.windll.kernel32.WaitForSingleObject(see.hProcess, 30000)
                ctypes.windll.kernel32.CloseHandle(see.hProcess)
                # 同步后立即测NTP偏差
                try:
                    r = subprocess.run(
                        ["w32tm", "/stripchart", "/computer:ntp.aliyun.com", "/samples:3", "/dataonly"],
                        capture_output=True, text=True, timeout=15)
                    offs = []
                    for line in r.stdout.split('\n'):
                        if ',' in line and ('s' in line):
                            try:
                                v = line.split(',')[1].strip().replace('s', '').replace('+', '')
                                offs.append(abs(float(v) * 1000))
                            except Exception:
                                pass
                    if offs:
                        avg = sum(offs) / len(offs)
                        if avg < 100:
                            self.nm_log(f"✓ 同步成功，当前NTP偏差{avg:.0f}ms")
                            messagebox.showinfo("同步成功", f"系统时间同步完成！\n\n当前NTP偏差: {avg:.0f}ms\n（安全阈值 100ms）")
                        else:
                            self.nm_log(f"⚠ 同步完成但偏差仍有{avg:.0f}ms")
                            messagebox.showwarning("同步完成", f"同步已执行，但偏差仍较大:\n\n当前NTP偏差: {avg:.0f}ms\n建议再次同步")
                    else:
                        self.nm_log("✓ 同步命令已执行")
                        messagebox.showinfo("同步完成", "同步命令已执行，请查看抢码日志NTP偏差")
                except Exception as e:
                    self.nm_log(f"✓ 同步已执行（状态查询失败: {e}）")
                    messagebox.showinfo("同步完成", "同步命令已执行完成")
            else:
                self.nm_log("✗ 同步失败或用户取消UAC")
                messagebox.showerror("同步失败", "同步失败或用户取消了UAC授权")
        except Exception as e:
            self.nm_log(f"✗ 同步系统时间失败: {e}")
            messagebox.showerror("同步失败", f"同步系统时间失败:\n{e}")

    def nm_query_time_status(self):
        """查询系统时间同步状态"""
        import subprocess
        try:
            self.nm_log("正在查询系统时间同步状态...")
            # 查询W32Time服务状态
            result = subprocess.run(
                ["w32tm", "/query", "/status"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.nm_log("=" * 40)
                self.nm_log("📊 系统时间同步状态")
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        self.nm_log(f"  {line}")
                self.nm_log("=" * 40)
            else:
                # 可能服务没启动，尝试启动
                self.nm_log("查询失败，尝试启动W32Time服务...")
                start_result = subprocess.run(
                    ["net", "start", "w32time"],
                    capture_output=True, text=True, timeout=10
                )
                if "已经启动" in start_result.stdout or "started" in start_result.stdout.lower():
                    self.nm_log("W32Time服务已启动，请重新查询")
                else:
                    self.nm_log(f"查询失败: {result.stderr}")
                    self.nm_log("提示: 请先点击「同步系统时间」按钮，通过UAC授权后再查询")
        except Exception as e:
            self.nm_log(f"查询失败: {e}")

    def nm_fix_time_service(self):
        """一键修复时间服务：停止→注销→重注册→启动→配NTP→同步"""
        import subprocess
        try:
            self.nm_log("=" * 50)
            self.nm_log("🔧 开始修复时间服务（需要管理员权限）...")
            self.nm_log("   步骤: 停止服务 → 注销 → 重注册 → 启动 → 配NTP → 同步")

            # 写一个临时bat脚本执行完整修复流程
            bat_content = """@echo off
chcp 65001 >nul
echo ========================================
echo   时间服务修复工具
echo ========================================
echo.
echo [1/6] 停止 W32Time 服务...
net stop w32time
echo.
echo [2/6] 注销时间服务...
w32tm /unregister
echo.
echo [3/6] 重新注册时间服务...
w32tm /register
echo.
echo [4/6] 启动 W32Time 服务...
net start w32time
echo.
echo [5/6] 配置NTP服务器(阿里云+微软)...
w32tm /config /syncfromflags:manual /manualpeerlist:"ntp.aliyun.com time.windows.com ntp.tencent.com"
w32tm /config /update
echo.
echo [6/6] 强制同步时间...
w32tm /resync /force
echo.
echo ========================================
echo   修复完成！
echo ========================================
echo.
pause
"""
            # P2-12/13: 用系统临时目录，避免onefile打包后__file__在_MEIPASS导致UAC后无法访问
            import tempfile
            bat_path = os.path.join(tempfile.gettempdir(), "fix_time_service.bat")
            with open(bat_path, "w", encoding="gbk") as f:
                f.write(bat_content)

            # 用ShellExecuteExW以管理员权限运行bat，等待完成（P2-14: 引用全局定义）
            see = _SHELLEXECUTEINFOW()
            see.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
            see.fMask = 0x00000040
            see.lpVerb = "runas"
            see.lpFile = bat_path
            see.nShow = 1

            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(see))
            if ok and see.hProcess:
                self.nm_log("✓ UAC已授权，正在执行修复（黑窗口显示进度）...")
                ctypes.windll.kernel32.WaitForSingleObject(see.hProcess, 60000)
                ctypes.windll.kernel32.CloseHandle(see.hProcess)
                # 清理临时bat
                try:
                    os.remove(bat_path)
                except Exception:
                    pass
                # 修复后测偏差
                try:
                    r = subprocess.run(
                        ["w32tm", "/stripchart", "/computer:ntp.aliyun.com", "/samples:5", "/dataonly"],
                        capture_output=True, text=True, timeout=20)
                    offs = []
                    for line in r.stdout.split('\n'):
                        if ',' in line and 's' in line:
                            try:
                                v = line.split(',')[1].strip().replace('s', '').replace('+', '')
                                offs.append(abs(float(v) * 1000))
                            except Exception:
                                pass
                    if offs:
                        avg = sum(offs) / len(offs)
                        if avg < 100:
                            self.nm_log(f"✓ 修复成功！当前NTP偏差{avg:.0f}ms")
                            messagebox.showinfo("修复成功", f"时间服务修复完成！\n\n当前NTP偏差: {avg:.0f}ms\n（已恢复正常）")
                        else:
                            self.nm_log(f"⚠ 修复完成但偏差仍有{avg:.0f}ms")
                            messagebox.showwarning("修复完成", f"修复已执行，但偏差仍较大:\n\n当前NTP偏差: {avg:.0f}ms\n\n建议:\n1. 检查网络是否能访问NTP服务器\n2. 检查是否有其他软件修改系统时间\n3. 重启电脑后再试")
                    else:
                        self.nm_log("✓ 修复命令已执行")
                        messagebox.showinfo("修复完成", "时间服务修复已执行，请查看抢码日志NTP偏差")
                except Exception as e:
                    self.nm_log(f"✓ 修复已执行（查询偏差失败: {e}）")
                    messagebox.showinfo("修复完成", "时间服务修复已执行")
            else:
                self.nm_log("✗ 修复失败或用户取消UAC")
                messagebox.showerror("修复失败", "修复失败或用户取消了UAC授权")
            self.nm_log("=" * 50)
        except Exception as e:
            self.nm_log(f"✗ 修复时间服务失败: {e}")
            messagebox.showerror("修复失败", f"修复时间服务失败:\n{e}")

    def nm_update_ui_state(self):
        """更新UI状态（启动按钮/停止按钮/状态标签）"""
        try:
            running_groups = []
            for group_id, thread in self.nm_group_threads.items():
                if thread.is_alive():
                    group = next((g for g in self.rush_groups if g["group_id"] == group_id), None)
                    group_name = group["group_name"] if group else group_id
                    running_groups.append(group_name)
            
            running_count = len(running_groups)
            
            current_running = False
            if self.current_group_id and self.current_group_id in self.nm_group_threads:
                current_running = self.nm_group_threads[self.current_group_id].is_alive()
            
            if current_running:
                self.nm_start_btn.config(state=tk.DISABLED)
                self.nm_stop_btn.config(state=tk.NORMAL)
            else:
                self.nm_start_btn.config(state=tk.NORMAL)
                self.nm_stop_btn.config(state=tk.NORMAL if running_count > 0 else tk.DISABLED)
            
            if running_count > 0:
                if running_count == 1:
                    status_text = f"● 运行中: {running_groups[0]}"
                else:
                    status_text = f"● {running_count}个组运行中"
                self.nm_status_label.config(text=status_text, fg=COLORS["success"])
            else:
                self.nm_status_label.config(text="● 未运行", fg=COLORS["text_muted"])
            
            try:
                group_names = []
                for g in self.rush_groups:
                    name = g["group_name"]
                    if g["group_id"] in self.nm_group_threads and self.nm_group_threads[g["group_id"]].is_alive():
                        name = f"▶ {name} (运行中)"
                    group_names.append(name)
                self.nm_group_combo.config(values=group_names)
            except Exception:
                pass
        except Exception:
            pass

    def nm_scheduler_update_loop(self):
        """调度器定时更新循环（每秒更新一次）"""
        if hasattr(self, 'nm_scheduler_running') and self.nm_scheduler_running:
            try:
                self.nm_update_scheduler()
            except Exception:
                pass
            self.after(1000, self.nm_scheduler_update_loop)
    
    def nm_update_scheduler(self):
        """更新调度器显示"""
        if not hasattr(self, 'nm_scheduler_tree'):
            return
        
        try:
            # 清空现有数据
            for item in self.nm_scheduler_tree.get_children():
                self.nm_scheduler_tree.delete(item)
            
            now = time.time()
            
            for group in self.rush_groups:
                group_id = group["group_id"]
                group_name = group["group_name"]
                target_time = group.get("target_time", "00:00:00.000")
                tasks = group.get("tasks", [])
                task_count = len(tasks)
                
                # 判断状态
                is_running = False
                is_finished = False
                is_stopped = False
                current_task_idx = 0
                total_attempts = 0
                success_count = 0
                
                if group_id in self.nm_group_threads:
                    thread = self.nm_group_threads[group_id]
                    if thread.is_alive():
                        is_running = True
                    else:
                        # 线程已结束，检查状态
                        status = self.nm_group_status.get(group_id, "stopped")
                        if status == "finished":
                            is_finished = True
                        elif status == "stopped":
                            is_stopped = True
                
                # 计算剩余时间
                remaining_text = "-"
                status_text = "未启动"
                status_color = "#95a5a6"
                progress_text = "-"
                
                if is_running:
                    # 解析目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        if now < target_ts:
                            remaining = target_ts - now
                            remaining_text = f"等待 {int(remaining//3600):02d}:{int((remaining%3600)//60):02d}:{int(remaining%60):02d}"
                            status_text = "等待中"
                            status_color = "#3498db"
                        else:
                            remaining_text = "执行中..."
                            status_text = "运行中"
                            status_color = COLORS["success"]
                    except Exception:
                        remaining_text = "执行中..."
                        status_text = "运行中"
                        status_color = COLORS["success"]
                    
                    progress_text = f"运行中"
                    
                elif is_finished:
                    status_text = "已完成"
                    status_color = "#27ae60"
                    remaining_text = "已结束"
                    progress_text = "全部完成"
                    
                elif is_stopped:
                    status_text = "已停止"
                    status_color = "#f39c12"
                    remaining_text = "已停止"
                    progress_text = "用户停止"
                    
                else:
                    # 未启动，计算距离目标时间
                    try:
                        parts = target_time.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        sec_parts = parts[2].split(".")
                        second = int(sec_parts[0])
                        now_t = time.localtime()
                        target_ts = time.mktime((now_t.tm_year, now_t.tm_mon, now_t.tm_mday, hour, minute, second, 0, 0, -1))
                        if target_ts < now:
                            target_ts += 86400
                        
                        remaining = target_ts - now
                        if remaining < 3600:
                            remaining_text = f"{int(remaining//60)}分{int(remaining%60)}秒后"
                        else:
                            remaining_text = f"{int(remaining//3600)}时{int((remaining%3600)//60)}分后"
                    except Exception:
                        remaining_text = "-"
                
                # 插入到表格
                display_name = f"▶ {group_name}" if is_running else group_name
                item = self.nm_scheduler_tree.insert("", tk.END, values=(
                    display_name, target_time, status_text, task_count, remaining_text, progress_text
                ))
                
                # 设置行颜色
                self.nm_scheduler_tree.tag_configure("running", background="#1a3a1a")
                self.nm_scheduler_tree.tag_configure("waiting", background="#1a2a3a")
                self.nm_scheduler_tree.tag_configure("finished", background="#1a3a2a")
                self.nm_scheduler_tree.tag_configure("stopped", background="#3a2a1a")
                
                if is_running:
                    if "等待" in remaining_text:
                        self.nm_scheduler_tree.item(item, tags=("waiting",))
                    else:
                        self.nm_scheduler_tree.item(item, tags=("running",))
                elif is_finished:
                    self.nm_scheduler_tree.item(item, tags=("finished",))
                elif is_stopped:
                    self.nm_scheduler_tree.item(item, tags=("stopped",))
                    
        except Exception as e:
            pass
        
        # 动态调整Treeview高度，显示全部任务组
        try:
            group_count = len(self.rush_groups)
            # 至少显示3行，最多显示20行
            display_height = max(3, min(group_count, 20))
            self.nm_scheduler_tree.configure(height=display_height)
        except Exception:
            pass
    
    def nm_scheduler_toggle(self):
        """双击调度器项：启动/停止"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        # 找到对应的组
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        
        # 检查是否在运行
        if group_id in self.nm_group_threads and self.nm_group_threads[group_id].is_alive():
            # 停止
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            # 启动
            self.current_group_id = group_id
            # 同步界面显示：更新任务组选择和时间输入框，避免启动时覆盖错误时间
            self.nm_group_var.set(group_name)
            self.nm_on_group_change()
            self.nm_start_rush()
    
    def nm_scheduler_start_selected(self):
        """启动选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        self.current_group_id = group["group_id"]
        # 同步界面显示：更新任务组选择和时间输入框，避免启动时覆盖错误时间
        self.nm_group_var.set(group_name)
        self.nm_on_group_change()
        self.nm_start_rush()
    
    def nm_scheduler_stop_selected(self):
        """停止选中的任务组"""
        selected = self.nm_scheduler_tree.selection()
        if not selected:
            self.nm_log("请先在调度器中选择一个任务组")
            return
        
        item = selected[0]
        values = self.nm_scheduler_tree.item(item, "values")
        group_name = values[0].replace("▶ ", "").strip()
        
        group = next((g for g in self.rush_groups if g["group_name"] == group_name), None)
        if not group:
            return
        
        group_id = group["group_id"]
        if group_id in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id]["stop"] = True
            self.nm_log(f"调度器：停止任务组「{group_name}」")
        else:
            self.nm_log(f"任务组「{group_name}」未在运行")

    def nm_rush_worker(self, group, group_id=None):
        """精准抢码核心线程"""
        """精准抢码核心线程（支持多组独立运行）"""
        if group_id is None:
            group_id = group.get("group_id", "default")
        if group_id not in self.nm_group_stop_flags:
            self.nm_group_stop_flags[group_id] = {"stop": False}
        stop_flag = self.nm_group_stop_flags[group_id]
        group_name = group.get("group_name", "未知")
        try:
            stop_flag["last_request_time"] = 0  # 每个任务组独立维护最后请求时间
            target_time_str = group.get("target_time", "00:00:00.000")
            # 解析目标时间（支持毫秒）
            parts = target_time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            sec_parts = parts[2].split(".")
            second = int(sec_parts[0])
            millisecond = int(sec_parts[1]) if len(sec_parts) > 1 else 0

            now = time.localtime()
            target_timestamp = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, hour, minute, second, 0, 0, -1)) + millisecond / 1000.0
            if target_timestamp < time.time():
                target_timestamp += 86400  # 等到明天

            wait_seconds = target_timestamp - time.time()
            self.nm_log(f"等待 {wait_seconds:.1f} 秒后开始（目标: {time.strftime('%H:%M:%S', time.localtime(target_timestamp))}）")

            # ===== 阶段1: NTP同步（抢码前1分钟或立即）=====
            ntp_offset = 0  # NTP偏差（秒），正数表示本地慢
            if wait_seconds > 60:
                # 等到抢码前1分钟再同步
                sync_time = target_timestamp - 60
                while time.time() < sync_time and not stop_flag["stop"]:
                    time.sleep(1)
                if not stop_flag["stop"]:
                    ntp_offset = self.nm_ntp_sync()
            else:
                ntp_offset = self.nm_ntp_sync()

            # ===== 阶段2: 等待到目标时间前2.5秒，连接预热 =====
            prewarm_time = target_timestamp - 2.5
            while time.time() < prewarm_time and not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if int(remaining) % 10 == 0 and int(remaining) > 0:
                    self.nm_log(f"  还剩 {int(remaining)} 秒...")
                time.sleep(0.5)

            if stop_flag["stop"]:
                self.nm_log("抢码已取消")
                return

            # 连接预热：提前2.5秒建立连接（并行建立，act_id已在添加任务时获取）
            self.nm_log("[连接预热] 提前2.5秒建立TCP连接（并行建立，act_id已在添加任务时获取）...")
            sessions = {}
            task_infos = {}
            import threading as _prewarm_threading
            prewarm_results = {}
            prewarm_lock = _prewarm_threading.Lock()
            
            def _prewarm_single_task(task):
                """单个任务的连接预热（在线程中执行）"""
                account = self.account_mgr.get_account(task["account_name"])
                if not account:
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("error", f"账户不存在: {task['account_name']}", None, None)
                    return
                session = requests.Session()
                session.headers.update(HEADERS)
                try:
                    session.get("https://www.bilibili.com", timeout=5)
                    # 【重要】清除预热时自动获取的cookie（buvid3/b_nut等），
                    # 避免与用户cookie合并导致B站反作弊返回[-351]错误
                    session.cookies.clear()
                    task_info = self.build_task_info_from_task(task)
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("ok", "", session, task_info)
                except Exception as e:
                    task_info = self.build_task_info_from_task(task)
                    with prewarm_lock:
                        prewarm_results[task["task_id"]] = ("error", str(e), session, task_info)
            
            # 并行建立所有连接
            prewarm_tasks = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            prewarm_threads = []
            for task in prewarm_tasks:
                t = _prewarm_threading.Thread(target=_prewarm_single_task, args=(task,), daemon=True)
                prewarm_threads.append(t)
                t.start()
            # 等待所有预热完成（最多4秒）
            for t in prewarm_threads:
                t.join(timeout=4)
            # 收集结果（按优先级顺序输出日志）
            for task in prewarm_tasks:
                result = prewarm_results.get(task["task_id"], ("error", "预热超时", None, None))
                status, msg, session, task_info = result
                if session:
                    sessions[task["task_id"]] = session
                if task_info:
                    task_infos[task["task_id"]] = task_info
                else:
                    task_infos[task["task_id"]] = self.build_task_info_from_task(task)
                if status == "ok":
                    self.nm_log(f"  ✓ {task['name']}: 连接已建立, act_id={task_infos[task['task_id']].get('act_id', '')}")
                else:
                    self.nm_log(f"  ⚠ {task['name']}: 连接预热异常: {msg}, 使用保存的act_id={task_infos[task['task_id']].get('act_id', '')}")

            # 计算提前量：基础提前量 + NTP偏差修正
            # NTP offset = ((t2-t1)+(t3-t4))/2，正数=本地慢于服务器，需要更多提前量
            base_advance = 100  # 基础提前量100ms（实测高峰期单向RTT约120ms，目标到达时间=目标后约20ms）
            ntp_correction = ntp_offset * 1000  # NTP偏差转ms
            dynamic_advance = base_advance + ntp_correction
            # 限制范围：0ms ~ 1500ms，避免异常值
            dynamic_advance = max(0, min(1500, dynamic_advance))

            # NTP偏差过大时强制警告（>100ms会显著影响首枪精度）
            if abs(ntp_correction) > 100:
                self.nm_log(f"[⚠️ NTP偏差警告] 当前偏差{ntp_correction:.0f}ms，超过100ms安全阈值！")
                self.nm_log(f"[⚠️ NTP偏差警告] 首枪 timing 误差可能超过±100ms，建议立即同步系统时间后重试")
                try:
                    self.after(0, lambda: messagebox.showwarning("NTP时间偏差过大",
                        f"当前系统时间与NTP服务器偏差 {ntp_correction:.0f}ms\n"
                        f"超过100ms安全阈值，抢码 timing 可能失准！\n\n"
                        f"建议：点击「同步系统时间」按钮或手动执行 w32tm /resync"))
                except Exception:
                    pass
            elif abs(ntp_correction) > 10:
                self.nm_log(f"[提前量修正] 基础{base_advance}ms + NTP偏差{ntp_correction:.0f}ms = {dynamic_advance:.0f}ms")
            else:
                self.nm_log(f"[固定提前量] {dynamic_advance:.0f}ms (首次请求目标后约50ms到达)")

            # ===== 阶段3: 精准首发（自旋等待到目标时间-动态提前量）=====
            fire_time = target_timestamp - dynamic_advance / 1000.0
            now_time = time.time()

            # P2-5: 用perf_counter做精确自旋等待，timeBeginPeriod提高Windows定时器精度
            try:
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass
            _perf_start = time.perf_counter()
            _time_start = now_time
            fire_time_perf = _perf_start + (fire_time - _time_start)

            # 如果预热超时导致fire_time已过，立即发送（不再等待）
            if now_time >= fire_time:
                self.nm_log(f"[精准首发] 预热已超时({(now_time - target_timestamp)*1000:.0f}ms)，立即发送")
            else:
                self.nm_log(f"[精准首发] 目标 {target_time_str}，提前{dynamic_advance:.0f}ms发送，自旋等待中...")
                while time.perf_counter() < fire_time_perf and not stop_flag["stop"]:
                    remaining = fire_time_perf - time.perf_counter()
                    if remaining > 0.1:
                        time.sleep(remaining / 2)
                    elif remaining > 0.02:
                        time.sleep(0.001)
                    # 小于20ms时自旋（忙等待），避免Windows sleep精度问题

            if stop_flag["stop"]:
                self.nm_log("抢码已取消")
                try:
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
                return

            actual_fire = time.time()
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
            self.nm_log(f"[精准首发] 发送！目标偏差: {(actual_fire - target_timestamp)*1000:.1f}ms")

            # ===== 阶段4: 按优先级依次执行任务 =====
            tasks_sorted = sorted(group["tasks"], key=lambda t: t.get("priority", 99))
            for task in tasks_sorted:
                if stop_flag["stop"]:
                    break

                task_deadline = target_timestamp + task.get("window_seconds", 15)
                if time.time() > task_deadline:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] {task['name']} 已过窗口期，跳过")
                    continue

                self.nm_log(f"[优先级{task.get('priority', '?')}] 开始: {task['name']} => {task['award']} (窗口期{task.get('window_seconds', 15)}秒)")

                success = self.nm_execute_task(task, task_infos.get(task["task_id"]),
                                               sessions.get(task["task_id"]), task_deadline, target_timestamp, stop_flag)

                if success:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✓ 领取成功，立即启动下一个优先级")
                else:
                    self.nm_log(f"[优先级{task.get('priority', '?')}] ✗ 未成功，启动下一个优先级")
                
                # 切换优先级前补足请求间隔，避免连续快速请求触发风控
                task_index = tasks_sorted.index(task)
                if task_index < len(tasks_sorted) - 1 and not stop_flag["stop"]:
                    switch_interval = task.get("base_interval", 0.9)
                    elapsed = time.time() - stop_flag.get("last_request_time", 0)
                    wait_time = switch_interval - elapsed
                    if wait_time > 0:
                        self.nm_log(f"  距上次请求 {elapsed*1000:.0f}ms，补足 {wait_time*1000:.0f}ms 后切换...")
                        time.sleep(wait_time)
                    else:
                        self.nm_log(f"  距上次请求 {elapsed*1000:.0f}ms，已超过间隔，立即切换")

            self.nm_log("=" * 50)
            self.nm_log("精准抢码全部结束")

        except Exception as e:
            self.nm_log(f"抢码异常: {e}")
            import traceback
            self.nm_log(traceback.format_exc())
        finally:
            self.nm_group_status[group_id] = "finished"
            if group_id in self.nm_group_threads:
                del self.nm_group_threads[group_id]
            try:
                self.after(0, lambda: self.nm_update_ui_state())
            except Exception:
                pass
            self.nm_log(f"任务组「{group_name}」已结束")
            running_count = len([g for g, t in self.nm_group_threads.items() if t.is_alive()])
            if running_count > 0:
                self.nm_log(f"还有 {running_count} 个任务组正在运行")

    def nm_ntp_sync(self):
        """NTP时间同步（使用socket方式，不依赖第三方库）"""
        import struct
        import socket
        ntp_servers = ["ntp.aliyun.com", "ntp.tencent.com", "cn.pool.ntp.org", "time.windows.com"]
        for server in ntp_servers:
            client = None
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.settimeout(3)
                # NTP请求包：LI=0, VN=3, Mode=3 (client)
                data = b'\x1b' + 47 * b'\0'
                t1 = time.time()
                client.sendto(data, (server, 123))
                data, address = client.recvfrom(1024)
                t4 = time.time()
                if data:
                    # 解析NTP响应
                    unpacked = struct.unpack('!12I', data[0:48])
                    # 接收时间戳 (t2) 和 发送时间戳 (t3)
                    t2 = unpacked[8] - 2208988800 + unpacked[9] / 4294967296.0
                    t3 = unpacked[10] - 2208988800 + unpacked[11] / 4294967296.0
                    # 计算偏差: offset = ((t2-t1) + (t3-t4)) / 2
                    offset = ((t2 - t1) + (t3 - t4)) / 2.0
                    self.nm_log(f"[NTP同步] 服务器={server}, 偏差={offset*1000:.1f}ms")
                    if abs(offset) > 0.5:
                        self.nm_log(f"[NTP同步] 偏差较大，建议手动同步系统时间")
                    return offset
            except Exception:
                continue
            finally:
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
        self.nm_log("[NTP同步] 所有NTP服务器均不可用，使用本地时间")
        return 0

    def nm_execute_task(self, task, task_info, session, deadline, target_time, stop_flag):
        """执行单个任务的抢码（带风控递增延迟）
        P1-4: target_time显式传入，不再从deadline反推
        """
        account = self.account_mgr.get_account(task["account_name"])
        if not account:
            self.nm_log(f"  账户不存在: {task['account_name']}")
            return False

        cookies = cookies_from_account(account)
        if not task_info:
            task_info = self.build_task_info_from_task(task)

        # 预生成随机波动数列（±30ms），提前计算好避免运行时随机开销
        import random
        random_fluctuations = [random.randint(-30, 30) for _ in range(100)]

        base_interval = task.get("base_interval", 1.0)  # P2-8: 默认1.0秒，符合实测安全线
        current_interval = base_interval
        attempt = 0
        success = False
        consecutive_risk_control = 0  # P1-3: 连续风控计数

        while time.time() < deadline and not stop_flag["stop"]:
            attempt += 1
            try:
                stop_flag["last_request_time"] = time.time()  # 记录请求发出时间（每组独立）
                ok, msg = self.do_receive_fast(task, task_info, account, session)
                recv_time = time.time()
                last_req = stop_flag.get("last_request_time", 0)
                rtt_ms = (recv_time - last_req) * 1000
                send_str = time.strftime("%H:%M:%S", time.localtime(last_req)) + "." + str(int((last_req % 1) * 1000)).zfill(3)
                recv_str = time.strftime("%H:%M:%S", time.localtime(recv_time)) + "." + str(int((recv_time % 1) * 1000)).zfill(3)
            except Exception as e:
                ok, msg = False, f"异常: {e}"
                recv_time = time.time()
                last_req = stop_flag.get("last_request_time", 0)
                rtt_ms = (recv_time - last_req) * 1000 if last_req > 0 else 0
                send_str = time.strftime("%H:%M:%S", time.localtime(last_req)) + "." + str(int((last_req % 1) * 1000)).zfill(3) if last_req > 0 else "??:??:??.???"
                recv_str = time.strftime("%H:%M:%S", time.localtime(recv_time)) + "." + str(int((recv_time % 1) * 1000)).zfill(3)

            if ok:
                success = True
                self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 🎉 第{attempt}次: 领取成功！({task['account_name']})")
                self.nm_log(f"  💡 提示: 兑换码请在「兑换码」页面点击「从领取记录导入」获取")
                break
            else:
                # 判断是否是未到领奖时间（202120），这种情况不切下一个优先级
                if "202120" in msg or "未到领取时间" in msg or "未到领奖时间" in msg:
                    # P2-7: 未到领取时间时，根据距目标时间动态调整间隔
                    _time_to_target = target_time - time.time()
                    if _time_to_target > 10:
                        current_interval = min(current_interval, 2.0)  # 还早，放慢
                    elif _time_to_target > 3:
                        current_interval = min(current_interval, 1.0)  # 接近，正常
                    else:
                        current_interval = base_interval  # 快到了，用基础间隔
                    self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 未到领取时间（距目标{_time_to_target:.1f}s），间隔{current_interval*1000:.0f}ms")
                elif "75255" in msg or "库存已经使用完" in msg or "库存已使用完" in msg:
                    # P1-4: 直接用传入的target_time，不再从deadline反推
                    consecutive_risk_control = 0
                    _elapsed_after_target = time.time() - target_time
                    _over_5s = _elapsed_after_target > 5
                    if not _over_5s:
                        # 目标后5秒内：库存可能正在刷新，放慢间隔持续重试（不限时段）
                        current_interval = max(current_interval, 2.0)
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 库存已使用完（目标后{_elapsed_after_target:.1f}s<5s，持续重试）")
                    else:
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 库存已使用完（目标后{_elapsed_after_target:.1f}s），切下一个优先级")
                        break
                elif "202129" in msg or "奖励领取已结束" in msg:
                    self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 奖励领取已结束，切下一个优先级")
                    break
                elif "-705" in msg or "-509" in msg or "-702" in msg or "请求过于频繁" in msg or "请求频率过高" in msg:
                    # 风控，间隔保持基础间隔不变（靠±30ms波动）
                    consecutive_risk_control += 1
                    # P1-3: 连续风控3次后，如果间隔被升过，恢复基础间隔（避免永久卡2秒）
                    if consecutive_risk_control >= 3 and current_interval != base_interval:
                        current_interval = base_interval
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 风控{consecutive_risk_control}次，恢复基础间隔{base_interval*1000:.0f}ms")
                    else:
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: 风控 {msg[:25]}，下次间隔 {current_interval*1000:.0f}ms")
                else:
                    # 无风控（未成功但也没被风控），恢复基础间隔
                    if current_interval != base_interval:
                        current_interval = base_interval
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: {msg[:40]}（风控已过，恢复基础间隔{base_interval*1000:.0f}ms）")
                    else:
                        self.nm_log(f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: {msg[:40]}")

            # 等待到下次尝试（从请求发出时间开始计算，叠加±30ms随机波动）
            fluctuation = random_fluctuations[min(attempt - 1, len(random_fluctuations) - 1)] / 1000.0
            next_time = stop_flag.get("last_request_time", time.time()) + current_interval + fluctuation
            while time.time() < next_time and time.time() < deadline and not stop_flag["stop"]:
                time.sleep(0.001)

        if not success and time.time() >= deadline:
            self.nm_log(f"  窗口期结束，共尝试{attempt}次")
        return success
