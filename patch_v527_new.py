#!/usr/bin/env python3
"""v5.2.7: 新增任务说明独立标签页，和其他功能标签并列"""

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 1. 在文件开头添加TASK_GUIDE_TEXT常量
# ============================================================
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

old_app_version = 'APP_VERSION = "v5.2.6"'
new_app_version = 'APP_VERSION = "v5.2.7"\n\nTASK_GUIDE_TEXT = """' + task_guide_text + '"""'

content = content.replace(old_app_version, new_app_version)
print("1. 已添加TASK_GUIDE_TEXT常量")

# ============================================================
# 2. 在标签栏新增任务说明标签（在账户管理后面）
# ============================================================
old_tab_account = '''        self.tab_account = tk.Label(tab_bar, text="👤 账户管理", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                    font=("微软雅黑", 10), padx=15, pady=8, cursor="hand2")
        self.tab_account.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_account.bind("<Button-1>", lambda e: self.switch_tab("account"))'''

new_tab_account = '''        self.tab_account = tk.Label(tab_bar, text="👤 账户管理", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                    font=("微软雅黑", 10), padx=15, pady=8, cursor="hand2")
        self.tab_account.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_account.bind("<Button-1>", lambda e: self.switch_tab("account"))

        # 任务说明标签
        self.tab_guide = tk.Label(tab_bar, text="📖 任务说明", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                  font=("微软雅黑", 10), padx=15, pady=8, cursor="hand2")
        self.tab_guide.pack(side=tk.LEFT, padx=(0, 15), pady=6)
        self.tab_guide.bind("<Button-1>", lambda e: self.switch_tab("guide"))'''

if old_tab_account in content:
    content = content.replace(old_tab_account, new_tab_account)
    print("2. 已新增任务说明标签")
else:
    print("2. 未找到账户管理标签代码")

# ============================================================
# 3. 创建任务说明页面（在account_page后面）
# ============================================================
old_account_page = '''        self.account_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.account_page.pack(fill=tk.BOTH, expand=True)
        self.account_page.pack_forget()'''

new_account_page = '''        self.account_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.account_page.pack(fill=tk.BOTH, expand=True)
        self.account_page.pack_forget()

        # 任务说明页面
        self.guide_page = tk.Frame(self.tab_container, bg=COLORS["bg_dark"])
        self.guide_page.pack(fill=tk.BOTH, expand=True)
        self.guide_page.pack_forget()
        self._build_guide_page()'''

if old_account_page in content:
    content = content.replace(old_account_page, new_account_page)
    print("3. 已创建任务说明页面")
else:
    print("3. 未找到account_page代码")

# ============================================================
# 4. 在switch_tab方法中添加任务说明标签的切换逻辑
# ============================================================
old_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()
        self.account_page.pack_forget()'''

new_switch_hide = '''        # 隐藏所有页面
        self.rush_page.pack_forget()
        self.danmaku_page.pack_forget()
        self.shutdown_page.pack_forget()
        self.watch_page.pack_forget()
        self.schedule_page.pack_forget()
        self.account_page.pack_forget()
        self.guide_page.pack_forget()'''

if old_switch_hide in content:
    content = content.replace(old_switch_hide, new_switch_hide)
    print("4. 已添加guide_page到隐藏列表")
else:
    print("4. 未找到switch_tab隐藏代码")

# 添加任务说明标签的重置样式
old_reset_style = '''        self.tab_account.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

new_reset_style = '''        self.tab_account.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))
        self.tab_guide.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 10))'''

if old_reset_style in content:
    content = content.replace(old_reset_style, new_reset_style)
    print("5. 已添加tab_guide重置样式")
else:
    print("5. 未找到重置样式代码")

# 添加任务说明标签的选中样式和显示逻辑
old_account_show = '''        elif tab_name == "account":
            self.account_page.pack(fill=tk.BOTH, expand=True)
            self.tab_account.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))'''

new_account_show = '''        elif tab_name == "account":
            self.account_page.pack(fill=tk.BOTH, expand=True)
            self.tab_account.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))
        elif tab_name == "guide":
            self.guide_page.pack(fill=tk.BOTH, expand=True)
            self.tab_guide.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 10, "bold"))'''

if old_account_show in content:
    content = content.replace(old_account_show, new_account_show)
    print("6. 已添加guide标签显示逻辑")
else:
    print("6. 未找到account显示逻辑代码")

# ============================================================
# 5. 添加_build_guide_page方法（在build_account_page后面）
# ============================================================
# 找到build_account_page方法的结束位置，在后面添加_build_guide_page
old_refresh_manager = '''    def _refresh_manager_room_list(self):
        """刷新直播间管理列表"""'''

new_build_guide = '''    def _build_guide_page(self):
        """构建任务说明页面"""
        main = tk.Frame(self.guide_page, bg=COLORS["bg_dark"])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 标题
        tk.Label(main, text="📖 任务说明", bg=COLORS["bg_dark"], fg=COLORS["accent"],
                 font=("微软雅黑", 16, "bold")).pack(anchor=tk.W, padx=8, pady=(0, 10))

        # 内容卡片
        card = tk.Frame(main, bg=COLORS["bg_card"], bd=0, highlightthickness=1, highlightbackground=COLORS["border"])
        card.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scroll = tk.Scrollbar(card)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 文本区域
        text = tk.Text(card, bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                        font=("微软雅黑", 10), bd=0, highlightthickness=0, wrap=tk.WORD,
                        padx=20, pady=20, yscrollcommand=scroll.set)
        text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=text.yview)

        # 插入任务说明内容
        text.insert(tk.END, TASK_GUIDE_TEXT)
        text.config(state=tk.DISABLED)

    def _refresh_manager_room_list(self):
        """刷新直播间管理列表"""'''

if old_refresh_manager in content:
    content = content.replace(old_refresh_manager, new_build_guide)
    print("7. 已添加_build_guide_page方法")
else:
    print("7. 未找到_refresh_manager_room_list代码")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("\n语法验证通过")
except py_compile.PyCompileError as e:
    print(f"\n语法错误: {e}")
