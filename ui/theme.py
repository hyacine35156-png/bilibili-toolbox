# -*- coding: utf-8 -*-
"""界面主题与 DPI 自适应（O7）。

之前反复出现的"显示不完全"问题，根因都是硬编码像素：
用户屏幕 1707x1067（150% 缩放），换台机器就会再犯一次。

本模块提供：
  get_scale()        当前 DPI 缩放系数（96dpi = 1.0）
  sz(n)              把设计像素换算成当前 DPI 下的实际像素
  font(size, bold)   按 DPI 缩放的字号
  create_dialog()    统一弹窗工厂：自动测内容尺寸、居中、封顶
  COLORS             继续从 config 复用

设计原则：所有新增 UI 都应该走这里的 sz()/font()，不要再写死数字。
"""

import tkinter as tk
from tkinter import ttk

from config import COLORS

_scale_cache = {"v": None}


def get_scale(widget=None):
    """获取 DPI 缩放系数。96dpi 为基准 1.0。"""
    if _scale_cache["v"] is not None:
        return _scale_cache["v"]
    v = 1.0
    try:
        if widget is not None:
            # winfo_fpixels('1i') 返回每英寸像素数
            v = float(widget.winfo_fpixels("1i")) / 96.0
        else:
            root = tk._default_root
            if root is not None:
                v = float(root.winfo_fpixels("1i")) / 96.0
    except Exception:
        v = 1.0
    v = max(1.0, min(2.5, v))   # 夹在 1.0~2.5，避免极端 DPI 把界面撑爆
    _scale_cache["v"] = v
    return v


def reset_scale_cache():
    _scale_cache["v"] = None


def sz(n, widget=None):
    """设计像素 -> 当前 DPI 实际像素。"""
    try:
        return int(round(float(n) * get_scale(widget)))
    except Exception:
        return int(n)


FONT_FAMILY = "微软雅黑"


def font(size=10, bold=False, family=None, italic=False):
    """字号元组。支持 bold / italic 组合。

    重要：字号 **不再** 乘 DPI scale。
    原因：主程序启动时已经调用 SetProcessDpiAwareness(2)，Tk 的字号
    已经是"逻辑单位"，Windows/字体渲染层会自动按缩放比例绘制。
    如果再乘一次 scale，就变成双重缩放 —— 150% 缩放下 10 号会变 15 号，
    这正是 v6.1.0 初版字体被放大的原因。这里保持与历史硬编码
    ("微软雅黑", 10) 完全一致的行为。
    """
    s = int(size)
    fam = family or FONT_FAMILY
    styles = []
    if bold:
        styles.append("bold")
    if italic:
        styles.append("italic")
    if styles:
        return (fam, s, " ".join(styles))
    return (fam, s)


# ---------- 富文本渲染（使用说明页用）----------
# 支持的轻量标记（不是 Markdown，避免和 Tk Text 混用歧义）：
#   【标题】       -> 大号加粗强调色
#   **文字**       -> 加粗
#   //文字//       -> 斜体
#   !!文字!!       -> 红色加粗（最高优先级，用于危险/必读）
#   ## 小节名      -> 小节标题（加粗 + 强调色）
#   | 表格行 |     -> 等宽字体展示
#
# 为什么不用 Markdown：Tkinter Text 没有 Markdown 引擎，需要自己解析。
# 这套标记更简单、不会有歧义（例如 ** 在中文语境里不会误判）。

def render_richtext(text_widget, content, base_size=10, pad=0):
    """把带轻量标记的文本渲染进 Tk Text 控件（支持加粗/斜体/红色加粗）。

    必须在 Text 的 state=NORMAL 状态下调用，调用方负责最终禁用。
    """
    import re as _re

    # 配置 tag 样式
    text_widget.tag_configure("bold", font=font(base_size, bold=True))
    text_widget.tag_configure("italic", font=font(base_size, italic=True))
    text_widget.tag_configure(
        "danger",
        font=font(base_size, bold=True),
        foreground="#ff4d4d",
    )
    text_widget.tag_configure(
        "accent", font=font(base_size, bold=True), foreground=COLORS["accent"]
    )
    text_widget.tag_configure("mono", font=mono_font(base_size - 1))
    text_widget.tag_configure(
        "h1", font=font(base_size + 6, bold=True), foreground=COLORS["accent"],
        spacing1=10, spacing3=6,
    )
    text_widget.tag_configure(
        "h2", font=font(base_size + 2, bold=True), foreground=COLORS["accent"],
        spacing1=8, spacing3=4,
    )

    # 行级标记优先处理
    for raw_line in content.split("\n"):
        line = raw_line

        # 标题行
        if line.startswith("【") and line.endswith("】"):
            text_widget.insert("end", line + "\n", ("h1",))
            continue
        if line.startswith("## "):
            text_widget.insert("end", line[3:] + "\n", ("h2",))
            continue

        # 行内标记：按优先级 danger > bold > italic 逐段解析
        i = 0
        while i < len(line):
            # danger: !!...!!
            if line.startswith("!!", i):
                end = line.find("!!", i + 2)
                if end > 0:
                    text_widget.insert("end", line[i + 2:end], ("danger",))
                    i = end + 2
                    continue
            # bold: **...**
            if line.startswith("**", i):
                end = line.find("**", i + 2)
                if end > 0:
                    text_widget.insert("end", line[i + 2:end], ("bold",))
                    i = end + 2
                    continue
            # italic: //...//
            # 防护：URL 里的 "https://" 不能被当成斜体标记。
            # 判定条件：前面紧邻的是 ":" 就跳过，按普通文本处理。
            if line.startswith("//", i) and not (i > 0 and line[i - 1] == ":"):
                end = line.find("//", i + 2)
                if end > 0:
                    text_widget.insert("end", line[i + 2:end], ("italic",))
                    i = end + 2
                    continue
            # 普通字符（成段写入，提升性能）
            # 关键防护：若标记未闭合（如孤立的 !!），j 会停在原地导致死循环。
            # 这里在检测到"当前正好是标记起点"时，直接吃掉两个字符当作普通文本。
            if (line.startswith("!!", i) or line.startswith("**", i)
                    or line.startswith("//", i)):
                text_widget.insert("end", line[i:i + 2], ())
                i += 2
                continue

            j = i
            while j < len(line) and not (
                line.startswith("!!", j)
                or line.startswith("**", j)
                or line.startswith("//", j)
            ):
                j += 1
            # 兜底：确保一定前进
            if j == i:
                j = i + 1
            text_widget.insert("end", line[i:j], ())
            i = j

        text_widget.insert("end", "\n")


