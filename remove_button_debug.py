file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 移除DarkButton的_on_click方法中的调试弹窗代码
old_on_click = '''    def _on_click(self, e):
        # 调试：检查点击事件是否被触发
        debug_msg = f"按钮被点击: {self.text}\\ncommand是否存在: {self.command is not None}"
        if self.command:
            try:
                self.command()
                debug_msg += "\\n✓ command执行成功"
            except Exception as ex:
                import traceback
                debug_msg += f"\\n✗ command执行异常: {ex}\\n{traceback.format_exc()}"
                try:
                    from tkinter import messagebox
                    messagebox.showerror("按钮调试", debug_msg)
                except Exception:
                    pass
                return
        else:
            debug_msg += "\\n✗ command为None"
        # 只在调试模式下显示，避免每次点击都弹窗
        # 临时开启调试弹窗
        try:
            from tkinter import messagebox
            messagebox.showinfo("按钮调试", debug_msg)
        except Exception:
            pass'''

new_on_click = '''    def _on_click(self, e):
        if self.command:
            try:
                self.command()
            except Exception as ex:
                import traceback
                print(f"[DarkButton错误] 按钮 {self.text} 的command执行异常: {ex}")
                traceback.print_exc()'''

if old_on_click in content:
    content = content.replace(old_on_click, new_on_click)
    print("✓ 已移除DarkButton的_on_click方法中的调试弹窗代码")
else:
    print("✗ 未找到_on_click方法中的调试代码")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
