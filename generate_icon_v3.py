#!/usr/bin/env python3
"""生成超清晰B站工具箱图标 - 纯色背景+大播放按钮，每尺寸单独绘制"""
from PIL import Image, ImageDraw

def draw_icon(size):
    """为每个尺寸单独精确绘制"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # B站粉纯色背景 - 圆角矩形
    bg_color = (251, 114, 153, 255)  # #FB7299
    radius = max(2, int(size * 0.22))
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=bg_color)

    # 白色播放按钮 - 大尺寸，占据60%宽度
    play_w = int(size * 0.42)
    play_h = int(size * 0.50)
    cx = size // 2
    cy = size // 2
    # 等腰三角形
    p1 = (cx - play_w//2, cy - play_h//2)
    p2 = (cx - play_w//2, cy + play_h//2)
    p3 = (cx + play_w//2, cy)
    draw.polygon([p1, p2, p3], fill=(255, 255, 255, 255))

    return img

# 为每个尺寸单独绘制（不从大图缩小，避免模糊）
sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
icons = [draw_icon(s) for s in sizes]

# 保存为ico
icons[0].save('app_icon.ico', format='ICO',
               sizes=[(s, s) for s in sizes],
               append_images=icons[1:])
print("图标已生成: app_icon.ico (10个尺寸，每尺寸单独绘制)")

# 保存256px预览
icons[-1].save('app_icon_preview.png')
print("预览图已生成: app_icon_preview.png")

# 也保存48px预览（任务栏常见尺寸）
icons[sizes.index(48)].save('app_icon_48.png')
print("48px预览已生成: app_icon_48.png")
