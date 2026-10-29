file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace('APP_VERSION = "v4.2.8"', 'APP_VERSION = "v4.2.9"')
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("版本号已更新到 v4.2.9")
