# -*- coding: utf-8 -*-
"""
添加兑换码导出模块
1. 添加全局函数：提取兑换码、保存兑换码、读取兑换码
2. 在领取成功处调用保存函数
3. 添加 CodeExportFrame 类
4. 在Tab栏添加"🎁 兑换码"标签
5. 在主窗口初始化新页面
"""
import re
import json

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# ============================================================
# 步骤1：在 claim_reward 函数后面添加兑换码相关全局函数
# ============================================================
# 找到 claim_reward 函数结束的位置（def cookies_from_account 之前）
insert_marker = "def cookies_from_account(acc):"

code_functions = '''
# ========== 兑换码导出相关函数 ==========
CODE_EXPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "兑换码记录.json")

def _ensure_code_dir():
    """确保data目录存在"""
    d = os.path.dirname(CODE_EXPORT_FILE)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def extract_redeem_codes(data):
    """从API返回数据中递归提取兑换码"""
    codes = []
    if not data:
        return codes
    # 可能的兑换码字段名
    code_keys = ["cdk", "redeem_code", "redeemCode", "award_code", "awardCode",
                 "gift_code", "giftCode", "exchange_code", "exchangeCode",
                 "code", "key", "ticket", "coupon"]
    
    def search(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = k.lower()
                # 检查是否是兑换码字段
                if k_lower in [ck.lower() for ck in code_keys]:
                    if isinstance(v, str) and v and len(v) >= 4 and not v.startswith("http"):
                        # 排除明显不是兑换码的值
                        if v not in ["0", "1", "true", "false", "success", "ok"]:
                            codes.append({"field": k, "value": v, "path": path + "." + k})
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item and len(item) >= 4:
                                codes.append({"field": k, "value": item, "path": path + "." + k})
                search(v, path + "." + k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search(item, path + f"[{i}]")
    
    search(data)
    return codes

def save_redeem_code(task_name, account_name, data, task_period="", task_type=""):
    """领取成功后保存兑换码到本地文件"""
    try:
        _ensure_code_dir()
        codes = extract_redeem_codes(data)
        if not codes:
            return False, "未提取到兑换码"
        
        # 读取已有记录
        records = []
        if os.path.exists(CODE_EXPORT_FILE):
            try:
                with open(CODE_EXPORT_FILE, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except:
                records = []
        
        import time as _time
        timestamp = _time.strftime("%Y-%m-%d %H:%M:%S")
        
        for code_info in codes:
            record = {
                "id": len(records) + 1,
                "time": timestamp,
                "task_name": task_name,
                "task_period": task_period,
                "task_type": task_type,
                "account": account_name,
                "code_field": code_info["field"],
                "redeem_code": code_info["value"],
                "status": "未使用",
                "raw_path": code_info.get("path", "")
            }
            records.append(record)
        
        with open(CODE_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        return True, f"已保存 {len(codes)} 个兑换码"
    except Exception as e:
        return False, f"保存兑换码失败: {e}"

def load_redeem_codes():
    """读取所有兑换码记录"""
    try:
        if os.path.exists(CODE_EXPORT_FILE):
            with open(CODE_EXPORT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def update_redeem_code_status(record_id, status):
    """更新兑换码状态"""
    try:
        records = load_redeem_codes()
        for r in records:
            if r["id"] == record_id:
                r["status"] = status
                break
        _ensure_code_dir()
        with open(CODE_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def delete_redeem_code(record_id):
    """删除单条兑换码记录"""
    try:
        records = load_redeem_codes()
        records = [r for r in records if r["id"] != record_id]
        # 重新编号
        for i, r in enumerate(records):
            r["id"] = i + 1
        _ensure_code_dir()
        with open(CODE_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def clear_redeem_codes():
    """清空所有兑换码记录"""
    try:
        _ensure_code_dir()
        with open(CODE_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

'''

if insert_marker in content:
    content = content.replace(insert_marker, code_functions + "\n" + insert_marker, 1)
    print("✓ 步骤1：已添加兑换码相关全局函数")
else:
    print("✗ 步骤1：未找到插入点")

# ============================================================
# 步骤2：在领取成功处调用保存函数
# ============================================================
# 位置1：定时任务领取成功（第2123行附近）
old1 = '''                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已完成"
                                break
                    break'''
