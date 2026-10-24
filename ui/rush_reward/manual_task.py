# -*- coding: utf-8 -*-
"""手动添加抢码任务（ManualTaskMixin）。

支持两种来源输入：纯 task_id、活动网址（含 ?task_id=xxx），可多行批量。
解析后可选择：
  1) 归类到某个「版本 / 期数 / 类型」——可选用已有版本（如 鸣潮3.7），也可直接
     输入新版本名自动新建，从而让手动任务和官方任务混排在同一个下拉框里；
  2) 直接加入精准抢码的「任务组」——可选已有组，也可输入新组名自动新建。

数据持久化在 data/manual_tasks.json（原子写），启动时并入 ALL_TASKS。
"""

import re
import time
import threading
import tkinter as tk
from tkinter import ttk

from config import COLORS
from tasks_config import (ALL_TASKS, MANUAL_TASKS, MANUAL_VERSION, MANUAL_PERIOD,
                          MANUAL_TYPE, add_manual_task, remove_manual_task)
from bili_api import cookies_from_account, get_mission_info

# task_id=xxx / &task_id=xxx / "task_id": "xxx" / task_id:xxx 均能匹配
_PARAM_RE = re.compile(r"task_id[\"']?\s*[=:]\s*[\"']?([0-9A-Za-z]{8,40})", re.I)
_BARE_RE = re.compile(r"^[0-9A-Za-z]{8,40}$")
_BAD_TOKENS = {"taskid", "taskids", "activitid", "activityid", "actid"}


def parse_task_ids(text):
    """从任意文本里提取 task_id 列表（多行批量、完整网址、纯 id 均可）。"""
    ids = []
    seen = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        found = list(_PARAM_RE.findall(line))
        if not found:
            for token in re.split(r"[\s,，;；、]+", line):
                token = token.strip().strip("\"'")
                if _BARE_RE.match(token) and token.lower() not in _BAD_TOKENS:
                    found.append(token)
        for tid in found:
            if tid.lower() in _BAD_TOKENS:
                continue
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
    return ids


def task_label(task, style="arrow"):
    """任务在下拉框中的显示文本；奖励为空时不显示空括号。"""
    name = (task.get("name") or "").strip()
    award = (task.get("award") or "").strip()
    if not award:
        return name
    return f"{name} => {award}" if style == "arrow" else f"{name} ({award})"


def available_versions():
    """ALL_TASKS 中的版本列表（按出现顺序，含「手动任务」）。"""
    versions = []
    for t in ALL_TASKS:
        v = t.get("version", "")
        if v and v not in versions:
            versions.append(v)
    return versions


def available_periods(version):
    out = []
    for t in ALL_TASKS:
        if t.get("version") == version and t.get("period") and t["period"] not in out:
            out.append(t["period"])
    return out


def available_types(version, period):
    out = []
    for t in ALL_TASKS:
        if t.get("version") == version and t.get("period") == period and t.get("type") and t["type"] not in out:
            out.append(t["type"])
    return out


def extract_task_meta(info, task_id, act_id_fallback=""):
    """从 mission/info 返回的 data 中提取手动任务需要的字段。"""
    info = info or {}

    def _pick(container, keys):
        if not isinstance(container, dict):
            return ""
        for k in keys:
            v = container.get(k)
            if v:
                return str(v)
        return ""

    act_id = (_pick(info, ["act_id", "activity_id", "ActivityId"])
              or _pick(info.get("act_info"), ["act_id", "activity_id"])
              or (act_id_fallback or ""))
    act_name = (_pick(info, ["act_name", "activity_name", "ActivityName"])
                or _pick(info.get("act_info"), ["act_name", "activity_name"]))
    task_name = _pick(info, ["task_name", "TaskName", "title", "name"])
    award = (_pick(info.get("reward_info"), ["award_name", "reward_name", "name"])
             or _pick(info.get("stock_info"), ["award_name", "reward_name"])
             or _pick(info, ["award_name", "reward_name"]))
    return {
        "task_id": task_id,
        "name": task_name or task_id,
        "award": award,
        "act_id": act_id,
        "act_name": act_name,
        "status": info.get("status"),
        "message": _pick(info, ["message", "status_text"]),
    }


