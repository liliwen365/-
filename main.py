# -*- coding: utf-8 -*-
"""本地自动化平台 - 程序入口。"""
import sys
import os
import webbrowser
import threading
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import settings
from backend.logger import logger
from backend.auth import SecurityManager


def find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((settings.HOST, 0))
        return s.getsockname()[1]


def start_server(port: int):
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.HOST, port=port, log_level="info")


def main():
    port = settings.PORT
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动")

    # 授权检查
    security = SecurityManager()
    db = __import__("backend.database", fromlist=["SessionLocal"]).SessionLocal()
    SettingModel = __import__("backend.database", fromlist=["SettingModel"]).SettingModel
    row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
    license_code = row.value if row else ""
    db.close()

    if not security.is_activated(license_code):
        logger.warning("软件未授权，请访问 http://localhost:{}/ 激活".format(port))

    # 启动FastAPI
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # 等待服务就绪后打开浏览器
    import time
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    logger.info(f"打开浏览器: {url}")
    webbrowser.open(url)

    # 系统托盘（可选，失败不影响使用）
    try:
        from backend.utils.tray import run_tray
        tray_thread = threading.Thread(target=run_tray, args=(url,), daemon=True)
        tray_thread.start()
    except Exception as e:
        logger.debug(f"系统托盘不可用: {e}")

    # 主线程等待
    try:
        signal.pause()
    except (KeyboardInterrupt, AttributeError):
        # macOS不支持signal.pause，用join代替
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    logger.info("程序退出")


if __name__ == "__main__":
    main()
