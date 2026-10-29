# -*- coding: utf-8 -*-
"""添加兑换码页面的活动筛选功能"""

FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在__init__中添加活动筛选变量
old_init = '''    def __init__(self, parent, account_mgr=None, room_mgr=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.selected_ids = set()
        self.build_ui()
        self.refresh_list()'''

new_init = '''    def __init__(self, parent, account_mgr=None, room_mgr=None):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.account_mgr = account_mgr
        self.room_mgr = room_mgr
        self.selected_ids = set()
        self.current_activity_filter = "全部活动"
        self.build_ui()
        self.refresh_list()'''

if old_init in content:
    content = content.replace(old_init, new_init, 1)
    print("✓ 已添加活动筛选变量")
else:
    print("✗ 未找到__init__代码")

# 2. 在统计信息旁边添加活动筛选下拉框
old_stats = '''        # 统计信息
        self.stats_label = tk.Label(btn_bar, text="", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 10))
        self.stats_label.pack(side=tk.RIGHT, padx=20)'''

new_stats = '''        # 活动筛选下拉框
        filter_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        filter_frame.pack(side=tk.RIGHT, padx=(0, 15))
        
        tk.Label(filter_frame, text="活动筛选:", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 8))
        
        from tkinter import ttk
        activity_list = ["全部活动"] + list(VERSION_DEFAULT_ACT_ID.keys())
        self.activity_filter_var = tk.StringVar(value="全部活动")
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Filter.TCombobox', 
                        fieldbackground=COLORS["bg_input"], 
                        background=COLORS["bg_input"],
                        foreground=COLORS["text_primary"],
                        arrowcolor=COLORS["accent"])
        
        self.activity_filter_combo = ttk.Combobox(filter_frame, textvariable=self.activity_filter_var,
                                                    values=activity_list, state="readonly",
                                                    font=("微软雅黑", 10), width=18,
                                                    style='Filter.TCombobox')
        self.activity_filter_combo.pack(side=tk.LEFT)
        self.activity_filter_combo.bind("<<ComboboxSelected>>", self._on_activity_filter_change)

        # 统计信息
        self.stats_label = tk.Label(btn_bar, text="", bg=COLORS["bg_card"],
                                     fg=COLORS["text_muted"], font=("微软雅黑", 10))
        self.stats_label.pack(side=tk.RIGHT, padx=20)'''

if old_stats in content:
    content = content.replace(old_stats, new_stats, 1)
    print("✓ 已添加活动筛选下拉框")
else:
    print("✗ 未找到统计信息代码")

# 3. 添加活动筛选变更处理方法和获取筛选后记录的方法
# 在_on_mousewheel方法后面添加
old_mousewheel = '''    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")'''

new_mousewheel = '''    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_activity_filter_change(self, event=None):
        """活动筛选变更"""
        self.current_activity_filter = self.activity_filter_var.get()
        self.refresh_list()
    
    def _get_filtered_records(self, records=None):
        """获取筛选后的记录"""
        if records is None:
            records = self.records
        if self.current_activity_filter == "全部活动":
            return records
        # 根据task_name前缀筛选（task_name格式为"活动名称 奖励名称"）
        filtered = []
        for r in records:
            task_name = r.get("task_name", "")
            if task_name.startswith(self.current_activity_filter):
                filtered.append(r)
        return filtered'''

if old_mousewheel in content:
    content = content.replace(old_mousewheel, new_mousewheel, 1)
    print("✓ 已添加活动筛选变更处理方法")
else:
    print("✗ 未找到_on_mousewheel代码")

# 4. 修改refresh_list方法，使用筛选后的记录
old_refresh = '''        records = load_redeem_codes()
        self.records = records

        # 更新统计
        total = len(records)
        unused = sum(1 for r in records if r.get("status") == "未使用")
        used = sum(1 for r in records if r.get("status") == "已使用")
        self.stats_label.config(text=f"共 {total} 条 | 未使用 {unused} | 已使用 {used}")

        if not records:'''

new_refresh = '''        all_records = load_redeem_codes()
        self.records = all_records
        records = self._get_filtered_records(all_records)

        # 更新统计（显示筛选后的数量和总数）
        total = len(records)
        total_all = len(all_records)
        unused = sum(1 for r in records if r.get("status") == "未使用")
        used = sum(1 for r in records if r.get("status") == "已使用")
        if self.current_activity_filter == "全部活动":
            self.stats_label.config(text=f"共 {total} 条 | 未使用 {unused} | 已使用 {used}")
        else:
            self.stats_label.config(text=f"筛选 {total}/{total_all} 条 | 未使用 {unused} | 已使用 {used}")

        if not records:'''

