file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在DarkButton的_on_click方法中添加调试日志
old_on_click = '''    def _on_click(self, e):
        if self.command:
            self.command()'''

new_on_click = '''    def _on_click(self, e):
        # 调试：检查点击事件是否被触发
        print(f"[DarkButton调试] 按钮被点击: text={self.text}, command={self.command is not None}")
        if self.command:
            try:
                self.command()
            except Exception as ex:
                print(f"[DarkButton调试] command执行异常: {ex}")
                import traceback
                traceback.print_exc()
        else:
            print("[DarkButton调试] command为None")'''

if old_on_click in content:
    content = content.replace(old_on_click, new_on_click)
    print("✓ 已在_on_click方法中添加调试日志")
else:
    print("✗ 未找到_on_click方法")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