new1 = '''                        self.log(f"🎉 定时任务「{task_name}」领取成功！（第{attempt}次，账户：{account['name']}）")
                        # 保存兑换码
                        try:
                            _data = msg if isinstance(msg, dict) else None
                            if _data is None and hasattr(self, '_last_claim_data'):
                                _data = self._last_claim_data
                            if _data:
                                ok_save, save_msg = save_redeem_code(
                                    task_name, account['name'], _data,
                                    task_period=task.get('period', ''),
                                    task_type=task.get('type', '')
                                )
                                if ok_save:
                                    self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
                        except:
                            pass
                        for t in self.scheduled_tasks:
                            if t["id"] == task_id:
                                t["status"] = "已完成"
                                break
                    break'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("✓ 步骤2a：已在定时任务领取成功处添加兑换码保存")
else:
    print("✗ 步骤2a：未找到定时任务领取成功位置")

# 位置2：手动领取成功（第2560行附近）
old2 = '''            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")'''
new2 = '''            self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
            # 保存兑换码
            try:
                if hasattr(self, '_last_claim_data') and self._last_claim_data:
                    ok_save, save_msg = save_redeem_code(
                        task['name'], self.current_account.get('name', '未知'),
                        self._last_claim_data,
                        task_period=task.get('period', ''),
                        task_type=task.get('type', '')
                    )
                    if ok_save:
                        self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
            except:
                pass'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("✓ 步骤2b：已在手动领取成功处添加兑换码保存")
else:
    print("✗ 步骤2b：未找到手动领取成功位置（可能有多个，继续找其他位置）")

# 位置3：另一个手动领取成功（第2710行附近）
old3 = '''                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")'''
new3 = '''                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                # 保存兑换码
                try:
                    if hasattr(self, '_last_claim_data') and self._last_claim_data:
                        ok_save, save_msg = save_redeem_code(
                            task['name'], self.current_account.get('name', '未知'),
                            self._last_claim_data,
                            task_period=task.get('period', ''),
                            task_type=task.get('type', '')
                        )
                        if ok_save:
                            self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
                except:
                    pass'''

count3 = content.count(old3)
if count3 > 0:
    content = content.replace(old3, new3)
    print(f"✓ 步骤2c：已在 {count3} 处领取成功位置添加兑换码保存")
else:
    print("✗ 步骤2c：未找到其他领取成功位置")

# 位置4：第2964行附近
old4 = '''                self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")'''
# 这个已经被上面的替换覆盖了，因为old3和old4相同

# 位置5：第3155行附近
old5 = '''                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")'''
new5 = '''                        self.log(f"🎉 领取成功：[{task['period']}][{task['type']}]{task['name']} -> {task['award']}")
                        # 保存兑换码
                        try:
                            if hasattr(self, '_last_claim_data') and self._last_claim_data:
                                ok_save, save_msg = save_redeem_code(
                                    task['name'], self.current_account.get('name', '未知'),
                                    self._last_claim_data,
                                    task_period=task.get('period', ''),
                                    task_type=task.get('type', '')
                                )
                                if ok_save:
                                    self.log(f"  🎁 {save_msg}，可在「兑换码」页面查看")
                        except:
                            pass'''

if old5 in content:
    content = content.replace(old5, new5, 1)
    print("✓ 步骤2d：已在第3155行附近领取成功处添加兑换码保存")
else:
    print("✗ 步骤2d：未找到第3155行附近领取成功位置")

# ============================================================
# 步骤3：在 claim_reward 函数中保存返回的data
# ============================================================
# 在 claim_reward 函数返回成功时，把data存到一个全局变量
old_claim = '''        if code == 0:
            return True, "领取成功", result.get("data")'''
new_claim = '''        if code == 0:
            # 保存最后一次领取成功的数据，供兑换码提取使用
            global _last_claim_data_global
            _last_claim_data_global = result.get("data")
            return True, "领取成功", result.get("data")'''

if old_claim in content:
    content = content.replace(old_claim, new_claim, 1)
    print("✓ 步骤3：已在claim_reward中添加data保存")
else:
    print("✗ 步骤3：未找到claim_reward成功返回位置")

