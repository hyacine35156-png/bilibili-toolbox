# -*- coding: utf-8 -*-
"""自定义 Tkinter 组件。"""

import tkinter as tk
from tkinter import ttk
import ctypes as _ctypes

from config import COLORS

# ========== 圆角绘制工具 ==========
def draw_round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """在 Canvas 上绘制平滑圆角矩形（用于统一圆角风格）。"""
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# ========== 圆角卡片容器 ==========
class RoundCard(tk.Frame):
    """圆角卡片：Canvas 绘制圆角底板 + 内嵌 body Frame 放内容。

    用法与原 tk.Frame 一致，但内容要放进 .body：
        card = RoundCard(parent)
        card.pack(fill=tk.X)
        tk.Label(card.body, text="...").pack()

    设计说明：
    - 外层 Frame 背景取父容器背景，保证圆角外缘与父容器无缝衔接
    - Canvas 铺满外层，绘制 smooth polygon 圆角矩形（Tk 支持的唯一圆角方式）
    - body 通过 create_window 嵌入，尺寸随卡片自适应
    """

    def __init__(self, parent, radius=8, bg=COLORS["bg_card"],
                 border=COLORS["border"], outer_bg=None, pad=0, **kwargs):
        self._radius = radius
        self._card_bg = bg
        self._border = border
        self._pad = pad
        self._outer_bg = outer_bg or _pick_bg(parent)

        super().__init__(parent, bg=self._outer_bg, **kwargs)
        self._cv = tk.Canvas(self, bg=self._outer_bg, highlightthickness=0, bd=0)
        self._cv.place(x=0, y=0, relwidth=1, relheight=1)

        self.body = tk.Frame(self._cv, bg=self._card_bg)
        self._win = self._cv.create_window(pad, pad, window=self.body, anchor="nw")

        self._cv.bind("<Configure>", self._redraw)
        # body 尺寸变化时把期望尺寸同步给卡片本身
        self.body.bind("<Configure>", self._on_body_configure)
        # 卡片被父容器拉伸/收缩后重绘圆角
        self.bind("<Configure>", self._on_self_configure)
        self.after(20, self._initial_sync)

    def _sync_size_to_parent(self):
        """把 body 的期望尺寸同步到卡片本身。

        为什么必须手动同步：
        Canvas 用 place 布局、body 用 create_window 嵌入，
        两者都不会向父 Frame 传播 geometry，导致 RoundCard 的
        reqwidth/reqheight 恒为 0 —— pack/grid 时整个卡片会被压扁。
        这里显式 configure(width/height)，让 pack 拿到正确尺寸。
        """
        try:
            need_w = self.body.winfo_reqwidth() + self._pad * 2
            need_h = self.body.winfo_reqheight() + self._pad * 2
            if need_w > 1 and abs(self.winfo_reqwidth() - need_w) > 1:
                self.configure(width=need_w)
            if need_h > 1 and abs(self.winfo_reqheight() - need_h) > 1:
                self.configure(height=need_h)
        except Exception:
            pass

    def _on_body_configure(self, event=None):
        self._sync_size_to_parent()

    def _on_self_configure(self, event=None):
        """卡片自身尺寸变化（被 pack fill 拉伸）时重绘。"""
        self._redraw()

    def _initial_sync(self):
        """初次显示后同步尺寸并重绘。"""
        self._sync_size_to_parent()
        self._redraw()

    def _redraw(self, event=None):
        try:
            w = self._cv.winfo_width()
            h = self._cv.winfo_height()
            if w <= 2 or h <= 2:
                return
            self._cv.delete("card")
            draw_round_rect(self._cv, 1, 1, w - 1, h - 1, self._radius,
                            fill=self._card_bg, outline=self._border,
                            width=1, tags="card")
            self._cv.tag_lower("card")
            self._cv.itemconfigure(self._win,
                                   width=max(1, w - self._pad * 2),
                                   height=max(1, h - self._pad * 2))
        except Exception:
            pass

    def set_radius(self, r):
        self._radius = r
        self._redraw()


