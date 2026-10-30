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
        # v6.6.2: ScheduleFrame 没有独立 room_mgr，统一走 app 的
        self.room_mgr = getattr(app, "room_mgr", None)
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
        """构建日程任务页面（v6.6.1 B+C 融合：参数内嵌 + 模板复用）。

        布局：
          ① 创建区（紧凑单行 + 常用时间快捷按钮）
          ② 参数区（随类型动态切换，不切屏即可配置）
          ③ 任务列表（表格化，行内操作）
          ④ 底部：模板管理(折叠) + 日志(35%宽度)
        """
        from widgets import RoundCombobox
        import schedule_params as sp

        # ============ ① 创建区 ============
        create_card = tk.Frame(self, bg=COLORS["bg_card"],
                               highlightthickness=1,
                               highlightbackground=COLORS["border"])
        create_card.pack(fill=tk.X, pady=(0, 10))

        head = tk.Frame(create_card, bg=COLORS["bg_card"])
        head.pack(fill=tk.X, padx=16, pady=(12, 8))
        tk.Label(head, text="➕ 创建日程任务", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 15, "bold")).pack(side=tk.LEFT)
        self.scheduler_status_label = tk.Label(
            head, text="● 调度器运行中", bg=COLORS["bg_card"],
            fg=COLORS["success"], font=("微软雅黑", 11, "bold"))
        self.scheduler_status_label.pack(side=tk.RIGHT)

        row1 = tk.Frame(create_card, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, padx=16, pady=(4, 8))

        tk.Label(row1, text="名称", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.task_name_entry = DarkEntry(row1, width=18)
        self.task_name_entry.pack(side=tk.LEFT, padx=(8, 22))

        tk.Label(row1, text="类型", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)

        # 类型：卡片式单选（选中高亮）
        self.task_type_var = tk.StringVar(value="watch")
        self._type_cards = {}
        for val, txt in [("rush", "⚡ 抢码"), ("watch", "📺 看播"),
                         ("danmaku", "💬 弹幕"), ("shutdown", "⏻ 关机")]:
            lbl = tk.Label(row1, text=txt, bg=COLORS["bg_input"],
                           fg=COLORS["text_secondary"],
                           font=("微软雅黑", 11), padx=14, pady=6,
                           cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=4)
            lbl.bind("<Button-1>",
                     lambda e, v=val: self._select_type_card(v))
            self._type_cards[val] = lbl

        tk.Label(row1, text="时间", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=(18, 0))
        # v6.6.5: 时间改为下拉选择（用户要求，不要手动输入）
        self.schedule_hour_var = tk.StringVar(value="02")
        self.schedule_hour = RoundCombobox(
            row1, textvariable=self.schedule_hour_var,
            values=["%02d" % h for h in range(24)], width=4, height=28)
        self.schedule_hour.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row1, text=":", bg=COLORS["bg_card"],
                 fg=COLORS["text_primary"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)
        self.schedule_minute_var = tk.StringVar(value="00")
        self.schedule_minute = RoundCombobox(
            row1, textvariable=self.schedule_minute_var,
            values=["%02d" % m for m in range(60)], width=4, height=28)
        self.schedule_minute.pack(side=tk.LEFT, padx=(2, 16))

        # 常用时间快捷
        for hhmm in ["00:10", "01:00", "02:00", "18:00"]:
            b = tk.Label(row1, text=hhmm, bg=COLORS["bg_input"],
                         fg=COLORS["text_secondary"],
                         font=("Consolas", 11), padx=8, pady=4,
                         cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            b.bind("<Button-1>",
                   lambda e, t=hhmm: self._apply_quick_time(t))

        # 第二行：参数区（动态）+ 添加按钮
        row2 = tk.Frame(create_card, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, padx=16, pady=(2, 8))

        self.param_frame = tk.Frame(row2, bg=COLORS["bg_card"])
        self.param_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_box = tk.Frame(row2, bg=COLORS["bg_card"])
        btn_box.pack(side=tk.RIGHT)
        DarkButton(btn_box, "＋ 添加", command=self.add_schedule_task,
                   width=110, height=34, bg_color=COLORS["accent"],
                   text_color="#000000").pack(side=tk.LEFT, padx=(0, 6))
        DarkButton(btn_box, "📋 带入当前页面",
                   command=self.import_current_params,
                   width=130, height=34, bg_color="#8e44ad",
                   text_color="#ffffff").pack(side=tk.LEFT)

        # 第三行：保存为模板
        row3 = tk.Frame(create_card, bg=COLORS["bg_card"])
        row3.pack(fill=tk.X, padx=16, pady=(0, 12))
        tk.Label(row3, text="💾 存为模板", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.tpl_save_name = DarkEntry(row3, width=14)
        self.tpl_save_name.pack(side=tk.LEFT, padx=(6, 4))
        DarkButton(row3, "保存", command=self.save_current_as_template,
                   width=64, height=28, bg_color="#27ae60",
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT)
        tk.Label(row3, text="   或载入模板：", bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.tpl_load_var = tk.StringVar()
        # v6.6.2: width 是"字符数"，RoundCombobox 会算成 char*9+40 像素，
        # 之前误写 150 -> 1390px 撑满整行。16 字符 ≈ 184px 合适。
        self.tpl_load_combo = RoundCombobox(row3, textvariable=self.tpl_load_var,
                                            values=[], width=16, height=28)
        self.tpl_load_combo.pack(side=tk.LEFT, padx=(4, 4))
        DarkButton(row3, "载入", command=self.load_template_to_form,
                   width=64, height=28, bg_color="#3498db",
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT)
        DarkButton(row3, "删除", command=self.delete_template_from_lib,
                   width=64, height=28, bg_color=COLORS["danger"],
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=(3, 0))

        # ============ ③ 任务列表 ============
        mid = tk.Frame(self, bg=COLORS["bg_dark"])
        mid.pack(fill=tk.BOTH, expand=True)

        # v6.6.2: grid weight 会被列表内容的最小宽度撑破比例（实测 54/46），
        # 改用 place + relwidth 精确实现 65% / 35%。
        list_card = tk.Frame(mid, bg=COLORS["bg_card"],
                             highlightthickness=1,
                             highlightbackground=COLORS["border"])
        list_card.place(x=0, y=0, relwidth=0.578, relheight=1.0)  # v6.6.5: 日志加宽到42%

        lh = tk.Frame(list_card, bg=COLORS["bg_card"])
        lh.pack(fill=tk.X, padx=12, pady=(8, 4))
        tk.Label(lh, text="📋 日程任务列表", bg=COLORS["bg_card"],
                 fg=COLORS["accent"],
                 font=("微软雅黑", 15, "bold")).pack(side=tk.LEFT)
        self.task_count_label = tk.Label(lh, text="", bg=COLORS["bg_card"],
                                         fg=COLORS["text_muted"],
                                         font=("微软雅黑", 11))
        self.task_count_label.pack(side=tk.LEFT, padx=(8, 0))

        # 批量操作条
        bar = tk.Frame(list_card, bg=COLORS["bg_card"])
        bar.pack(fill=tk.X, padx=12, pady=(0, 4))
        # v6.6.2: 加宽按钮避免中文字被截断（compact 模式文字宽度=设定值）
        DarkButton(bar, "☑ 全选/取消", command=self.toggle_select_all,
                   width=110, height=28, bg_color="#9b59b6",
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT)
        DarkButton(bar, "🗑 删除选中", command=self.delete_selected_tasks,
                   width=150, height=28, bg_color=COLORS["danger"],
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=(6, 0))
        DarkButton(bar, "⚡ 全部启用", command=self.enable_all_tasks,
                   width=150, height=28, bg_color="#e67e22",
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=(6, 0))
        DarkButton(bar, "⏸ 全部停用", command=self.disable_all_tasks,
                   width=150, height=28, bg_color="#7f8c8d",
                   text_color="#ffffff", compact=True).pack(side=tk.LEFT, padx=(6, 0))

        self.task_list_frame = tk.Frame(list_card, bg=COLORS["bg_card"])
        self.task_list_frame.pack(fill=tk.BOTH, expand=True,
                                  padx=12, pady=(0, 8))

        # ============ ④ 日志（35%） ============
        log_card = tk.Frame(mid, bg=COLORS["bg_card"],
                            highlightthickness=1,
                            highlightbackground=COLORS["border"])
        log_card.place(relx=0.582, y=0, relwidth=0.418, relheight=1.0)  # v6.6.5: 35%->42%

        tk.Label(log_card, text="📝 执行日志", bg=COLORS["bg_card"],
                 fg=COLORS["accent"],
                 font=("微软雅黑", 15, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 4))

        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.schedule_log_text = tk.Text(
            log_frame, bg="#0d1117", fg=COLORS["text_secondary"],
            insertbackground=COLORS["accent"], font=("Consolas", 11),
            bd=0, highlightthickness=0, wrap=tk.WORD, state=tk.DISABLED)
        self.schedule_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(log_frame, orient=tk.VERTICAL,
                          command=self.schedule_log_text.yview,
                          bg=COLORS["bg_input"])
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.schedule_log_text.config(yscrollcommand=sb.set)

        self.selected_task_id = None
        if not hasattr(self, "selected_ids"):
            self.selected_ids = set()

        # 初始化类型卡片 + 参数区
        self._select_type_card("watch")

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

    # ==================== v6.6.1 新增：参数内嵌 + 模板 ====================

    # ---------- v6.6.5: RoundCombobox 兼容 DarkEntry 接口 ----------
    def _tm_get(self, combo):
        """下拉框取值（兼容原 DarkEntry.get）。"""
        try:
            return combo.get()
        except Exception:
            return "0"

    def _tm_set(self, combo, val):
        """下拉框赋值。"""
        try:
            combo.set(str(val))
        except Exception:
            pass

    def _select_type_card(self, task_type):
        """选中任务类型卡片（高亮）+ 重建参数区。"""
        try:
            self.task_type_var.set(task_type)
        except Exception:
            pass
        # 卡片高亮
        for val, lbl in getattr(self, "_type_cards", {}).items():
            try:
                if val == task_type:
                    lbl.config(bg=COLORS["accent"], fg="#000000",
                               font=("微软雅黑", 11, "bold"))
                else:
                    lbl.config(bg=COLORS["bg_input"],
                               fg=COLORS["text_secondary"],
                               font=("微软雅黑", 11))
            except Exception:
                pass
        self._auto_fill_name(task_type)
        self._rebuild_param_panel(task_type)
        # 时间输入可用性
        try:
            if task_type in ("rush", "shutdown"):
                self.schedule_hour.combo.config(state="disabled")
                self.schedule_minute.combo.config(state="disabled")
            else:
                self.schedule_hour.combo.config(state="readonly")
                self.schedule_minute.combo.config(state="readonly")
        except Exception:
            pass
        self._refresh_template_combo(task_type)

    def _rebuild_param_panel(self, task_type):
        """按类型重建参数编辑区（就地配置，不用切屏）。"""
        import schedule_params as sp
        try:
            for w in self.param_frame.winfo_children():
                w.destroy()
        except Exception:
            return

        self._param_vars = {}
        spec = sp.task_param_spec(task_type)
        if not spec:
            tk.Label(self.param_frame,
                     text="（该类型无需额外参数）",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 11)).pack(side=tk.LEFT)
            return

        # 图标 + 标题
        tk.Label(self.param_frame, text=spec.get("icon", "⚙") + " ",
                 bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT)

        for f in spec.get("fields", []):
            key = f["key"]
            typ = f["type"]
            label = f.get("label", key)
            default = f.get("default")

            if typ == "accounts":
                # 账户多选：按钮弹窗选择
                txt = tk.Label(self.param_frame, text="账户: 未选",
                               bg=COLORS["bg_input"],
                               fg=COLORS["warning"],
                               font=("微软雅黑", 11),
                               padx=8, pady=3, cursor="hand2")
                txt.pack(side=tk.LEFT, padx=(2, 8))
                txt.bind("<Button-1>",
                         lambda e, k=key, t=txt:
                         self._pick_accounts(k, t))
                self._param_vars[key] = {"type": "accounts",
                                         "widget": txt,
                                         "value": list(default or [])}

            elif typ == "rooms":
                txt = tk.Label(self.param_frame, text="直播间: 未选",
                               bg=COLORS["bg_input"],
                               fg=COLORS["warning"],
                               font=("微软雅黑", 11),
                               padx=8, pady=3, cursor="hand2")
                txt.pack(side=tk.LEFT, padx=(2, 8))
                txt.bind("<Button-1>",
                         lambda e, k=key, t=txt:
                         self._pick_rooms(k, t, multi=True))
                self._param_vars[key] = {"type": "rooms",
                                         "widget": txt,
                                         "value": list(default or [])}

            elif typ == "room":
                txt = tk.Label(self.param_frame, text="直播间: 未选",
                               bg=COLORS["bg_input"],
                               fg=COLORS["warning"],
                               font=("微软雅黑", 11),
                               padx=8, pady=3, cursor="hand2")
                txt.pack(side=tk.LEFT, padx=(2, 8))
                txt.bind("<Button-1>",
                         lambda e, k=key, t=txt:
                         self._pick_rooms(k, t, multi=False))
                self._param_vars[key] = {"type": "room",
                                         "widget": txt,
                                         "value": default or ""}

            elif typ == "int":
                tk.Label(self.param_frame, text=label + ":",
                         bg=COLORS["bg_card"],
                         fg=COLORS["text_secondary"],
                         font=("微软雅黑", 11)).pack(side=tk.LEFT,
                                                    padx=(0, 2))
                ent = DarkEntry(self.param_frame, width=6)
                try:
                    ent.insert(0, str(default))
                except Exception:
                    pass
                ent.pack(side=tk.LEFT, padx=(0, 8))
                self._param_vars[key] = {"type": "int",
                                         "widget": ent,
                                         "value": default}

            elif typ == "choice":
                tk.Label(self.param_frame, text=label + ":",
                         bg=COLORS["bg_card"],
                         fg=COLORS["text_secondary"],
                         font=("微软雅黑", 11)).pack(side=tk.LEFT,
                                                    padx=(0, 2))
                # v6.6.3: 下拉框显示【中文标签】，内部存英文键值
                choices = f.get("choices", [])
                eng2cn = {c[0]: c[1] for c in choices}
                cn2eng = {c[1]: c[0] for c in choices}
                cn_vals = [c[1] for c in choices]
                init_cn = eng2cn.get(default, cn_vals[0] if cn_vals else "")
                disp_var = tk.StringVar(value=init_cn)
                try:
                    from widgets import RoundCombobox
                    cb = RoundCombobox(self.param_frame, textvariable=disp_var,
                                       values=cn_vals, width=11, height=26)
                except Exception:
                    cb = ttk.Combobox(self.param_frame, textvariable=disp_var,
                                      values=cn_vals, width=11, state="readonly")
                cb.pack(side=tk.LEFT, padx=(0, 8))
                self._param_vars[key] = {"type": "choice",
                                         "widget": cb,
                                         "var": disp_var,
                                         "cn2eng": cn2eng,
                                         "eng2cn": eng2cn,
                                         "value": default}

            elif typ == "bool":
                var = tk.BooleanVar(value=bool(default))
                chk = tk.Checkbutton(self.param_frame, text=label,
                                     variable=var,
                                     bg=COLORS["bg_card"],
                                     fg=COLORS["text_secondary"],
                                     selectcolor=COLORS["bg_input"],
                                     activebackground=COLORS["bg_card"],
                                     font=("微软雅黑", 11))
                chk.pack(side=tk.LEFT, padx=(0, 8))
                self._param_vars[key] = {"type": "bool",
                                         "widget": chk,
                                         "var": var,
                                         "value": default}

            elif typ == "groups":
                # 抢码任务组多选（只在 scope=select 时有意义）
                txt = tk.Label(self.param_frame, text="任务组: 全部",
                               bg=COLORS["bg_input"],
                               fg=COLORS["text_secondary"],
                               font=("微软雅黑", 11),
                               padx=8, pady=3, cursor="hand2")
                txt.pack(side=tk.LEFT, padx=(2, 8))
                txt.bind("<Button-1>",
                         lambda e, k=key, t=txt:
                         self._pick_rush_groups(k, t))
                self._param_vars[key] = {"type": "groups",
                                         "widget": txt,
                                         "value": list(default or [])}

    def _get_param_values(self):
        """从参数区收集当前值。"""
        out = {}
        for key, info in getattr(self, "_param_vars", {}).items():
            typ = info.get("type")
            if typ in ("accounts", "rooms", "room", "groups"):
                out[key] = info.get("value")
            elif typ == "int":
                try:
                    out[key] = int(info["widget"].get().strip())
                except Exception:
                    out[key] = 0
            elif typ == "choice":
                # v6.6.3: 界面显示中文，保存时转回英文键
                try:
                    disp = info["var"].get()
                    cn2eng = info.get("cn2eng") or {}
                    out[key] = cn2eng.get(disp, disp)
                except Exception:
                    out[key] = info.get("value")
            elif typ == "bool":
                try:
                    out[key] = info["var"].get()
                except Exception:
                    out[key] = info.get("value")
        return out

    def _set_param_values(self, params):
        """把参数回填到参数区（载入模板用）。"""
        for key, info in getattr(self, "_param_vars", {}).items():
            if key not in (params or {}):
                continue
            typ = info.get("type")
            val = params.get(key)
            if typ in ("accounts", "rooms", "room", "groups"):
                info["value"] = val
                self._refresh_param_label(key, typ, info)
            elif typ == "int":
                try:
                    w = info["widget"]
                    w.delete(0, tk.END)
                    w.insert(0, str(val))
                except Exception:
                    pass
            elif typ == "choice":
                # v6.6.3: 载入模板时英文键转中文显示
                try:
                    eng2cn = info.get("eng2cn") or {}
                    info["var"].set(eng2cn.get(val, val))
                except Exception:
                    pass
            elif typ == "bool":
                try:
                    info["var"].set(val)
                except Exception:
                    pass

    def _refresh_param_label(self, key, typ, info):
        """更新账户/房间标签的显示文本。"""
        w = info.get("widget")
        if w is None:
            return
        try:
            val = info.get("value")
            if typ == "accounts":
                if val:
                    w.config(text="账户: %d个" % len(val),
                             fg=COLORS["success"])
                else:
                    w.config(text="账户: 未选", fg=COLORS["warning"])
            elif typ == "rooms":
                if val:
                    w.config(text="直播间: %d个" % len(val),
                             fg=COLORS["success"])
                else:
                    w.config(text="直播间: 未选", fg=COLORS["warning"])
            elif typ == "room":
                if val:
                    w.config(text="直播间: 已选", fg=COLORS["success"])
                else:
                    w.config(text="直播间: 未选", fg=COLORS["warning"])
            elif typ == "groups":
                if val:
                    w.config(text="任务组: %d个" % len(val),
                             fg=COLORS["success"])
                else:
                    w.config(text="任务组: 全部",
                             fg=COLORS["text_secondary"])
        except Exception:
            pass

    def _apply_quick_time(self, hhmm):
        """常用时间快捷按钮。"""
        try:
            h, m = hhmm.split(":")
            self.schedule_hour.combo.config(state="readonly")
            self.schedule_minute.combo.config(state="readonly")
            self._tm_set(self.schedule_hour, h)
            self._tm_set(self.schedule_minute, m)
        except Exception:
            pass

    def import_current_params(self):
        """从对应页面读取当前参数（B+C 方案的兼容入口）。"""
        import schedule_params as sp
        task_type = self.task_type_var.get()
        params = sp.collect_current_params(self.app, task_type)
        self._set_param_values(params)
        self.log("✓ 已带入当前页面参数: " + sp.describe_params(task_type, params))

    # ---------- 账户/房间/任务组选择弹窗 ----------

    def _pick_accounts(self, key, label_widget):
        """弹窗多选账户。"""
        info = self._param_vars.get(key)
        if not info:
            return
        try:
            names = [a.get("name", "") for a in self.account_mgr.accounts]
        except Exception:
            names = []
        if not names:
            messagebox.showwarning("提示", "还没有任何账户，请先到「账户管理」添加",
                                   parent=self.winfo_toplevel())
            return
        cur = set(info.get("value") or [])
        self._open_multi_pick("选择账户", names, cur,
                              lambda sel: self._on_picked(key, "accounts", sel))

    def _pick_rooms(self, key, label_widget, multi=True):
        """弹窗选择直播间。"""
        info = self._param_vars.get(key)
        if not info:
            return
        try:
            rooms = [r.get("name", "") for r in self.app.room_mgr.rooms]
        except Exception:
            rooms = []
        if not rooms:
            messagebox.showwarning("提示", "还没有任何直播间，请先到「账户管理」添加",
                                   parent=self.winfo_toplevel())
            return
        cur = info.get("value")
        if multi:
            cur = set(cur or [])
        else:
            cur = set([cur]) if cur else set()
        typ = "rooms" if multi else "room"
        self._open_multi_pick("选择直播间", rooms, cur,
                              lambda sel: self._on_picked(key, typ, sel),
                              single=not multi)

    def _pick_rush_groups(self, key, label_widget):
        """弹窗选择抢码任务组。"""
        info = self._param_vars.get(key)
        if not info:
            return
        try:
            groups = [g.get("name", "") for g in self.app.rush_page.rush_groups]
        except Exception:
            groups = []
        if not groups:
            messagebox.showwarning("提示", "还没有任务组，请先在抢码页创建",
                                   parent=self.winfo_toplevel())
            return
        cur = set(info.get("value") or [])
        self._open_multi_pick("选择任务组", groups, cur,
                              lambda sel: self._on_picked(key, "groups", sel))

    def _open_multi_pick(self, title, items, selected, on_ok, single=False):
        """通用多选弹窗。"""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("360x420")
        win.configure(bg=COLORS["bg_card"])
        win.transient(self.winfo_toplevel())
        win.grab_set()

        tk.Label(win, text=title, bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 11, "bold")).pack(pady=(10, 6))

        body = tk.Frame(win, bg=COLORS["bg_card"])
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        vars_map = {}
        for it in items:
            var = tk.BooleanVar(value=it in selected)
            cb = tk.Checkbutton(body, text=it, variable=var,
                                bg=COLORS["bg_card"],
                                fg=COLORS["text_primary"],
                                selectcolor=COLORS["bg_input"],
                                activebackground=COLORS["bg_card"],
                                font=("微软雅黑", 11), anchor="w")
            cb.pack(fill=tk.X, pady=1)
            vars_map[it] = var

        foot = tk.Frame(win, bg=COLORS["bg_card"])
        foot.pack(fill=tk.X, padx=12, pady=(0, 10))

        def do_ok():
            sel = [it for it, v in vars_map.items() if v.get()]
            if single and len(sel) > 1:
                sel = sel[:1]
            on_ok(sel)
            win.destroy()

        DarkButton(foot, "确定", command=do_ok, width=90, height=30,
                   bg_color=COLORS["accent"],
                   text_color="#000000").pack(side=tk.LEFT)
        DarkButton(foot, "全选", width=70, height=30, bg_color="#9b59b6",
                   text_color="#ffffff",
                   command=lambda: [v.set(True) for v in vars_map.values()]
                   ).pack(side=tk.LEFT, padx=(6, 0))
        DarkButton(foot, "清空", width=70, height=30, bg_color="#7f8c8d",
                   text_color="#ffffff",
                   command=lambda: [v.set(False) for v in vars_map.values()]
                   ).pack(side=tk.LEFT, padx=(6, 0))
        DarkButton(foot, "取消", command=win.destroy, width=70, height=30,
                   bg_color=COLORS["danger"],
                   text_color="#ffffff").pack(side=tk.RIGHT)

    def _on_picked(self, key, typ, selections):
        """选择回调。"""
        info = self._param_vars.get(key)
        if not info:
            return
        if typ == "room":
            info["value"] = selections[0] if selections else ""
        else:
            info["value"] = list(selections)
        self._refresh_param_label(key, typ, info)

    # ---------- 模板 ----------

    def _refresh_template_combo(self, task_type=None):
        """刷新模板下拉框（只显示当前类型的模板）。"""
        import schedule_params as sp
        if task_type is None:
            task_type = self.task_type_var.get()
        try:
            names = list(sp.templates_of_type(task_type))
            self.tpl_load_combo["values"] = names
            if names and not self.tpl_load_var.get():
                self.tpl_load_var.set(names[0])
            elif names and self.tpl_load_var.get() not in names:
                self.tpl_load_var.set(names[0])
        except Exception:
            pass

    def save_current_as_template(self):
        """把当前参数存为模板。"""
        import schedule_params as sp
        name = ""
        try:
            name = self.tpl_save_name.get().strip()
        except Exception:
            pass
        if not name:
            messagebox.showwarning("提示", "请先填写模板名", parent=self.winfo_toplevel())
            return
        task_type = self.task_type_var.get()
        params = self._get_param_values()
        ok, err = sp.validate_params(task_type, params)
        if not ok:
            messagebox.showwarning("参数不完整", err, parent=self.winfo_toplevel())
            return
        if sp.upsert_template(name, task_type, params):
            self.log("✓ 模板「%s」已保存" % name)
            self._refresh_template_combo(task_type)
        else:
            messagebox.showerror("保存失败", "写入模板文件失败", parent=self.winfo_toplevel())

    def load_template_to_form(self):
        """把选定模板的参数载入到参数区。"""
        import schedule_params as sp
        try:
            name = self.tpl_load_var.get()
        except Exception:
            name = ""
        if not name:
            messagebox.showwarning("提示", "请先选择一个模板", parent=self.winfo_toplevel())
            return
        tpls = sp.load_templates()
        t = tpls.get(name)
        if not t:
            messagebox.showwarning("提示", "模板不存在", parent=self.winfo_toplevel())
            return
        ttype = t.get("type", "")
        if ttype != self.task_type_var.get():
            self._select_type_card(ttype)
        self._set_param_values(t.get("params") or {})
        self.log("✓ 已载入模板「%s」" % name)

    def delete_template_from_lib(self):
        """删除选定模板。"""
        import schedule_params as sp
        try:
            name = self.tpl_load_var.get()
        except Exception:
            name = ""
        if not name:
            return
        if not custom_askyesno("确认删除", "确定删除模板「%s」？" % name,
                               parent=self.winfo_toplevel()):
            return
        if sp.delete_template(name):
            self.log("✓ 模板「%s」已删除" % name)
            self._refresh_template_combo()

    def disable_all_tasks(self):
        """全部停用。"""
        for t in self.schedule_tasks:
            t["enabled"] = False
            t["status"] = "已取消"
        self.save_schedule()
        self.refresh_task_list()
        self.log("⏸ 已停用全部日程任务")


    def _on_type_changed(self, *args):
        """类型切换时：自动填名称 + 控制时间输入框"""
        task_type = self.task_type_var.get()
        self._auto_fill_name(task_type)

        if task_type == "rush":
            self.schedule_hour.combo.config(state="disabled")
            self.schedule_minute.combo.config(state="disabled")
            self.time_hint_label.config(text="（添加后立即启动抢码任务列表，各任务按自身领取时间运行）",
                                         fg=COLORS["warning"])
        elif task_type == "shutdown":
            self.schedule_hour.combo.config(state="disabled")
            self.schedule_minute.combo.config(state="disabled")
            self.time_hint_label.config(text="（关机时间在「定时关机」页面设置，此处无需填写）",
                                         fg=COLORS["warning"])
        else:
            self.schedule_hour.combo.config(state="readonly")
            self.schedule_minute.combo.config(state="readonly")
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
        """添加当前设置为日程任务（v6.6.1：含参数快照）。"""
        import schedule_params as sp

        task_type = self.task_type_var.get()
        params = self._get_param_values()

        # 参数校验
        ok, err = sp.validate_params(task_type, params)
        if not ok:
            messagebox.showwarning("参数不完整", err,
                                   parent=self.winfo_toplevel())
            return

        try:
            name = self.task_name_entry.get().strip()
        except Exception:
            name = ""
        if not name:
            name = sp.TASK_PARAM_SPEC.get(task_type, {}).get("icon", "") + "任务"
        task_name = name

        # 时间
        try:
            h = int(str(self._tm_get(self.schedule_hour)).strip() or "0")
            m = int(str(self._tm_get(self.schedule_minute)).strip() or "0")
            if h < 0 or h > 23 or m < 0 or m > 59:
                raise ValueError
        except ValueError:
            if task_type == "rush":
                h, m = 0, 0
            elif task_type == "shutdown":
                h, m = 0, 0
            else:
                messagebox.showwarning("提示", "请输入有效的时间（0-23时 / 0-59分）",
                                       parent=self.winfo_toplevel())
                return

        import uuid
        task_id = str(uuid.uuid4())[:8]

        icon = sp.TASK_PARAM_SPEC.get(task_type, {}).get("icon", "")
        type_name = {
            "rush": "⚡ 抢码", "watch": "📺 看播",
            "danmaku": "💬 弹幕", "shutdown": "⏻ 关机",
        }.get(task_type, task_type)

        scheduled_task = {
            "id": task_id,
            "name": task_name,
            "type": task_type,
            "type_name": type_name,
            "hour": h,
            "minute": m,
            "time_str": "%02d:%02d" % (h, m),
            "enabled": True,
            "last_run": "",
            "status": "等待中",
            # v6.6.1 核心：参数快照，执行时不再依赖其他页面
            "params": dict(params),
        }

        self.schedule_tasks.append(scheduled_task)
        self.save_schedule()
        self.refresh_task_list()
        self.log("✓ 已添加日程「%s」@ %s  %s"
                 % (task_name, scheduled_task["time_str"],
                    sp.describe_params(task_type, params)))

    def copy_schedule_task(self, task_id):
        """复制任务（v6.6.1 新增）：参数和时间完全复制，名称加「副本」。"""
        src_task = None
        for t in self.schedule_tasks:
            if t["id"] == task_id:
                src_task = t
                break
        if not src_task:
            return
        import uuid, copy
        new_task = copy.deepcopy(src_task)
        new_task["id"] = str(uuid.uuid4())[:8]
        new_task["name"] = src_task.get("name", "") + "副本"
        new_task["last_run"] = ""
        new_task["status"] = "等待中"
        self.schedule_tasks.append(new_task)
        self.save_schedule()
        self.refresh_task_list()
        self.log("⧉ 已复制日程「%s」" % src_task.get("name", ""))

    def run_task_now(self, task_id):
        """行内「立即执行」按钮。"""
        for t in self.schedule_tasks:
            if t["id"] == task_id:
                self.execute_task(t, manual=True)
                return

    def toggle_task_enabled(self, task_id):
        """行内「启用/停用」切换。"""
        for t in self.schedule_tasks:
            if t["id"] == task_id:
                t["enabled"] = not t.get("enabled", True)
                t["status"] = "等待中" if t["enabled"] else "已取消"
                self.save_schedule()
                self.refresh_task_list()
                self.log("%s 日程「%s」"
                         % ("✅ 已启用" if t["enabled"] else "⏸ 已停用",
                            t.get("name", "")))
                return

    def delete_one_task(self, task_id):
        """行内「删除」按钮。"""
        t = next((x for x in self.schedule_tasks if x["id"] == task_id), None)
        if not t:
            return
        if not custom_askyesno("确认删除",
                               "确定删除日程「%s」？" % t.get("name", ""),
                               parent=self.winfo_toplevel()):
            return
        self.schedule_tasks = [x for x in self.schedule_tasks
                               if x["id"] != task_id]
        self.schedule_task_stop_flags.pop(task_id, None)
        self.save_schedule()
        self.refresh_task_list()
        self.log("🗑 已删除日程「%s」" % t.get("name", ""))

    def refresh_task_list(self):
        """刷新任务列表（v6.6.7 用固定宽度列，保证表头与数据行严格对齐）。

        为什么不用 grid：grid 的 minsize 只是最小值，实际宽度会被
        Label 文本内容撑开，导致表头和数据行列宽不一致（实测 7 列全错位）。
        改用「每列一个固定 px 宽的 Frame + pack(left)」，宽度完全可控。
        """
        import schedule_params as sp

        for w in self.task_list_frame.winfo_children():
            w.destroy()

        n = len(self.schedule_tasks)
        try:
            enabled_n = sum(1 for t in self.schedule_tasks if t.get("enabled"))
            self.task_count_label.config(
                text="共 %d 项（启用 %d）" % (n, enabled_n))
        except Exception:
            pass

        if not self.schedule_tasks:
            tk.Label(self.task_list_frame,
                     text="还没有日程任务  ·  选好类型、配好参数、设好时间，点「＋ 添加」即可",
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 11), justify=tk.CENTER).pack(pady=40)
            return

        # 固定列宽（px）：总 943px 可用，各列合计约 930px
        # v6.6.7: 上次执行需容纳 "10-29 13:37"（约 120px），给 130px
        COLS = [
            ("", 12), ("状态", 96), ("类型", 82), ("名称", 100),
            ("时间", 70), ("参数", 96), ("上次执行", 130), ("操作", 200),
        ]
        ROW_PADY = 12   # v6.6.8: 行内上下间距加大（用户要求）

        def make_cell(parent, px, bg):
            """创建一个固定宽度的单元格容器（只锁宽度，高度自适应）。"""
            f = tk.Frame(parent, bg=bg, width=px)
            f.pack(side=tk.LEFT, fill=tk.Y)
            # 关键：只锁宽度方向，高度交给内部控件撑开
            f.pack_propagate(False)
            # 让内部控件撑开高度
            f.configure(height=52)
            return f

        # ---- 表头 ----
        head = tk.Frame(self.task_list_frame, bg=COLORS["bg_input"])
        head.pack(fill=tk.X, pady=(0, 6))
        for txt, px in COLS:
            cell = make_cell(head, px, COLORS["bg_input"])
            tk.Label(cell, text=txt, bg=COLORS["bg_input"],
                     fg=COLORS["text_secondary"],
                     font=("微软雅黑", 11, "bold"),
                     anchor=tk.W).pack(side=tk.LEFT, padx=(4, 0), pady=10)

        # ---- 数据行 ----
        for idx, task in enumerate(self.schedule_tasks):
            try:
                is_sel = task["id"] in self.selected_ids
                if is_sel:
                    bg = "#2d4a63"
                else:
                    bg = COLORS["bg_card"] if idx % 2 == 0 else COLORS["bg_input"]

                row = tk.Frame(self.task_list_frame, bg=bg)
                row.pack(fill=tk.X, pady=3)
                tid_row = task["id"]

                # 列0：选中标记条
                cell0 = make_cell(row, COLS[0][1], bg)
                mark = tk.Label(cell0, text="", bg=COLORS["accent"] if is_sel else bg,
                                width=1)
                mark.pack(fill=tk.Y, padx=(1, 0))
                for _w in (row, mark, cell0):
                    try:
                        _w.bind("<Button-1>",
                                lambda e, t=tid_row: self._toggle_row_select(t))
                        _w.configure(cursor="hand2")
                    except Exception:
                        pass

                # 列1：状态
                if not task.get("enabled"):
                    stxt, sfg = "已停用", COLORS["text_muted"]
                else:
                    stxt = task.get("status", "等待中")
                    if stxt == "执行中":
                        sfg = COLORS["accent"]
                    elif "启动失败" in stxt or stxt == "失败":
                        sfg = COLORS["danger"]
                    elif stxt in ("已完成", "已结束"):
                        sfg = COLORS["success"]
                    elif "已跳过" in stxt:
                        sfg = COLORS["warning"]
                    else:
                        sfg = COLORS["text_secondary"]
                cell1 = make_cell(row, COLS[1][1], bg)
                tk.Label(cell1, text="● " + stxt, bg=bg, fg=sfg,
                         font=("微软雅黑", 11), anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列2：类型
                cell2 = make_cell(row, COLS[2][1], bg)
                tk.Label(cell2, text=task.get("type_name", ""), bg=bg,
                         fg=COLORS["text_primary"], font=("微软雅黑", 11),
                         anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列3：任务名称
                cell3 = make_cell(row, COLS[3][1], bg)
                tk.Label(cell3, text=task.get("name", "")[:9], bg=bg,
                         fg=COLORS["text_primary"],
                         font=("微软雅黑", 11, "bold"), anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列4：执行时间
                cell4 = make_cell(row, COLS[4][1], bg)
                tk.Label(cell4, text=task.get("time_str", "--:--"), bg=bg,
                         fg=COLORS["accent"],
                         font=("Consolas", 11, "bold"), anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列5：参数摘要
                desc = sp.describe_params(task.get("type", ""),
                                          task.get("params") or {})
                if not task.get("params"):
                    desc = "旧任务"
                cell5 = make_cell(row, COLS[5][1], bg)
                tk.Label(cell5, text=desc[:10], bg=bg,
                         fg=COLORS["text_secondary"], font=("微软雅黑", 10),
                         anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列6：上次执行
                lr = task.get("last_run", "") or "-"
                if lr != "-":
                    lr = lr[5:16] if len(lr) > 16 else lr
                cell6 = make_cell(row, COLS[6][1], bg)
                tk.Label(cell6, text=lr, bg=bg, fg=COLORS["text_muted"],
                         font=("Consolas", 10), anchor=tk.W
                         ).pack(side=tk.LEFT, padx=(4, 0), pady=ROW_PADY)

                # 列7：操作按钮
                cell7 = make_cell(row, COLS[7][1], bg)
                ops = tk.Frame(cell7, bg=bg)
                ops.pack(side=tk.LEFT, padx=(2, 0))
                tid = task["id"]
                DarkButton(ops, "✏", command=lambda i=tid: self._edit_task_by_id(i),
                           width=28, height=22, bg_color="#3498db",
                           text_color="#ffffff", compact=True,
                           tip="编辑该任务的参数").pack(side=tk.LEFT, padx=1)
                DarkButton(ops, "⧉", command=lambda i=tid: self.copy_schedule_task(i),
                           width=28, height=22, bg_color="#8e44ad",
                           text_color="#ffffff", compact=True,
                           tip="复制该任务（参数和时间一起复制）").pack(side=tk.LEFT, padx=1)
                DarkButton(ops, "▶", command=lambda i=tid: self.run_task_now(i),
                           width=28, height=22, bg_color=COLORS["success"],
                           text_color="#ffffff", compact=True,
                           tip="立即执行该任务").pack(side=tk.LEFT, padx=1)
                en_txt = "⏸" if task.get("enabled") else "▶"
                en_bg = "#e67e22" if task.get("enabled") else "#27ae60"
                DarkButton(ops, en_txt,
                           command=lambda i=tid: self.toggle_task_enabled(i),
                           width=28, height=22, bg_color=en_bg,
                           text_color="#ffffff", compact=True,
                           tip="启用/停用该任务").pack(side=tk.LEFT, padx=1)
                DarkButton(ops, "×", command=lambda i=tid: self.delete_one_task(i),
                           width=28, height=22, bg_color=COLORS["danger"],
                           text_color="#ffffff", compact=True,
                           tip="删除该任务").pack(side=tk.LEFT, padx=1)
            except Exception as e:
                self.log("渲染任务行异常: %s" % e)


    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def _toggle_row_select(self, task_id):
        """点击行切换选中状态（v6.6.5，替代已移除的复选框）。"""
        if task_id in self.selected_ids:
            self.selected_ids.discard(task_id)
        else:
            self.selected_ids.add(task_id)
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
            messagebox.showwarning("提示", "请先点击要删除的任务行（整行变蓝表示已选中）", parent=self.winfo_toplevel())
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
                 font=("微软雅黑", 15, "bold")).pack(pady=(15, 10))

        # 任务名称
        name_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        name_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(name_frame, text="任务名称:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        name_entry = DarkEntry(name_frame, width=22)
        name_entry.insert(0, task["name"])
        name_entry.pack(side=tk.LEFT, padx=(10, 0))

        # 任务类型
        type_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        type_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(type_frame, text="任务类型:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        edit_type_var = tk.StringVar(value=task["type"])
        type_names = {"watch": "📺 看播", "danmaku": "💬 弹幕", "rush": "⚡ 抢码", "shutdown": "⏻ 关机"}
        for val, label in type_names.items():
            ttk.Radiobutton(type_frame, text=label, variable=edit_type_var, value=val,
                            style="Dark.TRadiobutton").pack(side=tk.LEFT, padx=(6, 0))

        # 执行时间
        time_frame = tk.Frame(edit_win, bg=COLORS["bg_card"])
        time_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(time_frame, text="执行时间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                 font=("微软雅黑", 11)).pack(side=tk.LEFT)
        hour_entry = DarkEntry(time_frame, width=5)
        hour_entry.insert(0, f"{task.get('hour', 20):02d}" if task.get("hour", -1) >= 0 else "20")
        hour_entry.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(time_frame, text=":", bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                 font=("微软雅黑", 15, "bold")).pack(side=tk.LEFT)
        minute_entry = DarkEntry(time_frame, width=5)
        minute_entry.insert(0, f"{task.get('minute', 0):02d}" if task.get("minute", -1) >= 0 else "00")
        minute_entry.pack(side=tk.LEFT, padx=(0, 0))
        time_hint = tk.Label(time_frame, text="", bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                             font=("微软雅黑", 11))
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
        """启动看播（v6.6.1：优先用任务自带参数快照，不依赖当前页面）。"""
        try:
            self.app._ensure_page_built("watch")
            wp = getattr(self.app, 'watch_page', None)
            if wp is None:
                msg = ("✗ [日程] 看播页未构建，无法启动「%s」"
                       % task.get('name', ''))
                self.log(msg)
                self.sync_log_to_modules(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
                return

            params = task.get("params") or {}

            # ---- 关键：把参数注入看播页，覆盖当前 UI 状态 ----
            if params:
                applied = self._apply_watch_params(wp, params)
                if not applied:
                    task["status"] = "启动失败"
                    self.refresh_task_list()
                    return
            else:
                self.log("  ⚠ 该任务无参数快照（旧任务），使用看播页当前设置")

            wp.start_watch()

            if getattr(wp, 'running', False):
                msg = ("✓ [日程] 看播任务「%s」已启动  %s"
                       % (task.get('name', ''),
                          ("(%d账户/%d房间/%s分钟)"
                           % (len(params.get("accounts") or []),
                              len(params.get("rooms") or []),
                              params.get("duration_minutes", 0)))
                          if params else ""))
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(wp, 'log'):
                    wp.log(msg)
            else:
                msg = ("✗ [日程] 看播任务「%s」启动失败："
                       "请检查任务的账户/直播间参数是否有效"
                       % task.get('name', ''))
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(wp, 'log'):
                    wp.log(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
        except Exception as e:
            import traceback
            msg = f"✗ [日程] 启动看播失败: {e}"
            self.log(msg)
            self.log(traceback.format_exc()[:300])
            self.sync_log_to_modules(msg)
            task["status"] = "启动失败"
            try:
                self.refresh_task_list()
            except Exception:
                pass

    def _apply_watch_params(self, wp, params):
        """把参数快照注入看播页（v6.6.1 核心）。返回是否成功。"""
        try:
            accounts = params.get("accounts") or []
            rooms = params.get("rooms") or []
            duration = params.get("duration_minutes")
            hb = params.get("heartbeat_interval")

            if not accounts:
                self.log("  ✗ 任务参数里没有账户")
                return False
            if not rooms:
                self.log("  ✗ 任务参数里没有直播间")
                return False

            # 1) 账户勾选：按参数精确设置
            for name, var in getattr(wp, "account_vars", {}).items():
                try:
                    var.set(name in accounts)
                except Exception:
                    pass
            # 若无匹配账户（账户被删），提示
            existing = set(getattr(wp, "account_vars", {}).keys())
            missing = [a for a in accounts if a not in existing]
            if missing:
                self.log("  ⚠ 以下账户已不存在，将跳过: %s" % ", ".join(missing))
            if len(missing) >= len(accounts):
                self.log("  ✗ 任务参数里的账户全部不存在")
                return False

            # 2) 直播间：确保选择框里有该房间并选中
            self._apply_watch_rooms(wp, rooms)

            # 3) 时长
            if duration is not None:
                try:
                    wp.duration_var.set(int(duration))
                except Exception:
                    pass
            # 4) 心跳间隔
            if hb is not None:
                try:
                    wp.interval_var.set(int(hb))
                except Exception:
                    pass

            self.log("  已注入参数: %d账户 / %d房间 / %s分钟 / %s秒心跳"
                     % (len(accounts), len(rooms), duration, hb))
            return True
        except Exception as e:
            self.log("  ✗ 注入看播参数异常: %s" % e)
            return False

    def _apply_watch_rooms(self, wp, room_ids):
        """确保看播页选中指定的直播间（必要时动态添加选择框）。"""
        try:
            # 找到房间对象
            rooms = []
            for rid in room_ids:
                r = next((x for x in self.app.room_mgr.rooms
                          if str(x.get("id")) == str(rid)), None)
                if r:
                    rooms.append(r)
            if not rooms:
                self.log("  ⚠ 参数里的直播间都不存在")
                return

            bars = getattr(wp, "watch_room_bars", [])
            names_wanted = [r.get("name", "") for r in rooms]

            # 已有的选择框：逐个设置为目标房间
            for i, name in enumerate(names_wanted):
                if i < len(bars):
                    bar, combo, del_btn = bars[i]
                    try:
                        combo.set(name)
                    except Exception:
                        pass
                else:
                    # 需要新增选择框
                    try:
                        if hasattr(wp, "add_room_bar"):
                            wp.add_room_bar()
                    except Exception:
                        pass

            # 刷新后重新尝试设置
            bars = getattr(wp, "watch_room_bars", [])
            for i, name in enumerate(names_wanted):
                if i < len(bars):
                    bar, combo, del_btn = bars[i]
                    try:
                        combo.set(name)
                    except Exception:
                        pass
        except Exception as e:
            self.log("  设置直播间异常: %s" % e)

    def _start_danmaku_safe(self, task):
        """启动弹幕（v6.6.1：优先用任务参数快照）。"""
        try:
            params = task.get("params") or {}
            if params:
                ok = self._apply_danmaku_params(params)
                if not ok:
                    task["status"] = "启动失败"
                    self.refresh_task_list()
                    return
            else:
                self.log("  ⚠ 该任务无参数快照（旧任务），使用弹幕页当前设置")

            if not hasattr(self.app, 'start_sending'):
                msg = "✗ [日程] 主程序缺少 start_sending 方法"
                self.log(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
                return

            before = bool(getattr(self.app, 'running', False))
            self.app.start_sending()
            after = bool(getattr(self.app, 'running', False))

            if after and not before:
                msg = f"✓ [日程] 弹幕任务「{task.get('name','')}」已启动"
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(self.app, 'log'):
                    self.app.log(msg)
            else:
                msg = (f"✗ [日程] 弹幕任务「{task.get('name','')}」启动失败："
                       "请检查账户/直播间/弹幕内容是否齐全")
                self.log(msg)
                self.sync_log_to_modules(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
        except Exception as e:
            msg = f"✗ [日程] 启动弹幕失败: {e}"
            self.log(msg)
            self.sync_log_to_modules(msg)
            task["status"] = "启动失败"
            try:
                self.refresh_task_list()
            except Exception:
                pass

    def _apply_danmaku_params(self, params):
        """把参数注入弹幕页。返回是否成功。"""
        try:
            accounts = params.get("accounts") or []
            room = params.get("room")
            mode = params.get("account_mode")
            cnt = params.get("max_send_count")

            if not accounts:
                self.log("  ✗ 弹幕任务参数里没有账户")
                return False

            # 账户勾选
            try:
                for name, var in getattr(self.app, "danmaku_account_vars",
                                         {}).items():
                    var.set(name in accounts)
            except Exception:
                pass

            # 发送模式
            if mode:
                try:
                    self.app.account_mode_var.set(mode)
                except Exception:
                    pass

            # 直播间：弹幕页用 room_combo 选择「房间名称」，不是 room_id
            if room:
                try:
                    target = None
                    for r in self.app.room_mgr.rooms:
                        if str(r.get("id")) == str(room):
                            target = r.get("name", "")
                            break
                    if target and hasattr(self.app, "room_combo"):
                        self.app.room_combo.set(target)
                        self.log("  已设置弹幕直播间: %s" % target)
                    elif target is None:
                        self.log("  ⚠ 参数里的直播间 %s 不存在" % room)
                except Exception as e:
                    self.log("  设置直播间异常: %s" % e)

            # 条数
            if cnt is not None:
                try:
                    self.app.max_send_entry.delete(0, tk.END)
                    self.app.max_send_entry.insert(0, str(cnt))
                except Exception:
                    pass

            self.log("  已注入弹幕参数: %d账户 / 房间%s / %s条"
                     % (len(accounts), room, cnt))
            return True
        except Exception as e:
            self.log("  ✗ 注入弹幕参数异常: %s" % e)
            return False

    def _start_rush_safe(self, task):
        """启动抢码（v6.6.1：只负责启动，抢码本身自带定时）。

        用户明确要求：抢码任务本身是自动定时的，
        日程只需负责「启动任务」即可：
          · 旧模式：启动任务栏内全部任务，或仅选中的
          · 新模式：启动所有任务组，或仅选中的组
        """
        try:
            rp = getattr(self.app, 'rush_page', None)
            if rp is None:
                msg = "✗ [日程] 抢码页不存在"
                self.log(msg)
                task["status"] = "启动失败"
                self.refresh_task_list()
                return

            params = task.get("params") or {}
            scope = params.get("start_scope", "all")
            groups = params.get("selected_groups") or []
            mode = params.get("rush_mode", "")

            started = False

            if groups:
                # 指定了任务组 -> 只启动这些
                for gname in groups:
                    try:
                        g = next((x for x in rp.rush_groups
                                  if x.get("name") == gname), None)
                        if g:
                            rp.nm_start_group(g.get("group_id", ""))
                            started = True
                    except Exception as e:
                        self.log("  启动任务组「%s」失败: %s" % (gname, e))
                if started:
                    msg = ("✓ [日程] 抢码任务「%s」已启动 %d 个任务组"
                           % (task.get('name', ''), len(groups)))
            else:
                # 全部启动：优先新模式的"启动全部"
                if hasattr(rp, "nm_start_all_groups"):
                    try:
                        rp.nm_start_all_groups()
                        started = True
                    except Exception as e:
                        self.log("  nm_start_all_groups 失败: %s" % e)
                if not started and hasattr(rp, "start_all_scheduled_tasks"):
                    try:
                        rp.start_all_scheduled_tasks()
                        started = True
                    except Exception as e:
                        self.log("  start_all_scheduled_tasks 失败: %s" % e)
                if started:
                    msg = ("✓ [日程] 抢码任务「%s」已启动全部任务/任务组"
                           % task.get('name', ''))

            if started:
                self.log(msg)
                self.sync_log_to_modules(msg)
                if hasattr(rp, 'log'):
                    rp.log(msg)
                task["status"] = "已完成"
            else:
                msg = ("✗ [日程] 抢码任务「%s」启动失败：未找到可启动的任务组"
                       % task.get('name', ''))
                self.log(msg)
                task["status"] = "启动失败"
            self.refresh_task_list()
        except Exception as e:
            msg = f"✗ [日程] 启动抢码失败: {e}"
            self.log(msg)
            task["status"] = "启动失败"
            try:
                self.refresh_task_list()
            except Exception:
                pass

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
                     font=("微软雅黑", 15, "bold")).pack(pady=(20, 10))
            tk.Label(confirm_win, text=f"任务「{task['name']}」时间到", bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=("微软雅黑", 11)).pack()
            countdown_label = tk.Label(confirm_win, text="60秒后自动关机...", bg=COLORS["bg_card"],
                                       fg=COLORS["warning"], font=("微软雅黑", 15, "bold"))
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
                "hour": str(self._tm_get(self.schedule_hour)),
                "minute": str(self._tm_get(self.schedule_minute)),
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
                self._tm_set(self.schedule_hour, h)
                self._tm_set(self.schedule_minute, m)
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