# 添加全局变量初始化（在文件顶部import之后）
global_var = "\n_last_claim_data_global = None\n"
# 在第一个class定义之前插入
first_class = content.find("class ")
if first_class > 0:
    # 找到前面的空行
    insert_pos = content.rfind("\n", 0, first_class)
    if "_last_claim_data_global" not in content[:first_class]:
        content = content[:insert_pos] + global_var + content[insert_pos:]
        print("✓ 步骤3b：已添加全局变量初始化")

# ============================================================
# 步骤4：添加 CodeExportFrame 类（在 WatchLiveFrame 之前）
# ============================================================
code_frame_class = '''
# ========== 兑换码导出模块 ==========
class CodeExportFrame(tk.Frame):
    """兑换码导出页面"""
    def __init__(self, parent, account_mgr=None, room_mgr=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.selected_ids = set()
        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        # 顶部标题栏
        header = tk.Frame(self, bg=COLORS["bg_card"], height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🎁 兑换码导出", bg=COLORS["bg_card"],
                 fg=COLORS["accent"], font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(header, text="领取成功后自动保存兑换码，支持复制和导出",
                 bg=COLORS["bg_card"], fg=COLORS["text_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 20))

        # 操作按钮栏
        btn_bar = tk.Frame(self, bg=COLORS["bg_card"], height=56)
        btn_bar.pack(fill=tk.X, pady=(0, 2))
        btn_bar.pack_propagate(False)

        btn_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        btn_frame.pack(side=tk.LEFT, padx=15, pady=8)

        self.refresh_btn = tk.Button(btn_frame, text="🔄 刷新列表", bg=COLORS["bg_input"],
                                      fg=COLORS["text_secondary"], font=("微软雅黑", 10),
                                      bd=0, padx=16, pady=6, cursor="hand2", command=self.refresh_list)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_selected_btn = tk.Button(btn_frame, text="📋 复制选中", bg=COLORS["accent"],
                                            fg="#000000", font=("微软雅黑", 10, "bold"),
                                            bd=0, padx=16, pady=6, cursor="hand2", command=self.copy_selected)
        self.copy_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.copy_all_btn = tk.Button(btn_frame, text="📋 复制全部", bg=COLORS["accent"],
                                       fg="#000000", font=("微软雅黑", 10, "bold"),
                                       bd=0, padx=16, pady=6, cursor="hand2", command=self.copy_all)
        self.copy_all_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_btn = tk.Button(btn_frame, text="💾 导出TXT", bg="#2E7D32",
                                     fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                     bd=0, padx=16, pady=6, cursor="hand2", command=self.export_txt)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_csv_btn = tk.Button(btn_frame, text="📊 导出CSV", bg="#1565C0",
                                          fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                          bd=0, padx=16, pady=6, cursor="hand2", command=self.export_csv)
        self.export_csv_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.delete_selected_btn = tk.Button(btn_frame, text="🗑 删除选中", bg="#C62828",
                                               fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                               bd=0, padx=16, pady=6, cursor="hand2", command=self.delete_selected)
        self.delete_selected_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = tk.Button(btn_frame, text="🧹 清空全部", bg="#616161",
                                    fg="#FFFFFF", font=("微软雅黑", 10, "bold"),
                                    bd=0, padx=16, pady=6, cursor="hand2", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT)

        # 统计信息
        self.stats_label = tk.Label(btn_bar, text="", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 10))
        self.stats_label.pack(side=tk.RIGHT, padx=20)

        # 列表区域
        list_container = tk.Frame(self, bg=COLORS["bg_card"])
        list_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        # 表头
        header_frame = tk.Frame(list_container, bg=COLORS["bg_input"], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        cols = [
            ("选择", 50),
            ("ID", 50),
            ("领取时间", 160),
            ("任务名称", 250),
            ("账户", 120),
            ("兑换码", 300),
            ("字段", 100),
            ("状态", 80),
            ("操作", 150),
        ]
        self.col_widths = [w for _, w in cols]
        for text, width in cols:
            tk.Label(header_frame, text=text, bg=COLORS["bg_input"],
                     fg=COLORS["accent"], font=("微软雅黑", 10, "bold"),
                     width=width // 8, anchor="w").pack(side=tk.LEFT, padx=4, pady=8)

        # 可滚动列表
        self.canvas = tk.Canvas(list_container, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=COLORS["bg_dark"])

        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_list(self):
        """刷新兑换码列表"""
        # 清空现有内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.selected_ids.clear()

        records = load_redeem_codes()
        self.records = records

        # 更新统计
        total = len(records)
        unused = sum(1 for r in records if r.get("status") == "未使用")
        used = sum(1 for r in records if r.get("status") == "已使用")
        self.stats_label.config(text=f"共 {total} 条 | 未使用 {unused} | 已使用 {used}")

        if not records:
            empty_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_dark"])
            empty_frame.pack(fill=tk.X, pady=40)
            tk.Label(empty_frame, text="📭 暂无兑换码记录", bg=COLORS["bg_dark"],
                     fg=COLORS["text_muted"], font=("微软雅黑", 14)).pack()
            tk.Label(empty_frame, text="领取奖励成功后，兑换码会自动保存到这里",
                     bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                     font=("微软雅黑", 10)).pack(pady=(8, 0))
            return

        for i, record in enumerate(records):
            row_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"])
            row_frame.pack(fill=tk.X, pady=1)

            # 选择框
            var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(row_frame, variable=var, bg=row_frame["bg"],
                                 activebackground=row_frame["bg"], command=lambda rid=record["id"], v=var: self._toggle_select(rid, v))
            cb.pack(side=tk.LEFT, padx=(10, 5), pady=6)

            # ID
            tk.Label(row_frame, text=str(record["id"]), bg=row_frame["bg"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                     width=4, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 时间
            tk.Label(row_frame, text=record.get("time", ""), bg=row_frame["bg"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                     width=18, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 任务名称
            task_name = record.get("task_name", "")
            if record.get("task_period"):
                task_name = f"[{record['task_period']}] {task_name}"
            tk.Label(row_frame, text=task_name, bg=row_frame["bg"],
                     fg=COLORS["text"], font=("微软雅黑", 9),
                     width=28, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 账户
            tk.Label(row_frame, text=record.get("account", ""), bg=row_frame["bg"],
                     fg=COLORS["text_secondary"], font=("微软雅黑", 9),
                     width=12, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 兑换码（可点击复制）
            code = record.get("redeem_code", "")
            code_label = tk.Label(row_frame, text=code, bg=row_frame["bg"],
                                   fg="#4FC3F7", font=("Consolas", 10, "bold"),
                                   cursor="hand2", anchor="w")
            code_label.pack(side=tk.LEFT, padx=2, pady=6)
            code_label.bind("<Button-1>", lambda e, c=code: self._copy_to_clipboard(c))

            # 字段
            tk.Label(row_frame, text=record.get("code_field", ""), bg=row_frame["bg"],
                     fg=COLORS["text_muted"], font=("微软雅黑", 8),
                     width=10, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 状态
            status = record.get("status", "未使用")
            status_color = "#4CAF50" if status == "未使用" else "#9E9E9E"
            tk.Label(row_frame, text=status, bg=row_frame["bg"],
                     fg=status_color, font=("微软雅黑", 9, "bold"),
                     width=6, anchor="w").pack(side=tk.LEFT, padx=2, pady=6)

            # 操作按钮
            op_frame = tk.Frame(row_frame, bg=row_frame["bg"])
            op_frame.pack(side=tk.LEFT, padx=(10, 5), pady=4)

            tk.Button(op_frame, text="复制", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                      font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                      command=lambda c=code: self._copy_to_clipboard(c)).pack(side=tk.LEFT, padx=(0, 4))

            if status == "未使用":
                tk.Button(op_frame, text="标记已用", bg="#FF8F00", fg="#FFFFFF",
                          font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                          command=lambda rid=record["id"]: self._mark_used(rid)).pack(side=tk.LEFT, padx=(0, 4))
            else:
                tk.Button(op_frame, text="标记未用", bg="#1565C0", fg="#FFFFFF",
                          font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                          command=lambda rid=record["id"]: self._mark_unused(rid)).pack(side=tk.LEFT, padx=(0, 4))

            tk.Button(op_frame, text="删除", bg="#C62828", fg="#FFFFFF",
                      font=("微软雅黑", 8), bd=0, padx=8, pady=2, cursor="hand2",
                      command=lambda rid=record["id"]: self._delete_one(rid)).pack(side=tk.LEFT)

    def _toggle_select(self, record_id, var):
        if var.get():
            self.selected_ids.add(record_id)
        else:
            self.selected_ids.discard(record_id)

    def _copy_to_clipboard(self, text):
        """复制到剪贴板"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        except:
            pass

    def _mark_used(self, record_id):
        update_redeem_code_status(record_id, "已使用")
        self.refresh_list()

    def _mark_unused(self, record_id):
        update_redeem_code_status(record_id, "未使用")
        self.refresh_list()

    def _delete_one(self, record_id):
        delete_redeem_code(record_id)
        self.refresh_list()

    def copy_selected(self):
        """复制选中的兑换码"""
        if not self.selected_ids:
            return
        codes = [r["redeem_code"] for r in self.records if r["id"] in self.selected_ids]
        if codes:
            self._copy_to_clipboard("\\n".join(codes))

    def copy_all(self):
        """复制全部兑换码"""
        if not self.records:
            return
        codes = [r["redeem_code"] for r in self.records]
        self._copy_to_clipboard("\\n".join(codes))

    def export_txt(self):
        """导出为TXT文件"""
        if not self.records:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("===== B站工具箱 兑换码导出 =====\\n")
                f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"共 {len(self.records)} 条\\n")
                f.write("=" * 50 + "\\n\\n")
                for r in self.records:
                    f.write(f"ID: {r['id']}\\n")
                    f.write(f"时间: {r.get('time', '')}\\n")
                    f.write(f"任务: {r.get('task_name', '')}\\n")
                    f.write(f"账户: {r.get('account', '')}\\n")
                    f.write(f"兑换码: {r.get('redeem_code', '')}\\n")
                    f.write(f"状态: {r.get('status', '')}\\n")
                    f.write("-" * 40 + "\\n")
            self._copy_to_clipboard(filepath)
        except Exception as e:
            pass

    def export_csv(self):
        """导出为CSV文件"""
        if not self.records:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.csv")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("ID,领取时间,任务名称,账户,兑换码,字段,状态\\n")
                for r in self.records:
                    f.write(f"{r['id']},{r.get('time','')},{r.get('task_name','')},{r.get('account','')},{r.get('redeem_code','')},{r.get('code_field','')},{r.get('status','')}\\n")
        except Exception as e:
            pass

    def delete_selected(self):
        """删除选中的记录"""
        if not self.selected_ids:
            return
        for rid in list(self.selected_ids):
            delete_redeem_code(rid)
        self.refresh_list()

    def clear_all(self):
        """清空全部记录"""
        clear_redeem_codes()
        self.refresh_list()


'''