# ========== 圆角下拉框（保留 ttk.Combobox 全部 API）==========
class RoundCombobox(tk.Frame):
    """圆角下拉框：Canvas 画圆角外框 + 内嵌 ttk.Combobox。

    设计要点：
    - 内部 combo 通过 self.combo 访问，但本类**代理转发**了常用 API
      (config / get / set / current / bind / cget)，因此可原样替换
      ttk.Combobox，不会破坏现有代码。
    - 圆角半径按高度自适应，避免小尺寸时变形。
    """

    def __init__(self, parent, radius=8, bg=None, **kwargs):
        self._outer_bg = bg or _pick_bg(parent)
        # 高度：默认 28（ttk 的 height 是下拉列表行数，不能拿来当控件高度）
        self._h = int(kwargs.pop("_height", 28))
        # 宽度：用 combo 的 width(字符数) 估算像素宽，否则父容器会塌成 1px
        char_w = int(kwargs.get("width", 20) or 20)
        self._font_obj = kwargs.get("font")
        self._w = max(80, char_w * 9 + 40)

        super().__init__(parent, bg=self._outer_bg,
                         height=self._h, width=self._w)
        # 关键：pack_propagate(False) 让 Frame 保持显式尺寸，
        # 否则内部用 place 布局会让 Frame 塌缩到 1px。
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._radius = radius
        self._canvas = tk.Canvas(self, bg=self._outer_bg, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.combo = ttk.Combobox(self, **kwargs)
        self._pad_x = 8
        self._pad_y = 3
        self.combo.place(x=self._pad_x, y=self._pad_y,
                         relwidth=1.0, relheight=1.0,
                         width=-self._pad_x * 2, height=-self._pad_y * 2)

        self.bind("<Configure>", lambda e: self._redraw())
        # 初始就按设定高度绘制一次，避免首帧无圆角
        self._canvas.update_idletasks()
        self.after(10, self._redraw)

    def _redraw(self):
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            if w <= 2 or h <= 2:
                return
            self._canvas.delete("bg")
            draw_round_rect(self._canvas, 1, 1, w - 1, h - 1,
                            self._radius, fill=COLORS["bg_input"],
                            outline=COLORS["border"], width=1, tags="bg")
            self._canvas.tag_lower("bg")
        except Exception:
            pass

    # ---------- API 代理 ----------
    def config(self, **kwargs):
        if "values" in kwargs or "textvariable" in kwargs or "state" in kwargs or "width" in kwargs:
            if "textvariable" in kwargs:
                self.combo.config(textvariable=kwargs.pop("textvariable"))
            if "values" in kwargs:
                self.combo.config(values=kwargs.pop("values"))
            if "state" in kwargs:
                self.combo.config(state=kwargs.pop("state"))
            if "width" in kwargs:
                self.combo.config(width=kwargs.pop("width"))
        if kwargs:
            try:
                super().config(**kwargs)
            except Exception:
                pass

    configure = config

    def cget(self, key):
        if key in ("values", "state", "textvariable", "width"):
            return self.combo.cget(key)
        return super().cget(key)

    def get(self):
        return self.combo.get()

    def set(self, value):
        return self.combo.set(value)

    def current(self, index=None):
        return self.combo.current(index) if index is not None else self.combo.current()

    def bind(self, sequence=None, func=None, add=None):
        try:
            return self.combo.bind(sequence, func, add)
        except Exception:
            return super().bind(sequence, func, add)

    def unbind(self, sequence, funcid=None):
        try:
            return self.combo.unbind(sequence, funcid)
        except Exception:
            return super().unbind(sequence, funcid)

    def event_generate(self, sequence, **kw):
        return self.combo.event_generate(sequence, **kw)

    def focus_set(self):
        return self.combo.focus_set()

    # 支持 combo["values"] = [...] 这种下标赋值（原代码大量使用）
    def __setitem__(self, key, value):
        self.combo[key] = value

    def __getitem__(self, key):
        return self.combo[key]


# ========== 圆角输入框（保留 ttk.Entry 全部 API）==========
class RoundEntry(tk.Frame):
    """圆角输入框：Canvas 画圆角外框 + 内嵌 ttk.Entry。

    保留并代理 Entry 常用 API：get / insert / delete / config / cget / bind / focus_set
    因此可以直接替换 DarkEntry / tk.Entry。
    """

    def __init__(self, parent, radius=8, _height=28, bg=None, **kwargs):
        self._outer_bg = bg or _pick_bg(parent)
        self._h = int(_height)

        # 宽度：用 width(字符数) 估算，否则 Frame 会塌缩
        char_w = int(kwargs.get("width", 20) or 20)
        self._w = max(60, char_w * 8 + 26)

        super().__init__(parent, bg=self._outer_bg, height=self._h, width=self._w)
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._radius = radius
        self._canvas = tk.Canvas(self, bg=self._outer_bg, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # 内部 Entry：去掉边框和背景，露出外层圆角
        ent_kwargs = dict(kwargs)
        ent_kwargs.setdefault("relief", tk.FLAT)
        ent_kwargs.setdefault("bd", 0)
        ent_kwargs.setdefault("highlightthickness", 0)
        ent_kwargs.setdefault("bg", COLORS["bg_input"])
        ent_kwargs.setdefault("fg", COLORS["text_primary"])
        ent_kwargs.setdefault("insertbackground", COLORS["accent"])
        if "font" not in ent_kwargs:
            ent_kwargs["font"] = ("微软雅黑", 10)
        self.entry = tk.Entry(self, **ent_kwargs)

        self._pad_x = 8
        self._pad_y = 3
        self.entry.place(x=self._pad_x, y=self._pad_y,
                         relwidth=1.0, relheight=1.0,
                         width=-self._pad_x * 2, height=-self._pad_y * 2)

        self.bind("<Configure>", lambda e: self._redraw())
        self.after(10, self._redraw)

    def _redraw(self):
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            if w <= 2 or h <= 2:
                return
            self._canvas.delete("bg")
            draw_round_rect(self._canvas, 1, 1, w - 1, h - 1,
                            self._radius, fill=COLORS["bg_input"],
                            outline=COLORS["border"], width=1, tags="bg")
            self._canvas.tag_lower("bg")
        except Exception:
            pass

    # ---------- API 代理 ----------
    def get(self):
        return self.entry.get()

    def insert(self, index, text):
        return self.entry.insert(index, text)

    def delete(self, first, last=None):
        return self.entry.delete(first, last)

    def config(self, **kwargs):
        if kwargs:
            try:
                self.entry.config(**kwargs)
            except Exception:
                try:
                    super().config(**kwargs)
                except Exception:
                    pass

    configure = config

    def cget(self, key):
        try:
            return self.entry.cget(key)
        except Exception:
            return super().cget(key)

    def bind(self, sequence=None, func=None, add=None):
        return self.entry.bind(sequence, func, add)

    def unbind(self, sequence, funcid=None):
        return self.entry.unbind(sequence, funcid)

    def focus_set(self):
        return self.entry.focus_set()

    def select_range(self, *a):
        return self.entry.select_range(*a)

    # 支持 entry["width"] = n 这类下标操作
    def __setitem__(self, key, value):
        self.entry[key] = value

    def __getitem__(self, key):
        return self.entry[key]


def _pick_bg(widget):
    """向上查找父容器背景色，保证圆角外框与父容器无缝。"""
    try:
        while widget is not None:
            bg = widget.cget("bg")
            if bg:
                return bg
            widget = widget.master
    except Exception:
        pass
    return COLORS["bg_card"]


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


# 按钮文字宽度测量（含 emoji）
# 之前用"中文字符14px、其他8px"的粗略估算，但 emoji（🔍🕐📊🔧 等）
# 实际渲染宽度约 18-20px，低估导致文字溢出按钮边界。
# 这里改用 tkfont.measure() 拿真实像素宽度，并在测量失败时用保守估算兜底。

_BTN_FONT_SIZE = 11
_BTN_PAD_X = 44          # 左右各留 22px 内边距
_BTN_MIN_WIDTH = 100
_measure_cache = {}


def _measure_button_width(text, height=44, pad_x=_BTN_PAD_X, min_width=_BTN_MIN_WIDTH):
    """计算按钮所需的最小宽度（像素），保证文字完整显示。

    pad_x / min_width 可调，供"紧凑模式"（如表格里的 ↑↓✎× 小按钮）使用。
    """
    key = (text, pad_x, min_width)
    if key in _measure_cache:
        return _measure_cache[key]

    tw = 0
    try:
        import tkinter.font as _tkfont
        f = _tkfont.Font(font=("微软雅黑", _BTN_FONT_SIZE, "bold"))
        tw = f.measure(text)
    except Exception:
        tw = 0

    if tw <= 0:
        # 兜底：保守估算（emoji 按 20px，中文 15px，其他 8px）
        for ch in text:
            cp = ord(ch)
            if cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF:
                tw += 20          # emoji / 符号
            elif '一' <= ch <= '鿿':
                tw += 15
            else:
                tw += 8

    width = max(min_width, tw + pad_x)
    _measure_cache[key] = width
    return width


class DarkButton(tk.Canvas):
    """自定义深色主题按钮"""
    def __init__(self, parent, text, command=None, width=None, height=44,
                 bg_color=COLORS["accent"], text_color="#000000", hover_color=COLORS["accent_hover"],
                 compact=False):
        """compact=True 用于小尺寸按钮（表格操作列等）：
        不套用 100px 最小宽度和 44px 内边距，按 min(width, 文字+16) 精确控制。
        """
        if compact:
            # 紧凑模式：按文字实际宽度 + 少量内边距，且允许很窄
            natural = _measure_button_width(text, height, pad_x=16, min_width=1)
            if width is None:
                width = natural
            elif width < natural:
                width = natural
        else:
            # 如果未指定宽度，根据文字自动计算
            if width is None:
                width = _measure_button_width(text, height)
            # 显式给了 width 也要校验：如果太窄，自动撑宽避免文字溢出
            else:
                min_w = _measure_button_width(text, height)
                if width < min_w:
                    width = min_w
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
        """兼容标准 Tkinter Button 的 config 方法。

        支持的参数：
          state / text / command / bg / fg / bg_color / text_color
          其余参数透传给 Canvas（如 cursor、width、height）

        注意：tk.Button 里用 command/bg/fg，Canvas 没有这些 option，
        必须先自行消费掉，否则会抛 "unknown option '-command'"。
        """
        redraw = False

        if "state" in kwargs:
            state = kwargs.pop("state")
            if str(state) in ("disabled", "DISABLED"):
                self.set_state("disabled")
            else:
                self.set_state("normal")

        if "text" in kwargs:
            self.text = kwargs.pop("text")
            redraw = True

        if "command" in kwargs:
            self.command = kwargs.pop("command")

        if "bg_color" in kwargs:
            self.bg_color = kwargs.pop("bg_color")
            redraw = True
        elif "bg" in kwargs:
            self.bg_color = kwargs.pop("bg")
            redraw = True

        if "text_color" in kwargs:
            self.text_color = kwargs.pop("text_color")
            redraw = True
        elif "fg" in kwargs:
            self.text_color = kwargs.pop("fg")
            redraw = True

        if redraw:
            self._draw(self.bg_color)

        # 剩余参数透传给 Canvas
        canvas_kwargs = {k: v for k, v in kwargs.items()
                         if k in ("cursor", "width", "height", "takefocus")}
        if canvas_kwargs:
            try:
                super().config(**canvas_kwargs)
            except Exception:
                pass


class DarkEntry(ttk.Entry):
    """深色输入框（保持原生外观：直角，不做圆角化）。

    说明：用户明确要求下拉框/输入框这类"方框"保持原样，
    只有卡片容器需要圆角，所以这里回退到原始 ttk 实现。
    """
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
