# -*- coding: utf-8 -*-
"""本地自动化平台 - 程序入口。"""
import sys
import os
import time
import webbrowser
import threading

# console=False 模式下 sys.stderr/stdout 为 None，第三方库写它们会崩溃
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import settings
from backend.logger import logger
from backend.auth import SecurityManager


def start_server(port: int):
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.HOST, port=port, log_level="info")


def main():
    # Windows + PyInstaller: 子进程必须调用 freeze_support，
    # 否则 ProcessPoolExecutor 产出的子进程会重新执行 main.py 导致崩溃
    import multiprocessing
    multiprocessing.freeze_support()

    # 建表必须在查询之前
    from backend.database import create_tables
    create_tables()

    port = settings.PORT
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动")

    # 授权检查
    security = SecurityManager()
    from backend.database import SessionLocal, SettingModel
    db = SessionLocal()
    row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
    license_code = row.value if row else ""
    db.close()

    if not security.is_activated(license_code):
        logger.warning("软件未授权，请访问 http://localhost:{}/ 激活".format(port))

    # 启动FastAPI（后台线程）
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    # 等待服务就绪后打开浏览器
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    logger.info(f"打开浏览器: {url}")
    webbrowser.open(url)

    # macOS上pystray必须在主线程运行，所以主线程跑托盘
    # Windows/Linux上托盘在子线程也可以，但统一在主线程更稳定
    try:
        from backend.utils.tray import run_tray
        logger.info("系统托盘已启动，关闭托盘图标退出程序")
        run_tray(url)  # 阻塞主线程，直到用户点退出
    except Exception as e:
        logger.debug(f"系统托盘不可用: {e}，按Ctrl+C退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    logger.info("程序退出")


if __name__ == "__main__":
    main()
