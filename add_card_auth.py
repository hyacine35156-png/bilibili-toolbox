#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为B站工具箱添加卡密验证功能
"""

import re

FILE_PATH = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

# 读取文件
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新版本号
content = content.replace('APP_VERSION = "v5.3.0"', 'APP_VERSION = "v5.4.0"')

# 2. 在版本号后添加卡密验证配置
card_config = '''
# ========== 卡密验证配置 ==========
CARD_API_BASE = "https://precious-tanuki-c4b16d.netlify.app/api"
CARD_VERIFY_URL = f"{CARD_API_BASE}/verify-card"
CARD_FILE = BASE_DIR / "card_auth.json"
'''

# 在APP_VERSION行后插入卡密配置
content = content.replace(
    'APP_VERSION = "v5.4.0"\n',
    'APP_VERSION = "v5.4.0"\n' + card_config
)

# 3. 在main函数之前添加卡密验证相关代码
card_verify_code = '''

# ========== 卡密验证功能 ==========
def get_machine_code():
    """获取设备唯一标识（CPU+硬盘+主板序列号组合哈希）"""
    import hashlib
    machine_info = ""
    
    try:
        import subprocess
        # CPU ID
        try:
            result = subprocess.run(['wmic', 'cpu', 'get', 'ProcessorId'], 
                                  capture_output=True, text=True, timeout=5)
            cpu_id = result.stdout.strip().split('\\n')[-1].strip() if result.stdout else ""
            machine_info += f"CPU:{cpu_id};"
        except Exception:
            pass
        
        # 硬盘序列号
        try:
            result = subprocess.run(['wmic', 'diskdrive', 'get', 'SerialNumber'], 
                                  capture_output=True, text=True, timeout=5)
            disk_id = result.stdout.strip().split('\\n')[-1].strip() if result.stdout else ""
            machine_info += f"DISK:{disk_id};"
        except Exception:
            pass
        
        # 主板序列号
        try:
            result = subprocess.run(['wmic', 'baseboard', 'get', 'SerialNumber'], 
                                  capture_output=True, text=True, timeout=5)
            board_id = result.stdout.strip().split('\\n')[-1].strip() if result.stdout else ""
            machine_info += f"BOARD:{board_id};"
        except Exception:
            pass
    except Exception:
        pass
    
    # 如果获取不到硬件信息，使用MAC地址
    if not machine_info or machine_info == "CPU:;DISK:;BOARD:;":
        try:
            import uuid
            machine_info = f"MAC:{uuid.getnode()}"
        except Exception:
            machine_info = "UNKNOWN_MACHINE"
    
    return hashlib.md5(machine_info.encode()).hexdigest()


def verify_card_online(card_code, machine_code):
    """在线验证卡密"""
    try:
        resp = requests.post(
            CARD_VERIFY_URL,
            json={"card_code": card_code, "machine_code": machine_code},
            timeout=15
        )
        result = resp.json()
        return result.get("code", -99) == 0, result
    except Exception as e:
        return False, {"code": -99, "msg": f"网络错误: {str(e)}"}


def load_saved_card():
    """加载保存的卡密信息"""
    try:
        if CARD_FILE.exists():
            with open(CARD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_card_info(card_code, card_info):
    """保存卡密信息"""
    try:
        data = {
            "card_code": card_code,
            "card_type": card_info.get("card_type"),
            "expires_at": card_info.get("expires_at"),
            "remaining_days": card_info.get("remaining_days"),
            "last_verify": datetime.now().isoformat()
        }
        with open(CARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class CardAuthDialog:
    """卡密验证弹窗"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.card_info = None
        
        # 创建弹窗
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("卡密验证 - B站工具箱")
        self.dialog.geometry("450x350")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=COLORS["bg_dark"])
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (parent.winfo_screenwidth() - 450) // 2
        y = (parent.winfo_screenheight() - 350) // 2
        self.dialog.geometry(f"450x350+{x}+{y}")
        
        # 使弹窗模态
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._build_ui()
        
        # 检查是否有保存的卡密
        saved = load_saved_card()
        if saved and saved.get("card_code"):
            self.card_entry.insert(0, saved["card_code"])
            # 自动验证
            self.dialog.after(500, self._verify)
    
    def _build_ui(self):
        """构建UI"""
        # 标题
        title_frame = tk.Frame(self.dialog, bg=COLORS["bg_dark"])
        title_frame.pack(fill=tk.X, pady=(30, 10))
        
        tk.Label(title_frame, text="🔐 卡密验证", 
                bg=COLORS["bg_dark"], fg=COLORS["accent"],
                font=("微软雅黑", 18, "bold")).pack()
        
        tk.Label(title_frame, text="请输入您的卡密以激活软件", 
                bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
                font=("微软雅黑", 10)).pack(pady=(5, 0))
        
        # 卡密输入
        input_frame = tk.Frame(self.dialog, bg=COLORS["bg_dark"])
        input_frame.pack(fill=tk.X, padx=40, pady=(20, 10))
        
        tk.Label(input_frame, text="卡密:", 
                bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                font=("微软雅黑", 11)).pack(anchor=tk.W)
        
        self.card_entry = tk.Entry(input_frame, 
                                   bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                                   insertbackground=COLORS["accent"],
                                   font=("微软雅黑", 12),
                                   relief=tk.FLAT, justify=tk.CENTER)
        self.card_entry.pack(fill=tk.X, pady=(5, 0), ipady=8)
        self.card_entry.bind('<Return>', lambda e: self._verify())
        
        # 状态标签
        self.status_label = tk.Label(self.dialog, text="", 
                                    bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                                    font=("微软雅黑", 9))
        self.status_label.pack(pady=(5, 0))
        
        # 按钮
        btn_frame = tk.Frame(self.dialog, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=40, pady=(20, 0))
        
        verify_btn = tk.Button(btn_frame, text="验证激活", 
                              bg=COLORS["accent"], fg="#000000",
                              font=("微软雅黑", 11, "bold"),
                              relief=tk.FLAT, cursor="hand2",
                              command=self._verify)
        verify_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5), ipady=8)
        
        cancel_btn = tk.Button(btn_frame, text="退出", 
                             bg=COLORS["danger"], fg="#ffffff",
                             font=("微软雅黑", 11, "bold"),
                             relief=tk.FLAT, cursor="hand2",
                             command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0), ipady=8)
        
        # 机器码显示
        machine_code = get_machine_code()
        tk.Label(self.dialog, text=f"设备码: {machine_code[:8]}...{machine_code[-8:]}", 
                bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                font=("微软雅黑", 8)).pack(side=tk.BOTTOM, pady=(0, 15))
    
    def _verify(self):
        """验证卡密"""
        card_code = self.card_entry.get().strip().upper()
        if not card_code:
            self.status_label.config(text="⚠ 请输入卡密", fg=COLORS["warning"])
            return
        
        self.status_label.config(text="⏳ 正在验证...", fg=COLORS["text_secondary"])
        self.dialog.update()
        
        machine_code = get_machine_code()
        success, result = verify_card_online(card_code, machine_code)
        
        if success:
            self.status_label.config(text=f"✓ {result.get('msg', '验证成功')}", fg=COLORS["success"])
            self.result = True
            self.card_info = result
            save_card_info(card_code, result)
            self.dialog.after(1000, self.dialog.destroy)
        else:
            code = result.get("code", -99)
            msg = result.get("msg", "验证失败")
            self.status_label.config(text=f"✗ {msg}", fg=COLORS["danger"])
            
            # 如果是网络错误，允许离线模式（7天内验证过的）
            if code == -99:
                saved = load_saved_card()
                if saved and saved.get("card_code") == card_code:
                    try:
                        last_verify = datetime.fromisoformat(saved.get("last_verify", ""))
                        days_diff = (datetime.now() - last_verify).days
                        if days_diff <= 7:
                            self.status_label.config(text=f"⚠ 网络错误，使用离线验证（剩余{7-days_diff}天）", fg=COLORS["warning"])
                            self.result = True
                            self.card_info = saved
                            self.dialog.after(1500, self.dialog.destroy)
                            return
                    except Exception:
                        pass
    
    def _cancel(self):
        """取消"""
        self.result = False
        self.dialog.destroy()