# 在 WatchLiveFrame 之前插入
watch_marker = "class WatchLiveFrame(tk.Frame):"
if watch_marker in content:
    content = content.replace(watch_marker, code_frame_class + "\n" + watch_marker, 1)
    print("✓ 步骤4：已添加 CodeExportFrame 类")
else:
    print("✗ 步骤4：未找到 WatchLiveFrame 插入点")

# ============================================================
# 步骤5：在Tab栏添加"🎁 兑换码"标签
# ============================================================
# 在看播任务标签后面添加
old_tab = '''        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))'''

new_tab = '''        self.tab_watch = tk.Label(tab_bar, text="📺 看播任务", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                   font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_watch.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_watch.bind("<Button-1>", lambda e: self.switch_tab("watch"))

        self.tab_code_export = tk.Label(tab_bar, text="🎁 兑换码", bg=COLORS["bg_input"], fg=COLORS["text_secondary"],
                                         font=("微软雅黑", 12), padx=24, pady=10, cursor="hand2")
        self.tab_code_export.pack(side=tk.LEFT, padx=(0, 5), pady=6)
        self.tab_code_export.bind("<Button-1>", lambda e: self.switch_tab("code_export"))'''

if old_tab in content:
    content = content.replace(old_tab, new_tab, 1)
    print("✓ 步骤5：已在Tab栏添加兑换码标签")
