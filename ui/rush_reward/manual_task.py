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
from ui.theme import sz, font as theme_font
from widgets import DarkButton
from tasks_config import (ALL_TASKS, MANUAL_TASKS, MANUAL_VERSION, MANUAL_PERIOD,
                          MANUAL_TYPE, OFFICIAL_TASKS, HIDDEN_TASK_IDS,
                          add_manual_task, remove_manual_task, hide_official_task)
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

        # O7: 字号统一走 theme，按 DPI 缩放
        font_lbl = theme_font(10)
        font_btn = theme_font(10, bold=True)
        font_input = theme_font(10)

        # ===== 可滚动容器：保证任何 DPI 下都不会"显示不完全" =====
        # 关键：滚动条必须用 place 绝对定位，不能用 pack。
        # 用 pack 时，滚动条的显示/隐藏会改变 canvas 宽度 -> 触发 <Configure> ->
        # 再次调整滚动条，形成"抖动"死循环。
        outer = tk.Frame(dlg, bg=COLORS["bg_dark"])
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, bg=COLORS["bg_dark"], highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        body = tk.Frame(canvas, bg=COLORS["bg_dark"])
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        # 滚动条位置随 canvas 尺寸同步（place 定位，不挤压内容）
        vbar_visible = {"on": False}

        def _place_vbar():
            try:
                cw = canvas.winfo_width()
                ch = canvas.winfo_height()
                if cw <= 1 or ch <= 1:
                    return
                vbar.place(in_=canvas, relx=1.0, rely=0, anchor="ne",
                           y=0, width=16, height=ch)
            except Exception:
                pass

        def _sync_body_width(event):
            """body 宽度扣除滚动条占位，避免文字被滚动条盖住。"""
            try:
                reserve = 16 if vbar_visible["on"] else 0
                canvas.itemconfigure(body_id, width=max(1, event.width - reserve))
                _place_vbar()
            except Exception:
                pass

        canvas.bind("<Configure>", _sync_body_width)

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
        # 列宽策略：label 列用 minsize 固定下限，输入列可伸展且有下限。
        # 这样即使窗口被拖窄，期数/类型下拉框也不会被挤成一条线。
        _COL_CFG = {
            0: dict(weight=0, minsize=86),   # 活动任务组 / 查询账户 label
            1: dict(weight=1, minsize=168),  # 活动任务组 / 账户 下拉框
            2: dict(weight=0, minsize=62),   # 期数 / act_id 兜底 label
            3: dict(weight=1, minsize=132),  # 期数 / act_id 输入
            4: dict(weight=0, minsize=46),   # 类型 label
            5: dict(weight=2, minsize=170),  # 类型下拉框（给足宽度显示自定义类型）
        }
        for col, cfg in _COL_CFG.items():
            grid.columnconfigure(col, **cfg)

        # 行1：归类 版本/期数/类型
        tk.Label(grid, text="活动任务组", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=0, sticky="w", pady=3)
        version_var = tk.StringVar(value=MANUAL_VERSION)
        version_combo = ttk.Combobox(grid, textvariable=version_var, values=available_versions(),
                                     state="normal", width=16, font=font_input)
        version_combo.grid(row=0, column=1, sticky="we", padx=(6, 12), pady=3)

        tk.Label(grid, text="期数", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=2, sticky="w", pady=3)
        period_var = tk.StringVar(value=MANUAL_PERIOD)
        period_combo = ttk.Combobox(grid, textvariable=period_var, values=[MANUAL_PERIOD],
                                    state="normal", width=11, font=font_input)
        period_combo.grid(row=0, column=3, sticky="we", padx=(6, 12), pady=3)

        tk.Label(grid, text="类型", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=font_lbl).grid(row=0, column=4, sticky="w", pady=3)
        type_var = tk.StringVar(value=MANUAL_TYPE)
        type_combo = ttk.Combobox(grid, textvariable=type_var, values=[MANUAL_TYPE],
                                  state="normal", width=14, font=font_input)
        type_combo.grid(row=0, column=5, sticky="we", padx=(6, 0), pady=3)

        def _sync_period_types(_event=None):
            """版本变化：刷新期数候选；期数/类型都允许用户自填，不被清空。"""
            v = version_var.get().strip()
            ps = available_periods(v)
            cur_period = period_var.get().strip()
            period_combo.config(values=ps or [MANUAL_PERIOD])
            # 只有当前期数不在候选里，才切到第一个；否则保留用户选择
            if cur_period and cur_period in ps:
                period_var.set(cur_period)
            elif ps:
                period_var.set(ps[0])
            # 期数定了，再刷新类型候选
            _sync_types()

        def _sync_types(_event=None):
            """期数变化：刷新类型候选；保留用户已输入的自定义类型。"""
            v = version_var.get().strip()
            p = period_var.get().strip()
            ts = available_types(v, p)
            cur_type = type_var.get().strip()
            # 把当前值并入候选，保证自定义类型不会从列表里消失
            merged = list(ts)
            if cur_type and cur_type not in merged:
                merged.append(cur_type)
            type_combo.config(values=merged or [cur_type or MANUAL_TYPE])
            if cur_type:
                type_var.set(cur_type)
        version_combo.bind("<<ComboboxSelected>>", _sync_period_types)
        period_combo.bind("<<ComboboxSelected>>", _sync_types)

        tk.Label(grid, text="↑ 归类到哪个活动任务组：选已有版本(如 鸣潮3.7)即可并入该组；也可输入新版本名自动新建一组",
                 bg=COLORS["bg_card"], fg=COLORS["success"], font=("微软雅黑", 9)
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

        # ---- 按钮 ----
        btn_row = tk.Frame(body, bg=COLORS["bg_dark"])
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 6))
        # 注意：按钮文字会随状态变化（如"保存到任务库（3）"），
        # 必须固定 width，否则文字变长会撑开按钮 -> 整行重排 -> 界面抖动。
        add_btn = DarkButton(btn_row, text="🔍 解析（预览）", bg_color=COLORS["accent"], text_color="#000000", height=32, width=150)
        add_btn.pack(side=tk.LEFT, ipady=4)

        # 保存按钮：解析只入预览区，点这里才真正写盘
        save_btn = DarkButton(btn_row, text="💾 保存到任务库", bg_color=COLORS["success"], text_color="#000000", height=32, width=200)
        save_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=4)

        discard_btn = DarkButton(btn_row, text="✕ 放弃预览", bg_color="#7f8c8d", text_color="#ffffff", height=32, width=130)
        discard_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=4)

        clear_btn = DarkButton(btn_row, text="清空输入", command=lambda: input_text.delete("1.0", tk.END), bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32)
        clear_btn.pack(side=tk.LEFT, padx=(8, 0), ipadx=10, ipady=4)
        close_btn = DarkButton(btn_row, text="关闭", bg_color="#555577", text_color="#ffffff", height=32)
        close_btn.pack(side=tk.RIGHT, ipadx=14, ipady=4)

        # ---- ③ 结果 ----
        card3 = tk.Frame(body, bg=COLORS["bg_card"])
        card3.pack(fill=tk.X, padx=10, pady=(0, 6))
        title_row = tk.Frame(card3, bg=COLORS["bg_card"])
        title_row.pack(fill=tk.X, padx=12, pady=(8, 4))
        tk.Label(title_row, text="③ 解析预览（尚未保存）", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        preview_count = tk.Label(title_row, text="", bg=COLORS["bg_card"], fg=COLORS["warning"],
                                 font=("微软雅黑", 9))
        preview_count.pack(side=tk.LEFT, padx=(10, 0))
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
            refresh_official_list()
            self.mt_refresh_task_combos()
            self._mt_after_change()

        DarkButton(del_row, text="🗑 删除选中", command=delete_selected, bg_color="#c0392b", text_color="#ffffff", height=32).pack(side=tk.LEFT, ipadx=10, ipady=3)
        DarkButton(del_row, text="刷新列表", command=lambda: (refresh_manual_list(), self.mt_refresh_task_combos()), bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32).pack(side=tk.LEFT, padx=(8, 0), ipadx=10, ipady=3)

        # ---- ⑤ 官方任务管理（删除后永久生效）----
        card5 = tk.Frame(body, bg=COLORS["bg_card"])
        card5.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tk.Label(card5, text="⑤ 官方任务管理（删除后永久生效，更新不复活）",
                 bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 2))
        tk.Label(card5, text="选中后点「删除官方任务」，会记入 data/hidden_tasks.json，之后启动不再出现",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)
                 ).pack(anchor=tk.W, padx=12, pady=(0, 4))

        official_frame = tk.Frame(card5, bg=COLORS["bg_card"], height=120)
        official_frame.pack(fill=tk.BOTH, expand=True, padx=12)
        obar = tk.Scrollbar(official_frame, orient=tk.VERTICAL)
        official_list = tk.Listbox(official_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                   relief=tk.FLAT, font=("Consolas", 9), height=5,
                                   selectmode=tk.EXTENDED, yscrollcommand=obar.set,
                                   selectbackground=COLORS["accent"], selectforeground="#000000")
        obar.config(command=official_list.yview)
        obar.pack(side=tk.RIGHT, fill=tk.Y)
        official_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        official_row = tk.Frame(card5, bg=COLORS["bg_card"])
        official_row.pack(fill=tk.X, padx=12, pady=(6, 10))

        official_shown = []

        def refresh_official_list():
            official_shown.clear()
            try:
                official_list.delete(0, tk.END)
            except Exception:
                return
            manual_ids = {t.get("task_id") for t in MANUAL_TASKS}
            for t in OFFICIAL_TASKS:
                if t.get("task_id") in HIDDEN_TASK_IDS or t.get("task_id") in manual_ids:
                    continue
                official_shown.append(t)
                official_list.insert(
                    tk.END,
                    f'{t.get("version","")}/{t.get("period","")}/{t.get("type","")}  |  '
                    f'{t.get("name","")}  |  {t.get("task_id","")}')

        def delete_official_selected():
            sel = list(official_list.curselection())
            if not sel:
                append_result("✗ 请先在⑤列表里选中要删除的官方任务")
                return
            targets = [official_shown[i] for i in sel if i < len(official_shown)]
            if not targets:
                return
            names = "、".join(t.get("name", "") for t in targets[:3])
            more = f" 等 {len(targets)} 个" if len(targets) > 3 else ""
            if not tk.messagebox.askyesno(
                    "删除官方任务",
                    f"确定删除以下官方任务吗？\n\n{names}{more}\n\n"
                    f"删除后会记入 hidden_tasks.json，之后启动和更新都不会再出现。",
                    parent=dlg):
                return
            for t in targets:
                if hide_official_task(t["task_id"]):
                    append_result(f"🗑 已永久删除官方任务 {t['task_id']} {t.get('name','')}")
            refresh_official_list()
            self.mt_refresh_task_combos()
            self._mt_after_change()

        DarkButton(official_row, text="🗑 删除官方任务", command=delete_official_selected, bg_color="#c0392b", text_color="#ffffff", height=32).pack(side=tk.LEFT, ipadx=10, ipady=3)
        DarkButton(official_row, text="刷新列表", command=lambda: (refresh_official_list(), refresh_manual_list()), bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32).pack(side=tk.LEFT, padx=(8, 0), ipadx=10, ipady=3)

        # ---- 解析 / 保存 / 放弃 ----
        # pending：本轮解析出的待保存任务。解析只进这里，点保存才落盘。
        pending = []

        def _update_pending_ui():
            n = len(pending)
            if n:
                preview_count.config(text=f"待保存 {n} 条", fg=COLORS["warning"])
                save_btn.config(state=tk.NORMAL, text=f"💾 保存到任务库（{n}）")
                discard_btn.config(state=tk.NORMAL)
            else:
                preview_count.config(text="", fg=COLORS["text_muted"])
                save_btn.config(state=tk.DISABLED, text="💾 保存到任务库")
                discard_btn.config(state=tk.DISABLED)

        def _clear_preview():
            pending.clear()
            result_text.configure(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            result_text.configure(state=tk.DISABLED)
            _update_pending_ui()

        def do_parse():
            if pending:
                if not tk.messagebox.askyesno(
                        "已有未保存的预览",
                        f"当前还有 {len(pending)} 条预览未保存，重新解析会丢弃它们。\n\n确定继续吗？",
                        parent=dlg):
                    return
            _clear_preview()

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

            add_btn.config(state=tk.DISABLED, text="解析中...")
            append_result(f"===== 开始解析 {len(ids)} 个 task_id | 活动任务组 {cls_version}/{cls_period}/{cls_type} =====")
            append_result("      解析完成后请点「保存到任务库」正式生效")

            def worker():
                cookies = {}
                try:
                    acc = next((a for a in self.account_mgr.accounts if a.get("name") == account_name), None)
                    if acc:
                        cookies = cookies_from_account(acc)
                except Exception as exc:
                    self.after(0, lambda: append_result(f"✗ 读取账户 Cookie 失败: {exc}"))

                parsed_ok = 0
                for i, tid in enumerate(ids, 1):
                    head = f"[{i}/{len(ids)}] {tid} "
                    try:
                        info, msg = get_mission_info(tid, cookies)
                    except Exception as exc:
                        info, msg = None, f"网络异常: {exc}"

                    meta = None
                    if info:
                        meta = extract_task_meta(info, tid, act_id_fallback)
                        meta.update({"version": cls_version, "period": cls_period, "type": cls_type})
                        # 只做「能否保存」的预检，不落盘
                        dup = (any(t.get("task_id") == tid for t in MANUAL_TASKS)
                               or any(t.get("task_id") == tid for t in ALL_TASKS))
                        dup_in_pending = any(t.get("task_id") == tid for t in pending)
                        if dup or dup_in_pending:
                            line = f"{head}⚠ 该 task_id 已存在，已跳过（不加入预览）"
                        else:
                            pending.append(meta)
                            parsed_ok += 1
                            line = (f"{head}✓ {meta['name']} | 奖励:{meta['award'] or '-'} | "
                                    f"act_id:{meta['act_id'] or '-'} | act:{meta['act_name'] or '-'}")
                    elif force:
                        meta = {"task_id": tid, "name": tid, "award": "", "act_id": act_id_fallback,
                                "act_name": "", "version": cls_version,
                                "period": cls_period, "type": cls_type}
                        if any(t.get("task_id") == tid for t in pending):
                            line = f"{head}⚠ 预览中已存在，跳过"
                        else:
                            pending.append(meta)
                            parsed_ok += 1
                            line = f"{head}⚠ 查询失败({msg})，已放入预览（强制添加）"
                    else:
                        line = f"{head}✗ 查询失败: {msg}（可勾选「查询失败也强制添加」）"

                    self.after(0, lambda l=line: append_result(l))
                    if i < len(ids):
                        time.sleep(0.6)

                def done():
                    add_btn.config(state=tk.NORMAL, text="🔍 解析（预览）")
                    _update_pending_ui()
                    append_result(f"===== 解析完成：{parsed_ok}/{len(ids)} 条待保存 =====")
                    if parsed_ok:
                        append_result("      ↑ 确认无误后点「保存到任务库」才会真正写入")
                self.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        def do_save():
            if not pending:
                append_result("✗ 没有待保存的任务，请先解析")
                return
            save_btn.config(state=tk.DISABLED, text="保存中...")
            saved, failed = 0, []
            for meta in list(pending):
                ok, msg = add_manual_task(meta)
                if ok:
                    saved += 1
                else:
                    failed.append(f"{meta.get('task_id')}: {msg}")

            pending.clear()
            result_text.configure(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            result_text.configure(state=tk.DISABLED)

            if saved:
                append_result(f"✓ 已保存 {saved} 条到任务库")
            for f in failed:
                append_result(f"⚠ 保存失败 {f}")

            save_btn.config(text="💾 保存到任务库")
            _update_pending_ui()
            refresh_manual_list()
            refresh_official_list()
            self.mt_refresh_task_combos()
            self._mt_after_change()

        def do_discard():
            n = len(pending)
            if not n:
                return
            if tk.messagebox.askyesno("放弃预览", f"确定放弃这 {n} 条未保存的预览吗？", parent=dlg):
                _clear_preview()
                append_result(f"已放弃 {n} 条预览（未写入任务库）")

        add_btn.config(command=do_parse)
        save_btn.config(command=do_save)
        discard_btn.config(command=do_discard)
        close_btn.config(command=lambda: (canvas.unbind_all("<MouseWheel>"), dlg.destroy()))
        dlg.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), dlg.destroy()))

        refresh_manual_list()
        refresh_official_list()
        append_result("提示：选「活动任务组」= 鸣潮3.7，该任务就会并进鸣潮3.7 这组活动任务里；")
        append_result("      下拉框里可直接输入新版本名（如 鸣潮3.8）自动新建一个活动任务组。")

        # ---- 自适应尺寸：按 body 真实内容尺寸（不是 canvas 外壳）----
        # 之前量的是 dlg.winfo_reqheight()，它只是 canvas 默认高度(264)，
        # 导致窗口被裁成一条、内容显示不全。这里改为量内部 body 的实际需求。
        body.update_idletasks()
        content_w = body.winfo_reqwidth()
        content_h = body.winfo_reqheight()

        screen_w = dlg.winfo_screenwidth()
        screen_h = dlg.winfo_screenheight()
        max_w = int(screen_w * 0.92)
        max_h = int(screen_h * 0.86)

        # 边距/最小尺寸保持原始像素值（与历史行为一致，不再乘 DPI）
        need_w = max(content_w + 40, 780)
        need_h = max(content_h + 16, 520)

        w = min(need_w, max_w)
        h = min(need_h, max_h)
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.minsize(min(700, w), min(420, h))

        # 滚动条按需显示：只在"需要/不需要"真正切换时才动，避免抖动
        def _sync_scrollbar(event=None):
            try:
                bbox = canvas.bbox("all")
                if not bbox:
                    return
                need = bbox[3] - bbox[1]
                vis = canvas.winfo_height()
                if vis <= 1:
                    return
                should_show = need > vis + 2
                if should_show == vbar_visible["on"]:
                    return  # 状态未变，绝不重复布局
                vbar_visible["on"] = should_show
                if should_show:
                    _place_vbar()
                else:
                    vbar.place_forget()
                    canvas.yview_moveto(0)
                # 宽度补偿：滚动条出现/消失后重新设置 body 宽度
                reserve = 16 if should_show else 0
                canvas.itemconfigure(body_id, width=max(1, canvas.winfo_width() - reserve))
            except Exception:
                pass

        def _on_body_configure(event=None):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass
            _sync_scrollbar()

        body.bind("<Configure>", _on_body_configure)
        dlg.after(80, _sync_scrollbar)

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
