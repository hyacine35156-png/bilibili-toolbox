# -*- coding: utf-8 -*-
"""自定义 Tkinter 组件。"""

import tkinter as tk
from tkinter import ttk
import ctypes as _ctypes

from config import COLORS

# ========== 自定义美观组件 ==========
class ToolTip:
    """简单的鼠标悬停提示框"""
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.after_id = None
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        self.after_id = self.widget.after(self.delay, self._show_tip)

    def _on_leave(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self._hide_tip()

    def _show_tip(self):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(tw, text=self.text, justify=tk.LEFT,
                 background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                 font=("微软雅黑", 9), wraplength=300).pack(ipadx=5, ipady=3)

    def _hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class DarkButton(tk.Canvas):
    """自定义深色主题按钮"""
    def __init__(self, parent, text, command=None, width=None, height=44,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"]):
        # 如果未指定宽度，根据文字自动计算
        if width is None:
            # 估算文字宽度（每个中文字符约12px，英文约7px，加上左右padding各20px）
            text_width = 0
            for ch in text:
                if '一' <= ch <= '鿿' or ch in "🚀⏹▶🔄⏰■":
                    text_width += 14
                else:
                    text_width += 8
            width = text_width + 70  # 左右padding各35px，留出空隙
            width = max(width, 100)  # 最小宽度100px
        super().__init__(parent, width=width, height=height, bg=COLORS["bg_card"],
                         highlightthickness=0, bd=0)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.text = text
        self.width = width
        self.height = height
        self._draw(self.bg_color)
        self.bind("<Enter>", lambda e: self._draw(self.hover_color))
        self.bind("<Leave>", lambda e: self._draw(self.bg_color))
        self.bind("<Button-1>", self._on_click)

    def _draw(self, color):
        self.delete("all")
        # 圆角矩形
        r = 8
        self.create_rectangle(r, 0, self.width - r, self.height, fill=color, outline=color)
        self.create_rectangle(0, r, self.width, self.height - r, fill=color, outline=color)
        self.create_oval(0, 0, 2*r, 2*r, fill=color, outline=color)
        self.create_oval(self.width-2*r, 0, self.width, 2*r, fill=color, outline=color)
        self.create_oval(0, self.height-2*r, 2*r, self.height, fill=color, outline=color)
        self.create_oval(self.width-2*r, self.height-2*r, self.width, self.height, fill=color, outline=color)
        self.create_text(self.width//2, self.height//2, text=self.text, fill=self.text_color,
                         font=("微软雅黑", 11, "bold"))

    def _on_click(self, e):
        if self.command:
            try:
                self.command()
            except Exception as ex:
                import traceback
                print(f"[DarkButton错误] 按钮 {self.text} 的command执行异常: {ex}")
                traceback.print_exc()

    def set_state(self, state):
        if state == "disabled":
            self._draw("#444444")
            self.unbind("<Button-1>")
        else:
            self._draw(self.bg_color)
            self.bind("<Button-1>", self._on_click)

    def config(self, **kwargs):
        """兼容标准Tkinter按钮的config方法，支持state和text参数"""
        if "state" in kwargs:
            state = kwargs["state"]
            if state == tk.DISABLED:
                self.set_state("disabled")
            else:
                self.set_state("normal")
        if "text" in kwargs:
            self.text = kwargs["text"]
            # 重绘按钮文本，保持当前背景色
            current_bg = self.cget("bg")
            self._draw(current_bg if current_bg != COLORS["bg_card"] else self.bg_color)
        # 其他参数传给Canvas的config
        canvas_kwargs = {k: v for k, v in kwargs.items() if k not in ("state", "text")}
        if canvas_kwargs:
            super().config(**canvas_kwargs)


class DarkEntry(ttk.Entry):
    """深色输入框"""
    def __init__(self, parent, **kwargs):
        style = ttk.Style()
        style.configure("Dark.TEntry",
                        fieldbackground=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        insertcolor=COLORS["accent"],
                        bordercolor=COLORS["border"],
                        lightcolor=COLORS["border"],
                        darkcolor=COLORS["border"],
                        padding=6)
        super().__init__(parent, style="Dark.TEntry", **kwargs)

# ========== 添加账户对话框 ==========
def custom_askyesno(parent, title, message):
    """自定义确认弹窗，使用DarkButton保证按钮大小一致"""
    result = {"value": False, "done": False}

    confirm_win = tk.Toplevel(parent)
    confirm_win.title(title)
    confirm_win.configure(bg=COLORS["bg_dark"])
    confirm_win.transient(parent)
    confirm_win.grab_set()

    # 内容
    content_frame = tk.Frame(confirm_win, bg=COLORS["bg_dark"], padx=30, pady=25)
    content_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(content_frame, text=message, bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
             font=("微软雅黑", 11), wraplength=350, justify=tk.LEFT).pack(pady=(0, 20))

    # 按钮
    btn_frame = tk.Frame(content_frame, bg=COLORS["bg_dark"])
    btn_frame.pack()

    def on_confirm():
        result["value"] = True
        result["done"] = True
        confirm_win.destroy()

    def on_cancel():
        result["value"] = False
        result["done"] = True
        confirm_win.destroy()

    DarkButton(btn_frame, "确认", command=on_confirm,
               width=150, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
    DarkButton(btn_frame, "取消", command=on_cancel,
               width=150, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    # 居中显示
    confirm_win.update_idletasks()
    x = (confirm_win.winfo_screenwidth() // 2) - 200
    y = (confirm_win.winfo_screenheight() // 2) - 100
    confirm_win.geometry(f"+{x}+{y}")
    confirm_win.resizable(False, False)

    # 等待用户点击
    confirm_win.wait_window()
    return result["value"]

# ---------- Win32 ShellExecuteEx 结构体（时间同步用）----------
# P2-14: 全局SHELLEXECUTEINFOW定义，避免两个函数内重复定义
import ctypes as _ctypes
class _SHELLEXECUTEINFOW(_ctypes.Structure):
    _fields_ = [
        ("cbSize", _ctypes.c_ulong), ("fMask", _ctypes.c_ulong),
        ("hwnd", _ctypes.c_void_p), ("lpVerb", _ctypes.c_wchar_p),
        ("lpFile", _ctypes.c_wchar_p), ("lpParameters", _ctypes.c_wchar_p),
        ("lpDirectory", _ctypes.c_wchar_p), ("nShow", _ctypes.c_int),
        ("hInstApp", _ctypes.c_void_p), ("lpIDList", _ctypes.c_void_p),
        ("lpClass", _ctypes.c_wchar_p), ("hkeyClass", _ctypes.c_void_p),
        ("dwHotKey", _ctypes.c_ulong), ("hIcon", _ctypes.c_void_p),
        ("hProcess", _ctypes.c_void_p),
    ]
