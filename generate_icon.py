#!/usr/bin/env python3
"""生成B站工具箱图标"""
from PIL import Image, ImageDraw, ImageFont
import math

def create_icon(size):
    """生成指定尺寸的图标"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角方形背景 - B站粉蓝渐变
    radius = int(size * 0.22)
    # 创建渐变
    for y in range(size):
        for x in range(size):
            # 检查是否在圆角矩形内
            cx, cy = size/2, size/2
            dx = abs(x - cx) - (size/2 - radius)
            dy = abs(y - cy) - (size/2 - radius)
            if dx > 0 and dy > 0:
                if dx*dx + dy*dy > radius*radius:
                    continue
            elif dx < 0 or dy < 0:
                pass
            else:
                continue
            # 渐变：左上粉色 -> 右下蓝色
            t = (x + y) / (2 * size)
            r = int(0xFB * (1-t) + 0x00 * t)
            g = int(0x72 * (1-t) + 0xA1 * t)
            b = int(0x99 * (1-t) + 0xD6 * t)
            img.putpixel((x, y), (r, g, b, 255))

    # 白色播放按钮（三角形）
    play_size = int(size * 0.35)
    cx = size // 2
    cy = size // 2
    # 三角形顶点
    p1 = (cx - play_size//3, cy - play_size//2)
    p2 = (cx - play_size//3, cy + play_size//2)
    p3 = (cx + play_size//2, cy)
    draw.polygon([p1, p2, p3], fill=(255, 255, 255, 255))

    # 底部小字 "B"
    try:
        font_size = int(size * 0.18)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    text = "B"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = int(size * 0.72)
    draw.text((tx, ty), text, fill=(255, 255, 255, 230), font=font)

    return img

# 生成多个尺寸
sizes = [16, 24, 32, 48, 64, 128, 256]
icons = []
for s in sizes:
    icons.append(create_icon(s))

# 保存为ico
icons[0].save('app_icon.ico', format='ICO', sizes=[(s, s) for s in sizes])
print("图标已生成: app_icon.ico")

# 同时保存一个256x256的png预览
icons[-1].save('app_icon_preview.png')
print("预览图已生成: app_icon_preview.png")
