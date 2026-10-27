# -*- coding: utf-8 -*-
"""精准抢码（新模式）全部逻辑：任务组、调度器、NTP、首枪、风控退避。

以 Mixin 形式提供，由 RushRewardFrame 继承。所有方法都依赖宿主类提供的
self.rush_groups / self.nm_group_threads / self.account_mgr 等属性。
"""

import ctypes
import json, os, random, struct, subprocess, threading, time
import tkinter as tk
from tkinter import ttk, messagebox

import requests

from config import (COLORS, BASE_DIR, HEADERS)
from tasks_config import ALL_TASKS, VERSION_DEFAULT_ACT_ID
from storage import atomic_write_json
from bili_api import (cookies_from_account, get_mission_info,
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

    def nm_quick_select_claimable(self):
            """快捷选中【已完成且可抢】的任务（v6.4.5 用户需求）。

            用户：「查询到已完成的任务后，在抢码界面可以进行快捷选中，方便选择」

            逻辑：
              1. 读取持久化的任务状态缓存（rush_stats.load_task_status_cache）
              2. 筛出 task_finished=True 且 stock_available=True 且 status 不在 (6,7)
              3. 列出这些任务的 任务名 + 账户 + 状态，让用户确认
              4. 确认后把它们按当前版本/期数/类型批量加入当前任务组

            返回：加入的任务数
            """
            try:
                import rush_stats as _rs
            except Exception:
                return 0

            try:
                cache = _rs.load_task_status_cache()
            except Exception:
                cache = {}

            if not cache:
                messagebox.showinfo(
                    "暂无查询结果",
                    "还没有查询过任务状态。\n\n"
                    "请先点「📋 查询可领取」查询任务，\n"
                    "查询结果会自动保存，重启后仍可快捷选中。",
                    parent=self.winfo_toplevel())
                return 0

            try:
                claimables = _rs.claimable_tasks(cache)
            except Exception:
                claimables = []

            if not claimables:
                messagebox.showinfo(
                    "没有可抢任务",
                    "已查询的任务里没有「已完成且可抢」的。\n\n"
                    "可抢条件：任务已完成 + 库存充足 + 非已领取/无资格。\n"
                    "可以重新查询一次，或等待任务完成。",
                    parent=self.winfo_toplevel())
                return 0

            # 构造选择列表
            lines = []
            for i, c in enumerate(claimables[:40], 1):
                lines.append("%2d. %s｜%s｜%s" % (
                    i,
                    str(c.get("task_name", "?"))[:26],
                    str(c.get("account", "?"))[:10],
                    str(c.get("status_text", ""))[:14]))
            preview = "\n".join(lines)
            if len(claimables) > 40:
                preview += "\n... 另有 %d 个" % (len(claimables) - 40)

            if not messagebox.askyesno(
                    "快捷选中可抢任务",
                    "找到 %d 个「已完成且可抢」的任务：\n\n%s\n\n"
                    "确定把它们加入当前任务组吗？\n"
                    "（已存在的任务会跳过，不重复添加）" % (len(claimables), preview),
                    parent=self.winfo_toplevel()):
                return 0

            group = None
            if self.current_group_id:
                group = next((g for g in self.rush_groups
                              if g["group_id"] == self.current_group_id), None)
            if not group:
                messagebox.showwarning(
                    "请先选择任务组",
                    "请先在顶部选择一个任务组，再执行快捷选中。",
                    parent=self.winfo_toplevel())
                return 0

            existing = {(t.get("task_id"), t.get("account_name"))
                        for t in group.get("tasks", [])}
            added = 0
            for c in claimables:
                tid = str(c.get("task_id", ""))
                acc = str(c.get("account", ""))
                if not tid:
                    continue
                if (tid, acc) in existing:
                    continue
                new_task = {
                    "task_id": tid,
                    "name": str(c.get("task_name", "")),
                    "award": "",
                    "window_seconds": 120,
                    "priority": len(group.get("tasks", [])) + 1,
                    "account_name": acc,
                    "act_id": str(c.get("act_id", "")),
                    "version": str(c.get("version", "")),
                    "status_color": "green",
                    "status_text": "✓ 可抢（来自快捷选中）",
                    "task_finished": True,
                    "stock_available": True,
                }
                group.setdefault("tasks", []).append(new_task)
                existing.add((tid, acc))
                added += 1

            if added:
                try:
                    self.save_rush_groups()
                except Exception:
                    pass
                try:
                    self.refresh_new_mode_task_list()
                except Exception:
                    pass
                try:
                    self.nm_update_scheduler()
                except Exception:
                    pass
                self.nm_log("[快捷选中] 已加入 %d 个可抢任务到「%s」"
                            % (added, group.get("group_name", "?")))
                messagebox.showinfo(
                    "已加入",
                    "成功加入 %d 个可抢任务到任务组「%s」。"
                    % (added, group.get("group_name", "?")),
                    parent=self.winfo_toplevel())
            else:
                messagebox.showinfo(
                    "无需添加",
                    "这些任务都已在当前任务组中，无需重复添加。",
                    parent=self.winfo_toplevel())
            return added

    def nm_refresh_version_combo(self):
        """刷新版本下拉框（v6.4.8）。

        为什么需要：nm_version_combo 在 UI 构建时只读取一次 ALL_TASKS，
        之后在查询中心新建的版本集合不会自动出现在下拉框里。
        这里提供主动刷新，供新建/删除版本后调用。
        """
        try:
            import tasks_config as _tc
            names = _tc.all_version_names()
            if not hasattr(self, "nm_version_combo"):
                return
            cur = ""
            try:
                cur = str(self.nm_version_var.get() or "")
            except Exception:
                pass
            self.nm_version_combo.config(values=names)
            if cur and cur in names:
                self.nm_version_var.set(cur)
            elif names:
                self.nm_version_var.set(names[0])
        except Exception:
            pass

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

    def nm_rename_group(self):
        """重命名当前任务组（v6.2.1 新增）。

        校验规则：
          - 不能为空
          - 不能与已有组重名（否则下拉框会混淆，且预案按名字查找会出错）
          - 长度不超过 30 字符
        """
        from tkinter import simpledialog, messagebox
        if not self.current_group_id:
            messagebox.showwarning("提示", "请先选择要改名的任务组", parent=self.winfo_toplevel())
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            messagebox.showwarning("提示", "当前任务组不存在", parent=self.winfo_toplevel())
            return

        old_name = group["group_name"]
        new_name = simpledialog.askstring(
            "重命名任务组",
            f"请输入新的任务组名称（当前：{old_name}）：",
            initialvalue=old_name,
            parent=self.winfo_toplevel()
        )
        if new_name is None:
            return   # 用户取消
        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning("提示", "任务组名称不能为空", parent=self.winfo_toplevel())
            return
        if new_name == old_name:
            return   # 没变化
        if len(new_name) > 30:
            messagebox.showwarning("提示", "任务组名称不能超过 30 个字符",
                                   parent=self.winfo_toplevel())
            return
        # 重名校验
        dup = next((g for g in self.rush_groups
                    if g["group_id"] != self.current_group_id and g.get("group_name") == new_name), None)
        if dup:
            messagebox.showwarning("提示", f"已存在同名任务组「{new_name}」，请换一个名称",
                                   parent=self.winfo_toplevel())
            return

        group["group_name"] = new_name
        # 保存并立即验证，确保真正写入文件
        self.save_rush_groups()
        try:
            from config import BASE_DIR
            groups_file = BASE_DIR / "rush_groups.json"
            with open(groups_file, "r", encoding="utf-8") as f:
                verify_data = json.load(f)
            found = next((g for g in verify_data if g.get("group_id") == self.current_group_id), None)
            if not found or found.get("group_name") != new_name:
                self.nm_log(f"⚠ 改名验证失败，重试保存...")
                self.save_rush_groups()
        except Exception as e:
            self.nm_log(f"⚠ 改名验证异常: {e}")

        # 刷新界面
        if hasattr(self, 'nm_group_var'):
            self.nm_group_var.set(new_name)
        self.refresh_new_mode_group_list()
        if hasattr(self, 'nm_update_scheduler'):
            self.nm_update_scheduler()
        self.nm_log(f"任务组改名: 「{old_name}」-> 「{new_name}」")
        messagebox.showinfo("改名成功",
                            f"任务组已重命名为「{new_name}」",
                            parent=self.winfo_toplevel())

    def nm_del_group(self):
        """删除当前任务组"""
        if not self.current_group_id:
            return
        group = next((g for g in self.rush_groups if g["group_id"] == self.current_group_id), None)
        if not group:
            return
        from tkinter import messagebox
        if not messagebox.askyesno("确认删除", f"确定删除任务组「{group['group_name']}」吗？", parent=self.winfo_toplevel()):
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

        DarkButton(btn_frame, text="保存", command=save_edit, bg_color=COLORS["success"], text_color="#ffffff", height=32).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)
        DarkButton(btn_frame, text="取消", command=edit_win.destroy, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32).pack(side=tk.RIGHT, padx=5, ipadx=20, ipady=4)

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
        """同步系统时间（v6.4.0 重写：真正验证结果 + 明确失败原因）。

        原实现的问题（实测确认）：
          1. 只检查命令是否"发出"，不检查时间是否真的被修正
          2. 用 w32tm /resync，但实测在权限不足时直接失败（0x80070005）
          3. 失败时仍提示"同步完成"，用户以为成功了

        新实现：
          1. UAC 提权执行 w32tm 完整修复流程（stop→unregister→register→start→config→resync）
          2. 同步前后各测一次真实 NTP 偏差，用【偏差是否下降】判断成功
          3. 失败时明确告知原因和解法
        """
        import subprocess

        # ---- 1) 同步前测基线偏差 ----
        before_off, _, _ = self.nm_measure_time_offset(samples_per_server=2)
        if before_off is not None:
            self.nm_log(f"[时间同步] 同步前偏差 {before_off:+.0f}ms")
        else:
            self.nm_log("[时间同步] 同步前无法测量偏差（网络问题）")

        # ---- 2) UAC 提权执行完整修复 ----
        # 用临时 bat 脚本：完整重置时间服务 + 强制同步
        # 注意：只做 resync 往往因权限/服务状态失败，需要完整流程
        bat_lines = [
            "@echo off",
            "chcp 65001 >nul",
            "echo ===== 正在修复系统时间 =====",
            "echo [1/5] 停止时间服务...",
            "net stop w32time >nul 2>&1",
            "echo [2/5] 注册时间服务...",
            "w32tm /unregister >nul 2>&1",
            "w32tm /register >nul 2>&1",
            "echo [3/5] 启动时间服务...",
            "net start w32time >nul 2>&1",
            "echo [4/5] 配置NTP服务器...",
            'w32tm /config /syncfromflags:manual /manualpeerlist:"ntp.aliyun.com ntp.tencent.com time.windows.com" >nul 2>&1',
            "w32tm /config /update >nul 2>&1",
            "echo [5/5] 强制同步...",
            "w32tm /resync /force",
            "echo.",
            "echo ===== 完成，窗口将在3秒后关闭 =====",
            "timeout /t 3 >nul",
        ]
        import tempfile
        bat_path = os.path.join(tempfile.gettempdir(), "dsh_fix_time.bat")
        try:
            with open(bat_path, "w", encoding="gbk") as f:
                f.write("\r\n".join(bat_lines))
        except Exception as e:
            messagebox.showerror("无法创建脚本", f"写入临时脚本失败：{e}",
                                 parent=self.winfo_toplevel())
            return

        self.nm_log("[时间同步] 请求管理员权限（请在弹出的UAC窗口点「是」）...")
        try:
            see = _SHELLEXECUTEINFOW()
            see.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
            see.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
            see.lpVerb = "runas"
            see.lpFile = "cmd.exe"
            see.lpParameters = f'/c "{bat_path}"'
            see.nShow = 1
            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(see))
        except Exception as e:
            self.nm_log(f"[时间同步] 提权失败: {e}")
            messagebox.showerror("同步失败", f"请求管理员权限失败：\n{e}",
                                 parent=self.winfo_toplevel())
            return

        if not ok or not see.hProcess:
            # 用户点了"否"，或 UAC 被拒绝
            err = ctypes.get_last_error()
            self.nm_log(f"[时间同步] 用户取消或UAC拒绝（错误码 {err}）")
            messagebox.showwarning(
                "同步已取消",
                "未获得管理员权限，无法修改系统时间。\n\n"
                "影响：时钟偏差会继续累积，但程序会自动补偿。\n"
                "解法：右键程序 → 以管理员身份运行，再点此按钮。",
                parent=self.winfo_toplevel())
            return

        self.nm_log("[时间同步] 已授权，等待修复流程完成...")
        ctypes.windll.kernel32.WaitForSingleObject(see.hProcess, 60000)
        ret_code = ctypes.c_ulong(0)
        try:
            ctypes.windll.kernel32.GetExitCodeProcess(
                see.hProcess, ctypes.byref(ret_code))
        except Exception:
            pass
        ctypes.windll.kernel32.CloseHandle(see.hProcess)
        self.nm_log(f"[时间同步] 修复命令执行完毕（返回码 {ret_code.value}）")

        # ---- 3) 同步后复测，用偏差是否下降判断是否真的成功 ----
        time.sleep(1.0)
        after_off, _, _ = self.nm_measure_time_offset(samples_per_server=2)
        if after_off is None:
            self.nm_log("[时间同步] 同步后无法测量偏差（网络问题），无法确认结果")
            messagebox.showwarning(
                "无法确认结果",
                "修复命令已执行，但无法测量当前偏差。\n\n"
                "请稍后点「查询时间状态」确认。",
                parent=self.winfo_toplevel())
            return

        self.nm_log(f"[时间同步] 同步后偏差 {after_off:+.0f}ms")
        if before_off is not None:
            improved = abs(before_off) - abs(after_off)
            self.nm_log(f"[时间同步] 改善 {improved:+.0f}ms")
        else:
            improved = None

        # ---- 4) 根据真实结果给出明确反馈 ----
        if abs(after_off) <= 50:
            self.nm_log(f"✓ 同步成功，偏差已降至 {after_off:+.0f}ms")
            messagebox.showinfo(
                "同步成功",
                f"系统时间同步成功！\n\n"
                f"同步前：{('%+.0fms' % before_off) if before_off is not None else '未知'}\n"
                f"同步后：{after_off:+.0f}ms\n\n"
                "偏差已降至安全范围（≤50ms）。",
                parent=self.winfo_toplevel())
        elif improved is not None and improved > 50:
            self.nm_log(f"○ 同步部分成功，偏差 {before_off:+.0f} -> {after_off:+.0f}ms")
            messagebox.showinfo(
                "同步部分成功",
                f"偏差有所改善，但仍有 {(after_off):+.0f}ms。\n\n"
                f"同步前：{before_off:+.0f}ms\n"
                f"同步后：{after_off:+.0f}ms\n\n"
                "可以再点一次同步，或用「一键修复时间服务」。",
                parent=self.winfo_toplevel())
        else:
            self.nm_log(f"✗ 同步失败，偏差仍为 {after_off:+.0f}ms")
            messagebox.showerror(
                "同步失败",
                f"时间没有成功校正。\n\n"
                f"当前偏差：{after_off:+.0f}ms\n\n"
                "可能原因：\n"
                "  1. Windows 时间服务被组策略禁用\n"
                "  2. NTP 端口(123/UDP)被防火墙拦截\n"
                "  3. 系统时间被其他软件锁定\n\n"
                "建议：点「一键修复时间服务」重装服务，\n"
                "或手动执行 w32tm /resync（管理员命令行）。",
                parent=self.winfo_toplevel())
    def nm_measure_time_offset(self, samples_per_server=2):
        """用原生 NTP 协议直接测系统时间偏差（v6.2.1 新增）。

        为什么不用 w32tm：
          实测 w32tm /query /status 在时间服务未启动时直接失败
          （错误 0x80070426），而 /stripchart 需要 4 秒以上。
          原生 NTP socket 只需 0.2 秒，且不依赖 Windows 时间服务。

        返回值：(offset_ms, rtt_ms, server_name) 或 (None, None, "")
          offset 定义：服务器时间 - 本地时间，正数表示本地慢。
        """
        import socket
        import struct
        import statistics
        servers = ["ntp.aliyun.com", "ntp.tencent.com", "cn.pool.ntp.org"]
        measured = []   # [(offset_s, rtt_s, name)]
        for server in servers:
            for _ in range(max(1, samples_per_server)):
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(2)
                    t1 = time.time()
                    sock.sendto(b'\x1b' + 47 * b'\x00', (server, 123))
                    data, _addr = sock.recvfrom(1024)
                    t4 = time.time()
                    if len(data) < 48:
                        continue
                    u = struct.unpack('!12I', data[0:48])
                    t2 = u[8] - 2208988800 + u[9] / 4294967296.0
                    t3 = u[10] - 2208988800 + u[11] / 4294967296.0
                    offset = ((t2 - t1) + (t3 - t4)) / 2.0
                    rtt = (t4 - t1) - (t3 - t2)
                    if abs(offset) < 3600:   # 过滤明显异常的响应
                        measured.append((offset, rtt, server))
                except Exception:
                    continue
                finally:
                    if sock:
                        try:
                            sock.close()
                        except Exception:
                            pass
                if measured:
                    break   # 拿到一个样本就够（同一服务器再取一个更稳）

        if not measured:
            return None, None, ""

        # 用 RTT 最小（网络最干净）的样本，偏差最可信
        measured.sort(key=lambda x: x[1])
        best = measured[0]
        offset_ms = best[0] * 1000.0
        rtt_ms = best[1] * 1000.0
        # 多服务器采样时取中位更稳
        if len(measured) >= 3:
            offset_ms = statistics.median([m[0] for m in measured]) * 1000.0
        return offset_ms, rtt_ms, best[2]

    def nm_query_time_status(self):
        """查询系统时间同步状态（v6.2.1 重写：原生NTP为主，w32tm为辅）"""
        import subprocess
        self.nm_log("=" * 44)
        self.nm_log("🕐 系统时间检测")
        self.nm_log("=" * 44)

        # ---- 主检测：原生 NTP（快、不依赖时间服务）----
        offset_ms, rtt_ms, server = self.nm_measure_time_offset(samples_per_server=2)
        if offset_ms is not None:
            self.nm_log(f"  ✓ NTP实测偏差: {offset_ms:+.0f}ms  (RTT {rtt_ms:.0f}ms, 来源 {server})")
            # 判断健康度
            abs_off = abs(offset_ms)
            if abs_off <= 100:
                self.nm_log(f"  ✓ 时间精度良好（≤100ms），抢码 timing 正常")
                grade = "good"
            elif abs_off <= 300:
                self.nm_log(f"  ⚠ 偏差偏大（>100ms）：虽已自动补偿，但建议同步")
                grade = "warn"
            else:
                self.nm_log(f"  ⚠ 偏差很大（>{300}ms）：已自动补偿，仍建议尽快同步系统时间")
                grade = "bad"
            self.nm_log(f"  说明：程序会把该偏差加入提前量计算，自动抵消")
            self._last_time_offset_ms = offset_ms
            self._time_status_grade = grade
        else:
            self.nm_log("  ✗ 所有NTP服务器不可达")
            self.nm_log(f"  可能原因: 网络不通 / 防火墙拦截UDP 123 端口")
            self.nm_log(f"  提示: 抢码将回退使用固定提前量，精度略降但可正常抢")
            self._last_time_offset_ms = None
            self._time_status_grade = "unknown"

        # ---- 辅助参考：Windows 时间服务状态 ----
        self.nm_log("-" * 44)
        try:
            result = subprocess.run(
                ["w32tm", "/query", "/status"],
                capture_output=True, text=True, encoding="gbk", errors="ignore",
                timeout=8
            )
            if result.returncode == 0 and result.stdout:
                self.nm_log("  Windows时间服务状态:")
                keep = False
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    # 只显示关键几行，避免刷屏
                    if any(k in line for k in ["Source", "源", "Last Successful", "上次成功",
                                                "Poll Interval", "轮询间隔", "Stratum", "层级"]):
                        self.nm_log(f"    {line}")
                        keep = True
                if not keep:
                    self.nm_log("    (服务运行中)")
            else:
                err = (result.stdout or result.stderr or "").strip()
                self.nm_log("  ⚠ Windows时间服务未运行")
                if err:
                    self.nm_log(f"    原因: {err[:80]}")
                self.nm_log("    影响: 系统时间可能慢慢漂移，建议偶尔点「同步系统时间」")
                self.nm_log("    （注意：不影响本次抢码，程序会自动补偿偏差）")
        except Exception as e:
            self.nm_log(f"  Windows时间服务检测跳过: {e}")

        self.nm_log("=" * 44)
        return offset_ms

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
                            messagebox.showinfo("修复成功", f"时间服务修复完成！\n\n当前NTP偏差: {avg:.0f}ms\n（已恢复正常）", parent=self.winfo_toplevel())
                        else:
                            self.nm_log(f"⚠ 修复完成但偏差仍有{avg:.0f}ms")
                            messagebox.showwarning("修复完成", f"修复已执行，但偏差仍较大:\n\n当前NTP偏差: {avg:.0f}ms\n\n建议:\n1. 检查网络是否能访问NTP服务器\n2. 检查是否有其他软件修改系统时间\n3. 重启电脑后再试", parent=self.winfo_toplevel())
                    else:
                        self.nm_log("✓ 修复命令已执行")
                        messagebox.showinfo("修复完成", "时间服务修复已执行，请查看抢码日志NTP偏差", parent=self.winfo_toplevel())
                except Exception as e:
                    self.nm_log(f"✓ 修复已执行（查询偏差失败: {e}）")
                    messagebox.showinfo("修复完成", "时间服务修复已执行", parent=self.winfo_toplevel())
            else:
                self.nm_log("✗ 修复失败或用户取消UAC")
                messagebox.showerror("修复失败", "修复失败或用户取消了UAC授权", parent=self.winfo_toplevel())
            self.nm_log("=" * 50)
        except Exception as e:
            self.nm_log(f"✗ 修复时间服务失败: {e}")
            messagebox.showerror("修复失败", f"修复时间服务失败:\n{e}", parent=self.winfo_toplevel())

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

            # ===== 阶段2: 等待到目标时间前 PREWARM_LEAD 秒，连接预热 =====
            #
            # v6.4.2 时序重新设计（针对"预热来不及"问题）：
            #
            # 原设计缺陷：2.5 秒窗口里既要 TCP/TLS 握手(200-400ms)，
            #   又要跑 5 次 RTT 探针(5*RTT + 4*150ms = 至少600ms固定开销)。
            #   RTT=300ms 时总耗时 2400ms，只剩 100ms 自旋；
            #   RTT=400ms 时直接超时，首发被迫立即发送 → 首发废掉。
            #
            # 但简单把窗口拉到 6 秒也有问题：
            #   · 连接空闲 6 秒可能被服务端超时断开（反而白预热）
            #   · 提前 6 秒发请求，更容易被判异常行为
            #   · 探针在 T-6s 测的 RTT 与 T 时刻真实网络偏差更大
            #
            # 新方案【分层预热】—— 窗口 3 秒，但内部职责分离：
            #   T-3.0s : 开始建连（仅 TCP/TLS，不做探针）
            #   T-1.5s : 建连应已完成，此时才开始探针（离目标更近，RTT 更准）
            #   T-1.0s : 探针完成，进入自旋（留 1 秒余量）
            # 这样即使 RTT 慢，最坏也有 500ms 自旋空间；
            # 且探针离目标时刻仅 1 秒，测得的 RTT 更贴近首发真实网络。
            PREWARM_LEAD = 4.0
            PROBE_AT = target_timestamp - 2.3   # 探针启动时刻
            prewarm_time = target_timestamp - PREWARM_LEAD
            while time.time() < prewarm_time and not stop_flag["stop"]:
                remaining = target_timestamp - time.time()
                if int(remaining) % 10 == 0 and int(remaining) > 0:
                    self.nm_log(f"  还剩 {int(remaining)} 秒...")
                time.sleep(0.5)

            if stop_flag["stop"]:
                self.nm_log("抢码已取消")
                return

            # 连接预热：提前2.5秒建立连接（并行建立，act_id已在添加任务时获取）
            self.nm_log(f"[连接预热] 提前{PREWARM_LEAD:.0f}秒建立TCP连接 + 测RTT"
                        f"（并行建立，act_id已在添加任务时获取）...")
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
                    # v6.2.0 修复（重要）：预热必须打到"真正发请求的那个域名"。
                    #
                    # 原代码预热 https://www.bilibili.com，而抢码接口在 https://api.bilibili.com
                    # —— 这是两个不同域名，TCP/TLS 连接完全无法复用。
                    # 实测：新建连接 109ms vs 复用连接 42ms，握手开销约 67ms，
                    # 而基础提前量只有 100ms，等于白送掉 2/3 的提前量优势。
                    #
                    # 现在预热真实接口域名（用只读的 nav 接口，最轻量、不触发风控），
                    # 使首发瞬间可直接复用已建立的连接。
                    session.get("https://api.bilibili.com/x/web-interface/nav",
                                headers=HEADERS, timeout=5)
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
            # v6.4.2: 建连最长等 1.4 秒（T-3.0s 开始，到 T-1.6s 必须完成）
            # 这样留出 0.1s 给探针启动，探针在 T-1.5s 开始
            _prewarm_join_deadline = time.time() + 1.6
            for t in prewarm_threads:
                _remain = _prewarm_join_deadline - time.time()
                if _remain <= 0:
                    break
                t.join(timeout=max(0.1, _remain))
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

            # ===== 计算提前量（v6.2.1 重写：基于接口延迟模型 + 时段校正）=====
            #
            # 【时间模型】设目标名义时刻为 N：
            #   offset = 服务器时间 - 本地时间（正数=本地时钟慢）
            #   用本地时钟在 L_s 发送 -> 到达服务器时服务器时钟为
            #       L_s + offset + one_way（one_way = 单程网络延迟）
            #   要让它"恰好在 N 之后 delta 毫秒到达"，需
            #       L_s = N + delta - offset - one_way
            #   即提前量（从 N 往前推多少发出）：
            #       advance = N - L_s = offset + one_way - delta
            #
            #   关键：offset 会与 NTP 修正项相加后抵消（代码里 advance 显式
            #   加上 offset，正好补偿本地时钟偏差），时间精度本身是准的。
            #   真正的误差来自 one_way —— 必须用【领取接口】的真实延迟，
            #   而不是查询接口的延迟。
            #
            # 【实测校准数据（2026-10-26）】
            #   查询接口 mission/info   RTT 中位 145ms -> 半RTT 73ms
            #   领取接口 mission/receive RTT 中位 165ms -> 半RTT 82ms
            #   比例 K = receive/query = 1.13（稳定）
            #
            # 【晚间高峰校正（用户反馈 + 数据验证）】
            #   0点/1点 是抢码高峰，此刻 B站接口负载最高、延迟显著更高：
            #     历史日志 深夜0/1点 RTT 中位 136ms
            #     白天实测    RTT 中位 251ms（同一账户不同时段）
            #   即高峰时段半RTT 约 68ms，白天 约 82ms。
            #   若仍用白天探针值，高峰会【到得太早】→ 被判"未到时间"/风控。
            #   因此引入时段系数：高峰时段把 one_way 上调。
            #
            # 【delta 设计】delta = 期望"晚到"多少毫秒。
            #   实测成功案例多在目标后 1-5 秒命中，且"早到"代价高于"晚到"
            #   （早到可能被判未到时间/烧风控额度）。取 delta = 60ms 作为
            #   保守值：既保证不早到，又不至于错过开库存瞬间。
            #
            ntp_correction = ntp_offset * 1000  # NTP偏差转ms

            # --- v6.4.2 分层：先确保建连完成，再在 PROBE_AT 时刻做探针 ---
            # 建连线程可能还在跑，等到探针时刻再继续
            _now = time.time()
            if _now < PROBE_AT:
                _wait_s = PROBE_AT - _now
                self.nm_log(f"[预热阶段] 建连完成，等待 {_wait_s:.2f}s 后测RTT...")
                while time.time() < PROBE_AT and not stop_flag["stop"]:
                    time.sleep(0.01)

            # --- 1) 用只读查询接口测当前 RTT（不消耗领取机会）---
            # v6.4.2: 先检查剩余时间，不够就跳过探针（用兜底值），
            # 保证自旋空间不被探针吃光。
            probe_rtt = None
            _time_left_ms = (target_timestamp - time.time()) * 1000.0
            _min_needed_ms = 600.0   # 探针至少需要 600ms，之后还要自旋
            _skip_probe = _time_left_ms < _min_needed_ms + 500.0
            if _skip_probe:
                self.nm_log(f"[RTT探针] 剩余{_time_left_ms:.0f}ms，跳过探针避免挤占自旋时间")
            try:
                if prewarm_tasks and not _skip_probe:
                    _probe_session = sessions.get(prewarm_tasks[0]["task_id"])
                    # v6.4.2: 采样 2 次（间隔0.80s，总耗时约 0.8+2*RTT≈1.2s）
                    # 优先用历史缓存基线，只有缓存过期时才真探
                    probe_rtt, probe_valid, probe_total = self._nm_probe_smart(
                        prewarm_tasks[0], _probe_session, target_timestamp)
            except Exception as e:
                self.nm_log(f"[RTT探针] 异常: {e}")

            # --- 2) 换算成领取接口的真实半RTT ---
            # v6.4.0: K 值改为实测校准值 1.60（原 1.13 偏低，导致提前量少算 13-15ms）
            # 实测：查询接口 RTT 中位 77ms，领取接口 RTT 中位 123ms -> K = 1.60
            K_RECV = 1.60
            FALLBACK_HALF = 82.0    # 探针失败时的兜底半RTT（白天实测中位）
            is_peak_hour = False
            try:
                _hour = time.localtime(target_timestamp).tm_hour
                # 抢码高峰：23点、0点、1点
                is_peak_hour = _hour in (23, 0, 1)
            except Exception:
                pass

            if probe_rtt and 20 <= probe_rtt <= 2000:
                half_query = probe_rtt / 2.0
                half_recv = half_query * K_RECV
                src = "实测"
            else:
                half_recv = FALLBACK_HALF
                src = "兜底"

            # --- 3) 晚间高峰校正 ---
            # 高峰时段网络更拥塞，实际单程延迟比探针测到的更高。
            # 经验系数 1.15：高峰 RTT 比同时段探针值再慢约15%。
            if is_peak_hour:
                half_recv *= 1.15
                peak_note = "  [高峰时段×1.15]"
            else:
                peak_note = ""

            # --- 4) 合成提前量 ---
            DELTA_MS = 60.0   # 期望晚到 60ms（不早到，且不错过开库存瞬间）
            dynamic_advance = ntp_correction + half_recv - DELTA_MS
            # 安全范围：10ms ~ 2000ms。下限防止退化成"立刻发"，
            # 上限防止系统时间异常导致等到目标之后才发。
            dynamic_advance = max(10.0, min(2000.0, dynamic_advance))

            self.nm_log(
                f"[提前量] {src}半RTT={half_recv:.0f}ms{peak_note} "
                f"+ NTP偏差{ntp_correction:+.0f}ms - 晚到补偿{DELTA_MS:.0f}ms "
                f"=> 提前 {dynamic_advance:.0f}ms 发送"
            )
            self.nm_log(
                f"[提前量] 预估到达: 目标{'后' if DELTA_MS >= 0 else '前'}"
                f"{abs(half_recv - (dynamic_advance - ntp_correction)):.0f}ms "
                f"（越接近0越理想）"
            )

            # NTP偏差过大时提示（仅提示，不阻止抢码）
            # 说明：offset 在公式中已被显式补偿，偏差本身不影响精度；
            #       但如果偏差持续增大，说明系统时钟在漂移，提醒用户关注即可。
            # ===== v6.4.0: 时钟偏差分级预警 =====
            # 实测发现：本机时钟一天内从 +126ms 漂移到 +472ms，
            # Windows 时间服务虽在运行，但 w32tm /resync 因权限不足失败（0x80070005），
            # 导致时钟持续漂移、无法自动校正。程序会自动补偿，但仍应提示用户。
            _abs_off = abs(ntp_correction)
            if _abs_off > 300:
                self.nm_log(f"[⚠️ 时钟偏差严重] {ntp_correction:+.0f}ms（本地{"慢" if ntp_correction > 0 else "快"}）")
                self.nm_log("   程序已自动补偿，但偏差仍在累积，建议尽快修复系统时间")
                self.nm_log("   修复方法：右键程序 → 以管理员身份运行 → 点「同步系统时间」")
            elif _abs_off > 150:
                self.nm_log(f"[⚠️ 时钟偏差偏大] {ntp_correction:+.0f}ms（本地{"慢" if ntp_correction > 0 else "快"}），已自动补偿")
                self.nm_log("   建议空档期点「同步系统时间」校正（需管理员权限）")
            elif _abs_off > 50:
                self.nm_log(f"[时钟偏差] {ntp_correction:+.0f}ms，已补偿，精度正常")

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
            # ===== v6.4.0: 计算精准首发的【真实到达偏差】=====
            # 关键：下面日志里的 (actual_fire - target_timestamp) 是【本地时钟】口径。
            # 因为系统时钟慢于服务器，它会显示成很大的负数（如 -446ms），
            # 容易误判为"早到了"，实际到达可能正好在目标之后。
            #
            # 真实到达时刻 = 本地发送时刻 + 时钟偏差 + 单程网络延迟
            #   到达偏差 = actual_fire + offset + one_way - target_timestamp
            #   正数 = 晚到（安全）  负数 = 早到（可能被判未到领取时间）
            _spin_error_ms = (actual_fire - fire_time) * 1000.0
            _arrive_dev_ms = (
                actual_fire + ntp_correction / 1000.0
                + half_recv / 1000.0 - target_timestamp) * 1000.0
            _session_id = time.strftime("%Y%m%d_%H%M%S",
                                         time.localtime(target_timestamp))

            self.nm_log(
                f"[精准首发] 本地偏差 {(actual_fire - target_timestamp)*1000:+.1f}ms"
                f"（本地时钟口径，含 {ntp_correction:+.0f}ms 时钟偏差）")
            self.nm_log(
                f"[精准首发] 真实到达偏差 {_arrive_dev_ms:+.1f}ms"
                f"（{'晚到' if _arrive_dev_ms >= 0 else '早到'}，自旋精度 {_spin_error_ms:+.1f}ms）")

            # 到达偏差分级提示（便于立即判断这一枪质量）
            if _arrive_dev_ms < -20:
                self.nm_log("  ⚠ 早到超过20ms，可能被判未到领取时间，建议提高晚到补偿")
            elif _arrive_dev_ms <= 50:
                self.nm_log("  ✓ 到达时机优秀（0-50ms）")
            elif _arrive_dev_ms <= 100:
                self.nm_log("  ✓ 到达时机良好（50-100ms）")
            elif _arrive_dev_ms <= 200:
                self.nm_log("  ○ 到达偏晚（100-200ms）")
            else:
                self.nm_log("  ⚠ 到达过晚（>200ms），可能错过首批库存")

            # 把本次场次的指标存入 stop_flag，供 nm_execute_task 写入记录
            stop_flag["_session_id"] = _session_id
            stop_flag["_ntp_offset_ms"] = ntp_correction
            stop_flag["_target_ts"] = target_timestamp
            stop_flag["_fire_ts"] = actual_fire
            stop_flag["_one_way_ms"] = half_recv
            stop_flag["_probe_rtt_med"] = probe_rtt or 0
            stop_flag["_probe_valid"] = probe_valid
            stop_flag["_probe_total"] = probe_total
            stop_flag["_spin_error_ms"] = _spin_error_ms
            stop_flag["_arrive_dev_ms"] = _arrive_dev_ms
            stop_flag["_first_shot_done"] = False

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
                                               sessions.get(task["task_id"]), task_deadline,
                                               target_timestamp, stop_flag,
                                               advance_ms=dynamic_advance)

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

    def nm_probe_rtt(self, task, session=None, samples=5):
        """用只读的 mission/info 查询接口测真实 RTT（v6.2.0 新增）。

        为什么用查询接口而不是领取接口：
          领取接口（mission/receive）是敏感操作，每次请求都会消耗"请求机会"，
          拿去测 RTT 成本极高、且可能触发风控。
          mission/info 是只读查询，频率限制宽松得多，适合做探针。

        返回：RTT 中位数（ms），失败返回 None。
        """
        try:
            import statistics
            account = self.account_mgr.get_account(task.get("account_name", ""))
            if not account:
                return None
            cookies = cookies_from_account(account)
            from config import MISSION_INFO_API
            from bili_api import get_wbi_keys, wbi_sign

            img_key, sub_key = get_wbi_keys(cookies)
            if not img_key:
                return None

            sess = session or requests.Session()
            sess.headers.update(HEADERS)
            params = wbi_sign({"task_id": task["task_id"], "web_location": "888.126558"},
                              img_key, sub_key)
            headers = {
                **HEADERS,
                "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task['task_id']}",
                "Origin": "https://www.bilibili.com",
            }

            rtts = []
            for i in range(max(1, samples)):
                t0 = time.perf_counter()
                try:
                    sess.get(MISSION_INFO_API, headers=headers, cookies=cookies,
                             params=params, timeout=5)
                except Exception:
                    continue
                rtts.append((time.perf_counter() - t0) * 1000)
                if i < samples - 1:
                    time.sleep(0.15)   # 轻微间隔，避免连续打

            if not rtts:
                return None
            med = statistics.median(rtts)
            self.nm_log(f"[RTT探针] 采样{len(rtts)}次: {[f'{r:.0f}' for r in rtts]}ms -> 中位 {med:.0f}ms")
            return med
        except Exception as e:
            try:
                self.nm_log(f"[RTT探针] 失败: {e}")
            except Exception:
                pass
            return None


