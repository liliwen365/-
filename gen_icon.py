# -*- coding: utf-8 -*-
"""生成应用图标 - 仅需运行一次，不随应用分发。"""
from PIL import Image, ImageDraw, ImageFont
import os

ICON_SIZES = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
BG_COLOR = (41, 98, 255)
FG_COLOR = (255, 255, 255)


def make_icon(size):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = max(1, size[0] // 16)
    r = max(2, size[0] // 8)
    draw.rounded_rectangle([margin, margin, size[0]-margin, size[1]-margin],
                           radius=r, fill=BG_COLOR)

    font_size = max(8, int(size[0] * 0.5))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

    text = "整"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size[0] - tw) / 2
    y = (size[1] - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=FG_COLOR, font=font)

    return img


def main():
    images = [make_icon(s) for s in ICON_SIZES]

    out_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(out_dir, exist_ok=True)

    ico_path = os.path.join(out_dir, "icon.ico")
    images[-1].save(ico_path, format="ICO", sizes=[(s.width, s.height) for s in images])
    print(f"已保存 {ico_path}")

    png_path = os.path.join(out_dir, "icon.png")
    images[-1].save(png_path, format="PNG")
    print(f"已保存 {png_path}")


if __name__ == "__main__":
    main()
