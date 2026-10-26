# -*- coding: utf-8 -*-
"""看播任务页面：进房、心跳、X25Kn 上报、弹幕 WS、送礼。"""

import hashlib, json, random, struct, threading, time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

import requests

from config import (COLORS, BASE_DIR, HEADERS)
from storage import atomic_write_json
from widgets import DarkButton

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

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


class WatchLiveFrame(tk.Frame):
    """看播任务工具：模拟观看B站直播间，完成看播里程碑任务"""

    ROOM_ENTRY_API = "https://api.live.bilibili.com/room/v1/Room/room_entry_action"
    HEARTBEAT_API = "https://api.live.bilibili.com/User/userOnlineHeart"

    def __init__(self, parent, account_mgr, room_mgr):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.root = parent.winfo_toplevel()  # P0-D: worker线程通过root.after回主线程
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.running = False
        self.watch_thread = None
        self.stop_flag = {"stop": False}
        self.account_stats = {}
        self.ws_clients = {}  # 存储WebSocket弹幕连接 {账户名: client}
        self.account_vars = {}  # 每个账户名对应一个BooleanVar
        self.account_checkbuttons = []  # 复选框列表，用于启用/禁用
        self.x25kn_threads = {}  # X25Kn观看心跳线程 {账户名: thread}
        self.x25kn_stop = {}  # X25Kn停止标志 {账户名: bool}
        self.x25kn_state = {}  # X25Kn协议状态 {账户名: dict}
        self.watch_config = self.load_watch_config()
        # 送礼功能变量
        self.gift_running = False
        self.gift_threads = {}
        self.gift_stop = {}
        self.gift_config = self.load_gift_config()
        self.gift_id_cache = None  # 缓存牛蛙牛蛙的gift_id
        self.gift_account_var = tk.StringVar(value="")  # 送礼账户下拉选择
        self.gift_account_battery = {}  # 送礼账户电池余额缓存
        # 看播历史记录
        self.watch_history = self.load_watch_history()
        self.current_watch_record = None  # 当前进行中的看播记录
        self.watch_snapshot_timer = None  # 快照定时器
        self.build_ui()
        # 启动时检查是否有异常中断的快照
        self.after(500, self.check_watch_snapshot)
        self.refresh_account_list()
        self.apply_watch_config()
        self.apply_gift_config()
        self.bind_auto_save()
        self.log("看播任务工具已启动，勾选账户和直播间后点击「开始看播」")


    # ========== 看播历史记录功能 ==========
    def load_watch_history(self):
        """加载看播历史记录"""
        history_file = BASE_DIR / "watch_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_watch_history(self):
        """保存看播历史记录"""
        try:
            history_file = BASE_DIR / "watch_history.json"
            atomic_write_json(history_file, self.watch_history)
        except Exception as e:
            self.log(f"⚠ 保存看播历史失败: {e}")

    def start_watch_record(self, room_ids, selected_accounts):
        """开始一条新的看播记录"""
        import uuid
        self.current_watch_record = {
            "id": str(uuid.uuid4())[:8],
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start_timestamp": time.time(),
            "end_time": None,
            "duration_seconds": 0,
            "target_minutes": self.duration_var.get(),
            "room_ids": room_ids,
            "accounts": [],
            "status": "进行中",
            "anomalies": [],
            "heartbeat_interval": self.interval_var.get()
        }
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.current_watch_record["accounts"].append({
                "account_name": name,
                "watch_seconds": 0,
                "heartbeat_count": 0,
                "status": "进入中",
                "anomalies": []
            })
        self.log(f"[历史记录] 开始记录: {len(room_ids)}个直播间, {len(selected_accounts)}个账户")

    def update_watch_record_stats(self):
        """更新当前看播记录的统计数据"""
        if not self.current_watch_record:
            return
        total_seconds = 0
        for acc_rec in self.current_watch_record["accounts"]:
            name = acc_rec["account_name"]
            if name in self.account_stats:
                stats = self.account_stats[name]
                acc_rec["watch_seconds"] = stats.get("watch_seconds", 0)
                acc_rec["heartbeat_count"] = stats.get("heartbeat_count", 0)
                acc_rec["status"] = stats.get("status", "未知")
                total_seconds = max(total_seconds, acc_rec["watch_seconds"])
        self.current_watch_record["duration_seconds"] = total_seconds  # P2-H: 多账户时为最长账户时长，非总和

    def add_watch_anomaly(self, anomaly_type, message, account_name=None, room_id=None):
        """添加异常事件到当前看播记录"""
        if not self.current_watch_record:
            return
        anomaly = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": anomaly_type,
            "message": message,
            "account": account_name,
            "room": room_id
        }
        self.current_watch_record["anomalies"].append(anomaly)
        # 如果指定了账户，也添加到账户的异常列表
        if account_name:
            for acc_rec in self.current_watch_record["accounts"]:
                if acc_rec["account_name"] == account_name:
                    acc_rec["anomalies"].append(anomaly)
                    break
        self.log(f"[异常] {anomaly_type}: {message}")

    def finish_watch_record(self, status="已完成"):
        """结束当前看播记录并保存到历史"""
        if not self.current_watch_record:
            return
        self.update_watch_record_stats()
        self.current_watch_record["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_watch_record["status"] = status
        # 插入到历史记录最前面
        self.watch_history.insert(0, self.current_watch_record)
        self.save_watch_history()
        self.log(f"[历史记录] 已保存: {status}, 时长{self.current_watch_record['duration_seconds']}秒, 异常{len(self.current_watch_record['anomalies'])}次")
        self.current_watch_record = None
        # 停止快照定时器
        if self.watch_snapshot_timer:
            try:
                self.after_cancel(self.watch_snapshot_timer)
            except Exception:
                pass
            self.watch_snapshot_timer = None
        # 删除快照文件
        try:
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            if snapshot_file.exists():
                snapshot_file.unlink()
        except Exception:
            pass

    def save_watch_snapshot(self):
        """保存看播快照（每5分钟一次，用于异常中断恢复）"""
        if not self.current_watch_record:
            return
        try:
            self.update_watch_record_stats()
            snapshot = {
                "record": self.current_watch_record,
                "snapshot_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "account_stats": {}
            }
            for name, stats in self.account_stats.items():
                snapshot["account_stats"][name] = {
                    "watch_seconds": stats.get("watch_seconds", 0),
                    "heartbeat_count": stats.get("heartbeat_count", 0),
                    "status": stats.get("status", "未知")
                }
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            atomic_write_json(snapshot_file, snapshot)
        except Exception as e:
            self.log(f"⚠ 保存看播快照失败: {e}")
        # 安排下一次快照（5分钟后）
        if self.running and self.current_watch_record:
            self.watch_snapshot_timer = self.after(300000, self.save_watch_snapshot)

    def check_watch_snapshot(self):
        """启动时检查是否有异常中断的快照"""
        try:
            snapshot_file = BASE_DIR / "watch_snapshot.json"
            if not snapshot_file.exists():
                return
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
            record = snapshot.get("record") or {}
            snapshot_time = snapshot.get("snapshot_time", "未知")
            # 将快照作为异常中断记录保存到历史
            record["end_time"] = snapshot_time
            record["status"] = "异常中断"
            record["anomalies"] = list(record.get("anomalies") or [])
            record["anomalies"].append({
                "time": snapshot_time,
                "type": "程序异常中断",
                "message": f"程序在{snapshot_time}异常退出，看播未正常结束",
                "account": None,
                "room": None
            })
            self.watch_history.insert(0, record)
            self.save_watch_history()
            # 弹窗警告
            from tkinter import messagebox
            self.after(100, lambda: messagebox.showwarning(
                "看播异常中断",
                f"检测到上次看播在 {snapshot_time} 异常中断！\n\n"
                f"直播间: {', '.join(record.get('room_ids', []))}\n"
                f"账户数: {len(record.get('accounts', []))}\n"
                f"已观看: {record.get('duration_seconds', 0)}秒\n\n"
                f"该记录已保存到历史记录中（标记为异常中断）。"
            , parent=self.winfo_toplevel()))
        except Exception as e:
            self.log(f"⚠ 检查看播快照失败: {e}")
        finally:
            # 删除快照文件（无论成功失败）
            try:
                if snapshot_file.exists():
                    snapshot_file.unlink()
            except Exception:
                pass


    def show_watch_history(self):
        """显示看播历史记录弹窗"""
        if not hasattr(self, 'history_window') or not self.history_window.winfo_exists():
            self.history_window = tk.Toplevel(self)
            self.history_window.title("看播历史记录")
            self.history_window.geometry("1300x750")
            self.history_window.configure(bg=COLORS["bg_dark"])
            self.history_window.transient(self.winfo_toplevel())
            self._build_history_ui()
        else:
            self.history_window.lift()
            self.history_window.focus_force()

    def _build_history_ui(self):
        """构建历史记录UI"""
        win = self.history_window
        # 顶部统计栏（P2-C: 保存为实例变量，避免winfo_children()[0]硬编码）
        self.history_stats_frame = tk.Frame(win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        self.history_stats_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        self._update_history_stats(self.history_stats_frame)

        # 工具栏
        toolbar = tk.Frame(win, bg=COLORS["bg_dark"])
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(toolbar, text=f"共 {len(self.watch_history)} 条记录", bg=COLORS["bg_dark"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        DarkButton(toolbar, "导出Excel", command=self.export_watch_history_excel, width=100, height=32, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(toolbar, "刷新", command=self._refresh_history_view, width=80, height=32, bg_color=COLORS["accent"], text_color="#000000").pack(side=tk.RIGHT)

        # 表格区域
        table_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 表头
        columns = ("开始时间", "结束时间", "时长", "直播间", "账户", "状态", "异常")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        col_widths = [160, 160, 90, 260, 300, 90, 100]
        for col, width in zip(columns, col_widths):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=width, anchor=tk.CENTER)
        # 样式
        style = ttk.Style()
        style.configure("History.Treeview", background=COLORS["bg_card"], fieldbackground=COLORS["bg_card"], foreground=COLORS["text_primary"], rowheight=28, font=("微软雅黑", 9))
        style.configure("History.Treeview.Heading", background=COLORS["bg_input"], foreground=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.history_tree.configure(style="History.Treeview")
        # 标签（标红）
        self.history_tree.tag_configure("anomaly", foreground=COLORS["danger"])
        self.history_tree.tag_configure("warning", foreground=COLORS["warning"])
        self.history_tree.tag_configure("success", foreground=COLORS["success"])

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击查看详情
        self.history_tree.bind("<Double-1>", self._show_history_detail)

        # 分页
        self.history_page = 0
        self.history_page_size = 20
        page_frame = tk.Frame(win, bg=COLORS["bg_dark"])
        page_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.history_page_label = tk.Label(page_frame, text="", bg=COLORS["bg_dark"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.history_page_label.pack(side=tk.LEFT)
        DarkButton(page_frame, "上一页", command=lambda: self._history_prev_page(), width=80, height=30, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]).pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(page_frame, "下一页", command=lambda: self._history_next_page(), width=80, height=30, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"]).pack(side=tk.RIGHT)

        self._refresh_history_view()

    def _update_history_stats(self, parent):
        """更新统计信息"""
        for widget in parent.winfo_children():
            widget.destroy()
        total = len(self.watch_history)
        total_seconds = sum(r.get("duration_seconds", 0) for r in self.watch_history)
        total_hours = total_seconds / 3600
        anomaly_count = sum(len(r.get("anomalies", [])) for r in self.watch_history)
        completed = sum(1 for r in self.watch_history if r.get("status") == "已完成")
        interrupted = sum(1 for r in self.watch_history if r.get("status") == "异常中断")

        stats = [
            ("总记录数", f"{total} 次"),
            ("总观看时长", f"{total_hours:.1f} 小时"),
            ("已完成", f"{completed} 次"),
            ("异常中断", f"{interrupted} 次"),
            ("异常事件", f"{anomaly_count} 次"),
        ]
        for i, (label, value) in enumerate(stats):
            frame = tk.Frame(parent, bg=COLORS["bg_card"])
            frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10, pady=8)
            tk.Label(frame, text=label, bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack()
            color = COLORS["danger"] if "异常" in label else COLORS["accent"]
            tk.Label(frame, text=value, bg=COLORS["bg_card"], fg=color, font=("微软雅黑", 13, "bold")).pack()

    def _refresh_history_view(self):
        """刷新历史记录表格"""
        # 重新加载
        self.watch_history = self.load_watch_history()
        # 更新统计（P2-C: 使用实例变量，避免winfo_children()[0]硬编码）
        if hasattr(self, 'history_stats_frame') and self.history_stats_frame.winfo_exists():
            self._update_history_stats(self.history_stats_frame)
        # 清空表格
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        # 计算分页
        total_pages = max(1, (len(self.watch_history) + self.history_page_size - 1) // self.history_page_size)
        if self.history_page >= total_pages:
            self.history_page = total_pages - 1
        start = self.history_page * self.history_page_size
        end = start + self.history_page_size
        page_records = self.watch_history[start:end]

        for record in page_records:
            start_time = record.get("start_time", "-")
            end_time = record.get("end_time", "-")
            duration = f"{record.get('duration_seconds', 0)}秒"
            rooms = ", ".join(record.get("room_ids", []))
            if len(rooms) > 20:
                rooms = rooms[:20] + "..."
            accounts = ", ".join(a.get("account_name", "") for a in record.get("accounts", []))
            if len(accounts) > 25:
                accounts = accounts[:25] + "..."
            status = record.get("status", "-")
            anomaly_count = len(record.get("anomalies", []))
            anomaly_text = f"{anomaly_count}次" if anomaly_count > 0 else "无"

            # 确定标签
            tags = ()
            if anomaly_count > 0:
                tags = ("anomaly",)
            elif status == "已完成":
                tags = ("success",)
            elif status == "异常中断":
                tags = ("anomaly",)
            elif status == "已停止":
                tags = ("warning",)

            # P2-B: 用记录id作为item的iid，避免同一秒多条记录定位错误
            record_id = record.get("id", "")
            self.history_tree.insert("", tk.END, iid=record_id, values=(start_time, end_time, duration, rooms, accounts, status, anomaly_text), tags=tags)

        self.history_page_label.config(text=f"第 {self.history_page + 1}/{total_pages} 页（每页{self.history_page_size}条）")

    def _history_prev_page(self):
        if self.history_page > 0:
            self.history_page -= 1
            self._refresh_history_view()

    def _history_next_page(self):
        total_pages = max(1, (len(self.watch_history) + self.history_page_size - 1) // self.history_page_size)
        if self.history_page < total_pages - 1:
            self.history_page += 1
            self._refresh_history_view()

    def _show_history_detail(self, event):
        """双击显示记录详情（P2-B: 用id定位而非时间戳）"""
        selection = self.history_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        # P2-B: 用item的iid（记录id）定位，避免同一秒多条记录显示错误
        record = None
        for r in self.watch_history:
            if r.get("id") == item_id:
                record = r
                break
        # 兼容旧记录（无id），回退到时间戳定位
        if not record:
            values = self.history_tree.item(item_id, "values")
            start_time = values[0]
            for r in self.watch_history:
                if r.get("start_time") == start_time:
                    record = r
                    break
        if not record:
            return

        detail_win = tk.Toplevel(self.history_window)
        detail_win.title(f"看播详情 - {record.get('start_time', '-')}")
        detail_win.geometry("700x550")
        detail_win.configure(bg=COLORS["bg_dark"])
        detail_win.transient(self.history_window)

        # 基本信息
        info_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(info_frame, text="基本信息", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        info_text = (
            f"开始时间: {record.get('start_time', '-')}\n"
            f"结束时间: {record.get('end_time', '-')}\n"
            f"观看时长: {record.get('duration_seconds', 0)}秒（目标{record.get('target_minutes', 0)}分钟）\n"
            f"直播间: {', '.join(record.get('room_ids', []))}\n"
            f"状态: {record.get('status', '-')}\n"
            f"心跳间隔: {record.get('heartbeat_interval', '-')}秒"
        )
        tk.Label(info_frame, text=info_text, bg=COLORS["bg_card"], fg=COLORS["text_primary"], font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(0, 10))

        # 账户统计
        acc_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        acc_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(acc_frame, text="账户统计", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        for acc in record.get("accounts", []):
            acc_text = f"  {acc.get('account_name', '-')}: 观看{acc.get('watch_seconds', 0)}秒, 心跳{acc.get('heartbeat_count', 0)}次, 状态{acc.get('status', '-')}"
            color = COLORS["danger"] if acc.get("anomalies") else COLORS["text_primary"]
            tk.Label(acc_frame, text=acc_text, bg=COLORS["bg_card"], fg=color, font=("微软雅黑", 10), justify=tk.LEFT).pack(anchor=tk.W, padx=15)

        # 异常事件
        anom_frame = tk.Frame(detail_win, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        anom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tk.Label(anom_frame, text=f"异常事件（{len(record.get('anomalies', []))}次）", bg=COLORS["bg_card"], fg=COLORS["danger"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))
        if record.get("anomalies"):
            text_widget = tk.Text(anom_frame, bg=COLORS["bg_dark"], fg=COLORS["text_primary"], font=("微软雅黑", 9), height=8, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            for anom in record["anomalies"]:
                line = f"[{anom.get('time', '-')}] {anom.get('type', '-')}: {anom.get('message', '-')}"
                if anom.get("account"):
                    line += f"（账户: {anom['account']}）"
                if anom.get("room"):
                    line += f"（直播间: {anom['room']}）"
                text_widget.insert(tk.END, line + "\n")
            text_widget.config(state=tk.DISABLED)
        else:
            tk.Label(anom_frame, text="  无异常事件", bg=COLORS["bg_card"], fg=COLORS["success"], font=("微软雅黑", 10)).pack(anchor=tk.W, padx=15, pady=(0, 10))

    def export_watch_history_excel(self):
        """导出看播历史记录为Excel"""
        try:
            from tkinter import filedialog
            default_name = f"看播历史记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx")],
                initialfile=default_name,
                title="导出看播历史记录"
            )
            if not file_path:
                return

            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment
            except ImportError:
                self.log("⚠ 未安装openpyxl，尝试使用csv格式导出")
                # 降级为CSV
                csv_path = file_path.replace(".xlsx", ".csv")
                with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                    import csv
                    writer = csv.writer(f)
                    writer.writerow(["开始时间", "结束时间", "观看时长(秒)", "目标时长(分钟)", "直播间", "账户", "状态", "异常次数", "异常详情"])
                    for r in self.watch_history:
                        anom_details = "; ".join(f"[{a.get('time','')}]{a.get('type','')}:{a.get('message','')}" for a in r.get("anomalies", []))
                        writer.writerow([
                            r.get("start_time", ""),
                            r.get("end_time", ""),
                            r.get("duration_seconds", 0),
                            r.get("target_minutes", 0),
                            ", ".join(r.get("room_ids", [])),
                            ", ".join(a.get("account_name", "") for a in r.get("accounts", [])),
                            r.get("status", ""),
                            len(r.get("anomalies", [])),
                            anom_details
                        ])
                self.log(f"✓ 已导出CSV: {csv_path}")
                return

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "看播历史记录"

            # 表头
            headers = ["开始时间", "结束时间", "观看时长(秒)", "目标时长(分钟)", "直播间", "账户", "状态", "异常次数", "异常详情"]
            header_fill = PatternFill(start_color="16213e", end_color="16213e", fill_type="solid")
            header_font = Font(color="00d9ff", bold=True, size=11)
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # 数据
            danger_fill = PatternFill(start_color="2d1b1b", end_color="2d1b1b", fill_type="solid")
            for row_idx, r in enumerate(self.watch_history, 2):
                anom_details = "; ".join(f"[{a.get('time','')}]{a.get('type','')}:{a.get('message','')}" for a in r.get("anomalies", []))
                values = [
                    r.get("start_time", ""),
                    r.get("end_time", ""),
                    r.get("duration_seconds", 0),
                    r.get("target_minutes", 0),
                    ", ".join(r.get("room_ids", [])),
                    ", ".join(a.get("account_name", "") for a in r.get("accounts", [])),
                    r.get("status", ""),
                    len(r.get("anomalies", [])),
                    anom_details
                ]
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=row_idx, column=col, value=value)
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    if len(r.get("anomalies", [])) > 0:
                        cell.fill = danger_fill
                        cell.font = Font(color="ff4757")

            # 列宽
            widths = [18, 18, 12, 14, 25, 30, 10, 10, 50]
            for col, width in enumerate(widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

            wb.save(file_path)
            self.log(f"✓ 已导出Excel: {file_path}")
            from tkinter import messagebox
            messagebox.showinfo("导出成功", f"看播历史记录已导出到:\n{file_path}", parent=self.winfo_toplevel())
        except Exception as e:
            import traceback
            self.log(f"[错误] 导出Excel失败: {e}")
            self.log(traceback.format_exc())
            from tkinter import messagebox
            messagebox.showerror("导出失败", f"导出Excel失败: {e}", parent=self.winfo_toplevel())

    def load_watch_config(self):
        default = {"room_id": "1791983148", "daily_minutes": 10, "heartbeat_interval": 60, "selected_accounts": [], "room_history": []}
        config_file = BASE_DIR / "watch_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_watch_config(self):
        try:
            # 保存所有直播间栏的选择
            room_selections = []
            for bar, combo, del_btn in self.watch_room_bars:
                selected = combo.get().strip()
                if selected:
                    room_selections.append(selected)
            self.watch_config["room_selections"] = room_selections
            self.watch_config["room_bar_count"] = len(self.watch_room_bars)
            self.watch_config["daily_minutes"] = self.duration_var.get()
            self.watch_config["heartbeat_interval"] = self.interval_var.get()
            selected = []
            for name, var in self.account_vars.items():
                if var.get():
                    selected.append(name)
            self.watch_config["selected_accounts"] = selected
            config_file = BASE_DIR / "watch_config.json"
            atomic_write_json(config_file, self.watch_config)
        except Exception:
            pass

    def apply_watch_config(self):
        try:
            self._refresh_room_combo_values()
            # 恢复直播间栏数量
            bar_count = self.watch_config.get("room_bar_count", 1)
            while len(self.watch_room_bars) < bar_count:
                self._add_watch_room_bar()
            # 恢复直播间选择
            room_selections = self.watch_config.get("room_selections", [])
            for i, (bar, combo, del_btn) in enumerate(self.watch_room_bars):
                if i < len(room_selections) and room_selections[i]:
                    combo.set(room_selections[i])
                else:
                    combo.set("")
            self.duration_var.set(self.watch_config.get("daily_minutes", 30))
            self.interval_var.set(self.watch_config.get("heartbeat_interval", 60))
            selected_names = self.watch_config.get("selected_accounts", [])
            # 如果配置中没有选中的账户（首次使用），默认全选
            if not selected_names:
                for name, var in self.account_vars.items():
                    var.set(True)
            else:
                for name, var in self.account_vars.items():
                    var.set(name in selected_names)
        except Exception:
            pass

    def load_gift_config(self):
        default = {
            "room_id": "",
            "gift_name": "牛蛙牛蛙",
            "gift_num": 1,
            "interval": 10,
            "max_count": 0,
            "selected_account": "",  # P2-E: 统一字段名，代码用selected_account
            "room_history": []
        }
        config_file = BASE_DIR / "gift_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    default.update(cfg)
            except Exception:
                pass
        return default

    def save_gift_config(self):
        try:
            current_room = self.gift_room_combo.get().strip()
            self.gift_config["room_name"] = current_room  # 保存直播间名称
            self.gift_config["gift_num"] = self.gift_num_var.get()
            self.gift_config["interval"] = self.gift_interval_var.get()
            self.gift_config["max_count"] = self.gift_count_var.get()
            # 保存选中的送礼账户
            selected = self.gift_account_combo.get()
            self.gift_config["selected_account"] = selected
            config_file = BASE_DIR / "gift_config.json"
            atomic_write_json(config_file, self.gift_config)
        except Exception:
            pass

    def apply_gift_config(self):
        try:
            cfg = self.gift_config
            self._refresh_gift_room_combo_values()
            # 恢复直播间名称（兼容旧配置的room_id）
            room_name = cfg.get("room_name", cfg.get("room_id", ""))
            if room_name:
                self.gift_room_combo.set(room_name)
            self.gift_num_var.set(cfg.get("gift_num", 1))
            self.gift_interval_var.set(cfg.get("interval", 10))
            self.gift_count_var.set(cfg.get("max_count", 0))
            # 恢复选中的送礼账户
            selected = cfg.get("selected_account", "")
            if selected and selected in self.gift_account_combo["values"]:
                self.gift_account_combo.set(selected)
        except Exception:
            pass

    def _refresh_gift_room_combo_values(self):
        """刷新送礼直播间下拉框选项：只显示直播间管理中的直播间名称"""
        if not hasattr(self, 'gift_room_combo') or not self.gift_room_combo.winfo_exists():
            return
        values = []
        for room in self.room_mgr.rooms:
            values.append(room["name"])
        self.gift_room_combo["values"] = values
        # 如果当前选中的不在列表中，清空
        if self.gift_room_combo.get() not in values:
            self.gift_room_combo.set("")

    def _on_gift_room_selected(self, event=None):
        """选择送礼直播间下拉框时：保存配置"""
        self.save_gift_config()

    def _get_gift_room_id(self):
        """根据选中的直播间名称获取直播间号"""
        selected_name = self.gift_room_combo.get().strip()
        if not selected_name:
            return None
        for room in self.room_mgr.rooms:
            if room["name"] == selected_name:
                return room["id"]
        return None

    def bind_auto_save(self):
        try:
            # 直播间多栏选择的保存绑定在_add_watch_room_bar中
            self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            self.interval_combo.bind("<<ComboboxSelected>>", lambda e: self.save_watch_config())
            # 送礼下拉框绑定
            self.gift_room_combo.bind("<<ComboboxSelected>>", self._on_gift_room_selected)
            self.gift_num_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        except Exception:
            pass

    def _refresh_room_combo_values(self):
        """刷新所有直播间栏的下拉框选项"""
        values = [room["name"] for room in self.room_mgr.rooms]
        for bar, combo, del_btn in getattr(self, 'watch_room_bars', []):
            current = combo.get()
            combo["values"] = values
            if current not in values:
                combo.set("")

    def _add_watch_room_bar(self):
        """添加一个直播间选择栏（P2-G: 所有栏都有删除按钮，只有一个栏时禁用）"""
        bar = tk.Frame(self.watch_room_container, bg=COLORS["bg_card"])
        bar.pack(side=tk.LEFT, padx=(0, 8))
        combo = ttk.Combobox(bar, width=20, values=[], state="readonly")
        combo.pack(side=tk.LEFT)
        combo.set("")
        # P2-G: 所有栏都创建删除按钮，避免删除第一栏后新第一栏无按钮
        del_btn = DarkButton(bar, text="✕", command=lambda b=bar: self._remove_watch_room_bar(b), bg_color=COLORS["danger"], text_color="#ffffff", height=32)
        del_btn.pack(side=tk.LEFT, padx=(4, 0))
        # 只有一个栏时禁用删除按钮
        if len(self.watch_room_bars) == 0:
            del_btn.config(state=tk.DISABLED)
        self.watch_room_bars.append((bar, combo, del_btn))
        self._refresh_room_combo_values()

    def _remove_watch_room_bar(self, bar):
        """删除一个直播间选择栏（P2-G: 删除后更新删除按钮状态）"""
        if len(self.watch_room_bars) <= 1:
            return
        for i, (b, c, d) in enumerate(self.watch_room_bars):
            if b == bar:
                b.destroy()
                self.watch_room_bars.pop(i)
                break
        # P2-G: 只剩一个栏时禁用其删除按钮，否则全部启用
        for idx, (b, c, d) in enumerate(self.watch_room_bars):
            if d is not None:
                if len(self.watch_room_bars) == 1:
                    d.config(state=tk.DISABLED)
                else:
                    d.config(state=tk.NORMAL)

    def _get_watch_room_ids(self):
        """获取所有选中的直播间号"""
        room_ids = []
        for bar, combo, del_btn in self.watch_room_bars:
            selected = combo.get().strip()
            if selected:
                for room in self.room_mgr.rooms:
                    if room["name"] == selected:
                        room_ids.append(room["id"])
                        break
        return room_ids

    def get_user_room_id(self, mid):
        """根据用户mid获取直播间号"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                room_id = data["data"].get("roomid")
                if room_id and data["data"].get("roomStatus") == 1:
                    return room_id
        except Exception:
            pass
        return None

    def get_battery_balance(self, account):
        """查询账户电池余额（gold字段，后两位为小数，100=1电池）"""
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = "https://api.live.bilibili.com/xlive/revenue/v1/wallet/myWallet?need_bp=1&need_metal=1"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                wallet = data.get("data", {})
                # gold字段是电池数，后两位为小数，如100=1电池
                gold_raw = wallet.get("gold", 0)
                battery = gold_raw / 100.0 if gold_raw else 0
                return battery
            return None
        except Exception:
            return None

    def _on_account_check(self):
        """复选框点击时保存配置"""
        self.save_watch_config()

    def on_close(self):
        self.stop_watch()
        # P2-D: 同时停止送礼，避免窗口销毁后worker仍循环
        if hasattr(self, 'gift_frame') and self.gift_frame:
            try:
                self.gift_frame.stop_gift()
            except Exception:
                pass
        self.save_watch_config()

    def build_ui(self):
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧账户（复选框多选）
        left_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_card.pack_propagate(False)
        left_card.configure(width=280)
        tk.Label(left_card, text="选择看播账户", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 4))
        tk.Label(left_card, text="（打钩多选，可全选）", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 8)).pack(anchor=tk.W, padx=15, pady=(0, 4))
        # 全选/取消全选按钮
        btn_frame = tk.Frame(left_card, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        self.select_all_btn = DarkButton(btn_frame, text="全选", command=self._select_all_accounts, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.deselect_all_btn = DarkButton(btn_frame, text="取消全选", command=self._deselect_all_accounts, bg_color=COLORS["bg_input"], text_color=COLORS["text_secondary"], height=32)
        self.deselect_all_btn.pack(side=tk.LEFT)
        # 复选框区域（无滚动条，账户数量少直接显示）
        list_frame = tk.Frame(left_card, bg=COLORS["bg_input"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.account_scrollable_frame = list_frame

        # 右侧
        right = tk.Frame(main, bg=COLORS["bg_dark"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # 设置卡片
        settings_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        settings_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(settings_card, text="看播设置", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        settings_inner = tk.Frame(settings_card, bg=COLORS["bg_card"])
        settings_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        row1 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        # 直播间多栏选择容器
        self.watch_room_bars = []
        self.watch_room_container = tk.Frame(row1, bg=COLORS["bg_card"])
        self.watch_room_container.pack(side=tk.LEFT, padx=(8, 0))
        self._add_watch_room_bar()
        # 添加直播间栏按钮
        self.add_room_bar_btn = DarkButton(row1, text="+ 添加", command=self._add_watch_room_bar, bg_color=COLORS["accent"], text_color="#000000", height=32)
        self.add_room_bar_btn.pack(side=tk.LEFT, padx=(8, 4))
        # 刷新直播间下拉框按钮
        self.refresh_room_btn = DarkButton(row1, text="↻ 刷新", command=self._refresh_room_combo_values, bg_color=COLORS["bg_input"], text_color=COLORS["text_primary"], height=32)
        self.refresh_room_btn.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(row1, text="每日时长(分):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.duration_var = tk.IntVar(value=10)
        # v6.2.0: 新增 3 分钟选项（用户需求）
        self.duration_combo = ttk.Combobox(row1, textvariable=self.duration_var, width=8,
                                           values=[3, 5, 10, 15, 20, 30, 45, 60, 90, 120],
                                           state="readonly")
        self.duration_combo.pack(side=tk.LEFT, padx=(8, 0))

        row2 = tk.Frame(settings_inner, bg=COLORS["bg_card"])
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="心跳间隔(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=60)
        self.interval_combo = ttk.Combobox(row2, textvariable=self.interval_var, width=8, values=[30, 45, 50, 60, 70, 90, 120], state="readonly")
        self.interval_combo.pack(side=tk.LEFT, padx=(8, 20))
        self.start_btn = DarkButton(row2, "▶ 开始看播", command=self.start_watch, width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = DarkButton(row2, "■ 停止看播", command=self.stop_watch, width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.config(state=tk.DISABLED)
        self.history_btn = DarkButton(row2, "📋 历史记录", command=self.show_watch_history, width=160, height=40, bg_color=COLORS["accent"], text_color="#000000")
        self.history_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 送礼设置卡片
        gift_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        gift_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(gift_card, text="送礼设置（牛蛙牛蛙）", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        gift_inner = tk.Frame(gift_card, bg=COLORS["bg_card"])
        gift_inner.pack(fill=tk.X, padx=15, pady=(0, 12))

        # 送礼账户选择（下拉单选）
        gift_acc_row = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_acc_row.pack(fill=tk.X, pady=3)
        tk.Label(gift_acc_row, text="送礼账户:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_account_combo = ttk.Combobox(gift_acc_row, width=25, values=[], state="readonly")
        self.gift_account_combo.pack(side=tk.LEFT, padx=(8, 10))
        self.gift_account_combo.bind("<<ComboboxSelected>>", lambda e: self.save_gift_config())
        # 查询电池按钮
        self.gift_query_battery_btn = DarkButton(gift_acc_row, text="查询电池", command=self._query_gift_battery, bg_color=COLORS["accent"], text_color="white", height=32)
        self.gift_query_battery_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.gift_battery_label = tk.Label(gift_acc_row, text="", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"))
        self.gift_battery_label.pack(side=tk.LEFT)

        gift_row1 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row1.pack(fill=tk.X, pady=3)
        tk.Label(gift_row1, text="直播间:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_room_combo = ttk.Combobox(gift_row1, width=24, values=[], state="readonly")
        self.gift_room_combo.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row1, text="礼物:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        tk.Label(gift_row1, text="牛蛙牛蛙", bg=COLORS["bg_input"], fg=COLORS["accent"], font=("微软雅黑", 10, "bold"), padx=10, pady=2).pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row1, text="数量:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_num_var = tk.IntVar(value=1)
        self.gift_num_combo = ttk.Combobox(gift_row1, textvariable=self.gift_num_var, width=6, values=[1, 10], state="readonly")
        self.gift_num_combo.pack(side=tk.LEFT, padx=(8, 0))

        gift_row2 = tk.Frame(gift_inner, bg=COLORS["bg_card"])
        gift_row2.pack(fill=tk.X, pady=3)
        tk.Label(gift_row2, text="送礼间隔(秒):", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_interval_var = tk.IntVar(value=10)
        self.gift_interval_entry = tk.Entry(gift_row2, width=8, textvariable=self.gift_interval_var, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_interval_entry.pack(side=tk.LEFT, padx=(8, 20))
        tk.Label(gift_row2, text="送礼次数:", bg=COLORS["bg_card"], fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.gift_count_var = tk.IntVar(value=0)
        self.gift_count_entry = tk.Entry(gift_row2, width=8, textvariable=self.gift_count_var, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("微软雅黑", 10), bd=0, insertbackground=COLORS["accent"])
        self.gift_count_entry.pack(side=tk.LEFT, padx=(8, 20))
        self.gift_start_btn = DarkButton(gift_row2, "▶ 开始送礼", command=self.start_gift, width=140, height=36, bg_color=COLORS["success"], text_color="#ffffff")
        self.gift_start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.gift_stop_btn = DarkButton(gift_row2, "■ 停止送礼", command=self.stop_gift, width=140, height=36, bg_color=COLORS["danger"], text_color="#ffffff")
        self.gift_stop_btn.pack(side=tk.LEFT)
        self.gift_stop_btn.config(state=tk.DISABLED)

        # 状态卡片
        status_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        status_card.pack(fill=tk.X, pady=(0, 6))
        tk.Label(status_card, text="观看状态", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        tree_frame = tk.Frame(status_card, bg=COLORS["bg_card"])
        tree_frame.pack(fill=tk.X, padx=15, pady=(0, 12))
        columns = ("account", "status", "watch_time", "heartbeat", "target")
        self.status_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=5)
        self.status_tree.heading("account", text="账户")
        self.status_tree.heading("status", text="状态")
        self.status_tree.heading("watch_time", text="已观看")
        self.status_tree.heading("heartbeat", text="心跳次数")
        self.status_tree.heading("target", text="目标时长")
        self.status_tree.column("account", width=140, anchor=tk.CENTER)
        self.status_tree.column("status", width=80, anchor=tk.CENTER)
        self.status_tree.column("watch_time", width=100, anchor=tk.CENTER)
        self.status_tree.column("heartbeat", width=80, anchor=tk.CENTER)
        self.status_tree.column("target", width=100, anchor=tk.CENTER)
        self.status_tree.pack(fill=tk.X)

        # 日志卡片
        log_card = tk.Frame(right, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        log_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="运行日志", bg=COLORS["bg_card"], fg=COLORS["accent"], font=("微软雅黑", 11, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 8))
        log_frame = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))
        self.log_text = tk.Text(log_frame, bg=COLORS["bg_input"], fg=COLORS["text_primary"], font=("Consolas", 9), bd=0, highlightthickness=0, wrap=tk.WORD, insertbackground=COLORS["text_primary"])
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def refresh_account_list(self):
        # 清空旧的复选框
        for widget in self.account_scrollable_frame.winfo_children():
            widget.destroy()
        self.account_vars.clear()
        self.account_checkbuttons.clear()
        # 创建新的复选框（默认全选）
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知账户")
            var = tk.BooleanVar(value=True)
            self.account_vars[name] = var
            cb = tk.Checkbutton(self.account_scrollable_frame, text=name, variable=var,
                                bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                selectcolor=COLORS["accent"], activebackground=COLORS["bg_input"],
                                activeforeground=COLORS["text_primary"], font=("微软雅黑", 9),
                                anchor="w", padx=8, pady=4, command=self._on_account_check)
            cb.pack(fill=tk.X, anchor="w")
            self.account_checkbuttons.append(cb)
        self.refresh_status_tree()
        # 同时刷新送礼账户下拉框
        self._refresh_gift_account_combo()

    def _refresh_gift_account_combo(self):
        """刷新送礼账户下拉框，只显示账户名"""
        if not hasattr(self, 'gift_account_combo'):
            return
        values = []
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            values.append(name)
        # 保存当前选择
        current = self.gift_account_combo.get()
        self.gift_account_combo["values"] = values
        # 恢复选择
        if current and current in values:
            self.gift_account_combo.set(current)
        elif values:
            self.gift_account_combo.set(values[0])

    def _query_gift_battery(self):
        """查询当前选中送礼账户的电池余额"""
        selected_name = self.gift_account_combo.get()
        if not selected_name:
            self.gift_battery_label.config(text="请先选择账户")
            return
        self.gift_battery_label.config(text="查询中...")
        self.gift_query_battery_btn.config(state=tk.DISABLED)
        # 异步查询
        def query():
            battery = None
            for acc in self.account_mgr.accounts:
                if acc.get("name") == selected_name:
                    battery = self.get_battery_balance(acc)
                    break
            # 在UI线程更新
            def update():
                if battery is not None:
                    self.gift_battery_label.config(text=f"电池余额: {battery}")
                else:
                    self.gift_battery_label.config(text="查询失败")
                self.gift_query_battery_btn.config(state=tk.NORMAL)
            self.after(0, update)
        threading.Thread(target=query, daemon=True).start()

    def _select_all_accounts(self):
        for var in self.account_vars.values():
            var.set(True)
        self.save_watch_config()

    def _deselect_all_accounts(self):
        for var in self.account_vars.values():
            var.set(False)
        self.save_watch_config()

    def refresh_status_tree(self):
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)
        for acc in self.account_mgr.accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name, {"status": "待开始", "watch_seconds": 0, "heartbeat_count": 0})
            watch_min = stats.get("watch_seconds", 0) // 60
            watch_sec = stats.get("watch_seconds", 0) % 60
            ws_status = "✓在线" if stats.get("ws_connected", False) else ""
            status_text = stats.get("status", "待开始")
            if ws_status:
                status_text = f"{status_text} {ws_status}"
            self.status_tree.insert("", tk.END, values=(name, status_text, f"{watch_min}分{watch_sec}秒", stats.get("heartbeat_count", 0), f"{self.duration_var.get()}分钟"))

    def log(self, msg):
        """线程安全的日志输出（O5: 同时写文件，便于排障）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\n"
        def _update():
            try:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, log_msg)
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
        # O5: 落文件（原实现只写 UI，重启即丢）
        try:
            _get_logger_cached(self, "watch_live").log(msg)
        except Exception:
            pass

    def get_danmu_token(self, account, room_id):
        """用登录cookie获取弹幕服务器token"""
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie}
            resp = requests.get(f"https://api.live.bilibili.com/room/v1/Danmu/getConf?room_id={room_id}",
                               headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data["data"].get("token", ""), data["data"].get("host", "broadcastlv.chat.bilibili.com")
        except Exception as e:
            self.log(f"  获取弹幕token异常: {e}")
        return "", "broadcastlv.chat.bilibili.com"

    def connect_ws_danmaku(self, account, room_id):
        """建立WebSocket弹幕连接，让账户出现在在线观众列表中，支持自动重连"""
        if not WEBSOCKET_AVAILABLE:
            self.log(f"  websocket-client未安装，跳过弹幕连接")
            return None

        name = account.get("name", "未知")
        uid = int(account.get("DedeUserID", "0") or "0")

        # B站弹幕协议
        HEADER_STRUCT = struct.Struct('>I2H2I')
        OP_HEARTBEAT = 2
        OP_AUTH = 7

        def pack_data(op, data_bytes):
            header = HEADER_STRUCT.pack(len(data_bytes) + 16, 16, 1, op, 1)
            return header + data_bytes

        client = {
            "ws": None, "running": False, "connected": False,
            "heartbeat_thread": None, "reconnect_count": 0,
            "account": account, "room_id": int(room_id), "name": name
        }

        def do_connect():
            """执行实际连接"""
            try:
                # 获取token
                token, host = self.get_danmu_token(account, room_id)
                if not token:
                    self.log(f"  [{name}] ✗ 获取弹幕token失败")
                    if client["running"]:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            self.log(f"  [{name}] {delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
                    return False

                def on_message(ws, message):
                    try:
                        if len(message) < 16:
                            return
                        _, _, _, op, _ = HEADER_STRUCT.unpack_from(message, 0)
                        if op == 8:  # 认证响应
                            body = message[16:]
                            result = json.loads(body.decode('utf-8'))
                            if result.get("code") == 0:
                                client["connected"] = True
                                client["reconnect_count"] = 0
                                self.log(f"  [{name}] ✓ 弹幕连接认证成功(uid={uid})，等待计入在线观众")
                                if name in self.account_stats:
                                    self.account_stats[name]["ws_connected"] = True
                                    self.after(0, self.refresh_status_tree)
                            else:
                                self.log(f"  [{name}] ✗ 弹幕认证失败: {result.get('message')}")
                        elif op == 3:  # 心跳响应，包含人气值
                            try:
                                popularity = struct.unpack('>I', message[16:20])[0]
                                client["last_popularity"] = popularity
                            except Exception:
                                pass
                    except Exception:
                        pass

                def on_error(ws, error):
                    if client["running"]:
                        err_str = str(error)
                        # 连接成功后过滤ping/pong等无关错误，初始连接失败时全部输出
                        if client["connected"]:
                            if "ping/pong" not in err_str and "Connection to remote host was lost" not in err_str:
                                self.log(f"  [{name}] 弹幕连接错误: {error}")
                        else:
                            self.log(f"  [{name}] 弹幕初始连接错误: {error}")

                def on_close(ws, *args):
                    was_connected = client["connected"]
                    client["connected"] = False
                    if name in self.account_stats:
                        self.account_stats[name]["ws_connected"] = False
                    # 自动重连（包括初始连接失败的情况）
                    if client["running"]:
                        client["reconnect_count"] += 1
                        if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            reason = "断开" if was_connected else "初始连接失败"
                            self.log(f"  [{name}] 弹幕连接{reason}，{delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
                        else:
                            self.log(f"  [{name}] 弹幕重连次数过多(15次)，停止重连")

                def on_open(ws):
                    auth_data = {
                        "uid": uid,
                        "roomid": int(room_id),
                        "protover": 2,
                        "platform": "web",
                        "clientver": "2.6.41",
                        "type": 2,
                        "key": token
                    }
                    ws.send(pack_data(OP_AUTH, json.dumps(auth_data, separators=(',', ':')).encode()),
                           opcode=websocket.ABNF.OPCODE_BINARY)

                ws_url = f"wss://{host}/sub"
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                client["ws"] = ws
                # 不使用库级别的ping/pong（B站不响应），只用应用层心跳
                threading.Thread(target=ws.run_forever,
                               kwargs={"origin": "https://live.bilibili.com"},
                               daemon=True).start()
                return True
            except Exception as e:
                self.log(f"  [{name}] 弹幕连接异常: {e}")
                # 异常时也安排重连
                if client["running"]:
                    client["reconnect_count"] += 1
                    if client["reconnect_count"] <= 15:
                            delay = min(2 ** client["reconnect_count"], 30)  # P1-9: 指数退避
                            self.log(f"  [{name}] {delay}秒后自动重连(第{client['reconnect_count']}次)")
                            # P1-E: 保存Timer对象，关闭时可cancel
                            client["reconnect_timer"] = threading.Timer(delay, do_connect)
                            client["reconnect_timer"].daemon = True
                            client["reconnect_timer"].start()
                    return False

        def heartbeat_loop():
            hb_count = 0
            while client["running"]:
                try:
                    if client["connected"] and client["ws"]:
                        client["ws"].send(pack_data(OP_HEARTBEAT, b"[object Object]"),
                                         opcode=websocket.ABNF.OPCODE_BINARY)
                        hb_count += 1
                        # 每2次心跳（60秒）显示一次连接状态
                        if hb_count % 2 == 0:
                            self.log(f"  [{name}] 弹幕连接正常，已发送{hb_count}次心跳")
                    elif not client["connected"]:
                        # 连接未建立，不打印（避免刷屏）
                        pass
                except Exception as e:
                    self.log(f"  [{name}] 弹幕心跳异常: {e}")
                time.sleep(30)

        # 初始连接
        client["running"] = True
        client["heartbeat_thread"] = threading.Thread(target=heartbeat_loop, daemon=True)
        client["heartbeat_thread"].start()
        do_connect()
        return client

    def close_all_ws(self):
        """关闭所有WebSocket弹幕连接（带超时，避免卡住）"""
        for name, client in self.ws_clients.items():
            if client:
                client["running"] = False
                # P1-E: 取消待触发的重连定时器，防止关闭后继续重连
                try:
                    if client.get("reconnect_timer"):
                        client["reconnect_timer"].cancel()
                except Exception:
                    pass
                if client.get("ws"):
                    try:
                        # 设置关闭超时，避免阻塞
                        ws = client["ws"]
                        ws.sock = None  # 强制断开
                        ws.close()
                    except Exception:
                        pass
        self.ws_clients.clear()

    def get_cookie(self, account):
        return f"SESSDATA={account.get('SESSDATA', '')}; bili_jct={account.get('bili_jct', '')}"

    def enter_room(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": int(room_id), "platform": "pc", "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.ROOM_ENTRY_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "进入直播间成功"
            return False, f"进入失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"进入异常: {e}"

    def send_heartbeat(self, account, room_id):
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}", "Origin": "https://live.bilibili.com", "Content-Type": "application/x-www-form-urlencoded"}
            data = {"room_id": int(room_id), "csrf": account.get("bili_jct", ""), "csrf_token": account.get("bili_jct", ""), "visit_id": ""}
            resp = requests.post(self.HEARTBEAT_API, headers=headers, data=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return True, "心跳成功"
            return False, f"心跳失败: {result.get('message', '未知')}"
        except Exception as e:
            return False, f"心跳异常: {e}"

    def get_play_url(self, account, room_id):
        """获取直播流URL（旧版API，flv直链，稳定可靠）"""
        try:
            cookie = self.get_cookie(account)
            headers = {
                **HEADERS,
                "Cookie": cookie,
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            # 旧版API：直接返回flv播放地址
            url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={room_id}&quality=4&platform=web"
            resp = requests.get(url, headers=headers, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                durl = data.get("durl", [])
                if durl:
                    play_url = durl[0].get("url", "")
                    if play_url:
                        return True, play_url
                return False, f"未找到直播流地址，data={str(data)[:200]}"
            return False, f"API返回code={result.get('code')}, msg={result.get('message')}"
        except Exception as e:
            return False, f"获取异常: {e}"

    # ========== X25Kn 观看心跳上报协议（v4.0.0新增）==========
    X25KN_E_URL = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
    X25KN_X_URL = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/X"
    X25KN_HMAC_FUNCS = ["md5", "sha1", "sha256", "sha224", "sha512", "sha384"]
    X25KN_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    def x25kn_sign(self, payload_json, rules, secret_key):
        """按secret_rule用secret_key做HMAC链式签名"""
        import hmac
        result = payload_json
        key_bytes = secret_key.encode("utf-8")
        for r in rules:
            if 0 <= r < len(self.X25KN_HMAC_FUNCS):
                mac = hmac.new(key_bytes, result.encode("utf-8"),
                               getattr(hashlib, self.X25KN_HMAC_FUNCS[r]))
                result = mac.hexdigest()
        return result

    def x25kn_get_buvid(self, account):
        """获取LIVE_BUVID（通过SPI接口）"""
        try:
            cookie = self.get_cookie(account)
            headers = {"User-Agent": self.X25KN_UA, "Cookie": cookie}
            resp = requests.get("https://api.bilibili.com/x/frontend/finger/spi", headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0 and data.get("data", {}).get("b_3"):
                return data["data"]["b_3"]
        except Exception:
            pass
        # fallback：随机生成
        import random, string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=37)) + "infoc"

    def x25kn_get_area_info(self, account, room_id):
        """获取直播间area_id和parent_area_id"""
        try:
            cookie = self.get_cookie(account)
            headers = {**HEADERS, "Cookie": cookie, "Referer": f"https://live.bilibili.com/{room_id}"}
            # 旧版API（新版getInfoByRoom可能返回-352风控）
            resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
                                headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data["data"]["area_id"], data["data"]["parent_area_id"], data["data"]["uid"]
        except Exception:
            pass
        return 874, 3, 3690972101740709  # 鸣潮分区默认值

    def x25kn_enter(self, account, room_id, area_id, parent_id, up_id, buvid, uuid_str):
        """E接口：进入房间，返回{timestamp, secret_key, secret_rule, heartbeat_interval}"""
        try:
            cookie = self.get_cookie(account)
            bili_jct = account.get("bili_jct", "")
            ts = int(time.time() * 1000)
            form = {
                "id": json.dumps([parent_id, area_id, 0, int(room_id)], separators=(",", ":")),
                "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
                "ts": ts,
                "is_patch": 0,
                "heart_beat": "[]",
                "ua": self.X25KN_UA,
                "csrf_token": bili_jct,
                "csrf": bili_jct,
                "visit_id": "",
                "ruid": up_id,
            }
            headers = {
                "User-Agent": self.X25KN_UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
                "Origin": "https://live.bilibili.com",
                "Referer": f"https://live.bilibili.com/{room_id}",
            }
            resp = requests.post(self.X25KN_E_URL, data=form, headers=headers, timeout=15)
            result = resp.json()
            if result.get("code") == 0 and result.get("data"):
                return result["data"]
            return {"_error": True, "code": result.get("code"), "message": result.get("message"), "raw": result}
        except Exception as e:
            return {"_error": True, "code": -1, "message": f"异常: {type(e).__name__}: {e}"}

    def x25kn_heartbeat(self, account, room_id, area_id, parent_id, up_id, seq,
                        buvid, uuid_str, ets, secret_key, secret_rule, heartbeat_interval):
        """X接口：心跳，返回{timestamp, secret_key, secret_rule, heartbeat_interval}"""
        try:
            cookie = self.get_cookie(account)
            bili_jct = account.get("bili_jct", "")
            ts = int(time.time() * 1000)
            sign_payload = {
                "platform": "web",
                "parent_id": parent_id,
                "area_id": area_id,
                "seq_id": seq,
                "room_id": int(room_id),
                "buvid": buvid,
                "uuid": uuid_str,
                "ets": ets,
                "time": heartbeat_interval,
                "ts": ts,
            }
            sign_input = json.dumps(sign_payload, separators=(",", ":"))
            s = self.x25kn_sign(sign_input, secret_rule, secret_key)
            form = {
                "s": s,
                "id": json.dumps([parent_id, area_id, seq, int(room_id)], separators=(",", ":")),
                "device": json.dumps([buvid, uuid_str], separators=(",", ":")),
                "ruid": up_id,
                "ets": ets,
                "benchmark": secret_key,
                "time": heartbeat_interval,
                "ts": ts,
                "ua": self.X25KN_UA,
                "csrf_token": bili_jct,
                "csrf": bili_jct,
                "visit_id": "",
            }
            headers = {
                "User-Agent": self.X25KN_UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
                "Origin": "https://live.bilibili.com",
                "Referer": f"https://live.bilibili.com/{room_id}",
            }
            resp = requests.post(self.X25KN_X_URL, data=form, headers=headers, timeout=15)
            result = resp.json()
            if result.get("code") == 0 and result.get("data"):
                return result["data"]
            return {"_error": True, "code": result.get("code"), "message": result.get("message"), "raw": result}
        except Exception as e:
            return {"_error": True, "code": -1, "message": f"异常: {type(e).__name__}: {e}"}

    def x25kn_thread_func(self, account, room_id, area_id, parent_id, up_id, name, deadline=None):
        """X25Kn观看心跳线程：E接口进入后，按心跳间隔循环X接口"""
        # P1-F: deadline检查，超过目标时长自动停止
        if deadline and time.time() > deadline:
            self.log(f"  [{name}] X25Kn已超过deadline，不启动")
            return
        import uuid as uuid_lib
        buvid = self.x25kn_get_buvid(account)
        uuid_str = str(uuid_lib.uuid4())
        self.log(f"  [{name}] X25Kn获取LIVE_BUVID: {buvid[:20]}...")

        # E接口
        e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
        if not e_data or e_data.get("_error"):
            err_msg = ""
            if e_data and e_data.get("_error"):
                err_msg = f"（code={e_data.get('code')}, message={e_data.get('message')}）"
            self.log(f"  [{name}] ✗ X25Kn E接口失败{err_msg}，观看心跳未启动")
            return

        secret_key = e_data["secret_key"]
        secret_rule = e_data["secret_rule"]
        ets = e_data["timestamp"]
        heartbeat_interval = int(e_data.get("heartbeat_interval") or 60)
        if heartbeat_interval < 5 or heartbeat_interval > 300:
            heartbeat_interval = 60

        self.x25kn_state[name] = {
            "secret_key": secret_key, "secret_rule": secret_rule, "ets": ets,
            "seq": 0, "interval": heartbeat_interval, "buvid": buvid, "uuid": uuid_str,
            "beat_count": 0,
        }
        self.log(f"  [{name}] ✓ X25Kn E接口成功，rule={secret_rule}，间隔{heartbeat_interval}s")

        # 等待第一个心跳间隔
        for _ in range(heartbeat_interval):
            if self.x25kn_stop.get(name, False) or self.stop_flag["stop"]:
                return
            time.sleep(1)

        # 循环X接口
        consecutive_fail = 0
        while not self.x25kn_stop.get(name, False) and not self.stop_flag["stop"]:
            # P1-F: deadline检查，超过目标时长自动停止
            if deadline and time.time() > deadline:
                self.log(f"  [{name}] X25Kn已超过deadline，停止心跳")
                break
            state = self.x25kn_state.get(name)
            if not state:
                break
            next_seq = state["seq"] + 1
            result = self.x25kn_heartbeat(
                account, room_id, area_id, parent_id, up_id, next_seq,
                state["buvid"], state["uuid"], state["ets"],
                state["secret_key"], state["secret_rule"], state["interval"]
            )
            if result and not result.get("_error"):
                state["seq"] = next_seq
                state["secret_key"] = result.get("secret_key", state["secret_key"])
                state["secret_rule"] = result.get("secret_rule", state["secret_rule"])
                state["ets"] = result.get("timestamp", state["ets"])
                next_interval = int(result.get("heartbeat_interval") or state["interval"])
                if 5 <= next_interval <= 300:
                    state["interval"] = next_interval
                state["beat_count"] += 1
                consecutive_fail = 0
                # P2-I: 同步beat_count和heartbeat_interval到account_stats，供达标判断使用
                if name in self.account_stats:
                    self.account_stats[name]["beat_count"] = state["beat_count"]
                    self.account_stats[name]["heartbeat_interval"] = state["interval"]
                if state["beat_count"] % 2 == 0:
                    self.log(f"  [{name}] X25Kn心跳 #{state['beat_count']} 成功")
            else:
                consecutive_fail += 1
                err_msg = ""
                if result and result.get("_error"):
                    err_msg = f"（code={result.get('code')}, message={result.get('message')}）"
                self.log(f"  [{name}] X25Kn心跳失败{err_msg}（连续{consecutive_fail}次），重新E接口...")
                if consecutive_fail >= 3:
                    # 重新E接口
                    e_data = self.x25kn_enter(account, room_id, area_id, parent_id, up_id, buvid, uuid_str)
                    if e_data and not e_data.get("_error"):
                        state["secret_key"] = e_data["secret_key"]
                        state["secret_rule"] = e_data["secret_rule"]
                        state["ets"] = e_data["timestamp"]
                        state["seq"] = 0
                        consecutive_fail = 0
                        self.log(f"  [{name}] X25Kn已重新E接口")
                    else:
                        time.sleep(10)

            # 等待心跳间隔
            interval = state.get("interval", 60)
            for _ in range(interval):
                if self.x25kn_stop.get(name, False) or self.stop_flag["stop"]:
                    return
                time.sleep(1)

    def play_thread(self, account, room_id):
        """持续播放线程：模拟真实浏览器持续下载视频流"""
        name = account.get("name", "未知")
        cookie = self.get_cookie(account)
        headers = {
            **HEADERS,
            "Cookie": cookie,
            "Referer": f"https://live.bilibili.com/{room_id}",
            "Origin": "https://live.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        play_count = 0
        last_m3u8_refresh = 0
        current_ts_urls = []
        base_url = ""
        consecutive_404 = 0  # 连续视频流404计数
        stream_paused = False  # 播放流是否已暂停（连续404过多时暂停，心跳继续）
        self.log(f"  [{name}] 播放线程已启动")
        
        while not self.stop_flag["stop"] and self.running:
            try:
                # 每60秒刷新一次播放地址（直播流地址会变）
                now = time.time()
                if now - last_m3u8_refresh > 60 or not current_ts_urls:
                    self.log(f"  [{name}] 正在获取播放地址...")
                    success, play_url = self.get_play_url(account, room_id)
                    if not success:
                        self.log(f"  [{name}] 获取播放地址失败: {play_url}")
                        time.sleep(5)
                        continue
                    self.log(f"  [{name}] 播放地址获取成功: {play_url[:80]}...")
                    # flv直链：保持长连接持续读取（模拟真实播放器）
                    try:
                        self.log(f"  [{name}] 正在连接视频流...")
                        resp = requests.get(play_url, headers=headers, timeout=(10, 30), stream=True)
                        if resp.status_code != 200:
                            self.log(f"  [{name}] 视频流连接失败: HTTP {resp.status_code}")
                            resp.close()
                            # 连续404检测：直播间可能已关播
                            if resp.status_code == 404:
                                consecutive_404 += 1
                                # 第1次404就记录异常（避免用户看不到异常）
                                if consecutive_404 == 1:
                                    self.add_watch_anomaly("视频流404", f"视频流HTTP 404（第{consecutive_404}次），直播间{room_id}可能已关播或波动", account_name=name, room_id=str(room_id))
                                elif consecutive_404 == 3:
                                    self.add_watch_anomaly("直播间关播", f"视频流连续3次HTTP 404，直播间{room_id}可能已关播", account_name=name, room_id=str(room_id))
                                    self.log(f"  [{name}] ⚠ 连续3次404，判定直播间可能关播，已记录异常，加大重试间隔")
                                if consecutive_404 >= 10 and not stream_paused:
                                    stream_paused = True
                                    self.add_watch_anomaly("播放暂停", f"视频流连续{consecutive_404}次404，暂停播放线程（心跳继续）", account_name=name, room_id=str(room_id))
                                    self.log(f"  [{name}] ⚠ 连续{consecutive_404}次404，暂停播放线程（心跳继续保持）")
                            else:
                                consecutive_404 = 0
                            # 连续404时加大重试间隔：3次后30秒，暂停后60秒
                            wait_time = 5
                            if consecutive_404 >= 3:
                                wait_time = 30
                            if stream_paused:
                                wait_time = 60
                            time.sleep(wait_time)
                            continue
                        consecutive_404 = 0
                        if stream_paused:
                            stream_paused = False
                            self.log(f"  [{name}] ✓ 视频流恢复，解除暂停")
                        self.log(f"  [{name}] ✓ 视频流连接成功，开始播放...")
                        # P1-B/P1-C: 给socket设置1秒超时，使流读可中断，及时响应stop_flag
                        try:
                            import socket as _socket
                            resp.raw._fp.fp._sock.settimeout(1.0)
                        except Exception:
                            pass
                        # 持续读取流数据，保持连接不断开
                        bytes_read = 0
                        play_start = time.time()
                        while not self.stop_flag["stop"]:
                            try:
                                chunk = resp.raw.read(8192)
                                if not chunk:
                                    break
                                bytes_read += len(chunk)
                                play_count += 1
                                # 每下载约1MB打印一次
                                if bytes_read % 1048576 < 8192:
                                    elapsed = int(time.time() - play_start)
                                    self.log(f"  [{name}] 播放中，已下载{bytes_read//1024}KB，持续{elapsed}秒")
                                # 控制读取速度（约500KB/s，模拟正常播放）
                                time.sleep(0.016)
                                # 每60秒刷新一次播放地址
                                if time.time() - play_start > 60:
                                    break
                            except (_socket.timeout, OSError):
                                # P1-B/P1-C: 超时后继续检查stop_flag，不退出循环
                                continue
                            except Exception as e:
                                self.log(f"  [{name}] 读取流异常: {e}")
                                break
                        resp.close()
                        last_m3u8_refresh = time.time()
                        if self.stop_flag["stop"]:
                            break
                        continue
                    except Exception as e:
                        self.log(f"  [{name}] 视频流异常: {e}")
                        time.sleep(5)
                        continue
                    # m3u8格式
                    resp = requests.get(play_url, headers=headers, timeout=10)
                    if resp.status_code == 200 and "#EXTM3U" in resp.text:
                        lines = resp.text.split("\n")
                        current_ts_urls = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                        base_url = play_url.rsplit("/", 1)[0]
                        last_m3u8_refresh = now
                        self.log(f"  [{name}] 获取m3u8成功，{len(current_ts_urls)}个分片")
                    else:
                        self.log(f"  [{name}] m3u8请求失败: HTTP {resp.status_code}, content={resp.text[:100]}")
                        time.sleep(5)
                        continue
                
                # 持续下载ts分片（每5秒一个，模拟播放）
                if current_ts_urls:
                    # 轮流下载ts分片
                    ts_url = current_ts_urls[play_count % len(current_ts_urls)]
                    if not ts_url.startswith("http"):
                        ts_url = f"{base_url}/{ts_url}"
                    try:
                        ts_resp = requests.get(ts_url, headers=headers, timeout=8, stream=True)
                        if ts_resp.status_code == 200:
                            # 下载前100KB（模拟播放，不完整下载）
                            ts_resp.raw.read(102400)
                            play_count += 1
                            if play_count % 12 == 0:  # 每分钟打印一次
                                self.log(f"  [{name}] 持续播放中，已下载{play_count}个分片")
                    except Exception:
                        pass
                
                # 模拟播放速度：每5秒一个ts分片（每个ts约1-3秒）
                time.sleep(5)
            except Exception as e:
                self.log(f"  [{name}] 播放线程异常: {e}")
                time.sleep(3)
        
        self.log(f"  [{name}] 播放线程已停止")

    def start_play_threads(self, selected_accounts, room_ids):
        """为每个账户启动持续播放线程"""
        self.play_threads = []
        for acc in selected_accounts:
            for rid in room_ids:
                t = threading.Thread(target=self.play_thread, args=(acc, rid), daemon=True)
                t.start()
                self.play_threads.append(t)
                time.sleep(0.5)  # 错开启动，避免同时请求

    def start_watch(self):
        try:
            if self.running:
                self.log("⚠ 看播任务已在运行中，请勿重复点击")
                return
            room_ids = self._get_watch_room_ids()
            if not room_ids:
                messagebox.showwarning("提示", "请至少选择一个直播间（可在账户管理页面添加）", parent=self.winfo_toplevel())
                return
            # 从复选框获取选中账户
            selected_names = [name for name, var in self.account_vars.items() if var.get()]
            if not selected_names:
                messagebox.showwarning("提示", "请至少勾选一个账户", parent=self.winfo_toplevel())
                return
            selected_accounts = [acc for acc in self.account_mgr.accounts if acc.get("name", "") in selected_names]
            if not selected_accounts:
                messagebox.showwarning("提示", "未找到选中的账户", parent=self.winfo_toplevel())
                return
            self.running = True
            self.stop_flag["stop"] = False  # P1-A: 不换对象，只改key，防止旧线程复活
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            for bar, combo, del_btn in self.watch_room_bars:
                combo.config(state=tk.DISABLED)
                if del_btn is not None:
                    del_btn.config(state=tk.DISABLED)
            self.add_room_bar_btn.config(state=tk.DISABLED)
            self.duration_combo.config(state=tk.DISABLED)
            self.interval_combo.config(state=tk.DISABLED)
            # 禁用所有复选框和按钮
            for cb in self.account_checkbuttons:
                cb.config(state=tk.DISABLED)
            self.select_all_btn.config(state=tk.DISABLED)
            self.deselect_all_btn.config(state=tk.DISABLED)
            self.account_stats = {}
            for acc in selected_accounts:
                name = acc.get("name", "未知")
                # P2-I: 添加beat_count（服务端确认的心跳次数）和heartbeat_interval
                self.account_stats[name] = {"watch_seconds": 0, "heartbeat_count": 0, "play_count": 0, "beat_count": 0, "heartbeat_interval": 0, "status": "进入中", "last_heartbeat": None, "account": acc}
            room_display = ", ".join(room_ids)
            self.log(f"开始看播，直播间: {room_display}（共{len(room_ids)}个），账户: {len(selected_accounts)}个")
            self.log(f"目标时长: {self.duration_var.get()} 分钟，心跳间隔: {self.interval_var.get()} 秒")
            # 开始历史记录
            self.start_watch_record(room_ids, selected_accounts)
            # 启动快照定时器（5分钟后第一次）
            self.watch_snapshot_timer = self.after(300000, self.save_watch_snapshot)
            self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
            self.watch_thread.start()
        except Exception as e:
            import traceback
            self.log(f"[错误] start_watch异常: {e}")
            self.log(traceback.format_exc())
            # P0-B: 完整回滚UI状态
            self.running = False
            self.stop_flag["stop"] = True
            # 取消快照定时器
            try:
                if hasattr(self, 'watch_snapshot_timer') and self.watch_snapshot_timer:
                    self.after_cancel(self.watch_snapshot_timer)
            except Exception:
                pass
            # 结束记录（标记为启动失败）
            try:
                if self.current_watch_record:
                    self.finish_watch_record(status="启动失败")
                    self.current_watch_record = None
            except Exception:
                pass
            self._reset_watch_ui()
            messagebox.showerror("错误", f"启动看播失败: {e}", parent=self.winfo_toplevel())

    def stop_watch(self):
        if not self.running:
            return
        self.stop_flag["stop"] = True
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        for bar, combo, del_btn in self.watch_room_bars:
            combo.config(state="readonly")
            if del_btn is not None:
                del_btn.config(state=tk.NORMAL)
        self.add_room_bar_btn.config(state=tk.NORMAL)
        self.duration_combo.config(state="readonly")
        self.interval_combo.config(state="readonly")
        # 启用所有复选框和按钮
        for cb in self.account_checkbuttons:
            cb.config(state=tk.NORMAL)
        self.select_all_btn.config(state=tk.NORMAL)
        self.deselect_all_btn.config(state=tk.NORMAL)
        # 停止所有x25kn心跳线程
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        # 关闭所有WebSocket弹幕连接（异步，避免卡住UI）
        threading.Thread(target=self.close_all_ws, daemon=True).start()
        # 停止播放线程（stop_flag已设置，线程会自动退出）
        for name in self.account_stats:
            self.account_stats[name]["status"] = "已停止"
        self.refresh_status_tree()
        self.log("已停止看播")
        # 结束历史记录
        if self.current_watch_record:
            self.finish_watch_record(status="已停止")

    def _watch_loop(self, room_ids, selected_accounts):
        import random
        base_interval = self.interval_var.get()
        target_seconds = self.duration_var.get() * 60
        # P1-5: 用monotonic记录开始时间，替代sleep累加计时
        watch_start_time = time.monotonic()
        # 进入所有直播间
        for acc in selected_accounts:
            if self.stop_flag["stop"]:
                break
            name = acc.get("name", "未知")
            entered_count = 0
            for rid in room_ids:
                if self.stop_flag["stop"]:
                    break
                self.log(f"  [{name}] 正在进入直播间 {rid}...")
                success, msg = self.enter_room(acc, rid)
                if success:
                    entered_count += 1
                    self.log(f"  [{name}] ✓ 直播间 {rid} {msg}")
                else:
                    self.log(f"  [{name}] ✗ 直播间 {rid} {msg}")
                    self.add_watch_anomaly("进入直播间失败", msg, account_name=name, room_id=rid)
                time.sleep(random.uniform(0.5, 1.5))
            if entered_count > 0:
                self.account_stats[name]["status"] = "观看中"
                self.account_stats[name]["heartbeat_count"] = entered_count
                self.account_stats[name]["ws_connected"] = False
                # 获取房间信息（浏览器加载页面时会调用）
                try:
                    self.get_room_info(room_ids[0], acc)
                except Exception as e:
                    self.log(f"  [{name}] 获取房间信息异常: {e}")
                # 建立WebSocket弹幕连接（对第一个直播间建立连接，让账户出现在在线观众列表）
                if WEBSOCKET_AVAILABLE and room_ids:
                    self.log(f"  [{name}] 正在建立弹幕连接...")
                    try:
                        ws_client = self.connect_ws_danmaku(acc, room_ids[0])
                        if ws_client:
                            self.ws_clients[name] = ws_client
                            self.log(f"  [{name}] ✓ 弹幕连接线程已启动")
                        else:
                            self.log(f"  [{name}] ✗ 弹幕连接建立失败（返回None）")
                    except Exception as e:
                        self.log(f"  [{name}] ✗ 弹幕连接异常: {e}")
                elif not WEBSOCKET_AVAILABLE:
                    self.log(f"  [{name}] ⚠ websocket-client不可用，跳过弹幕连接")
            else:
                self.account_stats[name]["status"] = "进入失败"
            self.refresh_status_tree()
            time.sleep(random.uniform(1, 2))
        # 启动X25Kn观看心跳上报线程（v4.0.0核心功能：让B站统计系统认为在"观看"）
        self.log("启动X25Kn观看心跳上报...")
        # 获取房间区域信息（用第一个账户获取一次即可）
        area_id, parent_id, up_id = self.x25kn_get_area_info(selected_accounts[0], room_ids[0])
        self.log(f"  房间区域: parent_id={parent_id}, area_id={area_id}, up_id={up_id}")
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            stats = self.account_stats.get(name)
            if not stats or stats["status"] != "观看中":
                continue
            self.x25kn_stop[name] = False
            # P1-F: 传入deadline，超过目标时长+60秒缓冲后自动停止
            x25kn_deadline = time.time() + target_seconds + 60
            t = threading.Thread(target=self.x25kn_thread_func,
                                 args=(acc, room_ids[0], area_id, parent_id, up_id, name, x25kn_deadline),
                                 daemon=True)
            self.x25kn_threads[name] = t
            t.start()
            time.sleep(0.5)

        # 启动持续播放线程（模拟真实浏览器播放）
        self.log("启动持续播放线程...")
        self.start_play_threads(selected_accounts, room_ids)
        # 心跳循环
        last_refresh_time = 0  # P2-F: 防止同一秒重复刷新
        last_ws_check_time = 0  # P2-F: 防止同一秒重复检查WS
        while not self.stop_flag["stop"]:
            # v6.2.0 修复：每轮循环先刷新本地计时（monotonic，不受系统改时间影响）
            _elapsed = int(time.monotonic() - watch_start_time)
            for _n, _s in self.account_stats.items():
                if _s.get("status") == "观看中":
                    _s["watch_seconds"] = _elapsed

            all_done = True
            has_watching = False
            has_failed = False
            for name, stats in self.account_stats.items():
                if stats["status"] == "观看中":
                    has_watching = True
                    # v6.2.0 修复：两个计时源取"任一达标"即算完成。
                    # 原来只用 beat_count * beat_interval（服务端确认时长）判断，
                    # 但 watch_seconds（local monotonic，也是界面显示值）会先到达目标，
                    # 两者相差一个心跳周期（通常60秒），导致界面显示"已观看10分53秒"
                    # 已超目标，但 beat_count 只有 9 次（540<600）判不达标，于是永远不停。
                    _watch_sec = stats.get("watch_seconds", 0)
                    _beat_count = stats.get("beat_count", 0)
                    _beat_interval = stats.get("heartbeat_interval", 0)
                    _confirmed_sec = _beat_count * _beat_interval if (_beat_count > 0 and _beat_interval > 0) else 0
                    if _watch_sec < target_seconds and _confirmed_sec < target_seconds:
                        all_done = False
                        break
                elif stats["status"] == "进入失败":
                    has_failed = True
            # P2-A: 如果没有观看中的账户且有进入失败的，不应标记为完成
            if not has_watching and has_failed:
                self.log("⚠ 所有账户均进入失败，任务终止")
                break
            if all_done and has_watching:
                self.log("所有账户已达到目标观看时长，自动停止")
                break
            interval = base_interval * random.uniform(0.8, 1.2)
            wait_segments = int(interval)
            for _ in range(wait_segments):
                if self.stop_flag["stop"]:
                    break
                time.sleep(1)
                for name, stats in self.account_stats.items():
                    if stats["status"] == "观看中":
                        # P1-5: 用monotonic差值计算真实观看时长，替代sleep累加
                        stats["watch_seconds"] = int(time.monotonic() - watch_start_time)
                _now_sec = int(time.time())
                if _now_sec % 10 == 0 and _now_sec != last_refresh_time:
                    last_refresh_time = _now_sec
                    self.refresh_status_tree()
                # 每60秒检查一次弹幕连接状态
                if _now_sec % 60 == 0 and _now_sec != last_ws_check_time:
                    last_ws_check_time = _now_sec
                    ws_connected = sum(1 for s in self.account_stats.values() if s.get("ws_connected", False))
                    ws_total = len(self.account_stats)
                    if ws_total > 0:
                        self.log(f"弹幕连接状态: {ws_connected}/{ws_total} 个在线")
                # 播放模拟已移到独立线程（持续播放）
            if self.stop_flag["stop"]:
                break
            for acc in selected_accounts:
                if self.stop_flag["stop"]:
                    break
                name = acc.get("name", "未知")
                stats = self.account_stats.get(name)
                if not stats or stats["status"] != "观看中":
                    continue
                if stats["watch_seconds"] >= target_seconds:
                    stats["status"] = "已完成"
                    self.log(f"  [{name}] ✓ 已达到目标时长 ({self.duration_var.get()}分钟)")
                    self.refresh_status_tree()
                    continue
                # 对每个直播间发送心跳
                for rid in room_ids:
                    if self.stop_flag["stop"]:
                        break
                    success, msg = self.send_heartbeat(acc, rid)
                    stats["heartbeat_count"] += 1
                    stats["last_heartbeat"] = datetime.now()
                    if not success:
                        self.log(f"  [{name}] 直播间{rid} 心跳失败: {msg}")
                        self.add_watch_anomaly("心跳失败", msg, account_name=name, room_id=rid)
                    time.sleep(random.uniform(0.3, 0.8))
                # 播放模拟在独立线程中持续执行
                if stats["heartbeat_count"] % (5 * len(room_ids)) < len(room_ids):
                    watch_min = stats["watch_seconds"] // 60
                    self.log(f"  [{name}] 心跳累计 #{stats['heartbeat_count']}，已观看 {watch_min} 分钟")
                self.refresh_status_tree()
                time.sleep(random.uniform(0.5, 2))
        self.running = False
        self.after(100, self._on_watch_finished)

    def _reset_watch_ui(self):
        """P0-B: 统一的UI复位逻辑，供正常结束和异常回滚共用"""
        try:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        except Exception:
            pass
        try:
            for bar, combo, del_btn in self.watch_room_bars:
                combo.config(state="readonly")
                if del_btn is not None:
                    del_btn.config(state=tk.NORMAL)
        except Exception:
            pass
        try:
            self.add_room_bar_btn.config(state=tk.NORMAL)
            self.duration_combo.config(state="readonly")
            self.interval_combo.config(state="readonly")
        except Exception:
            pass
        try:
            for cb in self.account_checkbuttons:
                cb.config(state=tk.NORMAL)
            self.select_all_btn.config(state=tk.NORMAL)
            self.deselect_all_btn.config(state=tk.NORMAL)
        except Exception:
            pass

    def _on_watch_finished(self):
        self.stop_flag["stop"] = True
        # 结束历史记录（已完成状态）
        if self.current_watch_record:
            self.finish_watch_record(status="已完成")
        for name in self.x25kn_stop:
            self.x25kn_stop[name] = True
        self.x25kn_threads = {}
        self.x25kn_state = {}
        self.close_all_ws()
        self._reset_watch_ui()

    # ========== 送礼功能 ==========
    def get_gift_id(self, account):
        """查询牛哇牛哇的gift_id（优先选bag_gift=0可直接用电池送的）"""
        if self.gift_id_cache:
            return self.gift_id_cache
        try:
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            # 获取礼物列表
            url = "https://api.live.bilibili.com/xlive/web-room/v1/giftPanel/giftConfig?platform=pc"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                gift_list = data.get("data", {}).get("list", [])
                # 优先找bag_gift=0（可直接用电池送）的牛哇牛哇
                for gift in gift_list:
                    name = gift.get("name", "")
                    bag_gift = gift.get("bag_gift", 0)
                    if ("牛哇" in name or "牛蛙" in name) and bag_gift == 0:
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {name} (id={gift['id']}, 价格={gift.get('price', 0)}, 可直接电池送)")
                        return gift["id"]
                # 找不到bag_gift=0的，找任意牛哇牛哇
                for gift in gift_list:
                    name = gift.get("name", "")
                    if "牛哇" in name or "牛蛙" in name:
                        self.gift_id_cache = gift["id"]
                        self.log(f"  找到礼物: {name} (id={gift['id']}, 价格={gift.get('price', 0)})")
                        return gift["id"]
            self.log("  ⚠ 未找到牛哇牛哇礼物，使用默认id=31039")
            self.gift_id_cache = 31039
            return 31039
        except Exception as e:
            self.log(f"  ⚠ 查询礼物ID失败: {e}，使用默认id=31039")
            self.gift_id_cache = 31039
            return 31039

    def get_room_info(self, room_id, account):
        """获取直播间信息（ruid等）"""
        try:
            sessdata = account.get("SESSDATA", "")
            cookies = {"SESSDATA": sessdata}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {})
            return {}
        except Exception:
            return {}

    def send_gift(self, account, room_id, gift_id, gift_num):
        """发送礼物（直接用电池购买送出）"""
        try:
            name = account.get("name", "未知")
            sessdata = account.get("SESSDATA", "")
            bili_jct = account.get("bili_jct", "")
            uid = account.get("uid", "") or account.get("DedeUserID", "")
            cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
            # 获取直播间ruid
            room_info = self.get_room_info(room_id, account)
            ruid = room_info.get("uid", "")
            # 送礼接口（直接用电池送，不是背包送礼）
            url = "https://api.live.bilibili.com/gift/v2/live/send"
            data = {
                "uid": uid,
                "gift_id": gift_id,
                "ruid": ruid,
                "gift_num": gift_num,
                "platform": "pc",
                "biz_code": "live",
                "biz_id": room_id,
                "rnd": int(time.time()),
                "storm_beat_id": "0",
                "metadata": "",
                "price": "100",
                "coin_type": "gold",
                "csrf_token": bili_jct,
                "csrf": bili_jct,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Origin": "https://live.bilibili.com",
            }
            resp = requests.post(url, data=data, cookies=cookies, headers=headers, timeout=10)
            result = resp.json()
            code = result.get("code", -1)
            msg = result.get("message", "") or result.get("msg", "")
            # 错误码中文说明
            error_map = {
                200007: "该房间不支持投喂该礼物",
                200010: "该礼物仅限从包裹中送出",
                200013: "余额不足（电池不够）",
                200014: "参数错误",
                200036: "该道具不能在这个房间投喂",
                75255: "库存已经使用完",
                -401: "请先登录（cookies失效）",
            }
            if code == 0:
                return True, "送礼成功"
            else:
                detail = error_map.get(code, msg)
                return False, f"[{code}] {detail}"
        except Exception as e:
            return False, f"网络异常: {e}"

    def start_gift(self):
        """开始送礼"""
        # 防重复调用
        if self.gift_running:
            self.log("⚠ 送礼任务已在运行中，请勿重复点击")
            return
        room_id = self._get_gift_room_id()
        if not room_id:
            self.log("✗ 请先选择直播间（可在账户管理页面添加直播间）")
            return
        # 获取选中的送礼账户
        selected_name = self.gift_account_combo.get()
        selected_accounts = []
        for acc in self.account_mgr.accounts:
            if acc.get("name") == selected_name:
                selected_accounts.append(acc)
                break
        if not selected_accounts:
            self.log("✗ 请先选择送礼账户")
            return
        gift_num = self.gift_num_var.get()
        interval = self.gift_interval_var.get()
        max_count = self.gift_count_var.get()
        # 检查次数
        if max_count <= 0:
            self.log("✗ 送礼次数必须大于0，请先设置送礼次数")
            return
        # 计算总消耗电池数（牛蛙牛蛙1电池/个）
        total_battery = len(selected_accounts) * max_count * gift_num
        # 确认弹窗，防止误触
        confirm = messagebox.askyesno("送礼确认",
            f"当前操作共计消耗 {total_battery} 电池\n\n"
            f"账户数: {len(selected_accounts)} 个\n"
            f"送礼次数: {max_count} 次\n"
            f"每次数量: 牛蛙牛蛙x{gift_num}\n"
            f"单个价格: 1电池/个\n\n"
            f"是否继续？",
            icon="warning", parent=self.winfo_toplevel())
        if not confirm:
            self.log("⏹ 已取消送礼操作")
            return
        self.save_gift_config()
        self.gift_running = True
        self.gift_start_btn.config(state=tk.DISABLED)
        self.gift_stop_btn.config(state=tk.NORMAL)
        self.log(f"▶ 开始送礼: 直播间{room_id}, 牛蛙牛蛙x{gift_num}, 间隔{interval}秒, 次数{max_count}")
        self.log(f"  共 {len(selected_accounts)} 个账户参与送礼")
        # 为每个账户启动独立线程
        for acc in selected_accounts:
            name = acc.get("name", "未知")
            self.gift_stop[name] = False
            t = threading.Thread(target=self._gift_worker, args=(acc, room_id, gift_num, interval, max_count), daemon=True)
            self.gift_threads[name] = t
            t.start()
            time.sleep(0.5)  # 错开启动

    def _gift_worker(self, account, room_id, gift_num, interval, max_count):
        """送礼工作线程"""
        name = account.get("name", "未知")
        count = 0
        try:
            # 先查询gift_id
            gift_id = self.get_gift_id(account)
            while not self.gift_stop.get(name, True) and self.gift_running:
                if count >= max_count:
                    self.log(f"  [{name}] ✓ 已达到最大送礼次数 ({max_count}次)")
                    break
                success, msg = self.send_gift(account, room_id, gift_id, gift_num)
                count += 1
                if success:
                    self.log(f"  [{name}] 第{count}次: ✓ {msg} (牛蛙牛蛙x{gift_num})")
                else:
                    self.log(f"  [{name}] 第{count}次: ✗ {msg}")
                    # P1-D/P1-10: 余额不足时立即停止该账户送礼，避免无效重试
                    if "余额不足" in msg or "200013" in msg or "电池不够" in msg:
                        self.log(f"  [{name}] ⚠ 电池余额不足，停止该账户送礼")
                        break
                # 等待间隔
                for _ in range(int(interval * 10)):
                    if self.gift_stop.get(name, True) or not self.gift_running:
                        break
                    time.sleep(0.1)
        except Exception as e:
            self.log(f"  [{name}] 送礼线程异常: {e}")
        finally:
            self.log(f"  [{name}] 送礼结束，共尝试 {count} 次")
            self.gift_threads.pop(name, None)
            # 检查是否所有线程都结束了
            if not self.gift_threads:
                self.after(100, self._on_gift_finished)

    def _on_gift_finished(self):
        """送礼全部结束"""
        self.gift_running = False
        self.gift_start_btn.config(state=tk.NORMAL)
        self.gift_stop_btn.config(state=tk.DISABLED)
        self.log("✓ 所有账户送礼已结束")

    def stop_gift(self):
        """停止送礼"""
        self.gift_running = False
        for name in self.gift_stop:
            self.gift_stop[name] = True
        self.log("⏹ 正在停止所有送礼线程...")
        self.gift_start_btn.config(state=tk.NORMAL)
        self.gift_stop_btn.config(state=tk.DISABLED)
        self.refresh_status_tree()
        self.log("送礼任务结束")
