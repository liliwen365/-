# -*- coding: utf-8 -*-
"""系统托盘 - pystray。"""
import webbrowser
from backend.logger import logger


def run_tray(url: str):
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        return

    def create_icon():
        img = Image.new("RGBA", (64, 64), (33, 150, 243, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([8, 8, 56, 56], radius=12, fill=(255, 255, 255, 255))
        draw.text((20, 18), "LA", fill=(33, 150, 243, 255))
        return img

    def on_open(icon, item):
        webbrowser.open(url)

    def on_exit(icon, item):
        icon.stop()

    icon = pystray.Icon(
        "LocalAgent",
        create_icon(),
        "本地自动化平台",
        menu=pystray.Menu(
            pystray.MenuItem("打开仪表板", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", on_exit),
        ),
    )
    icon.run()
