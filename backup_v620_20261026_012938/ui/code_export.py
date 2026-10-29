# -*- coding: utf-8 -*-
"""兑换码导出页面。"""

import csv, json, os, time
import re, threading
from storage import atomic_write_json
import tkinter as tk
from tkinter import ttk, messagebox

from config import COLORS, CODE_EXPORT_FILE, ACCOUNTS_FILE
from tasks_config import VERSION_DEFAULT_ACT_ID
from storage import (load_redeem_codes, save_redeem_code, update_redeem_code_status,
                     delete_redeem_code, clear_redeem_codes, extract_redeem_codes, _ensure_code_dir)
from bili_api import get_award_record, cookies_from_account
from widgets import DarkButton, DarkEntry, custom_askyesno

# ========== 兑换码导出模块 ==========
class CodeExportFrame(tk.Frame):
    """兑换码导出页面"""
    def __init__(self, parent, account_mgr=None, room_mgr=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.selected_ids = set()
        self.current_activity_filter = "全部活动"
        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self, bg=COLORS["bg_card"], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🎁 兑换码导出", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(header, text="从领取记录导入兑换码，支持复制和导出",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 20))

        # 操作按钮栏
        btn_bar = tk.Frame(self, bg=COLORS["bg_card"], height=56)
        btn_bar.pack(fill=tk.X, pady=(0, 2))
        btn_bar.pack_propagate(False)

        btn_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        btn_frame.pack(side=tk.LEFT, padx=15, pady=8)

        self.refresh_btn = DarkButton(btn_frame, text="🔄 刷新列表", command=self.refresh_list, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.import_btn = DarkButton(btn_frame, text="📥 从领取记录导入", command=self.import_from_records, bg_color="#FF8F00", text_color="#FFFFFF", height=32)
        self.import_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_selected_btn = DarkButton(btn_frame, text="📋 复制选中", command=self.copy_selected, bg_color=COLORS["accent"], text_color="#000000", height=32)
        self.copy_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_all_btn = DarkButton(btn_frame, text="📋 复制全部", command=self.copy_all, bg_color=COLORS["accent"], text_color="#000000", height=32)
        self.copy_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_btn = DarkButton(btn_frame, text="💾 导出TXT", command=self.export_txt, bg_color="#2E7D32", text_color="#FFFFFF", height=32)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_csv_btn = DarkButton(btn_frame, text="📊 导出CSV", command=self.export_csv, bg_color="#1565C0", text_color="#FFFFFF", height=32)
        self.export_csv_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.delete_selected_btn = DarkButton(btn_frame, text="🗑 删除选中", command=self.delete_selected, bg_color="#C62828", text_color="#FFFFFF", height=32)
        self.delete_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = DarkButton(btn_frame, text="🧹 清空全部", command=self.clear_all, bg_color="#616161", text_color="#FFFFFF", height=32)
        self.clear_btn.pack(side=tk.LEFT)

        # 活动筛选下拉框
        filter_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=(0, 15))
        
        tk.Label(filter_frame, text="活动筛选:", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        from tkinter import ttk
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        self.activity_filter_var = tk.StringVar(value="全部活动")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Filter.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        self.activity_filter_combo = ttk.Combobox(filter_frame, textvariable=self.activity_filter_var,
                                                    values=activity_list, state="readonly",
                                                    font=("微软雅黑", 10), width=18,
                                                    style='Filter.TCombobox')
        self.activity_filter_combo.pack(side=tk.LEFT)
        self.activity_filter_combo.bind("<<ComboboxSelected>>", self._on_activity_filter_change)

        # 统计信息
        self.stats_label = tk.Label(btn_bar, text="", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 10))
        self.stats_label.pack(side=tk.RIGHT, padx=20)

        # 列表区域
        list_container = tk.Frame(self, bg=COLORS["bg_card"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # 表头
        header_frame = tk.Frame(list_container, bg=COLORS["bg_input"], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        cols = [
            ("选择", 50),
            ("ID", 50),
            ("领取时间", 160),
            ("任务名称", 250),
            ("账户", 120),
            ("兑换码", 300),
            ("字段", 100),
            ("状态", 80),
            ("操作", 150),
        ]
        self.col_widths = [w for _, w in cols]
        for text, width in cols:
            tk.Label(header_frame, text=text, bg=COLORS["bg_input"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"),
                     width=width // 8, anchor="w").pack(side=tk.LEFT, padx=4, pady=8)

        # 可滚动列表
        self.canvas = tk.Canvas(list_container, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLORS["bg_dark"])

        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", 
                                  tags="scroll_frame")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("scroll_frame", width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮（P2-O: 只绑定canvas本身，不全局劫持）
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_activity_filter_change(self, event=None):
        """活动筛选变更"""
        self.current_activity_filter = self.activity_filter_var.get()
        self.refresh_list()
    
    def _get_filtered_records(self, records=None):
        """获取筛选后的记录"""
        if records is None:
            records = self.records
        if self.current_activity_filter == "全部活动":
            return records
        # P2-N: 筛选条件也剥掉"激励计划"后缀，与task_name构造逻辑一致
        import re
        filter_name = re.sub(r'版本激励计划.*$', '', self.current_activity_filter)
        filter_name = re.sub(r'激励计划.*$', '', filter_name).strip()
        # 根据task_name前缀筛选（task_name格式为"活动名称 奖励名称"）
        filtered = []
        for r in records:
            task_name = r.get("task_name", "")
            if task_name.startswith(filter_name):
                filtered.append(r)
        return filtered

    def import_from_records(self):
        """从领取记录导入所有兑换码（选择活动或全部导入）"""
        # 创建活动选择对话框
        dialog = tk.Toplevel(self)
        dialog.title("选择活动")
        dialog.geometry("360x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 360) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="请选择要导入兑换码的活动：", 
                 font=("微软雅黑", 11), bg=COLORS["bg_dark"], fg=COLORS["text_primary"]).pack(pady=(20, 10))
        
        # 活动列表（从VERSION_DEFAULT_ACT_ID获取）
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        activity_var = tk.StringVar(value=activity_list[0])
        
        from tkinter import ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Activity.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        activity_combo = ttk.Combobox(dialog, textvariable=activity_var, 
                                        values=activity_list, state="readonly",
                                        font=("微软雅黑", 11), width=25,
                                        style='Activity.TCombobox')
        activity_combo.pack(pady=10)
        
        result = {"selected": None}
        
        def on_confirm():
            result["selected"] = activity_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS["bg_dark"])
        btn_frame.pack(pady=20)
        
        DarkButton(btn_frame, text="确定", command=on_confirm, bg_color=COLORS["accent"], text_color="#000000", height=32).pack(side=tk.LEFT, padx=10)
        
        DarkButton(btn_frame, text="取消", command=on_cancel, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32).pack(side=tk.LEFT, padx=10)
        
        dialog.configure(bg=COLORS["bg_dark"])
        self.wait_window(dialog)
        
        selected_activity = result["selected"]
        if not selected_activity:
            return
        
        # 根据选择获取act_id列表
        if selected_activity == "全部活动":
            act_id_list = list(VERSION_DEFAULT_ACT_ID.values())
            activity_names = list(VERSION_DEFAULT_ACT_ID.keys())
        else:
            act_id_list = [VERSION_DEFAULT_ACT_ID.get(selected_activity, "")]
            activity_names = [selected_activity]
        
        # 过滤掉空的act_id
        valid_pairs = [(name, aid) for name, aid in zip(activity_names, act_id_list) if aid]
        if not valid_pairs:
            messagebox.showwarning("提示", "未找到有效的活动ID")
            return

        # 获取所有账户
        accounts = []
        try:
            if self.account_mgr and hasattr(self.account_mgr, 'accounts'):
                accounts = self.account_mgr.accounts
            else:
                # 从文件读取（使用统一的ACCOUNTS_FILE路径）
                if os.path.exists(str(ACCOUNTS_FILE)):
                    with open(str(ACCOUNTS_FILE), "r", encoding="utf-8") as f:
                        accounts = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"读取账户失败: {e}")
            return

        if not accounts:
            messagebox.showwarning("提示", "没有可用的账户，请先导入账户")
            return

        # 遍历所有活动和账户，调用领取记录API（后台线程执行，避免卡住UI）
        self._import_running = True
        if hasattr(self, 'import_btn'):
            self.import_btn.config(state=tk.DISABLED, text="导入中...")
        
        def _do_import():
            total_imported = 0
            total_skipped = 0
            account_results = []
            try:
                for activity_name, act_id in valid_pairs:
                    for acc in accounts:
                        try:
                            cookies = cookies_from_account(acc)
                            # P2-U: 分页获取所有领取记录，每页50条
                            all_records = []
                            page = 1
                            max_pages = 10  # 安全上限，防止无限循环
                            while page <= max_pages:
                                record_data, record_msg = get_award_record(act_id, cookies, page=page, page_size=50)
                                if record_data and record_data.get("list"):
                                    record_list = record_data["list"]
                                    all_records.extend(record_list)
                                    # P2-U: 检查是否还有下一页
                                    has_more = record_data.get("has_more", False)
                                    total = record_data.get("total", 0)
                                    if not has_more and len(all_records) >= total:
                                        break
                                    if len(record_list) < 50:
                                        break
                                    page += 1
                                    time.sleep(0.5)  # P2-U: 请求节流，避免触发-702
                                else:
                                    break
                            
                            if all_records:
                                account_codes = 0
                                for record in all_records:
                                    codes = extract_redeem_codes(record)
                                    for code_info in codes:
                                        record_activity_name = record.get("activity_name", "")
                                        award_name = record.get("award_name", "未知奖励")
                                        if record_activity_name:
                                            record_activity_name = re.sub(r'版本激励计划.*$', '', record_activity_name)
                                            record_activity_name = re.sub(r'激励计划.*$', '', record_activity_name)
                                            record_activity_name = record_activity_name.strip()
                                        task_name = f"{record_activity_name} {award_name}" if record_activity_name else award_name
                                        ok_save, save_msg = save_redeem_code(
                                            task_name, acc.get("name", "未知"), record,
                                            task_period="", task_type=record.get("type", "")
                                        )
                                        if ok_save:
                                            total_imported += 1
                                            account_codes += 1
                                        else:
                                            total_skipped += 1
                                account_results.append(f"  [{activity_name}] {acc['name']}: 导入 {account_codes} 个，共 {len(all_records)} 条记录（{page}页）")
                            else:
                                account_results.append(f"  [{activity_name}] {acc['name']}: 无领取记录 ({record_msg})")
                            # P2-U: 账户之间也加节流
                            time.sleep(0.3)
                        except Exception as e:
                            account_results.append(f"  [{activity_name}] {acc['name']}: 异常 - {e}")
            finally:
                self._import_running = False
            self.after(0, lambda: self._on_import_finished(total_imported, total_skipped, account_results))
        
        threading.Thread(target=_do_import, daemon=True).start()
    
    def _on_import_finished(self, total_imported, total_skipped, account_results):
        """导入完成回调（主线程执行）"""
        self.refresh_list()
        if hasattr(self, 'import_btn'):
            self.import_btn.config(state=tk.NORMAL, text="从领取记录导入")
        result_msg = f"导入完成！\n\n共导入 {total_imported} 个兑换码\n跳过 {total_skipped} 个（重复）\n\n详情：\n" + "\n".join(account_results)
        messagebox.showinfo("导入结果", result_msg)
    def refresh_list(self):
        """刷新兑换码列表"""
        # 清空现有内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.selected_ids.clear()

        all_records = load_redeem_codes()
        self.records = all_records
        records = self._get_filtered_records(all_records)

        # 更新统计（显示筛选后的数量和总数）
        total = len(records)
        total_all = len(all_records)
        unused = sum(1 for r in records if r.get("status") == "未使用")
        used = sum(1 for r in records if r.get("status") == "已使用")
        if self.current_activity_filter == "全部活动":
            self.stats_label.config(text=f"共 {total} 条 | 未使用 {unused} | 已使用 {used}")
        else:
            self.stats_label.config(text=f"筛选 {total}/{total_all} 条 | 未使用 {unused} | 已使用 {used}")

        if not records:
            empty_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_dark"])
            empty_frame.pack(fill=tk.X, pady=40)
            tk.Label(empty_frame, text="📭 暂无兑换码记录", bg=COLORS["bg_dark"],
                     fg=COLORS["text_muted"], font=("微软雅黑", 14)).pack()
            tk.Label(empty_frame, text="点击「从领取记录导入」获取兑换码",
                     bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 10)).pack(pady=(8, 0))
            return

        for i, record in enumerate(records):
            try:
                row_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"])
                row_frame.pack(fill=tk.X, pady=1)

                # 确保record是字典
                if not isinstance(record, dict):
                    tk.Label(row_frame, text=f"记录格式错误: {str(record)[:50]}", bg=row_frame["bg"],
                             fg="#FF5252", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10, pady=6)
                    continue

                rec_id = record.get("id", i + 1)
                rec_time = record.get("time", "")
                rec_task = record.get("task_name", "")
                if record.get("task_period"):
                    rec_task = f"[{record['task_period']}] {rec_task}"
                rec_account = record.get("account", "")
                rec_code = record.get("redeem_code", "")
                rec_field = record.get("code_field", "")
                rec_status = record.get("status", "未使用")

                # 选择框
                var = tk.BooleanVar(value=False)
                cb = tk.Checkbutton(row_frame, variable=var, bg=row_frame["bg"],
                                     activebackground=row_frame["bg"], command=lambda rid=rec_id, v=var: self._toggle_select(rid, v))
                cb.pack(side=tk.LEFT, padx=(10, 5), pady=6)

                # ID
                tk.Label(row_frame, text=str(rec_id), bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=4, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 时间
                tk.Label(row_frame, text=rec_time, bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=18, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 任务名称
                tk.Label(row_frame, text=rec_task, bg=row_frame["bg"],
                         fg=COLORS["text_primary"], font=("微软雅黑", 9),
                         width=28, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 账户
                tk.Label(row_frame, text=rec_account, bg=row_frame["bg"],
                         fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                         width=12, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 兑换码（可点击复制）
                code_label = tk.Label(row_frame, text=rec_code, bg=row_frame["bg"],
                                       fg="#4FC3F7", font=("Consolas", 10, "bold"),
                                       cursor="hand2", anchor="w")
                code_label.pack(side=tk.LEFT, padx=2, pady=6)
                code_label.bind("<Button-1>", lambda e, c=rec_code: self._copy_to_clipboard(c))

                # 字段
                tk.Label(row_frame, text=rec_field, bg=row_frame["bg"],
                         fg=COLORS["text_muted"], font=("微软雅黑", 8),
                         width=10, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 状态
                status_color = "#4CAF50" if rec_status == "未使用" else "#9E9E9E"
                tk.Label(row_frame, text=rec_status, bg=row_frame["bg"],
                         fg=status_color, font=("微软雅黑", 9, "bold"),
                         width=6, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

                # 操作按钮
                op_frame = tk.Frame(row_frame, bg=row_frame["bg"])
                op_frame.pack(side=tk.LEFT, padx=(10, 5), pady=4)

                DarkButton(op_frame, text="复制", command=lambda c=rec_code: self._copy_to_clipboard(c), bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32).pack(side=tk.LEFT, padx=(0, 4))

                if rec_status == "未使用":
                    DarkButton(op_frame, text="标记已用", command=lambda rid=rec_id: self._mark_used(rid), bg_color="#FF8F00", text_color="#FFFFFF", height=32).pack(side=tk.LEFT, padx=(0, 4))
                else:
                    DarkButton(op_frame, text="标记未用", command=lambda rid=rec_id: self._mark_unused(rid), bg_color="#1565C0", text_color="#FFFFFF", height=32).pack(side=tk.LEFT, padx=(0, 4))

                DarkButton(op_frame, text="删除", command=lambda rid=rec_id: self._delete_one(rid), bg_color="#C62828", text_color="#FFFFFF", height=32).pack(side=tk.LEFT)
            except Exception as e:
                # 渲染失败时显示错误信息，不中断整个列表
                err_frame = tk.Frame(self.scroll_frame, bg="#FFEBEE")
                err_frame.pack(fill=tk.X, pady=1)
                tk.Label(err_frame, text=f"记录 {i+1} 渲染失败: {str(e)}", bg="#FFEBEE",
                         fg="#C62828", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10, pady=6)

    def _toggle_select(self, record_id, var):
        if var.get():
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def _copy_to_clipboard(self, text):
        """复制到剪贴板"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except:
            pass

    def _mark_used(self, record_id):
        update_redeem_code_status(record_id, "已使用")
        self.refresh_list()

    def _mark_unused(self, record_id):
        update_redeem_code_status(record_id, "未使用")
        self.refresh_list()

    def _delete_one(self, record_id):
        delete_redeem_code(record_id)
        self.refresh_list()

    def copy_selected(self):
        """复制选中的兑换码（仅筛选后的记录）"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        # P2-L: 用.get()避免旧版记录缺字段时KeyError
        codes = [r.get("redeem_code", "") for r in filtered if r.get("id") in self.selected_ids and r.get("redeem_code")]
        if codes:
            self._copy_to_clipboard("\n".join(codes))

    def copy_all(self):
        """复制全部兑换码（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        # P2-L: 用.get()避免旧版记录缺字段时KeyError
        codes = [r.get("redeem_code", "") for r in filtered if r.get("redeem_code")]
        self._copy_to_clipboard("\n".join(codes))

    def export_txt(self):
        """导出为TXT文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("===== B站工具箱 兑换码导出 =====\n")
                f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"活动筛选: {self.current_activity_filter}\n")
                f.write(f"共 {len(filtered)} 条\n")
                f.write("=" * 50 + "\n\n")
                for r in filtered:
                    f.write(f"ID: {r['id']}\n")
                    f.write(f"时间: {r.get('time', '')}\n")
                    f.write(f"任务: {r.get('task_name', '')}\n")
                    f.write(f"账户: {r.get('account', '')}\n")
                    f.write(f"兑换码: {r.get('redeem_code', '')}\n")
                    f.write(f"状态: {r.get('status', '')}\n")
                    f.write("-" * 40 + "\n")
            self._copy_to_clipboard(filepath)
        except Exception as e:
            pass

    def export_csv(self):
        """导出为CSV文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.csv")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("ID,领取时间,任务名称,账户,兑换码,字段,状态\n")
                for r in filtered:
                    f.write(f"{r['id']},{r.get('time','')},{r.get('task_name','')},{r.get('account','')},{r.get('redeem_code','')},{r.get('code_field','')},{r.get('status','')}\n")
        except Exception as e:
            pass

    def delete_selected(self):
        """删除选中的记录（仅筛选后的记录中选中的）—— 一次性过滤，避免循环删除时id错位"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        filtered_ids = set(r["id"] for r in filtered)
        to_delete = set(rid for rid in self.selected_ids if rid in filtered_ids)
        if not to_delete:
            return
        try:
            records = load_redeem_codes()
            records = [r for r in records if r["id"] not in to_delete]
            # 统一重新编号
            for i, r in enumerate(records):
                r["id"] = i + 1
            _ensure_code_dir()
            atomic_write_json(CODE_EXPORT_FILE, records)
        except Exception as e:
            print(f"批量删除失败: {e}")
        self.refresh_list()

    def clear_all(self):
        """清空全部记录（P2-K: 加二次确认，防止误触）"""
        if not custom_askyesno(self.winfo_toplevel(), "确认清空", "确定要清空全部兑换码记录吗？此操作不可恢复！"):
            return
        clear_redeem_codes()
        self.refresh_list()
