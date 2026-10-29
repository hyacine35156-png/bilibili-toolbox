#!/usr/bin/env python3
"""v4.6.0: 自定义确认弹窗统一按钮大小，所有按钮宽度加长（高度不变，字号不变）"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在DarkButton类后面添加自定义确认弹窗函数
# ============================================================
# 找到DarkButton类结束的位置（在AddAccountDialog类之前）
darkbutton_end_marker = '''class AddAccountDialog(tk.Toplevel):'''

custom_confirm_func = '''def custom_askyesno(parent, title, message):
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
               width=110, height=38, bg_color=COLORS["success"], text_color="#ffffff").pack(side=tk.LEFT, padx=(0, 15))
    DarkButton(btn_frame, "取消", command=on_cancel,
               width=110, height=38, bg_color="#666666", text_color="#ffffff").pack(side=tk.LEFT)

    # 居中显示
    confirm_win.update_idletasks()
    x = (confirm_win.winfo_screenwidth() // 2) - 200
    y = (confirm_win.winfo_screenheight() // 2) - 100
    confirm_win.geometry(f"+{x}+{y}")
    confirm_win.resizable(False, False)

    # 等待用户点击
    confirm_win.wait_window()
    return result["value"]


class AddAccountDialog(tk.Toplevel):'''

if darkbutton_end_marker in content:
    content = content.replace(darkbutton_end_marker, custom_confirm_func)
    print("1. 已添加自定义确认弹窗函数 custom_askyesno")
else:
    print("1. 未找到DarkButton类结束位置")

# ============================================================
# 2. 替换所有messagebox.askyesno为custom_askyesno
# ============================================================
# 需要给每个调用添加parent参数
replacements_askyesno = [
    ('messagebox.askyesno("确认", f"确定删除选中的 {count} 个任务吗？")',
     'custom_askyesno(self.app.root, "确认", f"确定删除选中的 {count} 个任务吗？")'),
    ('messagebox.askyesno("确认", f"确定删除任务「{task[\'name\']}」吗？")',
     'custom_askyesno(self.app.root, "确认", f"确定删除任务「{task[\'name\']}」吗？")'),
    ('messagebox.askyesno("确认", f"确定启用全部 {len(disabled_tasks)} 个已取消的日程任务吗？\\n启用后任务将按设定时间自动执行")',
     'custom_askyesno(self.app.root, "确认", f"确定启用全部 {len(disabled_tasks)} 个已取消的日程任务吗？\\n启用后任务将按设定时间自动执行")'),
    ('messagebox.askyesno("确认", f"当前有 {len(self.schedule_tasks)} 个日程任务，加载方案将覆盖当前日程，是否继续？")',
     'custom_askyesno(self.app.root, "确认", f"当前有 {len(self.schedule_tasks)} 个日程任务，加载方案将覆盖当前日程，是否继续？")'),
    ('messagebox.askyesno("确认", f"确定要删除方案「{preset_name}」吗？")',
     'custom_askyesno(self.app.root, "确认", f"确定要删除方案「{preset_name}」吗？")'),
    ('messagebox.askyesno("确认", f"确定删除账户「{acc[\'name\']}」吗？")',
     'custom_askyesno(self.app.root, "确认", f"确定删除账户「{acc[\'name\']}」吗？")'),
]

count_askyesno = 0
for old, new in replacements_askyesno:
    if old in content:
        n = content.count(old)
        content = content.replace(old, new)
        count_askyesno += n
        print(f"   替换: {old[:40]}... ({n}处)")

print(f"2. 共替换 {count_askyesno} 处 messagebox.askyesno")

# ============================================================
# 3. 所有按钮宽度加长（高度不变，字号保持11号不变）
# ============================================================
# 按当前尺寸分组，只增加宽度，高度不变
width_replacements = [
    # 极小按钮
    ('width=60, height=28', 'width=80, height=28'),
    ('width=70, height=28', 'width=90, height=28'),
    ('width=70, height=30', 'width=90, height=30'),
    ('width=70, height=34', 'width=90, height=34'),
    # 小按钮
    ('width=80, height=30', 'width=100, height=30'),
    ('width=85, height=36', 'width=105, height=36'),
    ('width=90, height=30', 'width=110, height=30'),
    ('width=90, height=34', 'width=110, height=34'),
    ('width=90, height=38', 'width=110, height=38'),
    # 中按钮
    ('width=100, height=32', 'width=120, height=32'),
    ('width=100, height=34', 'width=120, height=34'),
    ('width=100, height=36', 'width=120, height=36'),
    ('width=110, height=34', 'width=130, height=34'),
    ('width=110, height=36', 'width=130, height=36'),
    ('width=110, height=38', 'width=130, height=38'),
    ('width=110, height=40', 'width=130, height=40'),
    ('width=110, height=42', 'width=130, height=42'),
    # 中大按钮
    ('width=120, height=30', 'width=140, height=30'),
    ('width=120, height=32', 'width=140, height=32'),
    ('width=120, height=36', 'width=140, height=36'),
    ('width=120, height=38', 'width=140, height=38'),
    ('width=120, height=40', 'width=140, height=40'),
    ('width=120, height=42', 'width=140, height=42'),
    # 大按钮
    ('width=130, height=34', 'width=150, height=34'),
    ('width=130, height=36', 'width=150, height=36'),
    ('width=130, height=38', 'width=150, height=38'),
    ('width=130, height=40', 'width=150, height=40'),
    ('width=130, height=42', 'width=150, height=42'),
    ('width=130, height=44', 'width=150, height=44'),
    ('width=140, height=40', 'width=160, height=40'),
    ('width=140, height=42', 'width=160, height=42'),
    ('width=140, height=44', 'width=160, height=44'),
    # 特大按钮
    ('width=150, height=44', 'width=170, height=44'),
    ('width=220, height=36', 'width=250, height=36'),
]

count_width = 0
for old, new in width_replacements:
    if old in content:
        n = content.count(old)
        content = content.replace(old, new)
        count_width += n

print(f"3. 共加长 {count_width} 处按钮宽度（高度不变，字号保持11号不变）")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.5.9"', 'APP_VERSION = "v4.6.0"')
print("4. 版本号已更新到 v4.6.0")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
