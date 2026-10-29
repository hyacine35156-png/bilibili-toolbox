import re

file_path = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\main_gui_pro.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"原始行数: {len(lines)}")

# 1. 删除AutoUploadFrame类（从"# ========== 自动投稿工具窗口 =========="到"# ========== 主界面 =========="之前）
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "# ========== 自动投稿工具窗口 ==========" in line:
        start_idx = i
    if start_idx is not None and "# ========== 主界面 ==========" in line:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    print(f"删除AutoUploadFrame类: 行{start_idx+1}到行{end_idx} (共{end_idx-start_idx}行)")
    del lines[start_idx:end_idx]

# 重新计算行号后，继续删除其他内容
content = "".join(lines)

# 2. 删除tab_upload标签按钮（整块）
content = re.sub(
    r'\n\s*self\.tab_upload = tk\.Label\(tab_bar.*?self\.tab_upload\.bind\("<Button-1>", lambda e: self\.switch_tab\("upload"\)\)\n',
    '\n',
    content,
    flags=re.DOTALL
)

# 3. 删除自动投稿页面创建（整块）
content = re.sub(
    r'\n\s*# 自动投稿页面\n\s*self\.upload_page = AutoUploadFrame\(self\.tab_container, self\.account_mgr\)\n\s*self\.upload_page\.pack\(fill=tk\.BOTH, expand=True\)\n\s*self\.upload_page\.pack_forget\(\)\n',
    '\n',
    content
)

# 4. 删除switch_tab中的upload相关
# 4a. 删除隐藏upload_page
content = content.replace('        self.upload_page.pack_forget()\n', '')
# 4b. 删除重置tab_upload样式
content = re.sub(r'\n\s*self\.tab_upload\.config\(bg=COLORS\["bg_input"\], fg=COLORS\["text_secondary"\], font=\("微软雅黑", 10\)\)', '', content)
# 4c. 删除upload分支
content = re.sub(
    r'\n\s*elif tab_name == "upload":\n\s*self\.upload_page\.pack\(fill=tk\.BOTH, expand=True\)\n\s*self\.tab_upload\.config\(bg=COLORS\["accent"\], fg="#000000", font=\("微软雅黑", 10, "bold"\)\)\n\s*self\.current_tab = "upload"\n\s*# 切换到自动投稿时刷新账户列表\n\s*self\.upload_page\.refresh_account_list\(\)',
    '',
    content
)

# 5. 删除on_closing中的upload_page保存
content = re.sub(
    r'\n\s*# 保存自动投稿配置\n\s*if hasattr\(self, \'upload_page\'\):\n\s*self\.upload_page\.on_close\(\)',
    '',
    content
)

# 6. 修改窗口标题
content = content.replace(
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机+自动投稿")',
    'self.root.title(f"B站工具箱 {APP_VERSION} - 弹幕+抢码+定时关机")'
)

# 7. 修改header文字
content = content.replace(
    'tk.Label(title_frame, text="  弹幕+抢码+定时关机+自动投稿", bg=COLORS["bg_card"],',
    'tk.Label(title_frame, text="  弹幕+抢码+定时关机", bg=COLORS["bg_card"],'
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# 验证删除结果
with open(file_path, "r", encoding="utf-8") as f:
    final_content = f.read()

checks = [
    ("AutoUploadFrame", "AutoUploadFrame类"),
    ("upload_page", "upload_page引用"),
    ("tab_upload", "tab_upload引用"),
    ("自动投稿", "自动投稿文字"),
    ("switch_tab(\"upload\")", "upload标签切换"),
    ("load_upload_config", "投稿配置加载"),
    ("save_upload_config", "投稿配置保存"),
    ("transcode_video", "视频转码"),
    ("generate_cover", "封面生成"),
    ("b站_upload", "视频上传"),
    ("b站_submit_video", "投稿提交"),
    ("probe_video", "视频检测"),
    ("ffmpeg", "FFmpeg引用"),
]

print("\n=== 验证删除结果 ===")
all_clean = True
for keyword, desc in checks:
    count = final_content.count(keyword)
    status = "✓ 已删除" if count == 0 else f"✗ 仍存在{count}处"
    if count > 0:
        all_clean = False
    print(f"  {desc}: {status}")

print(f"\n最终行数: {len(final_content.splitlines())}")
print(f"\n{'全部清理干净!' if all_clean else '仍有残留，需要进一步检查'}")