def show_card_auth(root):
    """显示卡密验证弹窗，返回是否验证通过"""
    dialog = CardAuthDialog(root)
    root.wait_window(dialog.dialog)
    return dialog.result, dialog.card_info

'''

# 在def main()之前插入卡密验证代码
content = content.replace(
    'def main():',
    card_verify_code + '\ndef main():'
)

# 4. 修改main函数，添加卡密验证
old_main = '''def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        # 尝试设置Per-Monitor DPI Aware（Windows 8.1+）
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # 降级为System DPI Aware（Windows Vista+）
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    app = DanmakuApp(root)
    root.mainloop()'''

new_main = '''def main():
    # 设置DPI感知，解决高DPI显示器上文字模糊问题
    try:
        import ctypes
        # 尝试设置Per-Monitor DPI Aware（Windows 8.1+）
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # 降级为System DPI Aware（Windows Vista+）
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    root.withdraw()  # 先隐藏主窗口
    
    # 卡密验证
    auth_success, card_info = show_card_auth(root)
    
    if not auth_success:
        root.destroy()
        return
    
    root.deiconify()  # 显示主窗口
    app = DanmakuApp(root)
    root.mainloop()'''

content = content.replace(old_main, new_main)

# 写回文件
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print("卡密验证功能添加完成！")
print(f"版本号已更新为 v5.4.0")
