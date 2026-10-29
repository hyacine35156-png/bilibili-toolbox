#!/usr/bin/env python3
"""v5.2.7: 账户管理页面右侧新增任务说明独立板块"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 调整账户列表宽度：300 -> 250
# ============================================================
old_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=300)'''

new_left_width = '''        left_card.pack_propagate(False)
        left_card.configure(width=250)'''

if old_left_width in content:
    content = content.replace(old_left_width, new_left_width)
    print("1. 账户列表宽度: 300 -> 250")
else:
    print("1. 未找到账户列表宽度代码")

# 调整账户列表按钮宽度：270 -> 220
old_btn_width = '''        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=270, height=38).pack(pady=(0, 6))
        DarkButton(btn_frame, "删除账户", command=self._manager_delete_account,
                   width=270, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "验证登录", command=self._manager_verify_account,
                   width=270, height=38, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "刷新信息", command=self._manager_refresh_info,
                   width=270, height=38, bg_color="#2980b9", text_color="#ffffff").pack()'''

new_btn_width = '''        DarkButton(btn_frame, "+ 添加账户", command=self.add_account,
                   width=220, height=38).pack(pady=(0, 6))
        DarkButton(btn_frame, "删除账户", command=self._manager_delete_account,
                   width=220, height=38, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "验证登录", command=self._manager_verify_account,
                   width=220, height=38, bg_color="#444466", text_color="#ffffff").pack(pady=(0, 6))
        DarkButton(btn_frame, "刷新信息", command=self._manager_refresh_info,
                   width=220, height=38, bg_color="#2980b9", text_color="#ffffff").pack()'''

if old_btn_width in content:
    content = content.replace(old_btn_width, new_btn_width)
    print("2. 账户列表按钮宽度: 270 -> 220")
else:
    print("2. 未找到账户列表按钮宽度代码")

# ============================================================
# 3. 调整账户详细信息宽度：400 -> 320
# ============================================================
old_right_width = '''        right_card.pack_propagate(False)
        right_card.configure(width=400)'''

new_right_width = '''        right_card.pack_propagate(False)
        right_card.configure(width=320)'''

if old_right_width in content:
    content = content.replace(old_right_width, new_right_width)
    print("3. 账户详细信息宽度: 400 -> 320")
else:
    print("3. 未找到账户详细信息宽度代码")

# ============================================================
# 4. 直播间管理：从expand=True改为固定宽度500
# ============================================================
old_room_card = '''        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))'''

new_room_card = '''        # ===== 直播间管理子区域 =====
        room_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        room_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        room_card.pack_propagate(False)
        room_card.configure(width=500)'''

if old_room_card in content:
    content = content.replace(old_room_card, new_room_card)
    print("4. 直播间管理: 改为固定宽度500")
else:
    print("4. 未找到直播间管理代码")

# 调整直播间管理右侧表单宽度：340 -> 280
old_room_right = '''        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=340)'''

new_room_right = '''        # 右侧：添加/编辑表单
        room_right = tk.Frame(room_inner, bg=COLORS["bg_card"], width=280)'''

if old_room_right in content:
    content = content.replace(old_room_right, new_room_right)
    print("5. 直播间管理表单宽度: 340 -> 280")
else:
    print("5. 未找到直播间管理表单宽度代码")

# 调整直播间管理按钮宽度：320 -> 260
old_room_btn = '''        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=320, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=320, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=320, height=34, bg_color="#2980b9", text_color="#ffffff").pack()'''

new_room_btn = '''        DarkButton(room_right, "+ 添加直播间", command=self._manager_add_room,
                   width=260, height=34).pack(pady=(0, 5))
        DarkButton(room_right, "删除直播间", command=self._manager_delete_room,
                   width=260, height=34, bg_color=COLORS["danger"], text_color="#ffffff").pack(pady=(0, 5))
        DarkButton(room_right, "从账户导入", command=self._manager_import_rooms_from_accounts,
                   width=260, height=34, bg_color="#2980b9", text_color="#ffffff").pack()'''

if old_room_btn in content:
    content = content.replace(old_room_btn, new_room_btn)
    print("6. 直播间管理按钮宽度: 320 -> 260")
else:
    print("6. 未找到直播间管理按钮宽度代码")

# ============================================================
# 7. 在直播间管理后面新增任务说明独立板块
# ============================================================
old_refresh_room = '''        self._refresh_manager_room_list()

    def _refresh_manager_room_list(self):'''

task_guide_text = '''【重点】导入账户机制
─────────────────────────────
1. 点击「+ 添加账户」按钮
2. 输入账户昵称（自定义，用于区分账户）
3. 输入SESSDATA（从浏览器Cookie中获取）
4. 输入bili_jct（CSRF Token，从Cookie中获取）
5. 输入DedeUserID（用户UID，可选，从Cookie中获取）
6. 点击确定，系统自动验证登录有效性
7. 验证成功后账户自动保存，所有功能模块共享

获取Cookie方法：
- 浏览器登录B站后，按F12打开开发者工具
- 切换到Application/存储标签
- 找到Cookies -> https://www.bilibili.com
- 复制SESSDATA、bili_jct、DedeUserID的值

注意事项：
- SESSDATA是账户身份凭证，请勿泄露给他人
- 账户数据保存在data/accounts.json文件中
- 「验证登录」可检查当前账户是否有效
- 「刷新信息」可更新账户的最新昵称

【抢码工具】
─────────────────────────────
1. 选择抢码任务（每日任务/累计任务等）
2. 选择参与抢码的账户（可多选）
3. 设置领取时间（精确到秒）
4. 点击「开始监控」，到点自动领取
5. 支持「开始领取」按配置自动执行
6. 库存为0时自动停止，避免无效请求

【弹幕工具】
─────────────────────────────
1. 选择发送弹幕的账户（可多选）
2. 选择直播间（在账户管理页面添加）
3. 输入弹幕内容（支持多条，随机/顺序发送）
4. 设置发送间隔（秒）
5. 点击「开始发送」，自动循环发送
6. 点击「停止发送」终止

【看播任务】
─────────────────────────────
1. 选择看播账户（可多选，默认全选）
2. 选择直播间（支持多栏，每栏选一个）
3. 点击「+ 添加」增加直播间栏
4. 设置每日时长（分钟）和心跳间隔（秒）
5. 点击「开始看播」，模拟真实观看
6. 建立弹幕连接+视频流下载，计入在线观众

【送礼功能】
─────────────────────────────
1. 选择送礼账户（单选，下拉选择）
2. 选择直播间（在账户管理页面添加）
3. 选择礼物（固定：牛蛙牛蛙，1电池）
4. 设置数量（1个或10个）
5. 设置送礼间隔（秒）和次数（0=不限制）
6. 点击「查询电池」查看账户电池余额
7. 电池为0的账户自动禁用送礼

【日程任务】
─────────────────────────────
1. 支持抢码/看播/弹幕/送礼/关机任务
2. 设置任务名称（自动编号，如看播1）
3. 设置执行时间（时:分:秒，下拉选择）
4. 任务自动保存，重启不丢失
5. 支持方案保存/加载，一键切换配置
6. 支持多选批量删除、全部启用/取消
7. 「一键执行」按时间顺序执行所有日程

【定时关机】
─────────────────────────────
1. 支持定时关机（指定时间）和延时关机
2. 设置关机时间后自动倒计时
3. 关机前有确认提示，可取消
4. 可加入日程任务，自动执行关机

【直播间管理】
─────────────────────────────
1. 在账户管理页面右侧统一管理
2. 「+ 添加直播间」手动添加（直播间号+名称+备注）
3. 「从账户导入」自动获取所有账户的直播间
4. 「删除直播间」移除选中的直播间
5. 所有功能模块共享直播间列表
6. 选择直播间时只显示名称，不显示数字ID'''

new_task_guide = '''        self._refresh_manager_room_list()

        # ===== 任务说明独立板块 =====
        guide_card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        guide_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))

        tk.Label(guide_card, text="任务说明", bg=COLORS["bg_card"], fg=COLORS["accent"],
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 8))

        guide_inner = tk.Frame(guide_card, bg=COLORS["bg_card"])
        guide_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 滚动条
        guide_scroll = tk.Scrollbar(guide_inner)
        guide_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.guide_text = tk.Text(guide_inner, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                  font=("微软雅黑", 9), bd=0, highlightthickness=0, wrap=tk.WORD,
                                  padx=12, pady=12, yscrollcommand=guide_scroll.set)
        self.guide_text.pack(fill=tk.BOTH, expand=True)
        guide_scroll.config(command=self.guide_text.yview)

        # 插入任务说明内容
        self.guide_text.insert(tk.END, TASK_GUIDE_TEXT)
        self.guide_text.config(state=tk.DISABLED)

    def _refresh_manager_room_list(self):'''

# 在文件开头添加TASK_GUIDE_TEXT常量
old_app_version = 'APP_VERSION = "v5.2.6"'
new_app_version = 'APP_VERSION = "v5.2.7"\n\nTASK_GUIDE_TEXT = """' + task_guide_text + '"""'

content = content.replace(old_app_version, new_app_version)
print("7. 已添加TASK_GUIDE_TEXT常量")

if old_refresh_room in content:
    content = content.replace(old_refresh_room, new_task_guide)
    print("8. 已新增任务说明独立板块")
else:
    print("8. 未找到_refresh_manager_room_list代码")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