else:
    print("✗ 步骤5：未找到Tab栏插入点")

# ============================================================
# 步骤6：在主内容区添加兑换码页面
# ============================================================
old_page = '''        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()'''

new_page = '''        # 看播任务页面
        self.watch_page = WatchLiveFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.watch_page.pack(fill=tk.BOTH, expand=True)
        self.watch_page.pack_forget()

        # 兑换码导出页面
        self.code_export_page = CodeExportFrame(self.tab_container, self.account_mgr, self.room_mgr)
        self.code_export_page.pack(fill=tk.BOTH, expand=True)
        self.code_export_page.pack_forget()'''

if old_page in content:
    content = content.replace(old_page, new_page, 1)
    print("✓ 步骤6：已在主内容区添加兑换码页面")
else:
    print("✗ 步骤6：未找到主内容区插入点")

# ============================================================
# 步骤7：在 switch_tab 函数中添加兑换码页面切换
# ============================================================
# 找到 switch_tab 函数
switch_match = re.search(r'def switch_tab\(self, tab_name\):.*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
if switch_match:
    switch_func = switch_match.group(0)
    # 在watch分支后面添加code_export分支
    if "code_export" not in switch_func:
        old_switch_watch = '''        elif tab_name == "watch":
            self.current_tab = "watch"
            self._set_tab_style("watch")
            self.watch_page.pack(fill=tk.BOTH, expand=True)'''
        new_switch_watch = '''        elif tab_name == "watch":
            self.current_tab = "watch"
            self._set_tab_style("watch")
            self.watch_page.pack(fill=tk.BOTH, expand=True)
        elif tab_name == "code_export":
            self.current_tab = "code_export"
            self._set_tab_style("code_export")
            self.code_export_page.pack(fill=tk.BOTH, expand=True)
            self.code_export_page.refresh_list()'''
        if old_switch_watch in switch_func:
            content = content.replace(old_switch_watch, new_switch_watch, 1)
            print("✓ 步骤7a：已在switch_tab添加兑换码切换")
        else:
            print("✗ 步骤7a：未找到watch切换分支")

        # 在 _set_tab_style 中添加 code_export
        if "_set_tab_style" in content:
            style_match = re.search(r'def _set_tab_style\(self, active_tab\):.*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
            if style_match:
                style_func = style_match.group(0)
                if "code_export" not in style_func:
                    # 在watch样式后面添加
                    old_style_watch = '''        watch_style = self.tab_watch
        if active_tab == "watch":
            watch_style.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 12, "bold"))
        else:
            watch_style.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 12))'''
                    new_style_watch = '''        watch_style = self.tab_watch
        if active_tab == "watch":
            watch_style.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 12, "bold"))
        else:
            watch_style.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 12))

        code_export_style = self.tab_code_export
        if active_tab == "code_export":
            code_export_style.config(bg=COLORS["accent"], fg="#000000", font=("微软雅黑", 12, "bold"))
        else:
            code_export_style.config(bg=COLORS["bg_input"], fg=COLORS["text_secondary"], font=("微软雅黑", 12))'''
                    if old_style_watch in style_func:
                        content = content.replace(old_style_watch, new_style_watch, 1)
                        print("✓ 步骤7b：已在_set_tab_style添加兑换码样式")
                    else:
                        print("✗ 步骤7b：未找到watch样式分支")
else:
    print("✗ 步骤7：未找到switch_tab函数")

# ============================================================
# 步骤8：在 pack_forget 所有页面的地方添加 code_export
# ============================================================
# 找到隐藏所有页面的地方（switch_tab函数开头通常有）
hide_pattern = r'(\s+self\.\w+_page\.pack_forget\(\)\s+){3,}'
hide_matches = list(re.finditer(hide_pattern, content))
for m in hide_matches:
    hide_block = m.group(0)
    if "watch_page.pack_forget" in hide_block and "code_export_page" not in hide_block:
        new_hide = hide_block.replace("self.watch_page.pack_forget()",
                                        "self.watch_page.pack_forget()\n        self.code_export_page.pack_forget()")
        content = content.replace(hide_block, new_hide, 1)
        print("✓ 步骤8：已在隐藏页面处添加code_export")
        break

# ============================================================
# 保存文件
# ============================================================
with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\\n" + "=" * 50)
print("所有修改已保存到 main_gui_pro.py")
print("=" * 50)