class ManualTaskMixin:
    """手动任务子系统。宿主须提供 account_mgr / rush_groups / after() / log()。"""

    # ---------------- 下拉框 / 版本刷新 ----------------

    def mt_refresh_task_combos(self):
        """把手动任务可能带来的新版本重新灌进两套版本下拉框。"""
        versions = available_versions()
        for combo_name in ("version_combo", "nm_version_combo"):
            combo = getattr(self, combo_name, None)
            if combo is None:
                continue
            try:
                combo.config(values=versions)
            except Exception:
                pass

    def mt_select_manual_version(self):
        """把两套版本下拉框切到「手动任务」并刷新联动。"""
        for var_name, handler_name in (("version_var", "on_version_change"),
                                       ("nm_version_var", "nm_on_version_change")):
            var = getattr(self, var_name, None)
            handler = getattr(self, handler_name, None)
            if var is None or handler is None:
                continue
            try:
                var.set(MANUAL_VERSION)
                handler()
            except Exception:
                pass

    # ---------------- 任务组 ----------------

    def mt_ensure_group(self, group_name):
        """按名字取任务组，不存在则自动新建。返回 (group, created)。"""
        name = (group_name or "").strip()
        if not name:
            return None, False
        groups = getattr(self, "rush_groups", None)
        if groups is None:
            return None, False
        for g in groups:
            if g.get("group_name") == name:
                return g, False
        group = {
            "group_id": f"group_{int(time.time() * 1000)}",
            "group_name": name,
            "target_time": "00:00:00.000",
            "tasks": [],
        }
        groups.append(group)
        self._mt_save_groups()
        return group, True

    def _mt_save_groups(self):
        saver = getattr(self, "save_rush_groups", None)
        if saver:
            try:
                saver()
            except Exception:
                pass

    def mt_add_task_to_group(self, entry, group_name, account_name):
        """把手动任务加入（或新建）精准抢码任务组。返回 (group, created, msg)。"""
        group, created = self.mt_ensure_group(group_name)
        if group is None:
            return None, False, "未指定任务组"
        if any(t.get("task_id") == entry.get("task_id") for t in group.get("tasks", [])):
            return group, created, "该任务已在组内"

        try:
            window_seconds = int(self.nm_window_entry.get())
        except Exception:
            window_seconds = 15
        try:
            base_interval = int(self.nm_base_interval_entry.get()) / 1000.0
            base_interval = max(0.3, min(2.0, base_interval))
        except Exception:
            base_interval = 0.9

        tasks = group.setdefault("tasks", [])
        priorities = [t.get("priority", 0) for t in tasks]
        priority = (max(priorities) + 1) if priorities else 1
        tasks.append({
            "task_id": entry["task_id"],
            "name": entry.get("name") or entry["task_id"],
            "award": entry.get("award") or "",
            "period": entry.get("period") or MANUAL_PERIOD,
            "type": entry.get("type") or MANUAL_TYPE,
            "version": entry.get("version") or MANUAL_VERSION,
            "account_name": account_name or "",
            "priority": priority,
            "window_seconds": window_seconds,
            "base_interval": base_interval,
            "act_id": entry.get("act_id") or "",
            "status_color": "gray",
            "status_text": "查询中...",
            "task_finished": None,
            "stock_available": None,
        })
        self._mt_save_groups()
        return group, created, f"已加入任务组（优先级{priority}）"

    def _mt_refresh_after_group_change(self):
        """任务组变化后的界面刷新（须在主线程调用）。"""
        for fn in ("refresh_new_mode_group_list", "refresh_new_mode_task_list", "nm_update_scheduler"):
            f = getattr(self, fn, None)
            if f is None:
                continue
            try:
                f()
            except Exception:
                pass

    # ---------------- 对话框 ----------------

    def mt_open_add_dialog(self):
        existing = getattr(self, "_mt_dialog", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except Exception:
            pass

        dlg = tk.Toplevel(self)
        self._mt_dialog = dlg
        dlg.title("手动添加抢码任务")
        dlg.configure(bg=COLORS["bg_dark"])
        dlg.resizable(True, True)
        try:
            dlg.transient(self.winfo_toplevel())
        except Exception:
            pass

        font_lbl = ("微软雅黑", 10)
        font_btn = ("微软雅黑", 10, "bold")
        font_input = ("微软雅黑", 10)

        # ===== 可滚动容器：保证任何 DPI 下都不会"显示不完全" =====
        outer = tk.Frame(dlg, bg=COLORS["bg_dark"])
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, bg=COLORS["bg_dark"], highlightthickness=0, bd=0)
        vbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        body = tk.Frame(canvas, bg=COLORS["bg_dark"])
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(body_id, width=e.width))

        def _wheel(event):
            try:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _wheel)
        dlg.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # ---- ① 输入 ----
        card1 = tk.Frame(body, bg=COLORS["bg_card"])
        card1.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(card1, text="① 粘贴 task_id 或活动网址（每行一个，可批量）",
                 bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 2))
        tk.Label(card1,
                 text="例：6ERAcwloghvosw00 ｜ https://www.bilibili.com/blackboard/era/award-exchange.html?task_id=6ERAcwloghvosw00",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9),
                 justify=tk.LEFT, wraplength=700).pack(anchor=tk.W, padx=12, pady=(0, 6))
        input_text = tk.Text(card1, height=4, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                             insertbackground=COLORS["text_primary"], relief=tk.FLAT,
                             font=("Consolas", 10), wrap=tk.WORD)
        input_text.pack(fill=tk.X, padx=12, pady=(0, 10))
        input_text.focus_set()

        # ---- ② 参数 ----
        card2 = tk.Frame(body, bg=COLORS["bg_card"])
        card2.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(card2, text="② 设置", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 4))

        grid = tk.Frame(card2, bg=COLORS["bg_card"])
        grid.pack(fill=tk.X, padx=12, pady=(0, 6))
        for col in range(6):
            grid.columnconfigure(col, weight=1 if col in (1, 3, 5) else 0)

        # 行1：归类 版本/期数/类型
        tk.Label(grid, text="归类版本", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=0, sticky="w", pady=3)
        version_var = tk.StringVar(value=MANUAL_VERSION)
        version_combo = ttk.Combobox(grid, textvariable=version_var, values=available_versions(),
                                     state="normal", width=16, font=font_input)
        version_combo.grid(row=0, column=1, sticky="we", padx=(6, 12), pady=3)

        tk.Label(grid, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=2, sticky="w", pady=3)
        period_var = tk.StringVar(value=MANUAL_PERIOD)
        period_combo = ttk.Combobox(grid, textvariable=period_var, values=[MANUAL_PERIOD],
                                    state="normal", width=12, font=font_input)
        period_combo.grid(row=0, column=3, sticky="we", padx=(6, 12), pady=3)

        tk.Label(grid, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=4, sticky="w", pady=3)
        type_var = tk.StringVar(value=MANUAL_TYPE)
        type_combo = ttk.Combobox(grid, textvariable=type_var, values=[MANUAL_TYPE],
                                  state="normal", width=12, font=font_input)
        type_combo.grid(row=0, column=5, sticky="we", padx=(6, 0), pady=3)

        def _sync_period_types(_event=None):
            v = version_var.get().strip()
            ps = available_periods(v)
            period_combo.config(values=ps or [MANUAL_PERIOD])
            ts = available_types(v, period_var.get().strip())
            type_combo.config(values=ts or [MANUAL_TYPE])

        def _sync_types(_event=None):
            ts = available_types(version_var.get().strip(), period_var.get().strip())
            type_combo.config(values=ts or [MANUAL_TYPE])
        version_combo.bind("<<ComboboxSelected>>", _sync_period_types)
        period_combo.bind("<<ComboboxSelected>>", _sync_types)

        tk.Label(grid, text="（可选用已有版本，也可直接输入新版本名→自动新建）",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)
                 ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(0, 4))

        # 行2：查询账户 / act_id 兜底 / 强制添加
        tk.Label(grid, text="查询账户", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=2, column=0, sticky="w", pady=3)
        account_names = [a.get("name", "") for a in getattr(self.account_mgr, "accounts", [])]
        account_var = tk.StringVar()
        account_combo = ttk.Combobox(grid, textvariable=account_var, values=account_names,
                                     state="readonly", width=16, font=font_input)
        account_combo.grid(row=2, column=1, sticky="we", padx=(6, 12), pady=3)
        if account_names:
            account_combo.current(0)

        tk.Label(grid, text="act_id 兜底", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=2, column=2, sticky="w", pady=3)
        act_id_var = tk.StringVar()
        act_id_entry = tk.Entry(grid, textvariable=act_id_var, width=14,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                insertbackground=COLORS["text_primary"], relief=tk.FLAT,
                                font=("Consolas", 10))
        act_id_entry.grid(row=2, column=3, sticky="we", padx=(6, 12), pady=3)

        force_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grid, text="查询失败也强制添加", variable=force_var,
                       bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                       selectcolor=COLORS["bg_input"], activebackground=COLORS["bg_card"],
                       activeforeground=COLORS["text_primary"],
                       font=("微软雅黑", 9)).grid(row=2, column=4, columnspan=2, sticky="w", pady=3)

        tk.Label(grid, text="（查询账户只用来读取任务名/奖励/act_id，不会改动账号数据）",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)
                 ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(0, 4))

        # 行3：加入任务组
        tk.Label(grid, text="加入任务组", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=4, column=0, sticky="w", pady=3)
        group_names = ["（不加入）"] + [g.get("group_name", "") for g in (getattr(self, "rush_groups", []) or [])]
        group_var = tk.StringVar(value="（不加入）")
        group_combo = ttk.Combobox(grid, textvariable=group_var, values=group_names,
                                   state="readonly", width=16, font=font_input)
        group_combo.grid(row=4, column=1, sticky="we", padx=(6, 12), pady=3)

        tk.Label(grid, text="或新建组名", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=4, column=2, sticky="w", pady=3)
        new_group_var = tk.StringVar()
        new_group_entry = tk.Entry(grid, textvariable=new_group_var, width=14,
                                   bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                   insertbackground=COLORS["text_primary"], relief=tk.FLAT,
                                   font=font_input)
        new_group_entry.grid(row=4, column=3, sticky="we", padx=(6, 12), pady=3)
        tk.Label(grid, text="（填了就自动新建该组；留空则用上面的组）",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)
                 ).grid(row=4, column=4, columnspan=2, sticky="w", pady=3)

        # ---- 按钮 ----
        btn_row = tk.Frame(body, bg=COLORS["bg_dark"])
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 6))
        add_btn = tk.Button(btn_row, text="🔍 解析并添加", bg=COLORS["accent"], fg="#000000",
                            font=font_btn, relief=tk.FLAT, cursor="hand2")
        add_btn.pack(side=tk.LEFT, ipadx=14, ipady=4)
        clear_btn = tk.Button(btn_row, text="清空输入", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                              font=font_btn, relief=tk.FLAT, cursor="hand2",
                              command=lambda: input_text.delete("1.0", tk.END))
        clear_btn.pack(side=tk.LEFT, padx=(8, 0), ipadx=10, ipady=4)
        close_btn = tk.Button(btn_row, text="关闭", bg="#555577", fg="#ffffff",
                              font=font_btn, relief=tk.FLAT, cursor="hand2")
        close_btn.pack(side=tk.RIGHT, ipadx=14, ipady=4)

        # ---- ③ 结果 ----
        card3 = tk.Frame(body, bg=COLORS["bg_card"])
        card3.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(card3, text="③ 解析结果", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 4))
        result_text = tk.Text(card3, height=5, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                              relief=tk.FLAT, font=("Consolas", 9), state=tk.DISABLED, wrap=tk.WORD)
        result_text.pack(fill=tk.X, padx=12, pady=(0, 10))

        # ---- ④ 已有手动任务 ----
        card4 = tk.Frame(body, bg=COLORS["bg_card"])
        card4.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tk.Label(card4, text="④ 已有手动任务（可删除）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 4))
        list_frame = tk.Frame(card4, bg=COLORS["bg_card"], height=120)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        lbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        task_list = tk.Listbox(list_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                               relief=tk.FLAT, font=("Consolas", 9), height=5,
                               yscrollcommand=lbar.set,
                               selectbackground=COLORS["accent"], selectforeground="#000000")
        lbar.config(command=task_list.yview)
        lbar.pack(side=tk.RIGHT, fill=tk.Y)
        task_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        del_row = tk.Frame(card4, bg=COLORS["bg_card"])
        del_row.pack(fill=tk.X, padx=12, pady=(6, 10))

        def append_result(line):
            try:
                result_text.configure(state=tk.NORMAL)
                result_text.insert(tk.END, line if line.endswith("\n") else line + "\n")
                result_text.see(tk.END)
                result_text.configure(state=tk.DISABLED)
            except Exception:
                pass

        def refresh_manual_list():
            try:
                task_list.delete(0, tk.END)
            except Exception:
                return
            for t in MANUAL_TASKS:
                award = t.get("award") or "-"
                cls = f'{t.get("version", "")}/{t.get("period", "")}/{t.get("type", "")}'
                task_list.insert(tk.END, f'{t.get("task_id","")}  |  {t.get("name","")}  |  {award}  |  {cls}')

        def delete_selected():
            sel = list(task_list.curselection())
            if not sel:
                append_result("✗ 请先在下方列表选中要删除的任务")
                return
            for idx in sel:
                if idx >= len(MANUAL_TASKS):
                    continue
                tid = MANUAL_TASKS[idx].get("task_id", "")
                if remove_manual_task(tid):
                    append_result(f"🗑 已删除手动任务 {tid}")
            refresh_manual_list()
            self.mt_refresh_task_combos()
            self._mt_after_change()

        tk.Button(del_row, text="🗑 删除选中", bg="#c0392b", fg="#ffffff", font=font_btn,
                  relief=tk.FLAT, cursor="hand2", command=delete_selected
                  ).pack(side=tk.LEFT, ipadx=10, ipady=3)
        tk.Button(del_row, text="刷新列表", bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                  font=font_btn, relief=tk.FLAT, cursor="hand2",
                  command=lambda: (refresh_manual_list(), self.mt_refresh_task_combos())
                  ).pack(side=tk.LEFT, padx=(8, 0), ipadx=10, ipady=3)

        # ---- 解析逻辑 ----
        def do_add():
            ids = parse_task_ids(input_text.get("1.0", tk.END))
            if not ids:
                append_result("✗ 没有识别到 task_id，请检查输入")
                return
            account_name = account_var.get()
            if not account_name:
                append_result("✗ 请先选择查询账户（没有账户请先到「账户管理」添加）")
                return
            cls_version = version_var.get().strip() or MANUAL_VERSION
            cls_period = period_var.get().strip() or MANUAL_PERIOD
            cls_type = type_var.get().strip() or MANUAL_TYPE
            act_id_fallback = act_id_var.get().strip()
            force = bool(force_var.get())
            target_group = ""
            if new_group_var.get().strip():
                target_group = new_group_var.get().strip()
            elif group_var.get() and group_var.get() != "（不加入）":
                target_group = group_var.get()

            add_btn.config(state=tk.DISABLED, text="解析中...")
            append_result(f"===== 开始解析 {len(ids)} 个 task_id | 归类 {cls_version}/{cls_period}/{cls_type} | 账户 {account_name} =====")

            def worker():
                cookies = {}
                try:
                    acc = next((a for a in self.account_mgr.accounts if a.get("name") == account_name), None)
                    if acc:
                        cookies = cookies_from_account(acc)
                except Exception as exc:
                    self.after(0, lambda: append_result(f"✗ 读取账户 Cookie 失败: {exc}"))

                ok_count = 0
                for i, tid in enumerate(ids, 1):
                    head = f"[{i}/{len(ids)}] {tid} "
                    try:
                        info, msg = get_mission_info(tid, cookies)
                    except Exception as exc:
                        info, msg = None, f"网络异常: {exc}"

                    added = False
                    meta = None
                    if info:
                        meta = extract_task_meta(info, tid, act_id_fallback)
                        meta.update({"version": cls_version, "period": cls_period, "type": cls_type})
                        added, add_msg = add_manual_task(meta)
                        if added:
                            line = (f"{head}✓ {meta['name']} | 奖励:{meta['award'] or '-'} | "
                                    f"act_id:{meta['act_id'] or '-'} | act:{meta['act_name'] or '-'}")
                        else:
                            line = f"{head}⚠ {add_msg}"
                    elif force:
                        meta = {"task_id": tid, "name": tid, "award": "", "act_id": act_id_fallback,
                                "act_name": "", "version": cls_version,
                                "period": cls_period, "type": cls_type}
                        added, add_msg = add_manual_task(meta)
                        line = (f"{head}⚠ 查询失败({msg})，已强制添加" if added else f"{head}⚠ {add_msg}")
                    else:
                        line = f"{head}✗ 查询失败: {msg}（可勾选「查询失败也强制添加」）"

                    if added:
                        ok_count += 1
                        if target_group:
                            try:
                                _g, created, gmsg = self.mt_add_task_to_group(meta, target_group, account_name)
                                line += f" → {gmsg}" + ("（新建组）" if created else "")
                            except Exception as exc:
                                line += f" → 加入任务组失败: {exc}"
                    self.after(0, lambda l=line: append_result(l))
                    if i < len(ids):
                        time.sleep(0.6)

                def done():
                    add_btn.config(state=tk.NORMAL, text="🔍 解析并添加")
                    refresh_manual_list()
                    self.mt_refresh_task_combos()
                    self._mt_after_change()
                    if target_group:
                        try:
                            group_combo.config(values=["（不加入）"] + [g.get("group_name", "") for g in (getattr(self, "rush_groups", []) or [])])
                        except Exception:
                            pass
                        self._mt_refresh_after_group_change()
                    append_result(f"===== 完成：成功 {ok_count}/{len(ids)} =====")
                self.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        add_btn.config(command=do_add)
        close_btn.config(command=lambda: (canvas.unbind_all("<MouseWheel>"), dlg.destroy()))
        dlg.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), dlg.destroy()))

        refresh_manual_list()
        append_result("提示：归类到已有版本（如 鸣潮3.7）后，该任务会和官方任务一起出现在对应下拉框；")
        append_result("      勾选/填写任务组则同时加入精准抢码的组，可直接开抢。")

        # ---- 自适应尺寸：按内容实际需要，且不超过屏幕 ----
        dlg.update_idletasks()
        need_w = max(dlg.winfo_reqwidth(), 720)
        need_h = dlg.winfo_reqheight()
        screen_w = dlg.winfo_screenwidth()
        screen_h = dlg.winfo_screenheight()
        w = min(need_w, int(screen_w * 0.92))
        h = min(need_h, int(screen_h * 0.86))
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.minsize(min(640, w), min(480, h))

    # ---------------- 宿主联动 ----------------

    def _mt_after_change(self):
        """手动任务库变化后，仅当界面正停在「手动任务」时刷新下游下拉框。"""
        var = getattr(self, "version_var", None)
        if var is not None:
            try:
                if var.get() == MANUAL_VERSION:
                    self.on_version_change()
            except Exception:
                pass
        nm_var = getattr(self, "nm_version_var", None)
        if nm_var is not None:
            try:
                if nm_var.get() == MANUAL_VERSION:
                    self.nm_on_version_change()
            except Exception:
                pass

    def mt_has_manual_tasks(self):
        return bool(MANUAL_TASKS)