def mono_font(size=9):
    # 同上：字号不乘 DPI scale
    return ("Consolas", int(size))


# ---------- 统一弹窗工厂 ----------

def create_dialog(parent, title, builder, min_w=700, min_h=420,
                  max_ratio=(0.92, 0.86), scrollable=True):
    """创建自适应弹窗。

    参数:
      parent    父窗口
      title     标题
      builder   builder(container) -> None，在 container 里构建内容
      min_w/min_h  最小尺寸（设计像素，会按 DPI 缩放）
      max_ratio 最大占屏比例 (宽, 高)
      scrollable  是否套可滚动容器（内容多时必开）

    返回: (dlg, content_frame)
      内容应放进 content_frame。
    """
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=COLORS["bg_dark"])
    dlg.resizable(True, True)
    try:
        dlg.transient(parent.winfo_toplevel())
    except Exception:
        pass

    if not scrollable:
        body = tk.Frame(dlg, bg=COLORS["bg_dark"])
        body.pack(fill=tk.BOTH, expand=True)
        builder(body)
        _finalize_geometry(dlg, body, min_w, min_h, max_ratio)
        return dlg, body

    # 可滚动容器：滚动条用 place 绝对定位，绝不参与布局（防抖动）
    outer = tk.Frame(dlg, bg=COLORS["bg_dark"])
    outer.pack(fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(outer, bg=COLORS["bg_dark"], highlightthickness=0, bd=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vbar = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)

    body = tk.Frame(canvas, bg=COLORS["bg_dark"])
    body_id = canvas.create_window((0, 0), window=body, anchor="nw")

    vbar_state = {"on": False}

    def _place_vbar():
        try:
            ch = canvas.winfo_height()
            if ch > 1:
                vbar.place(in_=canvas, relx=1.0, rely=0, anchor="ne",
                           y=0, width=sz(16), height=ch)
        except Exception:
            pass

    def _sync_bar():
        try:
            bbox = canvas.bbox("all")
            if not bbox:
                return
            need = bbox[3] - bbox[1]
            vis = canvas.winfo_height()
            if vis <= 1:
                return
            should = need > vis + sz(2)
            if should == vbar_state["on"]:
                return
            vbar_state["on"] = should
            if should:
                _place_vbar()
            else:
                vbar.place_forget()
                canvas.yview_moveto(0)
            reserve = sz(16) if should else 0
            canvas.itemconfigure(body_id, width=max(1, canvas.winfo_width() - reserve))
        except Exception:
            pass

    def _on_canvas(event):
        try:
            reserve = sz(16) if vbar_state["on"] else 0
            canvas.itemconfigure(body_id, width=max(1, event.width - reserve))
            _place_vbar()
        except Exception:
            pass

    def _on_body(event=None):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass
        _sync_bar()

    canvas.bind("<Configure>", _on_canvas)
    body.bind("<Configure>", _on_body)

    def _wheel(event):
        try:
            if vbar_state["on"]:
                canvas.yview_scroll(int(-event.delta / 120), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _wheel)

    def _cleanup(event=None):
        try:
            canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
    dlg.bind("<Destroy>", _cleanup, add="+")

    builder(body)
    body.update_idletasks()
    _finalize_geometry(dlg, body, min_w, min_h, max_ratio)
    dlg.after(sz(80), _sync_bar)
    return dlg, body


def _finalize_geometry(dlg, body, min_w, min_h, max_ratio):
    """按内容真实尺寸设置窗口几何，并居中、封顶。"""
    try:
        body.update_idletasks()
        content_w = body.winfo_reqwidth()
        content_h = body.winfo_reqheight()
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        max_w = int(sw * max_ratio[0])
        max_h = int(sh * max_ratio[1])

        need_w = max(content_w + sz(40), sz(min_w))
        need_h = max(content_h + sz(16), sz(min_h))

        w = min(need_w, max_w)
        h = min(need_h, max_h)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.minsize(min(sz(600), w), min(sz(360), h))
    except Exception:
        pass


def make_button(parent, text, command=None, bg=None, fg="#ffffff",
                width=None, bold=True, size=10):
    """统一风格按钮（带 DPI 缩放）。"""
    kw = {
        "text": text,
        "bg": bg or COLORS["bg_input"],
        "fg": fg,
        "font": font(size, bold),
        "relief": tk.FLAT,
        "cursor": "hand2",
    }
    if command is not None:
        kw["command"] = command
    if width is not None:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    return b


def make_label(parent, text, fg=None, bg=None, size=10, bold=False, **kw):
    return tk.Label(
        parent, text=text,
        bg=bg or COLORS["bg_card"],
        fg=fg or COLORS["text_primary"],
        font=font(size, bold),
        **kw
    )


def make_combo(parent, textvariable, values=None, width=16, state="readonly", size=10):
    return ttk.Combobox(
        parent, textvariable=textvariable, values=values or [],
        state=state, width=width, font=font(size),
    )