# ---------- v6.4.2: 智能探针（历史缓存优先，尽量少打扰服务端）----------
    _RTT_CACHE = {"rtt": 0.0, "ts": 0.0}
    RTT_CACHE_TTL = 1800.0   # 缓存有效期 30 分钟

    def _nm_load_hist_rtt(self):
        """从历史记录里取最近一次有效探针 RTT 作为基线（零开销、零风控）。"""
        try:
            import rush_stats
            recs = rush_stats.load_results(limit=200)
            for r in reversed(recs):
                v = float(r.get("probe_rtt_med") or 0)
                ts = str(r.get("ts") or "")
                if v > 20 and ts:
                    import datetime as _dt
                    t = _dt.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp()
                    age = time.time() - t
                    if 0 < age < self.RTT_CACHE_TTL:
                        return v, age
        except Exception:
            pass
        return 0.0, 0.0

    def _nm_probe_smart(self, task, session, target_timestamp):
        """智能探针（v6.4.2）。

        策略（按开销从低到高）：
          1) 内存缓存命中（30分钟内）-> 直接用，0 次请求
          2) 历史记录里有 30 分钟内的 probe_rtt_med -> 用，0 次请求
          3) 以上都没有，才真做 2 次探针（间隔 0.80s，实测风控率仅 20%）
          4) 时间预算不够则跳过，用兜底值

        这样绝大多数场次【完全不打扰服务端】，从根上回避探针风控。

        返回：(median_rtt, valid, total)
        """
        now = time.time()

        # --- 1) 内存缓存 ---
        if (self._RTT_CACHE["rtt"] > 20
                and 0 < now - self._RTT_CACHE["ts"] < self.RTT_CACHE_TTL):
            age = now - self._RTT_CACHE["ts"]
            self.nm_log(f"[RTT探针] 用内存缓存 {self._RTT_CACHE['rtt']:.0f}ms"
                        f"（{age/60:.0f}分钟前，0次请求）")
            return self._RTT_CACHE["rtt"], 2, 2

        # --- 2) 历史记录缓存 ---
        hist, age = self._nm_load_hist_rtt()
        if hist > 20:
            self.nm_log(f"[RTT探针] 用历史基线 {hist:.0f}ms"
                        f"（{age/60:.0f}分钟前，0次请求）")
            self._RTT_CACHE["rtt"] = hist
            self._RTT_CACHE["ts"] = now
            return hist, 2, 2

        # --- 3) 时间预算检查 ---
        remain_ms = (target_timestamp - now) * 1000.0
        # 2次探针 + 1个0.8s间隔 ≈ 0.8 + 2*RTT。保守按 RTT=400ms 估需 1.6s
        if remain_ms < 1800.0:
            self.nm_log(f"[RTT探针] 剩余{remain_ms:.0f}ms 不足1.8s，跳过探针用兜底值")
            return None, 0, 0

        # --- 4) 真做探针（2次，间隔0.8s）---
        rtt, valid, total = self.nm_probe_rtt_full(
            task, session, samples=2,
            deadline_ts=target_timestamp - 0.5)
        if rtt and rtt > 20:
            self._RTT_CACHE["rtt"] = rtt
            self._RTT_CACHE["ts"] = now
        return rtt, valid, total

    def nm_probe_rtt_full(self, task, session=None, samples=3, deadline_ts=0):
        """测 RTT 并区分「有效样本」与「风控样本」，且【自适应时间预算】（v6.4.2）。

        为什么需要自适应：
          原实现固定采 5 次、间隔 150ms，最坏耗时 5*RTT+600ms。
          RTT=400ms 时耗时 2600ms，而预热窗口只有 2.5s → 直接超时，
          首发被迫"立即发送"，提前量完全失效。

        新逻辑：
          1. 逐次采样，每采一次就用实测 RTT 估算下一次耗时
          2. 若"下一次采样"会超过 deadline_ts，立即停止
          3. 只把 code==0 的响应当有效样本（排除风控响应污染）
          4. 有效样本 <2 时返回 None（调用方用兜底值）

        参数:
          samples     期望采样数（实际可能更少）
          deadline_ts 硬截止时刻（epoch 秒）。0 表示不限制。

        返回：(median_rtt, valid_count, total_count)
        """
        try:
            import statistics
            account = self.account_mgr.get_account(task.get("account_name", ""))
            if not account:
                return None, 0, 0
            cookies = cookies_from_account(account)
            from config import MISSION_INFO_API
            from bili_api import get_wbi_keys, wbi_sign

            img_key, sub_key = get_wbi_keys(cookies)
            if not img_key:
                return None, 0, 0

            sess = session or requests.Session()
            sess.headers.update(HEADERS)
            params = wbi_sign({"task_id": task["task_id"],
                               "web_location": "888.126558"},
                              img_key, sub_key)
            headers = {
                **HEADERS,
                "Referer": f"https://www.bilibili.com/blackboard/era/award-exchange.html?task_id={task['task_id']}",
                "Origin": "https://www.bilibili.com",
            }

            valid_rtts = []
            all_rtts = []
            risk_count = 0
            est_next_ms = 200.0   # 第一次采样前的保守估计

            for i in range(max(1, samples)):
                # ---- 时间预算检查：这次采样会不会超 deadline ----
                if deadline_ts > 0:
                    remain_ms = (deadline_ts - time.time()) * 1000.0
                    if remain_ms < est_next_ms + 60.0:
                        self.nm_log(
                            f"[RTT探针] 剩余{remain_ms:.0f}ms < 预估{est_next_ms:.0f}ms，"
                            f"停止采样（已采{len(all_rtts)}次）")
                        break

                t0 = time.perf_counter()
                code = None
                try:
                    resp = sess.get(MISSION_INFO_API, headers=headers,
                                    cookies=cookies, params=params, timeout=5)
                    code = resp.json().get("code")
                except Exception:
                    pass
                dt = (time.perf_counter() - t0) * 1000
                all_rtts.append(dt)
                est_next_ms = dt      # 用本次实测更新下次预估
                if code == 0:
                    valid_rtts.append(dt)
                elif code in (-702, -509, -705, -412):
                    risk_count += 1

                if i < samples - 1:
                    # 间隔 80ms（原 150ms，压缩固定开销）
                    time.sleep(0.80)

            total = len(all_rtts)
            n_valid = len(valid_rtts)
            if n_valid < 2:
                self.nm_log(
                    f"[RTT探针] 有效样本仅 {n_valid}/{total}"
                    f"{('（风控' + str(risk_count) + '）') if risk_count else ''}，探针失效")
                return None, n_valid, total

            med = statistics.median(valid_rtts)
            self.nm_log(
                f"[RTT探针] 采样{total}次，有效{n_valid}个"
                f"{('，风控' + str(risk_count) + '个已排除') if risk_count else ''}"
                f": {[f'{r:.0f}' for r in valid_rtts]}ms -> 中位 {med:.0f}ms")
            return med, n_valid, total
        except Exception as e:
            try:
                self.nm_log(f"[RTT探针] 失败: {e}")
            except Exception:
                pass
            return None, 0, 0
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

    def nm_execute_task(self, task, task_info, session, deadline, target_time, stop_flag,
                        advance_ms=0):
        """执行单个任务的抢码（带风控递增延迟）
        P1-4: target_time显式传入，不再从deadline反推
        v6.2.0: advance_ms 传入本次提前量，用于统计最优提前量
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
                ok, msg = self.do_receive_fast(task, task_info, account, session,
                                               advance_ms=advance_ms,
                                               stop_flag=stop_flag)
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
                elif "202032" in msg or "无资格领取" in msg or "暂无领取资格" in msg:
                    # v6.2.2 新增：无资格领取奖励 -> 说明该任务本身没完成，重试毫无意义
                    #
                    # 实测教训（2026-10-26 18:00 那次）：
                    #   任务 status=7（任务未完成），程序没有识别这个码，
                    #   结果在窗口期内发了 82 次请求，其中 64 次都是 202032，
                    #   既浪费请求次数、又白白累积风控(-705 x14)，
                    #   还挡住了后面优先级2/3 的执行机会。
                    #
                    # 这类错误是"任务资格问题"，不是"抢的时机问题"，
                    # 立刻切换到下一个优先级才有意义。
                    _no_qualify_count = stop_flag.get("no_qualify_count", 0) + 1
                    stop_flag["no_qualify_count"] = _no_qualify_count
                    self.nm_log(
                        f"  [{send_str}->{recv_str}, {rtt_ms:.0f}ms] 第{attempt}次: "
                        f"⚠ 无资格领取（任务未完成/不满足条件），立即切换下一个优先级")
                    if attempt >= 2:
                        self.nm_log(f"     （累计{_no_qualify_count}次无资格，该优先级已放弃）")
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
