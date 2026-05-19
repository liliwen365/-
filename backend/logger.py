# -*- coding: utf-8 -*-
"""日志配置 - loguru。"""
import os
import sys
from loguru import logger

from backend.config import settings


def setup_logger():
    log_dir = os.path.join(settings.DATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        os.path.join(log_dir, "localagent_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
    )


setup_logger()