if old_refresh in content:
    content = content.replace(old_refresh, new_refresh, 1)
    print("✓ 已修改refresh_list使用筛选后的记录")
else:
    print("✗ 未找到refresh_list代码")

# 5. 修改copy_selected方法，使用筛选后的记录
old_copy_selected = '''    def copy_selected(self):
        """复制选中的兑换码"""
        if not self.selected_ids:
            return
        codes = [r["redeem_code"] for r in self.records if r["id"] in self.selected_ids]
        if codes:
            self._copy_to_clipboard("\\n".join(codes))'''

new_copy_selected = '''    def copy_selected(self):
        """复制选中的兑换码（仅筛选后的记录）"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        codes = [r["redeem_code"] for r in filtered if r["id"] in self.selected_ids]
        if codes:
            self._copy_to_clipboard("\\n".join(codes))'''

if old_copy_selected in content:
    content = content.replace(old_copy_selected, new_copy_selected, 1)
    print("✓ 已修改copy_selected")
else:
    print("✗ 未找到copy_selected代码")

# 6. 修改copy_all方法，使用筛选后的记录
old_copy_all = '''    def copy_all(self):
        """复制全部兑换码"""
        if not self.records:
            return
        codes = [r["redeem_code"] for r in self.records]
        self._copy_to_clipboard("\\n".join(codes))'''

new_copy_all = '''    def copy_all(self):
        """复制全部兑换码（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        codes = [r["redeem_code"] for r in filtered]
        self._copy_to_clipboard("\\n".join(codes))'''

if old_copy_all in content:
    content = content.replace(old_copy_all, new_copy_all, 1)
    print("✓ 已修改copy_all")
else:
    print("✗ 未找到copy_all代码")

# 7. 修改export_txt方法，使用筛选后的记录
old_export_txt = '''    def export_txt(self):
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
                for r in self.records:'''

new_export_txt = '''    def export_txt(self):
        """导出为TXT文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("===== B站工具箱 兑换码导出 =====\\n")
                f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"活动筛选: {self.current_activity_filter}\\n")
                f.write(f"共 {len(filtered)} 条\\n")
                f.write("=" * 50 + "\\n\\n")
                for r in filtered:'''

if old_export_txt in content:
    content = content.replace(old_export_txt, new_export_txt, 1)
    print("✓ 已修改export_txt")
else:
    print("✗ 未找到export_txt代码")

# 8. 修改export_csv方法，使用筛选后的记录
old_export_csv = '''    def export_csv(self):
        """导出为CSV文件"""
        if not self.records:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.csv")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("ID,领取时间,任务名称,账户,兑换码,字段,状态\\n")
                for r in self.records:'''

new_export_csv = '''    def export_csv(self):
        """导出为CSV文件（仅筛选后的记录）"""
        filtered = self._get_filtered_records()
        if not filtered:
            return
        try:
            _ensure_code_dir()
            filepath = os.path.join(os.path.dirname(CODE_EXPORT_FILE), "兑换码导出.csv")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("ID,领取时间,任务名称,账户,兑换码,字段,状态\\n")
                for r in filtered:'''

if old_export_csv in content:
    content = content.replace(old_export_csv, new_export_csv, 1)
    print("✓ 已修改export_csv")
else:
    print("✗ 未找到export_csv代码")

# 9. 修改delete_selected方法，使用筛选后的记录
old_delete_selected = '''    def delete_selected(self):
        """删除选中的记录"""
        if not self.selected_ids:
            return
        for rid in list(self.selected_ids):
            delete_redeem_code(rid)
        self.refresh_list()'''

new_delete_selected = '''    def delete_selected(self):
        """删除选中的记录（仅筛选后的记录中选中的）"""
        if not self.selected_ids:
            return
        filtered = self._get_filtered_records()
        filtered_ids = set(r["id"] for r in filtered)
        for rid in list(self.selected_ids):
            if rid in filtered_ids:
                delete_redeem_code(rid)
        self.refresh_list()'''

if old_delete_selected in content:
    content = content.replace(old_delete_selected, new_delete_selected, 1)
    print("✓ 已修改delete_selected")
else:
    print("✗ 未找到delete_selected代码")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\\n✓ 所有修改完成")
