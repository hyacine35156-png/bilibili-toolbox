#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站直播间自动发弹幕工具 - GUI多账户版
功能：多账户管理、一键发送、实时日志、弹幕列表管理
依赖：pip install requests
运行：python main_gui.py
"""

import json
import time
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

import requests

# ========== 常量 ==========
BASE_DIR = Path(__file__).parent
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
DANMAKU_FILE = BASE_DIR / "danmaku_list.txt"

SEND_API = "https://api.live.bilibili.com/msg/send"
USER_INFO_API = "https://api.bilibili.com/x/web-interface/nav"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}


# ========== 数据管理 ==========
class AccountManager:
    """账户管理：加载、保存、增删账户"""

    def __init__(self):
        self.accounts = []
        self.load()

    def load(self):
        if ACCOUNTS_FILE.exists():
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    self.accounts = json.load(f)
            except Exception:
                self.accounts = []
        else:
            self.accounts = []

    def save(self):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def add_account(self, name, sessdata, bili_jct, dede_userid=""):
        """添加账户，返回(是否成功, 消息)"""
        # 检查重名
        for acc in self.accounts:
            if acc["name"] == name:
                return False, f"账户名「{name}」已存在"

        # 验证cookie
        cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
        if dede_userid:
            cookie_str += f"; DedeUserID={dede_userid}"

        ok, msg = verify_login(cookie_str)
        if not ok:
            return False, f"登录验证失败: {msg}"

        account = {
            "name": name,
            "SESSDATA": sessdata,
            "bili_jct": bili_jct,
            "DedeUserID": dede_userid,
            "username": msg,  # 验证成功时msg是用户名
        }
        self.accounts.append(account)
        self.save()
        return True, f"账户「{name}」添加成功（登录用户: {msg}）"

    def delete_account(self, name):
        self.accounts = [a for a in self.accounts if a["name"] != name]
        self.save()

    def get_account(self, name):
        for acc in self.accounts:
            if acc["name"] == name:
                return acc
        return None

    def get_cookie_string(self, name):
        acc = self.get_account(name)
        if not acc:
            return ""
        parts = [f"SESSDATA={acc['SESSDATA']}", f"bili_jct={acc['bili_jct']}"]
        if acc.get("DedeUserID"):
            parts.append(f"DedeUserID={acc['DedeUserID']}")
        return "; ".join(parts)


def verify_login(cookie_str):
    """验证登录状态，返回(是否成功, 用户名或错误信息)"""
    headers = {**HEADERS, "Cookie": cookie_str}
    try:
        resp = requests.get(USER_INFO_API, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            return True, data["data"].get("uname", "未知用户")
        else:
            return False, data.get("message", "cookie无效或已过期")
    except Exception as e:
        return False, f"网络异常: {e}"


def send_danmaku(cookie_str, csrf, room_id, msg):
    """发送一条弹幕，返回(是否成功, 消息)"""
    headers = {**HEADERS, "Cookie": cookie_str}
    payload = {
        "csrf": csrf,
        "roomid": room_id,
        "msg": msg,
        "rnd": int(time.time()),
        "color": 16777215,
        "fontsize": 25,
        "mode": 1,
        "bubble": 0,
    }
    try:
        resp = requests.post(SEND_API, data=payload, headers=headers, timeout=10)
        data = resp.json()
        if data.get("code") == 0:
            return True, "发送成功"
        else:
            return False, f"[{data.get('code')}] {data.get('message', '未知错误')}"
    except Exception as e:
        return False, f"网络异常: {e}"


# ========== 添加账户对话框 ==========
class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.geometry("480x380")
        self.resizable(False, False)
        self.on_add = on_add
        self.result = None

        # 居中
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="账户备注名（如：小号1）:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=1, column=0, sticky=tk.W, pady=(0, 15))

        ttk.Label(frame, text="SESSDATA:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.sess_entry = ttk.Entry(frame, width=40, show="*")
        self.sess_entry.grid(row=3, column=0, sticky=tk.W, pady=(0, 15))

        ttk.Label(frame, text="bili_jct:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.jct_entry = ttk.Entry(frame, width=40, show="*")
        self.jct_entry.grid(row=5, column=0, sticky=tk.W, pady=(0, 15))

        ttk.Label(frame, text="DedeUserID（可选）:").grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        self.dede_entry = ttk.Entry(frame, width=40)
        self.dede_entry.grid(row=7, column=0, sticky=tk.W, pady=(0, 20))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, sticky=tk.EW)
        ttk.Button(btn_frame, text="显示/隐藏", command=self.toggle_show).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="验证并添加", command=self.on_submit).pack(side=tk.RIGHT)

    def toggle_show(self):
        current = self.sess_entry.cget("show")
        new = "" if current == "*" else "*"
        self.sess_entry.config(show=new)
        self.jct_entry.config(show=new)

    def on_submit(self):
        name = self.name_entry.get().strip()
        sessdata = self.sess_entry.get().strip()
        bili_jct = self.jct_entry.get().strip()
        dede = self.dede_entry.get().strip()

        if not name:
            messagebox.showwarning("提示", "请填写账户备注名")
            return
        if not sessdata or not bili_jct:
            messagebox.showwarning("提示", "SESSDATA 和 bili_jct 不能为空")
            return

        if self.on_add:
            ok, msg = self.on_add(name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)


# ========== 主界面 ==========
class DanmakuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("B站自动发弹幕工具 - 多账户版")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        self.account_mgr = AccountManager()
        self.danmaku_list = self.load_danmaku()
        self.running = False
        self.send_thread = None

        self.build_ui()
        self.refresh_account_list()
        self.refresh_danmaku_list()
        self.log("程序启动，已加载 " + str(len(self.account_mgr.accounts)) + " 个账户，" + str(len(self.danmaku_list)) + " 条弹幕")

    def build_ui(self):
        # 顶部：账户管理 + 发送设置
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        # 左侧：账户管理
        left_frame = ttk.LabelFrame(top_frame, text="账户管理", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.account_listbox = tk.Listbox(left_frame, width=22, height=8, exportselection=False)
        self.account_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.account_listbox.bind("<<ListboxSelect>>", self.on_account_select)

        acc_btn_frame = ttk.Frame(left_frame)
        acc_btn_frame.pack(fill=tk.X)
        ttk.Button(acc_btn_frame, text="添加账户", command=self.add_account).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(acc_btn_frame, text="删除", command=self.delete_account).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        ttk.Button(left_frame, text="验证当前账户登录", command=self.verify_current_account).pack(fill=tk.X, pady=(8, 0))

        self.account_info_label = ttk.Label(left_frame, text="未选择账户", foreground="gray", wraplength=150)
        self.account_info_label.pack(fill=tk.X, pady=(8, 0))

        # 右侧：发送设置
        right_frame = ttk.LabelFrame(top_frame, text="发送设置", padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        settings_grid = ttk.Frame(right_frame)
        settings_grid.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(settings_grid, text="直播间号:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=3)
        self.room_entry = ttk.Entry(settings_grid, width=15)
        self.room_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20), pady=3)

        ttk.Label(settings_grid, text="间隔(秒):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5), pady=3)
        self.interval_min_entry = ttk.Entry(settings_grid, width=5)
        self.interval_min_entry.insert(0, "5")
        self.interval_min_entry.grid(row=0, column=3, sticky=tk.W, pady=3)
        ttk.Label(settings_grid, text="-").grid(row=0, column=4, padx=2, pady=3)
        self.interval_max_entry = ttk.Entry(settings_grid, width=5)
        self.interval_max_entry.insert(0, "10")
        self.interval_max_entry.grid(row=0, column=5, sticky=tk.W, pady=3)

        ttk.Label(settings_grid, text="发送模式:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=3)
        self.mode_var = tk.StringVar(value="random")
        ttk.Radiobutton(settings_grid, text="随机", variable=self.mode_var, value="random").grid(row=1, column=1, sticky=tk.W, pady=3)
        ttk.Radiobutton(settings_grid, text="顺序", variable=self.mode_var, value="sequence").grid(row=1, column=2, sticky=tk.W, pady=3)

        # 弹幕列表
        danmaku_frame = ttk.Frame(right_frame)
        danmaku_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(danmaku_frame, text="弹幕列表（每行一条）:").pack(anchor=tk.W, pady=(0, 5))

        self.danmaku_text = scrolledtext.ScrolledText(danmaku_frame, height=6, wrap=tk.WORD)
        self.danmaku_text.pack(fill=tk.BOTH, expand=True)

        danmaku_btn_frame = ttk.Frame(danmaku_frame)
        danmaku_btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(danmaku_btn_frame, text="保存弹幕列表", command=self.save_danmaku).pack(side=tk.LEFT)

        # 底部：日志 + 控制按钮
        bottom_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(bottom_frame, text="运行日志:").pack(anchor=tk.W, pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 控制按钮
        ctrl_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        ctrl_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(ctrl_frame, text="▶ 启动发送", command=self.start_sending)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(ctrl_frame, text="■ 停止发送", command=self.stop_sending, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(ctrl_frame, text="状态: 未运行", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)

    # ---------- 账户管理 ----------
    def refresh_account_list(self):
        self.account_listbox.delete(0, tk.END)
        for acc in self.account_mgr.accounts:
            display = f"{acc['name']} ({acc.get('username', '?')})"
            self.account_listbox.insert(tk.END, display)

    def on_account_select(self, event):
        selection = self.account_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        acc = self.account_mgr.accounts[idx]
        self.account_info_label.config(
            text=f"当前: {acc['name']}\n用户: {acc.get('username', '未知')}\nDedeID: {acc.get('DedeUserID', '未设置')}",
            foreground="black"
        )

    def get_current_account(self):
        selection = self.account_listbox.curselection()
        if not selection:
            return None
        return self.account_mgr.accounts[selection[0]]

    def add_account(self):
        dialog = AddAccountDialog(self.root, on_add=self.account_mgr.add_account)
        self.root.wait_window(dialog)
        self.refresh_account_list()

    def delete_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择要删除的账户")
            return
        if messagebox.askyesno("确认", f"确定删除账户「{acc['name']}」吗？"):
            self.account_mgr.delete_account(acc["name"])
            self.refresh_account_list()
            self.account_info_label.config(text="未选择账户", foreground="gray")
            self.log(f"已删除账户: {acc['name']}")

    def verify_current_account(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择账户")
            return
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        ok, msg = verify_login(cookie_str)
        if ok:
            messagebox.showinfo("验证成功", f"账户「{acc['name']}」登录有效\n当前用户: {msg}")
            self.log(f"账户「{acc['name']}」验证成功，用户: {msg}")
        else:
            messagebox.showerror("验证失败", f"账户「{acc['name']}」验证失败: {msg}")
            self.log(f"账户「{acc['name']}」验证失败: {msg}")

    # ---------- 弹幕列表 ----------
    def load_danmaku(self):
        if DANMAKU_FILE.exists():
            with open(DANMAKU_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return ["666", "主播好强", "来了来了"]

    def save_danmaku(self):
        content = self.danmaku_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        with open(DANMAKU_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.danmaku_list = lines
        self.log(f"弹幕列表已保存，共 {len(lines)} 条")
        messagebox.showinfo("成功", f"弹幕列表已保存，共 {len(lines)} 条")

    def refresh_danmaku_list(self):
        self.danmaku_text.delete("1.0", tk.END)
        self.danmaku_text.insert("1.0", "\n".join(self.danmaku_list))

    # ---------- 日志 ----------
    def log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ---------- 发送控制 ----------
    def start_sending(self):
        acc = self.get_current_account()
        if not acc:
            messagebox.showwarning("提示", "请先选择一个账户")
            return

        room_id = self.room_entry.get().strip()
        if not room_id or not room_id.isdigit():
            messagebox.showwarning("提示", "请输入有效的直播间号（数字）")
            return

        # 重新读取弹幕列表
        content = self.danmaku_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            messagebox.showwarning("提示", "弹幕列表为空，请先添加弹幕内容")
            return
        self.danmaku_list = lines

        try:
            interval_min = float(self.interval_min_entry.get())
            interval_max = float(self.interval_max_entry.get())
            if interval_min <= 0 or interval_max <= 0 or interval_min > interval_max:
                raise ValueError
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的发送间隔（秒），且最小值 ≤ 最大值")
            return

        # 验证登录
        cookie_str = self.account_mgr.get_cookie_string(acc["name"])
        ok, msg = verify_login(cookie_str)
        if not ok:
            messagebox.showerror("登录失效", f"账户「{acc['name']}」登录验证失败: {msg}\n请更新cookie后重试")
            return

        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"状态: 运行中（账户: {acc['name']}）", foreground="green")

        self.log(f"===== 启动发送 =====")
        self.log(f"账户: {acc['name']} ({msg})")
        self.log(f"直播间: {room_id}")
        self.log(f"弹幕数量: {len(self.danmaku_list)}")
        self.log(f"发送间隔: {interval_min}-{interval_max} 秒")
        self.log(f"发送模式: {'随机' if self.mode_var.get() == 'random' else '顺序'}")

        self.send_thread = threading.Thread(
            target=self.send_loop,
            args=(acc, int(room_id), interval_min, interval_max),
            daemon=True
        )
        self.send_thread.start()

    def stop_sending(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 已停止", foreground="gray")
        self.log("===== 已停止发送 =====")

    def send_loop(self, account, room_id, interval_min, interval_max):
        """弹幕发送循环（后台线程）"""
        cookie_str = self.account_mgr.get_cookie_string(account["name"])
        csrf = account["bili_jct"]
        mode = self.mode_var.get()
        index = 0
        send_count = 0
        fail_count = 0

        while self.running:
            # 选取弹幕
            if mode == "random":
                msg = random.choice(self.danmaku_list)
            else:
                msg = self.danmaku_list[index % len(self.danmaku_list)]
                index += 1

            # 发送（带重试）
            success = False
            for retry in range(3):
                if not self.running:
                    break
                ok, result = send_danmaku(cookie_str, csrf, room_id, msg)
                if ok:
                    success = True
                    send_count += 1
                    fail_count = 0
                    self.log(f"✓ 发送成功 ({send_count}): {msg}")
                    break
                else:
                    if retry < 2:
                        self.log(f"  第{retry+1}次重试: {result}")
                        time.sleep(random.uniform(2, 4))

            if not success:
                fail_count += 1
                self.log(f"✗ 发送失败 ({fail_count}): {msg} - {result}")
                if fail_count >= 5:
                    self.log("连续失败5次，自动停止")
                    self.root.after(0, self.stop_sending)
                    break

            # 间隔等待（分段检查，方便快速停止）
            wait_time = random.uniform(interval_min, interval_max)
            waited = 0
            while waited < wait_time and self.running:
                time.sleep(0.5)
                waited += 0.5

        self.log(f"本次发送结束，共成功发送 {send_count} 条")


# ========== 入口 ==========
def main():
    root = tk.Tk()

    # 设置主题
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    app = DanmakuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
