# -*- coding: utf-8 -*-
"""账户添加/编辑对话框。"""

import tkinter as tk
from tkinter import messagebox

from config import COLORS
from widgets import DarkButton, DarkEntry
from bili_api import verify_login


class AddAccountDialog(tk.Toplevel):
    def __init__(self, parent, on_add=None):
        super().__init__(parent)
        self.title("添加B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.on_add = on_add

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(frame, text="添加B站账户", bg=COLORS["bg_dark"],
                         fg=COLORS["accent"], font=("微软雅黑", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 15))

        def add_field(label_text, show=None):
            lbl = tk.Label(frame, text=label_text, bg=COLORS["bg_dark"],
                           fg=COLORS["text_secondary"], font=("微软雅黑", 9))
            lbl.pack(anchor=tk.W, pady=(8, 3))
            entry = DarkEntry(frame, width=42)
            if show:
                entry.config(show=show)
            entry.pack(anchor=tk.W, pady=(0, 5))
            return entry

        self.name_entry = add_field("账户备注名（如：小号1）")
        self.sess_entry = add_field("SESSDATA", show="*")
        self.jct_entry = add_field("bili_jct", show="*")
        self.dede_entry = add_field("DedeUserID（可选）")

        btn_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        DarkButton(btn_frame, "显示/隐藏", command=self.toggle_show,
                   width=150, height=42, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT)
        DarkButton(btn_frame, "取消", command=self.destroy,
                   width=150, height=42, bg_color="#555577", text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(btn_frame, "验证并添加", command=self.on_submit,
                   width=180, height=42).pack(side=tk.RIGHT)

        # 确保窗口大小正确（在所有组件创建后设置）
        self.update_idletasks()
        self.geometry("600x600")
        self.minsize(600, 600)
        self.resizable(False, False)
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 300
        y = (self.winfo_screenheight() // 2) - 300
        self.geometry(f"600x600+{x}+{y}")
        self.grab_set()

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
        if not sessdata or not bili_jct:
            messagebox.showwarning("提示", "SESSDATA 和 bili_jct 不能为空")
            return
        if self.on_add:
            # 备注名为空时，先验证获取用户名，默认使用用户名作为备注
            if not name:
                cookie_str = f"SESSDATA={sessdata}; bili_jct={bili_jct}"
                if dede:
                    cookie_str += f"; DedeUserID={dede}"
                ok, msg = verify_login(cookie_str)
                if not ok:
                    messagebox.showwarning("提示", f"登录验证失败: {msg}")
                    return
                name = msg  # 默认使用B站用户名作为备注
            ok, msg = self.on_add(name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)


class EditAccountDialog(tk.Toplevel):
    """编辑账户对话框（cookie失效时禁止修改）"""
    def __init__(self, parent, account, on_update=None):
        super().__init__(parent)
        self.title("编辑B站账户")
        self.configure(bg=COLORS["bg_dark"])
        self.account = account
        self.on_update = on_update
        self.old_name = account["name"]

        frame = tk.Frame(self, bg=COLORS["bg_dark"], padx=25, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(frame, text="编辑B站账户", bg=COLORS["bg_dark"],
                         fg=COLORS["accent"], font=("微软雅黑", 14, "bold"))
        title.pack(anchor=tk.W, pady=(0, 10))

        current_user = account.get("username", "未知")
        tk.Label(frame, text=f"当前登录用户: {current_user}", bg=COLORS["bg_dark"],
                 fg=COLORS["text_muted"], font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 10))

        def add_field(label_text, show=None, default=""):
            lbl = tk.Label(frame, text=label_text, bg=COLORS["bg_dark"],
                           fg=COLORS["text_secondary"], font=("微软雅黑", 9))
            lbl.pack(anchor=tk.W, pady=(8, 3))
            entry = DarkEntry(frame, width=42)
            if show:
                entry.config(show=show)
            if default:
                entry.insert(0, default)
            entry.pack(anchor=tk.W, pady=(0, 5))
            return entry

        self.name_entry = add_field("账户备注名", default=account.get("name", ""))
        self.sess_entry = add_field("SESSDATA", show="*", default=account.get("SESSDATA", ""))
        self.jct_entry = add_field("bili_jct", show="*", default=account.get("bili_jct", ""))
        self.dede_entry = add_field("DedeUserID（可选）", default=account.get("DedeUserID", ""))

        btn_frame = tk.Frame(frame, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        DarkButton(btn_frame, "显示/隐藏", command=self.toggle_show,
                   width=150, height=42, bg_color="#444466", text_color="#ffffff").pack(side=tk.LEFT)
        DarkButton(btn_frame, "取消", command=self.destroy,
                   width=150, height=42, bg_color="#555577", text_color="#ffffff").pack(side=tk.RIGHT, padx=(5, 0))
        DarkButton(btn_frame, "验证并保存", command=self.on_submit,
                   width=180, height=42).pack(side=tk.RIGHT)

        self.update_idletasks()
        self.geometry("600x620")
        self.minsize(600, 620)
        self.resizable(False, False)
        x = (self.winfo_screenwidth() // 2) - 300
        y = (self.winfo_screenheight() // 2) - 310
        self.geometry(f"600x620+{x}+{y}")
        self.grab_set()

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
        if self.on_update:
            ok, msg = self.on_update(self.old_name, name, sessdata, bili_jct, dede)
            if ok:
                messagebox.showinfo("成功", msg)
                self.destroy()
            else:
                messagebox.showerror("失败", msg)
