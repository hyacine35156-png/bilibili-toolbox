file_path = r'C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在start_watch函数末尾添加except块
old_end = '''        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
        self.watch_thread.start()

    def stop_watch(self):'''

new_end = '''        self.watch_thread = threading.Thread(target=self._watch_loop, args=(room_ids, selected_accounts), daemon=True)
        self.watch_thread.start()
        self.log("[调试] start_watch执行完成，线程已启动")
        except Exception as e:
            import traceback
            self.log(f"[错误] start_watch异常: {e}")
            self.log(traceback.format_exc())
            # 恢复按钮状态
            self.running = False
            try:
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
            except Exception:
                pass
            messagebox.showerror("错误", f"启动看播失败: {e}")

    def stop_watch(self):'''

if old_end in content:
    content = content.replace(old_end, new_end)
    print("✓ 已在start_watch函数末尾添加except块")
else:
    print("✗ 未找到函数结束位置")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ 文件已保存")
