#!/usr/bin/env python3
"""v4.6.1: 统一开始监控按钮尺寸，弹幕工具控制栏改成两排"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 统一"开始监控"按钮尺寸为160x44（和周围一致）
# ============================================================
old_start_rush = '''        self.start_rush_btn = DarkButton(btn_row, "▶ 开始监控", command=self.start_rush,
                                          width=110, height=32, bg_color=COLORS["success"], text_color="#ffffff")'''

new_start_rush = '''        self.start_rush_btn = DarkButton(btn_row, "▶ 开始监控", command=self.start_rush,
                                          width=160, height=44, bg_color=COLORS["success"], text_color="#ffffff")'''

if old_start_rush in content:
    content = content.replace(old_start_rush, new_start_rush)
    print("1. 开始监控按钮: 110x32 -> 160x44（和周围一致）")
else:
    print("1. 未找到开始监控按钮代码")

# ============================================================
# 2. 弹幕工具控制栏改成两排，修复红色按钮被遮挡
# ============================================================
old_danmaku_ctrl = '''        # 控制栏（固定高度56px）
        danmaku_ctrl = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X)
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=56)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15)

        self.start_btn = DarkButton(ctrl_inner, "▶ 启动发送", command=self.start_sending,
                                     width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT, pady=10)

        self.stop_btn = DarkButton(ctrl_inner, "■ 停止发送", command=self.stop_sending,
                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0), pady=10)
        self.stop_btn.set_state("disabled")

        self.status_label = tk.Label(ctrl_inner, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.RIGHT)'''

new_danmaku_ctrl = '''        # 控制栏（两排布局，固定高度100px）
        danmaku_ctrl = tk.Frame(bottom_container, bg=COLORS["bg_card"], highlightthickness=1, highlightbackground=COLORS["border"])
        danmaku_ctrl.pack(fill=tk.X)
        danmaku_ctrl.pack_propagate(False)
        danmaku_ctrl.configure(height=100)

        ctrl_inner = tk.Frame(danmaku_ctrl, bg=COLORS["bg_card"])
        ctrl_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

        # 第一排：按钮
        btn_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        btn_row.pack(fill=tk.X)

        self.start_btn = DarkButton(btn_row, "▶ 启动发送", command=self.start_sending,
                                     width=160, height=40, bg_color=COLORS["success"], text_color="#ffffff")
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = DarkButton(btn_row, "■ 停止发送", command=self.stop_sending,
                                    width=160, height=40, bg_color=COLORS["danger"], text_color="#ffffff")
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.stop_btn.set_state("disabled")

        # 第二排：状态标签
        status_row = tk.Frame(ctrl_inner, bg=COLORS["bg_card"])
        status_row.pack(fill=tk.X, pady=(6, 0))

        self.status_label = tk.Label(status_row, text="状态：就绪，等待启动", bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"], font=("微软雅黑", 9))
        self.status_label.pack(side=tk.LEFT)'''

if old_danmaku_ctrl in content:
    content = content.replace(old_danmaku_ctrl, new_danmaku_ctrl)
    print("2. 弹幕工具控制栏改成两排，高度56 -> 100，修复红色按钮被遮挡")
else:
    print("2. 未找到弹幕工具控制栏代码")

# ============================================================
# 更新版本号
# ============================================================
content = content.replace('APP_VERSION = "v4.6.0"', 'APP_VERSION = "v4.6.1"')
print("3. 版本号已更新到 v4.6.1")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
