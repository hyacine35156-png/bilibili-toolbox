# -*- coding: utf-8 -*-
"""卡密认证页面。"""

import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

from config import COLORS, CARD_FILE
from widgets import DarkButton, DarkEntry
from card_auth import (get_machine_code, verify_card_online, load_saved_card,
                       is_card_expired, save_card_info, clear_saved_card)


class CardAuthFrame:
    """卡密验证界面（直接在主窗口显示，不用Toplevel）"""
    
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.result = False
        self.card_info = None
        self._verifying = False
        
        # 清空主窗口
        for widget in root.winfo_children():
            widget.destroy()
        
        # 设置窗口
        root.title("卡密验证 - B站工具箱")
        root.geometry("480x380")
        root.resizable(True, True)
        root.minsize(420, 340)
        root.configure(bg=COLORS["bg_dark"])
        
        # 居中
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 480) // 2
        y = (root.winfo_screenheight() - 380) // 2
        root.geometry(f"480x380+{x}+{y}")
        
        self._build_ui()
        
        # 检查是否有保存的卡密
        saved = load_saved_card()
        if saved and saved.get("card_code"):
            # 先检查本地是否过期
            if is_card_expired(saved):
                # 已过期，删除保存的卡密，显示验证界面
                try:
                    CARD_FILE.unlink()
                except Exception:
                    pass
                self.status_label.config(text="⚠ 卡密已过期，请重新输入", fg=COLORS["warning"])
            else:
                # 未过期，先在线验证卡密状态（检查是否被封禁）
                self.status_label.config(text="⏳ 正在验证卡密状态...", fg=COLORS["text_secondary"])
                self._verify_saved_card(saved)
                return
    
    def _build_ui(self):
        """构建UI"""
        # 标题
        title_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        title_frame.pack(fill=tk.X, pady=(30, 10))
        
        tk.Label(title_frame, text="🔐 卡密验证", 
                bg=COLORS["bg_dark"], fg=COLORS["accent"],
                font=("微软雅黑", 18, "bold")).pack()
        
        tk.Label(title_frame, text="请输入您的卡密以激活软件", 
                bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
                font=("微软雅黑", 10)).pack(pady=(5, 0))
        
        # 卡密输入
        input_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
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
        self.status_label = tk.Label(self.root, text="", 
                                    bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                                    font=("微软雅黑", 9))
        self.status_label.pack(pady=(5, 0))
        
        # 按钮
        btn_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=40, pady=(20, 0))
        
        self.verify_btn = DarkButton(btn_frame, text="验证激活",
                              width=160, height=44,
                              bg_color=COLORS["accent"], text_color="#000000",
                              command=self._verify)
        self.verify_btn.pack(side=tk.LEFT, padx=(0, 10), pady=0)
        
        cancel_btn = DarkButton(btn_frame, text="退出",
                             width=160, height=44,
                             bg_color=COLORS["danger"], text_color="#ffffff",
                             command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0), pady=0)
        
        # 机器码显示
        machine_code = get_machine_code()
        tk.Label(self.root, text=f"设备码: {machine_code[:8]}...{machine_code[-8:]}", 
                bg=COLORS["bg_dark"], fg=COLORS["text_muted"],
                font=("微软雅黑", 8)).pack(side=tk.BOTTOM, pady=(0, 15))
    
    def _verify(self):
        """验证卡密（后台线程）"""
        card_code = self.card_entry.get().strip().upper()
        if not card_code:
            self.status_label.config(text="⚠ 请输入卡密", fg=COLORS["warning"])
            return
        
        if self._verifying:
            return
        
        self._verifying = True
        self.verify_btn.config(state=tk.DISABLED, text="验证中...")
        self.status_label.config(text="⏳ 正在验证...", fg=COLORS["text_secondary"])
        
        def verify_thread():
            try:
                machine_code = get_machine_code()
                success, result = verify_card_online(card_code, machine_code)
            except Exception as e:
                success = False
                result = {"code": -99, "msg": f"验证异常: {str(e)}"}
            
            self.root.after(0, lambda: self._verify_result(card_code, success, result))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def _verify_result(self, card_code, success, result):
        """验证结果回调"""
        self._verifying = False
        self.verify_btn.config(state=tk.NORMAL, text="验证激活")
        
        if success:
            self.status_label.config(text=f"✓ {result.get('msg', '验证成功')}", fg=COLORS["success"])
            self.result = True
            self.card_info = result
            save_card_info(card_code, result)
            self.root.after(1000, lambda: self.on_success(self.card_info))
        else:
            code = result.get("code", -99)
            msg = result.get("msg", "验证失败")
            self.status_label.config(text=f"✗ {msg}", fg=COLORS["danger"])
            
            # 网络错误时尝试离线验证
            if code == -99:
                saved = load_saved_card()
                if saved and saved.get("card_code") == card_code:
                    try:
                        last_verify = datetime.strptime(saved.get("last_verify", ""), "%Y-%m-%dT%H:%M:%S")
                        days_diff = (datetime.now() - last_verify).days
                        if days_diff <= 1:
                            self.status_label.config(text=f"⚠ 网络错误，离线验证（剩余{1-days_diff}天）", fg=COLORS["warning"])
                            self.result = True
                            self.card_info = saved
                            # 更新本地缓存的last_verify时间，使离线宽限持续有效
                            save_card_info(card_code, saved)
                            self.root.after(1500, lambda: self.on_success(self.card_info))
                            return
                    except Exception:
                        pass
                    # 有保存的卡密但离线验证失败（超过1天或解析异常），清除缓存并提示
                    self.status_label.config(text="⚠ 网络错误且离线验证已过期，请重新输入", fg=COLORS["danger"])
                    clear_saved_card()
                else:
                    # 没有保存的卡密或卡密不匹配，只提示网络错误，不清除缓存
                    self.status_label.config(text="⚠ 网络错误，请检查网络后重试", fg=COLORS["warning"])
    
    def _verify_saved_card(self, saved):
        """在线验证保存的卡密状态（检查是否被封禁）"""
        card_code = saved.get("card_code")
        
        def verify_thread():
            try:
                machine_code = get_machine_code()
                success, result = verify_card_online(card_code, machine_code)
            except Exception as e:
                success = False
                result = {"code": -99, "msg": f"验证异常: {str(e)}"}
            
            self.root.after(0, lambda: self._verify_saved_card_result(saved, success, result))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def _verify_saved_card_result(self, saved, success, result):
        """保存卡密的在线验证结果"""
        card_code = saved.get("card_code")
        
        if success:
            # 在线验证通过，更新本地缓存并登录
            self.status_label.config(text="✓ 卡密有效，正在进入...", fg=COLORS["success"])
            self.result = True
            self.card_info = result
            save_card_info(card_code, result)
            self.root.after(1000, lambda: self.on_success(self.card_info))
        else:
            code = result.get("code", -99)
            msg = result.get("msg", "验证失败")
            
            if code == -99:
                # 网络错误，尝试离线登录（1天宽限期）
                try:
                    last_verify = datetime.strptime(saved.get("last_verify", ""), "%Y-%m-%dT%H:%M:%S")
                    days_diff = (datetime.now() - last_verify).days
                    if days_diff <= 1:
                        self.status_label.config(text=f"⚠ 网络错误，离线验证（剩余{1-days_diff}天）", fg=COLORS["warning"])
                        self.result = True
                        self.card_info = saved
                        # 更新本地缓存的last_verify时间，使离线宽限持续有效
                        save_card_info(card_code, saved)
                        self.root.after(1500, lambda: self.on_success(self.card_info))
                        return
                except Exception:
                    pass
                
                # 超过1天或解析失败，清除本地缓存，要求重新输入
                self.status_label.config(text="⚠ 网络错误且离线验证已过期，请重新输入", fg=COLORS["danger"])
                clear_saved_card()
            else:
                # 卡密被封禁/过期/绑定其他设备，清除本地缓存，要求重新输入
                self.status_label.config(text=f"✗ {msg}，请重新输入", fg=COLORS["danger"])
                clear_saved_card()
    
    def _cancel(self):
        """取消"""
        self.result = False
        self.root.destroy()


def show_card_auth(root):
    """显示卡密验证界面，阻塞直到验证通过或退出"""
    result = {"success": False, "card_info": None}
    
    def on_success(card_info):
        result["success"] = True
        result["card_info"] = card_info
        root.quit()
    
    frame = CardAuthFrame(root, on_success)
    
    # 进入事件循环，直到验证通过或窗口关闭
    root.mainloop()
    
    return result["success"], result["card_info"]
